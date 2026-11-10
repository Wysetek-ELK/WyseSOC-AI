import type { RequirementDomain } from "./types";

export const REQUIREMENT_DOMAINS: RequirementDomain[] = [
  {
    id: "req-fortisiem-connectivity",
    domainNumber: 1,
    title: "FortiSIEM Connectivity & Authorized Ingestion",
    stageTag: "Stage 1 · Telemetry Hub",
    summary:
      "Establishes authenticated, network-reachable communication between Server 1 and the FortiSIEM supervisor for incident and rule synchronization.",
    items: [
      {
        id: "fortisiem-host-creds",
        title: "FortiSIEM Supervisor Host, Username & Credential Configuration",
        criticality: "REQUIRED",
        description:
          "Configure FORTISIEM_HOST, FORTISIEM_USERNAME, and FORTISIEM_PASSWORD via Agent Configuration or environment settings using a dedicated read-only API service account.",
        whereToConfigure: "Agent Configuration → FortiSIEM Supervisor Connector (Administrator only)",
        route: "/agent-configuration",
        routeLabel: "Agent Configuration",
        consequenceIfMissing:
          "Live SIEM incident pulling fails or falls back to local fixture samples if FORTISIEM_MOCK_FALLBACK is enabled.",
        verificationCheck:
          "Run 'Test Connection' in Agent Configuration and confirm HTTP 200 status on /api/fortisiem/status.",
        liveStatusKey: "fortisiem",
      },
      {
        id: "fortisiem-ssl-verify",
        title: "TLS Certificate Verification (FORTISIEM_VERIFY_SSL)",
        criticality: "CONDITIONAL",
        description:
          "Enable SSL certificate verification in production environments with trusted internal PKI; disable only in isolated lab/self-signed dry-run sandboxes.",
        whereToConfigure: "Agent Configuration → FortiSIEM SSL Verification toggle",
        route: "/agent-configuration",
        routeLabel: "Agent Configuration",
        consequenceIfMissing:
          "Self-signed supervisor certificates without disabling verify_ssl cause TLS handshake failures; leaving verification off in production weakens transport security.",
        verificationCheck: "Verify Test Connection returns success without SSL handshake errors.",
      },
      {
        id: "sentinel-ingest-scheduler",
        title: "SentinelIngestWorker Continuous Sync Interval",
        criticality: "OPTIONAL",
        description:
          "Controls automated polling cadence and whether newly ingested incidents automatically queue for Verdict Triage Agent.",
        whereToConfigure: "Telemetry Hub → Sentinel Ingest Worker controls",
        route: "/telemetry-hub",
        routeLabel: "Telemetry Hub",
        consequenceIfMissing:
          "Manual pulls or file imports are required to bring new incidents into Server 1.",
        verificationCheck: "Inspect scheduler status in Telemetry Hub.",
      },
    ],
  },
  {
    id: "req-rule-definitions",
    domainNumber: 2,
    title: "Rule Identifiers & Authoritative Correlation Definitions",
    stageTag: "Stage 2 · Detection Semantics",
    summary:
      "Ensures every detection rule carries authoritative SIEM correlation logic (conditions, thresholds, windows, grouping keys) rather than runtime incident counters.",
    items: [
      {
        id: "authoritative-rule-xml",
        title: "Authoritative SIEM Rule XML / JSON Definition Import",
        criticality: "REQUIRED",
        description:
          "Sync rules from FortiSIEM or import authoritative XML/JSON correlation definitions so RuleIntelligenceAnalyzer classifies definition_status='VERIFIED'.",
        whereToConfigure: "Detection Intelligence or POST /api/rules/{identifier}/import-definition",
        route: "/detection-intelligence",
        routeLabel: "Detection Intelligence",
        consequenceIfMissing:
          "Rules remain INCOMPLETE or HEURISTIC_PARSER; Gate G1 caps score <= 10/20 and emits RULE_DEFINITION_INCOMPLETE blocker preventing policy approval.",
        verificationCheck:
          "In AIS → SIEM Semantics tab, confirm Definition Status is VERIFIED and Provenance is AUTHORITATIVE_SIEM_DEFINITION or AUTHORITATIVE_XML_IMPORT.",
      },
      {
        id: "rule-id-hygiene",
        title: "Stable SIEM Rule Identifier Mapping (rule_id & event_type)",
        criticality: "REQUIRED",
        description:
          "Ensure Incident.event_type / rule_id cleanly maps to registered Rule.rule_id entries (e.g. PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT).",
        whereToConfigure: "Detection Intelligence Registry & Telemetry Hub",
        route: "/detection-intelligence",
        routeLabel: "Detection Intelligence",
        consequenceIfMissing:
          "Unmapped incidents trigger auto-provisioned placeholder rules that lack approved policies, forcing POLICY_NOT_APPROVED abstention in live triage.",
        verificationCheck: "Confirm incidents link to the expected rule in AI Triage Workbench.",
      },
    ],
  },
  {
    id: "req-historical-sync",
    domainNumber: 3,
    title: "Historical Incident Synchronization",
    stageTag: "Stage 3 · Historical Dataset",
    summary:
      "Maintains sufficient rule-matched historical incidents with intact raw event attributes for Gate G8 simulation and regression backtesting.",
    items: [
      {
        id: "historical-incident-pull",
        title: "Rule-Specific Historical Incident Retrieval",
        criticality: "REQUIRED",
        description:
          "Pull or import historical incidents belonging to the exact target rule rather than relying on cross-rule samples.",
        whereToConfigure: "Telemetry Hub → Batch Pull / Import Jobs",
        route: "/telemetry-hub",
        routeLabel: "Telemetry Hub",
        consequenceIfMissing:
          "PolicySimulationService strictly excludes non-matching rules as RULE_MISMATCH, leaving Gate G8 at INSUFFICIENT_DATA.",
        verificationCheck: "Check Stage 2 (Rule Matched) count in AIS Simulation Lab funnel.",
      },
      {
        id: "event-payload-retention",
        title: "Nested Event & Raw Telemetry Retention",
        criticality: "REQUIRED",
        description:
          "Preserve incident raw_payload and IncidentEvent attributes during ingestion without stripping network/endpoint fields.",
        whereToConfigure: "Telemetry Hub / Ingestion Pipeline",
        route: "/telemetry-hub",
        routeLabel: "Telemetry Hub",
        consequenceIfMissing:
          "Empty payloads are rejected as CORRUPT_OR_EMPTY_PAYLOAD in simulation and score NOT_CALCULABLE in trustworthiness evaluation.",
        verificationCheck: "Open a sample incident in AI Triage Workbench and confirm raw telemetry & events render.",
      },
    ],
  },
  {
    id: "req-ground-truth-provenance",
    domainNumber: 4,
    title: "Analyst TP/FP Resolution Mapping & Provenance",
    stageTag: "Stage 4 · Ground Truth Integrity",
    summary:
      "Separates genuine human analyst TP/FP dispositions from automated ML closures or ambiguous ticket statuses.",
    items: [
      {
        id: "explicit-tp-fp-labels",
        title: "Explicit Human TP / FP Disposition (Not Closure-Only Status)",
        criticality: "REQUIRED",
        description:
          "Resolutions must map to explicit 'True Positive' or 'False Positive' dispositions. Generic statuses ('Closed', 'Auto Cleared', 'Manually Cleared') are classified as UNVERIFIED.",
        whereToConfigure: "FortiSIEM Resolution Sync / Human Review Queue",
        route: "/human-review-queue",
        routeLabel: "Human Review Queue",
        consequenceIfMissing:
          "Incidents are excluded from empirical accuracy calculations (MISSING_ANALYST_LABEL or AMBIGUOUS_LABEL) and cannot qualify for Gate G8.",
        verificationCheck: "Inspect Stage 4 (Eligible Ground Truth) vs Stage 5 exclusions in AIS Simulation Lab.",
      },
      {
        id: "provenance-identity-audit",
        title: "Analyst Identity (clearedUser), Rationale & Non-ML Provenance",
        criticality: "REQUIRED",
        description:
          "Ensure clearedUser / analyst identity and written resolution comments are preserved, and is_ml_generated is False. ML-set resolutions are strictly excluded.",
        whereToConfigure: "FortiSIEM Resolution Sync & Review Orchestrator",
        route: "/human-review-queue",
        routeLabel: "Human Review Queue",
        consequenceIfMissing:
          "ML/automated labels are filtered out as HEURISTIC_OR_ML_LABEL; missing analyst identity/rationale requires manual verification before treating an FP/TP tag as ground truth.",
        verificationCheck: "Audit HistoricalGroundTruth fields in Incident Detail view.",
      },
    ],
  },
  {
    id: "req-evidence-normalization",
    domainNumber: 5,
    title: "Evidence Normalization & Critical-Field Availability",
    stageTag: "Stage 5 · Evidence Confidence",
    summary:
      "Ensures vendor log attributes normalize into CANONICAL_FIELD_CATALOG keys expected by EvidencePreflightValidator and EvidenceSufficiencyEngine.",
    items: [
      {
        id: "canonical-field-mapping",
        title: "Canonical Attribute Normalization Coverage",
        criticality: "REQUIRED",
        description:
          "Verify incoming SIEM attributes map cleanly to canonical keys (e.g. srcIpAddr → network.source_ip, destPort → network.destination_port, Command → process.command_line).",
        whereToConfigure: "EvidenceNormalizationService & AIS Evidence Contract tab",
        route: "/agent-intelligence-studio",
        routeLabel: "Agent Intelligence Studio",
        consequenceIfMissing:
          "Missing critical fields trigger the Infallible Rule (sufficiency <= 49.0, status INSUFFICIENT), capping Trust Score <= 3/10 and forcing REQUIRES_ANALYST_ATTENTION.",
        verificationCheck: "Check canonical_evidence_count and evidence_completeness on triaged incidents.",
      },
      {
        id: "multi-sensor-enrichment",
        title: "Secondary Sensor & Authorization Context Enrichment",
        criticality: "CONDITIONAL",
        description:
          "Provide corroborating firewall/EDR sources or scanner inventory / change-management context where rules require affirmative benign proof.",
        whereToConfigure: "SIEM Event Correlation / Incident Context Enrichment",
        route: "/ai-triage-workbench",
        routeLabel: "AI Triage Workbench",
        consequenceIfMissing:
          "Single-sensor logs receive -3 consistency penalty, and FP candidates without affirmative authorization fail Guardrail G6 and abstain.",
        verificationCheck: "Review score_dimensions and supporting_evidence in Verdict Intelligence.",
      },
    ],
  },
  {
    id: "req-archetype-contract",
    domainNumber: 6,
    title: "Detection Archetype & Evidence Contract Alignment",
    stageTag: "Stage 6 · Policy Design",
    summary:
      "Binds each rule to an accurate Detection Archetype and synchronizes Section 4 required evidence with the machine-verifiable Evidence Contract.",
    items: [
      {
        id: "archetype-binding",
        title: "Accurate Archetype Classification (Not UNKNOWN)",
        criticality: "REQUIRED",
        description:
          "Confirm RuleIntelligenceAnalyzer & DetectionArchetypeRegistry classify the rule accurately (e.g. NETWORK_SCAN for TCP scans, NETWORK_EXFILTRATION for outbound transfers).",
        whereToConfigure: "Agent Intelligence Studio → SIEM Semantics & Archetype tab",
        route: "/agent-intelligence-studio",
        routeLabel: "Agent Intelligence Studio",
        consequenceIfMissing:
          "UNKNOWN classification triggers Gate G2 WARNING (INADEQUATE_TELEMETRY, 10-pt cap); mismatched directives (e.g. malware criteria on scans) trigger Gate G2 BLOCKER.",
        verificationCheck: "Verify Primary Archetype badge and confidence score in AIS Tab 3.",
      },
      {
        id: "contract-section4-sync",
        title: "Section 4 Evidence Alignment & No Unsafe FP Rules",
        criticality: "REQUIRED",
        description:
          "Ensure all critical Evidence Contract fields appear in policy Section 4 and remove blanket RFC-1918 benign rules or hardcoded confidence ranges from Sections 1 & 6.",
        whereToConfigure: "Agent Intelligence Studio → Policy Editor & Quality Gates",
        route: "/agent-intelligence-studio",
        routeLabel: "Agent Intelligence Studio",
        consequenceIfMissing:
          "Triggers Gate G3/G7 warnings or Gate G5 hard-gate failures (UNSAFE_FP_ASSUMPTION / PRESCRIPTIVE_CONFIDENCE_RANGE), blocking approval.",
        verificationCheck: "Run 'Validate Quality' in AIS and verify zero blocking findings.",
        liveStatusKey: "policies",
      },
    ],
  },
  {
    id: "req-versioning-rbac",
    domainNumber: 7,
    title: "Policy Versioning & Approval Permissions",
    stageTag: "Stage 7 · Governance & RBAC",
    summary:
      "Enforces strict separation of duties between draft authoring, automated quality gating, and Administrator-approved runtime policy promotion.",
    items: [
      {
        id: "admin-approval-rbac",
        title: "Administrator Role for Policy Approval & Rollback",
        criticality: "REQUIRED",
        description:
          "Ensure at least one active Administrator account exists to approve candidate PromptVersions or execute rollbacks; SOC Analysts can author drafts but cannot promote to live triage.",
        whereToConfigure: "Governance & Access → User Management",
        route: "/governance-access",
        routeLabel: "Governance & Access",
        consequenceIfMissing:
          "Draft policies remain stuck in DRAFT status; live VerdictTriageAgent returns POLICY_NOT_APPROVED for all incidents of that rule.",
        verificationCheck: "Verify Administrator accounts in Governance & Access and active APPROVED status in AIS.",
      },
      {
        id: "drift-revalidation",
        title: "Policy Drift Monitoring & Human Revalidation",
        criticality: "CONDITIONAL",
        description:
          "Review PolicyDriftEvents triggered by SIEM rule logic edits or diverged analyst feedback, and revalidate before approving new candidates.",
        whereToConfigure: "Agent Intelligence Studio → Drift & Monitoring tab",
        route: "/agent-intelligence-studio",
        routeLabel: "Agent Intelligence Studio",
        consequenceIfMissing:
          "Active policies flagged REVIEW_REQUIRED may no longer reflect updated SIEM correlation thresholds.",
        verificationCheck: "Check Drift & Monitoring tab for unacknowledged drift alerts.",
      },
    ],
  },
  {
    id: "req-llm-inference",
    domainNumber: 8,
    title: "Local LLM Connectivity & Inference Configuration",
    stageTag: "Stage 8 · Server 2 Inference",
    summary:
      "Connects Server 1 orchestration to Server 2 GPU inference (OpenAI-compatible endpoint serving Qwen 2.5 7B) with circuit-breaker safety.",
    items: [
      {
        id: "llm-endpoint-config",
        title: "Server 2 Host, Port, Protocol & Model Name",
        criticality: "REQUIRED",
        description:
          "Configure LOCAL_LLM_HOST, port, protocol, timeout, and model identifier (e.g. Qwen/Qwen2.5-7B-Instruct-AWQ) and verify reachability from Server 1.",
        whereToConfigure: "Agent Configuration → Local LLM Server 2 Connector",
        route: "/agent-configuration",
        routeLabel: "Agent Configuration",
        consequenceIfMissing:
          "Live AI triage defers with LocalLLMUnavailableError (production mode forbids simulated LLM fallback).",
        verificationCheck: "Run 'Test Connection' in Agent Configuration and confirm ACTIVE status in Sidebar / Inference Control.",
        liveStatusKey: "llm",
      },
      {
        id: "mock-fallback-isolation",
        title: "Disable Simulated Fallback in Production Mode (APP_ENV=production)",
        criticality: "REQUIRED",
        description:
          "Set APP_ENV=production and LOCAL_LLM_ALLOW_MOCK_FALLBACK=false for production triage so simulated verdicts are strictly prohibited.",
        whereToConfigure: "Deployment environment & Agent Configuration",
        route: "/agent-configuration",
        routeLabel: "Agent Configuration",
        consequenceIfMissing:
          "If enabled in dev/dry-run environments, simulated heuristic outputs carry is_simulated=true and must never be confused with live LLM reasoning.",
        verificationCheck: "Inspect is_simulated flag on verdicts and Server 2 health in Inference Control.",
      },
    ],
  },
  {
    id: "req-simulation-isolation",
    domainNumber: 9,
    title: "Simulation Dataset Isolation & Sufficient Verified Labels",
    stageTag: "Stage 9 · Empirical Simulation Lab",
    summary:
      "Guarantees zero train/test contamination and honest statistical gating before trusting empirical accuracy metrics.",
    items: [
      {
        id: "min-five-verified",
        title: "Minimum 5 Independently Verified Labels per Rule (Gate G8)",
        criticality: "CONDITIONAL",
        description:
          "Gate G8 requires N >= 5 rule-matched, human-verified TP/FP incidents to evaluate empirical performance without returning INSUFFICIENT_DATA.",
        whereToConfigure: "AIS Simulation Lab / Agent Simulation Lab / Human Review Queue",
        route: "/agent-simulation-lab",
        routeLabel: "Agent Simulation Lab",
        consequenceIfMissing:
          "Gate G8 remains WARNING (INSUFFICIENT_DATA, 0/15 pts) and empirical precision/recall remain N/A.",
        verificationCheck: "Check Eligible Ground Truth count >= 5 in AIS Tab 5 funnel.",
      },
      {
        id: "leakage-sanitization",
        title: "Strict Ground-Truth Sanitization & Deterministic Split Isolation",
        criticality: "REQUIRED",
        description:
          "HistoricalGroundTruthValidator strips resolution/clearedUser/comments prior to replay and partitions IDs deterministically (TRAIN 50%, TUNING 20%, CALIBRATION 15%, LOCKED_TEST 15%).",
        whereToConfigure: "Enforced automatically in PolicySimulationService & HistoricalGroundTruthValidator",
        route: "/verdict-intelligence",
        routeLabel: "Verdict Intelligence",
        consequenceIfMissing:
          "Would invalidate simulation metrics via data leakage if bypassed (strictly prevented by validator code).",
        verificationCheck: "Review partition and paired regression reports in Verdict Intelligence.",
      },
    ],
  },
  {
    id: "req-calibration-regression",
    domainNumber: 10,
    title: "Calibration & Regression Prerequisites",
    stageTag: "Stage 10 · Calibration & Trust Caps",
    summary:
      "Defines statistical thresholds needed before lifting the 6/10 Trust Score cap and reporting calibrated probabilities.",
    items: [
      {
        id: "min-thirty-balanced",
        title: "Minimum 30 Verified Cases with Balanced TP/FP (>= 3 Each)",
        criticality: "CONDITIONAL",
        description:
          "CalibrationEvaluator requires N >= 30 decisive verified evaluations AND >= 3 VERIFIED_TP AND >= 3 VERIFIED_FP before setting status='CALIBRATED' and computing Brier Score / 5-bin ECE.",
        whereToConfigure: "Verdict Intelligence → Calibration & Historical Evaluation",
        route: "/verdict-intelligence",
        routeLabel: "Verdict Intelligence",
        consequenceIfMissing:
          "Calibration remains NOT_CALIBRATED, Brier/ECE show N/A, Trust Score caps at <= 6/10, and automated TP/FP stays gated to human attention.",
        verificationCheck: "Inspect calibration_status and sample_count in Verdict Intelligence.",
        liveStatusKey: "verdict_metrics",
      },
      {
        id: "baseline-paired-replay",
        title: "Baseline Evaluation Run for Paired McNemar Regression Comparison",
        criticality: "OPTIONAL",
        description:
          "Select an existing baseline evaluation run when backtesting a candidate draft to detect critical false-negative regressions (McNemar chi-square > 3.841, p < 0.05).",
        whereToConfigure: "Verdict Intelligence → Dry-Run Evaluation & Compare",
        route: "/verdict-intelligence",
        routeLabel: "Verdict Intelligence",
        consequenceIfMissing:
          "Regression status remains NOT_ASSESSED rather than PASS or REGRESSION_DETECTED.",
        verificationCheck: "Run Baseline vs Candidate comparison in Verdict Intelligence.",
      },
    ],
  },
  {
    id: "req-monitoring-audit",
    domainNumber: 11,
    title: "Monitoring, Logs & Auditability",
    stageTag: "Stage 11 · Observability & Governance",
    summary:
      "Provides full transparency into system health, GPU circuit breakers, token consumption, timeline milestones, and immutable RBAC audit trails.",
    items: [
      {
        id: "health-gpu-telemetry",
        title: "Server 1 & Server 2 Health / Token Ledger / Timeline Telemetry",
        criticality: "REQUIRED",
        description:
          "Monitor /api/health, database connectivity, Redis/Celery queue depth, Server 2 GPU VRAM/latency, and bifurcated prompt/completion token usage.",
        whereToConfigure: "Inference Control & Agent Mission Control",
        route: "/inference-control",
        routeLabel: "Inference Control",
        consequenceIfMissing:
          "Silent GPU OOM, queue backlogs, or circuit-breaker trips can stall triage without operator visibility.",
        verificationCheck: "Inspect live CPU/GPU telemetry and historical series in Inference Control.",
      },
      {
        id: "immutable-audit-logs",
        title: "Immutable Audit Logs for Approvals, Verdicts & Config Changes",
        criticality: "REQUIRED",
        description:
          "Verify AuditLog records all AI_VERDICT_EVALUATE, PROMPT_VERSION_APPROVED, PROMPT_VERSION_ROLLEDBACK, and user administration events.",
        whereToConfigure: "Governance & Access → Audit Logs",
        route: "/governance-access",
        routeLabel: "Governance & Access",
        consequenceIfMissing:
          "Compliance, incident attribution, and change traceability cannot be audited post-incident.",
        verificationCheck: "Review Audit Log tab in Governance & Access.",
      },
    ],
  },
];
