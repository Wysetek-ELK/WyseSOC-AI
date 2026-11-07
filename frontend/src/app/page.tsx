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
  Activity,
  FileCheck2,
} from "lucide-react";
import { api, DashboardMetrics } from "@/lib/api";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.getDashboardMetrics();
      setMetrics(data);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard metrics");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

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

  return (
    <div className="space-y-3.5">
      {/* Top Banner / Actions */}
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <Activity className="h-4 w-4 text-cyan-400" />
            SOC Incident Operations Dashboard
          </h1>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Real-time SIEM intelligence telemetry · Server 1 Application Foundation
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <Link
            href="/imports"
            className="flex items-center gap-1.5 rounded-md bg-cyan-600 px-2.5 py-1 text-xs font-medium text-white hover:bg-cyan-500 shadow-sm shadow-cyan-900/30 transition-colors"
          >
            <UploadCloud className="h-3.5 w-3.5" />
            Upload Incidents
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800/80 bg-rose-950/40 p-2.5 text-xs text-rose-300 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={loadData} className="underline hover:text-rose-200">
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {metrics?.is_empty ? (
        <div className="rounded-xl border border-dashed border-slate-800 bg-slate-900/40 p-8 text-center">
          <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-950/50 text-cyan-400 border border-cyan-800/60 mb-3">
            <UploadCloud className="h-5 w-5" />
          </div>
          <h2 className="text-base font-bold text-slate-100">No Incidents Imported Yet</h2>
          <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
            The database is currently empty. Ingest your historical SIEM incident JSON files or the provided{" "}
            <code className="text-cyan-400 font-mono">Incident json.zip</code> archive to initialize metrics and rule mapping.
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <Link
              href="/imports"
              className="inline-flex items-center gap-1.5 rounded-md bg-cyan-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-cyan-500"
            >
              <UploadCloud className="h-3.5 w-3.5" />
              Go to Ingestion Center
            </Link>
          </div>
        </div>
      ) : (
        <>
          {/* Top 5 Metric Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
            {/* Total Incidents */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>Total Imported</span>
                <AlertTriangle className="h-3.5 w-3.5 text-cyan-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-slate-100">
                {isLoading ? "..." : metrics?.total_incidents.toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">Verified DB Records</div>
            </div>

            {/* Total Rules */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>SIEM Rules</span>
                <FileCode2 className="h-3.5 w-3.5 text-blue-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-slate-100">
                {isLoading ? "..." : metrics?.total_rules.toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">Parsed & Active</div>
            </div>

            {/* Historical True Positives */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>True Positives</span>
                <CheckCircle2 className="h-3.5 w-3.5 text-rose-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-rose-400">
                {isLoading ? "..." : metrics?.historical_true_positives.toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">Historical Ground Truth</div>
            </div>

            {/* Historical False Positives */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>False Positives</span>
                <XCircle className="h-3.5 w-3.5 text-emerald-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-emerald-400">
                {isLoading ? "..." : metrics?.historical_false_positives.toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">Historical Ground Truth</div>
            </div>

            {/* Unresolved / Unlabeled */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm col-span-2 sm:col-span-1">
              <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
                <span>Unlabeled</span>
                <HelpCircle className="h-3.5 w-3.5 text-amber-400" />
              </div>
              <div className="mt-1 text-xl font-bold font-mono text-amber-400">
                {isLoading ? "..." : metrics?.unresolved_incidents.toLocaleString()}
              </div>
              <div className="mt-0.5 text-[10px] text-slate-500 font-mono">Pending Investigation</div>
            </div>
          </div>

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
                  href="/incidents"
                  className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                >
                  View All
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
                      <th className="pb-1.5 px-2 font-medium">Historical Ground Truth</th>
                      <th className="pb-1.5 px-2 font-medium text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    {metrics?.recent_activity.map((inc) => (
                      <tr key={inc.incident_id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-1.5 px-2 font-semibold text-slate-200">{inc.incident_id}</td>
                        <td className="py-1.5 px-2 text-slate-400 truncate max-w-[200px]" title={inc.event_type}>
                          {inc.event_type}
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
                          <span
                            className={`px-1.5 py-0.2 rounded border text-[9px] ${getVerdictBadge(
                              inc.historical_verdict
                            )}`}
                          >
                            {inc.historical_verdict || "Unlabeled"}
                          </span>
                        </td>
                        <td className="py-1.5 px-2 text-right font-sans">
                          <Link
                            href={`/incidents/${inc.incident_id}`}
                            className="text-cyan-400 hover:text-cyan-300 text-xs font-medium"
                          >
                            Explore →
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
                  Import History
                </h2>
                <Link
                  href="/imports"
                  className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                >
                  Manage
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
