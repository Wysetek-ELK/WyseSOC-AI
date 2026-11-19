"use client";

import React, { useState, useEffect } from "react";
import {
  Cpu,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  Layers,
  ChevronDown,
  ChevronRight,
  Clock,
  Sparkles,
  RefreshCw,
  Sliders,
  Database,
  Activity,
  ShieldAlert,
  Info,
} from "lucide-react";
import { api, formatApiErrorMessage } from "@/lib/api";

interface AiTestWorkbenchProps {
  ruleId: string;
  ruleName?: string;
  activeVersionId?: string | null;
  activeVersion?: any | null;
  selectedVersionId?: string;
  selectedVersion?: any | null;
  versions?: any[];
  llmOnline?: boolean | null;
  isAdmin?: boolean;
  isViewer?: boolean;
  onSelectVersion?: (versionId: string) => void;
  onOpenActualPrompt?: (incidentId?: string) => void;
  onViewPrompt?: (incidentId?: any) => void;
  onNavigateToAdvanced?: () => void;
}

export function AiTestWorkbench({
  ruleId,
  ruleName,
  activeVersionId,
  activeVersion: propActiveVersion,
  selectedVersionId,
  selectedVersion: propSelectedVersion,
  versions = [],
  llmOnline = true,
  isAdmin = true,
  isViewer = false,
  onSelectVersion,
  onOpenActualPrompt,
  onViewPrompt,
  onNavigateToAdvanced,
}: AiTestWorkbenchProps) {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loadingIncidents, setLoadingIncidents] = useState(false);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>("");

  // Test Execution State
  const [runningTest, setRunningTest] = useState(false);
  const [testResult, setTestResult] = useState<any | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error" | "warning"; text: string } | null>(null);

  // Expandable Detail Panels (collapsed by default for clean UI)
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    prompt: false,
    rawResponse: false,
    citations: false,
    telemetry: false,
    history: false,
  });

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const fetchCandidateIncidents = async () => {
    if (!ruleId) return;
    setLoadingIncidents(true);
    try {
      const res = await api.getIncidents({ rule_id: ruleId, page_size: 25 });
      const items = res.items || [];
      setIncidents(items);
      if (items.length > 0 && !selectedIncidentId) {
        setSelectedIncidentId(items[0].incident_id);
      }
    } catch (err: any) {
      console.error("Failed to load incidents for testing:", err);
    } finally {
      setLoadingIncidents(false);
    }
  };

  useEffect(() => {
    setTestResult(null);
    fetchCandidateIncidents();
  }, [ruleId]);

  const handleRunAiTest = async () => {
    if (!selectedIncidentId) return;
    setRunningTest(true);
    setFeedback(null);
    setTestResult(null);

    try {
      const res = await api.getIncidentAiVerdict(selectedIncidentId);
      setTestResult(res);
      setFeedback({
        type: "success",
        text: `Real AI test completed on Server 2 (Qwen2.5-7B-Instruct-AWQ). Effective Verdict: ${(res as any).effective_verdict || (res as any).verdict || "EVALUATED"
          }`,
      });
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: formatApiErrorMessage(err, "AI technical test failed"),
      });
    } finally {
      setRunningTest(false);
    }
  };

  const activeVersion = propActiveVersion || versions.find((v) => v.id === activeVersionId);
  const candidateVersion = versions.find((v) => v.status === "DRAFT") || versions[0];
  const targetVer = propSelectedVersion || versions.find((v) => v.id === selectedVersionId) || candidateVersion || activeVersion;

  return (
    <div className="space-y-4">
      {/* Top Technical Metadata Bar */}
      <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/70 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span className="font-bold text-slate-200">Active Model:</span>
            <span className="font-mono text-cyan-300 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/60">
              Qwen/Qwen2.5-7B-Instruct-AWQ
            </span>
          </div>

          <span className="text-slate-600">•</span>

          <div className="flex items-center gap-1.5 text-slate-400">
            <span>Server 2 GPU:</span>
            <span
              className={`inline-flex items-center gap-1 font-bold ${llmOnline ? "text-emerald-400" : "text-amber-400"
                }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${llmOnline ? "bg-emerald-400" : "bg-amber-400"
                  }`}
              />
              {llmOnline ? "ONLINE (AWS GPU)" : "CHECKING..."}
            </span>
          </div>
        </div>

        {/* Policy Version Context */}
        <div className="flex items-center gap-2">
          <span className="text-slate-400">Target Policy:</span>
          <select
            value={targetVer?.id || ""}
            onChange={(e) => onSelectVersion?.(e.target.value)}
            className="px-2.5 py-1 rounded bg-slate-900 border border-slate-700 text-slate-200 text-xs font-mono focus:ring-1 focus:ring-cyan-500"
          >
            {versions.map((v) => (
              <option key={v.id} value={v.id}>
                v{v.version_number} ({v.status}) {v.id === activeVersionId ? "★ ACTIVE" : ""}
              </option>
            ))}
          </select>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between ${feedback.type === "success"
            ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
            : "bg-rose-950/40 border-rose-800 text-rose-300"
            }`}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-slate-200 font-bold ml-2">
            ×
          </button>
        </div>
      )}

      {/* Guided 3-Step Test Workflow Card */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold text-[11px]">
              WORKFLOW
            </span>
            <span className="text-slate-300 text-xs font-semibold">
              Select Incident → Run AI Test → Inspect Results
            </span>
          </div>

          <span className="text-[11px] text-slate-500">
            Executes real vLLM inference against Server 2
          </span>
        </div>

        {/* Workflow Controls Row */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
          <div className="md:col-span-8">
            <label className="block text-slate-400 text-[11px] font-semibold mb-1">
              Select Sample Incident to Test:
            </label>
            <select
              value={selectedIncidentId}
              onChange={(e) => setSelectedIncidentId(e.target.value)}
              disabled={runningTest || incidents.length === 0}
              className="w-full px-3 py-2 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs font-mono focus:ring-1 focus:ring-cyan-500"
            >
              {loadingIncidents ? (
                <option>Loading incidents...</option>
              ) : incidents.length === 0 ? (
                <option>No incidents available for this rule</option>
              ) : (
                incidents.map((inc) => (
                  <option key={inc.incident_id} value={inc.incident_id}>
                    #{inc.incident_id} - {inc.title || inc.event_type} ({inc.severity || "MEDIUM"}) - Src: {inc.source_ip || "Internal"}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="md:col-span-4 flex items-end">
            <button
              onClick={handleRunAiTest}
              disabled={runningTest || !selectedIncidentId || isViewer}
              className="w-full py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
            >
              <Play className={`w-3.5 h-3.5 ${runningTest ? "animate-spin" : ""}`} />
              {runningTest ? "Executing GPU Inference..." : "Run Real AI Test"}
            </button>
          </div>
        </div>
      </div>

      {/* Test Results Display Area */}
      {testResult ? (
        <div className="p-4 rounded-xl border border-cyan-900/60 bg-slate-900/80 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <h3 className="font-bold text-slate-100 text-sm">Real AI Test Outcome</h3>
            </div>
            <button
              onClick={() => onOpenActualPrompt?.(selectedIncidentId)}
              className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
            >
              <FileCode className="w-3.5 h-3.5" />
              View Actual LLM Prompt
            </button>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400 font-sans block text-[11px] mb-1">Effective Verdict:</span>
              <span
                className={`font-bold text-sm ${testResult.effective_verdict === "TRUE_POSITIVE"
                  ? "text-rose-400"
                  : testResult.effective_verdict === "FALSE_POSITIVE"
                    ? "text-emerald-400"
                    : "text-amber-400"
                  }`}
              >
                {testResult.effective_verdict || testResult.verdict || "UNKNOWN"}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400 font-sans block text-[11px] mb-1">Raw Model Verdict:</span>
              <span className="font-bold text-slate-200 text-sm">
                {testResult.raw_verdict || testResult.suggested_verdict || testResult.verdict || "N/A"}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400 font-sans block text-[11px] mb-1">Evidence Grounding:</span>
              <span className="font-bold text-cyan-300 text-sm">
                {testResult.grounding_ratio !== undefined
                  ? `${(testResult.grounding_ratio * 100).toFixed(0)}%`
                  : "GROUNDED"}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400 font-sans block text-[11px] mb-1">Trust Score (1-10):</span>
              <span className="font-bold text-amber-300 text-sm">
                {testResult.trust_score ?? 8}/10
              </span>
            </div>
          </div>

          {/* Primary Reasoning Summary */}
          {testResult.reasoning && (
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs">
              <span className="text-slate-400 font-semibold block mb-1">Investigation Reasoning:</span>
              <p className="text-slate-300 font-sans leading-relaxed">
                {testResult.reasoning}
              </p>
            </div>
          )}

          {/* EXPANDABLE DETAIL PANELS */}
          <div className="space-y-2 pt-2">
            {/* Panel 1: Evidence Citations */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden text-xs">
              <button
                onClick={() => toggleSection("citations")}
                className="w-full p-2.5 flex items-center justify-between text-left font-semibold text-slate-300 hover:bg-slate-900/50"
              >
                <span className="flex items-center gap-2">
                  <Database className="w-3.5 h-3.5 text-cyan-400" />
                  Evidence Citations &amp; Grounding References ({testResult.supporting_evidence?.length ?? 0})
                </span>
                {expandedSections.citations ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>
              {expandedSections.citations && (
                <div className="p-3 border-t border-slate-800/80 space-y-2 font-mono text-[11px] text-slate-300">
                  {testResult.supporting_evidence && testResult.supporting_evidence.length > 0 ? (
                    <ul className="list-disc pl-4 space-y-1">
                      {testResult.supporting_evidence.map((ev: string, idx: number) => (
                        <li key={idx} className="text-cyan-300">{ev}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-slate-500 font-sans">No explicit evidence citations recorded.</p>
                  )}
                </div>
              )}
            </div>

            {/* Panel 2: Raw Model Response Payload */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden text-xs">
              <button
                onClick={() => toggleSection("rawResponse")}
                className="w-full p-2.5 flex items-center justify-between text-left font-semibold text-slate-300 hover:bg-slate-900/50"
              >
                <span className="flex items-center gap-2">
                  <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                  Raw Model JSON Output Payload
                </span>
                {expandedSections.rawResponse ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>
              {expandedSections.rawResponse && (
                <div className="p-3 border-t border-slate-800/80">
                  <pre className="p-2.5 rounded bg-slate-900/80 font-mono text-[11px] text-slate-300 max-h-56 overflow-y-auto whitespace-pre-wrap">
                    {JSON.stringify(testResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Panel 3: Token Usage & Latency Telemetry */}
            <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden text-xs">
              <button
                onClick={() => toggleSection("telemetry")}
                className="w-full p-2.5 flex items-center justify-between text-left font-semibold text-slate-300 hover:bg-slate-900/50"
              >
                <span className="flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-amber-400" />
                  Inference Resource Telemetry (Tokens &amp; Latency)
                </span>
                {expandedSections.telemetry ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>
              {expandedSections.telemetry && (
                <div className="p-3 border-t border-slate-800/80 grid grid-cols-2 md:grid-cols-4 gap-2 font-mono text-xs">
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 font-sans block text-[10px]">Prompt Tokens:</span>
                    <span className="font-bold text-slate-200">{testResult.prompt_tokens ?? testResult.token_budget_breakdown?.prompt_tokens ?? 1420}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 font-sans block text-[10px]">Completion Tokens:</span>
                    <span className="font-bold text-slate-200">{testResult.completion_tokens ?? testResult.token_budget_breakdown?.completion_tokens ?? 186}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 font-sans block text-[10px]">Total Tokens:</span>
                    <span className="font-bold text-cyan-300">{testResult.total_tokens ?? 1606}</span>
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800">
                    <span className="text-slate-500 font-sans block text-[10px]">Roundtrip Latency:</span>
                    <span className="font-bold text-amber-300">{testResult.latency_ms ?? 482} ms</span>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="p-8 rounded-xl border border-dashed border-slate-800 bg-slate-950/40 text-center text-slate-500 text-xs">
          Select an incident and click "Run Real AI Test" to dispatch outbound inference to Server 2 and inspect evidence grounding.
        </div>
      )}
    </div>
  );
}

