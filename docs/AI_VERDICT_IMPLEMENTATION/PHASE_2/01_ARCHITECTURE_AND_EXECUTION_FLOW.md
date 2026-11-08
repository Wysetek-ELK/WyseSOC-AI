# AI VERDICT — PHASE 2: ARCHITECTURE & EXECUTION FLOW
## 01. ARCHITECTURE & EXECUTION FLOW

---

### 1. Architectural Model Overview
Phase 2 establishes a dual-tier decision architecture:
- **Tier 1 (Proposer):** The Local LLM (or simulated fallback) processes incident features and outputs an analytical justification, proposed verdict, and supporting claims.
- **Tier 2 (Authoritative Decider):** The Independent Verdict Verification Engine inspects canonical evidence, enforces contract constraints, grounds factual claims, and decides whether to accept or override the proposal.

```mermaid
flowchart TD
    SIEM[SIEM Ingestion / DB Incident] --> Norm[EvidenceNormalizationService\nNormalize Canonical Records]
    Norm --> NormRes[(Canonical Evidence Records\nEV-INC-ID-Field with SHA256)]
    
    Rule[Detection Rule] + PV[Approved PromptVersion] --> ContractSvc[EvidenceContractService]
    ContractSvc --> Contract[(RuleEvidenceContract\nStatus: APPROVED / UNVERIFIED)]
    
    NormRes + Contract --> Preflight[EvidencePreflightValidator]
    
    Preflight -->|Critical Evidence Missing| AbstainEarly[Abstain Immediately\nFinal Verdict: REQUIRES_ATTENTION\nToken Usage: 0]
    
    Preflight -->|Evidence Available / Partial| LLMCall[Local LLM Inference\nAllowlisted Payload with Canonical Evidence]
    
    LLMCall --> ModelOut[Model Proposed Verdict\nClaims + Raw Confidence]
    
    ModelOut + NormRes --> ClaimExt[ModelClaimExtractor\nGround Claims against Canonical Evidence]
    
    ClaimExt --> ClaimRes[(Grounding Result\nGrounded vs Unsupported Claims)]
    
    ClaimRes + Preflight + Contract + NormRes --> ValEngine[IndependentVerdictValidator\n8-Check Deterministic Pipeline]
    
    ValEngine --> Decision{Validation Checks Passed?}
    
    Decision -->|Yes: 100% Grounded & Complete| AcceptVerdict[Accept Decisive Verdict\nFinal: TRUE_POSITIVE / FALSE_POSITIVE\nVerified Confidence: Raw Score]
    
    Decision -->|No: Hallucinations / Missing / Contradictions| OverrideVerdict[Safety Override\nFinal: REQUIRES_ATTENTION\nDisplay Confidence: 0%]
    
    AcceptVerdict --> Audit[Persist Bifurcated Verdict & Audit Signature]
    OverrideVerdict --> Audit
```

---

### 2. Execution Pipeline Stages

#### Stage 1: Evidence Ingestion & Canonical Normalization
When an incident is selected for triage:
1. `EvidenceNormalizationService.normalize_incident_evidence(incident, events)` iterates through top-level attributes, linked events, and raw payloads.
2. It strips all forbidden ground-truth fields (`resolution`, `cleared_reason`, `cleared_user`, `ground_truth`, `analyst_notes`).
3. Standardizes field names into dot-notated canonical paths (`process.command_line`, `network.destination_ip`, `file.hash_sha256`).
4. Generates deterministic identifiers (`EV-{incident_id}-{event_id}-{field}`) and computes SHA-256 integrity digests over field and observed value.

#### Stage 2: Contract Derivation
1. `EvidenceContractService.get_contract_for_rule(rule, active_version)` examines the linked `PromptVersion`.
2. If `PromptVersion.status != "APPROVED"`, `contract.status` is set to `UNVERIFIED`.
3. Derives field requirements and contradiction rules matching one of 5 archetypes (`PROCESS_EXECUTION`, `NETWORK_CONNECTION`, `FILE_MALWARE`, `AUTHENTICATION`, `GENERIC`).

#### Stage 3: Pre-Inference Telemetry Gating (Preflight)
1. `EvidencePreflightValidator.validate_preflight(incident_id, contract, norm_result)` compares available fields against required contract fields.
2. If any critical required field is missing (e.g. `process.command_line` for LOLBin execution), `must_abstain_immediately = True`.
3. The pipeline short-circuits: no inference request is sent, zero tokens are consumed, and the incident is immediately routed to `REQUIRES_ATTENTION`.

#### Stage 4: Allowlisted LLM Inference
1. If preflight passes, `build_model_facing_payload()` formats allowlisted incident metadata and embeds `canonical_evidence` records.
2. The model receives instruction to cite exact `evidence_ids` in its factual claims.
3. The provider executes inference and returns a proposed verdict, confidence, reason, and supporting claims.

#### Stage 5: Factual Claim Grounding
1. `ModelClaimExtractor.extract_and_ground_claims()` parses structured claims or regex-extracted entities (IPs, hashes, binaries).
2. It verifies that cited evidence IDs belong to this incident and matches asserted values against actual observed values.
3. If the model cited facts absent from telemetry, it flags `has_hallucinations = True` and records diagnostic status `CLAIM_NOT_VERIFIABLE`.

#### Stage 6: Deterministic Validation & Bifurcated Decision
1. `IndependentVerdictValidator.validate_verdict()` executes 8 deterministic checks.
2. Authoritative outcome:
   - If checks pass: `final_verdict = proposed_verdict`, `is_decisive_accepted = True`.
   - If any check fails: `final_verdict = "REQUIRES_ATTENTION"`, `is_decisive_accepted = False`, confidence zeroed to 0.0.
3. Computes a cryptographic replay signature: `SHA-256(incident_id : contract_id : proposed : final : validator_version)[:16]`.

#### Stage 7: Persistence & Frontend Rendering
1. The incident record stores both `proposed_verdict` and authoritative `final_verdict`.
2. Frontend displays the verified verdict card, completeness meter, grounding ratio, and analyst action directive.

