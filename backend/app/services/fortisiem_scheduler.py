import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from app.database import AsyncSessionLocal
from app.config import settings, BASE_DIR
from app.services.fortisiem_service import FortiSIEMService

logger = logging.getLogger("ai_verdict.fortisiem_scheduler")


class SentinelIngestWorker:
    """
    Sentinel Ingest Worker & Continuous Telemetry Poller.
    Continuous background sync poller and telemetry ingestion worker.
    Executes an initial comprehensive pull of incidents,
    followed by automated incremental polling every N seconds (default: 180s / 3 mins).
    Idempotently ingests incoming telemetry and automatically triggers AI Verdicts via LLM.

    Resilience & Multi-Worker Architecture:
    - Durable state persistence in `scheduler_state.json` (and settings) so continuous
      sync survives server reboots, systemd restarts, deployments, and worker recycles.
    - Distributed leader election across multiple Uvicorn worker processes with heartbeats
      and stale-leader takeover (guarantees exactly one active polling loop).
    - Fault-tolerant execution: transient FortiSIEM network timeouts or LLM offline states
      never terminate the continuous loop; it logs the error and continues to the next cycle.
    """

    def __init__(self, state_file_path: Optional[str] = None):
        self._worker_id: str = f"worker-{os.getpid()}-{uuid.uuid4().hex[:6]}"
        self._task: Optional[asyncio.Task] = None
        self._supervisor_task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._shutdown_requested: bool = False
        self._is_local_leader: bool = False

        # State file configuration
        if state_file_path:
            self._state_file = state_file_path
        elif "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ:
            self._state_file = os.path.join(BASE_DIR, "test_scheduler_state.json")
        else:
            self._state_file = os.path.join(BASE_DIR, "scheduler_state.json")

        # In-memory mirrors populated from persisted state
        self.interval_seconds: int = 180
        self.auto_ai_verdict: bool = True
        self.initial_pull_completed: bool = False
        self.checkpoint_epoch: Optional[int] = None
        self.last_sync_time: Optional[datetime] = None
        self.next_sync_time: Optional[datetime] = None
        self.last_status: str = "IDLE"  # IDLE, RUNNING, SUCCESS, ERROR, STOPPED
        self.last_error: Optional[str] = None
        self.total_pulled_count: int = 0
        self.total_ai_verdicts_count: int = 0
        self.recent_sync_logs: List[Dict[str, Any]] = []

        # Load initial state from file if present
        self._sync_from_persisted_state()

    def _default_state(self) -> Dict[str, Any]:
        return {
            "is_enabled": False,
            "interval_seconds": 180,
            "auto_ai_verdict": True,
            "initial_pull_completed": False,
            "checkpoint_epoch": None,
            "last_sync_time": None,
            "next_sync_time": None,
            "last_status": "IDLE",
            "last_error": None,
            "total_pulled_count": 0,
            "total_ai_verdicts_count": 0,
            "recent_sync_logs": [],
            "leader_id": None,
            "heartbeat_at": None,
        }

    def _read_state(self) -> Dict[str, Any]:
        """Reads persistent scheduler state from file atomically."""
        if not os.path.exists(self._state_file):
            state = self._default_state()
            # If settings indicate auto poll is enabled, reflect it
            if getattr(settings, "FORTISIEM_AUTO_POLL_ENABLED", False):
                state["is_enabled"] = True
                state["interval_seconds"] = getattr(settings, "FORTISIEM_POLL_INTERVAL_SECONDS", 180)
                state["auto_ai_verdict"] = getattr(settings, "FORTISIEM_AUTO_AI_VERDICT", True)
            self._write_state(state)
            return state

        try:
            with open(self._state_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**self._default_state(), **data}
        except Exception as exc:
            logger.warning(f"Could not read scheduler state file ({exc}); falling back to defaults.")
            return self._default_state()

    def _write_state(self, state: Dict[str, Any]) -> None:
        """Writes persistent scheduler state using atomic file replacement."""
        tmp_file = f"{self._state_file}.tmp.{os.getpid()}"
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self._state_file)), exist_ok=True)
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_file, self._state_file)
        except Exception as exc:
            logger.error(f"Failed to write scheduler state file: {exc}")
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass

    def _sync_from_persisted_state(self) -> Dict[str, Any]:
        """Syncs in-memory instance attributes with persisted state."""
        state = self._read_state()
        self.interval_seconds = int(state.get("interval_seconds", 180))
        self.auto_ai_verdict = bool(state.get("auto_ai_verdict", True))
        self.initial_pull_completed = bool(state.get("initial_pull_completed", False))
        self.checkpoint_epoch = state.get("checkpoint_epoch")

        last_sync = state.get("last_sync_time")
        if last_sync:
            try:
                self.last_sync_time = datetime.fromisoformat(last_sync)
            except Exception:
                self.last_sync_time = None
        else:
            self.last_sync_time = None

        next_sync = state.get("next_sync_time")
        if next_sync:
            try:
                self.next_sync_time = datetime.fromisoformat(next_sync)
            except Exception:
                self.next_sync_time = None
        else:
            self.next_sync_time = None

        self.last_status = state.get("last_status", "IDLE")
        self.last_error = state.get("last_error")
        self.total_pulled_count = int(state.get("total_pulled_count", 0))
        self.total_ai_verdicts_count = int(state.get("total_ai_verdicts_count", 0))
        self.recent_sync_logs = state.get("recent_sync_logs", [])[-25:]
        return state

    @property
    def is_running(self) -> bool:
        """
        Returns True if continuous sync is active (enabled in persistent state and/or running locally).
        Authoritative across all worker processes.
        """
        state = self._read_state()
        return bool(state.get("is_enabled", False))

    def start_supervisor(self) -> None:
        """
        Starts the background supervisor task for this worker process.
        Invoked during FastAPI lifespan startup across all workers.
        """
        if self._supervisor_task is None or self._supervisor_task.done():
            self._shutdown_requested = False
            self._supervisor_task = asyncio.create_task(self._supervisor_loop())
            logger.info(f"Sentinel supervisor started for worker {self._worker_id}")

    def shutdown_worker(self) -> None:
        """
        Gracefully terminates local tasks for this worker process during app shutdown/reload.
        CRITICAL: Does NOT disable continuous sync in the state file, allowing the next worker
        or restarted process to automatically resume execution.
        """
        self._shutdown_requested = True
        self._stop_event.set()

        if self._task and not self._task.done():
            self._task.cancel()

        if self._supervisor_task and not self._supervisor_task.done():
            self._supervisor_task.cancel()

        backlog_task = getattr(self, "_backlog_task", None)
        if backlog_task and not backlog_task.done():
            backlog_task.cancel()

        # Release leadership if this worker was the active leader
        state = self._read_state()
        state_changed = False
        if state.get("leader_id") == self._worker_id:
            state["leader_id"] = None
            state["heartbeat_at"] = None
            state_changed = True
        if state.get("backlog_worker_id") == self._worker_id:
            state["backlog_worker_id"] = None
            state["backlog_heartbeat_at"] = None
            state_changed = True
        if state_changed:
            self._write_state(state)
        self._is_local_leader = False

    def start(self, interval_seconds: int = 180, auto_ai_verdict: bool = True) -> Dict[str, Any]:
        """
        Starts continuous FortiSIEM background sync.
        Persists state so polling continues permanently across server restarts and worker lifecycles.
        """
        self.interval_seconds = max(30, int(interval_seconds))
        self.auto_ai_verdict = bool(auto_ai_verdict)
        settings.FORTISIEM_AUTO_POLL_ENABLED = True
        settings.FORTISIEM_POLL_INTERVAL_SECONDS = self.interval_seconds
        settings.FORTISIEM_AUTO_AI_VERDICT = self.auto_ai_verdict

        now_utc = datetime.now(timezone.utc)
        state = self._read_state()
        state["is_enabled"] = True
        state["interval_seconds"] = self.interval_seconds
        state["auto_ai_verdict"] = self.auto_ai_verdict
        state["leader_id"] = self._worker_id
        state["heartbeat_at"] = now_utc.isoformat()
        if state.get("last_status") == "STOPPED":
            state["last_status"] = "IDLE"
        state["last_error"] = None
        self._write_state(state)

        self._is_local_leader = True
        self._stop_event.clear()
        self._shutdown_requested = False

        # Launch local worker task if not already executing
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._worker_loop())

        # Ensure supervisor is running
        self.start_supervisor()

        logger.info(f"Continuous FortiSIEM sync started (interval: {self.interval_seconds}s, worker: {self._worker_id})")
        return self.get_status()

    def stop(self) -> Dict[str, Any]:
        """
        Explicitly halts continuous FortiSIEM background polling.
        Persists disabled state so polling remains halted until explicitly re-enabled.
        """
        settings.FORTISIEM_AUTO_POLL_ENABLED = False
        self._stop_event.set()

        if self._task and not self._task.done():
            self._task.cancel()

        state = self._read_state()
        state["is_enabled"] = False
        state["last_status"] = "STOPPED"
        state["next_sync_time"] = None
        state["leader_id"] = None
        state["heartbeat_at"] = None
        self._write_state(state)
        self._is_local_leader = False

        self._sync_from_persisted_state()
        logger.info("Continuous FortiSIEM sync halted explicitly.")
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        """
        Returns real-time operational status, metrics, and sync history.
        Authoritative across all Uvicorn worker processes via durable state file.
        """
        state = self._sync_from_persisted_state()
        is_running = bool(state.get("is_enabled", False))

        return {
            "is_running": is_running,
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
            "leader_id": state.get("leader_id"),
        }

    async def trigger_immediate_sync(self, force_pull_all: bool = False) -> Dict[str, Any]:
        """Manually runs an immediate sync cycle without resetting the continuous interval."""
        return await self._execute_single_cycle(force_pull_all=force_pull_all)

    def _try_claim_or_renew_leadership(self) -> bool:
        """
        Checks if this worker is or should become the active leader.
        Takes over leadership if no leader is registered or if leader heartbeat is older than 60s.
        """
        state = self._read_state()
        if not state.get("is_enabled", False):
            return False

        now = datetime.now(timezone.utc)
        leader_id = state.get("leader_id")
        heartbeat_str = state.get("heartbeat_at")

        is_stale = True
        if heartbeat_str:
            try:
                hb = datetime.fromisoformat(heartbeat_str)
                if hb.tzinfo is None:
                    hb = hb.replace(tzinfo=timezone.utc)
                if (now - hb).total_seconds() < 60.0:
                    is_stale = False
            except Exception:
                is_stale = True

        if leader_id == self._worker_id:
            # Renew our own lease
            state["heartbeat_at"] = now.isoformat()
            self._write_state(state)
            self._is_local_leader = True
            return True

        if not leader_id or is_stale:
            # Claim leadership
            logger.info(f"Worker {self._worker_id} taking over leadership (previous leader: {leader_id}, stale: {is_stale})")
            state["leader_id"] = self._worker_id
            state["heartbeat_at"] = now.isoformat()
            self._write_state(state)
            self._is_local_leader = True
            return True

        self._is_local_leader = False
        return False

    def _get_backlog_lock(self) -> asyncio.Lock:
        lock = getattr(self, "_backlog_lock", None)
        if lock is None:
            lock = asyncio.Lock()
            self._backlog_lock = lock
        return lock

    def _claim_or_renew_backlog_lease(self) -> bool:
        """
        Cross-worker coordinator lease for background pending-incident AI reconciliation.
        Ensures only one worker drains pending verdicts even when continuous FortiSIEM polling is off.
        """
        state = self._read_state()
        now = datetime.now(timezone.utc)
        owner = state.get("backlog_worker_id")
        hb_str = state.get("backlog_heartbeat_at")

        is_stale = True
        if hb_str:
            try:
                hb = datetime.fromisoformat(hb_str)
                if hb.tzinfo is None:
                    hb = hb.replace(tzinfo=timezone.utc)
                if (now - hb).total_seconds() < 90.0:
                    is_stale = False
            except Exception:
                is_stale = True

        if owner == self._worker_id or not owner or is_stale:
            state["backlog_worker_id"] = self._worker_id
            state["backlog_heartbeat_at"] = now.isoformat()
            self._write_state(state)
            return True
        return False

    async def run_pending_reconciliation_until_drained(
        self,
        max_batch: int = 25,
        max_batches: int = 60,
        username: str = "llm_backlog_worker",
    ) -> Dict[str, Any]:
        """
        Sequentially drains pending incidents (ai_verdict IS NULL) once Local LLM Server 2 is online.
        Runs without short asyncio.wait_for cancellation timers so real GPU inference completes cleanly.
        """
        from app.services.llm_config_service import LLMConfigService
        lock = self._get_backlog_lock()
        if lock.locked():
            return {
                "success": True,
                "already_running": True,
                "processed": 0,
                "failed": 0,
                "pending_remaining": None,
                "message": "Pending verdict reconciliation is already running in this worker.",
            }

        async with lock:
            total_processed = 0
            total_failed = 0
            last_remaining = 0
            is_llm_online = False

            for _ in range(max_batches):
                if getattr(self, "_shutdown_requested", False):
                    break

                LLMConfigService.sync_runtime_settings()
                self._claim_or_renew_backlog_lease()

                try:
                    async with AsyncSessionLocal() as session:
                        service = FortiSIEMService(session)
                        res = await service.process_pending_incidents(
                            max_count=max_batch,
                            username=username,
                        )
                except Exception as exc:
                    logger.warning(f"[Pending Verdict Reconciliation Error]: {exc}")
                    break

                is_llm_online = bool(res.get("is_llm_online", False))
                processed = int(res.get("processed", 0))
                failed = int(res.get("failed", 0))
                last_remaining = int(res.get("pending_remaining", 0))
                total_processed += processed
                total_failed += failed

                if processed > 0:
                    self.total_ai_verdicts_count += processed
                    st = self._read_state()
                    st["total_ai_verdicts_count"] = self.total_ai_verdicts_count
                    self._write_state(st)

                if not is_llm_online or last_remaining == 0 or processed == 0:
                    break

            return {
                "success": is_llm_online or total_processed > 0,
                "is_llm_online": is_llm_online,
                "processed": total_processed,
                "failed": total_failed,
                "pending_remaining": last_remaining,
                "message": (
                    f"Processed {total_processed} pending incidents ({last_remaining} remaining)."
                    if is_llm_online
                    else f"Local LLM (Server 2) unavailable; {last_remaining} incidents remain pending."
                ),
            }

    def trigger_pending_reconciliation(
        self,
        force: bool = False,
        username: str = "llm_backlog_worker",
    ) -> bool:
        """
        Triggers asynchronous background reconciliation of pending incidents if not already running.
        """
        if getattr(self, "_shutdown_requested", False):
            return False

        is_pytest = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
        if is_pytest and not force:
            return False

        existing = getattr(self, "_backlog_task", None)
        if existing is not None and not existing.done():
            return False

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return False

        self._backlog_task = asyncio.create_task(
            self.run_pending_reconciliation_until_drained(username=username)
        )
        return True

    async def _supervisor_loop(self) -> None:
        """
        Supervisor loop running in every worker process:
        - Monitors `scheduler_state.json`.
        - If continuous sync is enabled, ensures a healthy leader is actively running.
        - If Server 2 LLM is online and pending incidents exist, ensures one worker reconciles them cleanly.
        """
        from app.services.llm_config_service import LLMConfigService
        from app.services.ai_verdict_service import AIVerdictService

        check_counter = 0
        while not self._shutdown_requested:
            try:
                LLMConfigService.sync_runtime_settings()
                state = self._read_state()
                is_enabled = bool(state.get("is_enabled", False)) or getattr(settings, "FORTISIEM_AUTO_POLL_ENABLED", False)
                auto_ai_verdict = bool(state.get("auto_ai_verdict", True))

                if is_enabled:
                    if not state.get("is_enabled", False):
                        state["is_enabled"] = True
                        self._write_state(state)

                    if self._try_claim_or_renew_leadership():
                        if self._task is None or self._task.done():
                            self._stop_event.clear()
                            self._task = asyncio.create_task(self._worker_loop())
                else:
                    if self._task and not self._task.done():
                        self._stop_event.set()
                        self._task.cancel()
                    self._is_local_leader = False

                # Even when FortiSIEM polling is off, check every ~30s if pending verdicts await an online Server 2
                check_counter += 1
                is_pytest = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ
                if (
                    auto_ai_verdict
                    and not is_pytest
                    and check_counter % 3 == 1
                    and (getattr(self, "_backlog_task", None) is None or self._backlog_task.done())
                ):
                    if self._claim_or_renew_backlog_lease():
                        async with AsyncSessionLocal() as session:
                            verdict_svc = AIVerdictService(session)
                            pending_count = await verdict_svc.get_pending_incident_count()
                        if pending_count > 0 and await AIVerdictService.is_local_llm_available():
                            self.trigger_pending_reconciliation(username="llm_auto_reconciler")

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning(f"[Supervisor Error in {self._worker_id}]: {exc}")

            try:
                await asyncio.sleep(10.0)
            except asyncio.CancelledError:
                break

    async def _worker_loop(self) -> None:
        """
        Continuous background execution loop.
        Runs permanently while `is_enabled` is True in state.
        Errors during sync cycles are recorded in logs and never terminate the continuous poller.
        """
        logger.info(f"Continuous sync worker loop started on {self._worker_id}")

        # Check if initial pull or immediate cycle is needed
        state = self._read_state()
        should_run_immediately = (
            state.get("next_sync_time") is None
            or not state.get("initial_pull_completed", False)
        )

        if should_run_immediately and not self._stop_event.is_set():
            try:
                await asyncio.wait_for(
                    self._execute_single_cycle(force_pull_all=not self.initial_pull_completed),
                    timeout=180.0,
                )
            except Exception as e:
                logger.error(f"Initial sync cycle error: {e}")
                self._record_cycle_error(f"Initial cycle error: {str(e)}")

        while not self._stop_event.is_set() and not self._shutdown_requested:
            state = self._read_state()
            if not state.get("is_enabled", False):
                break

            self.interval_seconds = int(state.get("interval_seconds", 180))
            now = datetime.now(timezone.utc)
            self.next_sync_time = now + timedelta(seconds=self.interval_seconds)

            # Update next sync time in state
            state["next_sync_time"] = self.next_sync_time.isoformat()
            state["heartbeat_at"] = now.isoformat()
            self._write_state(state)

            # Sleep interval in 15-second chunks:
            # Updates heartbeat and processes backlog when Local LLM comes online
            elapsed = 0
            step = 15
            while elapsed < self.interval_seconds and not self._stop_event.is_set() and not self._shutdown_requested:
                wait_time = min(step, self.interval_seconds - elapsed)
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=float(wait_time))
                    break  # Stop event was set
                except asyncio.TimeoutError:
                    elapsed += wait_time

                # Refresh heartbeat
                hb_now = datetime.now(timezone.utc)
                st = self._read_state()
                if not st.get("is_enabled", False) or st.get("leader_id") != self._worker_id:
                    # Leadership lost or paused
                    break
                st["heartbeat_at"] = hb_now.isoformat()
                self._write_state(st)

                # Process pending incident triage backlog asynchronously without killing batches on short timeouts
                if self.auto_ai_verdict and not self._stop_event.is_set():
                    try:
                        from app.services.llm_config_service import LLMConfigService
                        LLMConfigService.sync_runtime_settings()
                        self.trigger_pending_reconciliation(username="scheduler")
                    except Exception as pend_exc:
                        logger.warning(f"[Scheduler Worker Backlog Trigger Warning]: {pend_exc}")

            if self._stop_event.is_set() or self._shutdown_requested:
                break

            # Re-check state before running cycle
            state = self._read_state()
            if not state.get("is_enabled", False) or state.get("leader_id") != self._worker_id:
                break

            # Execute periodic sync cycle with timeout
            try:
                await asyncio.wait_for(
                    self._execute_single_cycle(force_pull_all=False),
                    timeout=180.0,
                )
            except Exception as e:
                logger.error(f"Periodic sync cycle error: {e}")
                self._record_cycle_error(f"Periodic cycle error: {str(e)}")

        logger.info(f"Continuous sync worker loop exited on {self._worker_id}")

    def _record_cycle_error(self, err_msg: str) -> None:
        """Records error in state without stopping continuous polling."""
        self.last_status = "ERROR"
        self.last_error = err_msg
        now_iso = datetime.now(timezone.utc).isoformat()
        state = self._read_state()
        state["last_status"] = "ERROR"
        state["last_error"] = err_msg
        logs = state.get("recent_sync_logs", [])
        logs.append({
            "timestamp": now_iso,
            "status": "ERROR",
            "error": err_msg,
        })
        state["recent_sync_logs"] = logs[-25:]
        self._write_state(state)

    async def _execute_single_cycle(self, force_pull_all: bool = False) -> Dict[str, Any]:
        """Executes a single ingestion cycle against FortiSIEM and generates AI verdicts."""
        self.last_status = "RUNNING"
        start_time = datetime.now(timezone.utc)
        cycle_result: Dict[str, Any] = {}

        # Update status to RUNNING in state file
        state = self._read_state()
        state["last_status"] = "RUNNING"
        self._write_state(state)

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

                # Process an immediate slice of pending incidents if Local LLM is online, then drain remainder asynchronously
                if self.auto_ai_verdict:
                    try:
                        from app.services.llm_config_service import LLMConfigService
                        LLMConfigService.sync_runtime_settings()
                        pending_res = await asyncio.wait_for(
                            service.process_pending_incidents(max_count=10, username="scheduler"),
                            timeout=180.0,
                        )
                        backlog_processed = pending_res.get("processed", 0)
                        if backlog_processed > 0:
                            ai_verdicts += backlog_processed
                        if pending_res.get("pending_remaining", 0) > 0 and pending_res.get("is_llm_online"):
                            self.trigger_pending_reconciliation(username="scheduler")
                    except Exception as pend_exc:
                        logger.warning(f"[Scheduler Backlog Warning]: {pend_exc}")

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

                # Persist updated metrics and logs
                st = self._read_state()
                st["initial_pull_completed"] = self.initial_pull_completed
                st["checkpoint_epoch"] = self.checkpoint_epoch
                st["total_pulled_count"] = self.total_pulled_count
                st["total_ai_verdicts_count"] = self.total_ai_verdicts_count
                st["last_status"] = "SUCCESS"
                st["last_error"] = None
                st["last_sync_time"] = start_time.isoformat()
                logs = st.get("recent_sync_logs", [])
                logs.append(log_entry)
                st["recent_sync_logs"] = logs[-25:]
                self._write_state(st)

                return cycle_result

        except Exception as exc:
            self._record_cycle_error(str(exc))
            return {"success": False, "error": str(exc), "status": "ERROR"}


# Global singleton instance and aliases
SentinelIngestWorkerAlias = SentinelIngestWorker
FortiSIEMSyncScheduler = SentinelIngestWorker
sentinel_ingest_worker = SentinelIngestWorker()
fortisiem_scheduler = sentinel_ingest_worker
