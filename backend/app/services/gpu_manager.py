import asyncio
import time
import logging
from enum import Enum
from typing import Dict, Any, Optional
from app.config import settings

logger = logging.getLogger("ai_verdict.gpu_manager")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"        # Normal operation: all requests allowed through
    OPEN = "OPEN"            # Server 2 is failing: fail-fast to prevent cascade
    HALF_OPEN = "HALF_OPEN"  # Testing recovery: single probe allowed


class CircuitBreakerOpenException(Exception):
    """Raised when Local GPU Server 2 circuit breaker is OPEN."""
    pass


class GPUServerCircuitBreaker:
    """
    Production-grade circuit breaker protecting Server 1 from hanging on Server 2 GPU outages.
    - Consecutive failure tracking
    - Exponential / cooldown recovery transitions
    - Half-open single probe testing
    """
    def __init__(
        self,
        failure_threshold: int = settings.LLM_CIRCUIT_BREAKER_FAIL_THRESHOLD,
        recovery_time_seconds: float = settings.LLM_CIRCUIT_BREAKER_RECOVERY_TIME,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_time_seconds = recovery_time_seconds
        self.state: CircuitState = CircuitState.CLOSED
        self.consecutive_failures: int = 0
        self.consecutive_successes: int = 0
        self.last_failure_time: float = 0.0
        self.last_state_change: float = time.time()
        self.total_trips: int = 0
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Determines whether a call to Server 2 is permitted."""
        async with self._lock:
            now = time.time()
            if self.state == CircuitState.OPEN:
                if (now - self.last_failure_time) >= self.recovery_time_seconds:
                    logger.info("Circuit breaker recovery cooldown elapsed. Transitioning to HALF_OPEN.")
                    self.state = CircuitState.HALF_OPEN
                    self.last_state_change = now
                    return True
                return False
            return True

    async def record_success(self) -> None:
        """Records a successful response from Server 2."""
        async with self._lock:
            self.consecutive_failures = 0
            if self.state == CircuitState.HALF_OPEN:
                self.consecutive_successes += 1
                if self.consecutive_successes >= 1:
                    logger.info("Probe request succeeded in HALF_OPEN. Resetting circuit to CLOSED.")
                    self.state = CircuitState.CLOSED
                    self.consecutive_successes = 0
                    self.last_state_change = time.time()

    async def record_failure(self, error_message: str = "") -> None:
        """Records a failed or timed-out request to Server 2."""
        async with self._lock:
            now = time.time()
            self.consecutive_failures += 1
            self.last_failure_time = now

            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"Probe request failed in HALF_OPEN: {error_message}. Tripping back to OPEN.")
                self.state = CircuitState.OPEN
                self.last_state_change = now
                self.total_trips += 1
            elif self.state == CircuitState.CLOSED:
                if self.consecutive_failures >= self.failure_threshold:
                    logger.error(
                        f"Consecutive failure threshold ({self.failure_threshold}) reached for Server 2 GPU. "
                        f"Tripping circuit breaker to OPEN! Last error: {error_message}"
                    )
                    self.state = CircuitState.OPEN
                    self.last_state_change = now
                    self.total_trips += 1

    def get_status(self) -> Dict[str, Any]:
        """Telemetry snapshot of circuit breaker status."""
        return {
            "state": self.state.value,
            "consecutive_failures": self.consecutive_failures,
            "failure_threshold": self.failure_threshold,
            "recovery_time_seconds": self.recovery_time_seconds,
            "seconds_since_last_failure": round(time.time() - self.last_failure_time, 1) if self.last_failure_time else None,
            "total_trips": self.total_trips,
        }


class GPUWorkloadManager:
    """
    Manages concurrency, circuit breaking, and backpressure for Local LLM Server 2.
    """
    def __init__(self, max_concurrent: int = settings.LLM_MAX_CONCURRENT_REQUESTS):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.circuit_breaker = GPUServerCircuitBreaker()
        self.max_concurrent = max_concurrent
        self.active_requests: int = 0
        self._lock = asyncio.Lock()

    async def acquire_inference_slot(self) -> None:
        """Acquires a concurrency slot and checks circuit breaker."""
        can_run = await self.circuit_breaker.can_execute()
        if not can_run:
            raise CircuitBreakerOpenException(
                f"Local LLM Server 2 Circuit Breaker is OPEN. "
                f"Consecutive failures: {self.circuit_breaker.consecutive_failures}. Fast-failing."
            )

        # Acquire concurrency semaphore slot
        await self.semaphore.acquire()
        async with self._lock:
            self.active_requests += 1

    async def release_inference_slot(self, success: bool, error_message: str = "") -> None:
        """Releases the concurrency slot and records outcome in circuit breaker."""
        try:
            if success:
                await self.circuit_breaker.record_success()
            else:
                await self.circuit_breaker.record_failure(error_message)
        finally:
            async with self._lock:
                self.active_requests = max(0, self.active_requests - 1)
            self.semaphore.release()

    def check_backpressure(self, current_queue_depth: int) -> bool:
        """Returns True if the system is under excessive backpressure."""
        return current_queue_depth >= settings.QUEUE_BACKPRESSURE_LIMIT

    def get_telemetry(self) -> Dict[str, Any]:
        """Provides runtime telemetry on active GPU requests and circuit breaker."""
        return {
            "active_requests": self.active_requests,
            "max_concurrent_slots": self.max_concurrent,
            "available_slots": max(0, self.max_concurrent - self.active_requests),
            "circuit_breaker": self.circuit_breaker.get_status(),
        }


# Global GPU Workload Manager instance
gpu_workload_manager = GPUWorkloadManager()

