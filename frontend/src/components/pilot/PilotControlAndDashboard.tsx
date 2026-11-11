"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  PauseCircle,
  Play,
  PowerOff,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sliders,
  Lock,
  UserCheck,
  FileText,
} from "lucide-react";
import {
  api,
  PilotConfig,
  PilotConfigHistoryItem,
  PilotEvaluationItem,
  PilotMetricsResponse,
} from "@/lib/api";
import { useApp } from "@/context/AppContext";

interface PilotControlProps {
  onError?: (msg: string | null) => void;
  onSuccess?: (msg: string | null) => void;
}

export default function PilotControlAndDashboard({ onError, onSuccess }: PilotControlProps) {
  const { user } = useApp();
  const isAdmin = user?.role === "Administrator";
  const isAnalystOrAdmin = user?.role === "Administrator" || user?.role === "SOC Analyst";

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [localSuccess, setLocalSuccess] = useState<string | null>(null);

  const [config, setConfig] = useState<PilotConfig | null>(null);
  const [metrics, setMetrics] = useState<PilotMetricsResponse | null>(null);
  const [history, setHistory] = useState<PilotConfigHistoryItem[]>([]);
  const [evaluations, setEvaluations] = useState<PilotEvaluationItem[]>([]);
  const [auditItems, setAuditItems] = useState<any[]>([]);
  const [modeFilter, setModeFilter] = useState<string>("ALL");

  // Config form fields
  const [pilotName, setPilotName] = useState("Default SOC Pilot");
  const [description, setDescription] = useState("");
  const [ingestionSource, setIngestionSource] = useState<"ALL" | "LIVE" | "HISTORICAL">("ALL");
  const [ruleIdsText, setRuleIdsText] = useState("");
  const [archetypesText, setArchetypesText] = useState("");
  const [severities, setSeverities] = useState<string[]>(["CRITICAL", "HIGH", "MEDIUM", "LOW"]);
  const [dailyBudget, setDailyBudget] = useState(500);
  const [hourlyBudget, setHourlyBudget] = useState(100);
  const [maxConcurrency, setMaxConcurrency] = useState(2);
  const [timeoutSeconds, setTimeoutSeconds] = useState(60);
  const [errorPolicy, setErrorPolicy] = useState<"ABSTAIN_AND_LOG" | "PAUSE_ON_CONSECUTIVE_ERRORS">("ABSTAIN_AND_LOG");
  const [errorThreshold, setErrorThreshold] = useState(5);
  const [reportingSchedule, setReportingSchedule] = useState<"HOURLY" | "DAILY" | "MANUAL">("HOURLY");
  const [requireApprovedPolicy, setRequireApprovedPolicy] = useState(true);
  const [requireAnalystReview, setRequireAnalystReview] = useState(true);
  const [changeReason, setChangeReason] = useState("Controlled SOC Pilot settings update");

  // Controlled batch runner
  const [batchSourceType, setBatchSourceType] = useState<"LIVE" | "HISTORICAL">("LIVE");
  const [batchMax, setBatchMax] = useState(10);
  const [batchAllowSimulated, setBatchAllowSimulated] = useState(false);
  const [batchSummary, setBatchSummary] = useState<any | null>(null);

  // Analyst feedback inline modal
  const [activeFeedbackId, setActiveFeedbackId] = useState<string | null>(null);
  const [feedbackAction, setFeedbackAction] = useState<"ACCEPTED" | "OVERRIDDEN" | "DISPUTED" | "REQUESTED_EVIDENCE">("ACCEPTED");
  const [feedbackDecision, setFeedbackDecision] = useState<"TRUE_POSITIVE" | "FALSE_POSITIVE" | "REQUIRES_ATTENTION">("TRUE_POSITIVE");
  const [feedbackReason, setFeedbackReason] = useState("");

  const reportError = (msg: string | null) => {
    setLocalError(msg);
    if (onError) onError(msg);
  };

  const reportSuccess = (msg: string | null) => {
    setLocalSuccess(msg);
    if (onSuccess) onSuccess(msg);
  };

  const loadPilotData = useCallback(async () => {
    setLoading(true);
    try {
      const [cfg, met, hist, evals, aud] = await Promise.all([
        api.getPilotConfig(),
        api.getPilotMetrics(),
        api.getPilotHistory().catch(() => []),
        api.getPilotEvaluations(modeFilter === "ALL" ? undefined : modeFilter, true).catch(() => []),
        api.getPilotAuditLogs().catch(() => ({ items: [], total: 0 })),
      ]);
      setConfig(cfg);
      setMetrics(met);
      setHistory(hist);
      setEvaluations(evals);
      setAuditItems(aud.items || []);

      // Sync form state
      setPilotName(cfg.pilot_name);
      setDescription(cfg.description || "");
      setIngestionSource(cfg.ingestion_source);
      setRuleIdsText((cfg.selected_rule_ids || []).join(", "));
      setArchetypesText((cfg.selected_archetypes || []).join(", "));
      setSeverities(cfg.included_severities || ["CRITICAL", "HIGH", "MEDIUM", "LOW"]);
      setDailyBudget(cfg.daily_evaluation_budget);
      setHourlyBudget(cfg.hourly_evaluation_budget);
      setMaxConcurrency(cfg.max_concurrent_inference);
      setTimeoutSeconds(cfg.request_timeout_seconds);
      setErrorPolicy((cfg.error_handling_policy as any) || "ABSTAIN_AND_LOG");
      setErrorThreshold(cfg.consecutive_error_pause_threshold || 5);
      setReportingSchedule((cfg.reporting_schedule as any) || "HOURLY");
      setRequireApprovedPolicy(Boolean(cfg.require_approved_policy));
      setRequireAnalystReview(Boolean(cfg.require_analyst_review));
    } catch (err: any) {
      reportError(err.message || "Failed to load SOC Pilot state");
    } finally {
      setLoading(false);
    }
  }, [modeFilter]);

  useEffect(() => {
    loadPilotData();
  }, [loadPilotData]);

  const toggleSeverity = (sev: string) => {
    setSeverities((prev) =>
      prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev]
    );
  };

  async function handleSaveConfig(e: React.FormEvent) {
    e.preventDefault();
    if (!isAdmin) return;
    setBusy(true);
    reportError(null);
    reportSuccess(null);
    try {
      const ruleList = ruleIdsText.split(",").map((s) => s.trim()).filter(Boolean);
      const archList = archetypesText.split(",").map((s) => s.trim()).filter(Boolean);
      const updated = await api.updatePilotConfig({
        pilot_name: pilotName,
        description,
        mode: config?.mode || "DISABLED",
        selected_rule_ids: ruleList,
        selected_archetypes: archList,
        included_severities: severities,
        ingestion_source: ingestionSource,
        daily_evaluation_budget: Number(dailyBudget),
        hourly_evaluation_budget: Number(hourlyBudget),
        max_concurrent_inference: Number(maxConcurrency),
        request_timeout_seconds: Number(timeoutSeconds),
        require_analyst_review: requireAnalystReview,
        require_approved_policy: requireApprovedPolicy,
        allow_external_writeback: false,
        allow_auto_incident_closure: false,
        error_handling_policy: errorPolicy,
        consecutive_error_pause_threshold: Number(errorThreshold),
        reporting_schedule: reportingSchedule,
        change_reason: changeReason || "Pilot configuration update",
      });
      setConfig(updated);
      reportSuccess(`Pilot configuration saved (v${updated.version_number}).`);
      await loadPilotData();
    } catch (err: any) {
      reportError(err.message || "Failed to save pilot configuration");
    } finally {
      setBusy(false);
    }
  }

  async function handleActivate(mode: "SHADOW" | "ANALYST_ASSISTED") {
    if (!isAdmin) return;
    setBusy(true);
    reportError(null);
    reportSuccess(null);
    try {
      const updated = await api.activatePilot(mode, `Operator activated ${mode} mode`);
      setConfig(updated);
      reportSuccess(`SOC Pilot switched to ${updated.mode} mode (v${updated.version_number}).`);
      await loadPilotData();
    } catch (err: any) {
      reportError(err.message || `Failed to activate ${mode}`);
    } finally {
      setBusy(false);
    }
  }

  async function handlePauseResume(pause: boolean) {
    if (!isAdmin) return;
    setBusy(true);
    reportError(null);
    reportSuccess(null);
    try {
      const updated = pause
        ? await api.pausePilot("Operator paused pilot execution")
        : await api.resumePilot("Operator resumed pilot execution");
      setConfig(updated);
      reportSuccess(pause ? "SOC Pilot paused." : "SOC Pilot resumed.");
      await loadPilotData();
    } catch (err: any) {
      reportError(err.message || "Failed to change pilot pause state");
    } finally {
      setBusy(false);
    }
  }

  async function handleDisable() {
    if (!isAdmin) return;
    setBusy(true);
    reportError(null);
    reportSuccess(null);
    try {
      const updated = await api.disablePilot("Safe pilot disable preserving history");
      setConfig(updated);
      reportSuccess("SOC Pilot safely DISABLED. Historical verdicts and audit logs remain preserved.");
      await loadPilotData();
    } catch (err: any) {
      reportError(err.message || "Failed to disable pilot");
    } finally {
      setBusy(false);
    }
  }

  async function handleRollback(versionNumber: number) {
    if (!isAdmin) return;
    setBusy(true);
    reportError(null);
    reportSuccess(null);
    try {
      const updated = await api.rollbackPilot(versionNumber, `Rollback to pilot configuration v${versionNumber}`);
      setConfig(updated);
      reportSuccess(`Rolled back Pilot configuration cleanly to v${versionNumber} (now v${updated.version_number}).`);
      await loadPilotData();
    } catch (err: any) {
      reportError(err.message || "Failed to rollback pilot configuration");
    } finally {
      setBusy(false);
    }
  }

  async function handleRunBatch() {
    if (!isAnalystOrAdmin) return;
    setBusy(true);
    reportError(null);
    reportSuccess(null);
    setBatchSummary(null);
    try {
      const res = await api.runPilotBatch({
        max_batch: Number(batchMax),
        source_type: batchSourceType,
        allow_simulated: batchSourceType === "HISTORICAL" ? batchAllowSimulated : false,
      });
      setBatchSummary(res);
      const errCount = Number(res.failed || 0);
      const evalCount = Number(res.evaluated || 0);
      const skipCount = Number(res.skipped || 0);
      if (res.status === "SKIPPED" || res.status === "DISABLED") {
        reportError(`Batch stopped: ${res.reason || res.status}`);
      } else if (errCount > 0 && evalCount === 0) {
        reportError(`Batch completed with ${errCount} inference failures (Local LLM provider unavailable or abstained).`);
      } else {
        reportSuccess(`Pilot batch finished: ${evalCount} evaluated, ${res.abstained || 0} abstained, ${skipCount} skipped/ineligible.`);
      }
      await loadPilotData();
    } catch (err: any) {
      reportError(err.message || "Failed to execute controlled pilot batch");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitFeedback(evalId: string) {
    if (!isAnalystOrAdmin) return;
    if (!feedbackReason.trim() || feedbackReason.trim().length < 3) {
      reportError("Please provide an analyst reason (at least 3 characters).");
      return;
    }
    setBusy(true);
    reportError(null);
    try {
      await api.submitPilotFeedback(evalId, {
        action: feedbackAction,
        analyst_decision: feedbackDecision,
        reason: feedbackReason.trim(),
      });
      setActiveFeedbackId(null);
      setFeedbackReason("");
      reportSuccess("Analyst feedback recorded separately without modifying AI recommendation.");
      await loadPilotData();
    } catch (err: any) {
      reportError(err.message || "Failed to submit analyst feedback");
    } finally {
      setBusy(false);
    }
  }

  async function handleSupervisorVerify(evalId: string) {
    if (!isAdmin) return;
    setBusy(true);
    reportError(null);
    try {
      await api.supervisorVerifyPilotFeedback(evalId, {
        approved: true,
        notes: "Independent supervisor verification approved in UI",
      });
      reportSuccess("Supervisor verification recorded.");
      await loadPilotData();
    } catch (err: any) {
      reportError(err.message || "Supervisor verification failed");
    } finally {
      setBusy(false);
    }
  }

  const fmtPct = (v?: number | null) => (v != null ? `${Math.round(v * 100)}%` : "N/A");
  const modeColor =
    config?.mode === "ANALYST_ASSISTED"
      ? "bg-emerald-950/70 text-emerald-300 border-emerald-700"
      : config?.mode === "SHADOW"
      ? "bg-indigo-950/70 text-indigo-300 border-indigo-700"
      : "bg-slate-900 text-slate-300 border-slate-700";

  return (
    <div className="space-y-6" data-testid="soc-pilot-dashboard">
      {/* Status Banner + Lifecycle Controls */}
      <div className="p-5 rounded-xl bg-slate-900/70 border border-slate-800 space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className={`px-2.5 py-0.5 text-xs font-mono font-bold rounded border ${modeColor}`} data-testid="pilot-mode-badge">
                MODE: {config?.mode || "DISABLED"}
              </span>
              {config?.is_paused && (
                <span className="px-2 py-0.5 text-xs font-mono font-bold rounded border bg-amber-950 text-amber-300 border-amber-700">
                  PAUSED
                </span>
              )}
              <span className="px-2 py-0.5 text-xs font-mono rounded bg-slate-950 text-slate-400 border border-slate-800">
                Config v{config?.version_number || 1}
              </span>
              <span className="px-2 py-0.5 text-xs font-mono rounded bg-slate-950 text-cyan-400 border border-slate-800">
                Role: {user?.role || "Unknown"}
              </span>
            </div>
            <h3 className="text-lg font-semibold text-white mt-2">
              {config?.pilot_name || "Default SOC Pilot"} — Controlled Rollout &amp; Monitoring
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Zero autonomous SIEM writebacks • Zero auto-closures • AI recommendations remain permanently separated from human decisions.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={loadPilotData}
              disabled={loading || busy}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs text-slate-300 hover:text-white"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>

            <button
              type="button"
              disabled={!isAdmin || busy || config?.mode === "SHADOW"}
              onClick={() => handleActivate("SHADOW")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/90 hover:bg-indigo-600 disabled:opacity-40 text-white text-xs font-semibold"
              data-testid="btn-activate-shadow"
            >
              <Activity className="w-3.5 h-3.5" />
              Activate SHADOW
            </button>

            <button
              type="button"
              disabled={!isAdmin || busy || config?.mode === "ANALYST_ASSISTED"}
              onClick={() => handleActivate("ANALYST_ASSISTED")}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/90 hover:bg-emerald-600 disabled:opacity-40 text-white text-xs font-semibold"
              data-testid="btn-activate-assisted"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Activate ANALYST_ASSISTED
            </button>

            {config?.mode !== "DISABLED" && (
              <button
                type="button"
                disabled={!isAdmin || busy}
                onClick={() => handlePauseResume(!config?.is_paused)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-950/80 hover:bg-amber-900 border border-amber-700 disabled:opacity-40 text-amber-200 text-xs font-semibold"
                data-testid="btn-pause-resume"
              >
                {config?.is_paused ? <Play className="w-3.5 h-3.5" /> : <PauseCircle className="w-3.5 h-3.5" />}
                {config?.is_paused ? "Resume Pilot" : "Pause Pilot"}
              </button>
            )}

            <button
              type="button"
              disabled={!isAdmin || busy || config?.mode === "DISABLED"}
              onClick={handleDisable}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-950/80 hover:bg-rose-900 border border-rose-700 disabled:opacity-40 text-rose-200 text-xs font-semibold"
              data-testid="btn-disable-pilot"
            >
              <PowerOff className="w-3.5 h-3.5" />
              Safe Disable
            </button>
          </div>
        </div>

        {!isAdmin && (
          <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-amber-300" data-testid="pilot-rbac-notice">
            <Lock className="w-4 h-4 shrink-0" />
            <span>
              {isAnalystOrAdmin
                ? "SOC Analyst mode: Pilot configuration, mode activation, pause/disable, rollback, and supervisor verification require Administrator authorization."
                : "Read-Only Viewer mode: All SOC Pilot configuration, execution, and feedback controls are locked."}
            </span>
          </div>
        )}

        {localError && (
          <div className="p-3 rounded-lg bg-red-950/50 border border-red-800/70 text-xs text-red-200 flex items-center gap-2" data-testid="pilot-error-banner">
            <ShieldAlert className="w-4 h-4 shrink-0 text-red-400" />
            <span>{localError}</span>
          </div>
        )}

        {localSuccess && (
          <div className="p-3 rounded-lg bg-emerald-950/50 border border-emerald-800/70 text-xs text-emerald-200 flex items-center gap-2" data-testid="pilot-success-banner">
            <CheckCircle className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{localSuccess}</span>
          </div>
        )}

        {metrics?.population_notice && (
          <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-400">
            <strong className="text-slate-300">Scope &amp; Token Bifurcation:</strong> {metrics.population_notice}
          </div>
        )}
      </div>

      {/* Stage 5 Metrics Grid: Operational + Reliability + Empirical Accuracy */}
      {metrics && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Operational Metrics */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h4 className="text-sm font-semibold text-white">Operational &amp; Provider Health</h4>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                metrics.operational.provider_available
                  ? "bg-emerald-950/70 text-emerald-300 border-emerald-800"
                  : "bg-red-950/70 text-red-300 border-red-800"
              }`}>
                Server 2: {metrics.operational.provider_available ? "ONLINE" : "OFFLINE"}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2.5 text-xs">
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Evaluated / Eligible</span>
                <span className="text-base font-bold text-white font-mono">
                  {metrics.operational.incidents_evaluated} / {metrics.operational.eligible_pilot_incidents}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Hourly / Daily Budget</span>
                <span className="text-base font-bold text-cyan-300 font-mono">
                  {metrics.operational.hourly_budget_used}/{metrics.operational.hourly_budget_limit} • {metrics.operational.daily_budget_used}/{metrics.operational.daily_budget_limit}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Verdict Mix (TP/FP/RA)</span>
                <span className="font-mono text-slate-200">
                  {metrics.operational.tp_recommendations} / {metrics.operational.fp_recommendations} / {metrics.operational.requires_attention}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">P50 / P95 Latency</span>
                <span className="font-mono text-slate-200">
                  {metrics.operational.p50_latency_ms != null ? `${metrics.operational.p50_latency_ms}ms` : "N/A"} /{" "}
                  {metrics.operational.p95_latency_ms != null ? `${metrics.operational.p95_latency_ms}ms` : "N/A"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Live Provider Tokens</span>
                <span className="font-mono text-emerald-300">
                  {metrics.operational.token_consumption_live.total_tokens.toLocaleString()}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Simulated Isolated Tokens</span>
                <span className="font-mono text-amber-300">
                  {metrics.operational.token_consumption_simulated_isolated.total_tokens.toLocaleString()} ({metrics.operational.simulated_evaluations_excluded_count} runs)
                </span>
              </div>
            </div>
            <div className="text-[11px] text-slate-400 flex items-center justify-between pt-1">
              <span>Queue Backlog: <strong className="font-mono text-slate-200">{metrics.operational.queue_backlog}</strong></span>
              <span>Failures: <strong className="font-mono text-rose-300">{metrics.operational.inference_failures}</strong></span>
              <span>Circuit: <strong className="font-mono text-slate-200">{metrics.operational.circuit_breaker_state}</strong></span>
            </div>
          </div>

          {/* Verdict Reliability Metrics */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h4 className="text-sm font-semibold text-white">Verdict Reliability (Pilot Cohort)</h4>
              <span className="text-[10px] font-mono text-slate-400">N={metrics.reliability.sample_size}</span>
            </div>
            <div className="grid grid-cols-2 gap-2.5 text-xs">
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Guardrail Acceptance</span>
                <span className="text-base font-bold text-emerald-300 font-mono">
                  {fmtPct(metrics.reliability.guardrail_acceptance_rate)}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Safe Abstention Rate</span>
                <span className="text-base font-bold text-amber-300 font-mono">
                  {fmtPct(metrics.reliability.abstention_rate)}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Unsupported Claims</span>
                <span className="font-mono text-slate-200">
                  {fmtPct(metrics.reliability.unsupported_claim_rate)}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Contradiction Rate</span>
                <span className="font-mono text-slate-200">
                  {fmtPct(metrics.reliability.contradiction_rate)}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Avg Completeness</span>
                <span className="font-mono text-cyan-300">
                  {fmtPct(metrics.reliability.evidence_completeness_avg)}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Analyst Disagreement</span>
                <span className="font-mono text-rose-300">
                  {fmtPct(metrics.reliability.analyst_disagreement_rate)} ({metrics.reliability.analyst_reviewed_count} reviewed)
                </span>
              </div>
            </div>
          </div>

          {/* Empirical Accuracy Metrics */}
          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3" data-testid="pilot-empirical-panel">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <h4 className="text-sm font-semibold text-white">Empirical Pilot Accuracy</h4>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                metrics.empirical_accuracy.metric_status === "CALCULATED"
                  ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                  : "bg-amber-950 text-amber-300 border-amber-800"
              }`}>
                {metrics.empirical_accuracy.metric_status}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2.5 text-xs">
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Balanced Accuracy</span>
                <span className="text-base font-bold text-white font-mono">
                  {metrics.empirical_accuracy.balanced_accuracy != null
                    ? fmtPct(metrics.empirical_accuracy.balanced_accuracy)
                    : "NOT_CALCULABLE"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">Decision Coverage</span>
                <span className="text-base font-bold text-cyan-300 font-mono">
                  {metrics.empirical_accuracy.decision_coverage != null
                    ? fmtPct(metrics.empirical_accuracy.decision_coverage)
                    : "N/A"}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">TP Precision / Recall</span>
                <span className="font-mono text-slate-200">
                  {fmtPct(metrics.empirical_accuracy.tp_precision)} / {fmtPct(metrics.empirical_accuracy.tp_recall)}
                </span>
              </div>
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                <span className="text-slate-500 block">FP Specificity / FN</span>
                <span className="font-mono text-slate-200">
                  {fmtPct(metrics.empirical_accuracy.fp_specificity)} / FN={metrics.empirical_accuracy.false_negatives}
                </span>
              </div>
            </div>
            <div className="text-[11px] text-slate-400 space-y-1">
              <div>Trust Scale: <span className="font-mono text-amber-300">{metrics.empirical_accuracy.trust_scale_label}</span></div>
              <div className="text-slate-500">{metrics.empirical_accuracy.balanced_accuracy_reason}</div>
            </div>
          </div>
        </div>
      )}

      {/* Configuration Form & Controlled Execution Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <form onSubmit={handleSaveConfig} className="lg:col-span-2 p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <h4 className="text-sm font-semibold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-indigo-400" />
              SOC Pilot Scope, Budgets &amp; Safeguards
            </h4>
            <span className="text-[11px] text-slate-500 font-mono">Versioned &amp; Auditable</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Pilot Name</label>
              <input
                type="text"
                disabled={!isAdmin}
                value={pilotName}
                onChange={(e) => setPilotName(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-white disabled:opacity-60"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Ingestion Source Scope</label>
              <select
                disabled={!isAdmin}
                value={ingestionSource}
                onChange={(e) => setIngestionSource(e.target.value as any)}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-white disabled:opacity-60"
              >
                <option value="ALL">ALL (Live + Historical)</option>
                <option value="LIVE">LIVE (No Mock Fallback)</option>
                <option value="HISTORICAL">HISTORICAL</option>
              </select>
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Selected Rule IDs (comma-separated, blank = all)</label>
              <input
                type="text"
                disabled={!isAdmin}
                placeholder="e.g. PH-Rule-001, PH-Rule-002"
                value={ruleIdsText}
                onChange={(e) => setRuleIdsText(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-white disabled:opacity-60"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Selected Archetypes (comma-separated)</label>
              <input
                type="text"
                disabled={!isAdmin}
                placeholder="e.g. BRUTE_FORCE_AUTH, PROCESS_EXECUTION"
                value={archetypesText}
                onChange={(e) => setArchetypesText(e.target.value)}
                className="w-full px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-white disabled:opacity-60"
              />
            </div>
          </div>

          <div className="text-xs space-y-1">
            <label className="text-slate-400 block">Included Severities</label>
            <div className="flex flex-wrap gap-3">
              {["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"].map((sev) => (
                <label key={sev} className="flex items-center gap-1.5 text-slate-300">
                  <input
                    type="checkbox"
                    disabled={!isAdmin}
                    checked={severities.includes(sev)}
                    onChange={() => toggleSeverity(sev)}
                    className="rounded border-slate-600 bg-slate-950 text-indigo-500"
                  />
                  {sev}
                </label>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Daily Budget</label>
              <input
                type="number"
                disabled={!isAdmin}
                value={dailyBudget}
                onChange={(e) => setDailyBudget(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Hourly Budget</label>
              <input
                type="number"
                disabled={!isAdmin}
                value={hourlyBudget}
                onChange={(e) => setHourlyBudget(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Max Concurrency</label>
              <input
                type="number"
                disabled={!isAdmin}
                value={maxConcurrency}
                onChange={(e) => setMaxConcurrency(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Timeout (s)</label>
              <input
                type="number"
                disabled={!isAdmin}
                value={timeoutSeconds}
                onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Error Handling</label>
              <select
                disabled={!isAdmin}
                value={errorPolicy}
                onChange={(e) => setErrorPolicy(e.target.value as any)}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              >
                <option value="ABSTAIN_AND_LOG">ABSTAIN_AND_LOG</option>
                <option value="PAUSE_ON_CONSECUTIVE_ERRORS">PAUSE_ON_CONSECUTIVE_ERRORS</option>
              </select>
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Auto-Pause Error Threshold</label>
              <input
                type="number"
                disabled={!isAdmin}
                value={errorThreshold}
                onChange={(e) => setErrorThreshold(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Reporting Schedule</label>
              <select
                disabled={!isAdmin}
                value={reportingSchedule}
                onChange={(e) => setReportingSchedule(e.target.value as any)}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              >
                <option value="HOURLY">HOURLY</option>
                <option value="DAILY">DAILY</option>
                <option value="MANUAL">MANUAL</option>
              </select>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 text-xs text-slate-300">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                disabled={!isAdmin}
                checked={requireApprovedPolicy}
                onChange={(e) => setRequireApprovedPolicy(e.target.checked)}
              />
              Require Approved Policy
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                disabled={!isAdmin}
                checked={requireAnalystReview}
                onChange={(e) => setRequireAnalystReview(e.target.checked)}
              />
              Require Analyst Review
            </label>
            <span className="text-emerald-400 font-mono">✓ External Writeback Blocked • ✓ Auto-Close Blocked</span>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <input
              type="text"
              disabled={!isAdmin}
              placeholder="Audit change reason..."
              value={changeReason}
              onChange={(e) => setChangeReason(e.target.value)}
              className="flex-1 px-3 py-1.5 rounded bg-slate-950 border border-slate-700 text-xs text-white"
            />
            <button
              type="submit"
              disabled={!isAdmin || busy}
              className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-semibold"
              data-testid="btn-save-pilot-config"
            >
              Save Configuration
            </button>
          </div>
        </form>

        {/* Controlled Pilot Batch Trigger */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
          <h4 className="text-sm font-semibold text-white flex items-center gap-2 border-b border-slate-800 pb-2">
            <Play className="w-4 h-4 text-emerald-400" />
            Controlled Pilot Batch Execution
          </h4>
          <p className="text-xs text-slate-400">
            Runs eligible incidents under active pilot rules &amp; budgets. Live batches strictly reject simulated fallbacks when Server 2 is offline.
          </p>
          <div className="space-y-3 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Batch Source Label</label>
              <select
                disabled={!isAnalystOrAdmin}
                value={batchSourceType}
                onChange={(e) => {
                  const v = e.target.value as "LIVE" | "HISTORICAL";
                  setBatchSourceType(v);
                  if (v === "LIVE") setBatchAllowSimulated(false);
                }}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              >
                <option value="LIVE">LIVE (Real Server 2 Required)</option>
                <option value="HISTORICAL">HISTORICAL Replay</option>
              </select>
            </div>
            <div>
              <label className="text-slate-400 block mb-1">Max Batch Incidents</label>
              <input
                type="number"
                min={1}
                max={200}
                disabled={!isAnalystOrAdmin}
                value={batchMax}
                onChange={(e) => setBatchMax(Number(e.target.value))}
                className="w-full px-2.5 py-1.5 rounded bg-slate-950 border border-slate-700 text-white"
              />
            </div>
            <label className={`flex items-center gap-2 ${batchSourceType === "LIVE" ? "opacity-50" : ""}`}>
              <input
                type="checkbox"
                disabled={!isAnalystOrAdmin || batchSourceType === "LIVE"}
                checked={batchSourceType === "HISTORICAL" && batchAllowSimulated}
                onChange={(e) => setBatchAllowSimulated(e.target.checked)}
              />
              Allow simulated fallback (HISTORICAL only)
            </label>
            <button
              type="button"
              disabled={!isAnalystOrAdmin || busy}
              onClick={handleRunBatch}
              className="w-full py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-semibold"
              data-testid="btn-run-pilot-batch"
            >
              Execute Controlled Pilot Batch
            </button>

            {batchSummary && (
              <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-[11px] font-mono space-y-1">
                <div>Status: <span className="text-cyan-300">{batchSummary.status}</span></div>
                <div>Evaluated: {batchSummary.evaluated || 0} • Abstained: {batchSummary.abstained || 0} • Failed: {batchSummary.failed || 0} • Skipped: {batchSummary.skipped || 0}</div>
                {batchSummary.reason && <div className="text-amber-300">{batchSummary.reason}</div>}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Pilot Evaluation Records & Analyst / Supervisor Governance */}
      <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <UserCheck className="w-4 h-4 text-cyan-400" />
            Pilot Evaluation Log (Shadow &amp; Analyst-Assisted Provenance)
          </h4>
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Filter Mode:</span>
            <select
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
              className="px-2.5 py-1 rounded bg-slate-950 border border-slate-700 text-white"
            >
              <option value="ALL">ALL</option>
              <option value="SHADOW">SHADOW</option>
              <option value="ANALYST_ASSISTED">ANALYST_ASSISTED</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2 pr-3">Incident</th>
                <th className="py-2 pr-3">Mode / Source</th>
                <th className="py-2 pr-3">Proposed → Validated</th>
                <th className="py-2 pr-3">Trust Score</th>
                <th className="py-2 pr-3">Model / Policy</th>
                <th className="py-2 pr-3">Human Review</th>
                <th className="py-2">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {evaluations.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500">
                    No pilot evaluation records recorded yet. Activate SHADOW or ANALYST_ASSISTED mode and run eligible incidents.
                  </td>
                </tr>
              ) : (
                evaluations.map((ev) => (
                  <React.Fragment key={ev.id}>
                    <tr className="hover:bg-slate-950/60">
                      <td className="py-2.5 pr-3 font-mono text-slate-200">
                        <div>{ev.incident_id}</div>
                        <div className="text-[10px] text-slate-500">{ev.rule_id} • {ev.severity}</div>
                      </td>
                      <td className="py-2.5 pr-3">
                        <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-700 font-mono text-[10px]">
                          {ev.execution_mode}
                        </span>
                        <div className="text-[10px] mt-1">
                          <span className={ev.is_simulated ? "text-amber-300" : "text-emerald-300"}>
                            {ev.source_type} • {ev.is_simulated ? "SIMULATED" : "LIVE_PROVIDER"}
                          </span>
                        </div>
                      </td>
                      <td className="py-2.5 pr-3 font-mono">
                        <div className="text-slate-300">
                          {ev.proposed_verdict || "NONE"} →{" "}
                          <strong className="text-white">{ev.validated_verdict || "ERROR"}</strong>
                        </div>
                        <div className="text-[10px] text-slate-500">{ev.validation_status}</div>
                      </td>
                      <td className="py-2.5 pr-3 font-mono">
                        {ev.trust_score != null ? (
                          <div>
                            <span className={ev.is_calibrated ? "text-emerald-300" : "text-amber-300"}>
                              {ev.trust_score}/10 ({ev.is_calibrated ? "Calibrated" : "Uncalibrated"})
                            </span>
                            {ev.historical_trust_score != null && ev.historical_trust_score !== ev.trust_score && (
                              <div className="text-[10px] text-slate-500">
                                Historical: {ev.historical_trust_score}/10
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-slate-500">NOT_SCORABLE</span>
                        )}
                      </td>
                      <td className="py-2.5 pr-3 text-[11px] font-mono text-slate-400">
                        <div>{ev.model_identifier}</div>
                        <div>{ev.policy_version_number ? `Policy v${ev.policy_version_number}` : "No policy"}</div>
                      </td>
                      <td className="py-2.5 pr-3 text-[11px]">
                        {ev.analyst_feedback_action ? (
                          <div>
                            <span className="text-cyan-300 font-semibold">{ev.analyst_feedback_action}</span> →{" "}
                            <span className="text-white">{ev.analyst_decision}</span>
                            <div className="text-[10px] text-slate-400">
                              By {ev.analyst_user} • {ev.supervisor_verified ? `✓ Supervisor (${ev.supervisor_user})` : "Awaiting Supervisor"}
                            </div>
                          </div>
                        ) : (
                          <span className="text-slate-500">Unreviewed</span>
                        )}
                      </td>
                      <td className="py-2.5 space-x-1 whitespace-nowrap">
                        {isAnalystOrAdmin && (
                          <button
                            type="button"
                            onClick={() => {
                              setActiveFeedbackId(activeFeedbackId === ev.id ? null : ev.id);
                              setFeedbackDecision((ev.validated_verdict as any) || "TRUE_POSITIVE");
                            }}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px]"
                          >
                            Review
                          </button>
                        )}
                        {isAdmin && ev.analyst_feedback_action && !ev.supervisor_verified && (
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => handleSupervisorVerify(ev.id)}
                            className="px-2 py-1 rounded bg-emerald-800/80 hover:bg-emerald-700 text-emerald-100 text-[11px]"
                          >
                            Supervisor Verify
                          </button>
                        )}
                      </td>
                    </tr>
                    {activeFeedbackId === ev.id && (
                      <tr>
                        <td colSpan={7} className="p-3 bg-slate-950/90 border-b border-slate-800">
                          <div className="flex flex-col sm:flex-row gap-2 items-center text-xs">
                            <select
                              value={feedbackAction}
                              onChange={(e) => setFeedbackAction(e.target.value as any)}
                              className="px-2 py-1 rounded bg-slate-900 border border-slate-700 text-white"
                            >
                              <option value="ACCEPTED">ACCEPTED</option>
                              <option value="OVERRIDDEN">OVERRIDDEN</option>
                              <option value="DISPUTED">DISPUTED</option>
                              <option value="REQUESTED_EVIDENCE">REQUESTED_EVIDENCE</option>
                            </select>
                            <select
                              value={feedbackDecision}
                              onChange={(e) => setFeedbackDecision(e.target.value as any)}
                              className="px-2 py-1 rounded bg-slate-900 border border-slate-700 text-white"
                            >
                              <option value="TRUE_POSITIVE">TRUE_POSITIVE</option>
                              <option value="FALSE_POSITIVE">FALSE_POSITIVE</option>
                              <option value="REQUIRES_ATTENTION">REQUIRES_ATTENTION</option>
                            </select>
                            <input
                              type="text"
                              placeholder="Analyst rationale (stored separately from AI verdict)..."
                              value={feedbackReason}
                              onChange={(e) => setFeedbackReason(e.target.value)}
                              className="flex-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-white"
                            />
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => handleSubmitFeedback(ev.id)}
                              className="px-3 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-semibold"
                            >
                              Submit Feedback
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Config Version History & Audit Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <RotateCcw className="w-4 h-4 text-amber-400" />
            Pilot Configuration History &amp; Safe Rollback
          </h4>
          <div className="space-y-2 max-h-72 overflow-y-auto text-xs">
            {history.length === 0 ? (
              <div className="text-slate-500 py-4 text-center">No version transitions yet.</div>
            ) : (
              history.map((h) => (
                <div key={h.id} className="p-2.5 rounded bg-slate-950 border border-slate-800 flex items-center justify-between gap-2">
                  <div>
                    <div className="font-mono text-slate-200">
                      v{h.version_number} • <span className="text-indigo-300">{h.action}</span> → {h.mode} {h.is_paused ? "(PAUSED)" : ""}
                    </div>
                    <div className="text-[11px] text-slate-400">{h.change_reason} • by {h.changed_by}</div>
                  </div>
                  {isAdmin && h.version_number !== config?.version_number && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleRollback(h.version_number)}
                      className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-amber-300 text-[11px]"
                    >
                      Rollback
                    </button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <h4 className="text-sm font-semibold text-white flex items-center gap-2">
            <FileText className="w-4 h-4 text-cyan-400" />
            Pilot Governance Audit Trail
          </h4>
          <div className="space-y-2 max-h-72 overflow-y-auto text-xs">
            {auditItems.length === 0 ? (
              <div className="text-slate-500 py-4 text-center">No pilot audit entries yet.</div>
            ) : (
              auditItems.map((log) => (
                <div key={log.id} className="p-2.5 rounded bg-slate-950 border border-slate-800 font-mono text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-cyan-300 font-bold">{log.action}</span>
                    <span className="text-slate-500">{log.username || "system"}</span>
                  </div>
                  <div className="text-slate-400 truncate mt-0.5">{JSON.stringify(log.details)}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
