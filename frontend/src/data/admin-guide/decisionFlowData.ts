import type { SwimlaneBoxSpec, WorkflowEdgeSpec, WorkflowStepSpec } from "./types";

export const DECISION_SWIMLANES: SwimlaneBoxSpec[] = [
  {
    id: "lane-decision-pipeline",
    title: "AI VERDICT DECISION ENGINE PIPELINE",
    subtitle: "Zero-Bias Extraction → Approved Policy & Contract Enforcement → Local LLM Reasoning → Deterministic Guardrails & Trust Scoring",
    accent: "cyan",
    position: { x: 16, y: 16 },
    width: 985,
    height: 300,
  },
  {
    id: "lane-decision-outcomes",
    title: "AUTHORITATIVE TRIAGE OUTCOMES (THREE-STATE VERDICT CONTRACT)",
    subtitle: "Decisive TP/FP requires >= 7/10 Trust & zero guardrails; uncertainty, missing evidence, or lack of authorization routes to REQUIRES_ANALYST_ATTENTION",
    accent: "emerald",
    position: { x: 16, y: 348 },
    width: 985,
    height: 292,
  },
];

export const DECISION_STEPS: WorkflowStepSpec[] = [
  {
    id: "new-incident",
    stepNumber: 1,
    title: "New Incident",
    shortLabel: "New Incident",
    lane: "decision",
    laneLabel: "Ingestion Trigger",
    accent: "sky",
    componentName: "Incident Record & Triage Queue",
    serviceModule: "backend/app/models/incident.py · ai_verdict_service.py",
    uiRoute: "/ai-triage-workbench",
    uiLabel: "AI Triage Workbench",
    summary:
      "A newly ingested FortiSIEM incident (or manual/batch triage request) enters VerdictTriageAgent.evaluate_incident().",
    inputData: [
      "Incident ID, title, severity, event_type, source_ip, reporting_device",
      "Raw SIEM JSON payload & correlated IncidentEvent records",
    ],
    processingLogic: [
      "Eager-loads Incident.rule and Incident.events from database",
      "Prepares incident record without exposing historical resolution fields to model inference",
    ],
    outputData: [
      "Hydrated Incident entity queued for rule matching",
    ],
    requiredConfig: [
      "Incident persisted via Telemetry Hub or fixture/API ingestion",
    ],
    failureOrAbstention: [
      "Non-existent incident identifier raises ValueError ('Incident not found')",
    ],
    position: { x: 32, y: 80 },
  },
  {
    id: "rule-match",
    stepNumber: 2,
    title: "Rule Match",
    shortLabel: "Rule Match",
    lane: "decision",
    laneLabel: "Detection Mapping",
    accent: "cyan",
    componentName: "Rule Linker & Auto-Provisioner",
    serviceModule: "backend/app/services/ai_verdict_service.py",
    uiRoute: "/detection-intelligence",
    uiLabel: "Detection Intelligence",
    summary:
      "Resolves the originating SIEM Rule by internal UUID, Rule.rule_id, or event_type to locate its detection semantics and policy registry.",
    inputData: [
      "Incident.rule_id and Incident.event_type",
      "Registered Rule catalog entries",
    ],
    processingLogic: [
      "Matches incident against stored Rule definitions",
      "Auto-provisions a placeholder Rule record if unmapped (and links sibling unmapped incidents)",
    ],
    outputData: [
      "Bound Rule object and identifier",
      "RulePrompt lookup key",
    ],
    requiredConfig: [
      "Synced FortiSIEM rules recommended so rule pattern_logic is authoritative rather than auto-provisioned",
    ],
    failureOrAbstention: [
      "Auto-provisioned rules lack an APPROVED policy version, which stops automated triage at the next step",
    ],
    position: { x: 274, y: 80 },
  },
  {
    id: "approved-policy-lookup",
    stepNumber: 3,
    title: "Approved Policy Lookup",
    shortLabel: "Approved Policy Lookup",
    lane: "decision",
    laneLabel: "Policy Governance",
    accent: "cyan",
    componentName: "AgentPolicyEngine & PolicyCompilerService",
    serviceModule: "backend/app/services/prompt_studio_service.py · policy_compiler_service.py",
    uiRoute: "/agent-intelligence-studio",
    uiLabel: "Agent Intelligence Studio",
    summary:
      "Verifies that the matched rule has an active APPROVED PromptVersion. Draft, archived, or missing policies are rejected in live triage.",
    inputData: [
      "RulePrompt.active_version_id and PromptVersion.status",
      "Execution mode (LIVE vs SIMULATION)",
    ],
    processingLogic: [
      "Checks that active version status === 'APPROVED'",
      "Compiles the 9-section policy specification and computes SHA-256 compilation_digest",
      "Retrieves rule-scoped verified precedents via VerifiedSemanticRetrievalService",
    ],
    outputData: [
      "CompiledPolicyPrompt (LIVE mode) or early abstention payload",
    ],
    requiredConfig: [
      "Administrator must approve a clean PromptVersion (zero blocking gates G1–G7) in AIS 2.0",
    ],
    failureOrAbstention: [
      "No APPROVED version in live triage triggers immediate POLICY_NOT_APPROVED → REQUIRES_ANALYST_ATTENTION (confidence 0.0)",
    ],
    position: { x: 516, y: 80 },
  },
  {
    id: "evidence-extraction",
    stepNumber: 4,
    title: "Evidence Extraction",
    shortLabel: "Evidence Extraction",
    lane: "decision",
    laneLabel: "Zero-Leakage Normalization",
    accent: "indigo",
    componentName: "EvidenceNormalizationService & Allowlist Guardrail",
    serviceModule: "backend/app/services/evidence_normalization_service.py · model_payload_allowlist.py",
    uiRoute: "/ai-triage-workbench",
    uiLabel: "AI Triage Workbench",
    summary:
      "Normalizes telemetry into canonical fields while strictly stripping historical resolutions, clearedUser, and analyst notes to prevent data leakage.",
    inputData: [
      "Raw Incident payload and nested IncidentEvent attributes",
    ],
    processingLogic: [
      "Maps vendor fields to canonical schema (e.g. srcIpAddr → network.source_ip, destPort → network.destination_port)",
      "Assigns unique canonical evidence IDs (e.g. EV-01, EV-02) and source provenance",
      "build_model_facing_payload & HistoricalGroundTruthValidator.sanitize_incident_for_inference strip outcome labels",
    ],
    outputData: [
      "EvidenceNormalizationResult (canonical_evidence records)",
      "Zero-leakage model-facing payload dictionary",
    ],
    requiredConfig: [
      "Canonical field aliases and allowlist policy active",
    ],
    failureOrAbstention: [
      "Empty or unparseable raw payloads yield zero canonical evidence records, lowering Evidence Sufficiency",
    ],
    position: { x: 758, y: 80 },
  },
  {
    id: "evidence-contract-validation",
    stepNumber: 5,
    title: "Evidence Contract Validation",
    shortLabel: "Contract Validation",
    lane: "decision",
    laneLabel: "Evidence Confidence",
    accent: "indigo",
    componentName: "EvidencePreflightValidator & EvidenceSufficiencyEngine",
    serviceModule: "backend/app/services/evidence_preflight_validator.py · evidence_sufficiency_engine.py",
    uiRoute: "/verdict-intelligence",
    uiLabel: "Verdict Intelligence",
    summary:
      "Checks critical fields required by the active RuleEvidenceContract and scores 4-dimensional Evidence Sufficiency before invoking the LLM.",
    inputData: [
      "RuleEvidenceContract & ArchetypeDefinition",
      "CanonicalEvidenceRecord list & incident payload",
    ],
    processingLogic: [
      "Verifies critical core fields (Coverage 40%, Provenance 25%, Consistency 20%, Freshness 15%)",
      "Detects direct telemetry contradictions (e.g. byte count mismatch > 1000x, inbound vs outbound conflict, loopback scan)",
      "Applies the Infallible Rule: missing mandatory field or contradiction caps sufficiency <= 49.0 and sets INSUFFICIENT / CONFLICTING",
    ],
    outputData: [
      "PreflightValidationResult (COMPLETE, PARTIAL, INSUFFICIENT, CONTRADICTORY)",
      "EvidenceSufficiencyAssessmentResult",
    ],
    requiredConfig: [
      "Approved RuleEvidenceContract bound to rule",
    ],
    failureOrAbstention: [
      "Missing critical evidence in live triage triggers immediate CRITICAL_TELEMETRY_MISSING → REQUIRES_ANALYST_ATTENTION before LLM inference",
      "Context exceeding TokenBudgetService limits triggers CONTEXT_WINDOW_EXCEEDED abstention",
    ],
    position: { x: 758, y: 224 },
  },
  {
    id: "local-llm-investigation",
    stepNumber: 6,
    title: "Local LLM Investigation",
    shortLabel: "Local LLM Investigation",
    lane: "decision",
    laneLabel: "Reasoning Inference",
    accent: "sky",
    componentName: "Server 2 OpenAI-Compatible Provider & GPUWorkloadManager",
    serviceModule: "backend/app/services/ai_verdict_service.py · gpu_manager.py",
    uiRoute: "/inference-control",
    uiLabel: "Inference Control",
    summary:
      "Sends the compiled 9-section prompt, verified precedents, and sanitized canonical evidence to Server 2 Local LLM (Qwen 2.5 7B) to propose a verdict and cited claims.",
    inputData: [
      "Budgeted 9-section policy prompt + up to 2 rule-scoped precedents",
      "Allowlisted canonical evidence payload",
    ],
    processingLogic: [
      "Acquires GPU slot guarded by GPUServerCircuitBreaker",
      "Produces JSON output containing proposed verdict, raw uncalibrated confidence (0–100), reason, cited supporting_claims, missing_evidence, and analyst_questions",
    ],
    outputData: [
      "Proposed verdict (TRUE_POSITIVE | FALSE_POSITIVE | REQUIRES_ATTENTION)",
      "Raw subjective model confidence (NOT a calibrated probability) + supporting_claims",
    ],
    requiredConfig: [
      "Local LLM Server 2 healthy and reachable",
      "Model endpoint configured in Agent Configuration",
    ],
    failureOrAbstention: [
      "Offline LLM or open circuit breaker raises LocalLLMUnavailableError (defers verdict cleanly)",
      "LLM may itself propose REQUIRES_ATTENTION when authorization or evidence is ambiguous",
    ],
    position: { x: 516, y: 224 },
  },
  {
    id: "deterministic-safety-checks",
    stepNumber: 7,
    title: "Deterministic Safety Checks",
    shortLabel: "Safety Guardrails",
    lane: "decision",
    laneLabel: "Claim & Guardrail Audit",
    accent: "amber",
    componentName: "VerdictClaimValidator · IndependentVerdictValidator · VerdictGuardrailsEngine",
    serviceModule: "backend/app/services/verdict_claim_validator.py · independent_verdict_validator.py · verdict_guardrails_engine.py",
    uiRoute: "/verdict-intelligence",
    uiLabel: "Verdict Intelligence",
    summary:
      "Audits model claims against actual telemetry and enforces 7 deterministic safety guardrails so ungrounded assertions or negative FP assumptions can never auto-resolve.",
    inputData: [
      "Proposed LLM verdict & supporting_claims",
      "EvidenceSufficiencyAssessmentResult & canonical telemetry",
    ],
    processingLogic: [
      "G1: Missing mandatory evidence → REQUIRES_ANALYST_ATTENTION",
      "G2: Material contradictions (e.g. Process Blocked=True vs unhindered breach) → REQUIRES_ANALYST_ATTENTION",
      "G3: Hallucinated IPs, hashes, or unverified thresholds → REQUIRES_ANALYST_ATTENTION",
      "G4: Incomplete rule semantics on threshold-dependent rules → REQUIRES_ANALYST_ATTENTION",
      "G6: False Positive without affirmative business authorization proof (e.g. no verified scanner ticket or maintenance justification) → REQUIRES_ANALYST_ATTENTION",
      "G7: Alert firing alone without grounded malicious indicator → REQUIRES_ANALYST_ATTENTION",
    ],
    outputData: [
      "ClaimVerificationResult (grounding_ratio, unsupported_claims, contradictions)",
      "VerdictGuardrailResult (guardrails_triggered, escalation_reason)",
    ],
    requiredConfig: [
      "Deterministic guardrails are permanently enforced in backend code",
    ],
    failureOrAbstention: [
      "Any triggered guardrail G1–G7 overrides model TP/FP proposal to REQUIRES_ANALYST_ATTENTION",
    ],
    position: { x: 274, y: 224 },
  },
  {
    id: "trustworthiness-calculation",
    stepNumber: 8,
    title: "Verdict Trustworthiness Calculation",
    shortLabel: "Trustworthiness Score",
    lane: "decision",
    laneLabel: "Explainable 1–10 Scoring",
    accent: "amber",
    componentName: "VerdictTrustworthinessEngine (v2.2.0)",
    serviceModule: "backend/app/services/verdict_trustworthiness_engine.py",
    uiRoute: "/verdict-intelligence",
    uiLabel: "Verdict Intelligence",
    summary:
      "Computes an explainable 1–10 ordinal Trust Score across 5 deterministic dimensions (100 raw points) with strict uncalibrated and missing-evidence caps.",
    inputData: [
      "ClaimVerificationResult & EvidenceSufficiencyAssessmentResult",
      "Historical sample size & calibration status (is_calibrated, N)",
    ],
    processingLogic: [
      "Sums 5 dimensions: Claim Support (35) + Source Reliability (20) + Contradiction Handling (15) + Corroboration (15) + Historical Validation (15)",
      "Maps raw 0–100 score to 1–10 ordinal scale; Score 10 requires calibrated N >= 30 and raw >= 98",
      "Caps Trust Score at <= 6/10 when rule is uncalibrated (N < 30), and at <= 3/10 if mandatory fields are missing or conflicting",
      "Returns NOT_CALCULABLE (null score) if telemetry is completely absent",
    ],
    outputData: [
      "VerdictTrustAssessmentResult (trust_score 1–10 or NOT_CALCULABLE, raw_trust_score, score_dimensions, confidence_limitations)",
    ],
    requiredConfig: [
      "N >= 30 verified balanced historical outcomes required to lift the 6/10 calibration cap",
    ],
    failureOrAbstention: [
      "Guardrail G5: Trust Score < 7/10 (or raw < 70) strictly blocks automated TP/FP and escalates to REQUIRES_ANALYST_ATTENTION",
    ],
    position: { x: 32, y: 224 },
  },
  {
    id: "final-decision",
    stepNumber: 9,
    title: "Final Decision",
    shortLabel: "Final Decision Gate",
    lane: "decision",
    laneLabel: "Authoritative Routing",
    accent: "cyan",
    componentName: "Authoritative Verdict Dispatcher",
    serviceModule: "backend/app/services/verdict_trustworthiness_engine.py · ai_verdict_service.py",
    uiRoute: "/ai-triage-workbench",
    uiLabel: "AI Triage Workbench",
    summary:
      "Emits the final persisted user-visible verdict (TRUE_POSITIVE, FALSE_POSITIVE, or REQUIRES_ANALYST_ATTENTION), records token/timeline telemetry, and updates the Human Review Queue.",
    inputData: [
      "Guardrail-adjusted effective_verdict & VerdictTrustAssessmentResult",
    ],
    processingLogic: [
      "Selects decisive TP or FP ONLY when Trust >= 7/10, evidence is SUFFICIENT, claims are grounded, and all guardrails G1–G7 pass",
      "Routes all uncertain, incomplete, conflicting, uncalibrated (< 7/10), or unapproved cases to REQUIRES_ANALYST_ATTENTION",
      "Persists Verdict, TokenUsageRecord, TelemetryTimelineRecord, and AuditLog",
    ],
    outputData: [
      "Three-state authoritative decision + audit trail",
    ],
    requiredConfig: [
      "AuditLog & DB persistence operational",
    ],
    failureOrAbstention: [
      "Fail-closed safety default: any error, uncertainty, or threshold gap routes to human analyst review",
    ],
    position: { x: 32, y: 458 },
  },
  {
    id: "outcome-tp",
    stepNumber: 10,
    title: "TRUE_POSITIVE",
    shortLabel: "TRUE_POSITIVE",
    lane: "outcome",
    laneLabel: "Decisive Malicious",
    accent: "rose",
    outcomeBadge: "TRUE_POSITIVE",
    componentName: "Confirmed Malicious / Unauthorized Activity",
    serviceModule: "UserVisibleVerdict.TRUE_POSITIVE",
    uiRoute: "/ai-triage-workbench",
    uiLabel: "AI Triage Workbench",
    summary:
      "Issued only when grounded telemetry proves unauthorized or malicious tradecraft, evidence is SUFFICIENT, Trust Score >= 7/10 (calibrated), and Guardrail G7 confirms more than just alert firing.",
    inputData: [
      "Grounded malicious OBSERVED_FACT claims + complete mandatory telemetry",
      "Trust Score >= 7/10 (raw >= 70) and rule calibrated",
    ],
    processingLogic: [
      "Passes G1–G7 guardrails with zero contradictions or hallucinated entities",
      "Preserves calibrated probability ONLY if CalibrationEvaluator has verified N >= 30 balanced samples",
    ],
    outputData: [
      "Authoritative TRUE_POSITIVE triage verdict + P1/P2 escalation guidance",
    ],
    requiredConfig: [
      "Calibrated rule & sufficient mandatory telemetry",
    ],
    failureOrAbstention: [
      "Alert firing alone without corroborating observed indicators is blocked by Guardrail G7 and demoted to REQUIRES_ANALYST_ATTENTION",
    ],
    position: { x: 344, y: 404 },
  },
  {
    id: "outcome-fp",
    stepNumber: 11,
    title: "FALSE_POSITIVE",
    shortLabel: "FALSE_POSITIVE",
    lane: "outcome",
    laneLabel: "Decisive Benign",
    accent: "emerald",
    outcomeBadge: "FALSE_POSITIVE",
    componentName: "Confirmed Benign / Authorized Activity",
    serviceModule: "UserVisibleVerdict.FALSE_POSITIVE",
    uiRoute: "/ai-triage-workbench",
    uiLabel: "AI Triage Workbench",
    summary:
      "Issued only with affirmative, grounded evidence of business authorization (e.g. verified vulnerability scanner, approved maintenance ticket, scheduled backup), SUFFICIENT evidence, and Trust Score >= 7/10.",
    inputData: [
      "Grounded affirmative benign justification claims or verified business_authorization context",
      "Complete mandatory evidence & zero contradictions",
    ],
    processingLogic: [
      "Satisfies Guardrail G6 (Prohibition of Negative/Blanket FP Assumptions)",
      "Never infers benign intent solely from internal RFC-1918 IPs or absence of malware artifacts",
    ],
    outputData: [
      "Authoritative FALSE_POSITIVE verdict with documented authorization evidence",
    ],
    requiredConfig: [
      "Affirmative benign context observable in telemetry or incident context",
    ],
    failureOrAbstention: [
      "Missing scanner/change-ticket authorization fails Guardrail G6 and safely demotes to REQUIRES_ANALYST_ATTENTION",
    ],
    position: { x: 344, y: 518 },
  },
  {
    id: "outcome-attention",
    stepNumber: 12,
    title: "REQUIRES_ANALYST_ATTENTION",
    shortLabel: "REQUIRES_ANALYST_ATTENTION",
    lane: "outcome",
    laneLabel: "Safe Abstention / Escalation",
    accent: "amber",
    outcomeBadge: "REQUIRES_ANALYST_ATTENTION",
    componentName: "Safe Abstention & Tier-2 Human Queue Routing",
    serviceModule: "UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION",
    uiRoute: "/human-review-queue",
    uiLabel: "Human Review Queue",
    summary:
      "First-class safety outcome whenever evidence is missing, telemetry conflicts, claims fail grounding, authorization is unverified, policy is unapproved, or Trust Score < 7/10.",
    inputData: [
      "Escalation reason, missing_evidence list, confidence_limitations, and analyst_questions",
    ],
    processingLogic: [
      "Preserves model transparency (proposed_verdict vs guardrail-adjusted effective_verdict)",
      "Creates/updates Investigation item for SOC analyst Q&A and verified adjudication",
    ],
    outputData: [
      "Actionable human review ticket with exact missing fields & investigative questions",
    ],
    requiredConfig: [
      "SOC Analyst team monitoring Human Review Queue",
    ],
    failureOrAbstention: [
      "Abstention is NOT a failure — it is the system's designed safety control preventing silent misclassifications",
    ],
    position: { x: 758, y: 458 },
  },
];

export const DECISION_EDGES: WorkflowEdgeSpec[] = [
  { id: "d-1-2", source: "new-incident", target: "rule-match", sourceHandle: "right-out", targetHandle: "left-in", accent: "sky" },
  { id: "d-2-3", source: "rule-match", target: "approved-policy-lookup", sourceHandle: "right-out", targetHandle: "left-in", accent: "cyan" },
  { id: "d-3-4", source: "approved-policy-lookup", target: "evidence-extraction", sourceHandle: "right-out", targetHandle: "left-in", accent: "indigo" },
  { id: "d-4-5", source: "evidence-extraction", target: "evidence-contract-validation", sourceHandle: "bottom-out", targetHandle: "top-in", accent: "indigo" },
  { id: "d-5-6", source: "evidence-contract-validation", target: "local-llm-investigation", sourceHandle: "left-out", targetHandle: "right-in", accent: "sky" },
  { id: "d-6-7", source: "local-llm-investigation", target: "deterministic-safety-checks", sourceHandle: "left-out", targetHandle: "right-in", accent: "amber" },
  { id: "d-7-8", source: "deterministic-safety-checks", target: "trustworthiness-calculation", sourceHandle: "left-out", targetHandle: "right-in", accent: "amber" },
  { id: "d-8-9", source: "trustworthiness-calculation", target: "final-decision", sourceHandle: "bottom-out", targetHandle: "top-in", accent: "cyan" },
  {
    id: "d-preflight-abstain",
    source: "evidence-contract-validation",
    target: "outcome-attention",
    label: "Missing Critical",
    isBridge: true,
    bridgeNote: "Preflight gate halts before LLM if mandatory fields are absent",
    sourceHandle: "bottom-out",
    targetHandle: "top-in",
    accent: "amber",
  },
  { id: "d-9-tp", source: "final-decision", target: "outcome-tp", label: "TP >=7/10", sourceHandle: "right-out", targetHandle: "left-in", accent: "rose" },
  { id: "d-9-fp", source: "final-decision", target: "outcome-fp", label: "FP >=7/10", sourceHandle: "right-out", targetHandle: "left-in", accent: "emerald" },
  { id: "d-9-attn", source: "final-decision", target: "outcome-attention", label: "Guardrail / <7", sourceHandle: "bottom-out", targetHandle: "bottom-in", accent: "amber" },
];
