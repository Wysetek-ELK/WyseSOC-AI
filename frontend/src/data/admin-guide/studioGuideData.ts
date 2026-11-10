import type { PolicySectionDoc, QualityGateDoc, StudioLifecycleStage } from "./types";

export const STUDIO_LIFECYCLE_STAGES: StudioLifecycleStage[] = [
  {
    step: 1,
    id: "ingestion-verification",
    title: "FortiSIEM Rule Ingestion & Authoritative Definition Verification",
    service: "FortiSIEMService & RuleIntelligenceAnalyzer",
    uiTab: "SIEM Semantics & Archetype",
    summary:
      "Separates genuine SIEM correlation rule definitions (thresholds, aggregation windows, GROUP BY keys) from observed runtime incident metrics.",
    keyGuarantee:
      "Runtime counters like {'incidentCount': 161} are segregated into parsed_metadata['source_incident_metrics'] and never treated as authoritative thresholds.",
    details: [
      "Authoritative XML/JSON definitions yield definition_status='VERIFIED' and provenance='AUTHORITATIVE_SIEM_DEFINITION' (or 'AUTHORITATIVE_XML_IMPORT').",
      "Auto-synced cache-miss rules or heuristic parses without XML are marked 'INCOMPLETE' or 'HEURISTIC_PARSER', capping Gate G1 and preventing unearned approval.",
      "Multiline GROUP BY, COUNT >= 1 single-match triggers, and time windows (e.g. 300s) are parsed deterministically.",
    ],
  },
  {
    step: 2,
    id: "archetype-classification",
    title: "Detection Archetype Classification (Including NETWORK_SCAN)",
    service: "DetectionArchetypeRegistry (v2.0.0)",
    uiTab: "SIEM Semantics & Archetype",
    summary:
      "Maps parsed rule semantics and MITRE ATT&CK indicators into a versioned behavioral archetype so investigation policies focus on the right telemetry domain.",
    keyGuarantee:
      "A network scanning rule receives NETWORK_SCAN reconnaissance criteria—never endpoint malware execution demands like SHA256 file hashes or PowerShell parent lineage.",
    details: [
      "NETWORK_SCAN matches HOST_SCAN, PORT_SCAN, T1595, T1018, and rules like PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT.",
      "Defines mandatory core fields (security.event_type, event.timestamp, network.source_ip, network.destination_port), conditional scan fields (scan.rate_per_second, scan.connection_count, network.destination_ip_list), and unsupported EDR fields.",
      "Inadequate telemetry metadata falls back honestly to UNKNOWN ('Unclassified / Inadequate Telemetry'), triggering Gate G2 WARNING.",
    ],
  },
  {
    step: 3,
    id: "evidence-contract",
    title: "Evidence Contract Generation & Field Requirements",
    service: "EvidenceContractService & EvidenceRequirementMapper",
    uiTab: "Evidence Contract",
    summary:
      "Constructs a machine-verifiable RuleEvidenceContract bound to the rule and policy version using CANONICAL_FIELD_CATALOG.",
    keyGuarantee:
      "Contract status is strictly bound to PromptVersion status: only APPROVED policy versions produce APPROVED contracts; drafts remain UNVERIFIED.",
    details: [
      "Classifies fields into CORE (mandatory critical), CONDITIONAL, OPTIONAL_ENRICHMENT, and UNSUPPORTED.",
      "For NETWORK_SCAN, critical contract fields include security.event_type, event.timestamp, network.source_ip, and network.destination_port.",
      "Synchronizes computed properties (core_fields, conditional_fields, unsupported_fields) directly to the AIS Tab 4 UI and runtime preflight checks.",
    ],
  },
  {
    step: 4,
    id: "nine-section-policy",
    title: "Nine-Section Intelligent Investigation Policy Generation",
    service: "PolicyGenerationService & PolicyCompilerService",
    uiTab: "Policy Editor (9 Sections)",
    summary:
      "Synthesizes a complete nine-section investigation policy draft tailored to the rule's DetectionSemantics, ArchetypeDefinition, and Evidence Contract.",
    keyGuarantee:
      "Eliminates blanket RFC-1918 benign assumptions and hardcoded subjective confidence ranges (e.g. 80–98%); never invents missing thresholds.",
    details: [
      "Section 1 enforces ENTERPRISE_SOC_BASELINE_V2 across all rules.",
      "Sections 2–8 translate detection logic, required evidence, TP/FP indicators, abstention criteria, and escalation rules into deterministic directives.",
      "Section 9 encodes structured analyst Q&A checklists used during triage and Human Review Queue follow-up.",
    ],
  },
  {
    step: 5,
    id: "quality-gates-g1-g7",
    title: "Structural Quality Validation Using Gates G1–G7",
    service: "PolicyQualityValidator (v2.0.0)",
    uiTab: "Quality Gates (G1–G8)",
    summary:
      "Runs deterministic structural verification across Gates G1 through G7 (85 raw structural points scaled to 0–100 structural_quality_score).",
    keyGuarantee:
      "Hard Gate Failure strictly overrides numeric score: even if structural quality scores high, any single blocking finding sets approval_eligible = FALSE.",
    details: [
      "Audits Rule Integrity (G1), Archetype Relevance (G2), Contract Feasibility (G3), TP Criteria (G4), FP Criteria (G5), Abstention/Escalation (G6), and Internal Consistency (G7).",
      "Computes cryptographic SHA-256 bindings: policy_digest, contract_digest, and rule_digest.",
      "Generates targeted remediation recommendations for every FAILED or WARNING gate.",
    ],
  },
  {
    step: 6,
    id: "historical-sim-g8",
    title: "Historical Simulation & Gate G8 Empirical Validation",
    service: "PolicySimulationService & EmpiricalAccuracyEvaluator",
    uiTab: "Simulation Lab",
    summary:
      "Replays isolated, rule-matched historical incidents through a 6-stage eligibility funnel and compares candidate policies against baselines.",
    keyGuarantee:
      "When fewer than 5 verified human-labeled TP/FP incidents exist for the target rule, Gate G8 honestly reports INSUFFICIENT_DATA (0/15 pts) rather than fabricating accuracy.",
    details: [
      "6-Stage Funnel: Total Scanned → Rule Matched → Analyst Labeled → Eligible Ground Truth → Excluded → Evaluated.",
      "Excludes unrelated rules (RULE_MISMATCH) and ML/automated closures (HEURISTIC_OR_ML_LABEL).",
      "Paired replay computes McNemar test approximation (chi-square > 3.841, p < 0.05) and blocks approval on critical false-negative regressions.",
    ],
  },
  {
    step: 7,
    id: "versioning-approval-rollback",
    title: "Candidate Versioning, Approval, Activation & Rollback",
    service: "AgentPolicyEngine & PolicyLifecycleMonitor",
    uiTab: "Policy Editor & Drift Monitoring",
    summary:
      "Maintains immutable, non-destructive PromptVersion history across DRAFT, APPROVED, and ARCHIVED states with Administrator RBAC gating.",
    keyGuarantee:
      "Generated or remediated drafts never overwrite an active APPROVED policy automatically; drift events flag active policies REVIEW_REQUIRED without silent mutation.",
    details: [
      "Approval atomically sets active version to APPROVED, clears is_template_draft, archives the prior version, and writes an AuditLog entry.",
      "Rollback reactivates a previously audited version deterministically if live drift or regression occurs.",
      "Only Administrator users (require_admin) can approve or roll back production triage policies.",
    ],
  },
  {
    step: 8,
    id: "runtime-governance",
    title: "Governing the Runtime Verdict Triage Agent",
    service: "PolicyCompilerService & VerdictTriageAgent",
    uiTab: "AI Triage Workbench",
    summary:
      "Compiles the active APPROVED nine-section policy and Evidence Contract into the exact runtime prompt and guardrail envelope used on live incidents.",
    keyGuarantee:
      "If a rule has no APPROVED policy version in live triage, VerdictTriageAgent refuses LLM inference and returns POLICY_NOT_APPROVED → REQUIRES_ATTENTION.",
    details: [
      "CompilationExecutionMode.LIVE enforces 100% prompt parity with Simulation Lab.",
      "Binds compilation_digest, contract_id, contract_version, and policy_version_number to every persisted AI verdict.",
      "Ensures runtime EvidencePreflightValidator and VerdictGuardrailsEngine enforce the exact contract designed in Studio.",
    ],
  },
];

export const QUALITY_GATES_DOCS: QualityGateDoc[] = [
  {
    gateId: "G1",
    gateCode: "G1_RULE_INTEGRITY",
    gateName: "Rule Definition Integrity",
    category: "STRUCTURAL",
    breakdownBucket: "detection_semantics (combined with G2, max 20 pts)",
    maxScore: 20,
    weightNote: "20 pts (shared bucket with G2)",
    description:
      "Verifies that the SIEM rule has authoritative correlation detection semantics rather than heuristic guesses, runtime incident counters, or fabricated numeric thresholds.",
    passConditions: [
      "definition_status is VERIFIED with AUTHORITATIVE_SIEM_DEFINITION or AUTHORITATIVE_XML_IMPORT provenance",
      "No runtime counters (incidentCount, incidentDetail) masquerading as rule logic",
      "Section 3 does not invent thresholds absent from authoritative rule definition",
    ],
    warningConditions: [
      "AUTO_SYNCED_FROM_INCIDENT provenance (-4 pts)",
      "HEURISTIC_PARSER provenance without authoritative XML/JSON (-6 pts)",
      "Runtime incidentCount / incidentDetail text detected in conditions (-4 pts)",
    ],
    blockerConditions: [
      "RULE_DEFINITION_INCOMPLETE: definition_status is INCOMPLETE or UNKNOWN (caps G1 score <= 10.0)",
      "INVENTED_THRESHOLD_DETECTED: Section 3 asserts a specific numeric threshold missing from authoritative SIEM rule logic",
    ],
    remediationGuidance: [
      "Import authoritative SIEM rule definition via XML/JSON API (POST /api/rules/{identifier}/import-definition).",
      "Remove fabricated or unverified numeric thresholds from Section 3 detection conditions.",
    ],
  },
  {
    gateId: "G2",
    gateCode: "G2_ARCHETYPE_RELEVANCE",
    gateName: "Detection Archetype Relevance",
    category: "STRUCTURAL",
    breakdownBucket: "detection_semantics (caps bucket to 10 on WARN, 0 on FAIL)",
    maxScore: 20,
    weightNote: "Caps detection_semantics bucket",
    description:
      "Ensures the policy's investigation directives match the classified Detection Archetype (e.g. NETWORK_SCAN vs NETWORK_EXFILTRATION vs MALWARE_EXECUTION) and blocks cross-domain criteria errors.",
    passConditions: [
      "Rule classified into a definitive behavioral archetype (not UNKNOWN)",
      "Policy sections align with archetype detection intent (e.g. scan rate, source IP authorization, destination port for NETWORK_SCAN)",
    ],
    warningConditions: [
      "INADEQUATE_TELEMETRY: Rule classified as UNKNOWN ('Unclassified / Inadequate Telemetry'), capping detection_semantics at 10.0 / 20.0",
    ],
    blockerConditions: [
      "ARCHETYPE_RELEVANCE_MISMATCH: Network exfiltration or NETWORK_SCAN policy demands >= 2 endpoint malware concepts (e.g. powershell, lolbin, file hash sha256, parent process lineage)",
    ],
    remediationGuidance: [
      "Enrich rule telemetry mappings and bind the authoritative detection archetype instead of UNKNOWN.",
      "Remove irrelevant endpoint malware execution directives from network scan or exfiltration policies.",
    ],
  },
  {
    gateId: "G3",
    gateCode: "G3_EVIDENCE_FEASIBILITY",
    gateName: "Evidence Contract Feasibility",
    category: "STRUCTURAL",
    breakdownBucket: "evidence_contract (max 20 pts)",
    maxScore: 20,
    weightNote: "20 pts",
    description:
      "Validates that a RuleEvidenceContract is bound, contains critical fields, maps every mandatory core field of the archetype, and avoids unsupported field demands.",
    passConditions: [
      "Valid RuleEvidenceContract bound to the policy version",
      "At least one critical evidence field defined",
      "Every archetype mandatory_core_field is present in contract.required_evidence",
      "Policy Section 4 does not demand fields listed in archetype.unsupported_fields",
    ],
    warningConditions: [
      "Contract defines zero critical evidence requirements (-5 pts)",
      "UNSUPPORTED_EVIDENCE_DEMAND: Policy requests fields unsupported by the archetype (-3 pts per field, up to -6 pts)",
    ],
    blockerConditions: [
      "MISSING_EVIDENCE_CONTRACT: No Evidence Contract bound (score = 0.0)",
      "UNMAPPED_CORE_EVIDENCE: Archetype mandatory core field missing from contract (-4 pts per field)",
    ],
    remediationGuidance: [
      "Bind an authoritative Evidence Contract via Rule Intelligence / Evidence Requirement Mapper.",
      "Map missing core fields to canonical telemetry attributes and remove unsupported EDR/host demands from network policies.",
    ],
  },
  {
    gateId: "G4",
    gateCode: "G4_TP_CRITERIA_VALIDITY",
    gateName: "TP Criteria Validity",
    category: "STRUCTURAL",
    breakdownBucket: "tp_fp_criteria (G4 10 pts + G5 10 pts = 20 pts)",
    maxScore: 10,
    weightNote: "10 pts",
    description:
      "Verifies that Section 5 True Positive indicators define concrete, measurable, domain-appropriate malicious criteria rather than vague suspicion.",
    passConditions: [
      "Substantive TP criteria (>= 20 chars) grounded in objective attack indicators",
      "Distinguishes confirmed threat behaviors from generic alert firing",
      "Domain-aligned indicators for network vs endpoint archetypes",
    ],
    warningConditions: [
      "TP indicators equate general 'suspicious' wording with confirmed maliciousness without objective terms (-3 pts)",
      "Network rule TP criteria reference endpoint malware artifacts like file hash, sha256, or quarantined (-3 pts)",
    ],
    blockerConditions: [
      "INADEQUATE_TP_CRITERIA: Section 5 True Positive indicators are empty or < 20 characters (score = 0.0)",
    ],
    remediationGuidance: [
      "Define concrete, measurable, evidence-backed True Positive criteria in Section 5 tailored to the rule's archetype.",
    ],
  },
  {
    gateId: "G5",
    gateCode: "G5_FP_CRITERIA_VALIDITY",
    gateName: "FP Criteria & Benign Assumptions",
    category: "STRUCTURAL",
    breakdownBucket: "tp_fp_criteria (G4 10 pts + G5 10 pts = 20 pts)",
    maxScore: 10,
    weightNote: "10 pts",
    description:
      "Audits Section 6 (and Section 1) to guarantee False Positive criteria rely on verifiable authorization rather than dangerous blanket internal-IP assumptions or hardcoded confidence ranges.",
    passConditions: [
      "Substantive FP criteria (>= 20 chars) specifying verifiable benign exceptions (e.g. authorized scanner with change ticket)",
      "Zero blanket assumptions that RFC-1918 or loopback traffic is benign",
      "Zero hardcoded prescriptive confidence ranges (e.g. 80–98%)",
    ],
    warningConditions: [
      "Brief FP criteria (< 20 chars) lacking explicit legitimate operational exceptions (-2 pts)",
    ],
    blockerConditions: [
      "UNSAFE_FP_ASSUMPTION: Blanket assertion that internal RFC-1918 or loopback (127.0.0.1 / ::1) traffic is benign (zeros G5 score = 0.0)",
      "PRESCRIPTIVE_CONFIDENCE_RANGE: Hardcoded artificial confidence ranges (e.g. 80-98%, 85-95%) detected (zeros G5 score = 0.0)",
    ],
    remediationGuidance: [
      "Remove hardcoded subjective confidence ranges from policy prompts.",
      "Revise Sections 1 & 6 to require affirmative verification (e.g. approved scanner inventory or maintenance ticket) instead of assuming internal IPs are safe.",
    ],
  },
  {
    gateId: "G6",
    gateCode: "G6_ABSTENTION_ESCALATION",
    gateName: "Abstention & Escalation Safety",
    category: "STRUCTURAL",
    breakdownBucket: "abstention_escalation (max 15 pts)",
    maxScore: 15,
    weightNote: "15 pts",
    description:
      "Ensures Sections 7 and 8 define explicit abstention triggers (REQUIRES_ATTENTION) for missing/conflicting telemetry and safe P1/P2 human escalation conditions.",
    passConditions: [
      "Section 7 defines >= 15 chars of abstention criteria explicitly mentioning REQUIRES_ATTENTION or abstain",
      "Section 8 defines >= 15 chars of P1/P2 escalation criteria without unsafe internal-target exemptions or un-gated autonomous host isolation",
    ],
    warningConditions: [
      "Abstention criteria omit explicit REQUIRES_ATTENTION / abstain instruction (-3 pts)",
      "Minimal escalation conditions (< 15 chars, -4 pts)",
      "Autonomous containment wording ('isolate host immediately') without human gating (-2 pts)",
    ],
    blockerConditions: [
      "MISSING_CRITICAL_ABSTENTION: Section 7 abstention criteria undefined (< 15 chars, -8 pts)",
      "UNSAFE_ESCALATION_ASSUMPTION: Escalation text assumes internal/RFC-1918 targets are benign (-5 pts)",
    ],
    remediationGuidance: [
      "Specify mandatory abstention triggers (REQUIRES_ATTENTION) and human-gated escalation conditions in Sections 7 & 8.",
    ],
  },
  {
    gateId: "G7",
    gateCode: "G7_POLICY_CONSISTENCY",
    gateName: "Internal Policy & Contract Consistency",
    category: "STRUCTURAL",
    breakdownBucket: "internal_consistency (max 10 pts)",
    maxScore: 10,
    weightNote: "10 pts",
    description:
      "Cross-checks that all critical Evidence Contract fields are explicitly represented in Section 4 and that Section 4 does not demand non-existent thresholds.",
    passConditions: [
      "Every critical field in RuleEvidenceContract (e.g. security.event_type, network.source_ip) is referenced in Section 4 required evidence",
      "No contradiction between INCOMPLETE semantics and Section 4 threshold demands",
    ],
    warningConditions: [
      "Critical contract field absent from Section 4 text (-1 pt per missing field)",
      "Section 4 demands an authoritative threshold while rule semantics threshold is None",
    ],
    blockerConditions: [
      "None directly in v2.0.0 unless paired with upstream G1/G3 blockers (score penalty reduces total quality score).",
    ],
    remediationGuidance: [
      "Explicitly list all critical Evidence Contract fields (e.g. security.event_type, event.timestamp) in Section 4.",
    ],
  },
  {
    gateId: "G8",
    gateCode: "G8_SIMULATION_REGRESSION",
    gateName: "Simulation & Regression Validation",
    category: "EMPIRICAL",
    breakdownBucket: "historical_simulation (max 15 pts — SEPARATE from Structural G1–G7)",
    maxScore: 15,
    weightNote: "15 pts (Empirical Only)",
    description:
      "Evaluates real historical performance on rule-matched, human-verified TP/FP incidents and ensures candidate drafts do not regress against the approved baseline.",
    passConditions: [
      "Simulation executed on >= 5 rule-matched, independently verified human ground-truth incidents",
      "Zero critical false-negative regressions against baseline (regression_status != REGRESSION_DETECTED)",
    ],
    warningConditions: [
      "NOT_EVALUATED: Historical simulation has not yet been executed (0.0 / 15.0 pts)",
      "INSUFFICIENT_DATA: Verified rule-matched ground-truth cases < 5 (0.0 / 15.0 pts — does NOT fabricate empirical pass)",
    ],
    blockerConditions: [
      "FAILED_REGRESSION_GATE: Critical regressions > 0 or regression_detected=True on paired historical replay (blocks approval)",
    ],
    remediationGuidance: [
      "Collect at least 5 independently verified, analyst-labeled TP/FP historical incidents matching the exact target rule.",
      "Resolve any false-negative behavioral regressions on the frozen dataset before promoting candidate policy.",
    ],
  },
];

export const NINE_POLICY_SECTIONS: PolicySectionDoc[] = [
  {
    sectionNumber: 1,
    sectionId: "COMMON_SOC_BASELINE",
    title: "Common SOC Baseline Protocol",
    owner: "Platform Standard (ENTERPRISE_SOC_BASELINE_V2)",
    description: "Shared enterprise Level-2 triage rules enforced across every rule policy.",
    purposeInTriage:
      "Mandates factual telemetry grounding, forbids treating suspicion as confirmation, bans blanket RFC-1918 benign assumptions, forbids hardcoded confidence ranges, and forces REQUIRES_ATTENTION on deficient evidence.",
    gateDependencies: ["G5", "G6"],
    exampleSnippet:
      "NO UNIVERSAL BENIGN ASSUMPTIONS: Internal RFC-1918 traffic and loopback addresses are NOT inherently harmless. Verify administrative authorization before classifying activity as benign.",
  },
  {
    sectionNumber: 2,
    sectionId: "RULE_SPECIFIC_DIRECTIVE",
    title: "Rule-Specific Investigation Directive",
    owner: "PolicyGenerationService (Archetype-Tailored)",
    description: "Tailors investigative steps to the rule's identifier, event category, and classified Detection Archetype.",
    purposeInTriage:
      "Guides the Local LLM to verify domain-specific facts (e.g. scan connection sweep, source scanner authorization, and TCP handshake completion for NETWORK_SCAN).",
    gateDependencies: ["G2"],
    exampleSnippet:
      "Behavioral Archetype: Network Scan & Host Reconnaissance (NETWORK_SCAN) — Verify sequential connection attempts across destination hosts on fixed destination port and confirm source scanner authorization.",
  },
  {
    sectionNumber: 3,
    sectionId: "DETECTION_CONDITIONS",
    title: "Detection Conditions & Pattern Logic",
    owner: "RuleIntelligenceAnalyzer",
    description: "Documents the SIEM data source, provenance, aggregation window, grouping keys, and authoritative threshold.",
    purposeInTriage:
      "Prevents the LLM from hallucinating rule thresholds by explicitly marking unverified thresholds as UNVERIFIED when SIEM XML is missing.",
    gateDependencies: ["G1"],
    exampleSnippet:
      "Authoritative Threshold: 50 (distinct destIpAddr) | Window: 300s | GroupBy: srcIpAddr,destPort | Provenance: AUTHORITATIVE_XML_IMPORT",
  },
  {
    sectionNumber: 4,
    sectionId: "REQUIRED_EVIDENCE",
    title: "Mandatory Evidence Gathering Checklist",
    owner: "EvidenceRequirementMapper",
    description: "Human-readable checklist mirroring the machine-verifiable RuleEvidenceContract.",
    purposeInTriage:
      "Aligns LLM reasoning with EvidencePreflightValidator so critical fields (e.g. security.event_type, event.timestamp, network.source_ip, network.destination_port) are explicitly checked.",
    gateDependencies: ["G3", "G7"],
    exampleSnippet:
      "CRITICAL CORE: security.event_type, event.timestamp, network.source_ip, network.destination_port | CONDITIONAL: scan.rate_per_second, scan.connection_count",
  },
  {
    sectionNumber: 5,
    sectionId: "TP_INDICATORS",
    title: "True Positive Indicators (Attack Evidence)",
    owner: "Policy Author / AIS 2.0 Generator",
    description: "Concrete, observable indicators required to substantiate a TRUE_POSITIVE decision.",
    purposeInTriage:
      "Prevents alert firing alone from being treated as proof of maliciousness (enforced together with Guardrail G7).",
    gateDependencies: ["G4", "G2"],
    exampleSnippet:
      "Sequential TCP SYN sweeps to sensitive services (22, 445, 3389) from an unauthorized source followed by lateral movement or exploit telemetry.",
  },
  {
    sectionNumber: 6,
    sectionId: "FP_INDICATORS",
    title: "False Positive Indicators (Benign Noise)",
    owner: "Policy Author / AIS 2.0 Generator",
    description: "Affirmative operational justification required to classify an alert as FALSE_POSITIVE.",
    purposeInTriage:
      "Requires verifiable scanner inventory match, approved change management ticket, or documented monitoring probe—enforced alongside Guardrail G6.",
    gateDependencies: ["G5"],
    exampleSnippet:
      "Authorized vulnerability scanner (Nessus, Qualys, Rapid7) operating from registered scanner IP with active maintenance/change ticket.",
  },
  {
    sectionNumber: 7,
    sectionId: "MISSING_INFO_CRITERIA",
    title: "When to Abstain (REQUIRES_ATTENTION)",
    owner: "Policy Author / AIS 2.0 Generator",
    description: "Explicit conditions under which the agent must abstain rather than guess TP or FP.",
    purposeInTriage:
      "Directs the model to return REQUIRES_ATTENTION and populate missing_evidence whenever core fields, scanner authorization, or thresholds are absent or conflicting.",
    gateDependencies: ["G6"],
    exampleSnippet:
      "Abstain and vote REQUIRES_ATTENTION if network.source_ip, destination port, connection count, or source scanner authorization cannot be verified.",
  },
  {
    sectionNumber: 8,
    sectionId: "ESCALATION_CONDITIONS",
    title: "P1/P2 Escalation Conditions",
    owner: "Policy Author / AIS 2.0 Generator",
    description: "Defines severity-based incident response triggers requiring immediate Tier-2 or IR escalation.",
    purposeInTriage:
      "Flags high-impact indicators (e.g. scan targeting Domain Controllers with completed sessions or internal host post-compromise behavior) for human escalation.",
    gateDependencies: ["G6"],
    exampleSnippet:
      "Escalate to SOC Tier 2 / IR if scanning originates from a non-scanner internal host and establishes completed sessions to Domain Controllers or databases.",
  },
  {
    sectionNumber: 9,
    sectionId: "ANALYST_QUESTIONS",
    title: "Standard Investigative Q&A Checklist",
    owner: "Policy Author / AIS 2.0 Generator",
    description: "Ordered list of domain-specific follow-up questions surfaced when incidents enter human review.",
    purposeInTriage:
      "Populates structured analyst_questions in AI verdicts and Human Review Queue investigations to accelerate Tier-2 resolution.",
    gateDependencies: ["G2", "G6"],
    exampleSnippet:
      "Is the source IP registered in corporate asset inventory as an authorized vulnerability scanner with an approved change ticket for this window?",
  },
];

export const ARCHETYPE_SPOTLIGHT = {
  totalRegisteredEnumEntries: 18,
  networkScan: {
    archetypeId: "NETWORK_SCAN",
    name: "Network Scan & Host Reconnaissance",
    registryVersion: "v2.0.0",
    purpose: "Detection of network port scanning, horizontal host reconnaissance, and unauthorized network sweeps.",
    matchedRulesExamples: [
      "PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT (Heavy TCP Host Scan On Fixed Port)",
      "Inbound TCP Port Sweep Across Subnets",
      "Remote System Discovery (T1018 / T1595)",
    ],
    mandatoryCoreFields: [
      "security.event_type",
      "event.timestamp",
      "network.source_ip",
      "network.destination_port",
    ],
    conditionalFields: [
      "network.destination_ip",
      "network.destination_ip_list",
      "network.protocol",
      "scan.rate_per_second",
      "scan.connection_count",
      "network.tcp_flags",
    ],
    optionalEnrichmentFields: ["geo.source_country", "network.bytes_out", "network.bytes_in", "endpoint.hostname"],
    unsupportedFields: [
      "file.hash_sha256",
      "process.name",
      "process.command_line",
      "process.parent_name",
      "registry.key_path",
    ],
  },
  allArchetypes: [
    "NETWORK_SCAN",
    "NETWORK_EXFILTRATION",
    "NETWORK_CONNECTION",
    "MALWARE_EXECUTION",
    "PROCESS_EXECUTION",
    "FILE_MALWARE",
    "AUTHENTICATION",
    "BRUTE_FORCE",
    "CREDENTIAL_ACCESS",
    "LATERAL_MOVEMENT",
    "DNS_TUNNELING",
    "WEB_ATTACK",
    "PRIVILEGE_ESCALATION",
    "CLOUD_DATA_ACCESS",
    "POLICY_VIOLATION",
    "ENDPOINT_DEFENSE_EVASION",
    "GENERIC",
    "UNKNOWN",
  ],
};

export const HEAVY_TCP_V1_VS_V2_COMPARISON = {
  ruleName: "Heavy TCP Host Scan On Fixed Port",
  ruleIdentifier: "PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
  rows: [
    {
      dimension: "Policy Version Status",
      v1: "Version 1 — Flawed Legacy (ARCHIVED / REWORK_REQUIRED)",
      v2: "Version 2 — Remediated Candidate (DRAFT / APPROVAL_ELIGIBLE)",
      improved: true,
    },
    {
      dimension: "G1: Rule Integrity",
      v1: "PASSED (20.0 / 20.0) after XML import",
      v2: "PASSED (20.0 / 20.0) authoritative XML preserved",
      improved: false,
    },
    {
      dimension: "G2: Archetype Relevance",
      v1: "WARNING (10.0 / 20.0) when unclassified; PASSED once NETWORK_SCAN bound",
      v2: "PASSED (20.0 / 20.0) with NETWORK_SCAN / WARNING (10.0) if unclassified",
      improved: true,
    },
    {
      dimension: "G5: FP Criteria & Safety",
      v1: "FAILED (0.0 / 10.0) — Hardcoded 80–98% confidence + blanket RFC-1918 / 127.0.0.1 benign assumption",
      v2: "PASSED (10.0 / 10.0) — Requires verified vulnerability scanner & active change ticket",
      improved: true,
    },
    {
      dimension: "G7: Contract Consistency",
      v1: "WARNING (9.0 / 10.0) — Missing critical field security.event_type in Section 4",
      v2: "PASSED (10.0 / 10.0) — Explicitly includes security.event_type & event.timestamp",
      improved: true,
    },
    {
      dimension: "G8: Empirical Simulation",
      v1: "WARNING (0.0 / 15.0) — INSUFFICIENT_DATA (N < 5 verified rule-matched cases)",
      v2: "WARNING (0.0 / 15.0) — INSUFFICIENT_DATA preserved honestly (never fabricated)",
      improved: false,
    },
    {
      dimension: "Structural Quality (G1–G7)",
      v1: "75.3 / 100 (or 81.2% prior baseline)",
      v2: "88.2 / 100 (or 100.0% when NETWORK_SCAN verified)",
      improved: true,
    },
    {
      dimension: "Approval Eligibility",
      v1: "FALSE (BLOCKED by G5 hard-gate failure)",
      v2: "TRUE (Zero G1–G7 blockers; G8 remains INSUFFICIENT_DATA warning)",
      improved: true,
    },
  ],
};

export const SIMULATION_FUNNEL_STAGES = [
  {
    stage: 1,
    name: "Total Scanned",
    description: "All historical incidents retrieved from the evaluation pool.",
  },
  {
    stage: 2,
    name: "Rule Matched",
    description: "Incidents strictly matching the target rule_id (non-matching rules excluded with RULE_MISMATCH).",
  },
  {
    stage: 3,
    name: "Analyst Labeled",
    description: "Rule-matched incidents possessing a recorded SIEM resolution or ground-truth entry.",
  },
  {
    stage: 4,
    name: "Eligible Ground Truth",
    description: "Independently verified human TP or FP benchmark controls (minimum N >= 5 required for Gate G8).",
  },
  {
    stage: 5,
    name: "Excluded (Auditable)",
    description: "Excluded with explicit code: RULE_MISMATCH, HEURISTIC_OR_ML_LABEL, MISSING_ANALYST_LABEL, AMBIGUOUS_LABEL, or CORRUPT_OR_EMPTY_PAYLOAD.",
  },
  {
    stage: 6,
    name: "Evaluated",
    description: "Sanitized incidents replayed through the compiled policy, guardrails, and trustworthiness scorer.",
  },
];

export const EVIDENCE_SUFFICIENCY_DIMENSIONS = [
  {
    name: "Required Evidence Coverage",
    weight: "40%",
    description: "Checks presence of critical core fields mapped by the active RuleEvidenceContract (with canonical alias awareness).",
  },
  {
    name: "Evidence Integrity & Provenance",
    weight: "25%",
    description: "Weights reliability by telemetry source (EDR_AGENT 1.0, FIREWALL_FLOW 0.95, SYSLOG_APPLIANCE 0.85, SIEM_ALERT_METADATA 0.70, SYNTHESIZED_FALLBACK 0.40).",
  },
  {
    name: "Internal Consistency & Corroboration",
    weight: "20%",
    description: "Penalizes single-sensor uncorroborated logs (-3 pts) and material contradictions such as >1000x byte-count divergences or inbound exfiltration (-10 pts).",
  },
  {
    name: "Freshness & Incident Relevance",
    weight: "15%",
    description: "Verifies epoch timestamps exist and penalizes stale correlation windows spanning > 30 days.",
  },
];

export const TRUSTWORTHINESS_DIMENSIONS = [
  {
    name: "Direct Claim-to-Evidence Support",
    maxPoints: 35,
    description: "Measures grounding_ratio of LLM assertions against actual telemetry; deducts 10 pts for unsupported assertions.",
  },
  {
    name: "Evidence Source Reliability",
    maxPoints: 20,
    description: "Scaled from Evidence Sufficiency provenance integrity score (EDR/Firewall flows score higher than fallback metadata).",
  },
  {
    name: "Contradiction & Counterevidence Handling",
    maxPoints: 15,
    description: "Deducts points when telemetry conflicts or model contradicts facts; grants +5 pts honest-acknowledgement credit if model flags conflict.",
  },
  {
    name: "Independent Corroboration",
    maxPoints: 15,
    description: "Scaled from multi-sensor corroboration and consistency across event sources.",
  },
  {
    name: "Historical Empirical Validation Support",
    maxPoints: 15,
    description: "CALIBRATED (N >= 30 & acc >= 70%): up to 15 pts; PARTIALLY_VALIDATED (N >= 5): up to 10 pts; UNCALIBRATED (N < 5): baseline 5 pts.",
  },
];

export const TRUST_SCORE_BANDS = [
  { range: "1–2", raw: "< 30 pts", label: "Very Weak", decisionRule: "Always REQUIRES_ANALYST_ATTENTION" },
  { range: "3–4", raw: "30–49 pts", label: "Weak / Substantially Uncertain", decisionRule: "Always REQUIRES_ANALYST_ATTENTION (Missing mandatory evidence caps score <= 3/10)" },
  { range: "5–6", raw: "50–69 pts", label: "Partial Support / Uncalibrated Cap", decisionRule: "Always REQUIRES_ANALYST_ATTENTION (Uncalibrated rules N < 30 are strictly capped <= 6/10)" },
  { range: "7–8", raw: "70–89 pts", label: "Strong Support", decisionRule: "Eligible for automated TP/FP ONLY if calibrated & all safety guardrails G1–G7 pass" },
  { range: "9", raw: "90–97 pts", label: "Very Strong Corroborated Support", decisionRule: "Eligible for automated TP/FP when calibrated & guardrails pass" },
  { range: "10", raw: "98–100 pts", label: "Exceptional Independently Validated", decisionRule: "Rare — requires is_calibrated=True and sample_count >= 30" },
];

export const DETERMINISTIC_GUARDRAILS = [
  {
    code: "G1_MANDATORY_EVIDENCE_MISSING",
    trigger: "Any critical mandatory field from the RuleEvidenceContract is absent.",
    effect: "Forces REQUIRES_ANALYST_ATTENTION and caps Trust Score <= 3/10.",
  },
  {
    code: "G2_MATERIAL_CONTRADICTIONS_DETECTED",
    trigger: "Evidence status is CONFLICTING or model claims contradict telemetry (e.g. Process Blocked=True vs unhindered breach).",
    effect: "Forces REQUIRES_ANALYST_ATTENTION and caps Trust Score <= 3/10.",
  },
  {
    code: "G2_G3_UNSUPPORTED_OR_HALLUCINATED_CLAIMS",
    trigger: "Model cites fabricated IPs, hashes, or unverified thresholds when proposing TP or FP.",
    effect: "Rejects decisive proposal and routes to REQUIRES_ANALYST_ATTENTION.",
  },
  {
    code: "G4_INCOMPLETE_DETECTION_SEMANTICS",
    trigger: "Rule definition_status is INCOMPLETE without authoritative threshold on threshold-dependent rules.",
    effect: "Provisional policy cannot auto-classify; routes to REQUIRES_ANALYST_ATTENTION.",
  },
  {
    code: "G5_LOW_TRUST_SCORE",
    trigger: "Ordinal Trust Score < 7/10 (or raw trust < 70.0), including all uncalibrated rules capped at 6/10.",
    effect: "Blocks automated TP/FP and escalates to REQUIRES_ANALYST_ATTENTION.",
  },
  {
    code: "G6_NEGATIVE_FP_PROHIBITION",
    trigger: "Model proposes FALSE_POSITIVE without affirmative, grounded evidence of business authorization (e.g. verified scanner, approved maintenance, backup).",
    effect: "Refuses blanket RFC-1918 / 'no malware seen' FP; routes to REQUIRES_ANALYST_ATTENTION.",
  },
  {
    code: "G7_ALERT_FIRING_ALONE",
    trigger: "Model proposes TRUE_POSITIVE without at least one concrete grounded OBSERVED_FACT indicator.",
    effect: "Prevents circular 'rule fired so it is TP' decisions; routes to REQUIRES_ANALYST_ATTENTION.",
  },
];
