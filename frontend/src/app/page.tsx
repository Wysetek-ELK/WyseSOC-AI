"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  AlertTriangle,
  FileCode2,
  CheckCircle2,
  XCircle,
  HelpCircle,
  UploadCloud,
  ArrowUpRight,
  RefreshCw,
  Clock,
  Layers,
  FileCheck2,
  Sparkles,
  Shield,
  Bot,
} from "lucide-react";
import { api, DashboardMetrics, PilotMetricsResponse } from "@/lib/api";
import { ServerInfrastructureMonitor } from "@/components/system/ServerInfrastructureMonitor";
import { BrandLogo } from "@/components/common/BrandLogo";

export default function AgentMissionControlPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [pilotMetrics, setPilotMetrics] = useState<PilotMetricsResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [mounted, setMounted] = useState<boolean>(false);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [isReconcilingPending, setIsReconcilingPending] = useState<boolean>(false);
  const [pendingNotice, setPendingNotice] = useState<string | null>(null);

  const handleReconcilePending = async () => {
    setIsReconcilingPending(true);
    setPendingNotice(null);
    try {
      const res = await api.processPendingFortiSiemVerdicts(100, true);
      setPendingNotice(res.message || "Pending verdict reconciliation triggered.");
      await loadData(false);
    } catch (err: unknown) {
      setPendingNotice(err instanceof Error ? err.message : "Failed to start pending verdict processing.");
    } finally {
      setIsReconcilingPending(false);
    }
  };

  const loadData = async (showSpinner: boolean = true) => {
    if (showSpinner) setIsLoading(true);
    setError(null);
    try {
      const [data, pilotRes] = await Promise.all([
        api.getDashboardMetrics(),
        api.getPilotMetrics().catch(() => null),
      ]);
      setMetrics(data);
      setPilotMetrics(pilotRes);
      setLastRefreshed(new Date());
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard metrics");
    } finally {
      if (showSpinner) setIsLoading(false);
    }
  };

  useEffect(() => {
    setMounted(true);
    setLastRefreshed(new Date());
    loadData(true);
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadData(false);
    }, 15000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const getSeverityBadge = (sev: string) => {
    switch (sev?.toUpperCase()) {
      case "CRITICAL":
        return "bg-rose-950 text-rose-300 border-rose-800";
      case "HIGH":
        return "bg-orange-950 text-orange-300 border-orange-800";
      case "MEDIUM":
        return "bg-amber-950 text-amber-300 border-amber-800";
      case "LOW":
        return "bg-blue-950 text-blue-300 border-blue-800";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const getVerdictBadge = (verdict?: string) => {
    if (!verdict) return "bg-slate-800 text-slate-400 border-slate-700";
    if (verdict.includes("True Positive")) {
      return "bg-rose-950/80 text-rose-300 border-rose-800";
    }
    if (verdict.includes("False Positive")) {
      return "bg-emerald-950/80 text-emerald-300 border-emerald-800";
    }
    return "bg-amber-950/80 text-amber-300 border-amber-800";
  };

  const getAiVerdictBadge = (aiVerdict?: any) => {
    if (!aiVerdict) {
      return (
        <span className="rounded bg-slate-900 border border-slate-800 px-1.5 py-0.2 text-[9px] text-slate-500 font-mono">
          Pending
        </span>
      );
    }
    const v = typeof aiVerdict === "object" ? aiVerdict.verdict : aiVerdict;
    if (v === "TRUE_POSITIVE") {
      return (
        <span className="rounded bg-rose-950/90 border border-rose-700 px-1.5 py-0.2 text-[9px] font-bold text-rose-300 font-mono shadow-sm">
          AI: TP
        </span>
      );
    }
    if (v === "FALSE_POSITIVE") {
      return (
        <span className="rounded bg-emerald-950/90 border border-emerald-700 px-1.5 py-0.2 text-[9px] font-bold text-emerald-300 font-mono shadow-sm">
          AI: FP
        </span>
      );
    }
    if (v === "REQUIRES_ATTENTION") {
      return (
        <span className="rounded bg-amber-950/90 border border-amber-700 px-1.5 py-0.2 text-[9px] font-bold text-amber-300 font-mono shadow-sm">
          AI: RA
        </span>
      );
    }
    return null;
  };

  const formatEpoch = (epoch?: number) => {
    if (!epoch) return "N/A";
    if (!mounted) return "--";
    const ms = epoch < 1e11 ? epoch * 1000 : epoch;
    try {
      return new Date(ms).toLocaleString([], {
        dateStyle: "short",
        timeStyle: "medium",
      });
    } catch {
      return String(epoch);
    }
  };

  return (
    <div className="space-y-2">
      {/* Top Banner / Actions */}
      <div className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <BrandLogo size={24} />
            Agent Mission Control
          </h1>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Agentic SOC Intelligence Platform · Evidence-Driven Security Intelligence
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Live Auto-Refresh Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ${
              autoRefresh
                ? "border-emerald-800 bg-emerald-950/60 text-emerald-300"
                : "border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
            title="Toggle automatic 15-second live dashboard polling"
          >
            <span className={`inline-block h-2 w-2 rounded-full ${autoRefresh ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
            <span>{autoRefresh ? "Live Sync: ON (15s)" : "Live Sync: OFF"}</span>
          </button>

          <button
            onClick={() => loadData(true)}
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <Link
            href="/telemetry-hub"
            className="flex items-center gap-1.5 rounded-md bg-cyan-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-cyan-500 shadow-sm shadow-cyan-900/30 transition-colors"
          >
            <UploadCloud className="h-3.5 w-3.5" />
            Ingest Telemetry
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800/80 bg-rose-950/40 p-2.5 text-xs text-rose-300 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => loadData(true)} className="underline hover:text-rose-200">
            Retry
          </button>
        </div>
      )}

      {/* Controlled SOC Pilot Status Banner */}
      {pilotMetrics && (
        <div className="rounded-lg border border-slate-800 bg-slate-950/90 px-3 py-2 flex flex-wrap items-center justify-between gap-2 text-xs" data-testid="mission-control-pilot-banner">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5 text-indigo-400" />
              SOC Pilot:
            </span>
            <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold border ${
              pilotMetrics.pilot.mode === "ANALYST_ASSISTED"
                ? "bg-emerald-950/70 text-emerald-300 border-emerald-700"
                : pilotMetrics.pilot.mode === "SHADOW"
                ? "bg-indigo-950/70 text-indigo-300 border-indigo-700"
                : "bg-slate-900 text-slate-400 border-slate-700"
            }`}>
              {pilotMetrics.pilot.mode}
            </span>
            {pilotMetrics.pilot.is_paused && (
              <span className="px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-700 text-[10px] font-mono">
                PAUSED
              </span>
            )}
            <span className="text-slate-400 font-mono text-[11px]">
              Evaluated: <strong className="text-white">{pilotMetrics.operational.incidents_evaluated}</strong> • Backlog:{" "}
              <strong className="text-slate-200">{pilotMetrics.operational.queue_backlog}</strong> • Verdictum Cortex:{" "}
              <strong className={pilotMetrics.operational.endpoint_provenance === "HTTP_MOCK" ? "text-cyan-300" : pilotMetrics.operational.provider_available ? "text-emerald-300" : "text-rose-300"}>
                {pilotMetrics.operational.endpoint_provenance === "HTTP_MOCK"
                  ? "HTTP_MOCK (TEST)"
                  : pilotMetrics.operational.current_s2_health || (pilotMetrics.operational.provider_available ? "ONLINE" : "OFFLINE")}
              </strong>
              {pilotMetrics.operational.test_environment ? ` • TEST_ENV=${pilotMetrics.operational.test_environment}` : ""}
            </span>
          </div>
          <Link
            href="/verdict-intelligence?tab=pilot"
            className="text-[11px] font-medium text-indigo-300 hover:text-indigo-200 flex items-center gap-1"
          >
            Pilot Console &amp; Metrics <ArrowUpRight className="h-3 w-3" />
          </Link>
        </div>
      )}

      {/* Empty State */}
      {metrics?.is_empty ? (
        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-8 text-center">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-950/50 text-cyan-400 border border-cyan-800/60 mb-3">
            <UploadCloud className="h-5 w-5" />
          </div>
          <h2 className="text-base font-bold text-slate-100">No Telemetry Ingested Yet</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
            The database is currently empty. Ingest your security incident JSON files or the provided{" "}
            <code className="text-cyan-400 font-mono">Incident json.zip</code> archive to initialize metrics and rule mapping.
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <Link
              href="/telemetry-hub"
              className="inline-flex items-center gap-1.5 rounded-md bg-cyan-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-cyan-500"
            >
              <UploadCloud className="h-3.5 w-3.5" />
              Go to Telemetry Hub
            </Link>
          </div>
        </div>
      ) : (
        <>
          {/* Top 5 AI & SOC Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
            {/* Total Incidents */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>Total Ingested</span>
                <AlertTriangle className="h-3.5 w-3.5 text-cyan-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-slate-100">
                {isLoading ? "..." : metrics?.total_incidents.toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">
                {metrics?.total_rules || 0} SIEM Rules Active
              </div>
            </div>

            {/* AI Triaged Progress */}
            <div className="rounded-lg border border-cyan-900/60 bg-gradient-to-br from-cyan-950/40 to-slate-950 p-2.5 sm:p-3 shadow-sm">
              <div className="flex items-center justify-between text-cyan-300 text-[11px] font-medium">
                <span>Agent Triaged</span>
                <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
              </div>
              <div className="mt-1 flex items-baseline justify-between gap-2">
                <div className="text-xl font-bold font-mono text-cyan-300">
                  {isLoading ? "..." : (metrics?.ai_evaluated_count ?? 0).toLocaleString()}
                </div>
                {!isLoading &&
                  metrics &&
                  metrics.total_incidents > (metrics.ai_evaluated_count || 0) && (
                    <button
                      type="button"
                      onClick={handleReconcilePending}
                      disabled={isReconcilingPending}
                      className="rounded border border-cyan-700/70 bg-cyan-950/80 px-1.5 py-0.5 text-[9px] font-mono font-semibold text-cyan-200 hover:bg-cyan-900/80 disabled:opacity-50 transition-colors"
                      title="Process remaining pending incidents with Verdictum Cortex Local LLM"
                    >
                      {isReconcilingPending
                        ? "Starting..."
                        : `Process ${(metrics.total_incidents - (metrics.ai_evaluated_count || 0)).toLocaleString()} Pending`}
                    </button>
                  )}
              </div>
              <div className="mt-0.5 text-[10px] text-cyan-400/80 font-mono">
                {metrics?.total_incidents
                  ? Math.round(((metrics.ai_evaluated_count || 0) / metrics.total_incidents) * 100)
                  : 0}% Triaged by Agent
              </div>
              {pendingNotice && (
                <div className="mt-1 text-[9px] font-mono text-amber-300 leading-snug" title={pendingNotice}>
                  {pendingNotice}
                </div>
              )}
            </div>

            {/* AI False Positives (Noise Auto-Dismissed) */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>Agent False Positives</span>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-emerald-400">
                {isLoading ? "..." : (metrics?.ai_false_positives ?? 0).toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">Noise Auto-Dismissed</div>
            </div>

            {/* AI True Positives (Confirmed Threats) */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>Agent True Positives</span>
                <ShieldAlert className="h-3.5 w-3.5 text-rose-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-rose-400">
                {isLoading ? "..." : (metrics?.ai_true_positives ?? 0).toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">Confirmed Threats</div>
            </div>

            {/* Requires Attention */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm col-span-2 sm:col-span-1">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>Human Review Queue</span>
                <HelpCircle className="h-3.5 w-3.5 text-amber-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-amber-400">
                {isLoading ? "..." : (metrics?.ai_requires_attention ?? 0).toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">Escalated to SOC Lead</div>
            </div>
          </div>

          {/* Historical Baseline Control & Live Telemetry Strip */}
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800/80 bg-slate-900/40 px-3 py-1.5 text-xs font-mono text-slate-400">
            <div className="flex items-center gap-2 flex-wrap">
              <Shield className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
              <span className="font-sans font-semibold text-slate-200">Historical Validation Baseline:</span>
              <span className="text-rose-400 font-semibold">{metrics?.historical_true_positives || 0} True Positives</span>
              <span className="text-slate-600">·</span>
              <span className="text-emerald-400 font-semibold">{metrics?.historical_false_positives || 0} False Positives</span>
              <span className="text-slate-600">·</span>
              <span className="text-slate-300 font-semibold">{metrics?.unresolved_incidents || 0} Live Unlabeled</span>
            </div>
            <div className="text-[11px] text-slate-500 flex items-center gap-1.5" suppressHydrationWarning>
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-400 animate-ping" />
              <span suppressHydrationWarning>
                {mounted && lastRefreshed ? `Synced ${lastRefreshed.toLocaleTimeString()}` : "Live Sync Active"}
              </span>
            </div>
          </div>

          {/* Dual-Server Infrastructure Utilization & Historical Telemetry */}
          <ServerInfrastructureMonitor />

          {/* Breakdown Charts Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-2.5 sm:gap-3">
            {/* Severity Distribution */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="flex items-center justify-between mb-2.5">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Incidents by Severity
                </h2>
                <span className="text-[10px] text-slate-500 font-mono">Actual DB Counts</span>
              </div>
              <div className="space-y-2">
                {metrics?.severity_breakdown.map((s) => (
                  <div key={s.severity} className="space-y-1">
                    <div className="flex justify-between text-[11px] font-medium">
                      <span className="text-slate-300">{s.severity}</span>
                      <span className="text-slate-400 font-mono">
                        {s.count} ({s.percentage}%)
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-900 overflow-hidden">
                      <div
                        className={`h-full ${
                          s.severity === "CRITICAL"
                            ? "bg-rose-500"
                            : s.severity === "HIGH"
                            ? "bg-orange-500"
                            : s.severity === "MEDIUM"
                            ? "bg-amber-500"
                            : "bg-blue-500"
                        }`}
                        style={{ width: `${Math.max(s.percentage, 5)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Source / Detection Rule Breakdown */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="flex items-center justify-between mb-2.5">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Top Ingestion Sources
                </h2>
                <span className="text-[10px] text-slate-500 font-mono">By Event Type</span>
              </div>
              <div className="space-y-2">
                {metrics?.source_breakdown.map((src) => (
                  <div key={src.source} className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-slate-300 truncate max-w-[200px]" title={src.source}>
                        {src.source}
                      </span>
                      <span className="text-slate-400 font-mono">{src.count}</span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-900 overflow-hidden">
                      <div
                        className="h-full bg-cyan-500"
                        style={{ width: `${Math.max(src.percentage, 5)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Ground Truth Breakdown */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="flex items-center justify-between mb-2.5">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Historical Ground Truth
                </h2>
                <span className="text-[10px] text-slate-500 font-mono">Isolated Table</span>
              </div>
              <div className="space-y-2">
                {metrics?.ground_truth_breakdown.map((gt) => (
                  <div key={gt.verdict} className="space-y-1">
                    <div className="flex justify-between text-[11px] font-medium">
                      <span className="text-slate-300">{gt.verdict}</span>
                      <span className="text-slate-400 font-mono">
                        {gt.count} ({gt.percentage}%)
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-slate-900 overflow-hidden">
                      <div
                        className={`h-full ${
                          gt.verdict.includes("True")
                            ? "bg-rose-500"
                            : gt.verdict.includes("False")
                            ? "bg-emerald-500"
                            : "bg-slate-600"
                        }`}
                        style={{ width: `${Math.max(gt.percentage, 5)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Activity Feed and Recent Import Jobs */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-2.5 sm:gap-3">
            {/* Recent Incident Activity Table */}
            <div className="lg:col-span-2 rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="flex items-center justify-between mb-2.5">
                <div className="flex items-center gap-2">
                  <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Recent Incident Activity
                  </h2>
                  <span className="rounded bg-slate-900 px-1.5 py-0.2 text-[10px] font-mono text-cyan-400 border border-slate-800">
                    Latest {metrics?.recent_activity.length}
                  </span>
                </div>
                <Link
                  href="/ai-triage-workbench"
                  className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                >
                  Inspect in Workbench
                  <ArrowUpRight className="h-3 w-3" />
                </Link>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-[10px] font-mono text-slate-400">
                      <th className="pb-1.5 px-2 font-medium">Incident ID</th>
                      <th className="pb-1.5 px-2 font-medium">Event Type</th>
                      <th className="pb-1.5 px-2 font-medium">Severity</th>
                      <th className="pb-1.5 px-2 font-medium">AI Verdict</th>
                      <th className="pb-1.5 px-2 font-medium">Historical Ground Truth</th>
                      <th className="pb-1.5 px-2 font-medium">Occurred</th>
                      <th className="pb-1.5 px-2 font-medium text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {metrics?.recent_activity.map((inc) => (
                      <tr key={inc.incident_id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-1.5 px-2 font-semibold text-slate-200">
                          <Link href={`/ai-triage-workbench/${inc.incident_id}`} className="text-cyan-400 hover:underline">
                            {inc.incident_id}
                          </Link>
                        </td>
                        <td className="py-1.5 px-2 text-slate-400 truncate max-w-[180px]" title={inc.title || inc.event_type}>
                          <div className="text-slate-200 truncate">{inc.title || inc.event_type}</div>
                          <div className="text-[10px] text-slate-500 truncate">{inc.event_type}</div>
                        </td>
                        <td className="py-1.5 px-2">
                          <span
                            className={`px-1.5 py-0.2 rounded border text-[9px] font-bold ${getSeverityBadge(
                              inc.severity
                            )}`}
                          >
                            {inc.severity}
                          </span>
                        </td>
                        <td className="py-1.5 px-2">
                          {getAiVerdictBadge(inc.ai_verdict)}
                        </td>
                        <td className="py-1.5 px-2">
                          <span
                            className={`px-1.5 py-0.2 rounded border text-[9px] ${getVerdictBadge(
                              inc.historical_verdict
                            )}`}
                          >
                            {inc.historical_verdict || "Unlabeled"}
                          </span>
                        </td>
                        <td className="py-1.5 px-2 text-slate-400 text-[10px]" suppressHydrationWarning>
                          {formatEpoch(inc.created_at_epoch)}
                        </td>
                        <td className="py-1.5 px-2 text-right font-sans">
                          <Link
                            href={`/ai-triage-workbench/${inc.incident_id}`}
                            className="text-cyan-400 hover:text-cyan-300 text-xs font-medium"
                          >
                            Triage →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Recent Import Jobs */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
              <div className="flex items-center justify-between mb-2.5">
                <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Telemetry Ingest History
                </h2>
                <Link
                  href="/telemetry-hub"
                  className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                >
                  Manage Hub
                  <ArrowUpRight className="h-3 w-3" />
                </Link>
              </div>

              <div className="space-y-2">
                {metrics?.recent_imports.length === 0 ? (
                  <p className="text-xs text-slate-500 py-3 text-center">No imports recorded</p>
                ) : (
                  metrics?.recent_imports.map((job) => (
                    <div
                      key={job.id}
                      className="rounded-md border border-slate-800 bg-slate-900/60 p-2 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-slate-200 truncate max-w-[170px]" title={job.filename}>
                          {job.filename}
                        </span>
                        <span
                          className={`text-[9px] px-1.5 py-0.2 rounded uppercase font-mono font-bold ${
                            job.status === "COMPLETED"
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                              : "bg-amber-950 text-amber-300 border border-amber-800"
                          }`}
                        >
                          {job.status}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                        <span>Imported: {job.imported_count}</span>
                        <span>Dup: {job.duplicate_count}</span>
                        <span>Err: {job.error_count}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
