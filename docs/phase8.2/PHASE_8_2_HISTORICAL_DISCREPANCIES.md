# Phase 8.2 — Stage C Forensic Investigation of Historical Discrepancies (`132439932`, `132441815`, `132474210`)

**Evidence Sources:**
- `docs/phase8.2/evidence/historical-data/stage_c_crowdstrike_discrepancies.json`
- `docs/phase8.2/evidence/verdicts/stage_c_e_verdict_inventory.json`

## 1. Corpus Context Across All 26 Seeded Incidents

Across all 26 incidents in `backend/ai_verdict.db`, **100% (`26/26`)** stored `ai_verdict` JSON blobs originate from `"simulated-heuristic-v1"` (`TRUE_POSITIVE: 15`, `REQUIRES_ATTENTION: 9`, `FALSE_POSITIVE: 2`), with **`0` rows** in `verdict_trust_assessments`, **`0` rows** in `evidence_sufficiency_assessments`, and `6` rows in `token_usage_records`. Zero stored historical verdicts were produced by live Server 2 LLM inference.

## 2. Incident-by-Incident Forensic Record (Read-Only Trace — Zero Silent Overwrites)

All 3 flagged incidents belong to rule `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (`Crowdstrike: Suspicious Activity`, customer `Tosoh`, reporting device `api.us-2.crowdstrike.com`), share `UltraViewer_Service.exe`, IOC domain `update.ultraviewer.net`, IOA rule `Ultraviewer Domain Block`, `"Process Blocked": "false"`, `"KillProcess": true`, and `"PatternDispositionDescription": "Prevention, process killed."`. All 3 have `is_ml_generated = false`, empty `cleared_user = ""`, local `Investigation(status = 'PENDING_REVIEW', analyst_verdict = None, is_independently_verified = 0)`, `verdict_trust_rows = 0`, `evidence_sufficiency_rows = 0`, and `token_usage_rows = 0`.

| Incident ID | Host & Events | Stored AI Verdict (`simulated-heuristic-v1`) | Historical Resolution | `cleared_reason` | Containment-Only FP Note | Forensic Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `132439932` | `TSI-IT-002-200` (8 events) | `TRUE_POSITIVE` (`94.0%`, `latency_ms=12`, `0 tokens`, `evaluated_by_user=scheduler`, `2026-11-07T12:40:59.598943`) | `False Positive` | `"kill process is true"` | `true` (`cleared_time_epoch=1793783492775`) | **Primary:** `HISTORICAL_SNAPSHOT`<br>**Secondary:** `DIFFERENT_VERDICT_SEMANTICS`, `LABEL_ERROR` |
| `132441815` | `DESKTOP-E0G2R49` (16 events) | `TRUE_POSITIVE` (`94.0%`, `latency_ms=12`, `0 tokens`, `evaluated_by_user=scheduler`, `2026-11-07T12:40:59.776620`) | `False Positive` | `"proccess is kiled"` | `true` (`cleared_time_epoch=1793784466188`) | **Primary:** `HISTORICAL_SNAPSHOT`<br>**Secondary:** `DIFFERENT_VERDICT_SEMANTICS`, `LABEL_ERROR` |
| `132474210` | `PC-TSI-DC` (13 events) | `TRUE_POSITIVE` (`94.0%`, `latency_ms=12`, `0 tokens`, `evaluated_by_user=scheduler`, `2026-11-07T12:41:00.574172`) | `False Positive` | `"legitimate activity, nothing suspicious observed."` | `false` (`cleared_time_epoch=1793798921497`) | **Primary:** `HISTORICAL_SNAPSHOT`<br>**Secondary:** `EVIDENCE_ERROR` (empty `clearedUser` + unverified local `Investigation`) |

## 3. Root Cause Summary

1. None of the 3 discrepancies represent a Server 2 LLM classification error: all 3 were emitted in a legacy `"scheduler"` batch by `"simulated-heuristic-v1"` on `2026-11-07T12:40:59–12:41:00` prior to AIS 2.1 validation/trust persistence.
2. `132439932` and `132441815` conflate **EDR process kill containment** (`"kill process is true"` / `"proccess is kiled"` while `"Process Blocked": "false"`) with **benign False Positive**. Under AIS 2.1 policy semantics, an unauthorized remote-access tool terminated by EDR containment (`KillProcess=true`) is not benign unless affirmative business authorization exists.
3. `HistoricalGroundTruthValidator.is_containment_only_fp_note` and `adjudicate_label` now flag weak containment-only closures for Tier-2 review without silently mutating historical records.

