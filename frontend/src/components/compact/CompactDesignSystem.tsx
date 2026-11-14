"use client";

import React, { useState, ReactNode } from "react";
import Link from "next/link";
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  XCircle,
  Info,
  Clock,
  ArrowRight,
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  Sparkles,
  Award,
  Cpu,
  Database,
  Check,
  X,
  ExternalLink,
  Layers,
  FileCheck2,
} from "lucide-react";
import { DiagnosticIssue, OperationalSummaryStatus } from "@/lib/diagnostics";

// =============================================================================
// 1. COMPACT PAGE HEADER
// =============================================================================
export interface CompactPageHeaderProps {
  title: string;
  subtitle?: string;
  archetype?: string;
  lifecycleStatus?: {
    label: string;
    badgeClass: string;
    dotClass: string;
  };
  backAction?: {
    label: string;
    onClick: () => void;
  };
  actions?: ReactNode;
  selector?: ReactNode;
}

export function CompactPageHeader({
  title,
  subtitle,
  archetype,
  lifecycleStatus,
  backAction,
  actions,
  selector,
}: CompactPageHeaderProps) {
  return (
    <div className="p-3 sm:px-4 rounded-xl theme-glass-panel border border-slate-800/80 bg-slate-950/70 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
      <div className="flex items-start sm:items-center gap-3 min-w-0">
        {backAction && (
          <button
            type="button"
            onClick={backAction.onClick}
            className="px-2.5 py-1.5 rounded-lg theme-secondary-btn text-xs font-semibold flex items-center gap-1.5 transition-colors shrink-0"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-cyan-400" />
            <span>{backAction.label}</span>
          </button>
        )}

        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 truncate">
              {title}
            </h1>
            {archetype && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-900 text-cyan-300 border border-cyan-800/60 font-mono uppercase tracking-wide">
                {archetype}
              </span>
            )}
            {lifecycleStatus && (
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border flex items-center gap-1.5 ${lifecycleStatus.badgeClass}`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${lifecycleStatus.dotClass}`} />
                {lifecycleStatus.label}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[11px] text-slate-400 mt-0.5 truncate">{subtitle}</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 shrink-0">
        {selector}
        {actions}
      </div>
    </div>
  );
}

// =============================================================================
// 2. METRIC SUMMARY CARD
// =============================================================================
export interface MetricSummaryCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  status?: "normal" | "success" | "warning" | "danger" | "neutral";
  icon?: ReactNode;
  badge?: string;
  onClick?: () => void;
}

export function MetricSummaryCard({
  label,
  value,
  subtext,
  status = "normal",
  icon,
  badge,
  onClick,
}: MetricSummaryCardProps) {
  const statusColors = {
    normal: "border-slate-800 bg-slate-900/60 text-slate-100",
    success: "border-emerald-900/60 bg-emerald-950/30 text-emerald-300",
    warning: "border-amber-900/60 bg-amber-950/30 text-amber-300",
    danger: "border-rose-900/60 bg-rose-950/30 text-rose-300",
    neutral: "border-slate-800/80 bg-slate-950/40 text-slate-400",
  };

  const Component = onClick ? "button" : "div";

  return (
    <Component
      onClick={onClick}
      className={`p-3 rounded-xl border transition-all text-left flex flex-col justify-between ${statusColors[status]} ${
        onClick ? "hover:border-cyan-700/60 cursor-pointer" : ""
      }`}
    >
      <div className="flex items-center justify-between gap-1 text-[11px] text-slate-400 font-medium">
        <span className="truncate">{label}</span>
        {badge && (
          <span className="px-1.5 py-0.2 rounded text-[9px] font-bold border border-slate-700 bg-slate-900/90 text-slate-300">
            {badge}
          </span>
        )}
        {icon && <span className="shrink-0">{icon}</span>}
      </div>
      <div className="mt-1 flex items-baseline gap-1.5">
        <span className="text-xl sm:text-2xl font-extrabold tracking-tight tabular-nums">
          {value}
        </span>
      </div>
      {subtext && (
        <span className="text-[10px] text-slate-400/90 mt-0.5 truncate">{subtext}</span>
      )}
    </Component>
  );
}

// =============================================================================
// 3. RULE STATUS SUMMARY (HERO 4-METRIC ROW)
// =============================================================================
export interface RuleStatusSummaryProps {
  qualityScore: number | null;
  aiAccuracy: number | null | undefined;
  totalReviews: number;
  automationState: "DISABLED" | "PILOT" | "APPROVED" | "ACTIVE" | string;
  operationalStatus: {
    label: string;
    badgeClass: string;
    dotClass: string;
  };
  onScoreClick?: () => void;
  onAccuracyClick?: () => void;
  onReviewsClick?: () => void;
}

export function RuleStatusSummary({
  qualityScore,
  aiAccuracy,
  totalReviews,
  automationState,
  operationalStatus,
  onScoreClick,
  onAccuracyClick,
  onReviewsClick,
}: RuleStatusSummaryProps) {
  // Accuracy display: NEVER display 0% if unverified
  const accuracyDisplay =
    aiAccuracy !== null && aiAccuracy !== undefined && totalReviews > 0
      ? `${(aiAccuracy * 100).toFixed(1)}%`
      : totalReviews === 0
      ? "N/A"
      : "Pending";

  const accuracySubtext =
    totalReviews === 0
      ? "Requires verified analyst reviews"
      : `${totalReviews} verified ground truth reviews`;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
      <MetricSummaryCard
        label="Rule Quality"
        value={qualityScore !== null ? `${qualityScore}/100` : "Pending"}
        subtext="G1–G8 validation score"
        status={qualityScore !== null && qualityScore >= 70 ? "success" : "warning"}
        icon={<Award className="w-4 h-4 text-sky-400" />}
        onClick={onScoreClick}
      />

      <MetricSummaryCard
        label="AI Accuracy"
        value={accuracyDisplay}
        subtext={accuracySubtext}
        status={
          totalReviews === 0
            ? "neutral"
            : aiAccuracy && aiAccuracy >= 0.85
            ? "success"
            : "warning"
        }
        icon={<Cpu className="w-4 h-4 text-cyan-400" />}
        onClick={onAccuracyClick}
      />

      <MetricSummaryCard
        label="Analyst Reviews"
        value={totalReviews}
        subtext={totalReviews >= 30 ? "Target met (≥30)" : `${30 - totalReviews} needed for pilot`}
        status={totalReviews >= 30 ? "success" : totalReviews > 0 ? "normal" : "warning"}
        icon={<FileCheck2 className="w-4 h-4 text-emerald-400" />}
        onClick={onReviewsClick}
      />

      <MetricSummaryCard
        label="Automation Status"
        value={automationState}
        subtext={operationalStatus.label}
        status={
          automationState === "ACTIVE"
            ? "success"
            : automationState === "PILOT"
            ? "normal"
            : "warning"
        }
        icon={<Shield className="w-4 h-4 text-amber-400" />}
      />
    </div>
  );
}

// =============================================================================
// 4. DIAGNOSTIC ISSUE CARD & ISSUE SUMMARY
// =============================================================================
export interface IssueSummaryProps {
  issues: DiagnosticIssue[];
  onNavigateToSection?: (tab: "overview" | "learning" | "advanced", section?: string) => void;
}

export function IssueSummary({ issues, onNavigateToSection }: IssueSummaryProps) {
  if (!issues || issues.length === 0) {
    return (
      <div className="p-3.5 rounded-xl border border-emerald-900/50 bg-emerald-950/20 text-emerald-300 text-xs flex items-center gap-2.5">
        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
        <div>
          <span className="font-bold">No Active Operational Blockers</span>
          <p className="text-[11px] text-emerald-400/90 mt-0.5">
            Rule specifications, evidence contracts, and governance safeguards are fully compliant.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
          <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
          What Needs Attention ({issues.length})
        </h2>
        <span className="text-[10px] text-slate-400">Prioritized by operational impact</span>
      </div>

      <div className="space-y-2">
        {issues.map((issue) => (
          <DiagnosticIssueCard
            key={issue.id}
            issue={issue}
            onActionClick={() => {
              if (onNavigateToSection && issue.targetTab) {
                onNavigateToSection(issue.targetTab, issue.targetAdvancedSection);
              }
            }}
          />
        ))}
      </div>
    </div>
  );
}

export interface DiagnosticIssueCardProps {
  issue: DiagnosticIssue;
  onActionClick?: () => void;
}

export function DiagnosticIssueCard({ issue, onActionClick }: DiagnosticIssueCardProps) {
  const [expanded, setExpanded] = useState(false);

  const severityStyles = {
    critical: "border-rose-900/70 bg-rose-950/30 text-rose-200",
    warning: "border-amber-900/70 bg-amber-950/25 text-amber-200",
    info: "border-blue-900/60 bg-blue-950/25 text-blue-200",
  };

  const iconMap = {
    critical: <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />,
    info: <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />,
  };

  return (
    <div className={`p-3 rounded-xl border text-xs transition-all ${severityStyles[issue.severity]}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2.5 min-w-0">
          {iconMap[issue.severity]}
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold text-slate-100">{issue.title}</span>
              {issue.rawCode && (
                <span className="font-mono text-[9px] px-1.5 py-0.2 rounded bg-slate-950/80 text-slate-400 border border-slate-800">
                  {issue.rawCode}
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-300/90 mt-0.5 leading-relaxed">
              <strong>Cause:</strong> {issue.cause}
            </p>
          </div>
        </div>

        {onActionClick && (
          <button
            type="button"
            onClick={onActionClick}
            className="px-2.5 py-1 rounded-lg bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-slate-700 text-[11px] font-semibold inline-flex items-center gap-1 shrink-0 transition-colors"
          >
            Fix <ArrowRight className="w-3 h-3 text-cyan-400" />
          </button>
        )}
      </div>

      <div className="mt-2 pt-2 border-t border-slate-800/60 flex flex-wrap items-center justify-between gap-2 text-[11px]">
        <div className="flex items-center gap-2 text-slate-300">
          <span className="text-slate-400">Next Action:</span>
          <span className="font-medium text-cyan-300">{issue.nextAction}</span>
        </div>

        {issue.missingInfo && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="text-[10px] text-slate-400 hover:text-slate-200 underline inline-flex items-center gap-0.5"
          >
            {expanded ? "Hide Details" : "Show Missing Details"}
          </button>
        )}
      </div>

      {expanded && issue.missingInfo && (
        <div className="mt-2 p-2 rounded-lg bg-slate-950/80 border border-slate-800 text-[11px] text-slate-300 font-mono">
          <span className="text-slate-400 block text-[10px] uppercase font-sans mb-1">Missing Elements:</span>
          {issue.missingInfo}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 5. NEXT ACTION CARD
// =============================================================================
export interface NextActionCardProps {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  status?: "primary" | "warning" | "success";
}

export function NextActionCard({
  title,
  description,
  actionLabel,
  onAction,
  status = "primary",
}: NextActionCardProps) {
  const styles = {
    primary: "border-cyan-800/70 bg-gradient-to-r from-cyan-950/40 via-slate-900/40 to-slate-950/40 text-cyan-200",
    warning: "border-amber-800/70 bg-amber-950/30 text-amber-200",
    success: "border-emerald-800/70 bg-emerald-950/30 text-emerald-200",
  };

  return (
    <div className={`p-3 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${styles[status]}`}>
      <div className="flex items-start gap-2.5">
        <Sparkles className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <span className="text-xs font-bold text-slate-100">{title}</span>
          <p className="text-[11px] text-slate-300/90 mt-0.5">{description}</p>
        </div>
      </div>

      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="px-3 py-1.5 rounded-lg theme-primary-btn text-xs font-semibold inline-flex items-center justify-center gap-1.5 shrink-0"
        >
          {actionLabel} <ArrowRight className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

// =============================================================================
// 6. COMPACT VERSION SELECTOR
// =============================================================================
export interface CompactVersionSelectorProps {
  versions: Array<{
    id: string;
    version_number: number;
    status: string;
    created_at?: string;
    author?: string;
  }>;
  selectedVersionId: string;
  activeVersionId?: string | null;
  onSelectVersion: (id: string) => void;
  onRollback?: () => void;
  canRollback?: boolean;
}

export function CompactVersionSelector({
  versions,
  selectedVersionId,
  activeVersionId,
  onSelectVersion,
  onRollback,
  canRollback,
}: CompactVersionSelectorProps) {
  const [open, setOpen] = useState(false);
  const selected = versions.find((v) => v.id === selectedVersionId) || versions[0];
  const isActive = selected?.id === activeVersionId;

  return (
    <div className="relative inline-block text-left">
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 hover:border-slate-600 text-xs text-slate-200 font-medium inline-flex items-center gap-2 transition-colors"
        >
          <span className="text-slate-400 text-[11px]">Version:</span>
          <strong className="text-cyan-300">v{selected?.version_number ?? 1}</strong>
          <span
            className={`px-1.5 py-0.2 rounded text-[9px] font-bold uppercase ${
              selected?.status === "APPROVED"
                ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                : "bg-amber-950 text-amber-400 border border-amber-800"
            }`}
          >
            {selected?.status ?? "DRAFT"}
          </span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
        </button>

        {!isActive && onRollback && canRollback && (
          <button
            type="button"
            onClick={onRollback}
            className="px-2 py-1.5 rounded-lg bg-amber-950/80 hover:bg-amber-900 text-amber-300 border border-amber-800/80 text-xs font-semibold inline-flex items-center gap-1 transition-colors"
            title="Rollback policy baseline to this version"
          >
            <RotateCcw className="w-3 h-3" />
            <span className="hidden sm:inline">Rollback</span>
          </button>
        )}
      </div>

      {open && (
        <div className="absolute right-0 mt-1 w-64 rounded-xl border border-slate-800 bg-slate-950 shadow-xl z-50 p-1.5 space-y-1">
          <div className="px-2 py-1 text-[10px] uppercase font-bold text-slate-400 border-b border-slate-800/80">
            Version History
          </div>
          <div className="max-h-60 overflow-y-auto space-y-1">
            {versions.map((ver) => {
              const isCurrActive = ver.id === activeVersionId;
              const isCurrSelected = ver.id === selectedVersionId;
              return (
                <button
                  key={ver.id}
                  type="button"
                  onClick={() => {
                    onSelectVersion(ver.id);
                    setOpen(false);
                  }}
                  className={`w-full px-2.5 py-2 rounded-lg text-left text-xs transition-colors flex items-center justify-between ${
                    isCurrSelected
                      ? "bg-slate-800 text-cyan-300 font-semibold"
                      : "hover:bg-slate-900 text-slate-300"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span>v{ver.version_number}</span>
                    <span
                      className={`px-1.5 py-0.2 rounded text-[9px] uppercase font-bold ${
                        ver.status === "APPROVED"
                          ? "bg-emerald-950 text-emerald-400"
                          : "bg-slate-900 text-slate-400"
                      }`}
                    >
                      {ver.status}
                    </span>
                    {isCurrActive && (
                      <span className="px-1 py-0.2 rounded text-[9px] bg-cyan-950 text-cyan-400 border border-cyan-800">
                        Active
                      </span>
                    )}
                  </div>
                  {isCurrSelected && <Check className="w-3.5 h-3.5 text-cyan-400" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 7. ADVANCED DETAILS PANEL (ACCESSIBLE COLLAPSIBLE)
// =============================================================================
export interface AdvancedDetailsPanelProps {
  title: string;
  badge?: string;
  defaultOpen?: boolean;
  children: ReactNode;
  icon?: ReactNode;
}

export function AdvancedDetailsPanel({
  title,
  badge,
  defaultOpen = false,
  children,
  icon,
}: AdvancedDetailsPanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="rounded-xl border border-slate-800/90 bg-slate-950/60 overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full p-3 flex items-center justify-between hover:bg-slate-900/50 transition-colors text-left"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          {icon || <ChevronRight className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? "rotate-90" : ""}`} />}
          <span className="text-xs font-bold text-slate-200">{title}</span>
          {badge && (
            <span className="px-1.5 py-0.2 rounded text-[9px] font-mono bg-slate-900 text-slate-400 border border-slate-800">
              {badge}
            </span>
          )}
        </div>
        <span className="text-[10px] text-slate-500 font-medium">
          {isOpen ? "Click to collapse" : "Click to inspect advanced details"}
        </span>
      </button>

      {isOpen && (
        <div className="p-3.5 pt-1 border-t border-slate-800/80 bg-slate-950/30">
          {children}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// 8. STATUS BADGE
// =============================================================================
export interface StatusBadgeProps {
  status: string;
  type?: "verdict" | "lifecycle" | "severity" | "gate";
  size?: "sm" | "md";
}

export function StatusBadge({ status, type = "verdict", size = "sm" }: StatusBadgeProps) {
  const s = (status || "").toUpperCase();

  let colorClass = "bg-slate-900 text-slate-300 border-slate-700";

  if (s === "TRUE_POSITIVE" || s === "TP") {
    colorClass = "bg-rose-950/80 text-rose-300 border-rose-800";
  } else if (s === "FALSE_POSITIVE" || s === "FP") {
    colorClass = "bg-emerald-950/80 text-emerald-300 border-emerald-800";
  } else if (s === "INSUFFICIENT_EVIDENCE") {
    colorClass = "bg-amber-950/80 text-amber-300 border-amber-800";
  } else if (s === "APPROVED" || s === "PASSED" || s === "ACTIVE") {
    colorClass = "bg-emerald-950/80 text-emerald-300 border-emerald-800";
  } else if (s === "CRITICAL") {
    colorClass = "bg-rose-950 text-rose-300 border-rose-800";
  } else if (s === "HIGH") {
    colorClass = "bg-orange-950 text-orange-300 border-orange-800";
  } else if (s === "MEDIUM") {
    colorClass = "bg-amber-950 text-amber-300 border-amber-800";
  } else if (s === "LOW") {
    colorClass = "bg-blue-950 text-blue-300 border-blue-800";
  }

  const padding = size === "sm" ? "px-1.5 py-0.2 text-[10px]" : "px-2.5 py-0.5 text-xs";

  return (
    <span className={`rounded font-bold border uppercase inline-flex items-center gap-1 ${padding} ${colorClass}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

// =============================================================================
// 9. EVIDENCE COMPLETENESS INDICATOR
// =============================================================================
export interface EvidenceCompletenessIndicatorProps {
  requiredCount: number;
  availableCount: number;
  missingCount: number;
  missingFields?: string[];
  isSemanticsVerified?: boolean;
}

export function EvidenceCompletenessIndicator({
  requiredCount,
  availableCount,
  missingCount,
  missingFields = [],
  isSemanticsVerified = true,
}: EvidenceCompletenessIndicatorProps) {
  // If semantics are unverified or missingCount > 0, field presence alone does NOT constitute 100% completeness
  const verifiedCount = Math.max(0, requiredCount - missingCount);
  const ratio =
    !isSemanticsVerified && missingCount === 0
      ? 50 // Unverified semantics cap at 50%
      : requiredCount > 0
      ? Math.min(100, Math.round((verifiedCount / requiredCount) * 100))
      : 100;

  const isFullyComplete = missingCount === 0 && isSemanticsVerified && verifiedCount >= requiredCount;

  return (
    <div className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-1.5 text-xs">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-slate-400 font-medium">Evidence Field Completeness:</span>
        <span className={`font-bold ${isFullyComplete ? "text-emerald-400" : "text-amber-400"}`}>
          {verifiedCount} / {requiredCount} ({ratio}%)
        </span>
      </div>

      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
        <div
          className={`h-full transition-all ${isFullyComplete ? "bg-emerald-500" : "bg-amber-500"}`}
          style={{ width: `${ratio}%` }}
        />
      </div>

      {!isSemanticsVerified ? (
        <p className="text-[10px] text-amber-300/90 truncate flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />
          <span>Evidence Semantics Unverified (Raw telemetry fields present but unvalidated)</span>
        </p>
      ) : missingCount > 0 ? (
        <p className="text-[10px] text-amber-300/90 truncate">
          Missing: {missingFields.join(", ")}
        </p>
      ) : null}
    </div>
  );
}

// =============================================================================
// 10. EMPTY STATE & ERROR STATE
// =============================================================================
export function EmptyState({
  title,
  message,
  actionLabel,
  onAction,
}: {
  title: string;
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="p-8 text-center rounded-xl border border-slate-800 bg-slate-950/40 text-slate-400 space-y-2">
      <div className="w-8 h-8 rounded-full bg-slate-900 border border-slate-800 mx-auto flex items-center justify-center text-slate-500">
        <Info className="w-4 h-4" />
      </div>
      <p className="text-sm font-semibold text-slate-200">{title}</p>
      <p className="text-xs text-slate-400 max-w-sm mx-auto">{message}</p>
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-2 px-3 py-1.5 rounded-lg theme-primary-btn text-xs font-semibold inline-flex items-center gap-1.5"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export function ErrorState({
  title = "Error Encountered",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="p-4 rounded-xl border border-rose-900/60 bg-rose-950/20 text-rose-300 text-xs flex items-start justify-between gap-3">
      <div className="flex items-start gap-2.5">
        <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold">{title}</span>
          <p className="text-[11px] text-rose-200/90 mt-0.5">{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="px-2.5 py-1 rounded bg-rose-900/60 hover:bg-rose-800 text-rose-200 border border-rose-700 text-xs font-semibold shrink-0"
        >
          Retry
        </button>
      )}
    </div>
  );
}
