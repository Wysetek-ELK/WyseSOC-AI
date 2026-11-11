"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  Search,
  Filter,
  Eye,
  EyeOff,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Shield,
  Clock,
  Layers,
  ArrowUpDown,
  DownloadCloud,
  Sparkles,
  Loader2,
  Bot,
  CheckCircle2,
  AlertCircle,
  X,
  Cpu,
  Database,
  RefreshCw,
} from "lucide-react";
import { api, IncidentListItem, IncidentAiVerdictResponse } from "@/lib/api";
import { useApp } from "@/context/AppContext";
import { formatExecutionProvenanceBadge } from "@/lib/provenance";
import { VerdictumLogo } from "@/components/brand/VerdictumLogo";

function AITriageWorkbenchContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { blindReviewMode, setBlindReviewMode } = useApp();

  const [incidents, setIncidents] = useState<IncidentListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(15);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [search, setSearch] = useState(searchParams.get("search") || "");
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [resolution, setResolution] = useState("");

  // AI Verdict Modal & Loading State
  const [analyzingId, setAnalyzingId] = useState<string | null>(null);
  const [aiVerdict, setAiVerdict] = useState<IncidentAiVerdictResponse | null>(null);
  const [verdictError, setVerdictError] = useState<string | null>(null);
  const [syncingResolutions, setSyncingResolutions] = useState(false);
  const [syncStatusMsg, setSyncStatusMsg] = useState<string | null>(null);
  const [llmOnline, setLlmOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getLlmStatus()
      .then((res) => {
        if (mounted) setLlmOnline(Boolean(res?.is_healthy));
      })
      .catch(() => {
        if (mounted) setLlmOnline(false);
      });
    const onStatus = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (mounted && detail && typeof detail.is_healthy === "boolean") {
        setLlmOnline(detail.is_healthy);
      }
    };
    window.addEventListener("llm-status-change", onStatus);
    return () => {
      mounted = false;
      window.removeEventListener("llm-status-change", onStatus);
    };
  }, []);

  const handleSyncResolutions = async () => {
    setSyncingResolutions(true);
    setSyncStatusMsg(null);
    try {
      const res = await api.syncFortiSiemResolutions();
      setSyncStatusMsg(res.message);
      loadIncidents();
      setTimeout(() => setSyncStatusMsg(null), 6000);
    } catch (err: any) {
      setSyncStatusMsg(`Sync error: ${err.message}`);
      setTimeout(() => setSyncStatusMsg(null), 6000);
    } finally {
      setSyncingResolutions(false);
    }
  };

  const handleRequestAiVerdict = async (incidentId: string) => {
    setAnalyzingId(incidentId);
    setVerdictError(null);
    try {
      const verdict = await api.getIncidentAiVerdict(incidentId);
      setAiVerdict(verdict);
      setIncidents((prev) =>
        prev.map((item) => (item.incident_id === incidentId ? { ...item, ai_verdict: verdict } : item))
      );
    } catch (err: any) {
      setVerdictError(err.message || "Failed to generate AI verdict from Local LLM.");
    } finally {
      setAnalyzingId(null);
    }
  };

  const loadIncidents = async () => {
    setIsLoading(true);
    try {
      const data = await api.getIncidents({
        page,
        page_size: pageSize,
        search: search || undefined,
        severity: severity || undefined,
        status: status || undefined,
        resolution: resolution || undefined,
        blind_review: blindReviewMode,
      });
      setIncidents(data.items);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
  }, [page, pageSize, severity, status, resolution, blindReviewMode]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadIncidents();
  };

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
    if (verdict.includes("Hidden")) {
      return "bg-amber-950/60 text-amber-400 border-amber-800/80 italic";
    }
    if (verdict.includes("True Positive")) {
      return "bg-rose-950/80 text-rose-300 border-rose-800";
    }
    if (verdict.includes("False Positive")) {
      return "bg-emerald-950/80 text-emerald-300 border-emerald-800";
    }
    return "bg-slate-800 text-slate-300 border-slate-700";
  };

  const formatEpoch = (epoch?: number) => {
    if (!epoch) return "N/A";
    const ms = epoch < 1e11 ? epoch * 1000 : epoch;
    return new Date(ms).toLocaleString([], {
      dateStyle: "short",
      timeStyle: "medium",
    });
  };

  const formatIncidentOccurredTime = (inc: IncidentListItem) => {
    const epoch = inc.first_seen_epoch || inc.created_at_epoch || inc.last_seen_epoch;
    if (epoch) {
      const ms = epoch < 1e11 ? epoch * 1000 : epoch;
      return new Date(ms).toLocaleString([], {
        dateStyle: "short",
        timeStyle: "medium",
      });
    }
    if (inc.created_at) {
      try {
        return new Date(inc.created_at).toLocaleString([], {
          dateStyle: "short",
          timeStyle: "medium",
        });
      } catch {
        return "N/A";
      }
    }
    return "N/A";
  };

  return (
    <div className="space-y-3">
      {/* Page Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-cyan-400" />
            AI Triage Workbench
          </h1>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Autonomous incident triage, evidence evaluation, and verdict reasoning
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleSyncResolutions}
            disabled={syncingResolutions}
            className="flex items-center gap-1.5 rounded-md border border-purple-800 bg-purple-950/60 px-2.5 py-1 text-xs font-semibold text-purple-300 hover:bg-purple-900/80 transition-colors shadow-sm disabled:opacity-50"
            title="Sync latest resolutions, cleared reasons, and closure status from FortiSIEM across all incidents"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${syncingResolutions ? "animate-spin text-purple-400" : "text-purple-400"}`} />
            <span>{syncingResolutions ? "Syncing..." : "Sync Resolutions"}</span>
          </button>

          <Link
            href="/telemetry-hub"
            className="flex items-center gap-1.5 rounded-md border border-cyan-800 bg-cyan-950/60 px-2.5 py-1 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/80 transition-colors shadow-sm"
          >
            <DownloadCloud className="h-3.5 w-3.5 text-cyan-400" />
            <span>Pull Telemetry</span>
          </Link>

          <button
            onClick={() => setBlindReviewMode(!blindReviewMode)}
            className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold transition-all ${
              blindReviewMode
                ? "border-amber-500/80 bg-amber-950/80 text-amber-300 shadow-md shadow-amber-950/50"
                : "border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            {blindReviewMode ? (
              <>
                <EyeOff className="h-3.5 w-3.5 text-amber-400" />
                <span>Blind Review: ACTIVE</span>
              </>
            ) : (
              <>
                <Eye className="h-3.5 w-3.5 text-slate-400" />
                <span>Blind Review: OFF</span>
              </>
            )}
          </button>
        </div>
      </div>

      {syncStatusMsg && (
        <div className="rounded-lg border border-purple-800/80 bg-purple-950/40 p-2.5 text-xs text-purple-300 flex items-center gap-2.5 animate-fadeIn">
          <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-purple-400" />
          <div className="text-[11px] leading-tight font-medium">
            {syncStatusMsg}
          </div>
        </div>
      )}

      {blindReviewMode && (
        <div className="rounded-lg border border-amber-800/80 bg-amber-950/40 p-2.5 text-xs text-amber-300 flex items-center gap-2.5">
          <EyeOff className="h-3.5 w-3.5 shrink-0 text-amber-400" />
          <div className="text-[11px] leading-tight">
            <strong className="font-semibold text-amber-200">Blind Review Active:</strong> Ground truth verdicts, resolution notes, and machine learning comments are masked.
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row gap-2 rounded-lg border border-slate-800 bg-slate-950 p-2 sm:p-2.5">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search Incident ID, Title, Source IP, Device or Event Type..."
            className="w-full rounded-md border border-slate-800 bg-slate-900 py-1 pl-8 pr-16 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
          <button
            type="submit"
            className="absolute right-1 top-1/2 -translate-y-1/2 rounded bg-cyan-600 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-cyan-500"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap gap-1.5 items-center">
          {/* Severity */}
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

          {/* Status */}
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="open">Open</option>
            <option value="closed">Closed</option>
          </select>

          {/* Historical Verdict */}
          {!blindReviewMode && (
            <select
              value={resolution}
              onChange={(e) => {
                setResolution(e.target.value);
                setPage(1);
              }}
              className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
            >
              <option value="">All Verdicts</option>
              <option value="True Positive">True Positive</option>
              <option value="False Positive">False Positive</option>
            </select>
          )}

          {(search || severity || status || resolution) && (
            <button
              onClick={() => {
                setSearch("");
                setSeverity("");
                setStatus("");
                setResolution("");
                setPage(1);
              }}
              className="rounded-md border border-slate-700 bg-slate-800 px-2.5 py-1 text-xs text-slate-300 hover:text-white"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      {/* Incidents Table */}
      <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60 text-[10px] font-mono text-slate-400">
                <th className="py-2 px-2.5 font-medium">Incident ID</th>
                <th className="py-2 px-2.5 font-medium">Rule / Event Type</th>
                <th className="py-2 px-2.5 font-medium">Severity</th>
                <th className="py-2 px-2.5 font-medium">Source / IP</th>
                <th className="py-2 px-2.5 font-medium">Occurred Time</th>
                <th className="py-2 px-2.5 font-medium">Events</th>
                <th className="py-2 px-2.5 font-medium">Historical Verdict</th>
                <th className="py-2 px-2.5 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-400 font-sans text-xs">
                    Loading incidents from database...
                  </td>
                </tr>
              ) : incidents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-8 text-center text-slate-500 font-sans text-xs">
                    No matching incidents found for the selected filter criteria.
                  </td>
                </tr>
              ) : (
                incidents.map((inc) => (
                  <tr key={inc.id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-1.5 px-2.5 font-bold text-slate-100">
                      <div className="flex items-center gap-1.5">
                        <Link
                          href={`/incidents/${inc.incident_id}`}
                          className="text-cyan-400 hover:underline"
                        >
                          {inc.incident_id}
                        </Link>
                      </div>
                      <div className="mt-0.5">
                        <span className={`px-1 py-0.2 rounded text-[8px] font-bold border ${
                          inc.status_name === "Manually Cleared"
                            ? "bg-purple-950/80 text-purple-300 border-purple-800"
                            : inc.status_code === 2
                            ? "bg-slate-900 text-slate-400 border-slate-800"
                            : "bg-blue-950/80 text-blue-300 border-blue-800"
                        }`}>
                          {inc.status_name}
                        </span>
                      </div>
                    </td>
                    <td className="py-1.5 px-2.5 text-slate-300">
                      <div className="font-semibold text-slate-200 truncate max-w-[200px]" title={inc.rule_name || inc.title}>
                        {inc.rule_name || inc.title}
                      </div>
                      <div className="text-[10px] text-slate-500 truncate max-w-[200px]" title={inc.event_type}>
                        {inc.event_type}
                      </div>
                    </td>
                    <td className="py-1.5 px-2.5">
                      <span
                        className={`px-1.5 py-0.2 rounded border text-[9px] font-bold ${getSeverityBadge(
                          inc.severity
                        )}`}
                      >
                        {inc.severity}
                      </span>
                    </td>
                    <td className="py-1.5 px-2.5 text-slate-400">
                      <div>{inc.source_ip || "Internal"}</div>
                      <div className="text-[10px] text-slate-500">{inc.reporting_device}</div>
                    </td>
                    <td className="py-1.5 px-2.5 text-slate-300 text-[10px]" suppressHydrationWarning>
                      <div className="font-medium text-slate-200" suppressHydrationWarning>
                        {formatIncidentOccurredTime(inc)}
                      </div>
                      {inc.last_seen_epoch && inc.first_seen_epoch && inc.last_seen_epoch !== inc.first_seen_epoch && (
                        <div className="text-[9px] text-slate-500" suppressHydrationWarning>
                          Last: {formatEpoch(inc.last_seen_epoch)}
                        </div>
                      )}
                    </td>
                    <td className="py-1.5 px-2.5 text-slate-300">
                      <span className="rounded bg-slate-900 px-1.5 py-0.2 text-[9px] border border-slate-800">
                        {inc.event_count} evts
                      </span>
                    </td>
                    <td className="py-1.5 px-2.5">
                      <div className="flex flex-col gap-1 items-start">
                        <span
                          className={`px-1.5 py-0.2 rounded border text-[9px] font-bold ${getVerdictBadge(
                            inc.historical_resolution
                          )}`}
                          title={`Historical SOC Analyst Closure Verdict${inc.cleared_user ? ` (Cleared by: ${inc.cleared_user})` : ""}${inc.cleared_reason ? ` | Reason: ${inc.cleared_reason}` : ""}`}
                        >
                          {inc.historical_resolution || "Unlabeled"}
                        </span>
                        {!blindReviewMode && (inc.cleared_user || inc.cleared_reason) && (
                          <div
                            className="text-[9px] text-slate-400 leading-tight max-w-[150px] truncate"
                            title={`Analyst: ${inc.cleared_user || "N/A"}${inc.cleared_reason ? ` | Reason: ${inc.cleared_reason}` : ""}`}
                          >
                            {inc.cleared_user && <span className="text-slate-300 font-mono">@{inc.cleared_user} </span>}
                            {inc.cleared_reason && <span className="text-slate-500 italic truncate">"{inc.cleared_reason}"</span>}
                          </div>
                        )}
                        {inc.ai_verdict && (
                          <span
                            className={`px-1.5 py-0.2 rounded border text-[9px] font-semibold flex items-center gap-1 ${
                              inc.ai_verdict.verdict === "TRUE_POSITIVE"
                                ? "bg-rose-950/80 text-rose-300 border-rose-800"
                                : inc.ai_verdict.verdict === "FALSE_POSITIVE"
                                ? "bg-emerald-950/80 text-emerald-300 border-emerald-800"
                                : "bg-amber-950/80 text-amber-300 border-amber-800"
                            }`}
                            title={`Stored AI Verdict: ${inc.ai_verdict.verdict} (${inc.ai_verdict.confidence}%) | Time: ${inc.ai_verdict.latency_ms}ms | Tokens: ${inc.ai_verdict.total_tokens || "N/A"}`}
                          >
                            <Sparkles className="h-2.5 w-2.5" />
                            AI: {inc.ai_verdict.verdict === "TRUE_POSITIVE" ? "TP" : inc.ai_verdict.verdict === "FALSE_POSITIVE" ? "FP" : "ATTN"}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-1.5 px-2.5 text-right font-sans">
                      <div className="flex items-center justify-end gap-1.5">
                        {inc.ai_verdict ? (
                          <button
                            onClick={() => {
                              setAiVerdict(inc.ai_verdict || null);
                              setVerdictError(null);
                            }}
                            className="inline-flex items-center gap-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-800/60 px-2 py-0.5 text-[11px] font-medium transition-all shadow-sm"
                            title="View stored AI verdict cached in database"
                          >
                            <Database className="h-3 w-3 text-cyan-400" />
                            <span>Stored Verdict</span>
                          </button>
                        ) : (
                          <button
                            onClick={() => handleRequestAiVerdict(inc.incident_id)}
                            disabled={analyzingId === inc.incident_id}
                            className="inline-flex items-center gap-1 rounded bg-emerald-950/70 hover:bg-emerald-900 text-emerald-300 border border-emerald-700/60 px-2 py-0.5 text-[11px] font-medium transition-all shadow-sm disabled:opacity-50"
                            title="Send to Server 2 Local LLM for instant AI security verdict"
                          >
                            {analyzingId === inc.incident_id ? (
                              <>
                                <Loader2 className="h-3 w-3 animate-spin text-emerald-400" />
                                <span>Analyzing...</span>
                              </>
                            ) : (
                              <>
                                <Sparkles className="h-3 w-3 text-emerald-400" />
                                <span>AI Verdict</span>
                              </>
                            )}
                          </button>
                        )}
                        <Link
                          href={`/incidents/${inc.incident_id}`}
                          className="inline-flex items-center gap-1 rounded bg-slate-900 px-2 py-0.5 text-[11px] font-medium text-cyan-400 hover:bg-slate-800 hover:text-cyan-300 border border-slate-800"
                        >
                          Inspect
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex items-center justify-between border-t border-slate-800 px-3 py-1.5 text-xs text-slate-400">
          <div>
            Showing <strong className="text-slate-200">{incidents.length}</strong> of{" "}
            <strong className="text-slate-200">{total}</strong> incidents
          </div>

          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="rounded p-0.5 border border-slate-800 bg-slate-900 text-slate-300 disabled:opacity-40 hover:bg-slate-800"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
            </button>
            <span className="font-mono text-slate-300 text-xs">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
              className="rounded p-0.5 border border-slate-800 bg-slate-900 text-slate-300 disabled:opacity-40 hover:bg-slate-800"
            >
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* AI Verdict Modal */}
      {(aiVerdict || verdictError) && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-xl rounded-xl border border-slate-800 bg-slate-950 p-5 shadow-2xl space-y-4 font-sans text-slate-200 animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <VerdictumLogo size={20} showWordmark={false} />
                  <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">
                    <Sparkles className="h-3.5 w-3.5" />
                    Server 2 AI Verdict
                  </span>
                  {aiVerdict && (
                    <span className="text-xs font-mono text-slate-400">
                      Incident #{aiVerdict.incident_id}
                    </span>
                  )}
                </div>
                <h3 className="text-sm font-semibold text-slate-100">
                  {aiVerdict?.rule_name || "Incident Security Analysis"}
                </h3>
              </div>
              <button
                onClick={() => {
                  setAiVerdict(null);
                  setVerdictError(null);
                }}
                className="rounded p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Error state */}
            {verdictError ? (
              <div className="rounded-lg border border-rose-800/80 bg-rose-950/40 p-4 text-xs text-rose-300 space-y-2">
                <div className="font-semibold flex items-center gap-1.5 text-rose-200">
                  <AlertCircle className="h-4 w-4 text-rose-400" />
                  Failed to Receive AI Verdict
                </div>
                <p className="text-[11px] text-rose-300/90">{verdictError}</p>
              </div>
            ) : aiVerdict && (
              <div className="space-y-3.5">
                {/* Verdict Banner */}
                <div
                  className={`rounded-lg border p-3 flex items-center justify-between ${
                    aiVerdict.verdict === "TRUE_POSITIVE"
                      ? "bg-rose-950/50 border-rose-800 text-rose-200"
                      : aiVerdict.verdict === "FALSE_POSITIVE"
                      ? "bg-emerald-950/50 border-emerald-800 text-emerald-200"
                      : "bg-amber-950/50 border-amber-800 text-amber-200"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    {aiVerdict.verdict === "TRUE_POSITIVE" ? (
                      <AlertTriangle className="h-5 w-5 text-rose-400" />
                    ) : aiVerdict.verdict === "FALSE_POSITIVE" ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                    ) : (
                      <AlertCircle className="h-5 w-5 text-amber-400" />
                    )}
                    <div>
                      <div className="text-[10px] uppercase font-mono tracking-wider opacity-80">
                        Model Determination
                      </div>
                      <div className="text-sm font-bold tracking-tight">
                        {aiVerdict.verdict.replace(/_/g, " ")}
                      </div>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-[10px] uppercase font-mono tracking-wider opacity-80">
                      Confidence
                    </div>
                    <div className="text-base font-extrabold font-mono">
                      {Math.round(aiVerdict.confidence)}%
                    </div>
                  </div>
                </div>

                {/* AI Reasoning */}
                <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-1">
                  <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
                    <Bot className="h-3 w-3 text-cyan-400" />
                    Analytical Justification
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed font-sans">
                    {aiVerdict.reason}
                  </p>
                </div>

                {/* Evidence points if any */}
                {aiVerdict.supporting_evidence && aiVerdict.supporting_evidence.length > 0 && (
                  <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-3 space-y-1.5">
                    <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                      Supporting Evidence Attributes
                    </div>
                    <ul className="text-xs space-y-1 text-slate-300 list-disc list-inside">
                      {aiVerdict.supporting_evidence.map((ev, idx) => (
                        <li key={idx} className="text-[11px] font-mono leading-tight">
                          {ev}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Missing Evidence / Questions if any */}
                {aiVerdict.missing_evidence && aiVerdict.missing_evidence.length > 0 && (
                  <div className="rounded-lg border border-amber-900/40 bg-amber-950/20 p-3 space-y-1.5">
                    <div className="text-[10px] font-mono uppercase text-amber-400 tracking-wider">
                      Missing Evidence / Context Needed
                    </div>
                    <ul className="text-xs space-y-1 text-amber-300 list-disc list-inside">
                      {aiVerdict.missing_evidence.map((me, idx) => (
                        <li key={idx} className="text-[11px] leading-tight">
                          {me}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Model Metadata Footer */}
                <div className="flex flex-col gap-2 text-[10px] font-mono text-slate-400 pt-2 border-t border-slate-800/80">
                  <div className="flex items-center justify-between">
                    <div>
                      Engine: <span className="text-slate-300">{aiVerdict.model_identifier}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 px-1.5 py-0.5 rounded text-[10px]">
                        <Database className="h-3 w-3" />
                        Stored in DB
                      </span>
                      {(() => {
                        const pb = formatExecutionProvenanceBadge({
                          executionProvenance: aiVerdict.execution_provenance,
                          isSimulated: aiVerdict.is_simulated,
                          validationStatus: aiVerdict.validation_status,
                          modelIdentifier: aiVerdict.model_identifier,
                          currentS2Health: llmOnline ? "ONLINE" : "OFFLINE",
                        });
                        const text =
                          aiVerdict.validation_status === "INVALID_MODEL_OUTPUT"
                            ? "• INVALID_MODEL_OUTPUT (Abstained)"
                            : pb.label === "SIMULATED"
                            ? "• SIMULATED (Non-Production)"
                            : ["POLICY_GUARD", "PREFLIGHT_GUARD", "TOKEN_BUDGET_GUARD", "VALIDATION_GUARD"].includes(pb.label)
                            ? `• Deterministic Guard (${aiVerdict.model_identifier || pb.label})`
                            : pb.label === "LIVE_PROVIDER"
                            ? llmOnline
                              ? `• LIVE_PROVIDER (${aiVerdict.model_identifier || "Server 2"}) • S2 Online`
                              : `• Historical Live Record (S2 Offline Now) • LIVE_PROVIDER`
                            : `• ${pb.label} (${aiVerdict.model_identifier || "Model"}) • S2: ${llmOnline ? "ONLINE" : "OFFLINE"}`;
                        return (
                          <span
                            className={`px-1.5 py-0.5 rounded border font-semibold ${pb.className}`}
                            title={pb.sublabel}
                          >
                            {text}
                          </span>
                        );
                      })()}
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 bg-slate-900/90 border border-slate-800 px-2.5 py-1.5 rounded text-slate-300">
                    <div className="flex items-center gap-1.5">
                      <Clock className="h-3 w-3 text-cyan-400" />
                      <span>Time Consumed:</span>
                      <strong className="text-white">
                        {aiVerdict.latency_ms} ms {aiVerdict.latency_ms ? `(${(aiVerdict.latency_ms / 1000).toFixed(2)}s)` : ""}
                      </strong>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Cpu className="h-3 w-3 text-purple-400" />
                      <span>Tokens:</span>
                      <strong className="text-purple-300">
                        {aiVerdict.total_tokens || 0}
                      </strong>
                      {(aiVerdict.prompt_tokens !== undefined || aiVerdict.completion_tokens !== undefined) && (
                        <span className="text-slate-500 text-[9px]">
                          ({aiVerdict.prompt_tokens || 0} prompt / {aiVerdict.completion_tokens || 0} completion)
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Modal Actions */}
            <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-800">
              <div>
                {aiVerdict && (
                  <button
                    onClick={() => handleRequestAiVerdict(aiVerdict.incident_id)}
                    disabled={analyzingId === aiVerdict.incident_id}
                    className="inline-flex items-center gap-1.5 rounded-md border border-emerald-700/80 bg-emerald-950/80 hover:bg-emerald-900 px-2.5 py-1 text-xs font-semibold text-emerald-300 shadow-sm transition-all disabled:opacity-50"
                    title="Re-run inference on Server 2 GPU"
                  >
                    {analyzingId === aiVerdict.incident_id ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-400" />
                        <span>Re-evaluating...</span>
                      </>
                    ) : (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 text-emerald-400" />
                        <span>Re-evaluate AI Verdict</span>
                      </>
                    )}
                  </button>
                )}
              </div>
              <div className="flex items-center gap-2">
                {aiVerdict && (
                  <Link
                    href={`/incidents/${aiVerdict.incident_id}`}
                    className="rounded-md border border-slate-700 bg-slate-800 px-3 py-1 text-xs font-medium text-slate-200 hover:bg-slate-700 transition-colors"
                  >
                    View Full Incident Detail
                  </Link>
                )}
                <button
                  onClick={() => {
                    setAiVerdict(null);
                    setVerdictError(null);
                  }}
                  className="rounded-md bg-cyan-600 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-500 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function AITriageWorkbenchPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center text-slate-400 text-xs font-mono">
          Loading AI Triage Workbench...
        </div>
      }
    >
      <AITriageWorkbenchContent />
    </Suspense>
  );
}
