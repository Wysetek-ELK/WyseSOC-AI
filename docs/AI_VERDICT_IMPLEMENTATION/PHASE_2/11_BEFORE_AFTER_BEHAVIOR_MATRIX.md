# AI VERDICT — PHASE 2: BEFORE/AFTER BEHAVIOR MATRIX
## 11. BEFORE/AFTER BEHAVIOR MATRIX

---

### 1. Architectural & Operational Comparison

| System Capability | Before Phase 2 (LLM Authority) | After Phase 2 (Evidence-Grounded Validator) |
|---|---|---|
| **Final Verdict Authority** | The Local LLM was the sole decider. If LLM returned `TRUE_POSITIVE`, that was stored and shown directly. | **Independent Verdict Validator** is the authoritative decider. LLM proposal is checked against real telemetry and policy contracts. |
| **Evidence Normalization** | Telemetry was forwarded as unstructured raw event dictionaries or key-value attributes. | Deterministically normalized into `CanonicalEvidenceRecord` objects with uniform dot-notation and SHA-256 integrity digests. |
| **Telemetry Completeness** | Missing critical telemetry (e.g. absent command line) was ignored; LLM guessed or assumed benignity. | Preflight validator detects missing critical telemetry and **abstains immediately**, routing to `REQUIRES_ATTENTION`. |
| **Hallucination Protection** | Zero protection. If the model fabricated external C2 IPs, nonexistent hashes, or binaries, the verdict was accepted. | Model claims are grounded against canonical records. Any fabricated entity triggers `CLAIM_NOT_VERIFIABLE` and forces `REQUIRES_ATTENTION`. |
| **Contradiction Detection** | None. Model could claim "Russian C2 beaconing" over loopback `127.0.0.1` and be accepted. | Preflight and validator cross-check source/dest IPs and process lineage. Contradictory claims trigger `EVIDENCE_CONTRADICTION` override. |
| **Detection Rule Contracts** | Rules had free-form text prompts with no machine-enforceable evidence requirements. | Machine-verifiable `RuleEvidenceContract` specifies mandatory fields, critical flags, and TP/FP criteria for 5 archetypes. |
| **Policy Approval Gating** | Unapproved prompt drafts in Agent Intelligence Studio could influence verdicts in non-prod. | An unapproved prompt draft yields an `UNVERIFIED` contract, forcing immediate deterministic abstention in all evaluation modes. |
| **Confidence Semantics** | Raw LLM score was presented as empirical verdict certainty (e.g. *"Confidence: 98%"*). | Raw score labeled as `Raw LLM Score (Uncalibrated)`. Effective confidence safely zeroed to `0%` whenever validation abstains. |
| **Forensic Audit & Replay** | No way to reproduce or verify why a verdict was reached or detect evidence tampering. | Cryptographic replay signature (`SHA-256[:16]`) and deterministic replay engine (`replay_validation`) detect any tampering. |
| **SOC Analyst UI Experience** | Plain verdict badge and raw explanation text. | Bifurcated verdict card (Proposed vs Authoritative), safety override alerts, completeness meter, grounding ratio, and analyst action directives. |
| **Token Consumption Efficiency** | Incomplete incidents still executed full LLM inference, burning tokens on unresolvable events. | Preflight gate short-circuits before LLM call when critical evidence is absent, consuming **0 tokens**. |

---

### 2. Behavioral Scenarios Walkthrough

#### Scenario A: Highly Confident Model with Missing Command Line
- **Before Phase 2:** Model receives process `powershell.exe` with no `cmdline`. Model guesses it is benign administrative traffic, outputs `FALSE_POSITIVE` (Confidence: 92%). SOC closes incident automatically.
- **After Phase 2:** Preflight validator evaluates `PROCESS_EXECUTION` contract. `process.command_line` is marked `critical=True` and is absent. Preflight halts inference immediately. Authoritative verdict set to `REQUIRES_ATTENTION` (Confidence: 0%, Reason: `CRITICAL_TELEMETRY_MISSING`). Zero tokens consumed. Analyst alerted to collect command line telemetry.

#### Scenario B: Hallucinated C2 IP Address
- **Before Phase 2:** Model claims incident is `TRUE_POSITIVE` citing connection to `203.0.113.199`. Incident only contains internal traffic. Verdict accepted and escalated to IR team on false grounds.
- **After Phase 2:** Model proposed `TRUE_POSITIVE`. `ModelClaimExtractor` scans telemetry for `203.0.113.199`, finds zero occurrences, flags `CLAIM_NOT_VERIFIABLE`. Validator executes Check 3, overrides model to `REQUIRES_ATTENTION`, zeroes confidence, and renders an alert in the UI showing the hallucinated claim.

