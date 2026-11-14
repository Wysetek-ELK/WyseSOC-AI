"use client";

import React, { useState, useEffect } from "react";
import {
  Play,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Clock,
  Layers,
  ShieldAlert,
  Server,
  FileText,
  BarChart2,
  Eye,
  RefreshCw,
  Info,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import Link from "next/link";
import {
  api,
  DryRunConfig,
  DryRunJob,
  DryRunResult,
  RuleItem,
} from "@/lib/api";
import { MetricSummaryCard, NextActionCard, AdvancedDetailsPanel } from "@/components/compact/CompactDesignSystem";

export default function AgentSimulationLabPage() {
  const [configs, setConfigs] = useState<DryRunConfig[]>([]);
  const [jobs, setJobs] = useState<DryRunJob[]>([]);
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [llmStatus, setLlmStatus] = useState<{
    is_healthy: boolean;
    model?: string;
    latency_ms?: number;
    endpoint_provenance?: string;
  } | null>(null);

  // Form State
  const [name, setName] = useState("Dry-Run Simulation Replay");
  const [description, setDescription] = useState("Automated incident replay with deterministic heuristic simulator");
  const [selectedRuleId, setSelectedRuleId] = useState<string>("");
  const [providerType, setProviderType] = useState("SIMULATED");
  const [splitStrategy, setSplitStrategy] = useState("ALL");
  const [sampleLimit, setSampleLimit] = useState<number | "">("");

  // Inspect Modal State
  const [selectedJob, setSelectedJob] = useState<DryRunJob | null>(null);
  const [jobResults, setJobResults] = useState<DryRunResult[]>([]);
  const [loadingResults, setLoadingResults] = useState(false);
  const [selectedResult, setSelectedResult] = useState<DryRunResult | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      const [fetchedRules, fetchedJobs, fetchedConfigs, fetchedLlmStatus] = await Promise.all([
        api.getRules().then((res) => res.items).catch(() => []),
        api.getDryRunJobs(30).catch(() => []),
        api.getDryRunConfigs().catch(() => []),
        api.getLlmStatus().catch(() => null),
      ]);
      setRules(fetchedRules);
      setJobs(fetchedJobs);
      setConfigs(fetchedConfigs);
      setLlmStatus(fetchedLlmStatus);
      if (fetchedLlmStatus?.is_healthy) {
        setProviderType("OPENAI_COMPATIBLE");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load dry-run data");
    } finally {
      setLoading(false);
    }
  }

  async function handleLaunch() {
    if (!name.trim()) {
      setError("Please provide a configuration name");
      return;
    }

    setLaunching(true);
    setError(null);
    setSuccessMsg(null);

    try {
      // 1. Create Config
      const newConfig = await api.createDryRunConfig({
        name: name.trim(),
        description: description.trim(),
        rule_id: selectedRuleId || undefined,
        provider_type: providerType,
        split_strategy: splitStrategy,
      });

      // 2. Trigger Job
      const limit = typeof sampleLimit === "number" && sampleLimit > 0 ? sampleLimit : undefined;
      const job = await api.triggerDryRunJob(newConfig.id, limit);

      setSuccessMsg(`Dry-run replay job launched and completed: ${job.processed_items} incidents processed.`);
      await loadData();
      inspectJob(job);
    } catch (err: any) {
      setError(err.message || "Execution failed");
    } finally {
      setLaunching(false);
    }
  }

  async function inspectJob(job: DryRunJob) {
    setSelectedJob(job);
    setSelectedResult(null);
    setLoadingResults(true);
    try {
      const results = await api.getDryRunJobResults(job.id, 100);
      setJobResults(results);
      if (results.length > 0) {
        setSelectedResult(results[0]);
      }
    } catch (err: any) {
      setError("Failed to load job results");
    } finally {
      setLoadingResults(false);
    }
  }

  return (
    <div className="space-y-3.5">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2.5 border-b border-border">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg sm:text-xl font-bold text-foreground">Agent Simulation Lab</h1>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Validation Engine
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            Controlled testing, heuristic simulation, and replay benchmarking without production impact.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-secondary/40 border border-border text-xs text-muted-foreground">
            <Server className={`w-3 h-3 ${llmStatus?.is_healthy ? "text-emerald-400" : "text-amber-400"}`} />
            <span>
              Server 2 LLM:{" "}
              {llmStatus?.endpoint_provenance === "HTTP_MOCK" ? (
                <strong className="text-cyan-300">HTTP_MOCK ({llmStatus.model || "Test Endpoint"})</strong>
              ) : llmStatus?.is_healthy ? (
                <strong className="text-emerald-400">Connected ({llmStatus.model || "Qwen 2.5 7B"})</strong>
              ) : (
                <strong className="text-foreground">Disconnected (Phase 3 Guard)</strong>
              )}
            </span>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-secondary hover:bg-secondary/80 text-foreground text-xs border border-border"
          >
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Compact Simulation Metrics Row */}
      {(() => {
        const totalItemsEvaluated = jobs.reduce((acc, j) => acc + (j.processed_items || 0), 0);
        const verifiedCases = jobResults.filter((r) => r.ground_truth_verdict && r.ground_truth_verdict !== "Unlabeled");
        const agreedCases = verifiedCases.filter((r) => r.is_agreement).length;
        const accuracyText = verifiedCases.length > 0
          ? `${Math.round((agreedCases / verifiedCases.length) * 100)}%`
          : "N/A (Pending Ground Truth)";

        return (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <MetricSummaryCard
                label="Replay Engine"
                value={llmStatus?.is_healthy ? "Local LLM" : "Heuristic Sim"}
                subtext={llmStatus?.is_healthy ? `${llmStatus.model || "Qwen 2.5"}` : "Deterministic Fallback"}
                status={llmStatus?.is_healthy ? "success" : "normal"}
              />
              <MetricSummaryCard
                label="Replay Batches"
                value={jobs.length}
                subtext={`${configs.length} active configurations`}
                status="normal"
              />
              <MetricSummaryCard
                label="Scanned Incidents"
                value={totalItemsEvaluated}
                subtext="Total items processed across jobs"
                status="normal"
              />
              <MetricSummaryCard
                label="Empirical Accuracy"
                value={accuracyText}
                subtext={verifiedCases.length > 0 ? `${verifiedCases.length} verified ground truth cases` : "Requires verified analyst cases"}
                status={verifiedCases.length > 0 ? "success" : "neutral"}
              />
            </div>

            <NextActionCard
              title={selectedJob ? `Inspecting Replay Batch: ${selectedJob.config_name || selectedJob.id}` : "Configure and Launch Replay Batch"}
              description={selectedJob ? "Examine predicted verdicts and reasoning below, or open statistical evaluation reports in Verdict Intelligence." : "Select a detection rule and partition strategy to benchmark agent policies against historical incidents."}
              actionLabel={selectedJob ? "View Evaluation Report" : "Launch Replay"}
              onAction={selectedJob ? () => { window.location.href = `/verdict-intelligence?jobId=${selectedJob.id}`; } : handleLaunch}
              status="primary"
            />
          </>
        );
      })()}

      {/* Prominent Simulation Guard Warning */}
      <div className="p-2.5 sm:p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-start gap-2.5">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-0.5">
          <div className="font-semibold text-amber-200">
            Dry-Run Simulation Guardrail Active
          </div>
          <p className="text-amber-300/90 leading-relaxed text-[11px]">
            All verdicts are generated by deterministic heuristic simulation algorithms and explicitly tagged{" "}
            <code className="px-1 py-0.5 rounded bg-amber-950/80 font-mono text-[10px]">is_simulated = True</code>.
            All historical closure fields (<code className="px-1 py-0.5 rounded bg-amber-950/80 font-mono text-[10px]">resolution</code>,{" "}
            <code className="px-1 py-0.5 rounded bg-amber-950/80 font-mono text-[10px]">comments</code>,{" "}
            <code className="px-1 py-0.5 rounded bg-amber-950/80 font-mono text-[10px]">clearedReason</code>) are strictly isolated
            from model input payloads to prevent data leakage.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-2.5 rounded-md bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-xs hover:underline">Dismiss</button>
        </div>
      )}

      {successMsg && (
        <div className="p-2.5 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} className="text-xs hover:underline">Dismiss</button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
        {/* Left Column: Replay Launcher Configuration */}
        <div className="lg:col-span-5 space-y-3.5">
          <div className="p-3 sm:p-3.5 rounded-lg border border-border bg-card shadow-sm space-y-3">
            <div className="flex items-center gap-2 pb-2 border-b border-border">
              <Play className="w-3.5 h-3.5 text-primary" />
              <h2 className="font-semibold text-foreground text-xs uppercase tracking-wide">
                Configure Dry-Run Replay
              </h2>
            </div>

            <div className="space-y-2.5 text-xs">
              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                  Replay Job Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-md bg-background border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="e.g. CrowdStrike Suspicious Activity Replay"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                  Target SIEM Detection Rule
                </label>
                <select
                  value={selectedRuleId}
                  onChange={(e) => setSelectedRuleId(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-md bg-background border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">All Detection Rules (Full Dataset)</option>
                  {rules.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} ({r.event_type})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                  Inference Model Provider
                </label>
                <select
                  value={providerType}
                  onChange={(e) => setProviderType(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-md bg-background border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary font-mono text-[11px]"
                >
                  <option value="OPENAI_COMPATIBLE">
                    OPENAI_COMPATIBLE ({llmStatus?.endpoint_provenance === "HTTP_MOCK" ? "HTTP_MOCK Test Endpoint" : llmStatus?.is_healthy ? "Server 2 Configured Endpoint — Online" : "Server 2 vLLM Node"})
                  </option>
                  <option value="SIMULATED">SIMULATED (Deterministic Heuristics - Fallback)</option>
                  <option value="DISABLED">DISABLED (Safe Provider Default)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                  Dataset Splitting Strategy
                </label>
                <select
                  value={splitStrategy}
                  onChange={(e) => setSplitStrategy(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-md bg-background border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="ALL">ALL (100% Ingested Rule Incidents)</option>
                  <option value="CHRONOLOGICAL_70_30">
                    CHRONOLOGICAL_70_30 (Holdout 30% Most Recent Incidents)
                  </option>
                  <option value="GROUP_AWARE_HOST">
                    GROUP_AWARE_HOST (Group by Host Device to Prevent Leakage)
                  </option>
                </select>
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  Prevents training/evaluation contamination across related security telemetry.
                </p>
              </div>

              <div>
                <label className="block text-[11px] font-medium text-muted-foreground mb-1">
                  Sample Limit (Optional)
                </label>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={sampleLimit}
                  onChange={(e) => setSampleLimit(e.target.value ? parseInt(e.target.value) : "")}
                  placeholder="Leave empty to test full partition"
                  className="w-full px-2.5 py-1.5 rounded-md bg-background border border-border text-foreground text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-1">
                <button
                  onClick={handleLaunch}
                  disabled={launching}
                  className="w-full py-2 px-3 rounded-md bg-primary hover:bg-primary/90 text-primary-foreground font-semibold text-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  {launching ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Executing Batch Replay...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5" />
                      <span>Launch Dry-Run Replay</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Architecture Card */}
          <div className="p-3 rounded-lg border border-border bg-card/60 text-[11px] space-y-1.5 text-muted-foreground">
            <div className="flex items-center gap-1.5 font-semibold text-foreground text-xs">
              <Info className="w-3 h-3 text-primary" />
              <span>Dry-Run Pipeline Flow</span>
            </div>
            <p>
              1. <strong>Strict Allowlist:</strong> Normalized incident without ground truth is extracted.
            </p>
            <p>
              2. <strong>Provider Call:</strong> Dispatched to provider abstraction with timeout and schema guard.
            </p>
            <p>
              3. <strong>Defensive Fallback:</strong> Any schema breach defaults to <code>REQUIRES_ATTENTION</code>.
            </p>
            <p>
              4. <strong>Automated Metric Rollup:</strong> Updates rule readiness metrics for evaluation reports.
            </p>
          </div>
        </div>

        {/* Right Column: Recent Jobs Table */}
        <div className="lg:col-span-7 space-y-3">
          <div className="p-3 sm:p-3.5 rounded-lg border border-border bg-card shadow-sm space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-border">
              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-primary" />
                <h2 className="font-semibold text-foreground text-xs uppercase tracking-wide">
                  Replay Job History ({jobs.length})
                </h2>
              </div>
              <span className="text-[11px] text-muted-foreground">Select a job to inspect results</span>
            </div>

            {jobs.length === 0 ? (
              <div className="p-6 text-center text-muted-foreground text-xs">
                No dry-run replay jobs executed yet. Launch a replay configuration on the left.
              </div>
            ) : (
              <div className="divide-y divide-border overflow-hidden rounded-md border border-border">
                {jobs.map((job) => {
                  const isSelected = selectedJob?.id === job.id;
                  return (
                    <div
                      key={job.id}
                      onClick={() => inspectJob(job)}
                      className={`p-2.5 transition-colors cursor-pointer flex items-center justify-between hover:bg-secondary/40 ${
                        isSelected ? "bg-primary/10 border-l-4 border-l-primary" : "bg-card"
                      }`}
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-xs text-foreground">
                            {job.config_name || "Dry-Run Job"}
                          </span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                              job.status === "COMPLETED"
                                ? "bg-emerald-500/10 text-emerald-400"
                                : job.status === "FAILED"
                                ? "bg-red-500/10 text-red-400"
                                : "bg-amber-500/10 text-amber-400"
                            }`}
                          >
                            {job.status}
                          </span>
                          {job.is_simulated && (
                            <span className="px-1.5 py-0.2 rounded text-[9px] bg-secondary text-amber-300 border border-amber-500/30">
                              SIMULATED
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-muted-foreground flex items-center gap-2.5">
                          <span>Processed: {job.processed_items} / {job.total_items}</span>
                          <span>Errors: {job.error_count}</span>
                          <span>Started: {new Date(job.started_at).toLocaleTimeString()}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Link
                          href={`/verdict-intelligence?jobId=${job.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="px-2 py-0.5 rounded bg-secondary hover:bg-secondary/80 text-foreground text-[11px] font-medium border border-border flex items-center gap-1"
                        >
                          <BarChart2 className="w-3 h-3 text-primary" />
                          <span>Evaluation</span>
                        </Link>
                        <ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Results Inspector Modal / Section */}
      {selectedJob && (
        <div className="p-3 sm:p-3.5 rounded-lg border border-border bg-card shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-2.5 border-b border-border">
            <div>
              <h3 className="text-sm sm:text-base font-bold text-foreground flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary" />
                Replay Results: {selectedJob.config_name || selectedJob.id}
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Inspecting individual incident verdicts, model reasoning, and ground-truth comparisons.
              </p>
            </div>

            <div className="flex items-center gap-1.5">
              <Link
                href={`/verdict-intelligence?jobId=${selectedJob.id}`}
                className="px-2.5 py-1 rounded-md bg-primary hover:bg-primary/90 text-primary-foreground text-xs font-semibold flex items-center gap-1.5"
              >
                <BarChart2 className="w-3 h-3" />
                View Full Report
              </Link>
              <a
                href={`/api/evaluations/job/${selectedJob.id}/export/csv`}
                download
                className="px-2.5 py-1 rounded-md bg-secondary hover:bg-secondary/80 text-foreground text-xs font-medium border border-border flex items-center gap-1.5"
              >
                CSV
              </a>
              <a
                href={`/api/evaluations/job/${selectedJob.id}/export/json`}
                download
                className="px-2.5 py-1 rounded-md bg-secondary hover:bg-secondary/80 text-foreground text-xs font-medium border border-border flex items-center gap-1.5"
              >
                JSON
              </a>
            </div>
          </div>

          {loadingResults ? (
            <div className="p-6 text-center text-xs text-muted-foreground flex items-center justify-center gap-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-primary" />
              Loading replay results...
            </div>
          ) : jobResults.length === 0 ? (
            <div className="p-6 text-center text-xs text-muted-foreground">
              No results recorded for this job.
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
              {/* Results List */}
              <div className="lg:col-span-5 border border-border rounded-md overflow-hidden max-h-[420px] overflow-y-auto divide-y divide-border bg-background">
                {jobResults.map((r) => {
                  const isCur = selectedResult?.id === r.id;
                  return (
                    <div
                      key={r.id}
                      onClick={() => setSelectedResult(r)}
                      className={`p-2 text-xs cursor-pointer transition-colors ${
                        isCur ? "bg-primary/10 border-l-4 border-l-primary" : "hover:bg-secondary/40"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="font-mono font-bold text-foreground text-[11px]">
                          {r.incident_vendor_id || r.incident_id.slice(0, 10)}
                        </span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                            r.predicted_verdict === "TRUE_POSITIVE"
                              ? "bg-red-500/10 text-red-400"
                              : r.predicted_verdict === "FALSE_POSITIVE"
                              ? "bg-emerald-500/10 text-emerald-400"
                              : "bg-amber-500/10 text-amber-400"
                          }`}
                        >
                          {r.predicted_verdict}
                        </span>
                      </div>
                      <div className="text-muted-foreground text-[11px] truncate">{r.incident_title || r.rule_name}</div>
                      <div className="mt-0.5 flex items-center justify-between text-[10px] text-muted-foreground">
                        <span>Confidence: {r.confidence}%</span>
                        <span className={`font-semibold ${r.is_agreement ? "text-emerald-400" : "text-amber-400"}`}>
                          {r.is_agreement ? "✓ Agreed" : "≠ Disagreed/Abstained"}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Result Detail Inspector */}
              <div className="lg:col-span-7 p-3 border border-border rounded-md bg-background text-xs space-y-3">
                {selectedResult ? (
                  <>
                    <div className="flex items-start justify-between border-b border-border pb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-sm text-foreground">
                            {selectedResult.incident_vendor_id || selectedResult.incident_id}
                          </span>
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              selectedResult.predicted_verdict === "TRUE_POSITIVE"
                                ? "bg-red-500/10 text-red-400"
                                : selectedResult.predicted_verdict === "FALSE_POSITIVE"
                                ? "bg-emerald-500/10 text-emerald-400"
                                : "bg-amber-500/10 text-amber-400"
                            }`}
                          >
                            Model: {selectedResult.predicted_verdict}
                          </span>
                          {selectedResult.is_simulated && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] bg-amber-500/10 text-amber-400 border border-amber-500/30">
                              SIMULATED
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-muted-foreground mt-0.5">
                          Rule: {selectedResult.rule_name || "Unknown"} | Latency: {selectedResult.latency_ms}ms | Model: {selectedResult.model_identifier}
                        </div>
                      </div>

                      <div className="text-right text-[11px]">
                        <div className="text-muted-foreground">Historical Analyst Ground Truth:</div>
                        <div className="font-bold text-foreground mt-0.5">
                          {selectedResult.ground_truth_verdict || "Unlabeled"}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                        Reasoning & Analytical Justification
                      </div>
                      <div className="p-2.5 rounded-md bg-secondary/30 border border-border font-mono text-[11px] text-foreground/90 leading-relaxed whitespace-pre-wrap">
                        {selectedResult.reasoning}
                      </div>
                    </div>

                    {selectedResult.supporting_evidence.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider">
                          Supporting Evidence Cited ({selectedResult.supporting_evidence.length})
                        </div>
                        <ul className="list-disc list-inside text-[11px] text-muted-foreground space-y-0.5">
                          {selectedResult.supporting_evidence.map((ev, i) => (
                            <li key={i}>{ev}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {(selectedResult.missing_evidence.length > 0 || selectedResult.analyst_questions.length > 0) && (
                      <AdvancedDetailsPanel
                        title={`Investigation Diagnostics (${selectedResult.missing_evidence.length} gaps, ${selectedResult.analyst_questions.length} questions)`}
                        defaultOpen={false}
                      >
                        <div className="space-y-3 pt-1">
                          {selectedResult.missing_evidence.length > 0 && (
                            <div className="space-y-1">
                              <div className="text-[10px] font-semibold text-amber-400 uppercase tracking-wider">
                                Missing Telemetry / Information Gaps
                              </div>
                              <ul className="list-disc list-inside text-[11px] text-muted-foreground space-y-0.5">
                                {selectedResult.missing_evidence.map((gap, i) => (
                                  <li key={i}>{gap}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {selectedResult.analyst_questions.length > 0 && (
                            <div className="space-y-1">
                              <div className="text-[10px] font-semibold text-primary uppercase tracking-wider">
                                Recommended Analyst Clarification Questions
                              </div>
                              <ul className="list-disc list-inside text-[11px] text-muted-foreground space-y-0.5">
                                {selectedResult.analyst_questions.map((q, i) => (
                                  <li key={i}>{q}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      </AdvancedDetailsPanel>
                    )}
                  </>
                ) : (
                  <div className="p-6 text-center text-muted-foreground text-xs">
                    Select a result from the list to view model reasoning.
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
