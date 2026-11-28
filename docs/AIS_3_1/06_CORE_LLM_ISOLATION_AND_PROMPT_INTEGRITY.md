# AIS 3.1 — Workstream 6: Core LLM Isolation & Prompt Integrity

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`

---

## 1. Strict Input Allowlist & Leakage Prevention

Verified in `backend/app/services/ais31_benchmark_service.py` (`_prepare_incident_wire_payload`):

- **Allowed Inputs Built Into Wire Payload:**
  1. Original SIEM incident metadata (`incidentId`, `title`, `severity`, `category`, `reportingDevice`, `reportingIp`, `eventType`, epochs).
  2. Original raw SIEM events (`eventId`, `eventType`, `receiveTime`, `rawMessage`, `attribute`, passed through `build_model_facing_payload`).
  3. Triggered FortiSIEM detection rule specification constructed deterministically via `RuleDefinitionBuilder.build_complete_rule_spec` (rule ID, description, conditions, aggregation, parsed raw schema fields).
  4. Canonical normalized records (`EvidenceNormalizationService`) and derived factual enrichments (`EvidenceIntelligenceEngine.enrich_incident_evidence`).
  5. Frozen neutral SOC evaluation directive + structured JSON schema (`FROZEN_NEUTRAL_SYSTEM_PROMPT`).
- **Strictly Excluded From Inference Query & Payload:**
  - `AnalystVerdictReview` table (never queried during inference preparation or GPU dispatch).
  - `HistoricalGroundTruth` table and any nested `ground_truth`/`resolution`/`cleared_user` fields (explicitly stripped twice via `HistoricalGroundTruthValidator.sanitize_incident_for_inference`).
  - `LearningRecord` / `VerifiedSemanticRetrievalService` (`rag_block=""`, `rag_excluded=True`, `memory_excluded=True`).
  - Operational `Incident.ai_verdict` / `ai_reasoning` / `ai_confidence` (never serialized into benchmark payload).

---

## 2. Prompt Injection & Untrusted Evidence Boundaries

- Raw FortiSIEM logs (`rawMessage`), event attributes, and rule descriptions are serialized inside structured JSON evidence payloads beneath `NEUTRAL_SOC_BASELINE_V2` instruction boundaries and strictly delimited from system directives.
- `test_structured_output_and_injection.py` and `test_ais_3_1_holdout_benchmark.py` verify that embedded injection strings or fake ground-truth markers in raw logs do not override verdict parsing or leak labels.

---

## 3. Raw LLM vs. Final Validated Application Separation

To ensure transparent empirical measurement without masking LLM capability behind deterministic overrides:

- **Raw LLM Verdict (`raw_llm_verdict`):** Parsed directly from vLLM response (`AIS27BenchmarkRunner._parse_raw_vllm_reply`) BEFORE any validator rules run (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ATTENTION`, or `None` if invalid/truncated).
- **Deterministic Post-Processing (`ModelClaimExtractor` + `IndependentVerdictValidator`):** Preserved completely unmodified (per Workstream 4.1 safety constraint). Never flips a verdict from `FALSE_POSITIVE -> TRUE_POSITIVE` or vice versa; it only accepts the raw verdict (`ACCEPTED`), preserves abstention (`ABSTENTION_PRESERVED`), or demotes an ungrounded/unsatisfied verdict to `REQUIRES_ATTENTION` (`OVERRULED_TO_ABSTAIN`).
- **Known Validator Scope Consideration:** Because `IndependentVerdictValidator` contains rule-specific TP/FP criteria tailored to earlier CrowdStrike and Prisma SASE rules, some generic FortiSIEM rules in the 30-rule holdout may trigger conservative validator abstention. Capturing and reporting **both** `Raw LLM` and `Validated Application` metrics cleanly separates model classification performance from deterministic safety validator behavior.
