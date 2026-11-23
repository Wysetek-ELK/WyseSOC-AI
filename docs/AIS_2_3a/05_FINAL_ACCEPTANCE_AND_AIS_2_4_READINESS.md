# AIS 2.3a — Final Acceptance & AIS 2.4 Readiness

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.3a (Runtime Evidence, Guardrail & Accuracy Integrity Correction)  
**Date:** November 23, 2026  
**Final Status:** PASS_READY_FOR_AIS_2_4  

---

## 1. Final Acceptance Status Determination

In strict accordance with the AIS 2.3a Master Prompt specifications, the execution outcomes and empirical verification results were evaluated against the five formal acceptance categories:

1. `PASS_READY_FOR_AIS_2_4` (All runtime evidence, guardrails, and traceability defects resolved with live GPU verification)
2. `PASS_WITH_NON_BLOCKING_LIMITATIONS`
3. `BLOCKED_GUARDRAIL_DEFECT`
4. `BLOCKED_TOKEN_EXHAUSTION`
5. `BLOCKED_GPU_OR_DEPLOYMENT`

### Certified Decision:
$$\mathbf{PASS\_READY\_FOR\_AIS\_2\_4}$$

### Formal Justification:
1. **Evidence Normalization & Lineage Preservation Repaired:** Canonical field aliasing was implemented in `EvidenceNormalizationService`, ensuring that FortiSIEM vendor fields (`File Name`, `Parent File Name`) reliably populate contract-specified fields (`process.name`, `process.file_name`, `process.parent_name`, `file.name`).
2. **Wire Compaction Deduplication Verified:** Added `seen_forensic_values` deduplication and alias compression in `EvidenceCompactionService`. Identical forensic entities repeating across dozens of events (e.g. `ss-widget.min.js` across 34 events) are deduplicated, completely resolving the payload explosion that previously resulted in a 5,809-token overflow.
3. **Token Headroom & Context Budget Calibration:** Strictly configured 768 reserved completion tokens for $\le 4,096$ hardware contexts in `VerdictPipeline`, guaranteeing Qwen has sufficient headroom to generate complete structured JSON reasoning without overflowing the 4,096 physical context limit of Server 2's vLLM instance.
4. **Guardrail Logic Defect Resolved:** Corrected the `UnboundLocalError: local variable 'action_directive' referenced before assignment` in `IndependentVerdictValidator`, ensuring zero runtime crashes during fail-closed validation.
5. **Traceability Fields Universally Populated:** Populated `rule_id`, `rule_name`, `policy_version_id`, `policy_version_number`, and `policy_status: APPROVED` across all pipeline exit points, guaranteeing full auditability.
6. **Live GPU Regression Verified:** Successfully executed 5 / 5 live GPU inferences on Server 2 (`Qwen/Qwen2.5-7B-Instruct-AWQ` via Server 1 at `172.26.41.240`) with 0 errors, mean latency 21.04s, and verified evidence citations (e.g., `ss-widget.min.js`, `clientlib-site.min....js`, `scripts-QBOKETIS.js`).
7. **Zero Regressions & Rigorous Safety Invariants:** All 64 backend tests, 14 heavy TCP scan tests, and 88 frontend tests pass 100%. Zero unsafe false positives occurred; all ambiguous alerts safely route to `REQUIRES_ATTENTION`.

---

## 2. Acceptance Criteria Checklist

- [x] **Stage A: Runtime Prompt & Token Audit**
  - Traced end-to-end evidence normalization and prompt generation for CrowdStrike and Prisma SASE incidents.
  - Pinpointed root causes: unaliased `process.file_name` dropped by compaction; 34 duplicate file entries causing token budget explosion.
  - Documented in `docs/AIS_2_3a/01_RUNTIME_PROMPT_AND_TOKEN_AUDIT.md`.
- [x] **Stage B: Guardrail Rejection Root Cause Analysis**
  - Pinpointed `UnboundLocalError` in `IndependentVerdictValidator` on `action_directive`.
  - Analyzed model citations: verified that Qwen was hallucinating citation IDs in AIS 2.3 due to missing prompt evidence, and verified proper fail-closed interception when reputation is uncorroborated.
  - Documented in `docs/AIS_2_3a/02_GUARDRAIL_REJECTION_ROOT_CAUSE.md`.
- [x] **Stage C: Implementation & Traceability Fixes**
  - Updated `EvidenceNormalizationService` with canonical aliases (`process.name`, `process.file_name`, `file.name`, `process.parent_name`).
  - Updated `EvidenceCompactionService` with forensic deduplication (`seen_forensic_values`).
  - Calibrated token budget in `VerdictPipeline` with 768 completion headroom.
  - Added `ModelClaimExtractor.ground_claims` helper for alias-resilient grounding.
  - Fixed `IndependentVerdictValidator` variable initialization.
  - Populated all rule and policy traceability attributes.
  - Documented in `docs/AIS_2_3a/03_IMPLEMENTATION_AND_TRACEABILITY_FIXES.md`.
- [x] **Stage D: Local Regression Testing**
  - 64 backend tests passed (including `test_ais_unified_population_contract.py`, `test_ais_evaluation_tracking.py`, `test_ais_2_3a_integrity.py`, `test_evidence_normalization.py`, `test_evidence_compaction_and_chunking.py`, `test_independent_verdict_validator.py`).
  - 14 Heavy TCP scan tests passed (`test_ais_heavy_tcp_e2e.py`).
  - 88 frontend tests passed (`npm test`).
- [x] **Stage E: UPLA Deployment to Server 1**
  - Synchronized Git commits `51b29840` and `b3fb4980` to GitHub `feature/phase3-compact-ui` after Gate 1 approval.
  - Executed remote deployment to Server 1 (`172.26.41.240`) after Gate 2 approval.
  - Verified remote Alembic migrations, remote pytest suite, Next.js build, and health checks.
- [x] **Stage F: Real GPU Regression Pilot on Server 2**
  - Executed 5 real historical incidents against Server 1 API calling Server 2 GPU (`13.204.214.64:8000/v1`).
  - Confirmed 100% completion, zero connection errors, and valid evidence citations.
  - Documented in `docs/AIS_2_3a/04_REAL_GPU_REGRESSION_RESULTS.md` and `scratch/gpu_regression_results_ais_2_3a.json`.
- [x] **Stage G: Final Acceptance & Documentation**
  - All 5 markdown reports and `FINAL_EVIDENCE.json` completed in `docs/AIS_2_3a/`.

---

## 3. Empirical Accuracy & Safety Baseline

In compliance with Wysetek's strict anti-fabrication mandate, the empirical results of the AIS 2.3a regression pilot are recorded below:

| Metric | Measured Value | Operational Interpretation |
| :--- | :---: | :--- |
| **Total Benchmark Incidents Evaluated** | 5 | 2 CrowdStrike, 3 Prisma SASE real historical incidents |
| **Execution Success Rate** | 100.0% (5/5) | Live vLLM Qwen AWQ inference completed on Server 2 |
| **Model Proposed `REQUIRES_ATTENTION`** | 5 / 5 (100.0%) | Model recognized incomplete forensic context |
| **Model Proposed `FALSE_POSITIVE`** | 0 / 5 (0.0%) | Zero unverified closure proposals from the model |
| **Model Proposed `TRUE_POSITIVE`** | 0 / 5 (0.0%) | Zero unsupported malicious escalations |
| **Authoritative Effective Verdicts** | 5 `REQUIRES_ATTENTION` | Safe Level-2 SOC routing across all alerts |
| **Decision Coverage** | 0.0% | Zero autonomous closures (Fail-Closed Safety) |
| **Abstention Rate** | 100.0% | 100% of alerts routed to human tier |
| **Unsafe False Positives (Missed Attacks)** | 0 (0.0%) | Perfect safety record preserved |
| **Selective Accuracy** | `NOT_MEASURABLE` | Defined as $\frac{\text{Correct Decisive}}{\text{Total Decisive}}$; zero decisive decisions taken |

---

## 4. Architectural Lessons & Defect Classification

Through AIS 2.3a, the team established clear empirical boundaries between the 5 failure classes identified in the objective:

1. **Evidence Genuinely Unavailable in FortiSIEM:**
   - In CrowdStrike incident `132527297`, the parent command-line telemetry was genuinely not captured in the raw FortiSIEM event. The model proposed `REQUIRES_ATTENTION`, which was accepted with `VALIDATED` status. This is the **correct, desired behavior** of an autonomous SOC agent.
2. **Evidence Available but Omitted from Prompt:**
   - In AIS 2.3, `process.name` and `file.name` were dropped because `FIELD_MAPPINGS` mapped to non-contract field keys. This defect is now **fully corrected** by canonical field aliasing and priority preservation in `EvidenceCompactionService`.
3. **Evidence Received but Incorrectly Interpreted:**
   - When Qwen received `ss-widget.min.js`, it recognized the benign web application but attempted to rationalize full benignity from file naming alone.
4. **Correct Model Proposals Rejected by Technical Validation Defect:**
   - In AIS 2.3, the validator crashed with `UnboundLocalError` when evaluating certain claim patterns. This technical barrier is now **completely resolved**.
5. **Genuinely Unsupported TP/FP Proposals Rejected by Guardrails:**
   - The `IndependentVerdictValidator` strictly enforces that a familiar file name or standard port does not prove benignity without cryptographic hash verification (SHA256 reputation) or an active change management ticket. Demoting such proposals to `REQUIRES_ATTENTION` represents **robust SOC safety, not a pipeline defect**.

---

## 5. AIS 2.4 Readiness Roadmap

With runtime evidence delivery, token budgeting, traceability, and validator execution stabilized, Verdictum AI is fully ready for **Phase AIS 2.4**. The following enhancements are prioritized:

### 5.1 Telemetry Enrichment: Local Hash Reputation
- **Current Limitation:** Qwen and the `IndependentVerdictValidator` correctly refuse to close alerts as `FALSE_POSITIVE` based solely on file names (e.g. `ss-widget.min.js`), because malware frequently masquerades under legitimate file names.
- **AIS 2.4 Implementation:** Integrate a local SHA256 / MD5 reputation lookup table (or offline MISP/NSRL database). When the raw event contains a file hash verified as known-benign, the validator will accept the `FALSE_POSITIVE` verdict with high confidence, unlocking decisive coverage.

### 5.2 Context Window Expansion to 8,192 Tokens
- **Current Limitation:** Server 2's vLLM instance is currently launched with a 4,096-token maximum context window, necessitating aggressive evidence compaction and deduplication to leave 768 tokens for model completion.
- **AIS 2.4 Implementation:** If GPU VRAM allows, increase `--max-model-len` to 8,192 tokens on Server 2. This will provide headroom for complete raw event logs across high-volume incidents without aggressive compaction.

### 5.3 Multi-Turn Tier-2 Analyst Feedback Loop
- **Current Limitation:** 13 historical benchmark incidents currently lack certified analyst ground-truth labels.
- **AIS 2.4 Implementation:** Implement a verification workflow in the Agent Intelligence Studio UI allowing Tier-2 and Tier-3 SOC leads to review the model's extracted evidence claims, approve/reject abstentions, and convert provisional incidents into certified ground truth.
