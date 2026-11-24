# 07 — Five-Incident Real GPU Pilot Execution

## 1. Pilot Cohort Definition

Prior to executing the full benchmark, a controlled 5-incident pilot was executed against Server 1 (`172.26.41.240`) and Server 2 (`13.204.214.64:8000`):
- `132438483` (CrowdStrike: UltraViewer on DESKTOP-E0G2R49)
- `132527297` (CrowdStrike: UltraViewer on TSI-IT-002-95)
- `132499009` (Prisma SASE: ss-widget.min.js download)
- `132499023` (Prisma SASE: clientlib-site.min.js download)
- `132499745` (Prisma SASE: scripts-QBOKETIS.js download)

---

## 2. Pilot Execution Results

| Incident ID | Rule Category | Provenance | Latency | Prompt Tok | Comp Tok | Model Proposal | Auth Verdict | Validation Status |
|---|---|---|---|---|---|---|---|---|
| `132438483` | CrowdStrike | **LIVE_PROVIDER** | 23,835 ms | 3,365 | 491 | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | VALIDATED |
| `132527297` | CrowdStrike | **LIVE_PROVIDER** | 20,853 ms | 3,370 | 444 | `TRUE_POSITIVE` (85%) | `REQUIRES_ATTENTION` | REJECTED |
| `132499009` | Prisma SASE | **TOKEN_BUDGET_GUARD** | 445 ms | 3,709 | 0 | `None` | `REQUIRES_ATTENTION` | CONTEXT_WINDOW_EXCEEDED |
| `132499023` | Prisma SASE | **TOKEN_BUDGET_GUARD** | 454 ms | 3,747 | 0 | `None` | `REQUIRES_ATTENTION` | CONTEXT_WINDOW_EXCEEDED |
| `132499745` | Prisma SASE | **TOKEN_BUDGET_GUARD** | 448 ms | 3,701 | 0 | `None` | `REQUIRES_ATTENTION` | CONTEXT_WINDOW_EXCEEDED |

### Observations
1. **Live GPU Execution Verified**: Incidents `132438483` and `132527297` executed genuine inference on Server 2 (Qwen2.5-7B-Instruct-AWQ) with authentic token generation and latency.
2. **Admission Guard Integrity**: Incidents `132499009`, `132499023`, and `132499745` were safely intercepted in ~450ms without crashing vLLM or truncating evidence.
