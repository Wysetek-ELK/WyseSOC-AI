# AIS 2.0 Ground Truth & Analyst Resolution Eligibility Audit

**Target Rule:** `PH_RULE_HEAVY_TCP_HOST_SCAN` (`9839fa49-40ac-4676-abcc-4c5581ae9e09`)  
**Observed Issue Under Investigation:** Only **1 of 2** rule-matched incidents qualified as independently verified ground truth during AIS G8 simulation.

---

## 1. End-to-End Ground Truth Provenance & Qualification Mechanism

### Storage & Provenance
1. **Primary Closure Table (`historical_ground_truth` / `HistoricalGroundTruth`):**
   Populated at ingestion (`ingestion_service.py:631-655`) or resolution sync (`fortisiem_service.py:1047-1180`) from FortiSIEM incident fields:
   - `resolution` (`incidentRes` / `resolution` / `incidentResolution` / `Resolution`)
   - `cleared_reason` (`clearedReason` / `incidentClearedReason` / `clearReason`)
   - `comments` (`comments` / `incidentComments` / `Comments`)
   - `cleared_user` (`clearedUser` / `cmsClearUser` / `clearUser` / `caseUser`)
   - `cleared_time_epoch`, `resolved_at_epoch`
   - `is_ml_generated` (boolean flag computed at ingest/sync)
2. **Workbench Investigation Table (`investigations` / `Investigation`):**
   Holds live analyst triage tracking (`analyst_verdict`, `is_disputed`, `is_independently_verified`, `analyst_notes`).

### Funnel Evaluation Sequence in AIS (`policy_simulation_service.py:446-591`)
For each incident in `rows`, AIS executes these deterministic checks **in order**:

1. **`RULE_MISMATCH` (`lines 452-477`):** Skips via `continue` if `inc.rule_id not in rule_ids`.
2. **`SYNTHETIC_FIXTURE_EXCLUDED` (`line 501`, `historical_ground_truth_validator.py:104-125`):** Rejects if `raw_payload.is_synthetic`/`synthetic` is True, `gt.provenance == "SYNTHETIC_FIXTURE"`, or `incident_id` starts with `("INC-DEBUG", "SYNTHETIC-", "DEBUG-FIXTURE")` with zero events (`events` and `rawEvents` empty).
3. **`CORRUPT_OR_EMPTY_PAYLOAD` or `MISSING_EVIDENCE` (`line 502`, `historical_ground_truth_validator.py:128-143`):** Rejects `CORRUPT_OR_EMPTY_PAYLOAD` when `raw_payload` is empty/falsy (or empty dict with no `source_ip` and 0 events); rejects `MISSING_EVIDENCE` when `events == []`, `source_ip` is empty, and `raw_payload` contains only `("metadata", "rawEventCount", "incidentId", "id")` with no `rawEvents`.
4. **`MISSING_ANALYST_LABEL` (`lines 513-516`):** Rejects when `HistoricalGroundTruth` record is absent or `gt.resolution` is empty/null.
   - *Counted as `analyst_labeled += 1` (`line 518`) for all incidents passing steps 1–4.*
5. **`HEURISTIC_OR_ML_LABEL` (`lines 526-535`, `historical_ground_truth_validator.py:81-101`):**
   Checks `_is_automated_resolution_text`: rejects as ML/automated if `gt.is_ml_generated` is True **OR** any of `"machine learning"`, `"resolution set by machine learning"`, `"automated"`, `"auto-cleared"`, `"auto cleared"`, `"ai verdict"`, `"simulated-heuristic"`, `"ml generated"` appears in `comments + cleared_reason + cleared_user + provenance`, OR `provenance` in `("AI_GENERATED", "ML_GENERATED", "SIMULATED", "HEURISTIC")`.
6. **`AMBIGUOUS_LABEL` (`lines 537-551`, `historical_ground_truth_validator.py:187-252`):**
   - Rejects `UNKNOWN` if `resolution` is empty or in `("UNKNOWN", "OPEN", "IN_PROGRESS", "NEW")`.
   - Rejects `UNVERIFIED` (`AMBIGUOUS_LABEL`) if `resolution` is merely a closure status without TP/FP disposition: `("CLOSED", "MANUALLY CLEARED", "AUTO CLEARED", "CLEARED", "RESOLVED", "CLOSE", "MITIGATED", "BLOCKED", "KILLED")`, or unrecognized strings (e.g., `"Under Investigation"`).
   - Accepts `VERIFIED_TP` if resolution contains `("TRUE POSITIVE", "TRUE_POSITIVE", "MALICIOUS", "ATTACK", "INCIDENT")`.
   - Accepts `VERIFIED_FP` if resolution contains `("FALSE POSITIVE", "FALSE_POSITIVE", "BENIGN", "AUTHORIZED", "EXPECTED", "NO_ACTION")`.
   - Rejects `CONFLICTING` if `("CONFLICT", "DISPUTED", "AMBIGUOUS", "INCONCLUSIVE")` in resolution.
7. **`DUPLICATE_CLUSTER_EXCLUDED` (`lines 553-561`, `historical_ground_truth_validator.py:166-184`):**
   Builds cluster key `sha256(f"{rule_key}|{adj_label}|epoch:{cleared_time_epoch}|{reason_norm}")[:16]` whenever `cleared_time_epoch` is non-zero and normalized `cleared_reason` length `>= 8`. Retains ONLY the incident with the highest event count (tie-breaking on lexicographically smallest `incident_id`).

---

## 2. Confirmed Ground-Truth Bugs & Local Database Proof

**Finding ID:** `AIS-F04` | **Severity:** HIGH | **Confidence:** **CONFIRMED (Code-level + Local Dev SQLite DB)**

### Bug A — Substring `"ml"` False Positive at Ingestion & Sync
- `backend/app/services/ingestion_service.py:639`:
  ```python
  is_ml_generated = (
      ...
      "ml" in comments.lower() or
      ...
  )
  ```
- `backend/app/services/fortisiem_service.py:1145`:
  ```python
  is_ml_generated = (
      ...
      "ML" in comments or
      ...
  )
  ```
Any human analyst closure comment containing everyday words/acronyms like `"normal"`, `"html"`, `"xml"`, `"yaml"`, `"similar"`, `"gmail"`, `"cmdline"`, or `"SAML"` permanently flags `HistoricalGroundTruth.is_ml_generated = True`, disqualifying valid human ground truth forever.

### Bug B — FortiSIEM Default `"Resolution set by Machine Learning"` Overrides Real Human Attribution
**Observed in Local Dev SQLite (`backend/ai_verdict.db`, 26 incidents / 24 ground truth rows):**
- **13 of 24** `historical_ground_truth` rows have `is_ml_generated = 1`.
- Inspection of actual imported FortiSIEM incidents in `backend/ai_verdict.db` shows analysts explicitly entering human disposition notes and/or human `cleared_user` while FortiSIEM retains `"Resolution set by Machine Learning"` in `comments`:
  - Incident `132501348` (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`, `Manually Cleared`, `resolution="True Positive"`): **`cleared_user="Yash Mungekar"`**, `comments="Resolution set by Machine Learning\nWe have observed the Crowdstrike user admin compromise using Disable or Modify Tools detected on DESKTOP-DR1F46U"`, `is_ml_generated=1` -> **excluded as `HEURISTIC_OR_ML_LABEL`**!
  - Incident `132461358` (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`, `Manually Cleared`, `resolution="False Positive"`): **`cleared_user="shivamw"`**, `cleared_reason="hash value is clean"`, `comments="Resolution set by Machine Learning"`, `is_ml_generated=1` -> **excluded as `HEURISTIC_OR_ML_LABEL`**!
  - Incidents `132502453`, `132527297`, `132438483`, `132461368`, `132472498`, `132499023`, `132499745`, `132578774`, `132591888`, `132595592`: all carry human `cleared_reason` text (`"Endpoint security has blocked the ultraviewer.exe"`, `"Informed to client, alert still generating"`, `"file observed is not suspicious"`), yet because `comments` contains `"Resolution set by Machine Learning"`, `is_ml_generated=1` causes total rejection.
- `HistoricalGroundTruthValidator._is_automated_resolution_text` (`historical_ground_truth_validator.py:81-101`) returns `True` immediately on `is_ml_generated` or `"machine learning" in combined` without checking whether a human `cleared_user` or human rationale in `cleared_reason` / second line of `comments` superseded the default ML boilerplate.

### Bug C — Simulation Omits `Investigation.is_disputed` Check (`AIS-F09` Part)
- `HistoricalEligibilityService.generate_eligibility_report` (`historical_eligibility_service.py:185`) explicitly excludes disputed cases (`if inc.id in disputed_inc_db_ids: disputed += 1; continue`).
- `PolicySimulationService.run_dry_run_intelligence_evaluation` (`policy_simulation_service.py:501-580`) **never queries `Investigation.is_disputed`**. Disputed labels can pass into G8 metrics if `gt.resolution` parses as TP/FP.

### Bug D — Excluded `RULE_MATCHED` Incidents Still Proceed to Evaluation & DB Persistence (`AIS-F09` Part)
In `policy_simulation_service.py:581-695`, after recording `exclusion_reason` for a `RULE_MATCHED` incident (`HEURISTIC_OR_ML_LABEL`, `AMBIGUOUS_LABEL`, `MISSING_ANALYST_LABEL`, `DUPLICATE_CLUSTER_EXCLUDED`, `CORRUPT_OR_EMPTY_PAYLOAD`), there is **no `continue`** statement. All excluded rule-matched incidents still pass to inference (`lines 593-695`), get written to `historical_evaluation_results` (making `evaluated_cases > eligible`, e.g., local run `645aa5c8` logged `rule_matched=6, eligible=2, evaluated=6`), and inflate latency/token cost. (`is_correct` stays `None` because `gt_label` stays `None`.)

### Containment-Only FP Caveat (`is_containment_only_fp_note`, lines 146-163)
Notice `HistoricalGroundTruthValidator.is_containment_only_fp_note` flags FP closures whose notes only state `"kill process"`/`"blocked"` without benign context (`e.g. 132439932` `"kill process is true"`), attaching a metadata warning `weak_containment_fp_note=True` (`line 578`), though it does **not** exclude them from `eligible_count`.

---

## 3. Why Only 1 of 2 Matched Incidents Qualified (Diagnostic Matrix + Live Verification SQL)

Because the 2 matched incidents for `PH_RULE_HEAVY_TCP_HOST_SCAN` reside in remote PostgreSQL (`UNVERIFIED`), the exact reason why the 2nd incident was excluded is one of the 6 funnel gates in `PolicySimulationService:501-580`. Run this read-only SQL + diagnostic query on the live server to inspect both incidents side by side:

```sql
-- Per-incident eligibility inspection for PH_RULE_HEAVY_TCP_HOST_SCAN
SELECT i.id AS inc_uuid,
       i.incident_id,
       i.rule_id,
       i.event_type,
       i.status_name,
       i.source_ip,
       (SELECT COUNT(*) FROM incident_events ie WHERE ie.incident_id = i.id) AS event_count,
       jsonb_typeof(i.raw_payload::jsonb) AS payload_type,
       gt.resolution,
       gt.is_ml_generated,
       gt.cleared_user,
       gt.cleared_reason,
       gt.cleared_time_epoch,
       gt.comments,
       inv.is_disputed,
       inv.analyst_verdict
FROM incidents i
LEFT JOIN historical_ground_truth gt ON gt.incident_id = i.id
LEFT JOIN investigations inv ON inv.incident_id = i.id
WHERE i.rule_id IN ('9839fa49-40ac-4676-abcc-4c5581ae9e09', 'PH_RULE_HEAVY_TCP_HOST_SCAN')
   OR i.event_type = 'PH_RULE_HEAVY_TCP_HOST_SCAN'
ORDER BY i.created_at DESC;
```

### Exact Per-Incident Exclusion Mapping Table

| If the Query Shows... | AIS Exclusion Code (`PolicySimulationService`) | Expected vs Defect? |
| :--- | :--- | :--- |
| `gt.resolution IS NULL` | `MISSING_ANALYST_LABEL` | Expected (open/unclosed alert) |
| `gt.is_ml_generated = true` or `"ml"`/`"machine learning"` in `comments` | `HEURISTIC_OR_ML_LABEL` | **Defect if** `"ml"` matched a substring (`normal`/`html`) or human `cleared_user` / `cleared_reason` overrode ML default |
| `gt.resolution` in `('Closed', 'Cleared', 'Under Investigation')` without `TP`/`FP` | `AMBIGUOUS_LABEL` | Expected unless closure reason clearly states TP/FP disposition |
| Matching `(rule, adj_label, cleared_time_epoch, reason_norm)` with another incident | `DUPLICATE_CLUSTER_EXCLUDED` | Expected de-duplication, provided timestamps aren't defaulted |
| `event_count = 0` AND (`raw_payload` empty or wrapper-only) | `CORRUPT_OR_EMPTY_PAYLOAD` or `MISSING_EVIDENCE` | Expected telemetry hygiene check (unless events failed enrichment) |
| `INC-DEBUG*` / `synthetic=true` | `SYNTHETIC_FIXTURE_EXCLUDED` | Expected synthetic isolation |

