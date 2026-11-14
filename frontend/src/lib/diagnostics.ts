/**
 * Verdictum AI - Intelligent Diagnostics & Error Mapping Engine
 *
 * Translates technical backend diagnostic codes, quality gate failures,
 * evidence gaps, and HTTP errors into human-understandable operational messages.
 *
 * Primary principle: SIMPLE BY DEFAULT — ADVANCED ON DEMAND.
 */

export interface DiagnosticIssue {
  id: string;
  title: string;
  severity: "critical" | "warning" | "info";
  category: "security" | "rule_definition" | "evidence" | "accuracy" | "governance" | "system";
  cause: string;
  missingInfo?: string;
  impact: string;
  nextAction: string;
  targetTab?: "overview" | "learning" | "advanced";
  targetAdvancedSection?: string;
  rawCode?: string;
}

export interface RuleDiagnosticInput {
  ruleId?: string;
  ruleName?: string;
  definitionStatus?: string; // "INCOMPLETE" | "VERIFIED"
  qualityAssessment?: {
    quality_score?: number;
    approval_eligible?: boolean;
    blocking_issues?: string[];
    blocking_findings?: string[];
    gate_results?: Record<string, { gate_name: string; status: string; score: number; details?: any; evidence_required?: string[] }>;
    gates?: Array<{ gate_name: string; status: string; score: number; details?: any; evidence_required?: string[] }>;
  } | null;
  learningProfile?: {
    total_analyst_reviews?: number;
    verified_tp_count?: number;
    verified_fp_count?: number;
    empirical_accuracy?: number | null;
    is_production_eligible?: boolean;
    eligibility_reasons?: string[];
    lifecycle_stage?: string;
  } | null;
  llmOnline?: boolean | null;
  evidenceContract?: {
    required_fields?: string[];
    available_fields?: string[];
    missing_fields?: string[];
    mapping_issues?: Array<{ field: string; issue: string }>;
  } | null;
}

/**
 * Diagnostic category priority weights:
 * 1. Security-critical failures (weight 100)
 * 2. Active processing failures / LLM offline (weight 90)
 * 3. Missing evidence or rule definitions (weight 80)
 * 4. Analyst actions required / Ground truth needed (weight 70)
 * 5. Production eligibility blockers (weight 60)
 * 6. Noncritical configuration warnings (weight 40)
 */
function getPriorityWeight(issue: DiagnosticIssue): number {
  if (issue.severity === "critical") return 100;
  switch (issue.category) {
    case "security":
      return 95;
    case "system":
      return 90;
    case "rule_definition":
      return 85;
    case "evidence":
      return 80;
    case "accuracy":
      return 70;
    case "governance":
      return 60;
    default:
      return 40;
  }
}

/**
 * Consolidate and deduplicate active diagnostic issues for a detection rule.
 */
export function extractConsolidatedIssues(input: RuleDiagnosticInput): DiagnosticIssue[] {
  const issues: DiagnosticIssue[] = [];
  const seenKeys = new Set<string>();

  // 1. Check LLM Offline status
  if (input.llmOnline === false) {
    issues.push({
      id: "sys_llm_offline",
      title: "AI Inference Engine Currently Offline",
      severity: "warning",
      category: "system",
      cause: "Local Qwen/vLLM inference server is unreachable or reported unhealthy.",
      impact: "New automated verdicts cannot be generated. Historical verdicts remain fully reviewable.",
      nextAction: "Verify local inference service status or switch provider to Simulated heuristic replay.",
      targetTab: "advanced",
      targetAdvancedSection: "simulation",
      rawCode: "LLM_OFFLINE",
    });
  }

  // 2. Detection Rule Definition Status (G1 Blocked)
  const isDefIncomplete =
    input.definitionStatus === "INCOMPLETE" ||
    input.qualityAssessment?.blocking_issues?.some((b) => b.includes("G1") || b.includes("DEFINITION"));

  if (isDefIncomplete) {
    const key = "issue_rule_definition_missing";
    if (!seenKeys.has(key)) {
      seenKeys.add(key);
      issues.push({
        id: key,
        title: "Detection Rule Definition Missing",
        severity: "critical",
        category: "rule_definition",
        cause: "Authoritative FortiSIEM correlation logic and detection thresholds have not been verified.",
        missingInfo: "Original SIEM rule conditions and numeric thresholds.",
        impact: "Production approval is hard-blocked. Policy remains a provisional draft.",
        nextAction: "Import or verify the FortiSIEM rule conditions in Detection Semantics.",
        targetTab: "advanced",
        targetAdvancedSection: "semantics",
        rawCode: "RULE_DEFINITION_INCOMPLETE_G1",
      });
    }
  }

  // 3. Evidence Contract Gaps
  if (input.evidenceContract) {
    const missing = input.evidenceContract.missing_fields || [];
    const mappingIssues = input.evidenceContract.mapping_issues || [];

    if (missing.length > 0) {
      const key = "issue_evidence_missing";
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        issues.push({
          id: key,
          title: `Required Evidence Fields Missing (${missing.length})`,
          severity: "warning",
          category: "evidence",
          cause: `Canonical fields (${missing.slice(0, 3).join(", ")}${missing.length > 3 ? "..." : ""}) are required by policy but not found in telemetry.`,
          missingInfo: missing.join(", "),
          impact: "AI reasoning will lack critical context, leading to Insufficient Evidence verdicts.",
          nextAction: "Inspect field mappings or enrich SIEM event collection in Evidence Contract.",
          targetTab: "advanced",
          targetAdvancedSection: "contract",
          rawCode: "EVIDENCE_CONTRACT_UNFULFILLED_G2",
        });
      }
    }

    if (mappingIssues.length > 0) {
      const key = "issue_evidence_mapping";
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        issues.push({
          id: key,
          title: "Telemetry Field Mapping Discrepancy",
          severity: "warning",
          category: "evidence",
          cause: "Telemetry fields exist in raw SIEM events but failed canonical schema path translation.",
          missingInfo: mappingIssues.map((m) => m.field).join(", "),
          impact: "Raw data is present but excluded from AI context due to mapping error.",
          nextAction: "Review canonical mapping schema in Evidence Contract tab.",
          targetTab: "advanced",
          targetAdvancedSection: "contract",
          rawCode: "FIELD_MAPPING_MISMATCH",
        });
      }
    }
  }

  // 4. Quality Gate Blocking Findings (Deduplicated against G1)
  const blockingFindings = [
    ...(input.qualityAssessment?.blocking_issues || []),
    ...(input.qualityAssessment?.blocking_findings || []),
  ];

  for (const finding of blockingFindings) {
    if (finding.includes("G1") || finding.includes("DEFINITION_INCOMPLETE")) {
      continue; // Handled above cleanly
    }

    let gateCategory: DiagnosticIssue["category"] = "governance";
    let title = "Policy Quality Requirement Unmet";
    let cause = finding;
    let nextAction = "Review and refine policy criteria in Policy Editor.";
    let targetSection = "editor";

    if (finding.includes("G2") || finding.includes("Evidence")) {
      gateCategory = "evidence";
      title = "Evidence Contract Incomplete (G2)";
      nextAction = "Define mandatory evidence fields in Evidence Contract.";
      targetSection = "contract";
    } else if (finding.includes("G3") || finding.includes("True Positive")) {
      title = "True Positive Indicators Incomplete (G3)";
      cause = "Policy lacks clear, verifiable indicators of true malicious activity.";
      nextAction = "Provide concrete TP indicators in Policy Editor Section 5.";
      targetSection = "editor";
    } else if (finding.includes("G4") || finding.includes("False Positive")) {
      title = "False Positive Indicators Incomplete (G4)";
      cause = "Policy lacks expected benign patterns or known administrative behaviors.";
      nextAction = "Define benign baseline scenarios in Policy Editor Section 6.";
      targetSection = "editor";
    } else if (finding.includes("G5") || finding.includes("Missing Info")) {
      title = "Missing Information Guidance Incomplete (G5)";
      cause = "Policy does not instruct the agent on what to do when telemetry is missing.";
      nextAction = "Add missing information handling criteria in Policy Editor Section 7.";
      targetSection = "editor";
    } else if (finding.includes("G6") || finding.includes("Escalation")) {
      title = "Escalation Criteria Undefined (G6)";
      cause = "Policy lacks clear trigger conditions for human analyst escalation.";
      nextAction = "Specify escalation thresholds in Policy Editor Section 8.";
      targetSection = "editor";
    } else if (finding.includes("G8") || finding.includes("Accuracy") || finding.includes("Simulation")) {
      gateCategory = "accuracy";
      title = "Empirical Validation Incomplete (G8)";
      cause = "Policy has not passed historical incident simulation or ground truth benchmarks.";
      nextAction = "Run policy simulation or perform analyst reviews.";
      targetSection = "simulation";
    }

    const key = `finding_${title.toLowerCase().replace(/[^a-z0-9]/g, "_")}`;
    if (!seenKeys.has(key)) {
      seenKeys.add(key);
      issues.push({
        id: key,
        title,
        severity: finding.toLowerCase().includes("critical") || finding.toLowerCase().includes("block") ? "critical" : "warning",
        category: gateCategory,
        cause,
        impact: "Blocks production approval and autonomous execution eligibility.",
        nextAction,
        targetTab: "advanced",
        targetAdvancedSection: targetSection,
        rawCode: finding,
      });
    }
  }

  // 5. Ground Truth & Accuracy Validation Gaps
  const totalReviews = input.learningProfile?.total_analyst_reviews ?? 0;
  const empiricalAccuracy = input.learningProfile?.empirical_accuracy;

  if (totalReviews === 0) {
    const key = "issue_ground_truth_zero";
    if (!seenKeys.has(key)) {
      seenKeys.add(key);
      issues.push({
        id: key,
        title: "AI Accuracy Not Verified — Analyst Reviews Required",
        severity: "warning",
        category: "accuracy",
        cause: "No independently verified analyst TP/FP reviews have been submitted for this rule yet.",
        missingInfo: "Ground truth evaluation dataset (target: 30 for pilot, 100 for production).",
        impact: "Empirical accuracy cannot be calculated (shown as N/A). Automated actions remain disabled.",
        nextAction: "Perform independent double-blind reviews on pending incidents in Analyst Review tab.",
        targetTab: "learning",
        rawCode: "INSUFFICIENT_GROUND_TRUTH_SAMPLES",
      });
    }
  } else if (totalReviews < 30) {
    const key = "issue_ground_truth_low";
    if (!seenKeys.has(key)) {
      seenKeys.add(key);
      issues.push({
        id: key,
        title: `More Verified Analyst Reviews Required (${totalReviews} / 30 for Pilot)`,
        severity: "info",
        category: "accuracy",
        cause: `Current sample size of ${totalReviews} verified reviews is below the statistical threshold for pilot automation.`,
        missingInfo: `${30 - totalReviews} additional verified reviews required.`,
        impact: "Rule remains in supervised learning mode.",
        nextAction: "Continue reviewing pending incidents in the Analyst Review Queue.",
        targetTab: "learning",
        rawCode: "SAMPLE_SIZE_BELOW_PILOT_THRESHOLD",
      });
    }
  }

  // 6. Production Eligibility Criteria
  if (input.learningProfile && !input.learningProfile.is_production_eligible && input.learningProfile.eligibility_reasons) {
    const unfulfilledReasons = input.learningProfile.eligibility_reasons.filter(
      (r) => !r.toLowerCase().includes("satisfied") && !r.toLowerCase().includes("pass")
    );
    if (unfulfilledReasons.length > 0) {
      const key = "issue_prod_eligibility";
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        issues.push({
          id: key,
          title: "Production Approval Blocked by Criteria",
          severity: "warning",
          category: "governance",
          cause: unfulfilledReasons.slice(0, 2).join("; "),
          missingInfo: unfulfilledReasons.join(" | "),
          impact: "Rule cannot be promoted to Controlled Production.",
          nextAction: "Review unmet requirements in Analyst Review & Learning -> Production Eligibility.",
          targetTab: "learning",
          rawCode: "PRODUCTION_PROMOTION_GATES_ACTIVE",
        });
      }
    }
  }

  // Sort by priority weight descending
  issues.sort((a, b) => getPriorityWeight(b) - getPriorityWeight(a));
  return issues;
}

/**
 * Derives a single operational summary status from backend lifecycle,
 * quality gate score, and operational conditions.
 */
export type OperationalSummaryStatus =
  | "READY_FOR_LEARNING"
  | "LEARNING_IN_PROGRESS"
  | "ACTION_REQUIRED"
  | "READY_FOR_VALIDATION"
  | "PRODUCTION_APPROVAL_PENDING"
  | "PRODUCTION_ACTIVE"
  | "SUSPENDED";

export function deriveOperationalStatus(input: {
  lifecycleStage?: string;
  isApprovalEligible?: boolean;
  isIncompleteDefinition?: boolean;
  activeVersionStatus?: string;
  hasHardGateFailure?: boolean;
  totalAnalystReviews?: number;
  qualityScore?: number | null;
}): {
  status: OperationalSummaryStatus;
  label: string;
  badgeClass: string;
  dotClass: string;
} {
  const stage = (input.lifecycleStage || "LEARNING").toUpperCase();

  if (stage === "SUSPENDED") {
    return {
      status: "SUSPENDED",
      label: "Suspended",
      badgeClass: "bg-rose-950/70 border-rose-800 text-rose-300",
      dotClass: "bg-rose-500",
    };
  }

  if (input.activeVersionStatus === "APPROVED" || stage === "CONTROLLED_PRODUCTION") {
    return {
      status: "PRODUCTION_ACTIVE",
      label: "Production Active",
      badgeClass: "bg-emerald-950/70 border-emerald-800 text-emerald-300",
      dotClass: "bg-emerald-400",
    };
  }

  if (input.isIncompleteDefinition || input.hasHardGateFailure) {
    return {
      status: "ACTION_REQUIRED",
      label: "Action Required",
      badgeClass: "bg-amber-950/70 border-amber-800 text-amber-300",
      dotClass: "bg-amber-400",
    };
  }

  if (input.isApprovalEligible && (input.totalAnalystReviews || 0) >= 30) {
    return {
      status: "PRODUCTION_APPROVAL_PENDING",
      label: "Production Approval Pending",
      badgeClass: "bg-cyan-950/70 border-cyan-700 text-cyan-200",
      dotClass: "bg-cyan-400",
    };
  }

  if ((input.totalAnalystReviews || 0) >= 10 && (input.qualityScore ?? 0) >= 60) {
    return {
      status: "READY_FOR_VALIDATION",
      label: "Ready for Validation",
      badgeClass: "bg-indigo-950/70 border-indigo-800 text-indigo-300",
      dotClass: "bg-indigo-400",
    };
  }

  if ((input.totalAnalystReviews || 0) > 0) {
    return {
      status: "LEARNING_IN_PROGRESS",
      label: "Learning in Progress",
      badgeClass: "bg-blue-950/70 border-blue-800 text-blue-300",
      dotClass: "bg-blue-400",
    };
  }

  return {
    status: "READY_FOR_LEARNING",
    label: "Ready for Learning",
    badgeClass: "bg-slate-900 border-slate-700 text-slate-300",
    dotClass: "bg-slate-400",
  };
}

/**
 * Format HTTP errors safely into actionable diagnostic advice.
 */
export function formatHttpError(err: any): {
  title: string;
  message: string;
  requestId?: string;
  isRetryable: boolean;
} {
  const status = err?.status || err?.response?.status;
  const data = err?.data || err?.response?.data;
  const requestId = data?.request_id || data?.correlation_id;

  if (status === 422) {
    const details = data?.detail;
    let explanation = "The request payload failed server validation.";
    if (Array.isArray(details)) {
      explanation = details.map((d: any) => `${d.loc?.join(".")}: ${d.msg}`).join("; ");
    } else if (typeof details === "string") {
      explanation = details;
    }
    return {
      title: "Request Could Not Be Processed",
      message: explanation,
      requestId,
      isRetryable: false,
    };
  }

  if (status === 403) {
    return {
      title: "Permission Required",
      message: "Your current account role does not possess authorization to execute this operational action.",
      requestId,
      isRetryable: false,
    };
  }

  if (status === 500) {
    return {
      title: "Server Internal Error",
      message: "The backend service encountered an unexpected condition. State has not been corrupted.",
      requestId,
      isRetryable: true,
    };
  }

  return {
    title: "Communication Failure",
    message: err?.message || "An unexpected error occurred while communicating with the backend API.",
    requestId,
    isRetryable: true,
  };
}
