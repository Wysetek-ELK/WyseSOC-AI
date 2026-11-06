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
} from "lucide-react";
import Link from "next/link";
import {
  api,
  DryRunJob,
  EvaluationMetrics,
  RuleMaturity,
  PromptComparisonItem,
  RuleItem,
  User,
} from "@/lib/api";

function EvaluationReportsContent() {
  const searchParams = useSearchParams();
  const urlJobId = searchParams.get("jobId");

  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [jobs, setJobs] = useState<DryRunJob[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [metrics, setMetrics] = useState<EvaluationMetrics | null>(null);
  const [maturityList, setMaturityList] = useState<RuleMaturity[]>([]);
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [promptComparisons, setPromptComparisons] = useState<PromptComparisonItem[]>([]);
  const [selectedRuleForPrompts, setSelectedRuleForPrompts] = useState<string>("");

  const [loading, setLoading] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Approval Modal State
  const [approvingRule, setApprovingRule] = useState<RuleMaturity | null>(null);
  const [approvalNotes, setApprovalNotes] = useState("");
  const [submittingApproval, setSubmittingApproval] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedJobId) {
      loadJobMetrics(selectedJobId);
    }
  }, [selectedJobId]);

  useEffect(() => {
    if (selectedRuleForPrompts) {
      loadPromptComparisons(selectedRuleForPrompts);
    }
  }, [selectedRuleForPrompts]);

  async function loadInitialData() {
    setLoading(true);
    setError(null);
    try {
      const [user, fetchedJobs, fetchedMaturity, fetchedRules] = await Promise.all([
        api.getMe().catch(() => null),
        api.getDryRunJobs(50).catch(() => []),
        api.getRuleMaturityStatus().catch(() => []),
        api.getRules().then((res) => res.items).catch(() => []),
      ]);

      setCurrentUser(user);
      setJobs(fetchedJobs);
      setMaturityList(fetchedMaturity);
      setRules(fetchedRules);

      if (fetchedRules.length > 0) {
        setSelectedRuleForPrompts(fetchedRules[0].id);
      }

      // Determine initial job
      if (urlJobId && fetchedJobs.some((j: DryRunJob) => j.id === urlJobId)) {
        setSelectedJobId(urlJobId);
      } else if (fetchedJobs.length > 0) {
        const completed = fetchedJobs.find((j: DryRunJob) => j.status === "COMPLETED") || fetchedJobs[0];
        setSelectedJobId(completed.id);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load evaluation data");
    } finally {
      setLoading(false);
    }
  }

  async function loadJobMetrics(jobId: string) {
    setLoadingMetrics(true);
    try {
      const data = await api.getJobMetrics(jobId);
      setMetrics(data);
    } catch (err: any) {
      setError("Failed to calculate metrics for selected replay job");
      setMetrics(null);
    } finally {
      setLoadingMetrics(false);
    }
  }

  async function loadPromptComparisons(ruleId: string) {
    try {
      const comparisons = await api.getPromptComparisons(ruleId);
      setPromptComparisons(comparisons);
    } catch (err: any) {
      setPromptComparisons([]);
    }
  }

  async function handleApproveRule() {
    if (!approvingRule) return;
    if (!approvalNotes.trim()) {
      setError("Mandatory approval notes required for production automation sign-off");
      return;
    }

    setSubmittingApproval(true);
    setError(null);
    try {
      await api.approveRuleForAutomation(approvingRule.rule_id, approvalNotes.trim());
      setSuccessMsg(`Rule '${approvingRule.rule_name || approvingRule.rule_id}' approved for automation.`);
      setApprovingRule(null);
      setApprovalNotes("");
      const updated = await api.getRuleMaturityStatus();
      setMaturityList(updated);
    } catch (err: any) {
      setError(err.message || "Failed to approve rule");
    } finally {
      setSubmittingApproval(false);
    }
  }

  const isAdmin = currentUser?.role === "Administrator";

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-foreground">
              Evaluation & Rule Automation Readiness
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Phase 3 Live
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Statistical measurement of precision, recall, coverage, confusion matrices, and progressive automation readiness.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {selectedJobId && (
            <>
              <a
                href={`/api/evaluations/job/${selectedJobId}/export/csv`}
                download
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-secondary hover:bg-secondary/80 text-foreground text-xs font-medium border border-border"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                <span>Export CSV</span>
              </a>
              <a
                href={`/api/evaluations/job/${selectedJobId}/export/json`}
                download
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-secondary hover:bg-secondary/80 text-foreground text-xs font-medium border border-border"
              >
                <FileJson className="w-3.5 h-3.5 text-primary" />
                <span>Export JSON</span>
              </a>
            </>
          )}

          <button
            onClick={() => {
              if (selectedJobId) loadJobMetrics(selectedJobId);
              api.getRuleMaturityStatus().then(setMaturityList);
            }}
            disabled={loadingMetrics}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary hover:bg-secondary/80 text-foreground text-xs border border-border"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingMetrics ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Prominent Simulation Warning */}
      <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-sm space-y-1">
          <div className="font-semibold text-amber-200">
            Phase 3 Dry-Run Simulation Notice
          </div>
          <p className="text-amber-300/90 leading-relaxed text-xs">
            These evaluation metrics reflect deterministic heuristic replay testing on historical incident datasets.
            All results are explicitly marked <code className="px-1 py-0.5 rounded bg-amber-950/80 font-mono text-[11px]">is_simulated = True</code>.
            Real inference accuracy will be evaluated once the dedicated private LLM server (Server 2) is deployed.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-md bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs hover:underline">Dismiss</button>
        </div>
      )}

      {successMsg && (
        <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-xs hover:underline">Dismiss</button>
        </div>
      )}

      {/* Job Selector Bar */}
      <div className="p-4 rounded-lg border border-border bg-card flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Filter className="w-4 h-4 text-primary" />
          <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            Selected Replay Test Run:
          </span>
          <select
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="px-3 py-1.5 rounded-md bg-background border border-border text-foreground text-sm font-medium focus:outline-none focus:ring-1 focus:ring-primary min-w-[300px]"
          >
            {jobs.length === 0 ? (
              <option value="">No Replay Jobs Available</option>
            ) : (
              jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.config_name || "Replay Job"} — {j.status} ({j.processed_items} items, {new Date(j.started_at).toLocaleDateString()})
                </option>
              ))
            )}
          </select>
        </div>

        <Link
          href="/dry-run"
          className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
        >
          <span>Run New Replay Test</span>
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      {/* Top Statistical Metric Cards */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div className="p-4 rounded-lg border border-border bg-card shadow-sm space-y-1">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Verdict Accuracy
            </div>
            <div className="text-2xl font-bold text-foreground">
              {metrics.verdict_accuracy}%
            </div>
            <div className="text-[11px] text-muted-foreground">
              Agreement across resolved cases
            </div>
          </div>

          <div className="p-4 rounded-lg border border-border bg-card shadow-sm space-y-1">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              True Positive Precision
            </div>
            <div className="text-2xl font-bold text-emerald-400">
              {metrics.tp_precision}%
            </div>
            <div className="text-[11px] text-muted-foreground">
              Recall: <strong>{metrics.tp_recall}%</strong>
            </div>
          </div>

          <div className="p-4 rounded-lg border border-border bg-card shadow-sm space-y-1">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              False Positive Precision
            </div>
            <div className="text-2xl font-bold text-blue-400">
              {metrics.fp_precision}%
            </div>
            <div className="text-[11px] text-muted-foreground">
              Recall: <strong>{metrics.fp_recall}%</strong>
            </div>
          </div>

          <div className="p-4 rounded-lg border border-border bg-card shadow-sm space-y-1">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Balanced F1 Score
            </div>
            <div className="text-2xl font-bold text-purple-400">
              {metrics.f1_score}%
            </div>
            <div className="text-[11px] text-muted-foreground">
              Harmonic precision/recall mean
            </div>
          </div>

          <div className="p-4 rounded-lg border border-border bg-card shadow-sm space-y-1">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Abstention Coverage
            </div>
            <div className="text-2xl font-bold text-amber-400">
              {metrics.abstention_coverage}%
            </div>
            <div className="text-[11px] text-muted-foreground">
              Abstained: <strong>{metrics.abstention_count}</strong> cases
            </div>
          </div>
        </div>
      )}

      {/* Confusion Matrix Section */}
      {metrics && (
        <div className="p-5 rounded-lg border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-border">
            <div className="flex items-center gap-2">
              <BarChart2 className="w-4 h-4 text-primary" />
              <h2 className="font-semibold text-foreground text-sm uppercase tracking-wide">
                Confusion Matrix & Decision Distribution
              </h2>
            </div>
            <span className="text-xs text-muted-foreground">
              Sample size: {metrics.total_evaluated} incidents | Average latency: {metrics.average_latency_ms}ms
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-center border-collapse text-xs">
              <thead>
                <tr>
                  <th className="p-3 border border-border bg-secondary/50 font-semibold text-left">
                    Ground Truth (Analyst)
                  </th>
                  <th className="p-3 border border-border bg-secondary/50 font-semibold text-emerald-400">
                    Predicted TRUE_POSITIVE
                  </th>
                  <th className="p-3 border border-border bg-secondary/50 font-semibold text-blue-400">
                    Predicted FALSE_POSITIVE
                  </th>
                  <th className="p-3 border border-border bg-secondary/50 font-semibold text-amber-400">
                    Predicted REQUIRES_ATTENTION (Abstain)
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-3 border border-border font-semibold text-left bg-secondary/20">
                    Actual TRUE_POSITIVE (Confirmed Malicious)
                  </td>
                  <td className="p-3 border border-border bg-emerald-500/10 font-bold text-sm text-emerald-400">
                    {metrics.confusion_matrix.true_positive_as_tp}
                    <div className="text-[10px] text-muted-foreground font-normal">True Positive (Agreed)</div>
                  </td>
                  <td className="p-3 border border-border bg-red-500/10 font-bold text-sm text-red-400">
                    {metrics.confusion_matrix.true_positive_as_fp}
                    <div className="text-[10px] text-muted-foreground font-normal">False Negative (Missed Threat)</div>
                  </td>
                  <td className="p-3 border border-border bg-amber-500/10 font-bold text-sm text-amber-400">
                    {metrics.confusion_matrix.true_positive_as_abstain}
                    <div className="text-[10px] text-muted-foreground font-normal">Abstained (Triage Queue)</div>
                  </td>
                </tr>
                <tr>
                  <td className="p-3 border border-border font-semibold text-left bg-secondary/20">
                    Actual FALSE_POSITIVE (Benign / Noise)
                  </td>
                  <td className="p-3 border border-border bg-red-500/10 font-bold text-sm text-red-400">
                    {metrics.confusion_matrix.false_positive_as_tp}
                    <div className="text-[10px] text-muted-foreground font-normal">False Positive (False Alarm)</div>
                  </td>
                  <td className="p-3 border border-border bg-blue-500/10 font-bold text-sm text-blue-400">
                    {metrics.confusion_matrix.false_positive_as_fp}
                    <div className="text-[10px] text-muted-foreground font-normal">True Negative (Agreed)</div>
                  </td>
                  <td className="p-3 border border-border bg-amber-500/10 font-bold text-sm text-amber-400">
                    {metrics.confusion_matrix.false_positive_as_abstain}
                    <div className="text-[10px] text-muted-foreground font-normal">Abstained (Triage Queue)</div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Rule Automation Readiness Maturity Dashboard */}
      <div className="p-5 rounded-lg border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h2 className="font-semibold text-foreground text-sm uppercase tracking-wide">
              Rule Automation Readiness Maturity Lifecycle
            </h2>
          </div>
          <span className="text-xs text-muted-foreground">
            Strict Multi-Gate Verification: Candidate requires Precision ≥ 95%, Recall ≥ 90%, Coverage ≥ 80%, N ≥ 5
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th className="py-2.5 px-3">SIEM Detection Rule</th>
                <th className="py-2.5 px-3">Maturity Status</th>
                <th className="py-2.5 px-3">Precision</th>
                <th className="py-2.5 px-3">Recall</th>
                <th className="py-2.5 px-3">Coverage</th>
                <th className="py-2.5 px-3">Sample N</th>
                <th className="py-2.5 px-3">Evaluation Justification</th>
                <th className="py-2.5 px-3 text-right">Admin Sign-off</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {maturityList.map((m) => {
                const isCandidate = m.maturity_status === "CANDIDATE_FOR_AUTOMATION";
                const isApproved = m.maturity_status === "APPROVED_FOR_AUTOMATION";
                const isUnderEval = m.maturity_status === "UNDER_EVALUATION";

                return (
                  <tr key={m.id} className="hover:bg-secondary/30 transition-colors">
                    <td className="py-3 px-3">
                      <div className="font-semibold text-foreground">{m.rule_name || m.rule_id}</div>
                      <div className="text-muted-foreground text-[11px]">{m.event_type}</div>
                    </td>

                    <td className="py-3 px-3">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold ${
                          isApproved
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : isCandidate
                            ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                            : isUnderEval
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : "bg-secondary text-muted-foreground border border-border"
                        }`}
                      >
                        {isApproved && <CheckCircle className="w-3 h-3" />}
                        {isCandidate && <ShieldCheck className="w-3 h-3" />}
                        {isUnderEval && <AlertTriangle className="w-3 h-3" />}
                        {m.maturity_status.replace(/_/g, " ")}
                      </span>
                    </td>

                    <td className="py-3 px-3 font-mono font-semibold">
                      <span className={m.precision_score >= 95 ? "text-emerald-400" : "text-foreground"}>
                        {m.precision_score}%
                      </span>
                    </td>

                    <td className="py-3 px-3 font-mono font-semibold">
                      <span className={m.recall_score >= 90 ? "text-emerald-400" : "text-foreground"}>
                        {m.recall_score}%
                      </span>
                    </td>

                    <td className="py-3 px-3 font-mono font-semibold">
                      <span className={m.coverage_score >= 80 ? "text-emerald-400" : "text-foreground"}>
                        {m.coverage_score}%
                      </span>
                    </td>

                    <td className="py-3 px-3 font-mono text-muted-foreground">
                      {m.sample_size} cases
                    </td>

                    <td className="py-3 px-3 text-muted-foreground max-w-xs truncate">
                      {m.recommendation_explanation}
                    </td>

                    <td className="py-3 px-3 text-right">
                      {isApproved ? (
                        <div className="text-[11px] text-emerald-400 font-semibold">
                          ✓ Approved by {m.approved_by_username || "Admin"}
                        </div>
                      ) : isCandidate ? (
                        <button
                          onClick={() => {
                            setApprovingRule(m);
                            setApprovalNotes("Reviewed dry-run replay metrics. Confirmed zero critical false negatives. Approved for dry-run auto-triage.");
                          }}
                          className="px-2.5 py-1 rounded bg-purple-600 hover:bg-purple-500 text-white font-semibold text-xs transition-colors"
                        >
                          Sign-Off Automation
                        </button>
                      ) : (
                        <span className="text-muted-foreground text-[11px]">
                          Thresholds not met
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Prompt Version Comparison Section */}
      <div className="p-5 rounded-lg border border-border bg-card shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-primary" />
            <h2 className="font-semibold text-foreground text-sm uppercase tracking-wide">
              Rule Prompt Version Performance Comparison
            </h2>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Rule:</span>
            <select
              value={selectedRuleForPrompts}
              onChange={(e) => setSelectedRuleForPrompts(e.target.value)}
              className="px-2.5 py-1 rounded bg-background border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {rules.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {promptComparisons.length === 0 ? (
          <div className="p-6 text-center text-xs text-muted-foreground">
            No prompt version comparisons recorded yet for this rule.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-border text-muted-foreground">
                  <th className="py-2.5 px-3">Version Number</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Evaluated Cases</th>
                  <th className="py-2.5 px-3">Accuracy</th>
                  <th className="py-2.5 px-3">TP Precision</th>
                  <th className="py-2.5 px-3">FP Precision</th>
                  <th className="py-2.5 px-3">Coverage</th>
                  <th className="py-2.5 px-3">Avg Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {promptComparisons.map((p) => (
                  <tr key={p.prompt_version_id} className="hover:bg-secondary/30 transition-colors">
                    <td className="py-2.5 px-3 font-bold text-foreground">
                      v{p.prompt_version_number}
                    </td>
                    <td className="py-2.5 px-3 text-muted-foreground">
                      {p.is_template_draft ? "Template Draft" : "Custom Analyst Prompt"}
                    </td>
                    <td className="py-2.5 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          p.status === "ACTIVE"
                            ? "bg-emerald-500/10 text-emerald-400"
                            : "bg-secondary text-muted-foreground"
                        }`}
                      >
                        {p.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono">{p.evaluated_cases}</td>
                    <td className="py-2.5 px-3 font-mono font-semibold text-foreground">
                      {p.verdict_accuracy}%
                    </td>
                    <td className="py-2.5 px-3 font-mono text-emerald-400">
                      {p.tp_precision}%
                    </td>
                    <td className="py-2.5 px-3 font-mono text-blue-400">
                      {p.fp_precision}%
                    </td>
                    <td className="py-2.5 px-3 font-mono text-amber-400">
                      {p.coverage}%
                    </td>
                    <td className="py-2.5 px-3 font-mono text-muted-foreground">
                      {p.average_latency_ms}ms
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Mandatory Administrator Sign-Off Modal */}
      {approvingRule && (
        <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-card border border-border rounded-lg shadow-xl max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center gap-2 border-b border-border pb-3">
              <ShieldCheck className="w-5 h-5 text-purple-400" />
              <h3 className="font-bold text-lg text-foreground">
                Administrator Sign-off: Production Automation Approval
              </h3>
            </div>

            <div className="p-3 rounded-md bg-secondary/40 border border-border text-xs space-y-1.5">
              <div className="font-semibold text-foreground">
                Target SIEM Rule: {approvingRule.rule_name || approvingRule.rule_id}
              </div>
              <div className="text-muted-foreground">
                Event Type: {approvingRule.event_type}
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 font-mono text-[11px]">
                <div>Precision: <strong className="text-emerald-400">{approvingRule.precision_score}%</strong> (≥95%)</div>
                <div>Recall: <strong className="text-emerald-400">{approvingRule.recall_score}%</strong> (≥90%)</div>
                <div>Coverage: <strong className="text-emerald-400">{approvingRule.coverage_score}%</strong> (≥80%)</div>
                <div>Sample Size: <strong className="text-foreground">{approvingRule.sample_size}</strong> (≥5)</div>
              </div>
            </div>

            <div className="space-y-1">
              <label className="block text-xs font-semibold text-foreground">
                Mandatory Audit Notes & Governance Justification *
              </label>
              <textarea
                rows={3}
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="Document your verification rationale, risk assessment, and dry-run performance observations..."
                className="w-full px-3 py-2 rounded-md bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
              <p className="text-[11px] text-muted-foreground">
                All automation sign-offs are immutably recorded in the system audit log.
              </p>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                onClick={() => setApprovingRule(null)}
                className="px-4 py-2 rounded-md bg-secondary hover:bg-secondary/80 text-foreground text-xs font-semibold border border-border"
              >
                Cancel
              </button>
              <button
                onClick={handleApproveRule}
                disabled={submittingApproval}
                className="px-4 py-2 rounded-md bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold transition-colors disabled:opacity-50 flex items-center gap-1.5"
              >
                {submittingApproval ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    <span>Signing Off...</span>
                  </>
                ) : (
                  <>
                    <Check className="w-3.5 h-3.5" />
                    <span>Approve Rule for Automation</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EvaluationReportsPage() {
  return (
    <Suspense
      fallback={
        <div className="p-8 text-center text-muted-foreground text-sm flex items-center justify-center gap-2">
          <RefreshCw className="w-4 h-4 animate-spin text-primary" />
          Loading Evaluation Reports...
        </div>
      }
    >
      <EvaluationReportsContent />
    </Suspense>
  );
}
