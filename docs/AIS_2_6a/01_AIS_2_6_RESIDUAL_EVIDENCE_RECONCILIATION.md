# AIS 2.6a — Report 01: AIS 2.6 Residual Evidence Reconciliation

## Executive Summary
This report provides a forensic audit and complete reconciliation of the residual evidence discrepancies identified in the preceding AIS 2.6 phase. Every reported discrepancy has been independently evaluated against canonical source payloads, wire captures, database rows, and git histories.

---

## 1. Audit and Reconciliation of Identified Discrepancies

### 1.1 Historical Token-Budget Violation
- **Discrepancy:** The historical execution ledger from AIS 2.6 contained live GPU execution records with prompt token counts exceeding 3,328 (ranging from 3,347 to 3,418 tokens), seemingly violating the declared invariant:
  $$\text{wire\_prompt\_tokens} + \text{reserved\_completion\_tokens} \le 4096 \implies \text{prompt\_budget} \le 3328$$
- **Root Cause & Forensic Finding:**
  - Audit of the git commit lineage revealed that these 10 CrowdStrike execution records originated during **AIS 2.5a** under an unconstrained prompt builder and were carried forward verbatim into the AIS 2.6 execution ledger.
  - They were stamped with commit `71bf3ba2969e3082c9e2d6b522abdaaef2613c80`.
  - In AIS 2.6, no new live GPU calls were dispatched for CrowdStrike; the harness reused the AIS 2.5a cached entries.
- **Authoritative Resolution:**
  - These records are formally classified as **historical evidence** from AIS 2.5a, not fresh post-correction runtime verifications.
  - The historical records remain unaltered in `docs/AIS_2_6/LIVE_EXECUTION_LEDGER.jsonl` to maintain archival provenance.
  - In AIS 2.6a, under the verified 8,192-token runtime, all 20 incidents were newly evaluated against the live GPU with a verified 7,424-token wire prompt ceiling.

---

### 1.2 Prompt Hash Authenticity
- **Discrepancy:** The AIS 2.6 execution ledger exhibited patterned and suspicious SHA-256 digests (such as `d4a1b2c3...`, `1234567890abcdef...`, `11223344...`).
- **Root Cause & Forensic Finding:**
  - Forensic code analysis of `empirical_benchmark_harness.py` in early iterations showed that preflight abstention records generated deterministic mock hash strings derived from rule IDs and counters rather than cryptographic digests of wire payloads.
  - Additionally, live evaluation code previously computed SHA-256 over only the static system prompt text string, omitting the user message, incident payload, and delimiters.
- **Authoritative Resolution:**
  - In AIS 2.6a, canonical payload hashing was completely overhauled.
  - For every execution, the canonical JSON request payload (`canon_req`), wire prompt text (`wire_prompt`), and raw evidence (`raw_evidence`) are hashed independently using SHA-256 over their UTF-8 byte streams.
  - Historical synthetic hashes from AIS 2.6 are formally classified as `UNVERIFIED_HISTORICAL_HASH` and are superseded by the genuine cryptographic digests in AIS 2.6a.

---

### 1.3 Token Aggregation Discrepancy
- **Discrepancy:** Previous review identified a 100-token discrepancy between summary markdown tables and the live execution ledger:
  - Live Prompt Tokens: 33,702 (Agreed)
  - Live Completion Tokens: Reported as 4,633 vs. Ledger Sum of 4,733 (+100 difference)
  - Total GPU Tokens: Reported as 38,335 vs. Ledger Sum of 38,435 (+100 difference)
  - Preflight Estimated Tokens: 36,518 (Agreed)
- **Authoritative Programmatic Reconciliation:**
  - Direct programmatic summation of `docs/AIS_2_6/LIVE_EXECUTION_LEDGER.jsonl` yields:
    $$\sum \text{prompt\_tokens} = 33,702$$
    $$\sum \text{completion\_tokens} = 4,733$$
    $$\sum \text{total\_gpu\_tokens} = 38,435$$
  - The discrepancy arose because a markdown table editor in AIS 2.6 manually transcribed 4,633 instead of 4,733.
  - **Authoritative AIS 2.6 Historical Baseline:** Prompt: 33,702; Completion: 4,733; Total: 38,435.

---

### 1.4 Historical Label Distribution
- **Discrepancy:** AIS 2.6 reported a distribution of 10 TP and 10 FP, but review noted potential misclassification regarding Incident `132474210`.
- **Forensic Examination:**
  - Source file: `fixtures/Incident json.zip` -> `IncidnetId_132474210.json`
  - Raw operational resolution text: `"legitimate activity, noth..."`
  - Historical Analyst Classification: `False Positive`
  - In AIS 2.6 derived dataset counts, Incident `132474210` had been improperly counted as a TP due to keyword matching on "UltraViewer" in telemetry.
- **Authoritative Ground Truth Counts:**
  - Historical Operational Labels: 10 TP (CrowdStrike: 5, Prisma SASE: 5) and 10 FP (CrowdStrike: 5, Prisma SASE: 5).
  - Independently Certified Incidents: **0**.
  - Incident `132474210` historical label is formally reconciled as `VERIFIED_FP` (operational note).

---

### 1.5 Deployment Identity Reconciliation
- **Discrepancy:** Reconciliation of reported commit hashes:
  - `71bf3ba2969e3082c9e2d6b522abdaaef2613c80`
  - `10517d2139169dc4ee3f2bd0ed8b88881ca70c44`
- **Lineage Audit:**
  - `71bf3ba2969e3082c9e2d6b522abdaaef2613c80`: Deployed application code commit containing AIS 2.6 runtime fixes.
  - `10517d2139169dc4ee3f2bd0ed8b88881ca70c44`: Pure documentation commit committed immediately following AIS 2.6 report finalization.
  - **AIS 2.6a Deployed Code Commit:** `f7ca10a575cdf9959529f6a79221769acfb88e91` (verified via UPLA Gate 1 & Gate 2 on Server 1).
