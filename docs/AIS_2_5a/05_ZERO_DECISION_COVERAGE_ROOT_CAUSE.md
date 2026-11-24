# 05 — Zero Decision-Coverage Root Cause Investigation

## 1. Problem Statement

AIS 2.5 reported:
- 20 historical incidents evaluated
- 0 final accepted TP verdicts
- 0 final accepted FP verdicts
- 20 `REQUIRES_ATTENTION` verdicts
- **0.0% Decisive Coverage**

---

## 2. Rejection Taxonomy & Forensic Breakdown

Every raw proposal across the 20 benchmark incidents was forensically analyzed. Rejections stemmed from three distinct, verifiable root causes:

### Root Cause 1: Ungrounded Malicious Predicates on Dual-Use Binaries (4 incidents)
- **Incidents**: `132439932`, `132461358`, `132472498`, `132527297`
- **Model Proposal**: `TRUE_POSITIVE` (Confidence: 85%)
- **Model Claims**: Asserted active malware compromise, unauthorized lateral movement, or malicious command execution.
- **Observed Telemetry**: Execution of `UltraViewer_Desktop.exe` from standard program directories. No command line arguments, no external C2 IP connection, no temp directory persistence, no credential dumping observed.
- **Validator Action**: `REJECTED` by `IndependentVerdictValidator` (`UNSUPPORTED_PREDICATE`, `UNSUPPORTED_CLAIM`, `TP_CRITERIA_UNSATISFIED`).
- **Verdict**: The validator correctly protected the SOC from hallucinated True Positives on dual-use administrative tools.

### Root Cause 2: Model Voluntary Abstention (6 incidents)
- **Incidents**: `132438483`, `132441815`, `132461368`, `132474210`, `132501348`, `132502453`
- **Model Proposal**: `REQUIRES_ATTENTION` (Confidence: 50% – 60%)
- **Reasoning**: The model correctly recognized that parent process lineage and enterprise ITSM change tickets were missing from the telemetry, preventing definitive TP or FP determination.
- **Validator Action**: `VALIDATED`. Model abstention was accepted as sound.

### Root Cause 3: Hardware Context Window Exceedance on Prisma SASE (10 incidents)
- **Incidents**: `132499009` through `132599330`
- **Model Proposal**: `None` (Intercepted prior to dispatch)
- **Reasoning**: System prompt + incident payload totaled 3,549 to 3,747 tokens, exceeding Server 2 vLLM's 3,328 input budget.
- **Validator Action**: `CONTEXT_WINDOW_EXCEEDED` preflight abstention enforced by `TokenBudgetService`.
- **Verdict**: Legitimate architectural halt preventing out-of-memory or model truncation failure on Server 2.

### Summary
The 0% decisive coverage in natural historical telemetry was **not** a validator bug—it was the combined result of:
1. Strict, correct rejection of unsupported True Positives on uncorroborated dual-use software.
2. Honest model abstention on sparse telemetry.
3. Physical context limits on Server 2 vLLM.
