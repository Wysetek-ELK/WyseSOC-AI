import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from app.database import AsyncSessionLocal
from app.config import settings
from app.services.fortisiem_service import FortiSIEMService


class FortiSIEMSyncScheduler:
    """
    Continuous FortiSIEM Background Sync Poller.
    Executes an initial comprehensive pull of incidents,
    followed by automated incremental polling every N seconds (default: 180s / 3 mins).
    Idempotently ingests incoming telemetry and automatically triggers AI Verdicts via LLM.
    """

    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._is_running: bool = False

        self.interval_seconds: int = 180
        self.auto_ai_verdict: bool = True
        self.initial_pull_completed: bool = False
        self.checkpoint_epoch: Optional[int] = None

        self.last_sync_time: Optional[datetime] = None
        self.next_sync_time: Optional[datetime] = None
        self.last_status: str = "IDLE"  # IDLE, RUNNING, SUCCESS, ERROR
        self.last_error: Optional[str] = None

        self.total_pulled_count: int = 0
        self.total_ai_verdicts_count: int = 0
        self.recent_sync_logs: List[Dict[str, Any]] = []

    @property
    def is_running(self) -> bool:
        return self._is_running and self._task is not None and not self._task.done()

    def start(self, interval_seconds: int = 180, auto_ai_verdict: bool = True) -> Dict[str, Any]:
        """Starts the background continuous sync loop if not already running."""
        if self.is_running:
            return self.get_status()

        self.interval_seconds = max(30, int(interval_seconds))
        self.auto_ai_verdict = bool(auto_ai_verdict)
        self._is_running = True
        self._stop_event.clear()
        self.last_status = "IDLE"
        self.last_error = None

        self._task = asyncio.create_task(self._worker_loop())
        return self.get_status()

    def stop(self) -> Dict[str, Any]:
        """Gracefully halts the continuous background poller."""
        self._is_running = False
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
        self.last_status = "STOPPED"
        self.next_sync_time = None
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """Returns the real-time operational status, statistics, and sync history."""
        return {
            "is_running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "auto_ai_verdict": self.auto_ai_verdict,
            "initial_pull_completed": self.initial_pull_completed,
            "checkpoint_epoch": self.checkpoint_epoch,
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "next_sync_time": self.next_sync_time.isoformat() if self.next_sync_time else None,
            "last_status": self.last_status,
            "last_error": self.last_error,
            "total_pulled_count": self.total_pulled_count,
            "total_ai_verdicts_count": self.total_ai_verdicts_count,
            "recent_sync_logs": self.recent_sync_logs[-15:],
        }

    async def trigger_immediate_sync(self, force_pull_all: bool = False) -> Dict[str, Any]:
        """Manually runs an immediate sync cycle without resetting the continuous interval."""
        return await self._execute_single_cycle(force_pull_all=force_pull_all)

    async def _worker_loop(self):
        """Continuous background execution loop."""
        try:
            # First cycle executes immediately on start
            try:
                await self._execute_single_cycle(force_pull_all=not self.initial_pull_completed)
            except Exception as e:
                self.last_status = "ERROR"
                self.last_error = f"Initial cycle error: {str(e)}"

            while self._is_running:
                now = datetime.now(timezone.utc)
                self.next_sync_time = now + timedelta(seconds=self.interval_seconds)

                # Wait for interval or stop event
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=float(self.interval_seconds))
                    # Stop event was set
                    break
                except asyncio.TimeoutError:
                    # Timeout reached: execute next cycle
                    pass

                if not self._is_running:
                    break

                try:
                    await self._execute_single_cycle(force_pull_all=False)
                except Exception as e:
                    self.last_status = "ERROR"
                    self.last_error = f"Periodic cycle error: {str(e)}"

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.last_status = "ERROR"
            self.last_error = f"Fatal scheduler worker error: {str(exc)}"
        finally:
            self._is_running = False

    async def _execute_single_cycle(self, force_pull_all: bool = False) -> Dict[str, Any]:
        """Executes a single ingestion cycle against FortiSIEM and generates AI verdicts."""
        self.last_status = "RUNNING"
        start_time = datetime.now(timezone.utc)
        cycle_result = {}

        try:
            async with AsyncSessionLocal() as session:
                service = FortiSIEMService(session)

                if force_pull_all or (not self.initial_pull_completed and self.checkpoint_epoch is None):
                    # Initial Pull: pull all historical incidents
                    cycle_result = await service.pull_all_incidents(
                        max_count=200,
                        auto_triage_llm=self.auto_ai_verdict,
                        force_refresh=False,
                        username="scheduler",
                    )
                    self.initial_pull_completed = True
                else:
                    # Incremental Pull: pull incidents since watermark
                    cycle_result = await service.pull_incremental_incidents(
                        since_epoch=self.checkpoint_epoch,
                        lookback_minutes=max(5, (self.interval_seconds // 60) + 2),
                        auto_triage_llm=self.auto_ai_verdict,
                        username="scheduler",
                    )

                newly_ingested = cycle_result.get("newly_ingested", 0)
                already_cached = cycle_result.get("already_cached", 0)
                ai_verdicts = cycle_result.get("ai_verdicts_generated", 0)
                checkpoint = cycle_result.get("checkpoint_epoch")

                if checkpoint:
                    self.checkpoint_epoch = max(self.checkpoint_epoch or 0, checkpoint)

                self.total_pulled_count += newly_ingested
                self.total_ai_verdicts_count += ai_verdicts
                self.last_status = "SUCCESS"
                self.last_error = None
                self.last_sync_time = start_time

                log_entry = {
                    "timestamp": start_time.isoformat(),
                    "status": "SUCCESS",
                    "mode": cycle_result.get("source", "UNKNOWN"),
                    "newly_ingested": newly_ingested,
                    "already_cached": already_cached,
                    "ai_verdicts_generated": ai_verdicts,
                    "message": cycle_result.get("message", ""),
                }
                self.recent_sync_logs.append(log_entry)
                return cycle_result

        except Exception as exc:
            self.last_status = "ERROR"
            self.last_error = str(exc)
            self.last_sync_time = start_time
            log_entry = {
                "timestamp": start_time.isoformat(),
                "status": "ERROR",
                "error": str(exc),
            }
            self.recent_sync_logs.append(log_entry)
            return {"success": False, "error": str(exc), "status": "ERROR"}


# Global singleton instance
fortisiem_scheduler = FortiSIEMSyncScheduler()
