"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  BookOpen,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  Sparkles,
  Database,
  Cpu,
  Layers,
  ArrowRight,
  Eye,
  Check,
  X,
  Info,
  SlidersHorizontal,
  ChevronRight,
} from "lucide-react";
import { api, LearningRecord, SimilarCaseMatch, RuleItem } from "@/lib/api";

export default function LearningHistoryPage() {
  const [records, setRecords] = useState<LearningRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [ruleFilter, setRuleFilter] = useState("");
  const [verdictFilter, setVerdictFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");

  const [rules, setRules] = useState<RuleItem[]>([]);
  const [seedingLoading, setSeedingLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Similar cases search tool
  const [simQueryIncidentId, setSimQueryIncidentId] = useState("");
  const [simQueryCommand, setSimQueryCommand] = useState("");
  const [simQueryIp, setSimQueryIp] = useState("");
  const [simMatches, setSimMatches] = useState<SimilarCaseMatch[]>([]);
  const [simSearching, setSimSearching] = useState(false);
  const [simSearched, setSimSearched] = useState(false);

  // Detail Modal
  const [activeRecord, setActiveRecord] = useState<LearningRecord | null>(null);

  const fetchRecords = async () => {
    setLoading(true);
    try {
      const res = await api.getLearningRecords({
        page,
        page_size: 20,
        rule_id: ruleFilter || undefined,
        verdict: verdictFilter || undefined,
        verification_status: statusFilter || undefined,
        search: search || undefined,
      });
      setRecords(res.items);
      setTotal(res.total);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecords();
  }, [page, ruleFilter, verdictFilter, statusFilter]);

  useEffect(() => {
    api.getRules({ page_size: 50 }).then((res) => setRules(res.items)).catch(() => { });
  }, []);

  const handleSeedHistorical = async () => {
    setSeedingLoading(true);
    setFeedback(null);
    try {
      const res = await api.seedHistoricalLearning();
      await fetchRecords();
      setFeedback({
        type: "success",
        text: `Successfully initialized ${res.seeded_count} verified learning records from historical SIEM ground truth!`,
      });
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setSeedingLoading(false);
    }
  };

  const handleRunSimilarSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimSearching(true);
    setSimSearched(true);
    try {
      const matches = await api.findSimilarCases({
        incident_id: simQueryIncidentId.trim() || undefined,
        command_substring: simQueryCommand.trim() || undefined,
        source_ip: simQueryIp.trim() || undefined,
        top_k: 5,
      });
      setSimMatches(matches);
    } catch (err: any) {
      console.error(err);
    } finally {
      setSimSearching(false);
    }
  };

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case "TRUE_POSITIVE":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/60"><ShieldAlert className="w-3 h-3" /> True Positive</span>;
      case "FALSE_POSITIVE":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/60"><ShieldCheck className="w-3 h-3" /> False Positive</span>;
      case "REQUIRES_ATTENTION":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/60 text-amber-400 border border-amber-800/60"><AlertTriangle className="w-3 h-3" /> Requires Attention</span>;
      default:
        return <span className="text-xs text-zinc-400">{verdict}</span>;
    }
  };

  return (
    <div className="space-y-3">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-800 pb-2.5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100">Learning History &amp; Knowledge Base</h1>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-semibold bg-sky-950/80 text-sky-400 border border-sky-800/60 font-mono">
              Phase 2 Active
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Verified-case knowledge repository organized by SIEM rule ID for future dry-run replay and evaluation.
          </p>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={handleSeedHistorical}
            disabled={seedingLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition-colors"
          >
            {seedingLoading ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Database className="w-3 h-3 text-sky-400" />}
            Seed Historical Cases
          </button>
          <button
            onClick={fetchRecords}
            className="p-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 border border-slate-700"
            title="Refresh"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`p-2.5 rounded-md text-xs border ${feedback.type === "success"
            ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
            : "bg-rose-950/60 border-rose-800 text-rose-300"
          }`}>
          {feedback.text}
        </div>
      )}

      {/* KPI Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div className="p-2 sm:p-2.5 rounded-lg border border-slate-800 bg-slate-950 shadow-sm">
          <div className="text-[10px] font-medium text-slate-400">Total Verified Records</div>
          <div className="text-xl font-bold text-slate-100 font-mono mt-0.5">{total}</div>
        </div>
        <div className="p-2 sm:p-2.5 rounded-lg border border-rose-950/40 bg-rose-950/20 shadow-sm">
          <div className="text-[10px] font-medium text-rose-400">Verified True Positives</div>
          <div className="text-xl font-bold text-rose-300 font-mono mt-0.5">
            {records.filter((r) => r.verified_verdict === "TRUE_POSITIVE").length}
          </div>
        </div>
        <div className="p-2 sm:p-2.5 rounded-lg border border-emerald-950/40 bg-emerald-950/20 shadow-sm">
          <div className="text-[10px] font-medium text-emerald-400">Verified False Positives</div>
          <div className="text-xl font-bold text-emerald-300 font-mono mt-0.5">
            {records.filter((r) => r.verified_verdict === "FALSE_POSITIVE").length}
          </div>
        </div>
        <div className="p-2 sm:p-2.5 rounded-lg border border-indigo-950/40 bg-indigo-950/20 shadow-sm">
          <div className="text-[10px] font-medium text-indigo-400">SIEM Rules Covered</div>
          <div className="text-xl font-bold text-indigo-300 font-mono mt-0.5">{rules.length}</div>
        </div>
      </div>

      {/* Section: Deterministic Similar Cases Explorer Tool */}
      <div className="p-2.5 sm:p-3 rounded-lg border border-sky-900/40 bg-sky-950/10 space-y-2.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-sky-900/40 pb-1.5">
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-sky-300 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-sky-400" />
              Deterministic Similar Case Matcher
            </h2>
            <p className="text-[10px] text-slate-400 mt-0.5">
              Query verified cases based on exact command artifacts, source IP, or event type overlap.
            </p>
          </div>
          <span className="text-[9px] font-mono text-sky-400/80 bg-sky-950/60 px-1.5 py-0.2 rounded border border-sky-800/40">
            Rule-Based Similarity
          </span>
        </div>

        <form onSubmit={handleRunSimilarSearch} className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          <div>
            <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">
              Search by Command / Keyword
            </label>
            <input
              type="text"
              placeholder="e.g. powershell, certutil, cmd.exe..."
              value={simQueryCommand}
              onChange={(e) => setSimQueryCommand(e.target.value)}
              className="w-full px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200 placeholder-slate-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-0.5">
              Search by Source IP
            </label>
            <input
              type="text"
              placeholder="e.g. 10.0.4.15..."
              value={simQueryIp}
              onChange={(e) => setSimQueryIp(e.target.value)}
              className="w-full px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200 placeholder-slate-500 focus:outline-none"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={simSearching}
              className="w-full py-1 px-3 bg-sky-800 hover:bg-sky-700 text-white rounded text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
            >
              {simSearching ? (
                <>
                  <RefreshCw className="w-3 h-3 animate-spin" /> Searching...
                </>
              ) : (
                <>
                  <Search className="w-3 h-3" /> Find Matches
                </>
              )}
            </button>
          </div>
        </form>

        {/* Similar Cases Results */}
        {simSearched && (
          <div className="space-y-1.5 pt-1.5 border-t border-sky-900/30">
            <div className="text-xs font-semibold text-slate-300">
              Matching Verified Cases ({simMatches.length} found):
            </div>
            {simMatches.length === 0 ? (
              <div className="p-3 rounded border border-dashed border-slate-800 text-center text-xs text-slate-500">
                No verified cases matched the given telemetry criteria.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {simMatches.map((match) => (
                  <div
                    key={match.learning_record_id}
                    className="p-2.5 rounded-lg border border-slate-800 bg-slate-950/70 space-y-1.5 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-slate-200">
                        {match.incident_vendor_id}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-sky-950 text-sky-400 border border-sky-800 font-mono">
                          {Math.round(match.match_score * 100)}% Match
                        </span>
                        {getVerdictBadge(match.verified_verdict)}
                      </div>
                    </div>

                    <div className="text-slate-300 text-[11px] line-clamp-1 font-medium">{match.title}</div>

                    <div className="text-slate-400 text-[11px] bg-slate-900 p-2 rounded border border-slate-800 whitespace-pre-wrap">
                      {match.analyst_explanation}
                    </div>

                    <div className="pt-0.5">
                      <span className="text-[9px] uppercase font-semibold text-slate-500 block mb-0.5">
                        Matched Telemetry Features:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {match.matched_features.map((feat, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.2 rounded text-[9px] bg-slate-800 text-slate-300 font-mono"
                          >
                            {feat}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Main Verified Knowledge Base Repository Table */}
      <div className="space-y-2">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
          <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-1.5">
            <BookOpen className="w-3.5 h-3.5 text-emerald-400" />
            Verified Case Knowledge Catalog
          </h2>

          {/* Filters */}
          <div className="flex flex-wrap gap-1.5 items-center text-xs">
            <select
              value={ruleFilter}
              onChange={(e) => {
                setRuleFilter(e.target.value);
                setPage(1);
              }}
              className="px-2 py-1 rounded-md border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none"
            >
              <option value="">All SIEM Rules</option>
              {rules.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>

            <select
              value={verdictFilter}
              onChange={(e) => {
                setVerdictFilter(e.target.value);
                setPage(1);
              }}
              className="px-2 py-1 rounded-md border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none"
            >
              <option value="">All Verified Verdicts</option>
              <option value="TRUE_POSITIVE">True Positive</option>
              <option value="FALSE_POSITIVE">False Positive</option>
              <option value="REQUIRES_ATTENTION">Requires Attention</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-2 py-1 rounded-md border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="VERIFIED">Verified Ground Truth</option>
              <option value="DISPUTED">Disputed</option>
              <option value="UNDER_REVIEW">Under Review</option>
            </select>
          </div>
        </div>

        <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-950 shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/60 text-slate-400 uppercase tracking-wider text-[10px] font-mono border-b border-slate-800">
                <tr>
                  <th className="py-2 px-2.5 font-semibold">Incident / Title</th>
                  <th className="py-2 px-2.5 font-semibold">SIEM Rule</th>
                  <th className="py-2 px-2.5 font-semibold">Verified Verdict</th>
                  <th className="py-2 px-2.5 font-semibold">Analyst Explanation &amp; Indicators</th>
                  <th className="py-2 px-2.5 font-semibold">Verification Status</th>
                  <th className="py-2 px-2.5 font-semibold">Recorded Date</th>
                  <th className="py-2 px-2.5 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                      <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1.5 text-slate-600" />
                      Loading verified knowledge base records...
                    </td>
                  </tr>
                ) : records.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                      No learning records found. Click &quot;Seed Historical Cases&quot; to populate verified records.
                    </td>
                  </tr>
                ) : (
                  records.map((rec) => (
                    <tr key={rec.id} className="hover:bg-slate-900/40 transition-colors">
                      <td className="py-1.5 px-2.5">
                        <div className="font-semibold text-slate-100 font-mono text-xs">
                          {rec.incident_vendor_id}
                        </div>
                        <div className="text-slate-400 text-[10px] line-clamp-1 max-w-xs">
                          {rec.incident_title}
                        </div>
                      </td>
                      <td className="py-1.5 px-2.5 text-slate-300 font-medium text-xs">
                        {rec.rule_name}
                      </td>
                      <td className="py-1.5 px-2.5">
                        {getVerdictBadge(rec.verified_verdict)}
                      </td>
                      <td className="py-1.5 px-2.5">
                        <div className="text-slate-300 text-[11px] line-clamp-2 max-w-md">
                          {rec.analyst_explanation}
                        </div>
                        {rec.tp_indicators.length > 0 && (
                          <div className="text-[10px] text-rose-400 mt-0.5 line-clamp-1 font-mono">
                            TP IOC: {rec.tp_indicators[0]}
                          </div>
                        )}
                        {rec.fp_indicators.length > 0 && (
                          <div className="text-[10px] text-emerald-400 mt-0.5 line-clamp-1 font-mono">
                            FP Tool: {rec.fp_indicators[0]}
                          </div>
                        )}
                      </td>
                      <td className="py-1.5 px-2.5">
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                          {rec.verification_status}
                        </span>
                      </td>
                      <td className="py-1.5 px-2.5 text-slate-400 text-[10px]">
                        {new Date(rec.feedback_timestamp).toLocaleDateString()}
                      </td>
                      <td className="py-1.5 px-2.5 text-right">
                        <button
                          onClick={() => setActiveRecord(rec)}
                          className="px-2 py-0.5 bg-slate-900 hover:bg-slate-800 text-slate-200 rounded text-xs font-medium border border-slate-700 transition-colors"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Detail Modal */}
      {activeRecord && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg max-w-xl w-full p-4 space-y-3 shadow-2xl">
            <div className="flex items-start justify-between border-b border-slate-800 pb-2">
              <div>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                  {activeRecord.incident_vendor_id}
                </span>
                <h3 className="text-sm font-bold text-slate-100 mt-1">{activeRecord.incident_title}</h3>
                <p className="text-[11px] text-slate-400">Rule: {activeRecord.rule_name}</p>
              </div>
              <button
                onClick={() => setActiveRecord(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-slate-400 font-semibold text-[11px]">Verified Verdict:</span>
                {getVerdictBadge(activeRecord.verified_verdict)}
                <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                  {activeRecord.verification_status}
                </span>
              </div>

              <div>
                <span className="text-slate-400 font-semibold block mb-0.5 text-[11px]">Analyst Technical Explanation:</span>
                <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-200 whitespace-pre-wrap text-[11px]">
                  {activeRecord.analyst_explanation}
                </div>
              </div>

              {activeRecord.tp_indicators.length > 0 && (
                <div>
                  <span className="text-rose-400 font-semibold block mb-0.5 text-[11px]">Confirmed True Positive Indicators:</span>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                    {activeRecord.tp_indicators.map((tp, i) => (
                      <li key={i}>{tp}</li>
                    ))}
                  </ul>
                </div>
              )}

              {activeRecord.fp_indicators.length > 0 && (
                <div>
                  <span className="text-emerald-400 font-semibold block mb-0.5 text-[11px]">Confirmed Benign / FP Indicators:</span>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                    {activeRecord.fp_indicators.map((fp, i) => (
                      <li key={i}>{fp}</li>
                    ))}
                  </ul>
                </div>
              )}

              {activeRecord.evidence_references.length > 0 && (
                <div>
                  <span className="text-slate-400 font-semibold block mb-0.5 text-[11px]">Evidence Artifact References:</span>
                  <div className="flex flex-wrap gap-1">
                    {activeRecord.evidence_references.map((ref, i) => (
                      <span key={i} className="px-1.5 py-0.2 rounded bg-slate-900 border border-slate-800 text-slate-300 font-mono text-[10px]">
                        {ref}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setActiveRecord(null)}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
