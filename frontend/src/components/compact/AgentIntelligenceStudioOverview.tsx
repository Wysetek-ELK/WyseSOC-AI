"use client";

import React, { useMemo } from "react";
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
  ExternalLink,
} from "lucide-react";
import {
  extractConsolidatedIssues,
  deriveOperationalStatus,
  DiagnosticIssue,
} from "@/lib/diagnostics";
import {
  RuleStatusSummary,
  IssueSummary,
  NextActionCard,
  CompactVersionSelector,
  EvidenceCompletenessIndicator,
  StatusBadge,
} from "./CompactDesignSystem";
import {
  PolicyQualityAssessmentResponse,
  RuleIntelligenceData,
  PromptVersion,
  QualityGateResult,
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
}

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
}: AgentIntelligenceStudioOverviewProps) {
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

  // Operational status summary
  const operationalStatus = useMemo(() => {
    return deriveOperationalStatus({
      lifecycleStage: learningProfile?.lifecycle_stage,
      isApprovalEligible,
      isIncompleteDefinition,
      activeVersionStatus: selectedVersion?.status,
      hasHardGateFailure,
      totalAnalystReviews: learningProfile?.total_analyst_reviews || 0,
      qualityScore: qualityAssessment?.quality_score,
    });
  }, [
    learningProfile?.lifecycle_stage,
    isApprovalEligible,
    isIncompleteDefinition,
    selectedVersion?.status,
    hasHardGateFailure,
    learningProfile?.total_analyst_reviews,
    qualityAssessment?.quality_score,
  ]);

  const gateList: QualityGateResult[] = qualityAssessment?.gate_results
    ? Object.values(qualityAssessment.gate_results)
    : qualityAssessment?.gates || [];
  const passedGates = gateList.filter((g) => g.status === "PASSED").length;

  const totalReviews = learningProfile?.total_analyst_reviews || 0;
  const empiricalAccuracy = learningProfile?.empirical_accuracy;
  const isSelectedActive = selectedVersion?.id === activeVersionId;

  // Derive highest-priority next action
  const topNextAction = useMemo(() => {
    if (isIncompleteDefinition) {
      return {
        title: "Detection Rule Definition Requires Verification",
        description:
          "Authoritative correlation conditions and thresholds are missing. Review the FortiSIEM detection rule specifications to unblock production approval.",
        label: "Inspect Semantics",
        action: () => onNavigateTab("advanced", "intelligence"),
        status: "warning" as const,
      };
    }

    if (totalReviews === 0) {
      return {
        title: "Initiate Ground Truth Calibration",
        description:
          "AI accuracy cannot be verified without independent analyst reviews. Conduct double-blind evaluations on pending incidents to calibrate the model.",
        label: "Review Incidents",
        action: () => onNavigateTab("learning"),
        status: "primary" as const,
      };
    }

    if (!qualityAssessment || qualityAssessment.quality_score < 70) {
      return {
        title: "Validate Policy Quality Requirements",
        description:
          "Verify that G1–G8 validation criteria and evidence bindings satisfy production standards.",
        label: "Run Quality Validation",
        action: onValidateQuality,
        status: "primary" as const,
      };
    }

    if (isApprovalEligible && selectedVersion?.status !== "APPROVED") {
      return {
        title: "Policy Ready for Production Approval",
        description:
          "All static quality gates and preliminary empirical requirements have been satisfied.",
        label: "Approve & Activate",
        action: onApproveClick,
        status: "success" as const,
      };
    }

    return {
      title: "Continue Supervised Rule Learning",
      description:
        `Review additional incidents to expand the ground truth dataset (${totalReviews} / 100 reviews).`,
      label: "Open Review Queue",
      action: () => onNavigateTab("learning"),
      status: "primary" as const,
    };
  }, [
    isIncompleteDefinition,
    totalReviews,
    qualityAssessment,
    isApprovalEligible,
    selectedVersion?.status,
    onNavigateTab,
    onValidateQuality,
    onApproveClick,
  ]);

  return (
    <div className="space-y-3.5">
      {/* 1. Quick Action & Version Control Strip */}
      <div className="p-2.5 sm:px-3 rounded-xl border border-slate-800/80 bg-slate-900/60 flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <CompactVersionSelector
            versions={versions}
            selectedVersionId={selectedVersion?.id || ""}
            activeVersionId={activeVersionId}
            onSelectVersion={onSelectVersion}
            onRollback={onRollback}
            canRollback={!isSelectedActive && !isViewer}
          />

          <span
            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border flex items-center gap-1.5 ${operationalStatus.badgeClass}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${operationalStatus.dotClass}`} />
            {operationalStatus.label}
          </span>
        </div>

        {/* Primary Action Buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            disabled={actionLoading}
            onClick={onGenerateIntelligentDraft}
            className="px-2.5 py-1.5 rounded-lg theme-primary-btn font-semibold flex items-center gap-1.5 text-xs transition-colors disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Synthesize Draft</span>
          </button>

          <button
            type="button"
            disabled={loadingQuality || isViewer}
            onClick={onValidateQuality}
            className="px-2.5 py-1.5 rounded-lg theme-secondary-btn font-medium flex items-center gap-1.5 text-xs transition-colors disabled:opacity-50"
          >
            <Award className="w-3.5 h-3.5 text-sky-400" />
            <span className="hidden sm:inline">Validate Quality</span>
          </button>

          <button
            type="button"
            disabled={loadingSimulation}
            onClick={onRunSimulation}
            className="px-2.5 py-1.5 rounded-lg theme-secondary-btn font-medium flex items-center gap-1.5 text-xs transition-colors disabled:opacity-50"
          >
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline">Simulation</span>
          </button>

          {selectedVersion && selectedVersion.status !== "APPROVED" && (
            <button
              type="button"
              disabled={actionLoading || !isApprovalEligible}
              onClick={onApproveClick}
              className={`px-3 py-1.5 rounded-lg font-bold flex items-center gap-1 text-xs transition-colors ${
                isApprovalEligible
                  ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                  : "bg-slate-900 text-slate-500 border border-slate-800 cursor-not-allowed"
              }`}
              title={
                isApprovalEligible
                  ? "Approve policy for production baseline"
                  : "Approval blocked by hard quality gate failures or incomplete rule specifications."
              }
            >
              <Check className="w-3.5 h-3.5" />
              Approve
            </button>
          )}
        </div>
      </div>

      {/* 2. Main 4-Metric Summary Row */}
      <RuleStatusSummary
        qualityScore={qualityAssessment?.quality_score ?? null}
        aiAccuracy={empiricalAccuracy}
        totalReviews={totalReviews}
        automationState={
          selectedVersion?.status === "APPROVED"
            ? "ACTIVE"
            : learningProfile?.lifecycle_stage === "SUPERVISED_PILOT"
            ? "PILOT"
            : isApprovalEligible
            ? "APPROVED"
            : "DISABLED"
        }
        operationalStatus={operationalStatus}
        onScoreClick={() => onNavigateTab("advanced", "quality")}
        onAccuracyClick={() => onNavigateTab("learning")}
        onReviewsClick={() => onNavigateTab("learning")}
      />

      {/* 3. Recommended Next Action */}
      <NextActionCard
        title={topNextAction.title}
        description={topNextAction.description}
        actionLabel={topNextAction.label}
        onAction={topNextAction.action}
        status={topNextAction.status}
      />

      {/* 4. "What Needs Attention?" Consolidated Diagnostic Section */}
      <IssueSummary
        issues={consolidatedIssues}
        onNavigateToSection={(tab, section) => onNavigateTab(tab, section)}
      />

      {/* 5. Compact Quick-Glance Health Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
        {/* Quality Gates Quick Glance */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-200 flex items-center gap-1.5">
              <Award className="w-3.5 h-3.5 text-sky-400" /> Quality Gates (G1–G8)
            </span>
            <button
              type="button"
              onClick={() => onNavigateTab("advanced", "quality")}
              className="text-[10px] text-cyan-400 hover:underline inline-flex items-center gap-0.5"
            >
              Details <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-300">
            <span>Passed Gates:</span>
            <strong className="text-slate-100">
              {gateList.length > 0 ? `${passedGates} / ${gateList.length}` : "Pending"}
            </strong>
          </div>
          <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
            <div
              className={`h-full transition-all ${
                passedGates === 8 ? "bg-emerald-500" : "bg-sky-500"
              }`}
              style={{
                width: `${gateList.length > 0 ? (passedGates / gateList.length) * 100 : 0}%`,
              }}
            />
          </div>
        </div>

        {/* Evidence Contract Quick Glance */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-200 flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-cyan-400" /> Evidence Contract
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
          />
        </div>

        {/* Learning Progress Quick Glance */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2 text-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-slate-200 flex items-center gap-1.5">
              <FileCheck2 className="w-3.5 h-3.5 text-emerald-400" /> Ground Truth Progress
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
        </div>
      </div>
    </div>
  );
}
