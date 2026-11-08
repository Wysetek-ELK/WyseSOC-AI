# 01. EXISTING ARCHITECTURE REVIEW (PHASES 0–4)

## Baseline Review & Evolution Context

Prior to the inception of Agent Intelligence Studio 2.0, the AI Verdict system completed a five-phase engineering lifecycle that established strict runtime safety, deterministic claim grounding, and asynchronous infrastructure:

### Summary of Completed Phases

1. **Phase 0: Audit Verification:**
   - Evaluated codebase fidelity against security baselines.
   - Identified mock services, untracked endpoints, and ungrounded decision paths.
2. **Phase 1: Critical Safety Controls:**
   - Implemented strict RBAC (`SOC_LEAD`, `ANALYST`) and audit event logging with SHA-256 HMAC integrity.
   - Enforced ground-truth isolation on blind triage review endpoints.
   - Neutralized simulated production fallbacks; established that production verdicts fail closed without live LLM inference.
   - Isolated external egress (`127.0.0.1` / local networks only).
3. **Phase 2: Evidence Grounding & Independent Verdict Verification:**
   - Created canonical evidence schemas (`CanonicalEvidenceItem`, `ClaimGroundingCheck`).
   - Implemented `IndependentVerdictValidator` evaluating evidence contract compliance, factual grounding, and confidence alignment.
   - Introduced deterministic abstention when mandatory telemetry fields are missing.
4. **Phase 3: Unified Policy Compiler, RAG & Evaluation:**
   - Unified prompt generation into `PolicyCompilerService` compiling 9-section structured prompts.
   - Added verified semantic RAG (`VerifiedRAGService`) with tenant isolation and strict exact-rule matching.
   - Created the Simulation Lab for dry-run backtesting on historical incidents.
5. **Phase 4: Production Hardening & Scalability:**
   - Integrated Celery task processing with Redis for background evaluations and ingestion.
   - Established PostgreSQL connection pooling, Alembic database migrations, and health observability.
   - Built the modern Next.js dashboard UI with interactive views.

---

## Architectural Gaps Identified in Studio 1.0

Despite the runtime grounding controls established in Phase 2 and 3, the upstream **Prompt Studio** retained structural deficiencies that compromised policy quality before compilation ever took place:

```text
+-------------------------------------------------------------------------+
|                        STUDIO 1.0 ARCHITECTURE                          |
|                                                                         |
|  [ SIEM Rule Metadata ]                                                 |
|          |                                                              |
|          v                                                              |
|  [ Generic Rule Parser ] ---------> [ Prompt Generator ]                |
|  (Conflates observed telemetry       (Applies static markdown template) |
|   with authoritative rules)                          |                  |
|                                                      v                  |
|                                          [ Raw 9-Section Policy ]       |
|                                          - Demands malware hashes for   |
|                                            network exfiltration rules.  |
|                                          - Blanket benign RFC-1918.     |
|                                          - Ungoverned manual edits.     |
|                                                      |                  |
|                                                      v                  |
|                                          [ SOC Lead Approval ]          |
|                                          (Analyst guesses safety;       |
|                                           no deterministic validation)  |
+-------------------------------------------------------------------------+
```

### Detailed Problem Breakdown

1. **Ungrounded Detection Semantics:**
   - In Studio 1.0, rules synchronized via FortiSIEM or CrowdStrike APIs only passed minimal fields (`rule_id`, `name`, `event_type`, `raw_payload`).
   - If an incident telemetry record included `{"sentBytes64": 2130499380}`, the system lacked semantics awareness to discern whether this was a configured alert threshold or an observed transfer volume during an incident.
2. **Archetype Contamination:**
   - The policy generator utilized a singular, monolithic prompt template. A medium-severity network rule like `PH_RULE_LARGE_OUTBOUND_XFER` received instructions to inspect parent process GUIDs, command-line arguments, executable hashes, and persistence registry keys.
3. **Flawed Common Baseline:**
   - The baseline text contained prescriptive instructions that actively degraded LLM verdict reliability:
     - *"Always maintain confidence between 85% and 95%."* (Violates empirical evidence grounding).
     - *"Classify internal RFC-1918 communication as False Positive."* (Enables lateral movement and internal exfiltration blindspots).
4. **Decoupled Evidence Contracts:**
   - Evidence Contracts were generated independently from prompt instructions. A prompt could require `network.flow.duration`, but the contract required only `source.ip`, creating a silent mismatch during runtime validation.
5. **Absence of Quality Gating Prior to Approval:**
   - A SOC Lead could approve a completely contradictory or ungrounded policy without the system running a single automated check.

---

## Technical Debt Resolved in AIS 2.0

AIS 2.0 addresses each of these gaps by creating a formal pipeline between raw SIEM definitions, behavioral archetypes, evidence contracts, and automated quality gates, ensuring that **no policy reaches production without passing deterministic quality and simulation verification**.
