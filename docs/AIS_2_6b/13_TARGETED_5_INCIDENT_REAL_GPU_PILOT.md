# 13 — Targeted 5-Incident Real GPU Pilot Execution Report

## 1. Pilot Cohort & Execution Telemetry
| Incident ID | Rule Category | Provenance | Latency (ms) | Prompt Tokens | Comp Tokens | Finish | Proposed | Final Verdict | Status |
|---|---|---|---|---|---|---|---|---|---|
| `132474210` | CrowdStrike | LIVE_PROVIDER | 34,176 | 6,384 | 555 | stop | TRUE_POSITIVE | TRUE_POSITIVE | VALIDATED |
| `132596403` | Prisma SASE | LIVE_PROVIDER | 28,173 | 3,042 | 571 | stop | TRUE_POSITIVE | REQUIRES_ATTENTION | REJECTED |
| `132599145` | Prisma SASE | LIVE_PROVIDER | 37,609 | 3,350 | 524 | stop | TRUE_POSITIVE | REQUIRES_ATTENTION | INSUFFICIENT_EVIDENCE |
| `132461368` | CrowdStrike | LIVE_PROVIDER | 27,993 | 4,834 | 573 | stop | TRUE_POSITIVE | TRUE_POSITIVE | VALIDATED |
| `132599330` | Prisma SASE | LIVE_PROVIDER | 39,986 | 3,351 | 675 | stop | TRUE_POSITIVE | REQUIRES_ATTENTION | INSUFFICIENT_EVIDENCE |

## 2. Go/No-Go Decision: GO
- HTTP 400 Bad Requests: 0 (Target: 0)
- Completion Truncations: 0 (Target: 0)
- Decisive Verdicts: 2 (Target: >=1)
- Unsafe False Positives: 0 (Target: 0)
- Unique Wire Hashes: 5/5

