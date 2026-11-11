"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Eye,
  EyeOff,
  Copy,
  Check,
  FileCode,
  Layers,
  Clock,
  ShieldCheck,
  ShieldAlert,
  Server,
  Network,
  Tag,
  Cpu,
  FileCheck2,
  Sparkles,
  Loader2,
  Bot,
  CheckCircle2,
  AlertCircle,
  Database,
  RefreshCw,
  Scale,
  FileSearch,
} from "lucide-react";
import { api, IncidentDetail, IncidentAiVerdictResponse } from "@/lib/api";
import { useApp } from "@/context/AppContext";
import { HistoricalTelemetryTimeline } from "@/components/telemetry/HistoricalTelemetryTimeline";
import { formatExecutionProvenanceBadge } from "@/lib/provenance";
import { VerdictumLogo } from "@/components/brand/VerdictumLogo";

export default function AITriageWorkbenchDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const incidentId = resolvedParams.id;
  const { blindReviewMode, setBlindReviewMode } = useApp();

  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [modelPayload, setModelPayload] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<
    "overview" | "events" | "rule" | "ground_truth" | "raw_json" | "model_payload" | "timeline" | "canonical_evidence"
  >("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [aiVerdict, setAiVerdict] = useState<IncidentAiVerdictResponse | null>(null);
  const [verdictError, setVerdictError] = useState<string | null>(null);
  const [syncingResolution, setSyncingResolution] = useState(false);
  const [syncSuccessMessage, setSyncSuccessMessage] = useState<string | null>(null);
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

  const handleSyncResolution = async () => {
    if (!incident) return;
    setSyncingResolution(true);
    setSyncSuccessMessage(null);
    try {
      const res = await api.syncFortiSiemIncidentResolution(incident.incident_id);
      const refreshed = await api.getIncidentDetail(incidentId, blindReviewMode);
      setIncident(refreshed);
      setSyncSuccessMessage(
        res.resolution
          ? `Resolution pulled: ${res.resolution}${res.cleared_user ? ` by ${res.cleared_user}` : ""}`
          : "Synchronized with FortiSIEM (Incident remains Open)."
      );
      setTimeout(() => setSyncSuccessMessage(null), 5000);
    } catch (err: any) {
      setError(err.message || "Failed to sync resolution from FortiSIEM");
    } finally {
      setSyncingResolution(false);
    }
  };

  const handleRequestAiVerdict = async () => {
    setAnalyzing(true);
    setVerdictError(null);
    try {
      const verdict = await api.getIncidentAiVerdict(incidentId);
      setAiVerdict(verdict);
    } catch (err: any) {
      setVerdictError(err.message || "Failed to generate AI verdict from Local LLM.");
    } finally {
      setAnalyzing(false);
    }
  };

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getIncidentDetail(incidentId, blindReviewMode);
        setIncident(data);
        if (data.ai_verdict) {
          setAiVerdict(data.ai_verdict);
        }

        // Also fetch model payload to demonstrate allowlist compliance
        try {
          const mp = await api.getIncidentModelPayload(incidentId);
          setModelPayload(mp);
        } catch {
          // ignore if model payload fails
        }
      } catch (err: any) {
        setError(err.message || "Failed to load incident detail");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [incidentId, blindReviewMode]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatEpoch = (epoch?: number, fallbackIso?: string) => {
    if (!epoch) {
      if (fallbackIso) {
        try {
          return new Date(fallbackIso).toLocaleString([], {
            dateStyle: "short",
            timeStyle: "medium",
          });
        } catch {
          return "N/A";
        }
      }
      return "N/A";
    }
    const ms = epoch < 1e11 ? epoch * 1000 : epoch;
    return new Date(ms).toLocaleString([], {
      dateStyle: "short",
      timeStyle: "medium",
    });
  };

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center text-slate-400 text-xs">
        Loading incident {incidentId}...
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="space-y-4">
        <Link href="/ai-triage-workbench" className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:underline">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to AI Triage Workbench
        </Link>
        <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-6 text-rose-300 text-xs">
          {error || "Incident not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3.5">
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <Link
            href="/ai-triage-workbench"
            className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
          </Link>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[11px] text-slate-400">Incident</span>
              <span className="font-mono font-bold text-slate-100 text-xs sm:text-sm">{incident.incident_id}</span>
              <span className="rounded bg-slate-800 border border-slate-700 px-1.5 py-0.2 text-[9px] font-bold text-slate-200">
                {incident.severity}
              </span>
              <span
                className={`rounded px-1.5 py-0.2 text-[9px] font-mono border ${
                  incident.status_code === 2
                    ? "bg-slate-900 text-slate-400 border-slate-800"
                    : "bg-cyan-950 text-cyan-300 border-cyan-800"
                }`}
              >
                {incident.status_name}
              </span>
            </div>
            <h1 className="text-sm sm:text-base font-bold text-slate-100 mt-0.5">{incident.title}</h1>
          </div>
        </div>

        {/* Header Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleRequestAiVerdict}
            disabled={analyzing}
            className="flex items-center gap-1.5 rounded-md border border-emerald-700/80 bg-emerald-950/80 hover:bg-emerald-900 px-2.5 py-1 text-xs font-semibold text-emerald-300 shadow-sm transition-all disabled:opacity-50"
            title="Invoke Verdict Triage Agent for instant AI security verdict"
          >
            {analyzing ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin text-emerald-400" />
                <span>Analyzing Incident...</span>
              </>
            ) : (
              <>
                {aiVerdict ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Re-evaluate Agent Verdict</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Verdict Triage Agent</span>
                  </>
                )}
              </>
            )}
          </button>

          <button
            onClick={() => setBlindReviewMode(!blindReviewMode)}
            className={`flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold transition-all ${
              blindReviewMode
                ? "border-amber-500/80 bg-amber-950/80 text-amber-300 shadow-sm"
                : "border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            {blindReviewMode ? (
              <>
                <EyeOff className="h-3.5 w-3.5 text-amber-400" />
                <span>Blind Review: ON</span>
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

      {blindReviewMode && (
        <div className="rounded-lg border border-amber-800/80 bg-amber-950/40 p-2.5 text-xs text-amber-300 flex items-center gap-2.5">
          <EyeOff className="h-3.5 w-3.5 shrink-0 text-amber-400" />
          <div className="text-[11px] leading-tight">
            <strong className="font-semibold text-amber-200">Blind Review Active:</strong> Historical ground truth tab and resolution verdicts are masked from view for this incident.
          </div>
        </div>
      )}

      {/* AI Verdict Result Box */}
      {verdictError && (
        <div className="rounded-lg border border-rose-800/80 bg-rose-950/40 p-3 text-xs text-rose-300 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 text-rose-400" />
            <span>{verdictError}</span>
          </div>
          <button onClick={() => setVerdictError(null)} className="text-xs hover:underline">
            Dismiss
          </button>
        </div>
      )}

      {aiVerdict && (
        <div className="relative overflow-hidden rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3.5 shadow-lg">
          <div aria-hidden="true" className="pointer-events-none absolute right-3 top-2 opacity-[0.07]">
            <VerdictumLogo size={64} showWordmark={false} />
          </div>
          {/* Header Row */}
          <div className="relative flex flex-wrap items-center justify-between border-b border-slate-800 pb-2.5 gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <VerdictumLogo size={20} showWordmark={false} />
              <span className="flex items-center gap-1.5 text-xs font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800 px-2 py-0.5 rounded">
                <Sparkles className="h-3.5 w-3.5" />
                Verdict Triage Agent
              </span>
              <span className="text-xs font-mono text-slate-400">
                Engine: {aiVerdict.model_identifier}
              </span>
              {aiVerdict.evaluated_at && (
                <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 px-1.5 py-0.5 rounded flex items-center gap-1" title={`Evaluated at ${aiVerdict.evaluated_at}`}>
                  <Database className="h-2.5 w-2.5" />
                  Stored Verdict
                </span>
              )}
              {aiVerdict.contract_id && (
                <span className="text-[10px] font-mono text-purple-300 bg-purple-950/60 border border-purple-800/60 px-1.5 py-0.5 rounded flex items-center gap-1" title={`Contract: ${aiVerdict.contract_id} v${aiVerdict.contract_version || 1}`}>
                  <Scale className="h-2.5 w-2.5 text-purple-400" />
                  Contract: {aiVerdict.contract_id} (v{aiVerdict.contract_version || 1})
                </span>
              )}
              {aiVerdict.compiler_version && (
                <span className="text-[10px] font-mono text-emerald-300 bg-emerald-950/60 border border-emerald-800/60 px-1.5 py-0.5 rounded flex items-center gap-1" title={`Compiled Policy Digest: ${aiVerdict.compilation_digest || 'N/A'}`}>
                  <FileCode className="h-2.5 w-2.5 text-emerald-400" />
                  Compiler: {aiVerdict.compiler_version} ({aiVerdict.policy_sections_count || 9}/9 secs)
                </span>
              )}
              <span className="text-[10px] font-mono text-amber-300 bg-amber-950/60 border border-amber-800/60 px-1.5 py-0.5 rounded flex items-center gap-1" title="Honest calibration status: Withheld until >= 30 verified ground truth cases">
                <ShieldCheck className="h-2.5 w-2.5 text-amber-400" />
                Calibration: {aiVerdict.calibration_status || "NOT_CALIBRATED"}
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-slate-400">
              <span className="flex items-center gap-1 text-slate-300" title="Inference Execution Time">
                <Clock className="h-3 w-3 text-cyan-400" />
                Time: <strong className="text-slate-100">{aiVerdict.latency_ms} ms</strong>
                <span className="text-[10px] text-slate-500">({(aiVerdict.latency_ms / 1000).toFixed(2)}s)</span>
              </span>

              <span className="flex items-center gap-1 text-slate-300" title="Tokens Consumed">
                <Cpu className="h-3 w-3 text-purple-400" />
                Tokens: <strong className="text-purple-300">{aiVerdict.total_tokens || 0}</strong>
                <span className="text-[10px] text-slate-500">({aiVerdict.prompt_tokens || 0} in / {aiVerdict.completion_tokens || 0} out)</span>
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
                    : `• Provenance: ${pb.label} (${aiVerdict.model_identifier || "Model"}) • S2 Now: ${llmOnline ? "ONLINE" : "OFFLINE"}`;
                return (
                  <span
                    className={`px-1.5 py-0.5 rounded border font-semibold ${pb.className}`}
                    title={pb.sublabel}
                  >
                    {text}
                  </span>
                );
              })()}
              <button
                onClick={() => setAiVerdict(null)}
                className="text-slate-400 hover:text-slate-200 text-xs px-1"
                title="Hide banner"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Overrule Alert Banner (when LLM proposed TP/FP but validator overrode to REQUIRES_ATTENTION) */}
          {aiVerdict.proposed_verdict && aiVerdict.proposed_verdict !== aiVerdict.verdict && (
            <div className="rounded-lg border border-amber-500/80 bg-amber-950/40 p-3 text-xs text-amber-200 flex items-start gap-2.5">
              <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-1">
                <div className="font-semibold text-amber-300 flex items-center gap-2">
                  <span>Deterministic Safety Override Applied</span>
                  <span className="text-[10px] font-mono bg-amber-900/60 border border-amber-700 px-1.5 py-0.2 rounded text-amber-200">
                    Proposed: {aiVerdict.proposed_verdict} → Final: {aiVerdict.verdict}
                  </span>
                </div>
                <p className="text-[11px] text-amber-300/90 leading-relaxed">
                  The model proposed a decisive <strong>{aiVerdict.proposed_verdict}</strong>, but independent verification rejected it due to incomplete telemetry, ungrounded claims, or unapproved policy contracts.
                </p>
              </div>
            </div>
          )}

          {/* Authoritative Verdict Card */}
          <div
            className={`rounded-lg border p-3 flex flex-wrap items-center justify-between gap-3 ${
              aiVerdict.verdict === "TRUE_POSITIVE"
                ? "bg-rose-950/50 border-rose-800 text-rose-200"
                : aiVerdict.verdict === "FALSE_POSITIVE"
                ? "bg-emerald-950/50 border-emerald-800 text-emerald-200"
                : "bg-amber-950/50 border-amber-800 text-amber-200"
            }`}
          >
            <div className="flex items-center gap-2.5">
              {aiVerdict.verdict === "TRUE_POSITIVE" ? (
                <AlertTriangle className="h-6 w-6 text-rose-400 shrink-0" />
              ) : aiVerdict.verdict === "FALSE_POSITIVE" ? (
                <CheckCircle2 className="h-6 w-6 text-emerald-400 shrink-0" />
              ) : (
                <AlertCircle className="h-6 w-6 text-amber-400 shrink-0" />
              )}
              <div>
                <div className="text-[10px] uppercase font-mono tracking-wider opacity-80 flex items-center gap-1.5">
                  Authoritative Platform Verdict
                  {aiVerdict.is_decisive_accepted ? (
                    <span className="text-[9px] bg-emerald-900/80 border border-emerald-600 px-1 py-0.2 rounded text-emerald-300 font-bold">
                      VERIFIED ACCEPTED
                    </span>
                  ) : (
                    <span className="text-[9px] bg-amber-900/80 border border-amber-600 px-1 py-0.2 rounded text-amber-300 font-bold">
                      ABSTAINED / FORCED ATTENTION
                    </span>
                  )}
                </div>
                <div className="text-base font-extrabold tracking-tight">
                  {aiVerdict.verdict.replace(/_/g, " ")}
                </div>
              </div>
            </div>

            <div className="flex items-center gap-6">
              {aiVerdict.raw_model_confidence !== undefined && aiVerdict.raw_model_confidence !== aiVerdict.confidence && (
                <div className="text-right border-r border-slate-700/60 pr-5">
                  <div className="text-[10px] uppercase font-mono tracking-wider text-slate-400" title="Raw uncalibrated score generated by LLM prior to validation">
                    Raw LLM Score
                  </div>
                  <div className="text-xs font-mono text-slate-300">
                    {Math.round(aiVerdict.raw_model_confidence)}% <span className="text-[9px] text-slate-500">(Uncalibrated)</span>
                  </div>
                </div>
              )}
              <div className="text-right">
                <div className="text-[10px] uppercase font-mono tracking-wider opacity-80" title="Effective confidence after independent deterministic evidence verification">
                  Effective Confidence
                </div>
                <div className="text-lg font-extrabold font-mono">
                  {Math.round(aiVerdict.confidence)}%
                </div>
              </div>
            </div>
          </div>

          {/* Phase 2 Evidence Grounding & Verification Metrics Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
            {/* Metric 1: Completeness */}
            <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
              <span className="text-[9px] text-slate-400 block uppercase">Evidence Completeness</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className={`text-sm font-bold ${
                  (aiVerdict.evidence_completeness ?? 0) >= 0.8
                    ? "text-emerald-400"
                    : (aiVerdict.evidence_completeness ?? 0) >= 0.4
                    ? "text-amber-400"
                    : "text-rose-400"
                }`}>
                  {Math.round((aiVerdict.evidence_completeness ?? 0) * 100)}%
                </span>
                <span className="text-[10px] text-slate-500">
                  ({aiVerdict.canonical_evidence_count ?? 0} canonical recs)
                </span>
              </div>
            </div>

            {/* Metric 2: Claim Grounding */}
            <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
              <span className="text-[9px] text-slate-400 block uppercase">Claim Grounding Ratio</span>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                {(aiVerdict.total_claims_count ?? 0) === 0 ? (
                  <>
                    <span className={`text-sm font-bold ${aiVerdict.verdict === "REQUIRES_ATTENTION" ? "text-amber-400" : "text-rose-400"}`}>
                      N/A
                    </span>
                    <span className="text-[10px] text-slate-400">
                      (0/0 claims — unclaimed)
                    </span>
                  </>
                ) : (
                  <>
                    <span className={`text-sm font-bold ${
                      (aiVerdict.grounding_ratio ?? 0) >= 0.99
                        ? "text-emerald-400"
                        : "text-rose-400"
                    }`}>
                      {Math.round((aiVerdict.grounding_ratio ?? 0) * 100)}%
                    </span>
                    <span className="text-[10px] text-slate-500">
                      ({aiVerdict.grounded_claims_count ?? 0}/{aiVerdict.total_claims_count ?? 0} grounded)
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Metric 3: Validation Status */}
            <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
              <span className="text-[9px] text-slate-400 block uppercase">Validation Status</span>
              <div className="mt-0.5 flex flex-wrap items-center gap-1.5">
                <span className={`text-xs font-bold px-1.5 py-0.5 rounded border inline-block ${
                  aiVerdict.validation_status === "VALIDATED"
                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                    : aiVerdict.validation_status === "INSUFFICIENT_EVIDENCE"
                    ? "bg-amber-950 text-amber-300 border-amber-800"
                    : "bg-rose-950 text-rose-300 border-rose-800"
                }`}>
                  {aiVerdict.validation_status || "UNVERIFIED"}
                </span>
                {aiVerdict.trust_score !== undefined && aiVerdict.trust_score !== null && (() => {
                  const isCalibrated = Boolean(aiVerdict.is_calibrated);
                  const rawScore = Number(aiVerdict.trust_score);
                  const capApplied = Boolean((aiVerdict as { trust_cap_applied?: boolean }).trust_cap_applied) || (!isCalibrated && rawScore > 6);
                  const effectiveScore = isCalibrated ? rawScore : Math.min(6, rawScore);
                  const historicalScore = (aiVerdict as { historical_trust_score?: number | null }).historical_trust_score ?? (capApplied ? rawScore : null);
                  return (
                    <span className="inline-flex items-center gap-1.5 flex-wrap">
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                        effectiveScore >= 7
                          ? "bg-emerald-950/60 text-emerald-300 border-emerald-800/70"
                          : effectiveScore >= 4
                          ? "bg-amber-950/60 text-amber-300 border-amber-800/70"
                          : "bg-rose-950/60 text-rose-300 border-rose-800/70"
                      }`}>
                        Trust: {effectiveScore}/10 ({isCalibrated ? "Calibrated" : capApplied ? "Uncalibrated Cap" : "Uncalibrated Ordinal"})
                      </span>
                      {historicalScore !== null && historicalScore !== undefined && historicalScore !== effectiveScore && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border bg-slate-900 text-slate-400 border-slate-700" title="Preserved legacy stored score prior to uncalibrated <= 6/10 cap">
                          Historical stored: {historicalScore}/10 (pre-cap)
                        </span>
                      )}
                    </span>
                  );
                })()}
              </div>
              {aiVerdict.final_disposition && (
                <span className="text-[9px] text-slate-400 font-mono block mt-1 truncate" title={aiVerdict.final_disposition}>
                  Disposition: {aiVerdict.final_disposition}
                </span>
              )}
            </div>

            {/* Metric 4: Replay Audit */}
            <div className="p-2 rounded-lg bg-slate-900/80 border border-slate-800">
              <span className="text-[9px] text-slate-400 block uppercase">Replay Signature</span>
              <div className="flex items-center justify-between mt-0.5">
                <span className="text-xs text-cyan-300 font-mono truncate" title={aiVerdict.replay_signature}>
                  {aiVerdict.replay_signature ? `${aiVerdict.replay_signature.substring(0, 10)}...` : "N/A"}
                </span>
                {aiVerdict.replay_signature && (
                  <button
                    onClick={() => copyToClipboard(aiVerdict.replay_signature || "")}
                    className="text-[9px] text-slate-400 hover:text-white"
                    title="Copy full cryptographic signature"
                  >
                    Copy
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Analyst Action Directive */}
          {aiVerdict.analyst_action_directive && (
            <div className="rounded-lg border border-cyan-800/60 bg-cyan-950/30 p-2.5 text-xs text-cyan-200 flex items-start gap-2">
              <FileCheck2 className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
              <div>
                <strong className="text-cyan-300 font-semibold block text-[11px] uppercase tracking-wider">
                  Analyst Action Directive:
                </strong>
                <p className="text-xs text-slate-200 font-sans mt-0.5 leading-relaxed">
                  {aiVerdict.analyst_action_directive}
                </p>
              </div>
            </div>
          )}

          {/* Reason & Analytical Justification */}
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
              <Bot className="h-3 w-3 text-cyan-400" />
              Analytical Justification & Deterministic Evaluation
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-sans">
              {aiVerdict.reason}
            </p>
          </div>

          {/* Validation Reason Codes */}
          {aiVerdict.validation_reason_codes && aiVerdict.validation_reason_codes.length > 0 && (
            <div className="space-y-1">
              <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                Validation Assessment Codes ({aiVerdict.validation_reason_codes.length}):
              </div>
              <div className="flex flex-wrap gap-1.5">
                {aiVerdict.validation_reason_codes.map((code, idx) => (
                  <span
                    key={idx}
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                      code.includes("PASSED")
                        ? "bg-emerald-950/70 text-emerald-300 border-emerald-800"
                        : code.includes("CLAIM_UNGROUNDED") || code.includes("CONTRADICTION")
                        ? "bg-rose-950/80 text-rose-300 border-rose-800"
                        : "bg-amber-950/70 text-amber-300 border-amber-800"
                    }`}
                  >
                    {code}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Unsupported Claims Alert (if any hallucinated claims detected) */}
          {aiVerdict.unsupported_claims && aiVerdict.unsupported_claims.length > 0 && (
            <div className="rounded-lg border border-rose-800/80 bg-rose-950/40 p-3 space-y-2 text-xs">
              <div className="flex items-center gap-2 text-rose-300 font-semibold">
                <AlertTriangle className="h-4 w-4 text-rose-400" />
                <span>Unsupported / Fabricated Claims Detected ({aiVerdict.unsupported_claims.length})</span>
              </div>
              <p className="text-[11px] text-rose-200/90 leading-relaxed">
                The model cited facts not present in verified incident telemetry. Independent verification flagged and neutralized these claims:
              </p>
              <div className="space-y-1 font-mono text-[11px]">
                {aiVerdict.unsupported_claims.map((claim, idx) => (
                  <div key={idx} className="p-1.5 rounded bg-rose-950 border border-rose-800/60 flex items-center justify-between">
                    <div>
                      <span className="text-rose-400 font-bold">{claim.claim_type}: </span>
                      <span className="text-slate-200">{String(claim.asserted_value)} </span>
                      <span className="text-slate-500">({claim.field})</span>
                    </div>
                    <span className="text-[9px] bg-rose-900 text-rose-200 px-1 py-0.2 rounded uppercase">
                      {claim.grounding_status || "UNGROUNDED"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Missing Required Telemetry */}
          {aiVerdict.missing_evidence && aiVerdict.missing_evidence.length > 0 && (
            <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-3 space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-amber-400 tracking-wider flex items-center gap-1.5">
                <AlertCircle className="h-3 w-3" />
                Missing Required Evidence Telemetry ({aiVerdict.missing_evidence.length})
              </div>
              <ul className="text-xs space-y-1 text-slate-300 list-disc list-inside font-mono">
                {aiVerdict.missing_evidence.map((item, idx) => (
                  <li key={idx} className="text-[11px] text-amber-200/90 leading-tight">
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Supporting Evidence Attributes */}
          {aiVerdict.supporting_evidence && aiVerdict.supporting_evidence.length > 0 && (
            <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-3 space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                Supporting Evidence Attributes ({aiVerdict.supporting_evidence.length})
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

          {/* Phase 3 Verified Historical Precedents (Semantic RAG) */}
          {aiVerdict.retrieved_precedents && aiVerdict.retrieved_precedents.length > 0 && (
            <div className="rounded-lg border border-indigo-900/60 bg-indigo-950/20 p-3 space-y-2 text-xs">
              <div className="flex items-center justify-between text-indigo-300 font-semibold">
                <div className="flex items-center gap-2">
                  <Database className="h-4 w-4 text-indigo-400" />
                  <span>Verified Historical Precedents ({aiVerdict.retrieved_precedents.length})</span>
                </div>
                <span className="text-[10px] font-mono text-indigo-400/80">
                  Tenant-Isolated & Exact-Rule Scoped
                </span>
              </div>
              <div className="space-y-2">
                {aiVerdict.retrieved_precedents.map((prec, idx) => (
                  <div key={idx} className="p-2.5 rounded bg-slate-900/90 border border-indigo-900/40 text-[11px] font-mono space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-indigo-300 font-bold">{prec.incident_title || prec.incident_id}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-slate-400">Similarity: {(prec.similarity_score * 100).toFixed(0)}%</span>
                        <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                          prec.verified_verdict === "TRUE_POSITIVE"
                            ? "bg-rose-950 text-rose-300 border border-rose-800"
                            : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                        }`}>
                          {prec.verified_verdict}
                        </span>
                      </div>
                    </div>
                    <p className="text-slate-300 font-sans text-xs">
                      {prec.analyst_explanation}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tabs Header */}
      <div className="flex border-b border-slate-800 space-x-1 overflow-x-auto text-xs font-medium">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "overview"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Incident Overview
        </button>

        <button
          onClick={() => setActiveTab("events")}
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "events"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Raw Events
          <span className="rounded bg-slate-800 px-1 py-0.2 text-[9px] font-mono text-slate-300">
            {incident.events.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("rule")}
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "rule"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Detection Intelligence Context
        </button>

        <button
          onClick={() => setActiveTab("ground_truth")}
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "ground_truth"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Historical Ground Truth
          {blindReviewMode && <EyeOff className="h-3 w-3 text-amber-400" />}
        </button>

        <button
          onClick={() => setActiveTab("raw_json")}
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "raw_json"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Raw Payload JSON
        </button>

        <button
          onClick={() => setActiveTab("model_payload")}
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "model_payload"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="h-3 w-3 text-cyan-400" />
          Evidence Integrity Guardrail
        </button>

        <button
          onClick={() => setActiveTab("timeline")}
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "timeline"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Clock className="h-3 w-3 text-cyan-400" />
          Historical Telemetry Timeline
        </button>

        <button
          onClick={() => setActiveTab("canonical_evidence")}
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "canonical_evidence"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Scale className="h-3 w-3 text-cyan-400" />
          Canonical Evidence
          {modelPayload?.canonical_evidence && (
            <span className="rounded bg-slate-800 px-1 py-0.2 text-[9px] font-mono text-cyan-300">
              {modelPayload.canonical_evidence.length}
            </span>
          )}
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
          <div className="lg:col-span-2 space-y-3">
            {/* Description & Detail */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2.5">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Investigation Description & Details
              </h2>
              <div className="space-y-2 text-xs leading-relaxed text-slate-300">
                <div>
                  <span className="text-[10px] font-mono text-slate-500 block mb-0.5">Description:</span>
                  <div className="p-2.5 rounded-md bg-slate-900 border border-slate-800 font-mono text-xs">
                    {incident.description || "No description provided by SIEM."}
                  </div>
                </div>
                {incident.detail && (
                  <div>
                    <span className="text-[10px] font-mono text-slate-500 block mb-0.5">Detail Telemetry:</span>
                    <pre className="p-2.5 rounded-md bg-slate-900 border border-slate-800 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap max-h-56">
                      {incident.detail}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            {/* Network & Device Evidence */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2.5">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Network & Reporting Entities
              </h2>
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="p-2.5 rounded-md bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 text-[9px] block">Source IP:</span>
                  <span className="text-slate-200 font-bold">{incident.source_ip || "Internal / Host"}</span>
                </div>
                <div className="p-2.5 rounded-md bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 text-[9px] block">Reporting IP:</span>
                  <span className="text-slate-200">{incident.reporting_ip || "N/A"}</span>
                </div>
                <div className="p-2.5 rounded-md bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 text-[9px] block">Reporting Device:</span>
                  <span className="text-slate-200 truncate block">{incident.reporting_device || "N/A"}</span>
                </div>
                <div className="p-2.5 rounded-md bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 text-[9px] block">Category / Subcategory:</span>
                  <span className="text-slate-200 truncate block">
                    {incident.category || "General"} {incident.subcategory ? `· ${incident.subcategory}` : ""}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Summary Column */}
          <div className="space-y-3">
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2.5 text-xs">
              <h2 className="font-bold uppercase tracking-wider text-slate-300 text-xs">Metadata Summary</h2>
              <div className="space-y-1.5 font-mono text-[11px]">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">SIEM Event Type:</span>
                  <span className="text-slate-200 truncate max-w-[150px]">{incident.event_type}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Rule Name:</span>
                  <span className="text-slate-200 truncate max-w-[150px]">{incident.rule_name || "Unmapped"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">First Seen:</span>
                  <span className="text-slate-200">{formatEpoch(incident.first_seen_epoch)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Last Seen:</span>
                  <span className="text-slate-200">{formatEpoch(incident.last_seen_epoch)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Created At:</span>
                  <span className="text-slate-200">{formatEpoch(incident.created_at_epoch, incident.created_at)}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Customer:</span>
                  <span className="text-slate-200">{incident.customer || "Enterprise Default"}</span>
                </div>
              </div>

              {incident.rule_id && (
                <div className="pt-1">
                  <Link
                    href={`/detection-intelligence/${incident.rule_id}`}
                    className="block w-full text-center rounded-md bg-slate-900 border border-slate-800 py-1.5 text-xs font-semibold text-cyan-400 hover:bg-slate-800 transition-colors"
                  >
                    View Detection Intelligence Rule →
                  </Link>
                </div>
              )}
            </div>

            {/* FortiSIEM Resolution & Ground Truth Card */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2.5 text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-1.5 font-bold uppercase tracking-wider text-slate-300 text-xs">
                  <ShieldCheck className="h-3.5 w-3.5 text-cyan-400" />
                  <span>SIEM Resolution & Ground Truth</span>
                </div>
                <button
                  onClick={handleSyncResolution}
                  disabled={syncingResolution}
                  className="inline-flex items-center gap-1 rounded bg-slate-900 border border-cyan-800/60 px-2 py-0.5 text-[10px] font-semibold text-cyan-300 hover:bg-slate-800 disabled:opacity-50 transition-colors"
                  title="Pull latest closure status, resolution, and cleared reason from FortiSIEM"
                >
                  <RefreshCw className={`h-2.5 w-2.5 ${syncingResolution ? "animate-spin text-cyan-400" : ""}`} />
                  <span>{syncingResolution ? "Syncing..." : "Sync SIEM"}</span>
                </button>
              </div>

              {syncSuccessMessage && (
                <div className="rounded bg-emerald-950/70 border border-emerald-800 p-2 text-[11px] text-emerald-300 flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                  <span>{syncSuccessMessage}</span>
                </div>
              )}

              {blindReviewMode ? (
                <div className="rounded bg-amber-950/30 border border-amber-900/60 p-2.5 text-[11px] text-amber-300 flex items-center gap-2">
                  <EyeOff className="h-3.5 w-3.5 text-amber-400 shrink-0" />
                  <span>Resolution details hidden in Blind Review mode.</span>
                </div>
              ) : (
                <div className="space-y-2">
                  {/* Status & Resolution Row */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="p-2 rounded bg-slate-900 border border-slate-800">
                      <span className="text-[9px] uppercase tracking-wider text-slate-400 block mb-0.5">
                        Incident Status
                      </span>
                      <span className={`inline-flex items-center gap-1 px-1.5 py-0.2 rounded border text-[10px] font-bold ${
                        incident.status_name === "Manually Cleared" || incident.status_code === 2
                          ? "bg-purple-950/80 text-purple-300 border-purple-800"
                          : "bg-blue-950/80 text-blue-300 border-blue-800"
                      }`}>
                        {incident.status_name === "Manually Cleared" && <Check className="h-2.5 w-2.5" />}
                        {incident.status_name}
                      </span>
                    </div>

                    <div className="p-2 rounded bg-slate-900 border border-slate-800">
                      <span className="text-[9px] uppercase tracking-wider text-slate-400 block mb-0.5">
                        Resolution
                      </span>
                      <span className={`inline-block px-1.5 py-0.2 rounded border text-[10px] font-bold ${
                        incident.ground_truth?.resolution === "True Positive"
                          ? "bg-rose-950/90 text-rose-300 border-rose-800"
                          : incident.ground_truth?.resolution === "False Positive"
                          ? "bg-emerald-950/90 text-emerald-300 border-emerald-800"
                          : "bg-slate-900 text-slate-400 border-slate-800"
                      }`}>
                        {incident.ground_truth?.resolution || "Unresolved / Open"}
                      </span>
                    </div>
                  </div>

                  {/* Cleared Reason */}
                  {incident.ground_truth?.cleared_reason && (
                    <div className="p-2 rounded bg-slate-900 border border-slate-800">
                      <span className="text-[9px] uppercase tracking-wider text-slate-400 block mb-0.5">
                        Cleared Reason
                      </span>
                      <p className="text-[11px] text-slate-200 font-sans italic">
                        "{incident.ground_truth.cleared_reason}"
                      </p>
                    </div>
                  )}

                  {/* Cleared User & Cleared Time */}
                  <div className="grid grid-cols-2 gap-2 text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-800/80">
                    <div>
                      <span className="text-slate-500 block text-[9px]">Cleared User:</span>
                      <span className="text-slate-200 font-semibold truncate block">
                        {incident.ground_truth?.cleared_user || "N/A"}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-500 block text-[9px]">Cleared Time:</span>
                      <span className="text-slate-200 truncate block">
                        {incident.ground_truth?.cleared_time_epoch
                          ? formatEpoch(incident.ground_truth.cleared_time_epoch)
                          : "N/A"}
                      </span>
                    </div>
                  </div>

                  {incident.ground_truth?.comments && (
                    <div className="text-[10px] text-slate-400 pt-1">
                      <span className="text-slate-500 block text-[9px]">Comments:</span>
                      <span className="text-slate-300">{incident.ground_truth.comments}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Raw Events Explorer */}
      {activeTab === "events" && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-mono">
              Displaying all {incident.events.length} raw security event logs and vendor attributes
            </span>
          </div>

          {incident.events.length === 0 ? (
            <div className="p-8 rounded-lg border border-slate-800 bg-slate-950 text-center text-xs text-slate-400 font-mono">
              No raw security events recorded for this incident.
            </div>
          ) : (
            <div className="space-y-2.5">
              {incident.events.map((evt, idx) => {
                const rawLog = evt.raw_log || evt.attributes?.["Raw Event Log"] || evt.attributes?.["rawMessage"] || evt.attributes?.["rawEventLog"];
                // Filter out raw log from the key-value attributes grid to avoid duplication
                const filteredAttrs = Object.entries(evt.attributes || {}).filter(
                  ([k]) => k !== "Raw Event Log" && k !== "rawMessage" && k !== "rawEventLog"
                );

                return (
                  <div key={evt.id || idx} className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-2 font-mono text-xs">
                    <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-cyan-950/70 border border-cyan-800 px-1.5 py-0.2 text-[9px] text-cyan-300 font-bold">
                          EVENT #{idx + 1}
                        </span>
                        <span className="text-slate-400 text-[10px]">ID: {evt.event_id}</span>
                        <span className="text-slate-400 text-[10px]">· {evt.event_type}</span>
                      </div>
                      <span className="text-[10px] text-slate-500">
                        Received: {formatEpoch(evt.event_receive_time, incident.created_at)}
                      </span>
                    </div>

                    {rawLog && (
                      <div>
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-[9px] text-slate-500 uppercase">Raw Event Log:</span>
                          <button
                            onClick={() => copyToClipboard(String(rawLog))}
                            className="text-[9px] text-cyan-400 hover:text-cyan-300"
                          >
                            Copy Log
                          </button>
                        </div>
                        <pre className="p-2 rounded bg-slate-900 border border-slate-800 text-[10px] text-slate-300 overflow-x-auto whitespace-pre-wrap max-h-48 leading-relaxed selection:bg-cyan-900 selection:text-white">
                          {String(rawLog)}
                        </pre>
                      </div>
                    )}

                    {/* Generic Vendor Attributes Grid */}
                    {filteredAttrs.length > 0 && (
                      <div>
                        <span className="text-[9px] text-slate-500 uppercase block mb-1">
                          Parsed Vendor Attributes ({filteredAttrs.length}):
                        </span>
                        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-1.5">
                          {filteredAttrs.map(([attrKey, attrVal]) => (
                            <div key={attrKey} className="p-1.5 rounded bg-slate-900/60 border border-slate-800/80 overflow-hidden">
                              <span className="text-[9px] text-slate-400 block truncate" title={attrKey}>
                                {attrKey}
                              </span>
                              <span className="text-slate-200 text-xs font-medium break-all" title={String(attrVal)}>
                                {typeof attrVal === "object" ? JSON.stringify(attrVal) : String(attrVal)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Detection Intelligence Context */}
      {activeTab === "rule" && (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <h2 className="text-sm font-bold text-slate-100">{incident.rule_name || incident.event_type}</h2>
              <span className="text-xs font-mono text-cyan-400">{incident.event_type}</span>
            </div>
            {incident.rule_id && (
              <Link
                href={`/detection-intelligence/${incident.rule_id}`}
                className="rounded-md bg-cyan-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-cyan-500"
              >
                Open Full Detection Spec
              </Link>
            )}
          </div>

          <div className="text-xs text-slate-300">
            <span className="text-[10px] font-mono text-slate-500 block mb-0.5">Rule Description:</span>
            <p className="p-2.5 rounded-md bg-slate-900 border border-slate-800 text-xs">
              {incident.rule_description || "No standalone description available."}
            </p>
          </div>
        </div>
      )}

      {/* Tab 4: Historical Ground Truth */}
      {activeTab === "ground_truth" && (
        <div className="space-y-3">
          {blindReviewMode || !incident.ground_truth ? (
            <div className="rounded-lg border border-dashed border-amber-800/80 bg-amber-950/20 p-6 text-center text-xs">
              <EyeOff className="h-6 w-6 text-amber-400 mx-auto mb-1.5" />
              <h3 className="font-bold text-amber-300 text-xs">Ground Truth Masked in Blind Review Mode</h3>
              <p className="text-slate-400 mt-1 max-w-md mx-auto text-[11px]">
                Historical resolution and comments are hidden so you can test independent verdicts without bias.
              </p>
              <button
                onClick={() => setBlindReviewMode(false)}
                className="mt-3 rounded-md bg-amber-700/80 px-2.5 py-1 text-xs font-semibold text-white hover:bg-amber-600"
              >
                Disable Blind Review to Reveal
              </button>
            </div>
          ) : (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3.5 space-y-3 text-xs font-mono">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
                <div className="flex items-center gap-3">
                  <div>
                    <span className="text-[9px] text-slate-500 uppercase block">Historical Verdict Label:</span>
                    <span
                      className={`mt-0.5 inline-block px-2.5 py-0.5 rounded border text-xs font-bold ${
                        incident.ground_truth.resolution.includes("True")
                          ? "bg-rose-950 text-rose-300 border-rose-800"
                          : incident.ground_truth.resolution.includes("False")
                          ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                          : "bg-slate-900 text-slate-400 border-slate-800"
                      }`}
                    >
                      {incident.ground_truth.resolution || "Unlabeled"}
                    </span>
                  </div>

                  <div>
                    <span className="text-[9px] text-slate-500 uppercase block">Status:</span>
                    <span className="mt-0.5 inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-bold bg-slate-900 text-slate-200 border-slate-800">
                      {incident.status_name}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {incident.ground_truth.is_ml_generated && (
                    <span className="rounded bg-purple-950 text-purple-300 border border-purple-800 px-1.5 py-0.5 text-[9px] uppercase font-bold">
                      Machine Learning Note
                    </span>
                  )}
                  <button
                    onClick={handleSyncResolution}
                    disabled={syncingResolution}
                    className="inline-flex items-center gap-1 rounded bg-slate-900 border border-cyan-800/60 px-2.5 py-1 text-xs font-semibold text-cyan-300 hover:bg-slate-800 disabled:opacity-50 transition-colors"
                  >
                    <RefreshCw className={`h-3 w-3 ${syncingResolution ? "animate-spin text-cyan-400" : ""}`} />
                    <span>{syncingResolution ? "Syncing..." : "Sync from FortiSIEM"}</span>
                  </button>
                </div>
              </div>

              <div>
                <span className="text-[9px] text-slate-500 uppercase block mb-0.5">Cleared Reason:</span>
                <div className="p-2.5 rounded-md bg-slate-900 border border-slate-800 text-slate-200 text-xs">
                  {incident.ground_truth.cleared_reason || "None recorded."}
                </div>
              </div>

              <div>
                <span className="text-[9px] text-slate-500 uppercase block mb-0.5">Analyst / System Comments:</span>
                <div className="p-2.5 rounded-md bg-slate-900 border border-slate-800 text-slate-200 text-xs">
                  {incident.ground_truth.comments || "No historical comments."}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[10px] text-slate-400 border-t border-slate-800 pt-2">
                <div>Cleared User: {incident.ground_truth.cleared_user || "System / Unspecified"}</div>
                <div>Cleared Time: {formatEpoch(incident.ground_truth.cleared_time_epoch)}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Raw JSON Viewer */}
      {activeTab === "raw_json" && (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400">
              Unmodified original SIEM ingestion payload
            </span>
            <button
              onClick={() => copyToClipboard(JSON.stringify(incident.raw_payload, null, 2))}
              className="flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900 px-2 py-0.5 text-xs text-slate-300 hover:text-white"
            >
              {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy Payload"}
            </button>
          </div>
          <pre className="rounded-md bg-slate-900 border border-slate-800 p-3 font-mono text-[11px] text-cyan-300 overflow-x-auto max-h-[500px] overflow-y-auto">
            {JSON.stringify(incident.raw_payload, null, 2)}
          </pre>
        </div>
      )}

      {/* Tab 6: Evidence Integrity Guardrail */}
      {activeTab === "model_payload" && (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5" />
                Evidence Integrity Guardrail (Zero Leakage Verification)
              </h2>
              <p className="text-[10px] text-slate-400 mt-0.5">
                Whitelisted features sent to LLM pipelines. Resolution verdicts, analyst comments, and closure timestamps are strictly excluded.
              </p>
            </div>
            <button
              onClick={() => copyToClipboard(JSON.stringify(modelPayload, null, 2))}
              className="flex items-center gap-1.5 rounded-md border border-slate-800 bg-slate-900 px-2 py-0.5 text-xs text-slate-300 hover:text-white"
            >
              {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
              {copied ? "Copied" : "Copy Model Input"}
            </button>
          </div>

          <pre className="rounded-md bg-slate-900 border border-slate-800 p-3 font-mono text-[11px] text-emerald-400 overflow-x-auto max-h-[500px] overflow-y-auto">
            {JSON.stringify(modelPayload, null, 2)}
          </pre>
        </div>
      )}

      {/* Tab 7: Historical Telemetry Timeline */}
      {activeTab === "timeline" && (
        <HistoricalTelemetryTimeline incidentId={incident.incident_id} />
      )}

      {/* Tab 8: Canonical Evidence Records */}
      {activeTab === "canonical_evidence" && (
        <div className="space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                <Scale className="h-3.5 w-3.5" />
                Normalized Canonical Evidence Records
              </h2>
              <p className="text-[10px] text-slate-400 mt-0.5">
                Each SIEM field is normalized into an immutable, deterministically keyed evidence record with SHA-256 cryptographic digest.
              </p>
            </div>
            {modelPayload?.canonical_evidence && (
              <span className="text-[10px] text-slate-400">
                Total: <strong className="text-cyan-300">{modelPayload.canonical_evidence.length}</strong> items
              </span>
            )}
          </div>

          {!modelPayload?.canonical_evidence || modelPayload.canonical_evidence.length === 0 ? (
            <div className="p-8 rounded-lg border border-slate-800 bg-slate-950 text-center text-slate-400">
              No normalized canonical evidence records available for this incident.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {modelPayload.canonical_evidence.map((ev: any, idx: number) => (
                <div
                  key={ev.evidence_id || idx}
                  className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1.5 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-1">
                    <span className="text-[9px] bg-cyan-950 text-cyan-300 border border-cyan-800 px-1.5 py-0.2 rounded font-bold">
                      {ev.evidence_type || ev.evidence_category || "TELEMETRY"}
                    </span>
                    <button
                      onClick={() => copyToClipboard(ev.evidence_id)}
                      className="text-[9px] text-slate-400 hover:text-white"
                      title="Copy evidence ID"
                    >
                      {ev.evidence_id}
                    </button>
                  </div>

                  <div>
                    <span className="text-[9px] text-slate-500 block">Canonical Field:</span>
                    <span className="text-cyan-300 font-bold">{ev.source_field || ev.canonical_field}</span>
                    {(ev.raw_field_name || ev.source_system) && (
                      <span className="text-[10px] text-slate-500 ml-1.5">
                        ({ev.raw_field_name ? "raw: " : "src: "}
                        <span className="text-slate-400">{ev.raw_field_name || ev.source_system}</span>)
                      </span>
                    )}
                  </div>

                  <div>
                    <span className="text-[9px] text-slate-500 block">Observed Value:</span>
                    <div className="p-1.5 rounded bg-slate-900 border border-slate-800/80 text-slate-200 text-[11px] break-all max-h-24 overflow-y-auto">
                      {typeof ev.observed_value === "object"
                        ? JSON.stringify(ev.observed_value)
                        : String(ev.observed_value)}
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[9px] text-slate-500 pt-1 border-t border-slate-900">
                    <span>Event: {ev.source_event_id || "incident_level"}</span>
                    <span title={ev.integrity_digest}>
                      SHA: {ev.integrity_digest ? ev.integrity_digest.substring(0, 10) : "N/A"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

