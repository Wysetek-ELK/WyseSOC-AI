import type { GlossaryEntry, GuidedTourStop, TroubleshootingScenario } from "./types";

export const GLOSSARY_ENTRIES: GlossaryEntry[] = [
  {
    id: "abstention",
    term: "Abstention (REQUIRES_ANALYST_ATTENTION)",
    aliases: ["REQUIRES_ATTENTION", "REQUIRES_ANALYST_ATTENTION", "Abstain"],
    category: "Decision & Trust",
    definition:
      "A first-class safe decision emitted whenever critical evidence is missing, telemetry conflicts, claims fail grounding, business authorization is unverified, policy is unapproved, or Trust Score is below 7/10. Abstention routes the incident to Tier-2 human review instead of guessing TP or FP.",
    codeReference: "UserVisibleVerdict.REQUIRES_ANALYST_ATTENTION · VerdictGuardrailsEngine",
    relatedTerms: ["Infallible Rule", "Guardrail G6"],
  },
  {
    id: "evidence-contract",
    term: "Evidence Contract",
    aliases: ["RuleEvidenceContract"],
    category: "AIS 2.0 & Gates",
    definition:
      "A machine-verifiable specification bound to a rule and PromptVersion listing CORE critical fields, conditional fields, optional enrichments, and unsupported fields. Only APPROVED policy versions produce APPROVED contracts.",
    codeReference: "RuleEvidenceContract · EvidenceContractService",
    relatedTerms: ["Detection Archetype", "Evidence Sufficiency"],
  },
  {
    id: "detection-archetype",
    term: "Detection Archetype",
    aliases: ["ArchetypeId", "NETWORK_SCAN"],
    category: "AIS 2.0 & Gates",
    definition:
      "A versioned behavioral classification (such as NETWORK_SCAN, NETWORK_EXFILTRATION, PROCESS_EXECUTION, or FILE_MALWARE) assigned by DetectionArchetypeRegistry so investigation policies and contracts demand telemetry appropriate to that attack domain.",
    codeReference: "DetectionArchetypeRegistry · ArchetypeId",
    relatedTerms: ["Evidence Contract", "Gate G2"],
  },
  {
    id: "structural-quality-score",
    term: "Structural Quality Score (G1–G7)",
    aliases: ["structural_quality_score"],
    category: "AIS 2.0 & Gates",
    definition:
      "Measures policy design integrity across Gates G1–G7 (85 raw points scaled to 0–100). Structural quality verifies rule fidelity, archetype alignment, contract mapping, and safety wording—it does NOT measure empirical accuracy on live or historical incidents.",
    codeReference: "PolicyQualityValidator.structural_quality_score",
    relatedTerms: ["Gate G8 (Empirical Simulation)", "Hard Gate Failure"],
  },
  {
    id: "hard-gate-failure",
    term: "Hard Gate Failure",
    aliases: ["approval_eligible", "Blocking Issue"],
    category: "AIS 2.0 & Gates",
    definition:
      "Critical policy defect (such as an invented threshold in G1, archetype mismatch in G2, missing core evidence in G3, or blanket RFC-1918 benign rule / hardcoded confidence range in G5). Strictly sets approval_eligible = FALSE regardless of numeric score.",
    codeReference: "PolicyQualityValidator (len(blocking_issues) == 0)",
    relatedTerms: ["Structural Quality Score (G1–G7)"],
  },
  {
    id: "evidence-sufficiency",
    term: "Evidence Sufficiency Score",
    aliases: ["Evidence Confidence", "EvidenceSufficiencyEngine"],
    category: "Decision & Trust",
    definition:
      "Four-dimensional deterministic telemetry audit: Required Coverage (40%), Integrity & Provenance (25%), Consistency & Corroboration (20%), and Freshness & Relevance (15%). Governed by the Infallible Rule.",
    codeReference: "EvidenceSufficiencyEngine.evaluate_incident_sufficiency",
    relatedTerms: ["Infallible Rule", "Trust Score"],
  },
  {
    id: "infallible-rule",
    term: "Infallible Rule",
    aliases: ["Sufficiency Cap"],
    category: "Decision & Trust",
    definition:
      "Safety invariant in EvidenceSufficiencyEngine guaranteeing that a high weighted score never overrides a missing mandatory field or material telemetry contradiction: overall sufficiency is capped <= 49.0, status becomes INSUFFICIENT or CONFLICTING, and automated TP/FP is blocked.",
    codeReference: "EvidenceSufficiencyEngine (lines 265–273)",
    relatedTerms: ["Evidence Sufficiency Score", "Abstention (REQUIRES_ANALYST_ATTENTION)"],
  },
  {
    id: "trust-score",
    term: "Verdict Trust Score (1–10 Ordinal)",
    aliases: ["Observed Trustworthiness Score", "Trustworthiness Engine"],
    category: "Decision & Trust",
    definition:
      "Explainable 1–10 ordinal score computed from 5 transparent dimensions totaling 100 raw points (Claim Support 35, Source Reliability 20, Contradiction Handling 15, Corroboration 15, Historical Validation 15). Capped <= 6/10 if uncalibrated (N < 30), capped <= 3/10 if mandatory evidence is missing/conflicting, or NOT_CALCULABLE when telemetry is empty.",
    codeReference: "VerdictTrustworthinessEngine (v2.2.0)",
    relatedTerms: ["Calibration", "Abstention (REQUIRES_ANALYST_ATTENTION)"],
  },
  {
    id: "raw-llm-confidence",
    term: "Raw LLM Confidence vs Calibrated Probability",
    aliases: ["raw_model_confidence", "Calibration"],
    category: "Empirical & Stats",
    definition:
      "The 0–100 confidence number emitted by Local LLM is an uncalibrated subjective score, NOT a statistical probability. Calibrated reliability metrics (Brier Score & 5-bin ECE) are reported only after N >= 30 verified balanced TP/FP evaluations (>= 3 each).",
    codeReference: "CalibrationEvaluator (MIN_CALIBRATION_SAMPLES = 30)",
    relatedTerms: ["Brier Score & ECE", "Verdict Trust Score (1–10 Ordinal)"],
  },
  {
    id: "brier-ece",
    term: "Brier Score & ECE (Expected Calibration Error)",
    aliases: ["Brier Score", "ECE"],
    category: "Empirical & Stats",
    definition:
      "Calibration metrics computed across 5 ordinal Trust Score bins (1–2, 3–4, 5–6, 7–8, 9–10). Reported as N/A when sample_count < 30 or class balance < 3 TP and < 3 FP so uncalibrated noise is never disguised as precision.",
    codeReference: "CalibrationEvaluator.evaluate_calibration",
    relatedTerms: ["Raw LLM Confidence vs Calibrated Probability"],
  },
  {
    id: "gate-g8",
    term: "Gate G8 (Empirical Historical Simulation)",
    aliases: ["G8", "INSUFFICIENT_DATA", "Historical Simulation"],
    category: "Empirical & Stats",
    definition:
      "Evaluates candidate policy performance against frozen, rule-matched human-verified historical incidents via a 6-stage eligibility funnel. Requires N >= 5 eligible verified cases and zero critical regressions; otherwise reports INSUFFICIENT_DATA (0/15 pts).",
    codeReference: "PolicyQualityValidator._evaluate_gate_8_simulation · PolicySimulationService",
    relatedTerms: ["Structural Quality Score (G1–G7)", "Eligibility Funnel"],
  },
  {
    id: "eligibility-funnel",
    term: "6-Stage Historical Eligibility Funnel",
    aliases: ["Funnel", "RULE_MISMATCH", "HEURISTIC_OR_ML_LABEL"],
    category: "Empirical & Stats",
    definition:
      "Auditable filtering pipeline in PolicySimulationService: Total Scanned → Rule Matched → Analyst Labeled → Eligible Ground Truth → Excluded → Evaluated. Excludes mismatched rules and automated/ML closures so ground truth remains pure.",
    codeReference: "PolicySimulationService.run_dry_run_intelligence_evaluation",
    relatedTerms: ["Gate G8 (Empirical Simulation)", "Ground-Truth Provenance"],
  },
  {
    id: "ground-truth-provenance",
    term: "Ground-Truth Provenance",
    aliases: ["HistoricalGroundTruth", "is_ml_generated", "clearedUser"],
    category: "Empirical & Stats",
    definition:
      "Metadata auditing who closed a SIEM incident and why (resolution, clearedUser, clearedReason, comments, is_ml_generated). ML-set resolutions or closure-only statuses without explicit human TP/FP disposition are adjudicated UNVERIFIED.",
    codeReference: "HistoricalGroundTruthValidator.adjudicate_label",
    relatedTerms: ["Eligibility Funnel", "Blind Review Mode"],
  },
  {
    id: "wilson-ci",
    term: "Wilson 95% Confidence Interval",
    aliases: ["Wilson CI"],
    category: "Empirical & Stats",
    definition:
      "Binomial confidence interval computed for Precision, Recall, and Specificity that remains statistically honest for small sample sizes (N < 30) without degenerate zero-width intervals.",
    codeReference: "EmpiricalAccuracyEvaluator.calculate_wilson_ci",
    relatedTerms: ["Gate G8 (Empirical Simulation)"],
  },
  {
    id: "mcnemar-test",
    term: "McNemar Paired Regression Test",
    aliases: ["McNemar Test", "REGRESSION_DETECTED"],
    category: "Empirical & Stats",
    definition:
      "Statistical comparison run on paired baseline vs candidate evaluations over identical verified historical incidents to detect significant accuracy regressions and critical false negatives.",
    codeReference: "PolicySimulationService · RegressionComparisonReport",
    relatedTerms: ["Gate G8 (Empirical Simulation)"],
  },
  {
    id: "blind-review",
    term: "Blind Review Mode",
    aliases: ["blindReviewMode"],
    category: "Operations",
    definition:
      "Safeguard toggle in the platform Header that suppresses historical SIEM ground-truth resolutions during investigation so SOC analysts adjudicate evidence neutrally without confirmation bias.",
    codeReference: "Header.tsx · AppContext · getIncidentDetail(blind_review=true)",
    relatedTerms: ["Ground-Truth Provenance"],
  },
  {
    id: "policy-drift",
    term: "Policy Drift Event",
    aliases: ["PolicyDriftEvent", "REVIEW_REQUIRED"],
    category: "Operations",
    definition:
      "Audit event emitted by PolicyLifecycleMonitor when SIEM rule pattern logic, severity, metadata, or diverged analyst feedback changes upstream assumptions. Marks active policies REVIEW_REQUIRED without silently overwriting them.",
    codeReference: "PolicyLifecycleMonitor",
    relatedTerms: ["Compiled Policy"],
  },
  {
    id: "compiled-policy",
    term: "Compiled Nine-Section Policy",
    aliases: ["PolicyCompilerService", "compilation_digest"],
    category: "Architecture",
    definition:
      "Deterministic prompt specification compiled from Sections 1–9 of an APPROVED PromptVersion with a SHA-256 compilation_digest, guaranteeing 100% parity between Live Triage and Simulation Lab.",
    codeReference: "PolicyCompilerService.compile_policy (v3.0.0)",
    relatedTerms: ["Evidence Contract", "Policy Drift Event"],
  },
];

export const TROUBLESHOOTING_SCENARIOS: TroubleshootingScenario[] = [
  {
    id: "ts-high-quality-g8-insufficient",
    question: "Why can Quality Score be high (or Structural Quality 88–100/100) while G8 is INSUFFICIENT_DATA?",
    category: "Policy & Gates",
    shortAnswer:
      "Structural policy quality (Gates G1–G7, up to 85 raw pts scaled to 0–100) measures how well the policy is written and aligned with the rule & Evidence Contract. Gate G8 (15 pts) measures empirical accuracy on >= 5 verified rule-matched historical incidents. Clean drafting does not invent missing historical data.",
    rootCauses: [
      "A remediated policy (e.g. Heavy TCP Host Scan V2) passed G1–G7 with zero blockers, yielding high structural_quality_score.",
      "Fewer than 5 verified human-labeled TP/FP incidents matching that exact rule exist in HistoricalGroundTruth.",
      "Existing historical closures may belong to other rules (excluded as RULE_MISMATCH) or carry ML/automated labels (excluded as HEURISTIC_OR_ML_LABEL).",
    ],
    howSystemBehaves: [
      "PolicyQualityValidator separates structural_quality_score (G1–G7) from empirical_validation_score (G8).",
      "Gate G8 honestly sets simulation_status = 'INSUFFICIENT_DATA' and awards 0.0 / 15.0 pts with a WARNING instead of blocking structural validation or faking sample metrics.",
    ],
    adminResolutionSteps: [
      "Open Telemetry Hub and synchronize genuine historical incidents for the target rule.",
      "Review and verify >= 5 human TP/FP outcomes in Human Review Queue with explicit rationale.",
      "Re-run Simulation Lab in Agent Intelligence Studio to update Gate G8.",
    ],
    relatedRoute: "/agent-intelligence-studio",
    relatedRouteLabel: "Open Agent Intelligence Studio",
  },
  {
    id: "ts-fp-gets-abstain",
    question: "Why may an incident labeled False Positive (FP) in SIEM receive an AI abstention (REQUIRES_ANALYST_ATTENTION)?",
    category: "Verdict & Trust",
    shortAnswer:
      "During triage, the AI cannot see the historical SIEM resolution (zero-leakage isolation) and is forbidden from guessing False Positive without complete critical evidence and affirmative authorization proof.",
    rootCauses: [
      "build_model_facing_payload and HistoricalGroundTruthValidator strip resolution, clearedUser, and closure comments prior to inference.",
      "Critical contract evidence (e.g. network.destination_port, scan metadata, or affirmative scanner authorization / change ticket) is missing from raw telemetry.",
      "Guardrail G6 strictly prohibits classifying an event as FALSE_POSITIVE merely because it uses RFC-1918 internal IPs or lacks malware artifacts.",
      "Uncalibrated rules (N < 30) cap Trust Score <= 6/10, and missing mandatory evidence caps Trust Score <= 3/10 (below the 7/10 automated decision threshold).",
    ],
    howSystemBehaves: [
      "Deterministic guardrails override any speculative FP guess and output REQUIRES_ANALYST_ATTENTION with a low Trust Score (e.g. 3/10 for Incident 165233).",
      "The abstention surfaces missing evidence and targeted questions for Tier-2 verification.",
    ],
    adminResolutionSteps: [
      "Inspect the incident's missing_evidence and escalation_reason in AI Triage Workbench or Verdict Intelligence.",
      "Check whether SIEM/enrichment payloads include scanner inventory or authorization fields.",
      "Verify the SIEM FP closure provenance (analyst identity & rationale) in Human Review Queue before counting it toward ground truth.",
    ],
    relatedRoute: "/human-review-queue",
    relatedRouteLabel: "Open Human Review Queue",
  },
  {
    id: "ts-zero-labels-empirical",
    question: "Why does zero verified labels prevent empirical accuracy calculation?",
    category: "Simulation & Metrics",
    shortAnswer:
      "Precision, Recall, Specificity, and Overall Accuracy require dividing by verified True Positive and False Positive counts. With zero verified labels, denominators are zero—so the platform refuses to fabricate 0% or guessed percentages and reports N/A / INSUFFICIENT_DATA.",
    rootCauses: [
      "No historical incidents match the rule, OR existing closures are marked UNVERIFIED (ML-generated, closure-only status like 'Closed' / 'Manually Cleared' without TP/FP disposition, or missing rationale).",
      "EmpiricalAccuracyEvaluator only counts VERIFIED_TP and VERIFIED_FP labels toward confusion matrix cells (TP, FP, TN, FN).",
    ],
    howSystemBehaves: [
      "EmpiricalAccuracyEvaluator returns None (rendered as N/A in UI) for undefined precision, recall, specificity, balanced accuracy, and F1.",
      "PolicySimulationService sets empirical_validation_status = 'INSUFFICIENT_DATA' and displays stage-by-stage funnel exclusion counts.",
    ],
    adminResolutionSteps: [
      "Inspect Stage 5 (Excluded Incidents) in AIS Simulation Lab to see exact exclusion codes (HEURISTIC_OR_ML_LABEL, MISSING_ANALYST_LABEL, RULE_MISMATCH).",
      "Synchronize explicit analyst-verified resolutions from FortiSIEM or adjudicate incidents in Human Review Queue.",
    ],
    relatedRoute: "/verdict-intelligence",
    relatedRouteLabel: "Open Verdict Intelligence",
  },
  {
    id: "ts-missing-evidence-lowers-trust",
    question: "Why does missing critical evidence lower Trustworthiness (capping at <= 3/10)?",
    category: "Verdict & Trust",
    shortAnswer:
      "Under the Infallible Rule in EvidenceSufficiencyEngine and the Trust Score cap in VerdictTrustworthinessEngine, missing mandatory Evidence Contract fields prevent a reliable decision regardless of how confident the LLM sounds.",
    rootCauses: [
      "One or more fields marked critical=True in the rule's RuleEvidenceContract are absent from raw payload, nested events, and canonical evidence.",
      "Direct telemetry contradictions (such as divergent byte counts or direction conflicts) produce status CONFLICTING.",
    ],
    howSystemBehaves: [
      "EvidenceSufficiencyEngine caps overall_sufficiency_score <= 49.0 and sets evidence_status = 'INSUFFICIENT'.",
      "VerdictTrustworthinessEngine enforces ordinal_score = min(3, ordinal_score) (or NOT_CALCULABLE if telemetry is totally absent).",
      "VerdictGuardrailsEngine triggers G1_MANDATORY_EVIDENCE_MISSING or G5_LOW_TRUST_SCORE, forcing REQUIRES_ANALYST_ATTENTION.",
    ],
    adminResolutionSteps: [
      "Compare the missing_evidence list against the rule's Evidence Contract in Agent Intelligence Studio Tab 4.",
      "Ensure FortiSIEM / upstream event parsers populate the missing attributes or reclassify non-essential enrichments from CORE to CONDITIONAL.",
    ],
    relatedRoute: "/agent-intelligence-studio",
    relatedRouteLabel: "Inspect Evidence Contracts",
  },
  {
    id: "ts-v1-vs-v2-different-results",
    question: "Why do an approved Version 1 and a draft Version 2 produce different validation results?",
    category: "Policy & Gates",
    shortAnswer:
      "Quality assessment is bound deterministically to the specific PromptVersion's 9 sections, its bound RuleEvidenceContract, and the current Rule semantics/archetype—tracked by SHA-256 digests (policy_digest, contract_digest, rule_digest).",
    rootCauses: [
      "V1 may retain legacy flaws such as hardcoded confidence ranges (80–98%) or blanket RFC-1918 benign rules (failing Gate G5) or missing Section 4 contract fields (warning on Gate G7).",
      "V2 remediates those sections using the updated NETWORK_SCAN archetype and Evidence Contract, raising structural quality and clearing G5/G7 blockers.",
      "Conversely, if authoritative SIEM rule XML was imported or archetype registry updated after V1 was approved, V1 and V2 are validated against different digest states.",
    ],
    howSystemBehaves: [
      "AIS 2.0 stores V1 and V2 as separate immutable PromptVersion rows without automatically overwriting V1.",
      "Quality cards compute exact per-version gate statuses, scores, and SHA-256 digests so admins can inspect before/after remediation side by side.",
    ],
    adminResolutionSteps: [
      "Open the rule in Agent Intelligence Studio and select V1 vs V2 in the version selector.",
      "Compare Gate G1–G8 findings and verify V2 has zero blockers before an Administrator promotes V2 to APPROVED.",
    ],
    relatedRoute: "/agent-intelligence-studio",
    relatedRouteLabel: "Compare Versions in AIS",
  },
  {
    id: "ts-llm-offline-deferred",
    question: "Why does AI triage defer or refuse evaluation when Server 2 Local LLM is offline?",
    category: "Operations",
    shortAnswer:
      "In live/production execution, VerdictTriageAgent checks Local LLM reachability and GPU circuit breaker state and refuses to fabricate simulated verdicts when Server 2 is unavailable.",
    rootCauses: [
      "Server 2 GPU endpoint is unreachable, timed out, or GPUServerCircuitBreaker tripped OPEN after consecutive inference failures.",
      "Production mode sets LOCAL_LLM_ALLOW_MOCK_FALLBACK=false so synthetic simulator outputs cannot masquerade as live AI decisions.",
    ],
    howSystemBehaves: [
      "Raises LocalLLMUnavailableError; pending incidents remain queued safely without bogus TP/FP tags.",
      "Once Server 2 recovers, Inference Control / Telemetry Hub can process pending verdicts.",
    ],
    adminResolutionSteps: [
      "Check Server 2 GPU status and circuit breaker state in Inference Control.",
      "Verify host/port/model configuration in Agent Configuration and run Test Connection.",
    ],
    relatedRoute: "/inference-control",
    relatedRouteLabel: "Open Inference Control",
  },
];

export const GUIDED_TOUR_STOPS: GuidedTourStop[] = [
  {
    stopNumber: 1,
    id: "tour-overview",
    title: "1. Platform Architecture at a Glance",
    subtitle: "Two distinct planes joined by strict governance bridges",
    targetMode: "architecture",
    estimatedMinutes: "2 min",
    keyTakeaways: [
      "Policy Creation & Governance (AIS 2.0) runs offline/control-plane to turn SIEM rules into validated 9-section policies and Evidence Contracts.",
      "Runtime Incident Investigation runs strictly under APPROVED policies, Evidence Sufficiency checks, Local LLM reasoning, and deterministic guardrails.",
      "SOC analyst feedback feeds Agent Memory & Calibration Monitoring—never silently overwriting live production policies.",
    ],
    narrative:
      "Start with the full animated End-to-End Architecture Diagram to see how all 17 stages connect across FortiSIEM ingestion, Agent Intelligence Studio 2.0, Verdict Triage Agent, Human Review Queue, and Calibration Monitoring.",
    actionLabel: "Open Interactive Architecture Flow",
  },
  {
    stopNumber: 2,
    id: "tour-ais-lifecycle",
    title: "2. Agent Intelligence Studio 2.0 & Quality Gates G1–G8",
    subtitle: "How rules become audited, archetype-aware investigation policies",
    targetMode: "policy-lifecycle",
    estimatedMinutes: "3 min",
    keyTakeaways: [
      "RuleIntelligenceAnalyzer separates authoritative SIEM XML correlation logic from runtime incident counters like incidentCount.",
      "DetectionArchetypeRegistry assigns domains like NETWORK_SCAN so policies never demand irrelevant endpoint hashes for network scans.",
      "Structural Quality (G1–G7) is strictly separated from Empirical Validation (G8): a clean policy can still report G8 INSUFFICIENT_DATA.",
    ],
    narrative:
      "Explore the 8-stage AIS 2.0 lifecycle, inspect the 9-section policy specification, and audit every Gate G1–G8 pass condition, blocker, and remediation rule.",
    actionLabel: "Explore Policy Lifecycle & Gates G1–G8",
  },
  {
    stopNumber: 3,
    id: "tour-decision-engine",
    title: "3. AI Verdict Decision Engine, Evidence Confidence & Trustworthiness",
    subtitle: "Why abstention is a first-class safety control",
    targetMode: "decision-engine",
    estimatedMinutes: "3 min",
    keyTakeaways: [
      "Three authoritative verdicts exist: TRUE_POSITIVE, FALSE_POSITIVE, and REQUIRES_ANALYST_ATTENTION.",
      "The Infallible Rule caps Evidence Sufficiency <= 49.0 when mandatory contract fields are missing or contradictory.",
      "VerdictTrustworthinessEngine scores 5 transparent dimensions on a 1–10 ordinal scale and refuses automated TP/FP below 7/10 or without calibration.",
    ],
    narrative:
      "Step through the animated Decision Engine workflow from New Incident to Final Decision and see how Guardrails G1–G7 prevent ungrounded TP or blanket RFC-1918 FP classifications.",
    actionLabel: "Animate Decision Engine Flow",
  },
  {
    stopNumber: 4,
    id: "tour-incident-165233",
    title: "4. Real-World Case Study: Incident 165233 (Heavy TCP Host Scan)",
    subtitle: "Walking through SIEM False Positive vs AI Abstention (3/10 Trust)",
    targetMode: "incident-walkthrough",
    estimatedMinutes: "2 min",
    keyTakeaways: [
      "AI emitted REQUIRES_ANALYST_ATTENTION with Trustworthiness Score 3/10 rather than guessing TP or FP.",
      "Even though SIEM records 'False Positive', ground-truth provenance requires verification if analyst identity or rationale is missing.",
      "One labeled incident cannot establish empirical accuracy—Historical Simulation G8 remains INSUFFICIENT_DATA until N >= 5 verified cases.",
    ],
    narrative:
      "Follow Incident 165233 step by step through rule matching, contract validation, authorization gating, 3/10 Trust capping, and historical provenance comparison.",
    actionLabel: "Launch Incident 165233 Walkthrough",
  },
  {
    stopNumber: 5,
    id: "tour-admin-setup",
    title: "5. Admin Prerequisites & Operational Configuration",
    subtitle: "What administrators must verify across all 11 operational stages",
    targetMode: "requirements",
    estimatedMinutes: "2 min",
    keyTakeaways: [
      "Required integrations: FortiSIEM credentials, authoritative rule XML definitions, canonical evidence fields, Administrator approval RBAC, and Server 2 Local LLM.",
      "Statistical thresholds: N >= 5 verified human labels per rule for Gate G8 simulation; N >= 30 balanced labels for Calibration (Brier / ECE).",
      "Read-only status checks verify live reachability when authenticated without mutating any records.",
    ],
    narrative:
      "Review every Required, Conditional, and Optional prerequisite along with the exact consequence of any missing configuration.",
    actionLabel: "Inspect Admin Setup Checklist",
  },
  {
    stopNumber: 6,
    id: "tour-troubleshooting",
    title: "6. Glossary, Diagnostics & Troubleshooting",
    subtitle: "Answers to common operational and statistical edge cases",
    targetMode: "troubleshooting",
    estimatedMinutes: "2 min",
    keyTakeaways: [
      "Understand why N/A replaces 0% when denominators are zero.",
      "Diagnose V1 vs V2 policy differences using SHA-256 digests and gate blockers.",
      "Navigate directly to any operational workspace in AI Verdict.",
    ],
    narrative:
      "Search platform terminology, expand diagnostic troubleshooting scenarios, and jump straight to live admin workspaces.",
    actionLabel: "Open Glossary & Troubleshooting",
  },
];

export const PLATFORM_PAGE_LINKS = [
  { title: "Agent Mission Control", href: "/agent-mission-control", category: "SOC Operations", summary: "Executive SOC KPIs, verdict distribution, and live pipeline overview." },
  { title: "AI Triage Workbench", href: "/ai-triage-workbench", category: "SOC Operations", summary: "Inspect triaged incidents, canonical evidence, claims, and AI decisions." },
  { title: "Telemetry Hub", href: "/telemetry-hub", category: "SOC Operations", summary: "Configure SentinelIngestWorker, sync FortiSIEM incidents/resolutions, and import fixtures." },
  { title: "Human Review Queue", href: "/human-review-queue", category: "SOC Operations", summary: "Adjudicate REQUIRES_ANALYST_ATTENTION incidents with Blind Review safeguard." },
  { title: "Agent Intelligence Studio", href: "/agent-intelligence-studio", category: "Agent Intelligence", summary: "9-section policy authoring, SIEM semantics, Evidence Contracts, Gates G1–G8, and Simulation Lab." },
  { title: "Detection Intelligence", href: "/detection-intelligence", category: "Agent Intelligence", summary: "Registered FortiSIEM detection rules, correlation expressions, and compiled policies." },
  { title: "Agent Memory", href: "/agent-memory", category: "Agent Intelligence", summary: "Verified LearningRecords powering rule-scoped semantic RAG precedents." },
  { title: "Agent Simulation Lab", href: "/agent-simulation-lab", category: "Validation & Trust", summary: "Controlled dry-run replay benchmarking without production impact." },
  { title: "Verdict Intelligence", href: "/verdict-intelligence", category: "Validation & Trust", summary: "Trustworthiness 1–10 scores, empirical accuracy, Wilson CIs, calibration bins, and McNemar regression." },
  { title: "Inference Control", href: "/inference-control", category: "Platform Control", summary: "Server 1 CPU/RAM & Server 2 GPU VRAM, latency, and circuit-breaker telemetry." },
  { title: "Agent Configuration", href: "/agent-configuration", category: "Platform Control", summary: "FortiSIEM supervisor credentials, Local LLM Server 2 settings, and connection tests." },
  { title: "Governance & Access", href: "/governance-access", category: "Platform Control", summary: "RBAC user management (Administrator / SOC Analyst / Read-Only) and Audit Logs." },
];
