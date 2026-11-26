# 09 — GPU Smoke Test & Priority Five-Incident Pilot

- **Pre-Fix Contention Root Cause**: Background FortiSIEM auto-triage across 4 uvicorn workers saturated Server 2's `--max-num-seqs 1` queue, causing 4 smoke-test failures (`task-173`, `task-181`, `task-215`, `task-240`) and 1 pilot timeout (`task-224` on `132474210`).
- **Post-Deploy Verification (`215f744c`)**:
  - Persistent scheduler stop verified (`is_running=False`, `active_requests=0`, `waiting_requests=0`).
  - Synthetic smoke test succeeded: `chatcmpl-b6de0ebd1e1f8817`, HTTP `200`, `47+14=61` tokens, `822.09 ms`, `finish_reason=stop`.
- **Priority 5 Pilot Progression (`132474210, 132596403, 132599145, 132438483, 132591888`)**:
  - Technical completion: `5/5` (`100%`) in Experiments A, B, C, and R.
  - Intelligence progression: `Exp C` parsed `5/5 (100%)` accurately (`TRUE_POSITIVE` on both CrowdStrike TPs; `REQUIRES_ATTENTION` on all 3 Prisma Inconclusives); validator confirmed `4/5` (blocking only `132474210` due to Mode B `8088+104=8192` token truncation).
