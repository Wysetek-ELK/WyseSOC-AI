# 11 — Security & RBAC Regression

- **Unauthenticated access (`RT18` live)**: `GET /api/chat/conversations` without token returned HTTP `401`.
- **Cross-user isolation (`RT18` unit)**: Analyst cannot list, read (`GET /conversations/{id}`), delete (`DELETE /conversations/{id}`), inspect telemetry (`GET /requests/{id}`), or continue (`POST /continue`) Admin's conversations (`403 Forbidden`).
- **Concurrency & GPU protection (`RT19` unit)**: `gpu_workload_manager` semaphore and circuit breaker (`503` when `OPEN`) verified; normal truncations do not trip circuit breaker.
- **AIS & Ground Truth Integrity (`RT20`–`RT22` live + unit)**: Heavy TCP active policy version, incident `#16100` `ai_verdict`, and `ground_truth` confirmed completely unchanged.
- **UPLA Security Scan (`upla-20261128-142508-2a4156`)**: 0 new blocking secrets or static findings; `npm audit` `PASS`.
