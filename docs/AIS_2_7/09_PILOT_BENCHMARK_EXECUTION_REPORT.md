# AIS 2.7 — Workstream 9: Priority Pilot Benchmark Execution Report (N = 5)

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [PILOT_EXECUTION_RESULTS.json](PILOT_EXECUTION_RESULTS.json), [PILOT_ACCEPTANCE_GATE.json](PILOT_ACCEPTANCE_GATE.json), [PILOT_INFERENCE_PROVENANCE.json](PILOT_INFERENCE_PROVENANCE.json)

## 1. Pilot Gate Outcome

- **Decision:** `PILOT_TECHNICALLY_VALID_CONTINUE_BASELINE`
- **Live GPU Calls Consumed:** `10 / 10` (`5` Mode A + `5` Mode B)
- **Technical Health:** `10/10` HTTP 200, `10/10` `finish_reason='stop'`, `10/10` valid JSON schema, `0` context overflows.

## 2. Per-Incident Priority Pilot Summary

| Incident ID | Vendor | GT-2 Label | Mode A (Tokens, Latency) | Mode B (Tokens, Latency) | Mode C Validator |
|---|---|---|---|---|---|
| `132474210` | CrowdStrike | `TRUE_POSITIVE` | `FALSE_POSITIVE` (4845t, 24652.92ms) | `REQUIRES_ATTENTION` (5472t, 32491.33ms) | `REQUIRES_ATTENTION` (ABSTENTION_WITH_CONTRADICTION, trust=6) |
| `132596403` | Prisma SASE | `INCONCLUSIVE` | `FALSE_POSITIVE` (3486t, 27531.07ms) | `FALSE_POSITIVE` (5535t, 65041.92ms) | `REQUIRES_ATTENTION` (REJECTED, trust=3) |
| `132599145` | Prisma SASE | `INCONCLUSIVE` | `FALSE_POSITIVE` (3761t, 28556.7ms) | `FALSE_POSITIVE` (5830t, 40667.8ms) | `FALSE_POSITIVE` (VALIDATED, trust=3) |
| `132438483` | CrowdStrike | `TRUE_POSITIVE` | `FALSE_POSITIVE` (5653t, 51028.4ms) | `REQUIRES_ATTENTION` (6271t, 29909.48ms) | `REQUIRES_ATTENTION` (ABSTENTION_WITH_CONTRADICTION, trust=6) |
| `132591888` | Prisma SASE | `INCONCLUSIVE` | `FALSE_POSITIVE` (3618t, 28297.75ms) | `FALSE_POSITIVE` (5721t, 45200.14ms) | `REQUIRES_ATTENTION` (INSUFFICIENT_EVIDENCE, trust=3) |

Early empirical signal spotted during pilot: Mode A predicted `FALSE_POSITIVE` on `5/5`, Mode B falsely claimed `process.command_line` missing on both CrowdStrike TPs and missed all 3 Prisma `INCONCLUSIVE` alerts, while Mode C blocked `2/3` Prisma errors and flagged missing-field contradictions. Technical infrastructure passed; full cohort authorized to continue.
