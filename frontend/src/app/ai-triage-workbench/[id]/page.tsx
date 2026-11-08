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
} from "lucide-react";
import { api, IncidentDetail, IncidentAiVerdictResponse } from "@/lib/api";
import { useApp } from "@/context/AppContext";

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
    "overview" | "events" | "rule" | "ground_truth" | "raw_json" | "model_payload" | "timeline"
  >("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [analyzing, setAnalyzing] = useState(false);
  const [aiVerdict, setAiVerdict] = useState<IncidentAiVerdictResponse | null>(null);
  const [verdictError, setVerdictError] = useState<string | null>(null);

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
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3 shadow-lg">
          <div className="flex flex-wrap items-center justify-between border-b border-slate-800 pb-2.5 gap-2">
            <div className="flex items-center gap-2 flex-wrap">
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

              <span className="text-emerald-400 font-semibold">• GPU Live</span>
              <button
                onClick={() => setAiVerdict(null)}
                className="text-slate-400 hover:text-slate-200 text-xs px-1"
                title="Hide banner"
              >
                ✕
              </button>
            </div>
          </div>

          <div
            className={`rounded-lg border p-3 flex items-center justify-between ${
              aiVerdict.verdict === "TRUE_POSITIVE"
                ? "bg-rose-950/50 border-rose-800 text-rose-200"
                : aiVerdict.verdict === "FALSE_POSITIVE"
                ? "bg-emerald-950/50 border-emerald-800 text-emerald-200"
                : "bg-amber-950/50 border-amber-800 text-amber-200"
            }`}
          >
            <div className="flex items-center gap-2.5">
              {aiVerdict.verdict === "TRUE_POSITIVE" ? (
                <AlertTriangle className="h-5 w-5 text-rose-400" />
              ) : aiVerdict.verdict === "FALSE_POSITIVE" ? (
                <CheckCircle2 className="h-5 w-5 text-emerald-400" />
              ) : (
                <AlertCircle className="h-5 w-5 text-amber-400" />
              )}
              <div>
                <div className="text-[10px] uppercase font-mono tracking-wider opacity-80">
                  Model Determination
                </div>
                <div className="text-sm font-bold tracking-tight">
                  {aiVerdict.verdict.replace(/_/g, " ")}
                </div>
              </div>
            </div>

            <div className="text-right">
              <div className="text-[10px] uppercase font-mono tracking-wider opacity-80">
                Confidence
              </div>
              <div className="text-base font-extrabold font-mono">
                {Math.round(aiVerdict.confidence)}%
              </div>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-1">
            <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider flex items-center gap-1.5">
              <Bot className="h-3 w-3 text-cyan-400" />
              Analytical Justification
            </div>
            <p className="text-xs text-slate-200 leading-relaxed font-sans">
              {aiVerdict.reason}
            </p>
          </div>

          {aiVerdict.supporting_evidence && aiVerdict.supporting_evidence.length > 0 && (
            <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-3 space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                Supporting Evidence Attributes
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
          className={`px-3 py-1.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "timeline"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Lifecycle Timeline
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
                <div>
                  <span className="text-[9px] text-slate-500 uppercase block">Historical Verdict Label:</span>
                  <span
                    className={`mt-0.5 inline-block px-2.5 py-0.5 rounded border text-xs font-bold ${
                      incident.ground_truth.resolution.includes("True")
                        ? "bg-rose-950 text-rose-300 border-rose-800"
                        : "bg-emerald-950 text-emerald-300 border-emerald-800"
                    }`}
                  >
                    {incident.ground_truth.resolution || "Unlabeled"}
                  </span>
                </div>
                {incident.ground_truth.is_ml_generated && (
                  <span className="rounded bg-purple-950 text-purple-300 border border-purple-800 px-1.5 py-0.5 text-[9px] uppercase font-bold">
                    Machine Learning Note
                  </span>
                )}
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

      {/* Tab 7: Timeline */}
      {activeTab === "timeline" && (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Incident Lifecycle Milestones
          </h2>
          <div className="relative border-l border-slate-800 pl-5 space-y-4 text-xs font-mono">
            {/* First Seen */}
            <div className="relative">
              <span className="absolute -left-[27px] flex h-3.5 w-3.5 items-center justify-center rounded-full bg-cyan-950 border border-cyan-500 text-cyan-300 text-[8px]">
                ●
              </span>
              <div className="font-semibold text-slate-200">First Telemetry Observed</div>
              <div className="text-slate-500 text-[10px]">{formatEpoch(incident.first_seen_epoch)}</div>
            </div>

            {/* Created */}
            <div className="relative">
              <span className="absolute -left-[27px] flex h-3.5 w-3.5 items-center justify-center rounded-full bg-blue-950 border border-blue-500 text-blue-300 text-[8px]">
                ●
              </span>
              <div className="font-semibold text-slate-200">SIEM Incident Alert Created</div>
              <div className="text-slate-500 text-[10px]">{formatEpoch(incident.created_at_epoch, incident.created_at)}</div>
            </div>

            {/* Last Seen */}
            <div className="relative">
              <span className="absolute -left-[27px] flex h-3.5 w-3.5 items-center justify-center rounded-full bg-slate-800 border border-slate-600 text-slate-300 text-[8px]">
                ●
              </span>
              <div className="font-semibold text-slate-200">Last Telemetry Observed</div>
              <div className="text-slate-500 text-[10px]">{formatEpoch(incident.last_seen_epoch)}</div>
            </div>

            {/* Cleared / Resolved */}
            {incident.ground_truth?.cleared_time_epoch && !blindReviewMode && (
              <div className="relative">
                <span className="absolute -left-[27px] flex h-3.5 w-3.5 items-center justify-center rounded-full bg-emerald-950 border border-emerald-500 text-emerald-300 text-[8px]">
                  ●
                </span>
                <div className="font-semibold text-slate-200">
                  SIEM Ticket Cleared ({incident.ground_truth.resolution})
                </div>
                <div className="text-slate-500 text-[10px]">
                  {formatEpoch(incident.ground_truth.cleared_time_epoch)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

