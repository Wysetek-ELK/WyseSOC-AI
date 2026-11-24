# 08 — Five-Incident Real GPU Pilot Execution Report

## Executive Summary

This report documents the controlled 5-incident pilot executed against Server 1 (`172.26.41.240`) and Server 2 (`13.204.214.64:8000`) to verify end-to-end inference connectivity, latency telemetry, and preflight guardrail behavior before full benchmark evaluation.

---

## 1. Pilot Cohort & Execution Telemetry

| Incident ID | Rule Category | Execution Provenance | Latency (ms) | Prompt Tokens | Completion Tokens | Proposed Verdict | Auth Verdict | Validation Status |
|---|---|---|---|---|---|---|---|---|
| `132438483` | CrowdStrike | **LIVE_PROVIDER** | 23,835 | 3,365 | 491 | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | ABSTENTION_WITH_CONTRADICTION |
| `132527297` | CrowdStrike | **LIVE_PROVIDER** | 20,853 | 3,370 | 444 | `TRUE_POSITIVE` (85%) | `REQUIRES_ATTENTION` | REJECTED |
| `132499009` | Prisma SASE | **PREFLIGHT_ABSTENTION** | 445 | 0 | 0 | `None` | `REQUIRES_ATTENTION` | CONTEXT_WINDOW_EXCEEDED |
| `132499023` | Prisma SASE | **PREFLIGHT_ABSTENTION** | 454 | 0 | 0 | `None` | `REQUIRES_ATTENTION` | CONTEXT_WINDOW_EXCEEDED |
| `132499745` | Prisma SASE | **PREFLIGHT_ABSTENTION** | 448 | 0 | 0 | `None` | `REQUIRES_ATTENTION` | CONTEXT_WINDOW_EXCEEDED |

---

## 2. Key Findings

1. **Genuine GPU Inference Verified**:
   - Incidents `132438483` and `132527297` dispatched genuine inference to Qwen2.5-7B-Instruct-AWQ on Server 2 with average latency of 22.3 seconds and 467 completion tokens.
2. **Deterministic Preflight Guardrail Verified**:
   - Incidents `132499009`, `132499023`, and `132499745` were intercepted locally in ~450 ms without consuming GPU memory or socket connections.
