# Report 05: Asynchronous Simulation Lab & Replay Processing (P4-REQ-05)

## 1. Problem Statement

In the Simulation Lab, security engineers replay historical datasets (often spanning 100 to 1,000+ incidents) to test proposed prompt revisions, evaluate rule precision, and analyze calibration curves.

In previous implementations, simulation replays ran synchronously within the HTTP request lifecycle. When evaluating 50+ incidents, HTTP request timeouts (typically 60s at the Nginx reverse proxy level) caused premature connection termination and lost progress tracking.

---

## 2. Decoupled Asynchronous Simulation Architecture

Phase 4 decouples long-running dry-run jobs from synchronous HTTP request loops:

```
+---------------------------------------------------------------------------------------------------+
|                                      FRONTEND NEXT.JS CLIENT                                      |
|                                                                                                   |
|   1. POST /api/dry-run/trigger (Starts replay)                                                    |
|      <--- Returns HTTP 201 Created with job_id and status="RUNNING"                               |
|                                                                                                   |
|   2. GET /api/dry-run/jobs/{job_id}/progress (Periodic polling every 2s)                          |
|      <--- Returns processed_items, total_items, progress_percent, eta_seconds                     |
|                                                                                                   |
|   3. Optional: POST /api/dry-run/jobs/{job_id}/cancel (Clean operator termination)                |
|      <--- Sets status="CANCELLED" and aborts gracefully after current incident                    |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                 SERVER 1 VALIDATION REPLAY ENGINE                                 |
|                                                                                                   |
|   - Streams incidents in dataset partition                                                        |
|   - Executes token budgeting and compiled policy per incident                                     |
|   - Checks cancellation flag on each iteration loop                                               |
|   - Persists bifurcated token consumption and telemetry timeline milestones                       |
|   - Commits partial results even if cancelled or interrupted                                      |
+---------------------------------------------------------------------------------------------------+
```

---

## 3. Real-Time Telemetry & Progress Polling API

The endpoint `GET /api/dry-run/jobs/{job_id}/progress` provides real-time progress analytics:

```json
{
  "job_id": "9d8e7f6a-5b4c-3d2e-1f0a-9b8c7d6e5f4a",
  "config_id": "conf-alpha-7b",
  "status": "RUNNING",
  "total_items": 250,
  "processed_items": 142,
  "error_count": 0,
  "progress_percent": 56.8,
  "elapsed_seconds": 38,
  "eta_seconds": 29,
  "is_simulated": false,
  "started_at": "2026-11-08T17:10:00.000Z",
  "completed_at": null
}
```

### Dynamic ETA Calculation:
The engine computes instantaneous processing velocity:
$$\text{velocity} = \frac{\text{processed\_items}}{\max(1, \text{elapsed\_seconds})}$$
$$\text{eta\_seconds} = \frac{\text{total\_items} - \text{processed\_items}}{\text{velocity}}$$

---

## 4. Safe Operator Cancellation

If an analyst discovers that a prompt configuration contains an error or if an urgent live triage burst occurs, the operator can cancel an active replay:
- **API Endpoint:** `POST /api/dry-run/jobs/{job_id}/cancel`
- **Loop Interruption:** In `ValidationEngine.execute_dry_run_job()`, before processing each incident, the loop inspects `job.status`:
  ```python
  status_check = await self.db.execute(select(DryRunJob.status).where(DryRunJob.id == job.id))
  if status_check.scalar_one_or_none() == "CANCELLED":
      job.status = "CANCELLED"
      job.completed_at = datetime.utcnow()
      await self.db.commit()
      return job
  ```
- **Integrity Preservation:** All results processed up to the cancellation moment are committed and preserved for inspection. The database is never left in an uncommitted or corrupted state.

---

## 5. Verification Evidence

Test module `backend/tests/test_async_simulation.py` validates:
- `test_dry_run_job_progress_and_cancellation`: PASSED. Confirms progress computation, percentage accuracy, ETA estimations, and clean cancellation termination.

