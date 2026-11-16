"use client";

import React, { useMemo, useState, useEffect } from "react";
import {
  Sparkles,
  Award,
  Cpu,
  Check,
  RotateCcw,
  AlertTriangle,
  ArrowRight,
  Shield,
  Layers,
  Database,
  Activity,
  FileCheck2,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  Info,
  HelpCircle,
  ExternalLink,
  Terminal,
  Eye,
} from "lucide-react";
import {
  extractConsolidatedIssues,
  deriveOperationalStatus,
  DiagnosticIssue,
} from "@/lib/diagnostics";
import {
  IssueSummary,
  NextActionCard,
  CompactVersionSelector,
  EvidenceCompletenessIndicator,
  StatusBadge,
} from "./CompactDesignSystem";
import {
  api,
  PolicyQualityAssessmentResponse,
  RuleIntelligenceData,
  PromptVersion,
  QualityGateResult,
  ProductionReadinessResponse,
  ReadinessStageItem,
  PolicyEligibilityResponse,
} from "@/lib/api";

export interface AgentIntelligenceStudioOverviewProps {
  ruleId: string;
  ruleName?: string;
  archetype?: string;
  qualityAssessment: PolicyQualityAssessmentResponse | null;
  learningProfile: any | null;
  intelligenceData: RuleIntelligenceData | null;
  selectedVersion: PromptVersion | null;
  versions: PromptVersion[];
  activeVersionId?: string | null;
  isApprovalEligible: boolean;
  isIncompleteDefinition: boolean;
  hasHardGateFailure: boolean;
  llmOnline: boolean | null;
  actionLoading: boolean;
  loadingQuality: boolean;
  loadingSimulation: boolean;
  isViewer: boolean;
  onSelectVersion: (id: string) => void;
  onRollback: () => void;
  onGenerateIntelligentDraft: () => void;
  onValidateQuality: () => void;
  onRunSimulation: () => void;
  onApproveClick: () => void;
  onNavigateTab: (tab: "overview" | "learning" | "advanced", section?: string) => void;
  onViewActualPrompt?: (incidentId?: string) => void;
  onPreviewPrompt?: () => void;
}

const STAGE_EXPLANATIONS: Record<string, { means: string; why: string; required: string }> = {
  define_detection: {
    means: "Verifies the FortiSIEM correlation conditions, trigger threshold, aggregation window, and detection archetype.",
    why: "Ensures the AI agent accurately models the exact attack logic and telemetry boundaries of the SIEM rule.",
    required: "Authoritative detection threshold and aggregation window defined in SIEM rule semantics.",
  },
  verify_evidence: {
    means: "Ensures all SIEM telemetry fields required to evaluate this attack behavior are present and mapped in the Evidence Contract.",
    why: "Prevents LLM hallucination and blind spots by ensuring the AI receives all necessary telemetry.",
    required: "All mandatory archetype telemetry fields mapped and verified in the Evidence Contract.",
  },
  validate_policy: {
    means: "Evaluates the AI prompt against quality criteria: true positive indicators, benign false positive assumptions, abstention safety, and consistency.",
    why: "Enforces that the decision policy aligns with SOC standard operating procedures and passes static quality gates G1–G7.",
    required: "Valid policy with complete sections, explicit indicators, and a quality score ≥70 without hard blockers.",
  },
  analyst_learning: {
    means: "Collects independent, double-blind analyst determinations (TP/FP) on real incidents to establish ground truth calibration.",
    why: "Ground truth provides the benchmark against which AI accuracy, precision, and recall are objectively measured.",
    required: "At least 30 verified analyst reviews for Supervised Pilot, or 100 for Controlled Production.",
  },
  test_accuracy: {
    means: "Tests the AI prompt against historical incidents in simulation replay to verify statistical precision (≥98%), recall (≥95%), and confidence (≥96%).",
    why: "Guarantees mathematically that the AI will not suppress true attacks or generate unmanageable false alarms.",
    required: "Completed simulation replay meeting FP Precision ≥98%, TP Recall ≥95%, and Wilson Lower Bound ≥96%.",
  },
  production_approval: {
    means: "Formal governance gate: verifies that all quality criteria pass before an authorized administrator signs off on production deployment.",
    why: "Enforces accountability, human oversight, and separation of duties before autonomous action is permitted.",
    required: "All 8 Quality Gates passed, zero blocking issues, and sign-off by an authorized SOC Lead or Administrator.",
  },
};

export function AgentIntelligenceStudioOverview({
  ruleId,
  ruleName,
  archetype,
  qualityAssessment,
  learningProfile,
  intelligenceData,
  selectedVersion,
  versions,
  activeVersionId,
  isApprovalEligible,
  isIncompleteDefinition,
  hasHardGateFailure,
  llmOnline,
  actionLoading,
  loadingQuality,
  loadingSimulation,
  isViewer,
  onSelectVersion,
  onRollback,
  onGenerateIntelligentDraft,
  onValidateQuality,
  onRunSimulation,
  onApproveClick,
  onNavigateTab,
  onViewActualPrompt,
  onPreviewPrompt,
}: AgentIntelligenceStudioOverviewProps) {
  // Authoritative Backend Readiness & Eligibility State
  const [readinessData, setReadinessData] = useState<ProductionReadinessResponse | null>(null);
  const [eligibilityData, setEligibilityData] = useState<PolicyEligibilityResponse | null>(null);
  const [loadingReadiness, setLoadingReadiness] = useState(false);
  const [expandedStageDetails, setExpandedStageDetails] = useState<Record<string, boolean>>({});

  // Fetch backend readiness and eligibility data whenever rule or version changes
  useEffect(() => {
    let isMounted = true;
    if (!ruleId) return;

    const fetchReadinessAndEligibility = async () => {
      setLoadingReadiness(true);
      try {
        const [readinessRes, eligibilityRes] = await Promise.allSettled([
          api.getRuleProductionReadiness(ruleId, selectedVersion?.id),
          api.getRulePolicyEligibility(ruleId, selectedVersion?.id),
        ]);
        if (isMounted) {
          if (readinessRes.status === "fulfilled") {
            setReadinessData(readinessRes.value);
          }
          if (eligibilityRes.status === "fulfilled") {
            setEligibilityData(eligibilityRes.value);
          }
        }
      } catch (err) {
        console.warn("Could not fetch authoritative readiness or eligibility from API:", err);
      } finally {
        if (isMounted) {
          setLoadingReadiness(false);
        }
      }
    };

    fetchReadinessAndEligibility();
    return () => {
      isMounted = false;
    };
  }, [ruleId, selectedVersion?.id]);

  // Extract consolidated diagnostic issues
  const consolidatedIssues: DiagnosticIssue[] = useMemo(() => {
    return extractConsolidatedIssues({
      ruleId,
      ruleName,
      definitionStatus: intelligenceData?.semantics?.definition_status,
      qualityAssessment,
      learningProfile,
      llmOnline,
      evidenceContract: {
        required_fields:
          intelligenceData?.candidate_evidence_contract?.core_fields?.map((c: any) => c.field_name || c.field) ||
          intelligenceData?.archetype_definition?.mandatory_core_fields ||
          [],
        available_fields: intelligenceData?.semantics?.relevant_fields || [],
        missing_fields: intelligenceData?.semantics?.missing_requirements || [],
        mapping_issues: [],
      },
    });
  }, [ruleId, ruleName, intelligenceData, qualityAssessment, learningProfile, llmOnline]);

  // Metrics from readinessData or props fallback
  const qualityScore = readinessData?.quality_score ?? qualityAssessment?.quality_score ?? null;
  const passedGates = readinessData?.quality_gates_passed ?? (
    qualityAssessment?.gate_results
      ? Object.values(qualityAssessment.gate_results).filter((g) => g.status === "PASSED").length
      : qualityAssessment?.gates?.filter((g) => g.status === "PASSED").length ?? 0
  );
  const totalReviews = readinessData?.verified_reviews_count ?? learningProfile?.total_analyst_reviews ?? 0;
  const empiricalAccuracy = readinessData?.metrics?.empirical_accuracy ?? learningProfile?.empirical_accuracy;
  const isSelectedActive = selectedVersion?.id === activeVersionId;
  const displayArchetype = readinessData?.detection_archetype || archetype || intelligenceData?.classification?.primary_archetype || "UNKNOWN";
  const ruleDisplayName = readinessData?.rule_name || ruleName || `Detection Rule ${ruleId.slice(0, 8)}`;
  const plainEnglishDescription = readinessData?.detection_description || intelligenceData?.semantics?.detection_objective || `Monitors security telemetry for ${displayArchetype} activity.`;
  const deploymentStatus = readinessData?.rule_deployment_status || (isSelectedActive && selectedVersion?.status === "APPROVED" ? "ACTIVE" : "NOT_DEPLOYED");

  // Decoupled Policy Governance & AI Execution Status
  const activeVersion = versions.find((v) => v.id === activeVersionId) || null;
  const selectedPolicyLabel = selectedVersion
    ? `V${selectedVersion.version_number} — ${selectedVersion.status}`
    : "None";
  const activePolicyLabel = activeVersion
    ? (activeVersion.status === "REVOKED"
        ? `V${activeVersion.version_number} — REVOKED`
        : `V${activeVersion.version_number} — ${activeVersion.status}`)
    : (eligibilityData?.active_version_number
        ? `V${eligibilityData.active_version_number} — ${eligibilityData.active_version_status}`
        : "None (Revoked / Suspended)");

  const isPolicyRevoked = Boolean(
    eligibilityData?.is_revoked ||
    selectedVersion?.status === "REVOKED" ||
    (activeVersion && activeVersion.status === "REVOKED")
  );

  const aiVerdictExecutionStatus: "Enabled" | "Disabled" | "Suspended" | "Offline" | "Unknown" | "Blocked" =
    readinessData?.ai_execution_status
      ? (readinessData.ai_execution_status as "Enabled" | "Disabled" | "Suspended" | "Offline" | "Unknown" | "Blocked")
      : eligibilityData?.ai_verdict_execution_status === "ENABLED"
      ? "Enabled"
      : eligibilityData?.ai_verdict_execution_status === "SUSPENDED" || isPolicyRevoked
      ? "Suspended"
      : "Blocked";

  // Decoupled Statuses: Authoritative Backend Readiness & Eligibility
  const effectiveApprovalEligible = Boolean(
    readinessData
      ? readinessData.approval_eligible
      : (isApprovalEligible && passedGates === 8 && totalReviews >= 30)
  );

  const blockingReqCount = readinessData?.blocking_requirements?.length ?? (
    (8 - passedGates > 0 ? (8 - passedGates) : 0) + (totalReviews < 30 ? 1 : 0)
  );

  const productionReadinessStatus: "Ready" | "Blocked" =
    readinessData?.approval_eligible
      ? "Ready"
      : (readinessData?.readiness_status === "APPROVED" && passedGates === 8) ||
        readinessData?.readiness_status === "ACTIVE"
      ? "Ready"
      : "Blocked";

  // Format accuracy for display
  const accuracyDisplay =
    empiricalAccuracy !== null && empiricalAccuracy !== undefined && totalReviews > 0
      ? `${(empiricalAccuracy * 100).toFixed(1)}%`
      : totalReviews === 0
      ? "N/A"
      : "Pending";

  // Production Readiness Status & Visual Badges
  const readinessStatus = readinessData?.readiness_status ?? (
    loadingReadiness
      ? "VALIDATING"
      : isIncompleteDefinition || hasHardGateFailure
      ? "BLOCKED"
      : totalReviews < 30
      ? "LEARNING"
      : effectiveApprovalEligible
      ? "READY_FOR_APPROVAL"
      : "VALIDATING"
  );

  const readinessBadgeMap: Record<string, { label: string; badge: string; dot: string; desc: string }> = {
    BLOCKED: {
      label: "BLOCKED / INCOMPLETE",
      badge: "bg-rose-950/80 border-rose-800 text-rose-300",
      dot: "bg-rose-500",
      desc: "Mandatory quality gates or definition specifications require remediation before validation can proceed.",
    },
    INCOMPLETE: {
      label: "INCOMPLETE SPECIFICATION",
      badge: "bg-rose-950/80 border-rose-800 text-rose-300",
      dot: "bg-rose-500",
      desc: "Authoritative SIEM correlation logic or evidence bindings are unverified.",
    },
    LEARNING: {
      label: "LEARNING IN PROGRESS",
      badge: "bg-blue-950/80 border-blue-800 text-blue-300",
      dot: "bg-blue-400",
      desc: "Collecting independent double-blind analyst determinations on real incidents for ground-truth calibration.",
    },
    VALIDATING: {
      label: "VALIDATING ACCURACY",
      badge: "bg-indigo-950/80 border-indigo-800 text-indigo-300",
      dot: "bg-indigo-400",
      desc: "Sufficient ground truth gathered. Historical simulation replay and regression testing in progress.",
    },
    READY_FOR_APPROVAL: {
      label: "READY FOR APPROVAL",
      badge: "bg-amber-950/80 border-amber-800 text-amber-300",
      dot: "bg-amber-400",
      desc: "All static quality criteria and empirical requirements satisfied. Awaiting administrator sign-off.",
    },
    APPROVED: {
      label: "APPROVED BASELINE",
      badge: "bg-emerald-950/80 border-emerald-800 text-emerald-300",
      dot: "bg-emerald-400",
      desc: "Formally approved by SOC Lead. Baseline policy established.",
    },
    ACTIVE: {
      label: "ACTIVE IN PRODUCTION",
      badge: "bg-emerald-950/90 border-emerald-700 text-emerald-300 shadow-sm shadow-emerald-900/30",
      dot: "bg-emerald-400 animate-pulse",
      desc: "Active in production monitoring with verified policy enforcement.",
    },
    UNKNOWN: {
      label: "STATUS UNKNOWN",
      badge: "bg-slate-900/80 border-slate-700 text-slate-400",
      dot: "bg-slate-500",
      desc: "Authoritative production readiness evaluation unavailable. Check backend service status.",
    },
    UNAVAILABLE: {
      label: "SERVICE UNAVAILABLE",
      badge: "bg-slate-900/80 border-slate-700 text-slate-400",
      dot: "bg-slate-500",
      desc: "Readiness service could not evaluate this policy specification.",
    },
  };

  const currentReadinessBadge = readinessBadgeMap[readinessStatus] || readinessBadgeMap.BLOCKED;

  // Derive Smart Next Action (single prioritized recommended action)
  const smartAction = useMemo(() => {
    if (readinessData?.recommended_action) {
      const ra = readinessData.recommended_action;
      return {
        title: ra.title,
        description: ra.description,
        label: ra.label,
        action: () => {
          if (ra.action_type === "VALIDATE_QUALITY") onValidateQuality();
          else if (ra.action_type === "RUN_SIMULATION") onRunSimulation();
          else if (ra.action_type === "APPROVE") onApproveClick();
          else onNavigateTab(ra.target_tab, ra.target_section);
        },
        status: ra.status,
      };
    }

    // Fallback priority cascade if readiness endpoint not yet loaded
    if (isIncompleteDefinition) {
      return {
        title: "Verify FortiSIEM Detection Semantics",
        description:
          "Authoritative correlation conditions and thresholds are missing. Review the FortiSIEM detection rule specifications to unblock production approval.",
        label: "Inspect Semantics",
        action: () => onNavigateTab("advanced", "intelligence"),
        status: "warning" as const,
      };
    }

    if (!qualityAssessment || qualityAssessment.quality_score < 70 || hasHardGateFailure) {
      return {
        title: "Validate AI Policy Quality Requirements",
        description:
          "Verify that G1–G8 validation criteria and evidence bindings satisfy production standards.",
        label: "Run Quality Validation",
        action: onValidateQuality,
        status: "primary" as const,
      };
    }

    if (totalReviews < 30) {
      return {
        title: "Review Pending Incidents for Ground Truth",
        description:
          `Ground truth calibration requires verified analyst reviews (${totalReviews}/30 for pilot). Conduct double-blind evaluations on pending incidents.`,
        label: "Review Incidents",
        action: () => onNavigateTab("learning"),
        status: "primary" as const,
      };
    }

    if (isApprovalEligible && selectedVersion?.status !== "APPROVED") {
      return {
        title: "Request Production Approval",
        description:
          "All static quality gates and preliminary empirical requirements have been satisfied. Promote candidate to production baseline.",
        label: "Approve & Activate",
        action: onApproveClick,
        status: "success" as const,
      };
    }

    return {
      title: "Run Simulation Replay",
      description:
        "Test candidate policy against historical incident datasets to verify model precision and recall.",
      label: "Run Simulation",
      action: onRunSimulation,
      status: "primary" as const,
    };
  }, [
    readinessData,
    isIncompleteDefinition,
    qualityAssessment,
    hasHardGateFailure,
    totalReviews,
    isApprovalEligible,
    selectedVersion?.status,
    onNavigateTab,
    onValidateQuality,
    onRunSimulation,
    onApproveClick,
  ]);

  // Guided 6 Stages (either from backend readiness response or locally mapped)
  const stages: ReadinessStageItem[] = useMemo(() => {
    if (readinessData?.stages && readinessData.stages.length > 0) {
      return readinessData.stages;
    }

    // Default fallback mapping
    return [
      {
        stage_id: "define_detection",
        stage_name: "Define Detection",
        stage_number: 1,
        status: isIncompleteDefinition ? "BLOCKED" : "COMPLETED",
        simple_explanation: "Verifies the FortiSIEM correlation conditions, trigger threshold, aggregation window, and detection archetype.",
        missing_requirement: isIncompleteDefinition ? "Authoritative SIEM detection condition and threshold definition missing." : null,
        next_action: isIncompleteDefinition ? "Review FortiSIEM correlation threshold definitions in SIEM Semantics." : "Detection logic and archetype verified.",
        action_button: { label: "Inspect Semantics", action: "open_tab", target_tab: "advanced", target_section: "intelligence" },
        technical_details: {},
      },
      {
        stage_id: "verify_evidence",
        stage_name: "Verify Evidence",
        stage_number: 2,
        status: intelligenceData?.semantics?.missing_requirements?.length ? "BLOCKED" : "COMPLETED",
        simple_explanation: "Ensures all SIEM telemetry fields required to evaluate this attack behavior are present and mapped in the Evidence Contract.",
        missing_requirement: intelligenceData?.semantics?.missing_requirements?.length ? `Unmapped fields: ${intelligenceData.semantics.missing_requirements.join(", ")}` : null,
        next_action: "Review field bindings in Evidence Contract.",
        action_button: { label: "Inspect Contract", action: "open_tab", target_tab: "advanced", target_section: "contract" },
        technical_details: {},
      },
      {
        stage_id: "validate_policy",
        stage_name: "Validate AI Policy",
        stage_number: 3,
        status: qualityScore && qualityScore >= 70 && !hasHardGateFailure ? "COMPLETED" : "NEEDS_ACTION",
        simple_explanation: "Evaluates the AI prompt against quality criteria: true positive indicators, benign false positive assumptions, abstention safety, and consistency.",
        missing_requirement: qualityScore && qualityScore < 70 ? `Quality score (${qualityScore}/100) below minimum standard.` : null,
        next_action: "Execute policy quality validation to inspect G1–G8 gates.",
        action_button: { label: "Validate Quality", action: "trigger_validation", target_tab: "overview" },
        technical_details: {},
      },
      {
        stage_id: "analyst_learning",
        stage_name: "Analyst Learning",
        stage_number: 4,
        status: totalReviews >= 30 ? "COMPLETED" : "NEEDS_ACTION",
        simple_explanation: "Collects independent, double-blind analyst determinations (TP/FP) on real incidents to establish ground truth calibration.",
        missing_requirement: totalReviews < 30 ? `Need ${30 - totalReviews} more verified reviews for pilot (target: 30).` : null,
        next_action: "Perform independent reviews in Analyst Review Workbench.",
        action_button: { label: "Review Incidents", action: "open_tab", target_tab: "learning" },
        technical_details: {},
      },
      {
        stage_id: "test_accuracy",
        stage_name: "Test AI Accuracy",
        stage_number: 5,
        status: totalReviews === 0 ? "BLOCKED" : "NEEDS_ACTION",
        simple_explanation: "Tests the AI prompt against historical incidents in simulation replay to verify statistical precision (≥98%), recall (≥95%), and confidence (≥96%).",
        missing_requirement: totalReviews === 0 ? "Requires analyst ground truth reviews before accuracy can be tested." : "Simulation replay required on current policy version.",
        next_action: "Run simulation replay to test accuracy.",
        action_button: { label: "Run Simulation", action: "trigger_simulation", target_tab: "overview" },
        technical_details: {},
      },
      {
        stage_id: "production_approval",
        stage_name: "Production Approval",
        stage_number: 6,
        status: (selectedVersion?.status === "APPROVED" && passedGates === 8) ? "COMPLETED" : effectiveApprovalEligible ? "NEEDS_ACTION" : "BLOCKED",
        simple_explanation: "Formal governance gate: verifies that all quality criteria pass before an authorized administrator signs off on production deployment.",
        missing_requirement: !effectiveApprovalEligible && selectedVersion?.status !== "APPROVED" ? `Approval blocked — ${blockingReqCount} mandatory checks incomplete.` : null,
        next_action: effectiveApprovalEligible ? "All prerequisite quality criteria satisfied. Ready for administrator sign-off." : "Resolve blocking stages above to enable approval.",
        action_button: effectiveApprovalEligible
          ? { label: "Approve Policy", action: "request_approval", target_tab: "overview" }
          : { label: "Approval Blocked", action: "request_approval", target_tab: "overview" },
        technical_details: {},
      },
    ];
  }, [readinessData, isIncompleteDefinition, intelligenceData, qualityScore, hasHardGateFailure, totalReviews, selectedVersion?.status, isApprovalEligible, effectiveApprovalEligible, passedGates, blockingReqCount]);

  const completedStagesCount = stages.filter((s) => s.status === "COMPLETED").length;
  const readinessProgress = readinessData?.readiness_progress ?? Math.round((completedStagesCount / 6) * 100);

  const toggleStageDetails = (stageId: string) => {
    setExpandedStageDetails((prev) => ({
      ...prev,
      [stageId]: !prev[stageId],
    }));
  };

  const handleStageAction = (stage: ReadinessStageItem) => {
    const btn = stage.action_button;
    if (btn.action === "trigger_validation") onValidateQuality();
    else if (btn.action === "trigger_simulation") onRunSimulation();
    else if (btn.action === "request_approval") onApproveClick();
    else onNavigateTab(btn.target_tab || "overview", btn.target_section);
  };

  return (
    <div data-testid="compact-rule-detail" className="space-y-3.5">
      {/* 1. RULE IDENTITY & QUICK ACTION STRIP */}
      <div className="p-3 sm:px-4 rounded-xl border border-slate-800/90 bg-slate-950/80 shadow-sm space-y-3">
        {/* Full-Width Rule Header */}
        <div className="space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2 min-w-0">
              <h1 className="text-base sm:text-lg font-bold text-slate-100 flex items-center gap-2 break-words leading-snug">
                <Shield className="w-4 h-4 text-cyan-400 shrink-0" />
                <span>{ruleDisplayName}</span>
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-semibold bg-slate-900 text-cyan-300 border border-cyan-800/60 uppercase shrink-0">
                {displayArchetype}
              </span>
            </div>

            <div className="text-[10px] font-mono text-slate-400 flex items-center gap-2 shrink-0">
              <span>Rule ID: <strong className="text-slate-300">{ruleId}</strong></span>
              <span>·</span>
              <span>Active Policy: <strong className="text-cyan-400">{activePolicyLabel}</strong></span>
            </div>
          </div>

          {/* Authoritative Decoupled Governance & Readiness Indicators (4-Part Decoupled Lifecycle) */}
          <div data-testid="ais-decoupled-lifecycle-strip" className="flex flex-wrap items-center gap-1.5 pt-0.5">
            {/* 1. FortiSIEM Detection Rule Status */}
            <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-900 border border-slate-700/80 text-slate-300 flex items-center gap-1.5" title="Underlying FortiSIEM Detection Rule Deployment Status">
              <span className="text-slate-500 font-mono text-[10px]">SIEM Rule:</span>
              <span className={`w-1.5 h-1.5 rounded-full ${deploymentStatus === "ACTIVE" ? "bg-emerald-400" : "bg-slate-500"}`} />
              <strong className={deploymentStatus === "ACTIVE" ? "text-emerald-300 font-semibold" : "text-slate-400"} title="SIEM Rule Deployment Status">
                {deploymentStatus}
              </strong>
            </span>

            {/* 2. Selected Policy Version & Status */}
            <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-900 border border-slate-700/80 text-slate-300 flex items-center gap-1.5" title="Candidate Policy Version loaded in Overview & Editor">
              <span className="text-slate-500 font-mono text-[10px]">
                {selectedVersion ? `Policy v${selectedVersion.version_number}:` : "Policy:"}
              </span>
              <strong className={
                selectedVersion?.status === "APPROVED"
                  ? "text-emerald-400 font-semibold"
                  : selectedVersion?.status === "REVOKED"
                  ? "text-rose-400 font-semibold"
                  : selectedVersion?.status === "VALIDATED"
                  ? "text-sky-300 font-semibold"
                  : "text-amber-400 font-semibold"
              }>
                {selectedVersion?.status || "None"}
              </strong>
            </span>

            {/* Active AI Policy Reference (if different from candidate) */}
            {activeVersion && activeVersion.id !== selectedVersion?.id && (
              <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-900 border border-slate-700/80 text-slate-300 flex items-center gap-1.5" title="Active Approved Policy assigned for production verdicts">
                <span className="text-slate-500 font-mono text-[10px]">Active Policy:</span>
                <strong className={activeVersion.status === "APPROVED" && !isPolicyRevoked ? "text-cyan-400 font-semibold" : "text-rose-400 font-semibold"}>
                  {activePolicyLabel}
                </strong>
              </span>
            )}

            {/* 3. AI Verdict Execution Status */}
            <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-900 border border-slate-700/80 text-slate-300 flex items-center gap-1.5" title={`Real-time execution state: ${aiVerdictExecutionStatus} (Runtime: ${readinessData?.runtime_availability || "Unknown"}, Automation Configured: ${readinessData?.automation_configured ? "Yes" : "No"})`}>
              <span className="text-slate-500 font-mono text-[10px]">AI Execution:</span>
              <span className={`w-1.5 h-1.5 rounded-full ${
                aiVerdictExecutionStatus === "Enabled"
                  ? "bg-emerald-400"
                  : aiVerdictExecutionStatus === "Suspended"
                  ? "bg-amber-400"
                  : aiVerdictExecutionStatus === "Offline"
                  ? "bg-rose-500"
                  : aiVerdictExecutionStatus === "Disabled"
                  ? "bg-slate-400"
                  : aiVerdictExecutionStatus === "Unknown"
                  ? "bg-slate-500"
                  : "bg-rose-400"
              }`} />
              <strong className={
                aiVerdictExecutionStatus === "Enabled"
                  ? "text-emerald-300 font-semibold"
                  : aiVerdictExecutionStatus === "Suspended"
                  ? "text-amber-300 font-semibold"
                  : aiVerdictExecutionStatus === "Offline"
                  ? "text-rose-400 font-semibold"
                  : aiVerdictExecutionStatus === "Disabled"
                  ? "text-slate-400 font-semibold"
                  : aiVerdictExecutionStatus === "Unknown"
                  ? "text-slate-400 font-semibold"
                  : "text-rose-300 font-semibold"
              }>
                {aiVerdictExecutionStatus}
              </strong>
            </span>

            {/* 4. Authoritative Production Readiness Status */}
            <span className="px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-900 border border-slate-700/80 text-slate-300 flex items-center gap-1.5" title="Authoritative production readiness state">
              <span className="text-slate-500 font-mono text-[10px]">Current Readiness:</span>
              <strong className={
                readinessStatus === "READY_FOR_APPROVAL" || readinessStatus === "ACTIVE"
                  ? "text-emerald-400 font-semibold"
                  : readinessStatus === "APPROVED"
                  ? "text-emerald-300 font-semibold"
                  : readinessStatus === "LEARNING"
                  ? "text-blue-300 font-semibold"
                  : "text-rose-400 font-semibold"
              }>
                {currentReadinessBadge.label}
              </strong>
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            {plainEnglishDescription}
          </p>

          {/* Warning banner when policy is revoked, suspended, or semantic mismatch */}
          {eligibilityData && !eligibilityData.is_eligible && (
            <div className="p-2.5 rounded-lg border border-amber-800/80 bg-amber-950/40 text-xs text-amber-200 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <div className="font-semibold text-amber-300 flex items-center gap-2">
                  <span>AI Execution Suspended: {eligibilityData.reason_code}</span>
                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-amber-900/80 text-amber-200 border border-amber-700">
                    Safe Fallback
                  </span>
                </div>
                <p className="text-[11px] text-amber-200/90 leading-relaxed">
                  {eligibilityData.explanation}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Dedicated Quick Action Toolbar Row */}
        <div className="border-t border-slate-800/80 pt-2.5 flex flex-wrap items-center justify-between gap-2">
          {/* Version Selector */}
          <div className="flex items-center gap-2">
            <CompactVersionSelector
              versions={versions}
              selectedVersionId={selectedVersion?.id || ""}
              activeVersionId={activeVersionId}
              onSelectVersion={onSelectVersion}
              onOpenVersionHistory={() => onNavigateTab("advanced", "history")}
            />
          </div>

          {/* Primary Operations */}
          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              disabled={actionLoading || isViewer}
              onClick={onGenerateIntelligentDraft}
              title={
                isViewer
                  ? "Read-Only Viewer cannot synthesize drafts (requires SOC Analyst or Administrator role)"
                  : "Synthesize draft policy using detection semantics"
              }
              className="px-2.5 py-1.5 rounded-lg theme-primary-btn font-semibold flex items-center gap-1.5 text-xs transition-colors disabled:opacity-50"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Synthesize Draft</span>
            </button>

            <button
              type="button"
              disabled={loadingQuality || isViewer}
              onClick={onValidateQuality}
              title={
                isViewer
                  ? "Read-Only Viewer cannot run quality validation"
                  : "Validate policy quality criteria G1–G8"
              }
              className="px-2.5 py-1.5 rounded-lg theme-secondary-btn font-medium flex items-center gap-1.5 text-xs transition-colors disabled:opacity-50"
            >
              <Award className="w-3.5 h-3.5 text-sky-400" />
              <span>Validate Quality</span>
            </button>

            <button
              type="button"
              disabled={loadingSimulation || isViewer}
              onClick={onRunSimulation}
              title={
                isViewer
                  ? "Read-Only Viewer cannot trigger simulation replay"
                  : "Run empirical simulation replay on historical incidents"
              }
              className="px-2.5 py-1.5 rounded-lg theme-secondary-btn font-medium flex items-center gap-1.5 text-xs transition-colors disabled:opacity-50"
            >
              <Cpu className="w-3.5 h-3.5 text-cyan-400" />
              <span>Simulation</span>
            </button>

            {/* Location 1: View Actual LLM Prompt */}
            <button
              type="button"
              onClick={() => onViewActualPrompt?.()}
              className="px-2.5 py-1.5 rounded-lg border border-emerald-600/70 bg-emerald-950/50 hover:bg-emerald-900/70 text-emerald-300 font-semibold flex items-center gap-1.5 text-xs transition-colors shadow-sm"
              title="Inspect exact prompt payload sent to Local LLM for this rule"
            >
              <Terminal className="w-3.5 h-3.5 text-emerald-400" />
              <span>View Actual LLM Prompt</span>
            </button>

            {/* Preview Compiled Prompt as explicitly separate action */}
            <button
              type="button"
              onClick={() => onPreviewPrompt?.()}
              className="px-2.5 py-1.5 rounded-lg border border-sky-800/60 bg-sky-950/40 hover:bg-sky-900/60 text-sky-300 font-medium flex items-center gap-1.5 text-xs transition-colors shadow-sm"
              title="Preview compiled prompt template without runtime capture"
            >
              <Eye className="w-3.5 h-3.5 text-sky-400" />
              <span className="hidden sm:inline">Preview Prompt</span>
            </button>

            {selectedVersion && selectedVersion.status !== "APPROVED" && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={actionLoading || !effectiveApprovalEligible || isViewer}
                  onClick={onApproveClick}
                  className={`px-3 py-1.5 rounded-lg font-bold flex items-center gap-1 text-xs transition-colors ${
                    effectiveApprovalEligible && !isViewer
                      ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm"
                      : "bg-slate-900 text-slate-500 border border-slate-800 cursor-not-allowed"
                  }`}
                  title={
                    isViewer
                      ? "Read-Only Viewer cannot approve policies (requires Administrator role)"
                      : effectiveApprovalEligible
                      ? "Approve policy for production baseline"
                      : `Approval blocked — ${blockingReqCount} mandatory checks incomplete`
                  }
                >
                  <Check className="w-3.5 h-3.5" />
                  {effectiveApprovalEligible && !isViewer ? "Approve" : "Approval Blocked"}
                </button>
                {(!effectiveApprovalEligible || isViewer) && (
                  <button
                    type="button"
                    onClick={() => {
                      const el = document.getElementById("guided-readiness-checklist");
                      if (el) el.scrollIntoView({ behavior: "smooth" });
                    }}
                    className="text-[11px] text-amber-400 hover:text-amber-300 underline font-medium cursor-pointer"
                    title="View incomplete requirements in checklist"
                  >
                    View Requirements
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 2. BALANCED 12-COLUMN MAIN & CONTEXT WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
        {/* LEFT 8 COLUMNS: PRIMARY ACTIONABLE WORKFLOW */}
        <div className="lg:col-span-8 space-y-3.5">
          {/* Smart Next Action Card */}
          <NextActionCard
            title={smartAction.title}
            description={smartAction.description}
            actionLabel={smartAction.label}
            onAction={smartAction.action}
            status={smartAction.status as any}
          />

          {/* Guided Production Readiness Checklist (6 Stages) */}
          <div id="guided-readiness-checklist" className="p-3 sm:p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-cyan-400" />
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Guided Production Readiness Checklist
                </h2>
              </div>
              <span className="text-[10px] text-slate-400">
                L1-Friendly Validation Cascade · Progressive Technical Disclosure
              </span>
            </div>

            <div className="space-y-2.5">
              {stages.map((stage) => {
                const isExpanded = !!expandedStageDetails[stage.stage_id];
                const isCompleted = stage.status === "COMPLETED";
                const isBlocked = stage.status === "BLOCKED";
                const isNeedsAction = stage.status === "NEEDS_ACTION";

                const statusColors = {
                  COMPLETED: "border-emerald-900/60 bg-emerald-950/20 text-emerald-300",
                  BLOCKED: "border-rose-900/60 bg-rose-950/20 text-rose-300",
                  NEEDS_ACTION: "border-amber-900/60 bg-amber-950/20 text-amber-300",
                  PENDING: "border-slate-800 bg-slate-950/40 text-slate-400",
                }[stage.status];

                const statusBadgeColors = {
                  COMPLETED: "bg-emerald-950 text-emerald-300 border-emerald-800",
                  BLOCKED: "bg-rose-950 text-rose-300 border-rose-800",
                  NEEDS_ACTION: "bg-amber-950 text-amber-300 border-amber-800",
                  PENDING: "bg-slate-900 text-slate-400 border-slate-800",
                }[stage.status];

                const statusIcon = {
                  COMPLETED: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />,
                  BLOCKED: <XCircle className="w-4 h-4 text-rose-400 shrink-0" />,
                  NEEDS_ACTION: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />,
                  PENDING: <Clock className="w-4 h-4 text-slate-500 shrink-0" />,
                }[stage.status];

                return (
                  <div
                    key={stage.stage_id}
                    data-testid={`readiness-stage-${stage.stage_id}`}
                    data-stage-status={stage.status}
                    className={`p-3 rounded-xl border transition-all text-xs space-y-2 ${statusColors}`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-start gap-2.5 min-w-0">
                        <span className="w-5 h-5 rounded-full bg-slate-900 border border-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300 shrink-0 mt-0.5 font-mono">
                          {stage.stage_number}
                        </span>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-bold text-slate-100 text-xs">
                              {stage.stage_name}
                            </span>
                            <span className={`px-2 py-0.2 rounded text-[9px] font-bold uppercase border flex items-center gap-1 ${statusBadgeColors}`}>
                              {statusIcon}
                              {stage.status.replace(/_/g, " ")}
                            </span>
                          </div>
                          <div className="space-y-1 pt-1.5 text-[11px]">
                            <p className="text-slate-300">
                              <strong className="text-slate-200">What this check means:</strong> {stage.simple_explanation || STAGE_EXPLANATIONS[stage.stage_id]?.means}
                            </p>
                            <p className="text-slate-400">
                              <strong className="text-slate-300">Why it matters:</strong> {STAGE_EXPLANATIONS[stage.stage_id]?.why}
                            </p>
                            <p className="text-slate-400">
                              <strong className="text-slate-300">What is required to complete it:</strong> {stage.missing_requirement || STAGE_EXPLANATIONS[stage.stage_id]?.required}
                            </p>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 sm:self-center">
                        {stage.action_button && (
                          <button
                            type="button"
                            disabled={stage.stage_id === "production_approval" ? (!effectiveApprovalEligible || isViewer) : false}
                            onClick={() => handleStageAction(stage)}
                            title={
                              stage.stage_id === "production_approval"
                                ? isViewer
                                  ? "Read-Only Viewer cannot approve policies (requires Administrator role)"
                                  : !effectiveApprovalEligible
                                  ? `Approval blocked — ${blockingReqCount} mandatory checks incomplete`
                                  : "Approve policy for production baseline"
                                : undefined
                            }
                            className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold inline-flex items-center gap-1 transition-colors ${
                              stage.stage_id === "production_approval" && (!effectiveApprovalEligible || isViewer)
                                ? "bg-slate-900/60 text-slate-500 border border-slate-800 cursor-not-allowed opacity-60"
                                : "bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700"
                            }`}
                          >
                            {stage.action_button.label} <ArrowRight className="w-3 h-3 text-cyan-400" />
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Missing Requirement Alert */}
                    {stage.missing_requirement && (
                      <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800/80 text-[11px] space-y-0.5">
                        <span className="text-amber-400 font-bold block uppercase text-[9px]">Missing Requirement:</span>
                        <p className="text-slate-300">{stage.missing_requirement}</p>
                        <div className="text-[10px] text-cyan-300 pt-0.5">
                          <strong>Next Action:</strong> {stage.next_action}
                        </div>
                      </div>
                    )}

                    {/* Progressive Technical Details Disclosure */}
                    <div className="pt-1 flex items-center justify-between border-t border-slate-800/50 text-[10px]">
                      <span className="text-slate-400">
                        {isCompleted ? "Status: Criteria Verified" : isBlocked ? "Status: Action Required to Unblock" : "Status: Evaluation Pending"}
                      </span>
                      <button
                        type="button"
                        onClick={() => toggleStageDetails(stage.stage_id)}
                        className="text-cyan-400 hover:text-cyan-300 font-medium inline-flex items-center gap-0.5"
                      >
                        {isExpanded ? "Hide Technical Details" : "Show Technical Details (G1–G8 / Evidence)"}
                        <ChevronDown className={`w-3 h-3 transition-transform ${isExpanded ? "rotate-180" : ""}`} />
                      </button>
                    </div>

                    {isExpanded && (
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[10px] space-y-1.5 text-slate-300">
                        <span className="text-slate-400 block font-sans font-bold uppercase text-[9px]">Technical Verification Evidence:</span>
                        <pre className="overflow-x-auto text-[10px] text-slate-300 whitespace-pre-wrap leading-tight">
                          {JSON.stringify(stage.technical_details, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Consolidated Diagnostic Issues ("What Needs Attention?") */}
          <IssueSummary
            issues={consolidatedIssues}
            onNavigateToSection={(tab, section) => onNavigateTab(tab, section)}
          />
        </div>

        {/* RIGHT 4 COLUMNS: PRODUCTION READINESS & CONTEXT SIDEBAR */}
        <div className="lg:col-span-4 space-y-3.5">
          {/* Production Readiness Summary Card */}
          <div className="p-3.5 sm:p-4 rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-2.5">
              <div>
                <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  Production Readiness Summary
                </div>
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  <span className={`px-2 py-0.5 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${currentReadinessBadge.badge}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${currentReadinessBadge.dot}`} />
                    {currentReadinessBadge.label}
                  </span>
                </div>
              </div>

              <div className="text-right shrink-0">
                <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                  Readiness
                </div>
                <div className="text-xl sm:text-2xl font-extrabold text-cyan-300 font-mono tabular-nums">
                  {readinessProgress}%
                </div>
              </div>
            </div>

            <p className="text-[11px] text-slate-400 leading-relaxed">
              {currentReadinessBadge.desc}
            </p>

            {/* 4 Hero Key Metrics (2x2 Grid) */}
            <div className="grid grid-cols-2 gap-2">
              {/* Quality Gates */}
              <div
                onClick={() => onNavigateTab("advanced", "quality")}
                className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-cyan-700/60 cursor-pointer transition-colors"
              >
                <div className="text-[10px] text-slate-400 font-medium flex items-center justify-between">
                  <span>Quality Gates</span>
                  <Award className="w-3.5 h-3.5 text-sky-400" />
                </div>
                <div className="text-base font-bold font-mono text-slate-100 mt-1">
                  {passedGates} / 8 Passed
                </div>
                <div className="text-[9px] text-slate-500 mt-0.5 truncate">
                  {hasHardGateFailure ? "Blockers present" : "Static gates"}
                </div>
              </div>

              {/* Rule Quality Score */}
              <div
                onClick={() => onNavigateTab("advanced", "quality")}
                className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-cyan-700/60 cursor-pointer transition-colors"
              >
                <div className="text-[10px] text-slate-400 font-medium flex items-center justify-between">
                  <span>Rule Quality</span>
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                </div>
                <div className="text-base font-bold font-mono text-sky-300 mt-1">
                  {qualityScore !== null ? `${qualityScore}/100` : "Pending"}
                </div>
                <div className="text-[9px] text-slate-500 mt-0.5 truncate">
                  {qualityScore && qualityScore >= 70 ? "≥70 Standard" : "Improve (<70)"}
                </div>
              </div>

              {/* Verified Analyst Reviews */}
              <div
                onClick={() => onNavigateTab("learning")}
                className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-cyan-700/60 cursor-pointer transition-colors"
              >
                <div className="text-[10px] text-slate-400 font-medium flex items-center justify-between">
                  <span>Analyst Reviews</span>
                  <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" />
                </div>
                <div className="text-base font-bold font-mono text-emerald-400 mt-1">
                  {totalReviews} / 30
                </div>
                <div className="text-[9px] text-slate-500 mt-0.5 truncate">
                  {totalReviews >= 30 ? "Target met" : `${30 - totalReviews} to pilot`}
                </div>
              </div>

              {/* Empirical Accuracy */}
              <div
                onClick={() => onNavigateTab("learning")}
                className="p-2.5 rounded-xl border border-slate-800 bg-slate-950/60 hover:border-cyan-700/60 cursor-pointer transition-colors"
              >
                <div className="text-[10px] text-slate-400 font-medium flex items-center justify-between">
                  <span>AI Accuracy</span>
                  <Cpu className="w-3.5 h-3.5 text-amber-400" />
                </div>
                <div className="text-base font-bold font-mono text-slate-100 mt-1">
                  {accuracyDisplay}
                </div>
                <div className="text-[9px] text-slate-500 mt-0.5 truncate">
                  {totalReviews === 0 ? "Pending reviews" : "Verified sample"}
                </div>
              </div>
            </div>

            {/* Progress Bar & Last Evaluated Strip */}
            <div className="space-y-1 pt-1 border-t border-slate-800/60">
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Gating Cascade</span>
                <span className="font-semibold text-slate-200">
                  {completedStagesCount} of 6 Completed
                </span>
              </div>
              <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
                <div
                  className={`h-full transition-all ${
                    readinessProgress === 100 ? "bg-emerald-500" : readinessProgress >= 50 ? "bg-cyan-500" : "bg-amber-500"
                  }`}
                  style={{ width: `${readinessProgress}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-500 font-mono text-right">
                Last Evaluated: {readinessData?.last_evaluated_at ? new Date(readinessData.last_evaluated_at).toLocaleDateString() : "Never evaluated"}
              </div>
            </div>
          </div>

          {/* Evidence Contract Feasibility */}
          <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-200 flex items-center gap-1.5">
                <Database className="w-3.5 h-3.5 text-cyan-400" /> Evidence Contract Feasibility
              </span>
              <button
                type="button"
                onClick={() => onNavigateTab("advanced", "contract")}
                className="text-[10px] text-cyan-400 hover:underline inline-flex items-center gap-0.5"
              >
                Details <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <EvidenceCompletenessIndicator
              requiredCount={
                intelligenceData?.candidate_evidence_contract?.core_fields?.length ||
                intelligenceData?.archetype_definition?.mandatory_core_fields?.length ||
                5
              }
              availableCount={intelligenceData?.semantics?.relevant_fields?.length || 5}
              missingCount={intelligenceData?.semantics?.missing_requirements?.length || 0}
              missingFields={intelligenceData?.semantics?.missing_requirements || []}
              isSemanticsVerified={
                intelligenceData?.semantics?.definition_status === "VERIFIED" &&
                (!intelligenceData?.semantics?.missing_requirements || intelligenceData.semantics.missing_requirements.length === 0)
              }
            />
          </div>

          {/* Ground Truth Calibration Progress */}
          <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <span className="font-bold text-slate-200 flex items-center gap-1.5">
                <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" /> Ground Truth Calibration
              </span>
              <button
                type="button"
                onClick={() => onNavigateTab("learning")}
                className="text-[10px] text-cyan-400 hover:underline inline-flex items-center gap-0.5"
              >
                Workbench <ArrowRight className="w-3 h-3" />
              </button>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-300">
              <span>Verified Reviews:</span>
              <strong className="text-slate-100">
                {totalReviews} / 30 <span className="text-slate-400 font-normal">(Pilot target)</span>
              </strong>
            </div>
            <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
              <div
                className={`h-full transition-all ${
                  totalReviews >= 30 ? "bg-emerald-500" : "bg-cyan-500"
                }`}
                style={{ width: `${Math.min(100, (totalReviews / 30) * 100)}%` }}
              />
            </div>
            <p className="text-[10px] text-slate-400">
              Double-blind evaluations prevent human confirmation bias. Minimum 30 samples required for supervised pilot.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
