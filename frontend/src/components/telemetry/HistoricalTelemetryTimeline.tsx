"use client";

import React, { useEffect, useState } from "react";
import {
  Clock,
  Database,
  Eye,
  FileText,
  AlertTriangle,
  Bot,
  CheckCircle2,
  Cpu,
  Layers,
  Zap,
  Copy,
  Check,
  RefreshCw,
  ShieldCheck,
  Tag,
  Sparkles,
} from "lucide-react";
import { api, IncidentTimelineResponse, TimelineMilestone } from "@/lib/api";

interface Props {
  incidentId: string;
}

export function HistoricalTelemetryTimeline({ incidentId }: Props) {
  const [data, setData] = useState<IncidentTimelineResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string>("ALL");
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const [expandedEvt, setExpandedEvt] = useState<number | null>(null);

  const loadTimeline = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await api.getIncidentTimeline(incidentId);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load historical telemetry timeline");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (incidentId) {
      loadTimeline();
    }
  }, [incidentId]);

  const copyText = (text: string, idx: number) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const getStageColor = (stage: string) => {
    switch (stage?.toUpperCase()) {
      case "OBSERVATION":
        return "border-cyan-500 bg-cyan-950 text-cyan-300";
      case "TELEMETRY":
        return "border-slate-600 bg-slate-900 text-slate-300";
      case "CORRELATION":
        return "border-amber-500 bg-amber-950 text-amber-300";
      case "INGESTION":
        return "border-blue-500 bg-blue-950 text-blue-300";
      case "TRIAGE":
        return "border-purple-500 bg-purple-950 text-purple-300";
      case "RESOLUTION":
        return "border-emerald-500 bg-emerald-950 text-emerald-300";
      default:
        return "border-slate-700 bg-slate-900 text-slate-400";
    }
  };

  const getStageIcon = (type: string, stage: string) => {
    if (stage === "TRIAGE") return <Bot className="h-3.5 w-3.5 text-purple-400" />;
    if (stage === "RESOLUTION") return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />;
    if (stage === "INGESTION") return <Database className="h-3.5 w-3.5 text-blue-400" />;
    if (stage === "CORRELATION") return <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />;
    if (type === "RAW_EVENT") return <FileText className="h-3.5 w-3.5 text-slate-400" />;
    return <Eye className="h-3.5 w-3.5 text-cyan-400" />;
  };

  const filteredMilestones = (data?.milestones || []).filter((m) => {
    if (activeFilter === "ALL") return true;
    if (activeFilter === "TELEMETRY") return m.stage === "TELEMETRY" || m.stage === "OBSERVATION";
    if (activeFilter === "TRIAGE") return m.stage === "TRIAGE";
    if (activeFilter === "LIFECYCLE") return m.stage !== "TELEMETRY";
    return true;
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400 text-xs font-mono">
        <RefreshCw className="h-4 w-4 animate-spin text-cyan-400 mr-2" />
        Loading historical telemetry timeline from Server 1...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs font-mono text-rose-300">
        {error || "Failed to retrieve telemetry timeline."}
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-4 space-y-4">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
        <div>
          <h2 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
            <Clock className="h-4 w-4 text-cyan-400" />
            Historical Telemetry Timeline
          </h2>
          <p className="text-[10px] text-slate-400 mt-0.5">
            Chronological audit trail of all raw security telemetry, correlation bursts, and triage stages persistently stored on Server 1
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300">
            <Database className="h-3 w-3 text-emerald-400" />
            Server 1 Stored
          </span>

          <button
            onClick={loadTimeline}
            className="text-[10px] font-mono text-slate-400 hover:text-slate-200 flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900 border border-slate-800"
          >
            <RefreshCw className="h-3 w-3" />
            Refresh
          </button>
        </div>
      </div>

      {/* Token Bifurcation Summary Pill (If Evaluated) */}
      {data.token_summary && data.token_summary.total_tokens > 0 && (
        <div className="rounded-lg border border-purple-900/60 bg-purple-950/20 p-2.5 flex flex-wrap items-center justify-between gap-2 font-mono text-xs">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-purple-400" />
            <span className="font-bold text-purple-200">Incident Token Consumption Bifurcation:</span>
          </div>

          <div className="flex items-center gap-3 text-[11px]">
            <span className="text-cyan-300">
              Prompt (Input): <strong>{data.token_summary.prompt_tokens.toLocaleString()}</strong>
            </span>
            <span className="text-emerald-300">
              Output (Reasoning): <strong>{data.token_summary.completion_tokens.toLocaleString()}</strong>
            </span>
            <span className="text-slate-200 font-bold px-1.5 py-0.5 rounded bg-purple-900/40 border border-purple-800/80">
              Total: {data.token_summary.total_tokens.toLocaleString()} tokens
            </span>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-1 text-[11px] font-mono border-b border-slate-800/80 pb-2 overflow-x-auto">
        <span className="text-slate-500 mr-1 text-[10px] uppercase">Filter:</span>
        {[
          { key: "ALL", label: `All Milestones (${data.milestones.length})` },
          { key: "LIFECYCLE", label: "Lifecycle Milestones" },
          { key: "TELEMETRY", label: "Raw Telemetry Logs" },
          { key: "TRIAGE", label: "Agent Triage Decisions" },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setActiveFilter(f.key)}
            className={`px-2 py-0.5 rounded transition-all ${
              activeFilter === f.key
                ? "bg-cyan-950 text-cyan-300 font-bold border border-cyan-800"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Timeline Stream */}
      <div className="relative border-l border-slate-800 pl-6 space-y-4 text-xs font-mono">
        {filteredMilestones.map((m: TimelineMilestone, idx: number) => {
          const isTriage = m.stage === "TRIAGE";
          const isRawEvt = m.type === "RAW_EVENT";

          return (
            <div key={idx} className="relative group">
              {/* Timeline Node Dot */}
              <span
                className={`absolute -left-[31px] flex h-4 w-4 items-center justify-center rounded-full border text-[9px] ${getStageColor(
                  m.stage
                )}`}
              >
                {getStageIcon(m.type, m.stage)}
              </span>

              {/* Event Content Card */}
              <div className="rounded-lg border border-slate-800/80 bg-slate-900/50 p-3 space-y-2 hover:border-slate-700 transition-colors">
                <div className="flex flex-wrap items-center justify-between gap-1.5 border-b border-slate-800/60 pb-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${getStageColor(m.stage)}`}>
                      {m.stage}
                    </span>
                    <strong className="text-slate-200 font-semibold text-xs">{m.title}</strong>
                  </div>

                  <span className="text-[10px] text-slate-500 flex items-center gap-1 font-mono">
                    <Clock className="h-3 w-3 text-slate-500" />
                    {m.timestamp}
                  </span>
                </div>

                <p className="text-xs text-slate-300 font-sans leading-relaxed">
                  {m.description}
                </p>

                {/* Triage Milestone Bifurcated Tokens Pill */}
                {isTriage && m.token_bifurcation && (
                  <div className="rounded bg-purple-950/40 border border-purple-900/60 p-2 space-y-1 text-[11px] font-mono">
                    <div className="flex items-center justify-between text-purple-300">
                      <span>Model: {m.token_bifurcation.model}</span>
                      <span>Latency: {m.token_bifurcation.latency_ms} ms</span>
                    </div>
                    <div className="flex items-center gap-3 text-slate-300 pt-0.5 border-t border-purple-900/40">
                      <span className="text-cyan-300">
                        Input: <strong>{m.token_bifurcation.prompt_tokens}</strong> toks
                      </span>
                      <span className="text-emerald-300">
                        Output: <strong>{m.token_bifurcation.completion_tokens}</strong> toks
                      </span>
                      <span className="text-slate-100 font-bold">
                        Total: {m.token_bifurcation.total_tokens} toks
                      </span>
                    </div>
                  </div>
                )}

                {/* Raw Event Attributes / Details */}
                {isRawEvt && m.metadata?.attributes && (
                  <div className="space-y-1 pt-1">
                    <div className="flex items-center justify-between">
                      <button
                        onClick={() => setExpandedEvt(expandedEvt === idx ? null : idx)}
                        className="text-[10px] text-cyan-400 hover:underline flex items-center gap-1"
                      >
                        {expandedEvt === idx ? "Hide Telemetry Attributes ▲" : `View Attributes (${m.metadata.attribute_count}) ▼`}
                      </button>

                      <button
                        onClick={() => copyText(JSON.stringify(m.metadata?.attributes, null, 2), idx)}
                        className="text-[10px] text-slate-400 hover:text-white flex items-center gap-1"
                      >
                        {copiedIdx === idx ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                        {copiedIdx === idx ? "Copied" : "Copy Attributes"}
                      </button>
                    </div>

                    {expandedEvt === idx && (
                      <pre className="p-2 rounded bg-slate-950 border border-slate-800 text-[10px] text-emerald-300 overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
                        {JSON.stringify(m.metadata.attributes, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
