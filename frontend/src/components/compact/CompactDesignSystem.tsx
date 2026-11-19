"use client";

import React, { useState, useRef, useEffect, ReactNode } from "react";
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
  History,
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
  siemStatus?: {
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
  siemStatus,
  backAction,
  actions,
  selector,
}: CompactPageHeaderProps) {
  return (
    <div className="p-3 sm:px-4 rounded-xl theme-glass-panel border border-slate-800/80 bg-slate-950/70 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
      <div className="flex items-start sm:items-center gap-3 min-w-0 flex-1">
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

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 break-words leading-snug">
              {title}
            </h1>
            {archetype && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-900 text-cyan-300 border border-cyan-800/60 font-mono uppercase tracking-wide shrink-0">
                {archetype}
              </span>
            )}
            {siemStatus && (
              <span
                data-testid="header-siem-rule-status"
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border flex items-center gap-1.5 shrink-0 ${siemStatus.badgeClass}`}
                title="Authoritative FortiSIEM detection rule deployment status"
              >
                <span className={`w-1.5 h-1.5 rounded-full ${siemStatus.dotClass}`} />
                {siemStatus.label}
              </span>
            )}
            {lifecycleStatus && (
              <span
                data-testid="header-policy-lifecycle-status"
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border flex items-center gap-1.5 shrink-0 ${lifecycleStatus.badgeClass}`}
                title="AI policy lifecycle and readiness state"
              >
                <span className={`w-1.5 h-1.5 rounded-full ${lifecycleStatus.dotClass}`} />
                {lifecycleStatus.label}
              </span>
            )}
          </div>
          {subtitle && (
            <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-2 leading-relaxed">{subtitle}</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 shrink-0 self-start md:self-center">
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
  onOpenVersionHistory?: () => void;
  align?: "left" | "right";
}

export function CompactVersionSelector({
  versions,
  selectedVersionId,
  activeVersionId,
  onSelectVersion,
  onRollback,
  canRollback,
  onOpenVersionHistory,
  align = "left",
}: CompactVersionSelectorProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const selected = versions.find((v) => v.id === selectedVersionId) || versions[0];
  const isActive = selected?.id === activeVersionId;

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const alignClass = align === "right" ? "right-0" : "left-0";

  return (
    <div ref={containerRef} className="relative inline-block text-left">
      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          className={`px-2.5 py-1.5 rounded-lg border text-xs font-medium inline-flex items-center gap-2 transition-colors ${
            open
              ? "theme-version-selected text-white"
              : "bg-slate-900 border-slate-700 hover:border-slate-500 text-slate-200"
          }`}
          title="Switch policy prompt version"
        >
          <span className="text-slate-400 text-[11px]">Version:</span>
          <strong className="text-cyan-300 font-mono">v{selected?.version_number ?? 1}</strong>
          <span
            className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border ${
              selected?.status === "APPROVED"
                ? "bg-emerald-950/80 text-emerald-300 border-emerald-800/80"
                : selected?.status === "REVOKED"
                ? "bg-rose-950/80 text-rose-300 border-rose-800/80"
                : selected?.status === "ARCHIVED"
                ? "bg-slate-900 text-slate-400 border-slate-800"
                : "bg-amber-950/80 text-amber-300 border-amber-800/80"
            }`}
          >
            {selected?.status ?? "DRAFT"}
          </span>
          <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${open ? "rotate-180 text-amber-400" : ""}`} />
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
        <div className={`absolute ${alignClass} mt-1.5 w-72 sm:w-80 rounded-xl border border-slate-800/90 bg-slate-950/95 backdrop-blur-md shadow-2xl shadow-black/95 z-[100] p-1.5 space-y-1.5`}>
          <div className="px-2.5 py-1.5 text-[10px] uppercase font-bold text-slate-300 border-b border-slate-800/80 flex items-center justify-between">
            <span className="flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-amber-400" />
              <span>Version History</span>
            </span>
            <span className="text-[10px] text-slate-400 font-mono font-normal">
              {versions.length} {versions.length === 1 ? "version" : "versions"}
            </span>
          </div>
          <div className="max-h-64 overflow-y-auto space-y-1 pr-0.5">
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
                      ? "theme-version-selected font-semibold shadow-sm"
                      : "hover:bg-slate-900/80 text-slate-300 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-slate-100">v{ver.version_number}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded text-[9px] uppercase font-bold border ${
                        ver.status === "APPROVED"
                          ? "bg-emerald-950/80 text-emerald-300 border-emerald-800/80"
                          : ver.status === "REVOKED"
                          ? "bg-rose-950/80 text-rose-300 border-rose-800/80"
                          : ver.status === "ARCHIVED"
                          ? "bg-slate-900 text-slate-400 border-slate-800"
                          : "bg-amber-950/80 text-amber-300 border-amber-800/80"
                      }`}
                    >
                      {ver.status}
                    </span>
                    {isCurrActive && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-amber-950/90 text-amber-300 border border-amber-700/80">
                        Active
                      </span>
                    )}
                  </div>
                  {isCurrSelected && <Check className="w-3.5 h-3.5 text-amber-300 shrink-0" />}
                </button>
              );
            })}
          </div>
          {onOpenVersionHistory && (
            <div className="pt-1.5 border-t border-slate-800/80">
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  onOpenVersionHistory();
                }}
                className="w-full px-2.5 py-1.5 text-center text-[10px] text-amber-400 hover:text-amber-300 font-semibold flex items-center justify-center gap-1 hover:bg-slate-900/80 rounded transition-colors"
              >
                <span>Advanced Version History &amp; Controls</span>
                <ChevronRight className="w-3 h-3" />
              </button>
            </div>
          )}
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

// =============================================================================
// 11. COMPACT RULE SCOPE BAR (AI TRIAGE WORKBENCH)
// =============================================================================
export interface MatchedRuleItem {
  rule_uuid?: string | null;
  logical_rule_id: string;
  incident_count: number;
  event_type?: string | null;
}

export interface CompactRuleScopeBarProps {
  matchedRules: MatchedRuleItem[];
  distinctRuleCount: number;
  totalIncidents: number;
  exactRuleId: string;
  onSelectExactRule: (ruleId: string) => void;
  onClearExactRule: () => void;
  exactRuleLabel?: string | null;
}

export function CompactRuleScopeBar({
  matchedRules,
  distinctRuleCount,
  totalIncidents,
  exactRuleId,
  onSelectExactRule,
  onClearExactRule,
  exactRuleLabel,
}: CompactRuleScopeBarProps) {
  const [showAllChips, setShowAllChips] = useState(false);

  // If an exact rule is selected, show active filter banner
  if (exactRuleId) {
    const activeRule = matchedRules.find(
      (r) => (r.rule_uuid || r.logical_rule_id) === exactRuleId
    );
    const displayName = activeRule
      ? activeRule.logical_rule_id
      : exactRuleLabel || exactRuleId;

    return (
      <div
        data-testid="exact-rule-filter-banner"
        className="rounded-lg border border-cyan-800/80 bg-cyan-950/40 p-2.5 text-xs text-cyan-200 flex flex-wrap items-center justify-between gap-2 shadow-sm"
      >
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-cyan-400 shrink-0" />
          <span>
            Scoped to exact canonical rule:{" "}
            <strong className="text-white font-mono">{displayName}</strong>
            {activeRule?.rule_uuid && (
              <span className="text-slate-400 font-mono ml-1">
                [{activeRule.rule_uuid.slice(0, 8)}]
              </span>
            )}
            {" — "}
            <strong>{totalIncidents}</strong> matching incident(s) (aligned with AIS canonical rule filter).
          </span>
        </div>
        <button
          type="button"
          onClick={onClearExactRule}
          className="text-[10px] px-2.5 py-1 rounded border border-cyan-700 bg-slate-900 text-cyan-300 hover:text-white hover:bg-slate-800 transition-colors shrink-0"
        >
          Clear Exact Rule Filter
        </button>
      </div>
    );
  }

  // If multiple distinct rules matched, show compact scoped selector
  if (distinctRuleCount > 1) {
    const topRules = matchedRules.slice(0, 3);
    const hasMore = matchedRules.length > 3;

    return (
      <div
        data-testid="multi-rule-search-warning"
        className="rounded-lg border border-amber-700/80 bg-amber-950/30 p-2.5 text-xs text-amber-200 space-y-2 shadow-sm"
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-[11px] font-semibold">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
            <span>
              Results combine {distinctRuleCount} distinct SIEM rules across {totalIncidents} incidents. Select an exact canonical rule to avoid cross-rule confusion:
            </span>
          </div>

          {/* Quick Dropdown for 1-click jump among all rules */}
          <div className="flex items-center gap-1.5 shrink-0">
            <label htmlFor="canonical-rule-quick-select" className="sr-only">
              Select Canonical Rule
            </label>
            <select
              id="canonical-rule-quick-select"
              aria-label="Filter by Canonical Rule"
              value=""
              onChange={(e) => {
                if (e.target.value) {
                  onSelectExactRule(e.target.value);
                }
              }}
              className="bg-slate-900 border border-amber-800/80 rounded px-2 py-1 text-[11px] text-amber-100 font-mono focus:outline-none focus:ring-1 focus:ring-cyan-500"
            >
              <option value="">Jump to rule ({distinctRuleCount})...</option>
              {matchedRules.map((mr) => {
                const idVal = mr.rule_uuid || mr.logical_rule_id;
                return (
                  <option key={idVal} value={idVal}>
                    {mr.logical_rule_id} ({mr.incident_count})
                  </option>
                );
              })}
            </select>
          </div>
        </div>

        {/* Top 3 Frequent Rule Quick-Select Buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-amber-400/80 uppercase font-bold tracking-wider mr-1">
            Top Rules:
          </span>
          {(showAllChips ? matchedRules : topRules).map((mr) => (
            <button
              key={`${mr.rule_uuid || "unlinked"}-${mr.logical_rule_id}`}
              type="button"
              onClick={() => {
                onSelectExactRule(mr.rule_uuid || mr.logical_rule_id);
              }}
              className="px-2 py-0.5 rounded border border-amber-800/70 bg-slate-900/90 hover:bg-slate-800 text-[10px] font-mono text-amber-100 flex items-center gap-1.5 transition-colors"
              title={`UUID: ${mr.rule_uuid || "unlinked"} | Event: ${mr.event_type || "N/A"}`}
            >
              <span className="font-bold text-cyan-300">{mr.logical_rule_id}</span>
              {mr.rule_uuid && (
                <span className="text-slate-400">[{mr.rule_uuid.slice(0, 8)}]</span>
              )}
              <span className="px-1 rounded bg-amber-900/60 text-amber-200">{mr.incident_count}</span>
            </button>
          ))}

          {hasMore && (
            <button
              type="button"
              onClick={() => setShowAllChips(!showAllChips)}
              className="text-[10px] text-cyan-400 hover:text-cyan-300 underline font-medium px-1.5 py-0.5"
            >
              {showAllChips ? "Show Fewer" : `+${matchedRules.length - 3} more`}
            </button>
          )}
        </div>
      </div>
    );
  }

  return null;
}
