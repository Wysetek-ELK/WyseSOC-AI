"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileCode2,
  Search,
  ExternalLink,
  Shield,
  ShieldCheck,
  AlertTriangle,
  Activity,
  Layers,
  CheckCircle,
  AlertCircle,
  RefreshCw,
  Sparkles,
  X,
} from "lucide-react";
import { api, RuleItem, RuleStatsResponse } from "@/lib/api";

export default function DetectionIntelligencePage() {
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [readinessFilter, setReadinessFilter] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [ruleStats, setRuleStats] = useState<RuleStatsResponse | null>(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [isSyncingRules, setIsSyncingRules] = useState(false);
  const [syncFeedback, setSyncFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const loadRuleStats = async () => {
    setIsLoadingStats(true);
    try {
      const stats = await api.getRuleStats();
      setRuleStats(stats);
    } catch (err) {
      console.error("Failed to load rule stats", err);
    } finally {
      setIsLoadingStats(false);
    }
  };

  const loadRules = async () => {
    setIsLoading(true);
    try {
      const data = await api.getRules({
        page,
        page_size: pageSize,
        search: search || undefined,
        severity: severity || undefined,
        status: status || undefined,
        readiness: readinessFilter || undefined,
      });
      setRules(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRuleStats();
  }, []);

  useEffect(() => {
    loadRules();
  }, [page, pageSize, severity, status, readinessFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadRules();
  };

  const handleSyncFortiSiemRules = async () => {
    setIsSyncingRules(true);
    setSyncFeedback(null);
    try {
      const res = await api.syncFortiSiemRules();
      setSyncFeedback({
        type: "success",
        text: res.message,
      });
      loadRules();
      loadRuleStats();
    } catch (err: any) {
      setSyncFeedback({
        type: "error",
        text: err.message || "Failed to synchronize rules from FortiSIEM",
      });
    } finally {
      setIsSyncingRules(false);
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev?.toUpperCase()) {
      case "CRITICAL":
        return "bg-rose-950 text-rose-300 border-rose-800";
      case "HIGH":
        return "bg-orange-950 text-orange-300 border-orange-800";
      case "MEDIUM":
        return "bg-amber-950 text-amber-300 border-amber-800";
      default:
        return "bg-blue-950 text-blue-300 border-blue-800";
    }
  };

  const getReadinessBadge = (status?: string) => {
    switch (status?.toUpperCase()) {
      case "ACTIVE":
        return {
          label: "ACTIVE",
          classes: "bg-emerald-950 text-emerald-300 border-emerald-800",
        };
      case "APPROVED":
        return {
          label: "APPROVED",
          classes: "bg-teal-950 text-teal-300 border-teal-800",
        };
      case "READY_FOR_APPROVAL":
        return {
          label: "READY FOR APPROVAL",
          classes: "bg-cyan-950 text-cyan-300 border-cyan-800 animate-pulse",
        };
      case "VALIDATING":
        return {
          label: "VALIDATING",
          classes: "bg-blue-950 text-blue-300 border-blue-800",
        };
      case "LEARNING":
        return {
          label: "LEARNING",
          classes: "bg-amber-950 text-amber-300 border-amber-800",
        };
      case "BLOCKED":
        return {
          label: "BLOCKED",
          classes: "bg-rose-950 text-rose-300 border-rose-800",
        };
      case "INCOMPLETE":
      default:
        return {
          label: status ? status.replace(/_/g, " ") : "INCOMPLETE",
          classes: "bg-slate-900 text-slate-400 border-slate-800",
        };
    }
  };

  return (
    <div className="space-y-3">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <FileCode2 className="h-4 w-4 text-cyan-400" />
            Detection Intelligence Registry
          </h1>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Registered detection rules, correlation patterns, and context intelligence registry
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleSyncFortiSiemRules}
            disabled={isSyncingRules}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-cyan-600 hover:bg-cyan-500 text-white disabled:opacity-50 transition-colors shadow-sm shadow-cyan-900/30"
          >
            <RefreshCw className={`h-3 w-3 ${isSyncingRules ? "animate-spin" : ""}`} />
            <span>{isSyncingRules ? "Syncing..." : "Sync Detection Rules"}</span>
          </button>
        </div>
      </div>

      {/* Sync Feedback Banner */}
      {syncFeedback && (
        <div
          className={`rounded-lg border p-2.5 text-xs flex items-center justify-between gap-3 ${
            syncFeedback.type === "success"
              ? "border-emerald-800 bg-emerald-950/40 text-emerald-300"
              : "border-rose-800 bg-rose-950/40 text-rose-300"
          }`}
        >
          <div className="flex items-center gap-2">
            {syncFeedback.type === "success" ? (
              <CheckCircle className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
            ) : (
              <AlertCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />
            )}
            <span>{syncFeedback.text}</span>
          </div>
          <button
            type="button"
            onClick={() => setSyncFeedback(null)}
            className="text-slate-400 hover:text-white"
          >
            <X className="h-3 w-3" />
          </button>
        </div>
      )}

      {/* 5 Rule Registry & Governance Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
        {/* Total Ingested Rules */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
            <span>Total Rules Ingested</span>
            <FileCode2 className="h-3.5 w-3.5 text-cyan-400" />
          </div>
          <div className="mt-1 text-xl font-bold font-mono text-slate-100">
            {isLoadingStats ? "..." : (ruleStats?.total_rules ?? total).toLocaleString()}
          </div>
          <div className="mt-0.5 text-[10px] text-cyan-400/80 font-mono flex items-center gap-1">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-cyan-400" />
            <span>Parsed in Registry</span>
          </div>
        </div>

        {/* Active Rules */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
            <span>Active Detections</span>
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          </div>
          <div className="mt-1 text-xl font-bold font-mono text-emerald-400">
            {isLoadingStats ? "..." : (ruleStats?.active_rules ?? 0).toLocaleString()}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500 font-mono">
            {ruleStats?.inactive_rules ? `${ruleStats.inactive_rules} Inactive` : "100% Active Coverage"}
          </div>
        </div>

        {/* Alert Correlation Coverage */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
            <span>Rules with Incidents</span>
            <Activity className="h-3.5 w-3.5 text-amber-400" />
          </div>
          <div className="mt-1 text-xl font-bold font-mono text-amber-300">
            {isLoadingStats ? "..." : `${ruleStats?.rules_with_incidents ?? 0} / ${ruleStats?.total_rules ?? total}`}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500 font-mono">
            {(ruleStats?.total_linked_incidents ?? 0).toLocaleString()} Linked Alerts
          </div>
        </div>

        {/* Critical & High Severity Rules */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 sm:p-3 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-[11px] font-medium">
            <span>Critical / High Rules</span>
            <AlertTriangle className="h-3.5 w-3.5 text-rose-400" />
          </div>
          <div className="mt-1 text-xl font-bold font-mono text-rose-400">
            {isLoadingStats ? "..." : `${(ruleStats?.critical_rules ?? 0) + (ruleStats?.high_rules ?? 0)}`}
          </div>
          <div className="mt-0.5 text-[10px] text-slate-500 font-mono">
            {ruleStats?.medium_rules ?? 0} Med · {ruleStats?.low_rules ?? 0} Low
          </div>
        </div>

        {/* Prompt Studio Governance */}
        <div className="rounded-lg border border-indigo-900/50 bg-gradient-to-br from-indigo-950/30 to-slate-950 p-2.5 sm:p-3 shadow-sm">
          <div className="flex items-center justify-between text-indigo-300 text-[11px] font-medium">
            <span>Prompt Studio Ready</span>
            <Sparkles className="h-3.5 w-3.5 text-indigo-400" />
          </div>
          <div className="mt-1 text-xl font-bold font-mono text-indigo-300">
            {isLoadingStats ? "..." : (ruleStats?.rules_with_prompt_templates ?? 0).toLocaleString()}
          </div>
          <div className="mt-0.5 text-[10px] text-indigo-400/80 font-mono">
            AI Triage Templates
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-2 rounded-lg border border-slate-800 bg-slate-950 p-2 sm:p-2.5">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rules by name, event type, data source, or pattern keywords..."
            className="w-full rounded-md border border-slate-800 bg-slate-900 py-1 pl-8 pr-16 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
          <button
            type="submit"
            className="absolute right-1 top-1/2 -translate-y-1/2 rounded bg-cyan-600 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-cyan-500"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap gap-2 items-center">
          <select
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value="">All Baseline Statuses</option>
            <option value="ACTIVE">Active Baseline</option>
            <option value="INACTIVE">Inactive Baseline</option>
          </select>

          <select
            value={readinessFilter}
            onChange={(e) => {
              setReadinessFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value="">All Production Readiness</option>
            <option value="BLOCKED">Blocked / Incomplete</option>
            <option value="LEARNING">Learning</option>
            <option value="VALIDATING">Validating</option>
            <option value="READY_FOR_APPROVAL">Ready for Approval</option>
            <option value="APPROVED">Approved</option>
            <option value="ACTIVE">Active</option>
          </select>
        </div>
      </div>

      {/* Rules Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60 text-[10px] font-mono text-slate-400">
                <th className="py-2 px-2.5 font-medium">Rule Name / Event Type</th>
                <th className="py-2 px-2.5 font-medium">Severity</th>
                <th className="py-2 px-2.5 font-medium">Baseline Status</th>
                <th className="py-2 px-2.5 font-medium">Production Readiness</th>
                <th className="py-2 px-2.5 font-medium">Data Source</th>
                <th className="py-2 px-2.5 font-medium">Linked Incidents</th>
                <th className="py-2 px-2.5 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400 font-sans text-xs">
                    Loading detection rules from database...
                  </td>
                </tr>
              ) : rules.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-sans text-xs">
                    No rules found in registry. Ingest a SIEM ZIP archive to automatically register rules.
                  </td>
                </tr>
              ) : (
                rules.map((rule) => {
                  const rBadge = getReadinessBadge(rule.production_readiness_status);
                  const gates = rule.gates_passed_count ?? 0;
                  const missing = rule.missing_requirements_count ?? 0;

                  return (
                    <tr key={rule.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-1.5 px-2.5 font-semibold text-slate-200">
                        <Link href={`/agent-intelligence-studio?rule_id=${rule.id}`} className="text-cyan-400 hover:underline">
                          {rule.name}
                        </Link>
                        <div className="text-[10px] text-slate-400 font-normal">
                          Event Type: <span className="text-slate-300">{rule.event_type}</span>
                        </div>
                      </td>
                      <td className="py-1.5 px-2.5">
                        <span
                          className={`px-1.5 py-0.2 rounded border text-[9px] font-bold ${getSeverityBadge(
                            rule.severity
                          )}`}
                        >
                          {rule.severity}
                        </span>
                      </td>
                      <td className="py-1.5 px-2.5">
                        <span
                          className={`px-1.5 py-0.2 rounded border text-[9px] font-bold ${
                            rule.status === "ACTIVE"
                              ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                              : "bg-slate-900 text-slate-400 border-slate-800"
                          }`}
                        >
                          {rule.status}
                        </span>
                      </td>
                      <td className="py-1.5 px-2.5">
                        <div className="flex flex-col gap-0.5">
                          <span className={`inline-block px-1.5 py-0.5 rounded border text-[9px] font-bold ${rBadge.classes} w-fit`}>
                            {rBadge.label}
                          </span>
                          <div className="text-[10px] text-slate-400 font-mono">
                            Gates: <span className="text-slate-300">{gates}/8</span>
                            {missing > 0 && (
                              <span className="ml-1.5 text-amber-400">({missing} missing)</span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="py-1.5 px-2.5 text-slate-300 truncate max-w-[200px]" title={rule.data_source}>
                        {rule.data_source || "SIEM Telemetry"}
                      </td>
                      <td className="py-1.5 px-2.5">
                        <Link
                          href={`/ai-triage-workbench?rule_id=${encodeURIComponent(rule.event_type)}`}
                          className="rounded bg-slate-900 px-2 py-0.5 text-[10px] text-cyan-300 border border-slate-800 hover:bg-slate-800 hover:border-cyan-800 transition-colors"
                        >
                          {rule.incident_count} Incidents →
                        </Link>
                      </td>
                      <td className="py-1.5 px-2.5 text-right font-sans">
                        <div className="inline-flex items-center gap-1.5 justify-end">
                          <Link
                            href={`/agent-intelligence-studio?rule_id=${rule.id}`}
                            className="inline-flex items-center gap-1 rounded bg-cyan-950/80 px-2 py-0.5 text-[11px] font-medium text-cyan-300 hover:bg-cyan-900 border border-cyan-800 shadow-sm"
                          >
                            Studio
                          </Link>
                          <Link
                            href={`/detection-intelligence/${rule.id}`}
                            className="inline-flex items-center gap-1 rounded bg-slate-900 px-2 py-0.5 text-[11px] font-medium text-slate-400 hover:bg-slate-800 hover:text-cyan-300 border border-slate-800"
                            title="View Detection Semantics & Context"
                          >
                            <ExternalLink className="h-3 w-3" />
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

