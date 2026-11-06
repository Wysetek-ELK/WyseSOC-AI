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
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Learning History &amp; Knowledge Base</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-sky-950/80 text-sky-400 border border-sky-800/60">
              Phase 2 Active
            </span>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Verified-case knowledge repository organized by SIEM rule ID for future dry-run replay and evaluation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSeedHistorical}
            disabled={seedingLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-zinc-200 border border-zinc-700 transition-colors"
          >
            {seedingLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Database className="w-3.5 h-3.5 text-sky-400" />}
            Seed Historical Cases
          </button>
          <button
            onClick={fetchRecords}
            className="p-1.5 rounded-md bg-zinc-850 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 border border-zinc-800"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {feedback && (
        <div className={`p-3 rounded-md text-xs border ${feedback.type === "success"
            ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
            : "bg-rose-950/60 border-rose-800 text-rose-300"
          }`}>
          {feedback.text}
        </div>
      )}

      {/* KPI Counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-lg border border-zinc-800 bg-zinc-900/60">
          <div className="text-xs font-medium text-zinc-400">Total Verified Records</div>
          <div className="text-2xl font-bold text-zinc-100 mt-1">{total}</div>
        </div>
        <div className="p-3.5 rounded-lg border border-rose-950/40 bg-rose-950/10">
          <div className="text-xs font-medium text-rose-400">Verified True Positives</div>
          <div className="text-2xl font-bold text-rose-300 mt-1">
            {records.filter((r) => r.verified_verdict === "TRUE_POSITIVE").length}
          </div>
        </div>
        <div className="p-3.5 rounded-lg border border-emerald-950/40 bg-emerald-950/10">
          <div className="text-xs font-medium text-emerald-400">Verified False Positives</div>
          <div className="text-2xl font-bold text-emerald-300 mt-1">
            {records.filter((r) => r.verified_verdict === "FALSE_POSITIVE").length}
          </div>
        </div>
        <div className="p-3.5 rounded-lg border border-indigo-950/40 bg-indigo-950/10">
          <div className="text-xs font-medium text-indigo-400">SIEM Rules Covered</div>
          <div className="text-2xl font-bold text-indigo-300 mt-1">{rules.length}</div>
        </div>
      </div>

      {/* Section: Deterministic Similar Cases Explorer Tool */}
      <div className="p-4 rounded-lg border border-sky-900/40 bg-sky-950/10 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-sky-900/40 pb-2">
          <div>
            <h2 className="text-sm font-bold text-sky-300 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-sky-400" />
              Deterministic Similar Case Matcher
            </h2>
            <p className="text-xs text-zinc-400 mt-0.5">
              Query verified cases based on exact command artifacts, source IP, or event type overlap.
            </p>
          </div>
          <span className="text-[10px] font-mono text-sky-400/80 bg-sky-950/60 px-2 py-0.5 rounded border border-sky-800/40">
            Rule-Based Deterministic Similarity
          </span>
        </div>

        <form onSubmit={handleRunSimilarSearch} className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block mb-1">
              Search by Command / Keyword
            </label>
            <input
              type="text"
              placeholder="e.g. powershell, certutil, cmd.exe..."
              value={simQueryCommand}
              onChange={(e) => setSimQueryCommand(e.target.value)}
              className="w-full px-3 py-1.5 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-200 placeholder-zinc-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block mb-1">
              Search by Source IP
            </label>
            <input
              type="text"
              placeholder="e.g. 10.0.4.15..."
              value={simQueryIp}
              onChange={(e) => setSimQueryIp(e.target.value)}
              className="w-full px-3 py-1.5 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-200 placeholder-zinc-500 focus:outline-none"
            />
          </div>

          <div className="flex items-end">
            <button
              type="submit"
              disabled={simSearching}
              className="w-full py-1.5 px-4 bg-sky-800 hover:bg-sky-700 text-white rounded text-xs font-bold transition-colors flex items-center justify-center gap-1.5"
            >
              {simSearching ? (
                <>
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Searching Matches...
                </>
              ) : (
                <>
                  <Search className="w-3.5 h-3.5" /> Find Similar Verified Cases
                </>
              )}
            </button>
          </div>
        </form>

        {/* Similar Cases Results */}
        {simSearched && (
          <div className="space-y-2 pt-2 border-t border-sky-900/30">
            <div className="text-xs font-semibold text-zinc-300">
              Matching Verified Cases ({simMatches.length} found):
            </div>
            {simMatches.length === 0 ? (
              <div className="p-4 rounded border border-dashed border-zinc-800 text-center text-xs text-zinc-500">
                No verified cases matched the given telemetry criteria.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {simMatches.map((match) => (
                  <div
                    key={match.learning_record_id}
                    className="p-3.5 rounded-lg border border-zinc-800 bg-zinc-950/70 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono font-bold text-zinc-200">
                        {match.incident_vendor_id}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-sky-950 text-sky-400 border border-sky-800 font-mono">
                          {Math.round(match.match_score * 100)}% Match
                        </span>
                        {getVerdictBadge(match.verified_verdict)}
                      </div>
                    </div>

                    <div className="text-zinc-300 text-[11px] line-clamp-1 font-medium">{match.title}</div>

                    <div className="text-zinc-400 text-[11px] bg-zinc-900 p-2 rounded border border-zinc-850 whitespace-pre-wrap">
                      {match.analyst_explanation}
                    </div>

                    <div className="pt-1">
                      <span className="text-[10px] uppercase font-semibold text-zinc-500 block mb-1">
                        Matched Telemetry Features:
                      </span>
                      <div className="flex flex-wrap gap-1">
                        {match.matched_features.map((feat, idx) => (
                          <span
                            key={idx}
                            className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-800 text-zinc-300 font-mono"
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
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <h2 className="text-base font-bold text-zinc-100 flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-emerald-400" />
            Verified Case Knowledge Catalog
          </h2>

          {/* Filters */}
          <div className="flex flex-wrap gap-2 items-center text-xs">
            <select
              value={ruleFilter}
              onChange={(e) => {
                setRuleFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 rounded-md border border-zinc-800 bg-zinc-950 text-zinc-300 focus:outline-none"
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
              className="px-2.5 py-1.5 rounded-md border border-zinc-800 bg-zinc-950 text-zinc-300 focus:outline-none"
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
              className="px-2.5 py-1.5 rounded-md border border-zinc-800 bg-zinc-950 text-zinc-300 focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="VERIFIED">Verified Ground Truth</option>
              <option value="DISPUTED">Disputed</option>
              <option value="UNDER_REVIEW">Under Review</option>
            </select>
          </div>
        </div>

        <div className="border border-zinc-800 rounded-lg overflow-hidden bg-zinc-900/30">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-zinc-300">
              <thead className="bg-zinc-900/80 text-zinc-400 uppercase tracking-wider text-[11px] border-b border-zinc-800">
                <tr>
                  <th className="py-3 px-4 font-semibold">Incident / Title</th>
                  <th className="py-3 px-3 font-semibold">SIEM Rule</th>
                  <th className="py-3 px-3 font-semibold">Verified Verdict</th>
                  <th className="py-3 px-4 font-semibold">Analyst Explanation &amp; Indicators</th>
                  <th className="py-3 px-3 font-semibold">Verification Status</th>
                  <th className="py-3 px-3 font-semibold">Recorded Date</th>
                  <th className="py-3 px-4 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-850">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-zinc-500">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-zinc-600" />
                      Loading verified knowledge base records...
                    </td>
                  </tr>
                ) : records.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-zinc-500">
                      No learning records found. Click &quot;Seed Historical Cases&quot; to populate verified records.
                    </td>
                  </tr>
                ) : (
                  records.map((rec) => (
                    <tr key={rec.id} className="hover:bg-zinc-800/40 transition-colors">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-zinc-100 font-mono">
                          {rec.incident_vendor_id}
                        </div>
                        <div className="text-zinc-400 text-[11px] line-clamp-1 max-w-xs mt-0.5">
                          {rec.incident_title}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-zinc-300 font-medium">
                        {rec.rule_name}
                      </td>
                      <td className="py-3 px-3">
                        {getVerdictBadge(rec.verified_verdict)}
                      </td>
                      <td className="py-3 px-4">
                        <div className="text-zinc-300 text-[11px] line-clamp-2 max-w-md">
                          {rec.analyst_explanation}
                        </div>
                        {rec.tp_indicators.length > 0 && (
                          <div className="text-[10px] text-rose-400 mt-1 line-clamp-1">
                            TP IOC: {rec.tp_indicators[0]}
                          </div>
                        )}
                        {rec.fp_indicators.length > 0 && (
                          <div className="text-[10px] text-emerald-400 mt-1 line-clamp-1">
                            FP Tool: {rec.fp_indicators[0]}
                          </div>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                          {rec.verification_status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-zinc-400 text-[11px]">
                        {new Date(rec.feedback_timestamp).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => setActiveRecord(rec)}
                          className="px-2.5 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-xs font-medium border border-zinc-700"
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
          <div className="bg-zinc-950 border border-zinc-800 rounded-lg max-w-2xl w-full p-6 space-y-4 shadow-2xl">
            <div className="flex items-start justify-between border-b border-zinc-800 pb-3">
              <div>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                  {activeRecord.incident_vendor_id}
                </span>
                <h3 className="text-base font-bold text-zinc-100 mt-1">{activeRecord.incident_title}</h3>
                <p className="text-xs text-zinc-400">Rule: {activeRecord.rule_name}</p>
              </div>
              <button
                onClick={() => setActiveRecord(null)}
                className="p-1 rounded text-zinc-400 hover:text-zinc-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex items-center gap-3">
                <span className="text-zinc-400 font-semibold">Verified Verdict:</span>
                {getVerdictBadge(activeRecord.verified_verdict)}
                <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                  {activeRecord.verification_status}
                </span>
              </div>

              <div>
                <span className="text-zinc-400 font-semibold block mb-1">Analyst Technical Explanation:</span>
                <div className="p-3 rounded bg-zinc-900 border border-zinc-850 text-zinc-200 whitespace-pre-wrap">
                  {activeRecord.analyst_explanation}
                </div>
              </div>

              {activeRecord.tp_indicators.length > 0 && (
                <div>
                  <span className="text-rose-400 font-semibold block mb-1">Confirmed True Positive Indicators:</span>
                  <ul className="list-disc list-inside space-y-1 text-zinc-300">
                    {activeRecord.tp_indicators.map((tp, i) => (
                      <li key={i}>{tp}</li>
                    ))}
                  </ul>
                </div>
              )}

              {activeRecord.fp_indicators.length > 0 && (
                <div>
                  <span className="text-emerald-400 font-semibold block mb-1">Confirmed Benign / FP Indicators:</span>
                  <ul className="list-disc list-inside space-y-1 text-zinc-300">
                    {activeRecord.fp_indicators.map((fp, i) => (
                      <li key={i}>{fp}</li>
                    ))}
                  </ul>
                </div>
              )}

              {activeRecord.evidence_references.length > 0 && (
                <div>
                  <span className="text-zinc-400 font-semibold block mb-1">Evidence Artifact References:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {activeRecord.evidence_references.map((ref, i) => (
                      <span key={i} className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-300 font-mono">
                        {ref}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-3 border-t border-zinc-800">
              <button
                type="button"
                onClick={() => setActiveRecord(null)}
                className="px-4 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-xs font-semibold"
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
