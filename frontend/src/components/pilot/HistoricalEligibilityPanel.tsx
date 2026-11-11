"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle,
  Database,
  Download,
  FileJson,
  FileSpreadsheet,
  Filter,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { api, HistoricalEligibilityReport } from "@/lib/api";

export default function HistoricalEligibilityPanel() {
  const [report, setReport] = useState<HistoricalEligibilityReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ruleFilter, setRuleFilter] = useState("");

  const loadReport = useCallback(async (rule?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getHistoricalEligibilityReport(rule?.trim() || undefined);
      setReport(res);
    } catch (err: any) {
      setError(err.message || "Failed to load historical eligibility report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  async function handleDownload(fmt: "json" | "csv") {
    try {
      const q = new URLSearchParams({ format: fmt });
      if (ruleFilter.trim()) q.set("rule_id", ruleFilter.trim());
      const token = typeof window !== "undefined" ? localStorage.getItem("ai_verdict_token") : null;
      const res = await fetch(`/api/verdict-intelligence/eligibility-report?${q.toString()}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `historical_eligibility_report.${fmt}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(err.message || "Failed to export eligibility report");
    }
  }

  const getEligibilityBadge = (status: string) => {
    if (status === "ELIGIBLE" || status === "G8_ELIGIBLE" || status === "CALIBRATION_ELIGIBLE") {
      return "bg-emerald-950 text-emerald-300 border-emerald-800";
    }
    return "bg-amber-950 text-amber-300 border-amber-800";
  };

  return (
    <div className="space-y-6" data-testid="historical-eligibility-panel">
      {/* Header & Controls */}
      <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-cyan-400" />
              Historical Evaluation &amp; Ground Truth Readiness Report
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Measures verified historical corpus sufficiency, deduplication, and holdout separation prior to G8 certification or probability calibration.
            </p>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-1.5 bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Filter rule_id..."
                value={ruleFilter}
                onChange={(e) => setRuleFilter(e.target.value)}
                className="bg-transparent text-xs text-white focus:outline-none w-32"
              />
            </div>
            <button
              type="button"
              onClick={() => loadReport(ruleFilter)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs text-white"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Apply
            </button>
            <button
              type="button"
              onClick={() => handleDownload("json")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/80 hover:bg-indigo-600 text-xs text-white"
            >
              <FileJson className="w-3.5 h-3.5" />
              Export JSON
            </button>
            <button
              type="button"
              onClick={() => handleDownload("csv")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-700/80 hover:bg-emerald-700 text-xs text-white"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              Export CSV
            </button>
          </div>
        </div>

        {error && (
          <div className="p-3 rounded-lg bg-red-950/50 border border-red-800 text-xs text-red-200 flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {report?.integrity_notice && (
          <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/60 text-xs text-amber-200 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400 mt-0.5" />
            <span>{report.integrity_notice}</span>
          </div>
        )}
      </div>

      {/* Summary Cards */}
      {report && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400">Available Incidents</span>
              <div className="text-2xl font-bold text-white font-mono mt-1">
                {report.summary.available_incident_count}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Duplicate Groups: {report.summary.duplicate_group_count}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400">Eligible Independent</span>
              <div className="text-2xl font-bold text-cyan-300 font-mono mt-1">
                {report.summary.eligible_independent_count}
              </div>
              <div className="text-[11px] text-slate-400 mt-1">
                Verified TP: {report.summary.verified_tp_count} • FP: {report.summary.verified_fp_count}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400">Excluded Cases</span>
              <div className="text-2xl font-bold text-amber-300 font-mono mt-1">
                {report.summary.disputed_count +
                  report.summary.insufficient_evidence_count +
                  report.summary.unverified_or_ml_count +
                  report.summary.synthetic_count}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Disputed: {report.summary.disputed_count} • Insufficient: {report.summary.insufficient_evidence_count} • Synthetic: {report.summary.synthetic_count}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400 block">G8 Certification Status</span>
              <span className={`inline-block mt-2 px-2 py-0.5 text-[11px] font-mono rounded border ${getEligibilityBadge(report.summary.g8_eligibility)}`}>
                {report.summary.g8_eligibility}
              </span>
              <div className="text-[10px] text-slate-500 mt-1">Requires ≥10 TP &amp; ≥10 FP verified</div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400 block">Calibration Readiness</span>
              <span className={`inline-block mt-2 px-2 py-0.5 text-[11px] font-mono rounded border ${getEligibilityBadge(report.summary.calibration_eligibility)}`}>
                {report.summary.calibration_eligibility}
              </span>
              <div className="text-[10px] text-slate-500 mt-1">Requires ≥30 independent verified</div>
            </div>
          </div>

          {/* Partitions + Missing Fields */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Holdout Partitions (Leakage Prevention)
              </h4>
              <div className="flex flex-wrap gap-2 text-xs font-mono">
                {Object.entries(report.summary.holdout_partitions || {}).map(([part, cnt]) => (
                  <span key={part} className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-200">
                    {part}: <strong>{cnt}</strong>
                  </span>
                ))}
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Top Missing Required Evidence Fields
              </h4>
              {report.summary.missing_evidence_fields.length === 0 ? (
                <div className="text-xs text-slate-500">No missing contract fields detected across scanned rules.</div>
              ) : (
                <div className="flex flex-wrap gap-2 text-xs font-mono">
                  {report.summary.missing_evidence_fields.slice(0, 8).map((f) => (
                    <span key={f.field} className="px-2 py-0.5 rounded bg-rose-950/50 border border-rose-800/60 text-rose-200">
                      {f.field}: {f.missing_count}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Per-Rule Breakdown */}
          <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800">
            <h4 className="text-sm font-semibold text-white mb-3">Per-Rule Eligibility Breakdown</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 pr-3">Rule</th>
                    <th className="py-2 pr-3">Available</th>
                    <th className="py-2 pr-3">Verified TP / FP</th>
                    <th className="py-2 pr-3">Eligible</th>
                    <th className="py-2 pr-3">Excluded (Disp/Insuff/Dup)</th>
                    <th className="py-2 pr-3">G8 Status</th>
                    <th className="py-2">Calibration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/70">
                  {report.rules.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-6 text-center text-slate-500">
                        No rules matched the current filter or corpus.
                      </td>
                    </tr>
                  ) : (
                    report.rules.map((r) => (
                      <tr key={r.rule_uuid} className="hover:bg-slate-950/50">
                        <td className="py-2.5 pr-3">
                          <div className="font-mono text-white">{r.rule_id}</div>
                          <div className="text-[11px] text-slate-400 truncate max-w-[240px]">{r.rule_name}</div>
                        </td>
                        <td className="py-2.5 pr-3 font-mono">{r.available_incident_count}</td>
                        <td className="py-2.5 pr-3 font-mono text-emerald-300">
                          {r.verified_tp_count} / {r.verified_fp_count}
                        </td>
                        <td className="py-2.5 pr-3 font-mono text-cyan-300 font-bold">{r.eligible_independent_count}</td>
                        <td className="py-2.5 pr-3 font-mono text-slate-400">
                          {r.disputed_count} / {r.insufficient_evidence_count} / {r.duplicate_excluded_count}
                        </td>
                        <td className="py-2.5 pr-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${getEligibilityBadge(r.g8_eligibility)}`}>
                            {r.g8_eligibility}
                          </span>
                        </td>
                        <td className="py-2.5">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${getEligibilityBadge(r.calibration_eligibility)}`}>
                            {r.calibration_eligibility}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
