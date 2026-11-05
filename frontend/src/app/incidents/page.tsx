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
} from "lucide-react";
import { api, IncidentListItem } from "@/lib/api";
import { useApp } from "@/context/AppContext";

function IncidentsContent() {
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
    return new Date(epoch).toLocaleString();
  };

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
            <AlertTriangle className="h-5 w-5 text-cyan-400" />
            SIEM Incident Explorer
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Explore, filter and inspect normalized SIEM incidents and evidence telemetry
          </p>
        </div>

        {/* Blind Review Banner Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setBlindReviewMode(!blindReviewMode)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all ${
              blindReviewMode
                ? "border-amber-500/80 bg-amber-950/80 text-amber-300 shadow-md shadow-amber-950/50"
                : "border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            {blindReviewMode ? (
              <>
                <EyeOff className="h-3.5 w-3.5 text-amber-400" />
                <span>Blind Review: ACTIVE (Labels Hidden)</span>
              </>
            ) : (
              <>
                <Eye className="h-3.5 w-3.5 text-slate-400" />
                <span>Enable Blind Review Mode</span>
              </>
            )}
          </button>
        </div>
      </div>

      {blindReviewMode && (
        <div className="rounded-xl border border-amber-800/80 bg-amber-950/40 p-3.5 text-xs text-amber-300 flex items-center gap-3">
          <EyeOff className="h-4 w-4 shrink-0 text-amber-400" />
          <div>
            <strong className="font-semibold text-amber-200">Blind Review Mode Active:</strong> Historical ground truth verdicts, resolution notes, and machine learning comments are masked across all listings and details so analysts can conduct independent, unbiased evaluations.
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by Incident ID, Title, Source IP, Device or Event Type..."
            className="w-full rounded-lg border border-slate-800 bg-slate-900 py-1.5 pl-9 pr-20 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
          <button
            type="submit"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded bg-cyan-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-cyan-500"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap gap-2.5">
          {/* Severity */}
          <select
            value={severity}
            onChange={(e) => {
              setSeverity(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
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
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
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
              className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
            >
              <option value="">All Historical Verdicts</option>
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
              className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:text-white"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Incidents Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60 text-[11px] font-mono text-slate-400">
                <th className="py-3 px-4 font-medium">Incident ID</th>
                <th className="py-3 px-4 font-medium">Rule / Event Type</th>
                <th className="py-3 px-4 font-medium">Severity</th>
                <th className="py-3 px-4 font-medium">Source / IP</th>
                <th className="py-3 px-4 font-medium">Created Time</th>
                <th className="py-3 px-4 font-medium">Events</th>
                <th className="py-3 px-4 font-medium">Historical Verdict</th>
                <th className="py-3 px-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400 font-sans">
                    Loading incidents from database...
                  </td>
                </tr>
              ) : incidents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 font-sans">
                    No matching incidents found for the selected filter criteria.
                  </td>
                </tr>
              ) : (
                incidents.map((inc) => (
                  <tr key={inc.id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-slate-100">
                      <Link
                        href={`/incidents/${inc.incident_id}`}
                        className="text-cyan-400 hover:underline"
                      >
                        {inc.incident_id}
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      <div className="font-semibold text-slate-200 truncate max-w-[220px]" title={inc.rule_name || inc.title}>
                        {inc.rule_name || inc.title}
                      </div>
                      <div className="text-[10px] text-slate-500 truncate max-w-[220px]" title={inc.event_type}>
                        {inc.event_type}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-bold ${getSeverityBadge(
                          inc.severity
                        )}`}
                      >
                        {inc.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      <div>{inc.source_ip || "Internal"}</div>
                      <div className="text-[10px] text-slate-500">{inc.reporting_device}</div>
                    </td>
                    <td className="py-3 px-4 text-slate-400 text-[11px]">
                      {formatEpoch(inc.created_at_epoch)}
                    </td>
                    <td className="py-3 px-4 text-slate-300">
                      <span className="rounded bg-slate-900 px-2 py-0.5 text-[10px] border border-slate-800">
                        {inc.event_count} evts
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] ${getVerdictBadge(
                          inc.historical_resolution
                        )}`}
                      >
                        {inc.historical_resolution || "Unlabeled"}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      <Link
                        href={`/incidents/${inc.incident_id}`}
                        className="inline-flex items-center gap-1 rounded bg-slate-900 px-2.5 py-1 text-xs font-medium text-cyan-400 hover:bg-slate-800 hover:text-cyan-300 border border-slate-800"
                      >
                        Inspect
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Bar */}
        <div className="flex items-center justify-between border-t border-slate-800 px-4 py-3 text-xs text-slate-400">
          <div>
            Showing <strong className="text-slate-200">{incidents.length}</strong> of{" "}
            <strong className="text-slate-200">{total}</strong> incidents
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page <= 1}
              className="rounded p-1 border border-slate-800 bg-slate-900 text-slate-300 disabled:opacity-40 hover:bg-slate-800"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="font-mono text-slate-300">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page >= totalPages}
              className="rounded p-1 border border-slate-800 bg-slate-900 text-slate-300 disabled:opacity-40 hover:bg-slate-800"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function IncidentsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-64 items-center justify-center text-slate-400 text-xs font-mono">
          Loading Incident Explorer...
        </div>
      }
    >
      <IncidentsContent />
    </Suspense>
  );
}
