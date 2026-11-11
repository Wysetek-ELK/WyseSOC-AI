# AIS 2.0 Quality Gates G1–G8 Audit & Score Reconciliation

**Target Rule:** `PH_RULE_HEAVY_TCP_HOST_SCAN` (`9839fa49-40ac-4676-abcc-4c5581ae9e09`)  
**Reported Live Observations Reconciled:**
- Overall quality: `81` | Structural quality: `95.3%`
- G1–G7 awarded points reported as: `91/105` (Code proves **`101/105`** — see Section 2!) | G8: `0/15` (`INSUFFICIENT_DATA`)
- G1 warns about missing authoritative correlation parameters
- `validation_status: null`
- Policy `status: APPROVED`, `approval_eligible: true`, `empirical_validation_eligible: false`

---

## 1. Gate-by-Gate Audit Specification (`PolicyQualityValidator` v2.0.0)

Source: `backend/app/services/policy_quality_validator.py` (all thresholds deterministic; no runtime external config).

| Gate | Source Function & Lines | Max Gate Score (`max_score`) | Score Breakdown Bucket | Validation Logic, Thresholds & Conditions | Dependencies & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **G1: Rule Definition Integrity** | `_evaluate_gate_1_integrity` (`:347-391`) | `20.0` | `detection_semantics` (`max 20.0`) | Base `20`. **FAILED (`-10`, cap `10`)** if `definition_status` in `("INCOMPLETE", "UNKNOWN")`. **WARN (`-4`)** if `AUTO_SYNCED_FROM_INCIDENT`; **WARN (`-6`)** if `HEURISTIC_PARSER`. **WARN (`-4`)** if `"incidentCount"` or `"incidentDetail"` appears in `str(semantics.conditions) + str(prompt_version.detection_conditions)`. **FAILED (`-8`)** if `semantics.threshold is None` and S3 matches `threshold\s*[:=]\s*\d+`. | String match on `"incidentCount"`/`"incidentDetail"` inside S3 text triggers `-4.0` warning even on `VERIFIED` vendor rules. |
| **G2: Detection Archetype Relevance** | `_evaluate_gate_2_relevance` (`:394-463`) | `20.0` | Shares `detection_semantics`! (`min(g1, 10)` if WARN; `0` if FAIL) | **WARN (`10.0`)** if `archetype == UNKNOWN`. **FAILED (`0.0`)** if `NETWORK_EXFILTRATION` or `NETWORK_SCAN` has `>= 2` malware artifacts (`powershell` without scan/outbound, `lolbin`, `hash`+`sha256`, `parent process`/`ppid`, `malware execution`). Otherwise **PASSED (`20.0`)**. | Double-counted `max_score` (`20.0`) in `gate_results` despite sharing `detection_semantics` bucket with G1 (`:102, 123-126`). |
| **G3: Evidence Contract Feasibility** | `_evaluate_gate_3_contract` (`:466-512`) | `20.0` | `evidence_contract` (`max 20.0`) | Base `20`. **FAILED (`0.0`)** if `contract is None`. **WARN (`-5`)** if 0 critical fields. **FAILED (`-4`/field)** for each `archetype_def.mandatory_core_fields` absent from `contract.required_evidence`. **WARN (`-3`/field, cap `-6`)** if `prompt_version.required_evidence` requests archetype `unsupported_fields`. | Checks contract field existence, NOT whether normalized SIEM telemetry actually populates those keys (e.g., `"Destination Port"` gap). |
| **G4: TP Criteria Specificity** | `_evaluate_gate_4_tp_criteria` (`:515-538`) | `10.0` | `tp_fp_criteria` (`10` of `20`) | Base `10`. **FAILED (`0.0`)** if `len(tp_indicators.strip()) < 20`. **WARN (`-3`)** if `"suspicious"` appears without objective verbs (`exceed`, `unauthorized`, `scan`, etc.). **WARN (`-3`)** if network rule mentions `file hash`, `sha256`, `powershell download`, `quarantined`. | Purely lexical keyword heuristics; does not test logical discrimination against rule conditions. |
| **G5: FP Criteria & Benign Assumptions** | `_evaluate_gate_5_fp_criteria` (`:541-584`) | `10.0` | `tp_fp_criteria` (`10` of `20`) | Base `10`. **FAILED (`0.0`)** if `fp_indicators` treats `"rfc-1918"` or `("loopback", "127.0.0.1", "::1")` as `"benign"` without safeguard negation (`"not benign"`/`"verify"`), OR if `fp+common` matches hardcoded `confidence 60-99%`. **WARN (`-2`)** if `len < 20`. | Regex/phrase guards work well for known anti-patterns. |
| **G6: Abstention & Escalation Safety** | `_evaluate_gate_6_abstention_escalation` (`:587-620`) | `15.0` | `abstention_escalation` (`max 15.0`) | Base `15`. **FAILED (`-8`)** if `len(missing_info_criteria) < 15`. **WARN (`-3`)** if neither `"requires_attention"` nor `"abstain"` present. **WARN (`-4`)** if `len(escalation_conditions) < 15`. **FAILED (`-5`)** if escalation claims internal/RFC-1918 benign. **WARN (`-2`)** if `"isolate host immediately"` without `"human"`. | Presence/phrase check only. |
| **G7: Internal Policy Consistency** | `_evaluate_gate_7_consistency` (`:623-672`) | `10.0` | `internal_consistency` (`max 10.0`) | Base `10`. **FAILED (`-5` -> `0.0`)** if critical contract fields exist while S4 `required_evidence` `len < 10`. **WARN (`-1`/field)** for each critical field omitted from S4 text. **FAILED (`0.0`)** if `len(tp) >= 15` and `tp == fp`. **WARN** if `INCOMPLETE` semantics + `"authoritative threshold"` in S4. | Matches `field.split(".")[-1]` or full dotted name in S4 prose (`:648-649`). |
| **G8: Simulation & Regression Validation** | `_evaluate_gate_8_simulation` (`:675-737`) | `15.0` | `historical_simulation` (`max 15.0`) | If no `simulation_results` or stale `policy_digest`: **WARNING (`0.0`, `NOT_EVALUATED`)**. If `regressions > 0` or `REGRESSION_DETECTED`: **FAILED (`0.0`, `EVALUATED_FAILED`)**. If `INSUFFICIENT_DATA` or `sample_count < 5` or `eligible_count < 5`: **WARNING (`0.0`, `INSUFFICIENT_DATA`)**. If `INCONCLUSIVE` or `decision_coverage <= 0` (`overall_accuracy is None`): **WARNING (`0.0`, `INCONCLUSIVE`)**. Else **PASSED (`15.0`, `EVALUATED_PASSED`)**. | Reads stored `HistoricalEvaluationRunRecord` for matching `(rule_id, policy_version_id)`. Because AIS defaults to mock `SIMULATED` and `WARNING` adds zero blockers, G8 never blocks approval! |

---

## 2. Exact Reconciliation of All Observed Metrics & Discrepancies

**Finding IDs:** `AIS-F05`, `AIS-F06`, `AIS-F03` | **Confidence:** **CONFIRMED (Code & Unit Test Math)**

### A. Overall Quality = `81` and Structural Quality = `95.3%` (`policy_quality_validator.py:240-248`)
When `G1 = 16.0` (20 - 4 warning) and `G2–G7` achieve full marks (`G2=20`, `G3=20`, `G4=10`, `G5=10`, `G6=15`, `G7=10`), with `G8 = 0.0`:
- `score_breakdown` buckets = `{"detection_semantics": 16, "evidence_contract": 20, "tp_fp_criteria": 20, "abstention_escalation": 15, "internal_consistency": 10, "historical_simulation": 0}`.
- `structural_raw = 16 + 20 + 20 + 15 + 10 = 81.0` (out of **`85.0`** maximum structural breakdown points).
- `structural_quality_score = round(min(100.0, (81.0 / 85.0) * 100.0), 1) = round(95.2941, 1) = 95.3`!
- `quality_score = round(81.0 + 0.0, 1) = 81.0`!

### B. Denominator Mismatch (`85` vs `105`) AND the `91/105` vs `101/105` Reconciliation
- **Confirmed Scoring Defect (`AIS-F05`):** Summing individual `max_score` values across `G1..G7` yields `20 + 20 + 20 + 10 + 10 + 15 + 10 = 105` (and G1–G8 = `120`), whereas `score_breakdown` sums `85 + 15 = 100` because **both `G1` (`max=20`) and `G2` (`max=20`) map into the single 20-point `detection_semantics` bucket** (`lines 102, 123-126`).
- **Algebraic Proof Regarding `91/105` vs `101/105`:**
  In `PolicyQualityValidator` v2.0.0 (`lines 90-248`):
  - If `G1 = 16` (`score_breakdown["detection_semantics"] = 16`) and `G2 = 20 (PASSED)`, and `G3=20, G4=10, G5=10, G6=15, G7=10`:
    $$\sum_{i=1}^{7} G_i = 16 + 20 + 20 + 10 + 10 + 15 + 10 = \mathbf{101 / 105}$$
    Indeed, `frontend/tests/quality-export.test.mjs:24-116` tests this exact scenario (`quality_score: 81`, `structural_quality_score: 95.3`, `G1=16/20`, `G2=20/20`, `G3=20/20`, `G4=10/10`, `G5=10/10`, `G6=15/15`, `G7=10/10`, `G8=0/15`, sum = **`101/105`**).
  - Under current code, **it is algebraically impossible for `G1..G7` card scores to sum to `91/105` when `structural_raw = 81` (`95.3%`)**: if `G2 = 10 (WARNING)` (`-10` on G2), `lines 123-124` execute `score_breakdown["detection_semantics"] = min(16, 10) = 10`, capping `structural_raw <= 75` (`88.2%`) and `quality_score <= 75`. If `G4=0` or `G7=0` (`-10`), `structural_raw <= 71` (`83.5%`).
  - **Most Likely Explanations for Reported `91/105` (UNVERIFIED without live export JSON):** (1) Manual addition of `G1..G6` omitting `G7=10` (`16+20+20+10+10+15 = 91`), or arithmetic typo vs `101/105`; OR (2) an earlier pre-`9616971` database record / stale assessment snapshot.

### C. G1 Authoritative Correlation-Parameter Warning (`policy_quality_validator.py:370-374`)
- Triggered verbatim by:
  ```python
  s3 = getattr(prompt_version, "detection_conditions", "") or ""
  conds_str = str(getattr(semantics, "conditions", []) or []) + str(s3)
  if "incidentCount" in conds_str or "incidentDetail" in conds_str:
      warns.append("Incident runtime counter observed in rule conditions. Authoritative correlation parameters required.")
      score -= 4.0
  ```
- Deducts `4.0` pts (`20 -> 16`) with `GateStatus.WARNING` (non-blocking). Observed when either `semantics.conditions` or Section 3 text mentions `"incidentCount"` / `"incidentDetail"`. Notice `fortisiem_service.py:218` stores `"incident_detail"` in `parsed_metadata["source_incident_metrics"]`, and auto-generated or edited Section 3 notes discussing incident runtime counters trigger G1's string check cleanly.

### D. Why `validation_status: null` (`AIS-F06`)
- `backend/app/schemas/policy_quality.py:34-78` defines `empirical_validation_status` and `simulation_status` on `PolicyQualityAssessmentResponse` — **it has NO `validation_status` attribute**.
- `frontend/src/lib/qualityExport.ts:170` populates the exported JSON payload with `validation_status: assessment.validation_status || null`, which therefore **always outputs `null`**.

### E. Why `status: APPROVED` + `approval_eligible: true` + `empirical_validation_eligible: false` (`AIS-F03` — CRITICAL)
1. `PolicyQualityValidator` (`line 252`) sets `approval_eligible = (len(blocking_issues) == 0)`.
2. `G8` (`lines 712-716`) emits `GateStatus.WARNING` (not `FAILED`) when `INSUFFICIENT_DATA` (`< 5` verified cases), contributing zero blocking issues.
3. `prompts.py:454-463` correctly distinguishes three UI flags:
   - `structural_approval_eligible = True`
   - `empirical_validation_eligible = False`
   - `autonomous_operation_eligible = False`
4. **Control Breakage:**
   - `AgentPolicyEngine.approve_version` (`prompt_studio_service.py:333`) checks ONLY `if not quality_res.approval_eligible:` -> sets `PromptVersion.status = "APPROVED"`, `RulePrompt.active_version_id = target_version.id`.
   - **`VerdictTriageAgent.evaluate_incident` (`ai_verdict_service.py:277`) checks ONLY `if candidate and candidate.status == "APPROVED":`!** It does **NOT** check `autonomous_operation_eligible`, `empirical_validation_eligible`, `G8 == EVALUATED_PASSED`, or `RuleMaturityEvaluation.is_admin_approved` (`maturity_service.py`). Thus a structurally approved policy with `G8 = INSUFFICIENT_DATA` and `autonomous_operation_eligible = False` is immediately used in live SOC triage!

