"use client";

import React, { useState, useEffect, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  BarChart2,
  CheckCircle,
  AlertTriangle,
  XCircle,
  TrendingUp,
  ShieldCheck,
  ShieldAlert,
  Download,
  Filter,
  RefreshCw,
  FileSpreadsheet,
  FileJson,
  Check,
  ArrowRight,
  Info,
  Layers,
  Lock,
  Search,
  ChevronDown,
  ChevronRight,
  Sliders,
  ExternalLink,
  Play,
  RotateCcw,
  Activity,
  FileText,
  HelpCircle,
  Zap,
} from "lucide-react";
import Link from "next/link";
import {
  api,
  User,
  VerdictTrustOverviewResponse,
  RuleWiseTrustworthinessItem,
  VerdictTrustAssessmentResult,
  RegressionComparisonReport,
} from "@/lib/api";

function VerdictIntelligenceContent() {
  const searchParams = useSearchParams();
  const ruleParam = searchParams.get("rule_id") || "";
  const initialTab = searchParams.get("tab") || (ruleParam ? "rules" : "overview");

  // Tab State: "overview" | "accuracy" | "rules" | "explain" | "simulation"
  const [activeTab, setActiveTab] = useState<string>(initialTab);

  // Data States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Dashboard A: Overview Data
  const [overview, setOverview] = useState<VerdictTrustOverviewResponse | null>(null);

  // Dashboard C: Rule-wise Data
  const [ruleItems, setRuleItems] = useState<RuleWiseTrustworthinessItem[]>([]);
  const [ruleSearch, setRuleSearch] = useState<string>(ruleParam);
  const [selectedArchetypeFilter, setSelectedArchetypeFilter] = useState<string>("ALL");

  // Dashboard D: Individual Incident Explanation State
  const [lookupIncidentId, setLookupIncidentId] = useState<string>("");
  const [allowSimulation, setAllowSimulation] = useState<boolean>(false);
  const [selectedAssessment, setSelectedAssessment] = useState<VerdictTrustAssessmentResult | null>(null);
  const [evaluatingIncident, setEvaluatingIncident] = useState<boolean>(false);

  // Dashboard E: Simulation & Regression Comparison State
  const [evaluationRuns, setEvaluationRuns] = useState<any[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [runDetails, setRunDetails] = useState<any | null>(null);
  const [baselineRunId, setBaselineRunId] = useState<string>("");
  const [comparisonReport, setComparisonReport] = useState<RegressionComparisonReport | null>(null);
  const [comparing, setComparing] = useState<boolean>(false);
  const [launchingRun, setLaunchingRun] = useState<boolean>(false);
  const [newRunName, setNewRunName] = useState<string>("Dry-Run Intelligence Backtest");
  const [newRunSampleLimit, setNewRunSampleLimit] = useState<number>(50);

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function loadDashboardData() {
    setLoading(true);
    setError(null);
    try {
      const [ov, rules, runs] = await Promise.all([
        api.getVerdictTrustOverview().catch(() => null),
        api.getRuleWiseTrustworthiness().catch(() => []),
        api.listEvaluationRuns(15).catch(() => []),
      ]);

      setOverview(ov);
      setRuleItems(rules);
      setEvaluationRuns(runs);

      if (runs && runs.length > 0) {
        setSelectedRunId(runs[0].id);
        const details = await api.getEvaluationRunDetails(runs[0].id).catch(() => null);
        setRunDetails(details);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load verdict intelligence data");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectRun(runId: string) {
    setSelectedRunId(runId);
    try {
      const details = await api.getEvaluationRunDetails(runId);
      setRunDetails(details);
    } catch (err: any) {
      setError("Failed to load details for run " + runId);
    }
  }

  async function handleEvaluateIncident(e?: React.FormEvent) {
    if (e) e.preventDefault();
    if (!lookupIncidentId.trim()) return;
    setEvaluatingIncident(true);
    setError(null);
    try {
      const res = await api.evaluateIncidentTrust({
        incident_id: lookupIncidentId.trim(),
        allow_simulation: allowSimulation,
      });
      setSelectedAssessment(res);
      setActiveTab("explain");
      setSuccessMsg(`Incident ${lookupIncidentId} evaluated successfully.`);
    } catch (err: any) {
      setError(err.message || "Failed to evaluate incident trust");
    } finally {
      setEvaluatingIncident(false);
    }
  }

  async function handleLaunchEvaluation() {
    setLaunchingRun(true);
    setError(null);
    try {
      const res = await api.startHistoricalEvaluation({
        run_name: newRunName,
        sample_limit: newRunSampleLimit,
        provider_type: "SIMULATED",
      });
      setSuccessMsg(`Historical Evaluation Run started: ${res.run_name}`);
      await loadDashboardData();
      if (res.run_id) {
        handleSelectRun(res.run_id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to start evaluation run");
    } finally {
      setLaunchingRun(false);
    }
  }

  async function handleCompareRuns() {
    if (!selectedRunId || !baselineRunId) {
      setError("Please select both a baseline and a candidate evaluation run.");
      return;
    }
    setComparing(true);
    setError(null);
    try {
      const rep = await api.compareEvaluationRuns(baselineRunId, selectedRunId);
      setComparisonReport(rep);
    } catch (err: any) {
      setError(err.message || "Failed to execute paired regression comparison");
    } finally {
      setComparing(false);
    }
  }

  async function handleExport(format: "json" | "csv") {
    try {
      const { blob, filename } = await api.exportEvaluationReport(selectedRunId || undefined, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError("Export failed: " + err.message);
    }
  }

  // Filtered Rules
  const filteredRules = ruleItems.filter((r) => {
    const matchesSearch =
      r.rule_name.toLowerCase().includes(ruleSearch.toLowerCase()) ||
      r.rule_id.toLowerCase().includes(ruleSearch.toLowerCase());
    const matchesArchetype =
      selectedArchetypeFilter === "ALL" || r.archetype === selectedArchetypeFilter;
    return matchesSearch && matchesArchetype;
  });

  const distinctArchetypes = Array.from(new Set(ruleItems.map((r) => r.archetype))).filter(Boolean);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
              <ShieldCheck className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Verdict Intelligence & Dry-Run Validation
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-mono font-medium">
                  AIS 2.1
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Deterministic Trust Scoring (1–10), Evidence Sufficiency, Empirical Accuracy & Historical Replay
              </p>
            </div>
          </div>
        </div>

        {/* Global Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => handleExport("csv")}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 text-sm font-medium rounded-lg border border-slate-700 transition"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            Export CSV
          </button>
          <button
            onClick={() => handleExport("json")}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-900 hover:bg-slate-800 text-slate-200 text-sm font-medium rounded-lg border border-slate-700 transition"
          >
            <FileJson className="w-4 h-4 text-blue-400" />
            Export JSON
          </button>
          <button
            onClick={loadDashboardData}
            disabled={loading}
            className="p-2 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white rounded-lg border border-slate-700 transition"
            title="Refresh Intelligence Data"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-red-200 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-sm flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-200 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Incident Quick Search / Evaluate Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleEvaluateIncident} className="flex items-center gap-2 w-full md:w-auto flex-1">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
            <input
              type="text"
              value={lookupIncidentId}
              onChange={(e) => setLookupIncidentId(e.target.value)}
              placeholder="Enter Incident ID to evaluate trust (e.g. INC-001, PH_INC_2026_01)..."
              className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
          <button
            type="submit"
            disabled={evaluatingIncident || !lookupIncidentId.trim()}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white text-sm font-medium rounded-lg transition"
          >
            <ShieldCheck className="w-4 h-4" />
            {evaluatingIncident ? "Evaluating..." : "Evaluate Trust"}
          </button>
          <label className="flex items-center gap-1.5 text-xs text-slate-400 cursor-pointer select-none whitespace-nowrap pl-2" title="When disabled, requires a stored AI verdict or custom model output">
            <input
              type="checkbox"
              checked={allowSimulation}
              onChange={(e) => setAllowSimulation(e.target.checked)}
              className="rounded border-slate-600 bg-slate-900 text-indigo-500"
            />
            Allow simulation fallback
          </label>
        </form>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400" /> Auto Decision (Trust 7–10)
          </span>
          <span className="flex items-center gap-1 ml-2">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Analyst Attention (Trust &lt; 7)
          </span>
        </div>
      </div>

      {/* Sub-Navigation Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 overflow-x-auto pb-1 text-sm font-medium">
        {[
          { id: "overview", label: "Dashboard A: Verdict Trust Overview", icon: BarChart2 },
          { id: "accuracy", label: "Dashboard B: Empirical Accuracy", icon: TrendingUp },
          { id: "rules", label: "Dashboard C: Rule-Wise Trustworthiness", icon: Layers },
          { id: "explain", label: "Dashboard D: Incident Verdict Drill-Down", icon: FileText },
          { id: "simulation", label: "Dashboard E: Replay & Regression Comparison", icon: Sliders },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg transition whitespace-nowrap ${
                isActive
                  ? "bg-indigo-600/10 text-indigo-400 border border-indigo-500/30"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-900"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* ========================================================================= */}
      {/* DASHBOARD A: VERDICT TRUST OVERVIEW                                       */}
      {/* ========================================================================= */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Total Evaluated Cases</span>
              <div className="text-3xl font-bold text-white mt-2">
                {overview?.total_evaluated_incidents || 0}
              </div>
              <p className="text-xs text-slate-500 mt-1">Evaluated through evidence sufficiency & trust engines</p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Decisive Automated Verdicts</span>
              <div className="text-3xl font-bold text-emerald-400 mt-2">
                {(overview?.true_positive_recommendations || 0) + (overview?.false_positive_recommendations || 0)}
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-400 mt-1">
                <span className="text-emerald-400 font-medium">TP: {overview?.true_positive_recommendations || 0}</span>
                <span>•</span>
                <span className="text-blue-400 font-medium">FP: {overview?.false_positive_recommendations || 0}</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Analyst Attention Rate</span>
              <div className="text-3xl font-bold text-amber-400 mt-2">
                {overview?.total_evaluated_incidents
                  ? `${Math.round(((overview.analyst_attention_decisions || 0) / overview.total_evaluated_incidents) * 100)}%`
                  : "0%"}
              </div>
              <p className="text-xs text-amber-400/80 mt-1">
                {overview?.analyst_attention_decisions || 0} cases safely routed to human review
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
              <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Average Trust Score</span>
              <div className="text-3xl font-bold text-indigo-400 mt-2 flex items-baseline gap-1">
                {overview?.average_trust_score || "N/A"}
                <span className="text-sm font-normal text-slate-500">/ 10</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Avg Sufficiency: {overview?.average_sufficiency_score || 0}%
              </p>
            </div>
          </div>

          {/* Trust Score Distribution Chart */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-white">Trust Score Distribution (1–10 Ordinal Scale)</h3>
                  <p className="text-xs text-slate-400">Histogram of evaluated incident trust scores across 10 discrete bands</p>
                </div>
                <span className="text-xs px-2.5 py-1 bg-slate-800 text-slate-300 rounded-md border border-slate-700">
                  Scores &ge; 7: Eligible for Automated Verdict
                </span>
              </div>

              {/* Bar Histogram */}
              <div className="grid grid-cols-10 gap-2 items-end h-44 pt-6 pb-2 border-b border-slate-800">
                {Array.from({ length: 10 }, (_, i) => i + 1).map((score) => {
                  const count = overview?.trust_score_distribution?.[String(score)] || 0;
                  const maxCount = Math.max(1, ...Object.values(overview?.trust_score_distribution || {}));
                  const heightPercent = Math.max(6, Math.round((count / maxCount) * 100));
                  const isEligible = score >= 7;

                  return (
                    <div key={score} className="flex flex-col items-center gap-1 h-full justify-end group">
                      <span className="text-[10px] font-mono text-slate-400 opacity-0 group-hover:opacity-100 transition">
                        {count}
                      </span>
                      <div
                        style={{ height: `${heightPercent}%` }}
                        className={`w-full rounded-t transition-all duration-300 ${
                          isEligible
                            ? "bg-indigo-500 group-hover:bg-indigo-400"
                            : "bg-amber-500/70 group-hover:bg-amber-400"
                        }`}
                      />
                      <span className="text-xs font-mono text-slate-300 font-semibold">{score}</span>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                <span>Score 1: Very Weak Evidence Support</span>
                <span>Score 7+: Safe Automatic Verdict</span>
                <span>Score 10: Exceptional Support</span>
              </div>
            </div>

            {/* Safety & Disqualification Indicators */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
              <h3 className="text-base font-semibold text-white">Safety Gating Breakdown</h3>
              <p className="text-xs text-slate-400">Incidents disqualified from automated decisioning</p>

              <div className="space-y-3 pt-2">
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <div>
                      <div className="text-sm font-medium text-slate-200">Missing Mandatory Telemetry</div>
                      <div className="text-xs text-slate-500">Core contract fields absent</div>
                    </div>
                  </div>
                  <span className="text-sm font-mono font-bold text-amber-400">
                    {overview?.missing_evidence_count || 0}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <XCircle className="w-4 h-4 text-red-400" />
                    <div>
                      <div className="text-sm font-medium text-slate-200">Conflicting Telemetry Records</div>
                      <div className="text-xs text-slate-500">Volume or directional conflict</div>
                    </div>
                  </div>
                  <span className="text-sm font-mono font-bold text-red-400">
                    {overview?.conflicting_evidence_count || 0}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <ShieldAlert className="w-4 h-4 text-purple-400" />
                    <div>
                      <div className="text-sm font-medium text-slate-200">Low Trust Assessment (&lt; 7/10)</div>
                      <div className="text-xs text-slate-500">Evidence insufficient for threshold</div>
                    </div>
                  </div>
                  <span className="text-sm font-mono font-bold text-purple-400">
                    {overview?.low_trust_verdicts_count || 0}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* DASHBOARD B: EMPIRICAL ACCURACY & CALIBRATION                              */}
      {/* ========================================================================= */}
      {activeTab === "accuracy" && (
        <div className="space-y-6">
          {runDetails?.run?.metrics ? (
            <>
              {/* Confusion Matrix & Key Proportions */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 2x2 Confusion Matrix */}
                <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
                  <h3 className="text-base font-semibold text-white">Adjudicated Confusion Matrix</h3>
                  <p className="text-xs text-slate-400">Decisive automated verdicts vs verified historical analyst labels</p>

                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-center">
                      <span className="text-xs text-emerald-400 font-semibold uppercase tracking-wider">True Positive (TP)</span>
                      <div className="text-3xl font-mono font-bold text-white mt-1">
                        {runDetails.run.metrics.true_positives || 0}
                      </div>
                      <p className="text-[11px] text-emerald-400/80 mt-1">Correctly identified attacks</p>
                    </div>

                    <div className="p-4 rounded-xl bg-red-950/30 border border-red-800/40 text-center">
                      <span className="text-xs text-red-400 font-semibold uppercase tracking-wider">False Positive (FP)</span>
                      <div className="text-3xl font-mono font-bold text-white mt-1">
                        {runDetails.run.metrics.false_positives || 0}
                      </div>
                      <p className="text-[11px] text-red-400/80 mt-1">Benign misclassified as attack</p>
                    </div>

                    <div className="p-4 rounded-xl bg-red-950/30 border border-red-800/40 text-center">
                      <span className="text-xs text-red-400 font-semibold uppercase tracking-wider">False Negative (FN)</span>
                      <div className="text-3xl font-mono font-bold text-white mt-1">
                        {runDetails.run.metrics.false_negatives || 0}
                      </div>
                      <p className="text-[11px] text-red-400/80 mt-1">Missed malicious attack</p>
                    </div>

                    <div className="p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-center">
                      <span className="text-xs text-emerald-400 font-semibold uppercase tracking-wider">True Negative (TN)</span>
                      <div className="text-3xl font-mono font-bold text-white mt-1">
                        {runDetails.run.metrics.true_negatives || 0}
                      </div>
                      <p className="text-[11px] text-emerald-400/80 mt-1">Correctly identified benign</p>
                    </div>
                  </div>
                </div>

                {/* Accuracy & Wilson Confidence Intervals */}
                <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-base font-semibold text-white">Empirical Accuracy & Wilson Confidence Intervals</h3>
                      <p className="text-xs text-slate-400">Statistical bounds (95% two-sided Wilson score intervals)</p>
                    </div>
                    <span className="text-xs px-2.5 py-1 bg-slate-800 text-slate-300 rounded-md border border-slate-700 font-mono">
                      N = {runDetails.run.metrics.verified_ground_truth_cases || 0} Verified Cases
                    </span>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2">
                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-xs text-slate-400 font-medium">TP Precision</span>
                      <div className="text-xl font-bold text-white mt-1">
                        {runDetails.run.metrics.precision !== null ? `${Math.round(runDetails.run.metrics.precision * 100)}%` : "N/A"}
                      </div>
                      {runDetails.run.metrics.precision_ci?.lower_bound !== null && (
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          95% CI: [{Math.round(runDetails.run.metrics.precision_ci.lower_bound * 100)}%–
                          {Math.round(runDetails.run.metrics.precision_ci.upper_bound * 100)}%]
                        </div>
                      )}
                    </div>

                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-xs text-slate-400 font-medium">TP Recall (Sensitivity)</span>
                      <div className="text-xl font-bold text-white mt-1">
                        {runDetails.run.metrics.recall !== null ? `${Math.round(runDetails.run.metrics.recall * 100)}%` : "N/A"}
                      </div>
                      {runDetails.run.metrics.recall_ci?.lower_bound !== null && (
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          95% CI: [{Math.round(runDetails.run.metrics.recall_ci.lower_bound * 100)}%–
                          {Math.round(runDetails.run.metrics.recall_ci.upper_bound * 100)}%]
                        </div>
                      )}
                    </div>

                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-xs text-slate-400 font-medium">FP Specificity</span>
                      <div className="text-xl font-bold text-white mt-1">
                        {runDetails.run.metrics.specificity !== null ? `${Math.round(runDetails.run.metrics.specificity * 100)}%` : "N/A"}
                      </div>
                      {runDetails.run.metrics.specificity_ci?.lower_bound !== null && (
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          95% CI: [{Math.round(runDetails.run.metrics.specificity_ci.lower_bound * 100)}%–
                          {Math.round(runDetails.run.metrics.specificity_ci.upper_bound * 100)}%]
                        </div>
                      )}
                    </div>

                    <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-xs text-slate-400 font-medium">Balanced Accuracy</span>
                      <div className="text-xl font-bold text-white mt-1">
                        {runDetails.run.metrics.balanced_accuracy !== null
                          ? `${Math.round(runDetails.run.metrics.balanced_accuracy * 100)}%`
                          : "N/A"}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">(Recall + Specificity)/2</div>
                    </div>
                  </div>

                  {/* Selective Classification Details */}
                  <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 grid grid-cols-3 gap-4 mt-2">
                    <div>
                      <span className="text-xs text-slate-400">Automatic Decision Coverage</span>
                      <div className="text-lg font-bold text-emerald-400 mt-0.5">
                        {runDetails.run.metrics.automatic_decision_coverage !== null
                          ? `${Math.round(runDetails.run.metrics.automatic_decision_coverage * 100)}%`
                          : "0%"}
                      </div>
                      <p className="text-[11px] text-slate-500">Decided without human intervention</p>
                    </div>

                    <div>
                      <span className="text-xs text-slate-400">Analyst Escalation Rate</span>
                      <div className="text-lg font-bold text-amber-400 mt-0.5">
                        {runDetails.run.metrics.analyst_attention_rate !== null
                          ? `${Math.round(runDetails.run.metrics.analyst_attention_rate * 100)}%`
                          : "0%"}
                      </div>
                      <p className="text-[11px] text-slate-500">Safely abstained on uncertain telemetry</p>
                    </div>

                    <div>
                      <span className="text-xs text-slate-400">Critical False Negatives</span>
                      <div className="text-lg font-bold text-red-400 mt-0.5">
                        {runDetails.run.metrics.critical_false_negatives || 0}
                      </div>
                      <p className="text-[11px] text-slate-500">Missed malicious incidents</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Calibration & Reliability Diagram Bins */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-semibold text-white">Score Calibration & Reliability Bins</h3>
                    <p className="text-xs text-slate-400">Empirical relationship between Trust Score bands and observed correctness</p>
                  </div>
                  <span className={`text-xs px-2.5 py-1 rounded-md border font-mono ${
                    runDetails.run.calibration_metrics?.is_calibrated
                      ? "bg-emerald-950/60 text-emerald-400 border-emerald-800"
                      : "bg-slate-800 text-slate-400 border-slate-700"
                  }`}>
                    Status: {runDetails.run.calibration_metrics?.status || "NOT_CALIBRATED"}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-800 text-xs uppercase text-slate-400">
                        <th className="py-2.5 px-3">Score Band</th>
                        <th className="py-2.5 px-3">Mean Trust</th>
                        <th className="py-2.5 px-3">Cases (N)</th>
                        <th className="py-2.5 px-3">Observed Accuracy</th>
                        <th className="py-2.5 px-3">Observed Error Rate</th>
                        <th className="py-2.5 px-3">Calibration Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
                      {(runDetails.run.calibration_metrics?.reliability_bins || []).map((bin: any) => (
                        <tr key={bin.bin_index} className="hover:bg-slate-900/40">
                          <td className="py-2.5 px-3 text-slate-200 font-sans font-medium">{bin.score_range}</td>
                          <td className="py-2.5 px-3 text-slate-300">{bin.mean_predicted_trust} / 10</td>
                          <td className="py-2.5 px-3 text-slate-300">{bin.sample_count}</td>
                          <td className="py-2.5 px-3 text-emerald-400">
                            {bin.observed_accuracy !== null ? `${Math.round(bin.observed_accuracy * 100)}%` : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-red-400">
                            {bin.error_rate !== null ? `${Math.round(bin.error_rate * 100)}%` : "N/A"}
                          </td>
                          <td className="py-2.5 px-3 text-slate-400 font-sans">
                            {bin.sample_count >= 5 ? "Sufficient Data" : "Sparse (< 5)"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <div className="p-8 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400">
              <Info className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <p>No historical evaluation run selected. Launch a run in Dashboard E to inspect empirical accuracy.</p>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* DASHBOARD C: RULE-WISE TRUSTWORTHINESS                                     */}
      {/* ========================================================================= */}
      {activeTab === "rules" && (
        <div className="space-y-4">
          {/* Search & Filters */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800">
            <div className="relative w-full md:w-80">
              <Search className="w-4 h-4 absolute left-3 top-3 text-slate-500" />
              <input
                type="text"
                value={ruleSearch}
                onChange={(e) => setRuleSearch(e.target.value)}
                placeholder="Filter rules by name or ID..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-400">Archetype:</span>
              <select
                value={selectedArchetypeFilter}
                onChange={(e) => setSelectedArchetypeFilter(e.target.value)}
                className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-2 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Archetypes ({distinctArchetypes.length})</option>
                {distinctArchetypes.map((arch) => (
                  <option key={arch} value={arch}>
                    {arch}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Rules Table */}
          <div className="rounded-xl bg-slate-900/60 border border-slate-800 overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-800 text-xs uppercase text-slate-400 bg-slate-900/80">
                  <th className="py-3 px-4">Rule ID & Name</th>
                  <th className="py-3 px-4">Archetype</th>
                  <th className="py-3 px-4">Evaluated Incidents</th>
                  <th className="py-3 px-4">Avg Trust Score</th>
                  <th className="py-3 px-4">Evidence Sufficiency</th>
                  <th className="py-3 px-4">Measured Accuracy</th>
                  <th className="py-3 px-4">Abstention Rate</th>
                  <th className="py-3 px-4">Validation Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredRules.length > 0 ? (
                  filteredRules.map((r) => (
                    <tr key={r.rule_id} className="hover:bg-slate-800/30 transition">
                      <td className="py-3 px-4">
                        <div className="font-semibold text-white">{r.rule_name}</div>
                        <div className="text-xs font-mono text-slate-400">{r.rule_id}</div>
                      </td>

                      <td className="py-3 px-4">
                        <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono">
                          {r.archetype}
                        </span>
                      </td>

                      <td className="py-3 px-4 font-mono text-xs text-slate-300">
                        {r.incident_count} cases
                      </td>

                      <td className="py-3 px-4">
                        {r.average_trust_score !== null && r.average_trust_score !== undefined ? (
                          <div className="flex items-center gap-1.5">
                            <span
                              className={`text-xs font-mono font-bold px-2 py-0.5 rounded ${
                                r.average_trust_score >= 7.0
                                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                                  : "bg-amber-950 text-amber-400 border border-amber-800/60"
                              }`}
                            >
                              {r.average_trust_score}/10
                            </span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500">Unscored</span>
                        )}
                      </td>

                      <td className="py-3 px-4">
                        {r.evidence_sufficiency !== null && r.evidence_sufficiency !== undefined ? (
                          <span className="text-xs font-mono text-slate-300 font-medium">
                            {r.evidence_sufficiency}%
                          </span>
                        ) : (
                          <span className="text-xs text-slate-500">N/A</span>
                        )}
                      </td>

                      <td className="py-3 px-4 font-mono text-xs">
                        {r.measured_accuracy !== null && r.measured_accuracy !== undefined ? (
                          <span className="text-emerald-400 font-bold">{r.measured_accuracy}%</span>
                        ) : (
                          <span className="text-slate-500">Insufficient Data</span>
                        )}
                      </td>

                      <td className="py-3 px-4 font-mono text-xs text-amber-400">
                        {r.abstention_rate !== null && r.abstention_rate !== undefined ? `${r.abstention_rate}%` : "N/A"}
                      </td>

                      <td className="py-3 px-4">
                        <span
                          className={`text-xs px-2 py-0.5 rounded font-medium ${
                            r.validation_status === "VALIDATED"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : r.validation_status === "REGRESSION_DETECTED"
                              ? "bg-red-950 text-red-400 border border-red-800"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {r.validation_status}
                        </span>
                      </td>

                      <td className="py-3 px-4 text-right">
                        <Link
                          href={`/agent-intelligence-studio?ruleId=${r.rule_id}`}
                          className="text-xs px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-md transition"
                        >
                          Open Studio
                        </Link>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-slate-500">
                      No detection rules matching search criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* DASHBOARD D: INDIVIDUAL VERDICT EXPLANATION                                */}
      {/* ========================================================================= */}
      {activeTab === "explain" && (
        <div className="space-y-6">
          {selectedAssessment ? (
            <div className="space-y-6">
              {/* Top Summary Card */}
              <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                      Incident: {selectedAssessment.incident_id}
                    </span>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono">
                      {selectedAssessment.archetype}
                    </span>
                    {selectedAssessment.is_simulated && (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-950/60 text-amber-300 border border-amber-700/60 font-mono">
                        SIMULATED
                      </span>
                    )}
                  </div>
                  <h2 className="text-xl font-bold text-white mt-1">
                    Rule: {selectedAssessment.rule_id}
                  </h2>
                </div>

                <div className="flex items-center gap-4">
                  {/* Trust Score Gauge */}
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block font-medium">Verdict Trust Score</span>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span
                        className={`text-2xl font-mono font-bold px-3 py-0.5 rounded-lg border ${
                          (selectedAssessment.trust_score || 0) >= 7
                            ? "bg-emerald-950 text-emerald-400 border-emerald-800"
                            : "bg-amber-950 text-amber-400 border-amber-800"
                        }`}
                      >
                        {selectedAssessment.trust_score !== null ? `${selectedAssessment.trust_score}/10` : "NOT_SCORABLE"}
                      </span>
                    </div>
                  </div>

                  {/* Effective Verdict Badge */}
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block font-medium">Guardrail Verdict</span>
                    <span
                      className={`text-sm font-bold px-3 py-1 rounded-md inline-block mt-0.5 border ${
                        selectedAssessment.effective_verdict === "TRUE_POSITIVE"
                          ? "bg-emerald-950/80 text-emerald-300 border-emerald-800"
                          : selectedAssessment.effective_verdict === "FALSE_POSITIVE"
                          ? "bg-blue-950/80 text-blue-300 border-blue-800"
                          : "bg-amber-950/80 text-amber-300 border-amber-800"
                      }`}
                    >
                      {selectedAssessment.effective_verdict}
                    </span>
                  </div>
                </div>
              </div>

              {/* Explanation & Escalation Reasons */}
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                <span className="text-xs text-slate-400 uppercase tracking-wider font-semibold">Human-Readable Explanation</span>
                <p className="text-sm text-slate-200 leading-relaxed font-sans">
                  {selectedAssessment.human_readable_explanation}
                </p>
                {selectedAssessment.escalation_reason && (
                  <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/40 text-amber-300 text-xs mt-2 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                    <span><strong>Escalation Reason:</strong> {selectedAssessment.escalation_reason}</span>
                  </div>
                )}
              </div>

              {/* Dimension Breakdowns */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Trust Score 5 Dimensions */}
                <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                  <h3 className="text-base font-semibold text-white">Trust Assessment Dimensions (Max 100)</h3>
                  <p className="text-xs text-slate-400">Deterministic scoring components for 1–10 ordinal trust</p>

                  <div className="space-y-2.5 pt-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-slate-300">1. Direct Claim Support (Max 35)</span>
                      <span className="font-mono font-bold text-white">
                        {selectedAssessment.score_dimensions.direct_claim_support} / 35
                      </span>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${(selectedAssessment.score_dimensions.direct_claim_support / 35) * 100}%` }}
                        className="bg-indigo-500 h-full rounded-full"
                      />
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1">
                      <span className="text-slate-300">2. Source Reliability (Max 20)</span>
                      <span className="font-mono font-bold text-white">
                        {selectedAssessment.score_dimensions.source_reliability} / 20
                      </span>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${(selectedAssessment.score_dimensions.source_reliability / 20) * 100}%` }}
                        className="bg-indigo-500 h-full rounded-full"
                      />
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1">
                      <span className="text-slate-300">3. Contradiction Handling (Max 15)</span>
                      <span className="font-mono font-bold text-white">
                        {selectedAssessment.score_dimensions.contradiction_handling} / 15
                      </span>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${(selectedAssessment.score_dimensions.contradiction_handling / 15) * 100}%` }}
                        className="bg-indigo-500 h-full rounded-full"
                      />
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1">
                      <span className="text-slate-300">4. Independent Corroboration (Max 15)</span>
                      <span className="font-mono font-bold text-white">
                        {selectedAssessment.score_dimensions.independent_corroboration} / 15
                      </span>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${(selectedAssessment.score_dimensions.independent_corroboration / 15) * 100}%` }}
                        className="bg-indigo-500 h-full rounded-full"
                      />
                    </div>

                    <div className="flex items-center justify-between text-xs pt-1">
                      <span className="text-slate-300">5. Historical Validation Support (Max 15)</span>
                      <span className="font-mono font-bold text-white">
                        {selectedAssessment.score_dimensions.historical_validation_support} / 15
                      </span>
                    </div>
                    <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden">
                      <div
                        style={{ width: `${(selectedAssessment.score_dimensions.historical_validation_support / 15) * 100}%` }}
                        className="bg-indigo-500 h-full rounded-full"
                      />
                    </div>
                  </div>
                </div>

                {/* Evidence Sufficiency & Observed Claims */}
                <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                  <h3 className="text-base font-semibold text-white">Evidence Sufficiency & Supporting Facts</h3>
                  <p className="text-xs text-slate-400">Canonical evidence grounding status</p>

                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between">
                    <span className="text-xs text-slate-300">Evidence Status:</span>
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-md font-mono font-bold ${
                        selectedAssessment.evidence_status === "SUFFICIENT"
                          ? "bg-emerald-950 text-emerald-400"
                          : selectedAssessment.evidence_status === "CONFLICTING"
                          ? "bg-red-950 text-red-400"
                          : "bg-amber-950 text-amber-400"
                      }`}
                    >
                      {selectedAssessment.evidence_status} ({selectedAssessment.evidence_sufficiency_score}%)
                    </span>
                  </div>

                  <div className="space-y-2 pt-1">
                    <span className="text-xs text-slate-400 uppercase font-semibold">Grounded Observations:</span>
                    {selectedAssessment.supporting_evidence.length > 0 ? (
                      <ul className="space-y-1.5 text-xs text-slate-300">
                        {selectedAssessment.supporting_evidence.map((ev, i) => (
                          <li key={i} className="flex items-center gap-2">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                            <span>{ev}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No grounded claims asserted by model.</p>
                    )}
                  </div>

                  {selectedAssessment.missing_evidence.length > 0 && (
                    <div className="space-y-1 pt-2">
                      <span className="text-xs text-amber-400 font-semibold uppercase">Missing Mandatory Telemetry:</span>
                      <ul className="space-y-1 text-xs text-amber-300">
                        {selectedAssessment.missing_evidence.map((mv, i) => (
                          <li key={i} className="flex items-center gap-1.5">
                            <XCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                            <span>{mv}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400">
              <Search className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <p>Enter an Incident ID in the search bar above to drill down into its evidence claims and Trust Score.</p>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* DASHBOARD E: REPLAY & REGRESSION COMPARISON                                */}
      {/* ========================================================================= */}
      {activeTab === "simulation" && (
        <div className="space-y-6">
          {/* Action Header */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 p-5 rounded-xl bg-slate-900/60 border border-slate-800">
            <div>
              <h3 className="text-base font-semibold text-white">Historical Replay & Regression Comparison</h3>
              <p className="text-xs text-slate-400">Execute dry-run backtests and evaluate candidate vs baseline policy regression</p>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="text"
                value={newRunName}
                onChange={(e) => setNewRunName(e.target.value)}
                placeholder="Evaluation Run Name..."
                className="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-56"
              />
              <button
                onClick={handleLaunchEvaluation}
                disabled={launchingRun}
                className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white text-xs font-medium rounded-lg transition"
              >
                <Play className="w-3.5 h-3.5" />
                {launchingRun ? "Replaying..." : "Start Evaluation"}
              </button>
            </div>
          </div>

          {/* Runs Selector & Regression Comparison Panel */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Runs List */}
            <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
              <h4 className="text-xs uppercase text-slate-400 font-semibold">Historical Evaluation Runs</h4>

              <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
                {evaluationRuns.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => handleSelectRun(r.id)}
                    className={`p-3 rounded-lg border cursor-pointer transition ${
                      selectedRunId === r.id
                        ? "bg-indigo-950/40 border-indigo-500/50 text-white"
                        : "bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800/50"
                    }`}
                  >
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold truncate">{r.run_name}</span>
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                          r.validation_state === "VALIDATED"
                            ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                            : r.validation_state === "REGRESSION_DETECTED"
                            ? "bg-red-950 text-red-400 border border-red-800"
                            : "bg-slate-800 text-slate-400"
                        }`}
                      >
                        {r.validation_state}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 mt-2 font-mono">
                      <span>N={r.total_cases}</span>
                      <span>Acc: {r.overall_accuracy !== null ? `${Math.round(r.overall_accuracy * 100)}%` : "N/A"}</span>
                      <span>Cov: {r.automatic_coverage !== null ? `${Math.round(r.automatic_coverage * 100)}%` : "N/A"}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Comparison Controls & Summary */}
            <div className="lg:col-span-2 p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h4 className="text-sm font-semibold text-white">Paired Regression Comparison</h4>

                <div className="flex items-center gap-2">
                  <select
                    value={baselineRunId}
                    onChange={(e) => setBaselineRunId(e.target.value)}
                    className="bg-slate-950 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none"
                  >
                    <option value="">Select Baseline Run...</option>
                    {evaluationRuns
                      .filter((r) => r.id !== selectedRunId)
                      .map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.run_name} ({r.id.slice(0, 8)})
                        </option>
                      ))}
                  </select>

                  <button
                    onClick={handleCompareRuns}
                    disabled={comparing || !baselineRunId}
                    className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition"
                  >
                    {comparing ? "Comparing..." : "Compare"}
                  </button>
                </div>
              </div>

              {comparisonReport ? (
                <div className="space-y-4 pt-1">
                  <div
                    className={`p-4 rounded-xl border flex items-center justify-between ${
                      comparisonReport.validation_state === "VALIDATED"
                        ? "bg-emerald-950/30 border-emerald-800/40 text-emerald-300"
                        : comparisonReport.validation_state === "REGRESSION_DETECTED"
                        ? "bg-red-950/30 border-red-800/40 text-red-300"
                        : "bg-slate-950 border-slate-800 text-slate-300"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      {comparisonReport.validation_state === "VALIDATED" ? (
                        <CheckCircle className="w-5 h-5 text-emerald-400" />
                      ) : (
                        <AlertTriangle className="w-5 h-5 text-red-400" />
                      )}
                      <div>
                        <div className="font-semibold text-sm">
                          Validation State: {comparisonReport.validation_state}
                        </div>
                        <div className="text-xs text-slate-400 mt-0.5 font-sans">
                          {comparisonReport.summary_message}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                      <span className="text-xs text-slate-400">Accuracy Delta</span>
                      <div
                        className={`text-lg font-bold font-mono mt-1 ${
                          (comparisonReport.accuracy_delta || 0) >= 0 ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {(comparisonReport.accuracy_delta || 0) > 0 ? "+" : ""}
                        {comparisonReport.accuracy_delta || 0}%
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                      <span className="text-xs text-slate-400">Coverage Delta</span>
                      <div
                        className={`text-lg font-bold font-mono mt-1 ${
                          comparisonReport.coverage_delta >= 0 ? "text-emerald-400" : "text-amber-400"
                        }`}
                      >
                        {comparisonReport.coverage_delta > 0 ? "+" : ""}
                        {comparisonReport.coverage_delta}%
                      </div>
                    </div>

                    <div className="p-3 bg-slate-950 rounded-lg border border-slate-800">
                      <span className="text-xs text-slate-400">Critical Regressions</span>
                      <div
                        className={`text-lg font-bold font-mono mt-1 ${
                          comparisonReport.critical_regressions_count === 0 ? "text-emerald-400" : "text-red-400"
                        }`}
                      >
                        {comparisonReport.critical_regressions_count}
                      </div>
                    </div>
                  </div>

                  {/* Regressed Cases Table */}
                  {comparisonReport.regressed_cases.length > 0 && (
                    <div className="space-y-2 pt-2">
                      <h5 className="text-xs uppercase text-red-400 font-semibold">Critical Regressed Cases</h5>
                      <div className="rounded-lg border border-red-900/40 bg-red-950/20 overflow-hidden">
                        <table className="w-full text-left text-xs font-mono">
                          <thead>
                            <tr className="border-b border-red-900/40 bg-red-950/40 text-red-300">
                              <th className="py-2 px-3">Incident ID</th>
                              <th className="py-2 px-3">Ground Truth</th>
                              <th className="py-2 px-3">Baseline</th>
                              <th className="py-2 px-3">Candidate</th>
                              <th className="py-2 px-3">Regression Type</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-red-900/20">
                            {comparisonReport.regressed_cases.map((rc, i) => (
                              <tr key={i}>
                                <td className="py-2 px-3 text-slate-200">{rc.incident_id}</td>
                                <td className="py-2 px-3 text-emerald-400">{rc.ground_truth}</td>
                                <td className="py-2 px-3 text-slate-300">{rc.baseline_verdict}</td>
                                <td className="py-2 px-3 text-red-400 font-bold">{rc.candidate_verdict}</td>
                                <td className="py-2 px-3 text-red-300">{rc.regression_type}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 text-xs">
                  Select a baseline evaluation run from the dropdown and click "Compare" to evaluate regression.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VerdictIntelligencePage() {
  return (
    <Suspense fallback={<div className="p-6 text-slate-400">Loading Verdict Intelligence Dashboard...</div>}>
      <VerdictIntelligenceContent />
    </Suspense>
  );
}
