"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  FileCode2,
  Search,
  ExternalLink,
  Shield,
  Activity,
  Layers,
  CheckCircle,
  AlertCircle,
} from "lucide-react";
import { api, RuleItem } from "@/lib/api";

export default function RulesPage() {
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  const loadRules = async () => {
    setIsLoading(true);
    try {
      const data = await api.getRules({
        page,
        page_size: pageSize,
        search: search || undefined,
        severity: severity || undefined,
        status: status || undefined,
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
    loadRules();
  }, [page, pageSize, severity, status]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadRules();
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

  return (
    <div className="space-y-5">
      {/* Page Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
            <FileCode2 className="h-5 w-5 text-cyan-400" />
            SIEM Detection Rule Registry
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Registered detection rules, correlation patterns, and historical incident linkages
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search rules by name, event type, data source, or pattern keywords..."
            className="w-full rounded-lg border border-slate-800 bg-slate-900 py-1.5 pl-9 pr-20 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
          <button
            type="submit"
            className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded bg-cyan-600 px-2.5 py-1 text-[11px] font-medium text-white hover:bg-cyan-500"
          >
            Search
          </button>
        </form>

        <div className="flex gap-2.5">
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

          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs text-slate-300 focus:border-cyan-500 focus:outline-none"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        </div>
      </div>

      {/* Rules Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/60 text-[11px] font-mono text-slate-400">
                <th className="py-3 px-4 font-medium">Rule Name / Event Type</th>
                <th className="py-3 px-4 font-medium">Severity</th>
                <th className="py-3 px-4 font-medium">Status</th>
                <th className="py-3 px-4 font-medium">Data Source</th>
                <th className="py-3 px-4 font-medium">Linked Incidents</th>
                <th className="py-3 px-4 font-medium text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400 font-sans">
                    Loading detection rules from database...
                  </td>
                </tr>
              ) : rules.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500 font-sans">
                    No rules found in registry. Ingest a SIEM ZIP archive to automatically register rules.
                  </td>
                </tr>
              ) : (
                rules.map((rule) => (
                  <tr key={rule.id} className="hover:bg-slate-900/40 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-200">
                      <Link href={`/rules/${rule.id}`} className="text-cyan-400 hover:underline">
                        {rule.name}
                      </Link>
                      <div className="text-[10px] text-slate-400 font-normal mt-0.5">
                        Event Type: <span className="text-slate-300">{rule.event_type}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-bold ${getSeverityBadge(
                          rule.severity
                        )}`}
                      >
                        {rule.severity}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded border text-[10px] font-bold ${
                          rule.status === "ACTIVE"
                            ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                            : "bg-slate-900 text-slate-400 border-slate-800"
                        }`}
                      >
                        {rule.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300 truncate max-w-[220px]" title={rule.data_source}>
                      {rule.data_source || "SIEM Telemetry"}
                    </td>
                    <td className="py-3 px-4">
                      <Link
                        href={`/incidents?rule_id=${encodeURIComponent(rule.event_type)}`}
                        className="rounded bg-slate-900 px-2.5 py-1 text-[11px] text-cyan-300 border border-slate-800 hover:bg-slate-800 hover:border-cyan-800 transition-colors"
                      >
                        {rule.incident_count} Incidents →
                      </Link>
                    </td>
                    <td className="py-3 px-4 text-right font-sans">
                      <Link
                        href={`/rules/${rule.id}`}
                        className="inline-flex items-center gap-1 rounded bg-slate-900 px-2.5 py-1 text-xs font-medium text-cyan-400 hover:bg-slate-800 hover:text-cyan-300 border border-slate-800"
                      >
                        Details
                        <ExternalLink className="h-3 w-3" />
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

