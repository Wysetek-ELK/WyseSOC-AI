import type { IncidentWalkthroughStep } from "./types";

export const INCIDENT_165233_METADATA = {
  incidentId: "165233",
  ruleName: "Heavy TCP Host Scan",
  ruleIdentifier: "PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
  archetype: "NETWORK_SCAN",
  siemResolution: "False Positive",
  historicalAiDecision: "REQUIRES_ANALYST_ATTENTION",
  observedTrustScore: "3/10",
  simulationStatus: "INSUFFICIENT_DATA",
  disclaimer:
    "Illustrative Case Study: Real observed identifiers (Incident 165233, Rule Heavy TCP Host Scan, SIEM Resolution False Positive, Historical AI Decision Requires Analyst Attention, Trustworthiness Score 3/10) are preserved exactly. Fields not available in documentation are shown as [ILLUSTRATIVE PLACEHOLDER] and never fabricated.",
};

export const INCIDENT_165233_STEPS: IncidentWalkthroughStep[] = [
  {
    stepNumber: 1,
    id: "inc-165233-rule-match",
    stageName: "1. Rule Matching & Policy Lookup",
    componentName: "VerdictTriageAgent & DetectionArchetypeRegistry",
    statusBadge: "MATCHED: NETWORK_SCAN",
    statusTone: "cyan",
    whatHappens:
      "Incident 165233 enters the triage pipeline and resolves to the rule 'Heavy TCP Host Scan' (PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT), classified under the NETWORK_SCAN detection archetype.",
    observedFacts: [
      "Incident ID: 165233",
      "Target Rule: Heavy TCP Host Scan",
      "Archetype: NETWORK_SCAN (requires security.event_type, event.timestamp, network.source_ip, network.destination_port)",
    ],
    illustrativePlaceholders: [
      "[ILLUSTRATIVE PLACEHOLDER] Policy state checked: Active APPROVED PromptVersion & bound RuleEvidenceContract for Heavy TCP Host Scan",
      "[ILLUSTRATIVE PLACEHOLDER] Raw SIEM alert payload fields (source IP, target host list, destination port) are stripped of any historical resolution tags before inference",
    ],
    guardrailOrScoreImpact:
      "Zero ground-truth leakage guaranteed: the SIEM's 'False Positive' resolution is completely stripped before model investigation.",
    takeaway:
      "The AI evaluates Incident 165233 strictly from available alert telemetry—never peeking at the SIEM closure label.",
  },
  {
    stepNumber: 2,
    id: "inc-165233-evidence-validation",
    stageName: "2. Evidence Extraction & Contract Validation",
    componentName: "EvidenceNormalizationService & EvidenceSufficiencyEngine",
    statusBadge: "EVIDENCE DEFICIENT / UNVERIFIED",
    statusTone: "amber",
    whatHappens:
      "Evidence Sufficiency and Preflight Validation inspect canonical telemetry against the NETWORK_SCAN contract (mandatory fields + affirmative authorization context).",
    observedFacts: [
      "Rule requires verifying scan source IP, destination port, connection pattern, and whether source is an authorized scanner or monitoring host",
      "Observed Trustworthiness Score in historical trace: 3/10 (consistent with the <= 3/10 mandatory-evidence/conflict cap)",
    ],
    illustrativePlaceholders: [
      "[ILLUSTRATIVE PLACEHOLDER] Canonical telemetry availability check: e.g., missing mandatory contract field(s) or absent affirmative scanner inventory / change-ticket authorization record",
      "[ILLUSTRATIVE PLACEHOLDER] Actual source IP, destination port, and packet counts for Incident 165233 are intentionally omitted rather than invented",
    ],
    guardrailOrScoreImpact:
      "Under EvidenceSufficiencyEngine's Infallible Rule, missing mandatory contract fields cap overall sufficiency <= 49.0 (INSUFFICIENT) and prevent automated classification.",
    takeaway:
      "Even when an alert looks routine, missing mandatory fields or missing scanner authorization cannot pass Evidence Confidence checks.",
  },
  {
    stepNumber: 3,
    id: "inc-165233-investigation",
    stageName: "3. Local LLM Investigation & Authorization Gate",
    componentName: "Server 2 Local LLM & Compiled 9-Section Policy",
    statusBadge: "NO ASSUMED BENIGN FP",
    statusTone: "cyan",
    whatHappens:
      "Under the remediated NETWORK_SCAN policy (Sections 1, 6, and 7), internal RFC-1918 addresses or lack of endpoint malware cannot be treated as automatic False Positives.",
    observedFacts: [
      "Section 1 & Section 6 prohibit blanket benign assumptions without verified scanner authorization",
      "Section 7 mandates voting REQUIRES_ATTENTION when critical evidence or authorization proof is unavailable",
    ],
    illustrativePlaceholders: [
      "[ILLUSTRATIVE PLACEHOLDER] No verified vulnerability scanner ticket or approved maintenance window is asserted in raw telemetry",
      "[ILLUSTRATIVE PLACEHOLDER] Illustrative analyst follow-up question from Section 9: 'Is the source IP registered in asset inventory as an authorized scanner with an active change ticket?'",
    ],
    guardrailOrScoreImpact:
      "Guardrail G6 (Negative/Blanket FP Prohibition) blocks any FALSE_POSITIVE outcome lacking grounded affirmative business authorization.",
    takeaway:
      "Unlike a naive heuristic that auto-closes internal scans as False Positive, AIS 2.0/2.1 demands verifiable authorization proof.",
  },
  {
    stepNumber: 4,
    id: "inc-165233-decision-trust",
    stageName: "4. Guardrails & Observed Trustworthiness Score (3/10)",
    componentName: "VerdictGuardrailsEngine & VerdictTrustworthinessEngine",
    statusBadge: "AI DECISION: REQUIRES ANALYST ATTENTION · 3/10",
    statusTone: "rose",
    whatHappens:
      "Deterministic safety checks and Trust Score calculation finalize the verdict. Because critical supporting/authorization evidence is unverified or missing and the rule lacks calibrated N >= 30 history, Trust Score is capped at 3/10.",
    observedFacts: [
      "Historical AI Decision: Requires Analyst Attention (REQUIRES_ANALYST_ATTENTION)",
      "Observed Trustworthiness Score: 3/10 (Weak / Substantially Uncertain)",
      "Threshold for automated TP/FP: Trust Score >= 7/10 AND calibrated AND zero guardrails triggered",
    ],
    illustrativePlaceholders: [
      "[ILLUSTRATIVE PLACEHOLDER] Illustrative 5-dimension Trust Score cap behavior: missing mandatory evidence or conflict enforces ordinal_score = min(3, ordinal_score)",
      "[ILLUSTRATIVE PLACEHOLDER] Uncalibrated history also imposes baseline historical validation score (5/15 pts) and <= 6/10 calibration cap",
    ],
    guardrailOrScoreImpact:
      "The AI abstained rather than forcing TRUE_POSITIVE or FALSE_POSITIVE. Abstention routes Incident 165233 safely to the Human Review Queue.",
    takeaway:
      "A 3/10 Trust Score with REQUIRES_ANALYST_ATTENTION proves the safety architecture worked as designed—refusing to guess when evidence is incomplete.",
  },
  {
    stepNumber: 5,
    id: "inc-165233-historical-comparison",
    stageName: "5. Historical Comparison & Ground-Truth Provenance Audit",
    componentName: "HistoricalGroundTruthValidator & ReviewOrchestrator",
    statusBadge: "SIEM: FALSE POSITIVE vs AI: ABSTAINED",
    statusTone: "amber",
    whatHappens:
      "Comparing the AI outcome against SIEM history shows SIEM Resolution = 'False Positive' while AI Decision = 'Requires Analyst Attention'. Before counting Incident 165233 as verified ground truth, provenance must be audited.",
    observedFacts: [
      "SIEM Resolution: False Positive",
      "Historical AI Decision: Requires Analyst Attention (Abstention)",
      "Abstention is NOT counted as a wrong TP/FP prediction; it signals insufficient runtime evidence or unverified authorization",
    ],
    illustrativePlaceholders: [
      "[ILLUSTRATIVE PLACEHOLDER] Provenance Audit Check: Inspect clearedUser, clearedReason, comments, and is_ml_generated on HistoricalGroundTruth",
      "[ILLUSTRATIVE PLACEHOLDER] If analyst identity (clearedUser) or written FP rationale is unavailable, or if closure came from automation/ML, ground-truth provenance requires human verification before promotion to gold-standard benchmark",
    ],
    guardrailOrScoreImpact:
      "HistoricalGroundTruthValidator assigns reliability 1.0 only when analyst rationale >= 10 chars exists and is_ml_generated=False; missing analyst provenance requires verification.",
    takeaway:
      "An SIEM 'False Positive' tag without documented analyst identity/rationale cannot automatically validate or penalize AI accuracy.",
  },
  {
    stepNumber: 6,
    id: "inc-165233-simulation-impact",
    stageName: "6. Empirical Accuracy & Gate G8 Impact",
    componentName: "PolicySimulationService & EmpiricalAccuracyEvaluator",
    statusBadge: "G8 STATUS: INSUFFICIENT_DATA",
    statusTone: "amber",
    whatHappens:
      "Even if Incident 165233 is verified as a human False Positive, a single labeled incident cannot establish reliable empirical accuracy or pass Gate G8.",
    observedFacts: [
      "Sample count requirement for Gate G8 Simulation Pass: N >= 5 independently verified rule-matched incidents",
      "Sample count requirement for Calibration (Brier / ECE): N >= 30 balanced TP & FP cases (>= 3 each)",
      "With 1 incident (or 0 verified labels), Historical Simulation remains INSUFFICIENT_DATA (0.0 / 15.0 pts)",
    ],
    illustrativePlaceholders: [
      "[ILLUSTRATIVE PLACEHOLDER] Funnel view: Rule Matched >= 1 → Eligible Ground Truth <= 1 (still < 5 threshold) → Empirical Accuracy = INSUFFICIENT_DATA, Precision/Recall = N/A",
    ],
    guardrailOrScoreImpact:
      "Gate G8 stays WARNING (INSUFFICIENT_DATA) and Calibration stays NOT_CALIBRATED—preventing false statistical confidence from N=1.",
    takeaway:
      "One labeled incident does not establish empirical accuracy. Collect >= 5 verified rule-matched incidents for G8 simulation and >= 30 balanced cases for calibration.",
  },
];
