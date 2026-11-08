import pytest
import asyncio
from app.services.gpu_manager import (
    GPUServerCircuitBreaker,
    GPUWorkloadManager,
    CircuitState,
    CircuitBreakerOpenException,
)


@pytest.mark.asyncio
async def test_circuit_breaker_trips_to_open_after_threshold():
    """Verifies that consecutive failures trip the circuit breaker from CLOSED to OPEN."""
    cb = GPUServerCircuitBreaker(failure_threshold=3, recovery_time_seconds=1.0)
    assert cb.state == CircuitState.CLOSED

    # 1. First failure
    await cb.record_failure("Timeout 1")
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 1

    # 2. Second failure
    await cb.record_failure("Timeout 2")
    assert cb.state == CircuitState.CLOSED

    # 3. Third failure -> TRIPS TO OPEN
    await cb.record_failure("Timeout 3")
    assert cb.state == CircuitState.OPEN
    assert cb.total_trips == 1

    # While OPEN, can_execute returns False
    can_run = await cb.can_execute()
    assert can_run is False


@pytest.mark.asyncio
async def test_circuit_breaker_recovery_cycle():
    """Verifies recovery cycle: OPEN -> HALF_OPEN after cooldown -> CLOSED on success."""
    cb = GPUServerCircuitBreaker(failure_threshold=2, recovery_time_seconds=0.1)

    # Trip to OPEN
    await cb.record_failure("Err 1")
    await cb.record_failure("Err 2")
    assert cb.state == CircuitState.OPEN

    # Wait for cooldown
    await asyncio.sleep(0.15)

    # First call after cooldown transitions to HALF_OPEN
    can_run = await cb.can_execute()
    assert can_run is True
    assert cb.state == CircuitState.HALF_OPEN

    # Successful probe restores to CLOSED
    await cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.consecutive_failures == 0


@pytest.mark.asyncio
async def test_gpu_workload_manager_bounded_concurrency():
    """Verifies bounded concurrency slot acquisition and release."""
    mgr = GPUWorkloadManager(max_concurrent=2)
    assert mgr.active_requests == 0

    await mgr.acquire_inference_slot()
    assert mgr.active_requests == 1

    await mgr.acquire_inference_slot()
    assert mgr.active_requests == 2

    # Release slots
    await mgr.release_inference_slot(success=True)
    assert mgr.active_requests == 1

    await mgr.release_inference_slot(success=True)
    assert mgr.active_requests == 0

