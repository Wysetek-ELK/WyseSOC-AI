# Phase 8.2 — Remaining Work & Phase 9 Readiness Prerequisites

**Current Phase 9 Readiness Status:** `NOT_ESTABLISHED` (`PHASE_8_2_BLOCKED`)

Because Phase 8.2 remediated every discovered software, corpus-filtering, metric-integrity, normalization, and RBAC defect (`P8.2-DEF-001` through `P8.2-DEF-007`), **all remaining Phase 8.2 -> Phase 9 prerequisites depend strictly on provisioning live non-production staging infrastructure and accumulating genuine human-adjudicated SOC labels:**

1. **Provision Isolated Staging Target (Non-Production):**
   - PostgreSQL instance (`DBM-01-C2`: run `alembic upgrade head` -> `007_distributed_locks`).
   - Redis broker/backend + Celery worker processes (`WRK-02-C2`: execute distributed task locking on real Redis/Celery).
   - Server 2 GPU / vLLM OpenAI-compatible inference server hosting `Qwen/Qwen2.5-7B-Instruct-AWQ` (`LLM-01-C2`, `MON-02-C2`: execute real inference and capture real GPU/VRAM telemetry).
   - Staging FortiSIEM supervisor or authorized live REST feed with valid TLS verification `FORTISIEM_VERIFY_SSL=true` (`FSI-01-C3`).
2. **Execute Real-Model Historical Replay (`QGS-02-C3`):**
   - Run `PolicySimulationService` against live Server 2 (`allow_mock_fallback=False`) using clean non-synthetic, deduplicated historical incidents.
3. **Accumulate Clean Independent Ground Truth (`>= 5` for G8, `>= 30` for Calibration):**
   - Current corpus yields only `3` independent human-labeled groups on `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (`2` containing weak containment-only notes) and `3` on `Prisma_SASE_Suspicious_File_Threat_Detection_`.
   - Adjudicate `>= 5` independent non-synthetic incidents per active rule to unlock G8 regression certification and `>= 30` with both TP and FP classes to enable Platt/isotonic probability calibration.

