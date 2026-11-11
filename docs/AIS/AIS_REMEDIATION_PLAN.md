# AIS 2.0 Prioritized Remediation Plan

**Constraint Notice:** This document is a **read-only engineering plan** derived strictly from verified code & local database defects. **Zero edits** have been made to the codebase or configuration.

---

## Priority Overview

| Priority | Finding IDs | Focus Area | Impact |
| :-: | :--- | :--- | :--- |
| **P0 (Critical Safety)** | `AIS-F03` | Enforce G8 / Autonomous-Operation Gating | Prevents unvalidated policies (`G8 = INSUFFICIENT_DATA`) from driving live automated AI verdicts |
| **P1 (Core Accuracy & Retrieval)** | `AIS-F01`, `AIS-F02`, `AIS-F04`, `AIS-F09` | Rule-scoped retrieval, real LLM simulation, clean GT ML filter, parity with `IndependentVerdictValidator` | Fixes `52` (`50+2`) scan bug, enables real LLM G8 validation on `NETWORK_SCAN`, recovers valid human GT |
| **P2 (Scoring, Normalization & Mapping)** | `AIS-F05`, `AIS-F06`, `AIS-F07`, `AIS-F08`, `AIS-F10` | Align G1–G8 weights (`100` vs `105`), export status, `"Destination Port"` normalization, consistent `event_type` lookup | Eliminates confusing `85`/`105` gate math, `validation_status: null`, and telemetry false abstentions |
| **P3 (Architecture & Config Hygiene)** | `AIS-F11`, `AIS-F12`, `AIS-F13` | Consolidate duplicate dry-run vs VI engines, async queue execution, `.env` hygiene, live SQL audit | Removes legacy drift (`DryRun` vs `AIS`), prevents HTTP timeouts, verifies 2,900+ remote DB state |

---

## Detailed Remediation Work Packages

### Work Package 1 (`P0` / `AIS-F03`): Enforce Three-Tier Eligibility in Live Triage & Approval
- **Affected Files & Functions:**
  - `backend/app/services/prompt_studio_service.py`: `AgentPolicyEngine.approve_version` (`lines 242-384`)
  - `backend/app/services/ai_verdict_service.py`: `VerdictTriageAgent.evaluate_incident` (`lines 272-360`)
  - `backend/app/api/prompts.py`: `approve_prompt_version` (`lines 701-729`)
- **Current Behavior:** Policies pass `approve_version` solely on `structural_approval_eligible` (`blocking_issues == 0`), even when `G8 = INSUFFICIENT_DATA` (`autonomous_operation_eligible = False`). `VerdictTriageAgent` accepts any `PromptVersion` with `status == "APPROVED"`.
- **Expected Behavior:** Distinguish **Structural Approval (Shadow / Assisted Only)** vs **Empirical Autonomous Approval (`G8 = EVALUATED_PASSED`)**. In `VerdictTriageAgent`, if the rule's active policy lacks `EVALUATED_PASSED` G8 certification (or `autonomous_operation_eligible`), restrict execution to analyst-advisory (`REQUIRES_ATTENTION` cap or shadow tag / explicit admin override audit), or disallow decisive auto-verdicts until G8 passes.
- **Acceptance Criteria:**
  - Approving a policy with `G8 = INSUFFICIENT_DATA` records `autonomous_operation_eligible=False` cleanly.
  - `VerdictTriageAgent` unit tests verify decisive live verdicts are blocked/held for review when `autonomous_operation_eligible=False` unless explicit shadow/override mode is configured.

---

### Work Package 2 (`P1` / `AIS-F01` & `AIS-F08`): Fix AIS Historical Incident Retrieval & Rule Matching
- **Affected Files & Functions:**
  - `backend/app/services/policy_simulation_service.py`: `run_dry_run_intelligence_evaluation` (`lines 276-325`) & `evaluate_candidate_policy` (`lines 1084-1090`)
  - `backend/app/services/prompt_studio_service.py`: lines `99, 189, 256, 402, 657, 691`
  - `backend/app/api/rules.py`: `list_rules` (`lines 30-38`)
  - `backend/app/services/rule_parser.py`: `DetectionContextEngine.parse_rule_text` (`lines 112-115`)
- **Current Behavior:** AIS queries global top-50 unrelated rows (`scanned_q`) plus `Incident.rule_id.in_(rule_ids)` (`matched_q`, capped at 50, ignoring `event_type`). `AgentPolicyEngine` mixes `Rule.id` and `Rule.rule_id`; `DetectionContextEngine` drops `"Pattern Conditions"`.
- **Expected Behavior:**
  1. When `rule_id` is supplied to `run_dry_run_intelligence_evaluation`, **remove `scanned_q` global pollution** and query ONLY target-rule incidents via `or_(Incident.rule_id.in_(rule_ids), Incident.event_type == matched_rule.event_type)`.
  2. Support pagination or bounded higher retrieval cap (e.g., `200–500` prioritized toward closed/ground-truth-bearing incidents when `sample_limit` defaults) rather than truncating at the 50 newest alerts.
  3. Standardize `or_(Rule.id == ..., Rule.rule_id == ..., Rule.event_type == ...)` across `AgentPolicyEngine`, `RuleMaturityService`, and `rules.list_rules`.
  4. Copy `sections["pattern conditions"]` into `data["pattern_logic"]` in `rule_parser.py:112-115`.
- **Acceptance Criteria:**
  - Running simulation on a rule with 2 matching incidents reports `total_scanned = 2`, `rule_matched = 2`, `RULE_MISMATCH = 0`.
  - Unlinked incidents (`rule_id IS NULL`) matching `Rule.event_type` are captured without merging distinct rules (`PH_RULE_HEAVY_TCP_HOST_SCAN` stays isolated from `_ON_FIXED_PORT`).

---

### Work Package 3 (`P1` / `AIS-F02` & `AIS-F09`): Enable Live LLM Simulation & Restore Live-Simulation Parity
- **Affected Files & Functions:**
  - `backend/app/services/policy_simulation_service.py`: `run_dry_run_intelligence_evaluation` (`lines 581-710`), `_simulate_model_output` (`:937-1045`), `evaluate_candidate_policy` (`:1048-1091`)
  - `backend/app/api/prompts.py`: `evaluate_policy_simulation` (`:518-561`)
  - `frontend/src/app/agent-intelligence-studio/page.tsx` & `verdict-intelligence/page.tsx`: pass explicit `provider_type`
- **Current Behavior:** `evaluate_candidate_policy` always executes `_simulate_model_output` (`SIMULATED`), which lacks `NETWORK_SCAN` rules and abstains at 50%. Even with `OPENAI_COMPATIBLE`, G8 bypasses `EvidencePreflightValidator`, RAG, `TokenBudgetService`, `IndependentVerdictValidator`, and `RuleIntelligenceSnapshot` lookup, AND still evaluates excluded `RULE_MATCHED` rows.
- **Expected Behavior:**
  1. Expose explicit `provider_type` (`"OPENAI_COMPATIBLE"` default when Server 2 is online, `"SIMULATED"` strictly labeled mock/offline-only) in AIS `evaluate-simulation` API & UI, executing async via Celery `simulation_replay` queue for large batches.
  2. Route simulation through the same compiled pipeline (`PolicyCompilerService` + `EvidencePreflightValidator` + `TokenBudgetService` + `IndependentVerdictValidator` + `RuleIntelligenceSnapshot`) as `VerdictTriageAgent` (`ai_verdict_service.py`), recording `execution_provenance`.
  3. Add `if exclusion_reason: continue` (and `Investigation.is_disputed` check matching `HistoricalEligibilityService:185`) so excluded rows are neither fed to the LLM nor counted in `evaluated_cases`.
  4. Never allow `"SIMULATED"` runs to satisfy empirical G8 `EVALUATED_PASSED` certification (`PolicyQualityValidator._evaluate_gate_8_simulation` must verify real model provenance).
- **Acceptance Criteria:**
  - Simulation on `PH_RULE_HEAVY_TCP_HOST_SCAN` with online LLM uses real Qwen inference; `is_simulated=True` runs never grant empirical G8 `15/15` pass.
  - `evaluated_cases <= eligible` (zero excluded incidents sent to model inference).

---

### Work Package 4 (`P1` / `AIS-F04`): Fix Ground Truth ML Word-Boundary & Human Override Logic
- **Affected Files & Functions:**
  - `backend/app/services/ingestion_service.py`: `_ingest_single_incident_dict` (`lines 636-643`)
  - `backend/app/services/fortisiem_service.py`: `extract_ground_truth_data` (`lines 1142-1147`)
  - `backend/app/services/historical_ground_truth_validator.py`: `_is_automated_resolution_text` (`lines 81-101`)
- **Current Behavior:** `"ml" in comments.lower()` / `"ML" in comments` false-triggers on substrings (`normal`, `html`, `xml`, `similar`), and `"Resolution set by Machine Learning"` overrides incidents with real human `cleared_user` (`e.g. "Yash Mungekar"`, `"shivamw"`) or substantive human rationale in `cleared_reason`.
- **Expected Behavior:**
  1. Replace substring `"ml"` check with strict word-boundary regex `re.search(r"\bml\b", ...)` plus exact phrases (`"resolution set by machine learning"`, `"machine learning"`).
  2. When `"Resolution set by Machine Learning"` co-occurs with explicit human `cleared_user` (non-system/non-empty) **or** distinct non-boilerplate human rationale in `cleared_reason` / additional comment lines, treat as human-verified (or `HUMAN_REVIEWED_AFTER_ML`) rather than silently discarding.
  3. Add read-only data-reconciliation report / backfill migration to re-evaluate existing `is_ml_generated = 1` rows in PostgreSQL.
- **Acceptance Criteria:**
  - Unit tests confirm `"Normal maintenance confirmed"` sets `is_ml_generated = False`.
  - Incidents like `132501348` (`cleared_user="Yash Mungekar"`) and `132461358` (`cleared_user="shivamw"`, `cleared_reason="hash value is clean"`) qualify as verified ground truth while pure ML-only closures stay excluded.

---

### Work Package 5 (`P2` / `AIS-F05`, `AIS-F06`, `AIS-F07`, `AIS-F10`): Scoring Math, Export Fields & `NETWORK_SCAN` Telemetry
- **Affected Files & Functions:**
  - `backend/app/services/policy_quality_validator.py`: lines `47-52, 95, 114, 240-248`, `detection_archetype_registry.py:691`
  - `backend/app/schemas/policy_quality.py` & `frontend/src/lib/qualityExport.ts:170`
  - `backend/app/services/evidence_normalization_service.py:58-59, 241-249, 303` & `evidence_sufficiency_engine.py:165-190`
  - `backend/app/services/evidence_contract_service.py:83`
- **Current Behavior:** G1 (`20`) + G2 (`20`) double-count `detection_semantics` (`max 20`), producing `85` vs `105` structural denominators; `qualityExport.ts:170` outputs `validation_status: null`; `FIELD_MAPPINGS` omits `"Destination Port"`/`"dstPort"`/`"destinationPort"`; `EvidenceContractService` ignores `RuleIntelligenceSnapshot`.
- **Expected Behavior:**
  1. Split weights explicitly (`G1=10`, `G2=10`, `G3=20`, `G4=10`, `G5=10`, `G6=15`, `G7=10`, sum=`85` + `G8=15` = **`100`**) so G1–G7 card `max_score` sum equals `85` (zero double-counting), OR display a clearly normalized `100`-pt structural denominator matching breakdown weights.
  2. Map `validation_status` cleanly (e.g., deprecate or map from `empirical_validation_status` in `qualityExport.ts:170`).
  3. Add `"destination port"`, `"destination_port"`, `"destinationport"`, `"dstport"`, `"dst_port"`, `"dest_port"` aliases to both `FIELD_MAPPINGS` and `EvidenceSufficiencyEngine._match_field`, include `"port"` in fallback heuristic (`line 303`), and extract `rawEvents` even when `"attributes"` exists.
  4. Respect `RuleIntelligenceSnapshot` inside `EvidenceContractService.get_contract_for_rule` (`lines 82-96`) and fix `"PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT"` typo at `detection_archetype_registry.py:691`.
  5. In AI Triage Workbench (`frontend/src/app/ai-triage-workbench/page.tsx`), display rule ID chips alongside search hits and allow one-click exact `rule_id` filtering from search results so users immediately distinguish `PH_RULE_HEAVY_TCP_HOST_SCAN` from `_ON_FIXED_PORT`.
- **Acceptance Criteria:**
  - `sum(G1..G8.max_score) == 100.0` (matches `score_breakdown` sum).
  - JSON export contains non-null `validation_status` / consistent `empirical_validation_status`.
  - FortiSIEM `"Destination Port"` events map to `network.destination_port` and pass `NETWORK_SCAN` sufficiency.

---

### Work Package 6 (`P3` / `AIS-F11`, `AIS-F12`, `AIS-F13`): Consolidation, Config Hygiene & Live DB Audit
- **Affected Files & Targets:**
  - `dry_run_service.py` / `maturity_service.py` vs `policy_simulation_service.py`
  - `backend/app/services/llm_config_service.py` (clean `.env` upserts) & `backend/.env` hygiene
  - Live PostgreSQL read-only diagnostic run
- **Expected Behavior:**
  1. Deprecate or unify legacy `ValidationEngine`/`RuleMaturityService` into `PolicySimulationService` / `HistoricalEvaluationRunRecord` so one canonical evaluation ledger drives AIS G8, calibration, and maturity.
  2. Run the read-only SQL diagnostics from `AIS_INCIDENT_RETRIEVAL_AUDIT.md`, `AIS_RULE_MAPPING_AUDIT.md`, and `AIS_GROUND_TRUTH_AUDIT.md` on the live PostgreSQL server to capture exact counts for the 34 rules and 2,900+ incidents.
  3. Fix `llm_config_service.py` in-place `.env` updating to replace existing keys without appending repeated `# Local LLM Server 2...` blocks, and enforce `LOCAL_LLM_ALLOW_MOCK_FALLBACK=false` and `FORTISIEM_MOCK_FALLBACK=false` in staging/production `.env`.

