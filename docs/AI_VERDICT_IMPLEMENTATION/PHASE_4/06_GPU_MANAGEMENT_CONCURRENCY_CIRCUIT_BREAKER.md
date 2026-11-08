# Report 06: Workload Scalability & Local GPU Management (P4-REQ-06)

## 1. Hardware Capacity Boundaries

In the two-server architecture, Server 2 operates a dedicated NVIDIA GPU (e.g. NVIDIA T4 with 16GB VRAM on an AWS EC2 `g4dn.2xlarge` instance) running vLLM.

### Hardware Constraints:
- **Quantization:** AWQ 4-bit (`Qwen2.5-7B-Instruct-AWQ`).
- **GPU Memory Allocation:** ~9.5GB model weights + ~4GB KV cache = ~13.5GB utilized.
- **Max Concurrency Limit:** 4 concurrent active inference streams. Exceeding 4 concurrent requests risks KV cache exhaustion, Out-Of-Memory (OOM) aborts, or severe response latency spikes (>60s).

---

## 2. Concurrency Semaphore & Workload Management

Phase 4 implements `GPUWorkloadManager` in `backend/app/services/gpu_manager.py`:
- **Bounded Concurrency Slots:** Uses an `asyncio.Semaphore` capped at `settings.LLM_MAX_CONCURRENT_REQUESTS` (default: 4).
- **Active Slot Tracking:** Maintains real-time tracking of `active_requests` and `available_slots`.
- **Automatic Queue Backpressure:** If the backlog of triage tasks exceeds `QUEUE_BACKPRESSURE_LIMIT` (default: 1,000), new background simulation jobs are throttled with HTTP 429/503 to preserve GPU throughput for live incoming SIEM alerts.

---

## 3. Circuit Breaker Architecture (`GPUServerCircuitBreaker`)

To prevent Server 1 from cascading into failure when Server 2 experiences temporary hardware stalls, GPU resets, or network disconnects, `GPUServerCircuitBreaker` enforces a three-state machine:

```
               +----------------------------------------------------+
               |                       CLOSED                       |
               |         (Normal Operation: Requests Allowed)       |
               +----------------------------------------------------+
                     |                                       ^
                     | Consecutive Failures >= 5             | Probe Succeeded
                     v                                       |
               +----------------------------------------------------+
               |                        OPEN                        |
               |        (Server 2 Offline: Fail-Fast Rejection)     |
               +----------------------------------------------------+
                     |                                       ^
                     | Cooldown Elapsed (>= 30.0s)           | Probe Failed
                     v                                       |
               +----------------------------------------------------+
               |                     HALF_OPEN                      |
               |       (Testing Recovery: 1 Single Probe Allowed)   |
               +----------------------------------------------------+
```

### State Transitions & Safety Controls:
1. **`CLOSED` (Normal):** Requests pass freely to Server 2. Each success resets `consecutive_failures` to 0.
2. **`OPEN` (Fail-Fast):** When `consecutive_failures` reaches 5 (configurable via `LLM_CIRCUIT_BREAKER_FAIL_THRESHOLD`), the circuit trips to `OPEN`. All incoming requests immediately fail fast with `CircuitBreakerOpenException` without waiting for the 60s network timeout.
3. **`HALF_OPEN` (Probe):** After a 30-second cooldown (`LLM_CIRCUIT_BREAKER_RECOVERY_TIME`), the circuit enters `HALF_OPEN`. It permits exactly one test request:
   - If the request succeeds, the circuit immediately resets to `CLOSED`.
   - If the request fails, the circuit immediately trips back to `OPEN` for another 30-second cooldown cycle.

---

## 4. Integration into AI Verdict Service

In `app/services/ai_verdict_service.py`, all calls to `OPENAI_COMPATIBLE` (Server 2) are guarded:

```python
if use_gpu_manager:
    from app.services.gpu_manager import gpu_workload_manager, CircuitBreakerOpenException
    try:
        await gpu_workload_manager.acquire_inference_slot()
    except CircuitBreakerOpenException as cb_exc:
        if not allow_mock:
            raise LocalLLMUnavailableError(str(cb_exc))
        # Fallback to simulated provider if explicitly allowed in dev/test
        chosen_provider_type = "SIMULATED"
        use_gpu_manager = False

try:
    verdict = await provider.analyze_incident(...)
    if use_gpu_manager:
        await gpu_workload_manager.release_inference_slot(
            success=(not is_connection_error),
            error_message=verdict.reason if is_connection_error else ""
        )
except Exception as exc:
    if use_gpu_manager:
        await gpu_workload_manager.release_inference_slot(success=False, error_message=str(exc))
    raise
```

---

## 5. Verification Evidence

Test module `backend/tests/test_gpu_circuit_breaker.py` validates:
- `test_circuit_breaker_trips_to_open_after_threshold`: PASSED. Confirms transition to `OPEN` after threshold reached and fail-fast rejection while `OPEN`.
- `test_circuit_breaker_recovery_cycle`: PASSED. Confirms cooldown elapsed -> `HALF_OPEN` -> successful probe resets to `CLOSED`.
- `test_gpu_workload_manager_bounded_concurrency`: PASSED. Confirms bounded slots: 0 -> 1 -> 2 -> 1 -> 0.

