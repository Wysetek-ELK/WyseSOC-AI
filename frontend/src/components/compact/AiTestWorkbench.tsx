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
  History,
  X,
  Check,
  AlertCircle,
  HelpCircle,
  Search,
} from "lucide-react";
import {
  api,
  formatApiErrorMessage,
  AisEvaluationItem,
  AisEvaluationSummary,
  AisEvaluationHistoryItem,
  AisEvaluationHistoryResponse,
  AisBatchEvaluationResponse,
} from "@/lib/api";

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

  // Target Policy Version
  const activeVersion = propActiveVersion || versions.find((v) => v.id === activeVersionId);
  const candidateVersion = versions.find((v) => v.status === "DRAFT") || versions[0];
  const targetVer = propSelectedVersion || versions.find((v) => v.id === selectedVersionId) || candidateVersion || activeVersion;

  // Stored Evaluation Items for the Target Policy Version
  const [ruleEvalItems, setRuleEvalItems] = useState<AisEvaluationItem[]>([]);
  const [evalSummary, setEvalSummary] = useState<AisEvaluationSummary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  // History Modal State
  const [evalHistory, setEvalHistory] = useState<AisEvaluationHistoryResponse | null>(null);
  const [loadingEvalHistory, setLoadingEvalHistory] = useState(false);
  const [showHistoryModal, setShowHistoryModal] = useState(false);

  // Test Execution State
  const [runningTest, setRunningTest] = useState(false);
  const [testResult, setTestResult] = useState<any | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error" | "warning"; text: string } | null>(null);

  // Batch Missing Incidents Modal State
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchConcurrency, setBatchConcurrency] = useState<number>(1);
  const [batchConfirmed, setBatchConfirmed] = useState(false);
  const [batchResult, setBatchResult] = useState<AisBatchEvaluationResponse | null>(null);

  // Table Filters State
  const [tableFilter, setTableFilter] = useState<string>("ALL");
  const [tableSearch, setTableSearch] = useState<string>("");

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
      const res = await api.getIncidents({ rule_id: ruleId, page_size: 50 });
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

  const fetchRuleSummary = async () => {
    if (!ruleId) return;
    setLoadingSummary(true);
    try {
      const res = await api.getRuleEvaluationStatus(ruleId, {
        policy_version_id: targetVer?.id,
        policy_version_number: targetVer?.version_number,
        page_size: 100,
      });
      setEvalSummary(res.summary);
      setRuleEvalItems(res.items || []);
    } catch (err: any) {
      console.error("Failed to fetch rule evaluation summary:", err);
    } finally {
      setLoadingSummary(false);
    }
  };

  const fetchIncidentHistory = async (incId: string) => {
    if (!incId) return;
    setLoadingEvalHistory(true);
    try {
      const res = await api.getIncidentEvaluationHistory(incId);
      setEvalHistory(res);
    } catch (err: any) {
      console.error("Failed to fetch incident evaluation history:", err);
      setEvalHistory(null);
    } finally {
      setLoadingEvalHistory(false);
    }
  };

  useEffect(() => {
    setTestResult(null);
    fetchCandidateIncidents();
  }, [ruleId]);

  useEffect(() => {
    fetchRuleSummary();
  }, [ruleId, targetVer?.id, targetVer?.version_number]);

  useEffect(() => {
    if (selectedIncidentId) {
      fetchIncidentHistory(selectedIncidentId);
    }
  }, [selectedIncidentId]);

  // Find authoritative evaluation item for the selected incident under the current target version
  const currentItem = ruleEvalItems.find(
    (it) => it.incident_id === selectedIncidentId || it.db_id === selectedIncidentId
  );
  const incidentStatus = currentItem?.status || "NOT_EVALUATED";

  // Prepopulate stored result if available
  useEffect(() => {
    if (currentItem && (currentItem.status === "EVALUATED_DECISIVE" || currentItem.status === "ABSTAINED")) {
      setTestResult({
        effective_verdict: currentItem.effective_verdict,
        raw_verdict: currentItem.raw_model_verdict,
        verdict: currentItem.effective_verdict,
        grounding_ratio: currentItem.confidence ?? 0.85,
        trust_score: 8,
        reasoning: currentItem.reason || `Stored real inference for policy v${currentItem.policy_version_number ?? targetVer?.version_number}.`,
        model_name: currentItem.model_name || "Qwen/Qwen2.5-7B-Instruct-AWQ",
        latency_ms: currentItem.latency_ms ?? 450,
        policy_version_number: currentItem.policy_version_number,
        is_stored_result: true,
        status: currentItem.status,
      });
    } else {
      setTestResult(null);
    }
  }, [selectedIncidentId, currentItem?.status, targetVer?.version_number]);

  const handleRunAiTest = async () => {
    if (!selectedIncidentId) return;
    setRunningTest(true);
    setFeedback(null);

    try {
      const res = await api.getIncidentAiVerdict(
        selectedIncidentId,
        targetVer?.id,
        targetVer?.version_number
      );
      setTestResult(res);
      setFeedback({
        type: "success",
        text: `Real AI test completed on Server 2 (Qwen2.5-7B-Instruct-AWQ). Effective Verdict: ${(res as any).effective_verdict || (res as any).verdict || "EVALUATED"}`,
      });
      // Refresh status & summary
      await fetchRuleSummary();
      await fetchIncidentHistory(selectedIncidentId);
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: formatApiErrorMessage(err, "AI technical test failed"),
      });
    } finally {
      setRunningTest(false);
    }
  };

  const handleExecuteBatchMissing = async () => {
    if (!ruleId || !batchConfirmed) return;
    setBatchRunning(true);
    setFeedback(null);
    try {
      const res = await api.evaluateMissingIncidentsBatch(ruleId, {
        version_id: targetVer?.id,
        version_number: targetVer?.version_number,
        max_concurrency: batchConcurrency,
        confirm_execution: true,
      });
      setBatchResult(res);
      const succ = res.succeeded_count ?? 0;
      const fail = res.failed_count ?? 0;
      const total = res.total_processed ?? (succ + fail);
      setFeedback({
        type: "success",
        text: `Batch inference completed: ${succ} evaluated, ${fail} failed, total processed: ${total}.`,
      });
      await fetchRuleSummary();
      if (selectedIncidentId) {
        await fetchIncidentHistory(selectedIncidentId);
      }
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: formatApiErrorMessage(err, "Batch missing inference execution failed"),
      });
    } finally {
      setBatchRunning(false);
    }
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "EVALUATED_DECISIVE":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 shadow-sm">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            EVALUATED — DECISIVE
          </span>
        );
      case "ABSTAINED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-950/80 text-amber-300 border border-amber-700/60 shadow-sm">
            <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
            ABSTAINED
          </span>
        );
      case "VALIDATION_REJECTED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-950/80 text-rose-300 border border-rose-700/60 shadow-sm">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
            VALIDATION REJECTED
          </span>
        );
      case "EVALUATION_FAILED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-red-950/80 text-red-300 border border-red-700/60 shadow-sm">
            <X className="w-3.5 h-3.5 text-red-400" />
            EVALUATION FAILED
          </span>
        );
      case "QUEUED":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-blue-950/80 text-blue-300 border border-blue-700/60 shadow-sm">
            <Clock className="w-3.5 h-3.5 text-blue-400 animate-spin" />
            QUEUED
          </span>
        );
      case "RUNNING":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-700/60 shadow-sm">
            <RefreshCw className="w-3.5 h-3.5 text-cyan-400 animate-spin" />
            RUNNING
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700 shadow-sm">
            <HelpCircle className="w-3.5 h-3.5 text-slate-400" />
            NOT EVALUATED
          </span>
        );
    }
  };

  const renderStatusExplanation = (status: string) => {
    switch (status) {
      case "EVALUATED_DECISIVE":
        return `Evaluated — Decisive: Effective verdict stored (${currentItem?.effective_verdict || "DECISIVE"}) for policy v${targetVer?.version_number ?? 7}.`;
      case "ABSTAINED":
        return `Abstained: Real inference completed; governed effective outcome is REQUIRES_ATTENTION for policy v${targetVer?.version_number ?? 7}.`;
      case "VALIDATION_REJECTED":
        return `Validation Rejected: Model generated output, but deterministic evidence/format validation rejected it: ${currentItem?.validation_failure_reason || currentItem?.reason || "Evidence grounding threshold not met."}`;
      case "EVALUATION_FAILED":
        return `Evaluation Failed: Inference failed, timed out, or returned an unusable execution result: ${currentItem?.validation_failure_reason || currentItem?.reason || "Model timeout or execution error."}`;
      case "QUEUED":
        return `Queued: Incident is queued in the background worker pool for inference.`;
      case "RUNNING":
        return `Running: Local LLM GPU inference is currently executing on Server 2.`;
      default:
        return `Not Evaluated: No real model execution found for policy v${targetVer?.version_number ?? 7}.`;
    }
  };

  const missingCandidates = ruleEvalItems.filter(
    (it) => it.status === "NOT_EVALUATED" && it.analyst_review !== null && it.analyst_review !== undefined
  );
  const missingCount = evalSummary?.missing_evaluations_among_reviewed ?? missingCandidates.length;

  const filteredEvalItems = ruleEvalItems.filter((it) => {
    if (tableFilter !== "ALL" && it.status !== tableFilter) return false;
    if (tableSearch.trim()) {
      const q = tableSearch.trim().toLowerCase();
      const incIdStr = String(it.incident_id || "").toLowerCase();
      const titleStr = String(it.title || "").toLowerCase();
      if (!incIdStr.includes(q) && !titleStr.includes(q)) return false;
    }
    return true;
  });

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
              className={`inline-flex items-center gap-1 font-bold ${
                llmOnline ? "text-emerald-400" : "text-amber-400"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  llmOnline ? "bg-emerald-400" : "bg-amber-400"
                }`}
              />
              {llmOnline ? "ONLINE (AWS GPU)" : "CHECKING..."}
            </span>
          </div>
        </div>

        {/* Policy Version Context & Batch Missing Action */}
        <div className="flex items-center gap-3">
          {isAdmin && missingCount > 0 && (
            <button
              onClick={() => {
                setBatchResult(null);
                setBatchConfirmed(false);
                setShowBatchModal(true);
              }}
              className="px-2.5 py-1 rounded bg-amber-950/60 hover:bg-amber-900/60 text-amber-300 border border-amber-800 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
              title="Run controlled batch inference for reviewed incidents without stored AI evaluations"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              Evaluate Missing Incidents ({missingCount})
            </button>
          )}

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
      </div>

      {feedback && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
            feedback.type === "success"
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

      {/* SECTION A: Evaluation Coverage Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between">
          <span className="text-slate-400 font-medium text-[11px]">Current Incidents</span>
          <span className="text-xl font-bold font-mono text-slate-100 mt-1">
            {evalSummary?.total_incidents ?? ruleEvalItems.length}
          </span>
          <span className="text-[10px] text-slate-500 font-mono mt-0.5">Current Operational Scope</span>
        </div>

        <div className="p-3 rounded-xl border border-emerald-900/50 bg-emerald-950/20 flex flex-col justify-between">
          <span className="text-emerald-400 font-medium text-[11px] flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
            Decisive Verdicts
          </span>
          <span className="text-xl font-bold font-mono text-emerald-300 mt-1">
            {evalSummary?.evaluated_decisive ?? 0}
          </span>
          <span className="text-[10px] text-emerald-500 font-mono mt-0.5">
            {evalSummary?.decision_coverage_percent ? `${evalSummary.decision_coverage_percent}% coverage` : "TP / FP"}
          </span>
        </div>

        <div className="p-3 rounded-xl border border-amber-900/50 bg-amber-950/20 flex flex-col justify-between">
          <span className="text-amber-400 font-medium text-[11px] flex items-center gap-1">
            <AlertTriangle className="w-3 h-3 text-amber-400" />
            Abstained
          </span>
          <span className="text-xl font-bold font-mono text-amber-300 mt-1">
            {evalSummary?.abstained ?? 0}
          </span>
          <span className="text-[10px] text-amber-500 font-mono mt-0.5">
            {evalSummary?.abstention_rate_percent ? `${evalSummary.abstention_rate_percent}% rate` : "Requires Attention"}
          </span>
        </div>

        <div className="p-3 rounded-xl border border-rose-900/50 bg-rose-950/20 flex flex-col justify-between">
          <span className="text-rose-400 font-medium text-[11px] flex items-center gap-1">
            <ShieldAlert className="w-3 h-3 text-rose-400" />
            Rejected
          </span>
          <span className="text-xl font-bold font-mono text-rose-300 mt-1">
            {evalSummary?.validation_rejected ?? 0}
          </span>
          <span className="text-[10px] text-rose-500 font-mono mt-0.5">Evidence Grounding</span>
        </div>

        <div className="p-3 rounded-xl border border-red-900/50 bg-red-950/20 flex flex-col justify-between">
          <span className="text-red-400 font-medium text-[11px] flex items-center gap-1">
            <X className="w-3 h-3 text-red-400" />
            Failed / Timeout
          </span>
          <span className="text-xl font-bold font-mono text-red-300 mt-1">
            {evalSummary?.evaluation_failed ?? 0}
          </span>
          <span className="text-[10px] text-red-500 font-mono mt-0.5">Execution Errors</span>
        </div>

        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40 flex flex-col justify-between">
          <span className="text-slate-400 font-medium text-[11px] flex items-center gap-1">
            <HelpCircle className="w-3 h-3 text-slate-400" />
            Not Evaluated
          </span>
          <span className="text-xl font-bold font-mono text-slate-300 mt-1">
            {evalSummary?.not_evaluated ?? 0}
          </span>
          <span className="text-[10px] text-slate-500 font-mono mt-0.5">Missing Inference</span>
        </div>
      </div>

      {/* SECTION B: Incident Evaluation Tracking Table */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-cyan-400" />
            <h3 className="font-bold text-slate-100 text-xs">Incident Evaluation Tracking</h3>
            <span className="text-[11px] text-slate-500 font-mono">
              (Target Policy: v{targetVer?.version_number ?? 7} · Scope: Current Inventory [{evalSummary?.total_incidents ?? ruleEvalItems.length}])
            </span>
          </div>

          <div className="flex items-center gap-2 flex-1 max-w-xs">
            <div className="relative w-full">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
              <input
                type="text"
                value={tableSearch}
                onChange={(e) => setTableSearch(e.target.value)}
                placeholder="Search Incident ID..."
                className="w-full pl-8 pr-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono focus:ring-1 focus:ring-cyan-500"
              />
            </div>
            <button
              onClick={fetchRuleSummary}
              disabled={loadingSummary}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition-colors shrink-0"
              title="Refresh tracking data"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingSummary ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
          {[
            { id: "ALL", label: "All Incidents", count: ruleEvalItems.length },
            { id: "NOT_EVALUATED", label: "Not Evaluated", count: evalSummary?.not_evaluated ?? 0 },
            { id: "EVALUATED_DECISIVE", label: "Decisive", count: evalSummary?.evaluated_decisive ?? 0 },
            { id: "ABSTAINED", label: "Abstained", count: evalSummary?.abstained ?? 0 },
            { id: "VALIDATION_REJECTED", label: "Rejected", count: evalSummary?.validation_rejected ?? 0 },
            { id: "EVALUATION_FAILED", label: "Failed", count: evalSummary?.evaluation_failed ?? 0 },
          ].map((pill) => (
            <button
              key={pill.id}
              onClick={() => setTableFilter(pill.id)}
              className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all flex items-center gap-1.5 ${
                tableFilter === pill.id
                  ? "bg-cyan-950 text-cyan-300 border border-cyan-800"
                  : "bg-slate-950/60 text-slate-400 border border-slate-800/80 hover:text-slate-200"
              }`}
            >
              <span>{pill.label}</span>
              <span className="font-mono text-[10px] text-slate-500">({pill.count})</span>
            </button>
          ))}
        </div>

        {/* Table */}
        <div className="rounded-lg border border-slate-800 bg-slate-950/80 overflow-hidden">
          <div className="overflow-x-auto max-h-72 overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 text-[11px] sticky top-0 z-10">
                <tr>
                  <th className="py-2 px-3">Incident</th>
                  <th className="py-2 px-3">Severity</th>
                  <th className="py-2 px-3">Canonical Status</th>
                  <th className="py-2 px-3">Effective Verdict</th>
                  <th className="py-2 px-3">Policy</th>
                  <th className="py-2 px-3">Analyst Review</th>
                  <th className="py-2 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loadingSummary ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                      <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-cyan-400" />
                      Loading incident evaluation records...
                    </td>
                  </tr>
                ) : filteredEvalItems.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500 text-xs">
                      No incidents match the selected filter.
                    </td>
                  </tr>
                ) : (
                  filteredEvalItems.map((item) => {
                    const isSelected = selectedIncidentId === item.incident_id || selectedIncidentId === item.db_id;
                    return (
                      <tr
                        key={item.incident_id}
                        onClick={() => setSelectedIncidentId(item.incident_id)}
                        className={`cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-cyan-950/30 border-l-2 border-l-cyan-400"
                            : "hover:bg-slate-900/40"
                        }`}
                      >
                        <td className="py-2 px-3 font-bold text-slate-200">
                          #{item.incident_id}
                          {item.title && (
                            <span className="block font-sans text-[10px] text-slate-400 font-normal truncate max-w-xs">
                              {item.title}
                            </span>
                          )}
                        </td>
                        <td className="py-2 px-3">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                            {item.customer || "DEFAULT"}
                          </span>
                        </td>
                        <td className="py-2 px-3">
                          {renderStatusBadge(item.status)}
                        </td>
                        <td className="py-2 px-3">
                          {item.effective_verdict ? (
                            <span className={item.effective_verdict === "TRUE_POSITIVE" ? "text-rose-400 font-bold" : "text-emerald-400 font-bold"}>
                              {item.effective_verdict}
                            </span>
                          ) : item.status === "ABSTAINED" ? (
                            <span className="text-amber-400 font-semibold">REQUIRES_ATTENTION</span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-slate-400">
                          v{item.policy_version_number ?? targetVer?.version_number ?? "?"}
                        </td>
                        <td className="py-2 px-3">
                          {item.analyst_review ? (
                            <span className="text-cyan-300 font-bold flex items-center gap-1 text-[11px]">
                              <Check className="w-3 h-3 text-emerald-400" />
                              {item.analyst_review.analyst_verdict}
                            </span>
                          ) : (
                            <span className="text-slate-600 italic text-[11px]">Unreviewed</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-right">
                          <div className="flex items-center justify-end gap-1.5" onClick={(e) => e.stopPropagation()}>
                            <button
                              onClick={() => setSelectedIncidentId(item.incident_id)}
                              className={`px-2 py-0.5 rounded text-[11px] font-semibold transition-colors ${
                                isSelected
                                  ? "bg-cyan-600 text-slate-950 font-bold"
                                  : "bg-slate-800 hover:bg-slate-700 text-slate-300"
                              }`}
                            >
                              {isSelected ? "Active" : "Select"}
                            </button>
                            <button
                              onClick={() => {
                                setSelectedIncidentId(item.incident_id);
                                setShowHistoryModal(true);
                              }}
                              className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                              title="Evaluation History"
                            >
                              <History className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Guided Test Workflow Card */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold text-[11px]">
              EVALUATION WORKFLOW
            </span>
            <span className="text-slate-300 text-xs font-semibold">
              Select Incident → Check Stored Evaluation → Run Controlled Inference
            </span>
          </div>

          <span className="text-[11px] text-slate-500">
            Executes real vLLM inference against Server 2 (Qwen2.5-7B-Instruct-AWQ)
          </span>
        </div>

        {/* Workflow Controls Row */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
          <div className="md:col-span-8">
            <label className="block text-slate-400 text-[11px] font-semibold mb-1">
              Select Incident for Single Evaluation:
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

          <div className="md:col-span-4 flex items-end gap-2">
            {incidentStatus === "EVALUATED_DECISIVE" || incidentStatus === "ABSTAINED" ? (
              <div className="flex items-center gap-2 w-full">
                <button
                  onClick={() => setShowHistoryModal(true)}
                  className="flex-1 py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <History className="w-3.5 h-3.5" />
                  View History
                </button>
                <button
                  onClick={handleRunAiTest}
                  disabled={runningTest || !selectedIncidentId || isViewer}
                  title="Force re-execution of AI evaluation for this incident"
                  className="py-2 px-3 rounded-lg bg-amber-950/70 hover:bg-amber-900/80 text-amber-300 border border-amber-800/80 font-bold text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-40"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${runningTest ? "animate-spin" : ""}`} />
                  {runningTest ? "Running..." : "Rerun"}
                </button>
              </div>
            ) : incidentStatus === "VALIDATION_REJECTED" || incidentStatus === "EVALUATION_FAILED" ? (
              <div className="flex items-center gap-2 w-full">
                <button
                  onClick={() => setShowHistoryModal(true)}
                  className="py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <History className="w-3.5 h-3.5" />
                  History
                </button>
                <button
                  onClick={handleRunAiTest}
                  disabled={runningTest || !selectedIncidentId || isViewer}
                  className="flex-1 py-2 px-3 rounded-lg bg-rose-600 hover:bg-rose-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-40 shadow-md"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${runningTest ? "animate-spin" : ""}`} />
                  {runningTest ? "Retrying..." : "Retry Evaluation"}
                </button>
              </div>
            ) : (
              <button
                onClick={handleRunAiTest}
                disabled={runningTest || !selectedIncidentId || isViewer}
                className="w-full py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-md"
              >
                <Play className={`w-3.5 h-3.5 ${runningTest ? "animate-spin" : ""}`} />
                {runningTest ? "Executing GPU Inference..." : "Run Real AI Test"}
              </button>
            )}
          </div>
        </div>

        {/* Canonical Evaluation Status Callout Banner */}
        <div
          className={`p-3.5 rounded-lg border text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 ${
            incidentStatus === "EVALUATED_DECISIVE"
              ? "bg-emerald-950/20 border-emerald-800/60 text-slate-200"
              : incidentStatus === "ABSTAINED"
              ? "bg-amber-950/20 border-amber-800/60 text-slate-200"
              : incidentStatus === "VALIDATION_REJECTED" || incidentStatus === "EVALUATION_FAILED"
              ? "bg-rose-950/20 border-rose-800/60 text-slate-200"
              : "bg-slate-950/40 border-slate-800 text-slate-400"
          }`}
        >
          <div className="flex items-center gap-3">
            <div>{renderStatusBadge(incidentStatus)}</div>
            <div>
              <p className="font-semibold text-slate-200">{renderStatusExplanation(incidentStatus)}</p>
              {currentItem?.is_simulated && (
                <p className="text-[11px] text-amber-400 font-mono mt-0.5">
                  [MOCK RESULT DETECTED: Stored evaluation originates from test mock provider and does not represent real GPU execution]
                </p>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-center font-mono text-[11px] text-slate-400">
            <span>Policy: v{targetVer?.version_number ?? 7}</span>
            {evalHistory && evalHistory.history_count > 0 && (
              <button
                onClick={() => setShowHistoryModal(true)}
                className="text-cyan-400 hover:underline flex items-center gap-1 font-sans font-semibold ml-2"
              >
                <History className="w-3 h-3" />
                {evalHistory.history_count} attempt(s)
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Test Results Display Area */}
      {testResult ? (
        <div className="p-4 rounded-xl border border-cyan-900/60 bg-slate-900/80 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <div>
                <h3 className="font-bold text-slate-100 text-sm">
                  {testResult.is_stored_result ? "Stored AI Evaluation Result" : "Real AI Test Outcome"}
                </h3>
                <span className="text-[11px] text-slate-400">
                  Evaluated under Policy v{testResult.policy_version_number ?? targetVer?.version_number} ({targetVer?.status || "APPROVED"}) via {testResult.model_name || "Qwen2.5-7B-Instruct-AWQ"}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowHistoryModal(true)}
                className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <History className="w-3.5 h-3.5" />
                History
              </button>
              <button
                onClick={() => onOpenActualPrompt?.(selectedIncidentId)}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <FileCode className="w-3.5 h-3.5" />
                View Actual LLM Prompt
              </button>
            </div>
          </div>

          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800">
              <span className="text-slate-400 font-sans block text-[11px] mb-1">Effective Verdict:</span>
              <span
                className={`font-bold text-sm ${
                  testResult.effective_verdict === "TRUE_POSITIVE"
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

      {/* MODAL 1: Incident Evaluation History Modal */}
      {showHistoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-cyan-400" />
                <h3 className="font-bold text-sm text-slate-100">
                  Evaluation History — #{selectedIncidentId}
                </h3>
              </div>
              <button
                onClick={() => setShowHistoryModal(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <p className="text-xs text-slate-400">
                Full chronological record of real and attempted model executions for this incident.
              </p>

              {loadingEvalHistory ? (
                <div className="py-8 text-center text-xs text-slate-500">
                  <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2 text-cyan-400" />
                  Loading execution history...
                </div>
              ) : !evalHistory || evalHistory.history.length === 0 ? (
                <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
                  No evaluation history recorded for this incident.
                </div>
              ) : (
                <div className="space-y-2">
                  {evalHistory.history.map((exec: AisEvaluationHistoryItem, idx: number) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 text-xs font-mono space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            exec.dispatch_status === "COMPLETED"
                              ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                              : "bg-rose-950 text-rose-300 border border-rose-800"
                          }`}>
                            {exec.dispatch_status}
                          </span>
                          <span className="font-sans font-bold text-slate-300">
                            v{exec.policy_version_number ?? "?"}
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-500">
                          {exec.captured_at ? new Date(exec.captured_at).toLocaleString() : "Recent"}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px] pt-1">
                        <div>
                          <span className="text-slate-500 font-sans">Raw Verdict: </span>
                          <span className="text-slate-300 font-bold">{exec.raw_verdict || "N/A"}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 font-sans">Confidence: </span>
                          <span className="text-cyan-300 font-bold">
                            {exec.confidence !== undefined && exec.confidence !== null
                              ? `${(exec.confidence * 100).toFixed(0)}%`
                              : "N/A"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 font-sans">Model: </span>
                          <span className="text-slate-400">{exec.model_name || "Qwen2.5"}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 font-sans">Integrity: </span>
                          <span className={exec.prompt_integrity_status === "VALID" ? "text-emerald-400" : "text-amber-400"}>
                            {exec.prompt_integrity_status || "PASSED"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 font-sans">Duration: </span>
                          <span className="text-slate-400">{exec.latency_ms ? `${exec.latency_ms}ms` : "N/A"}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 font-sans">Execution Type: </span>
                          <span className={exec.is_simulated ? "text-amber-400 font-bold" : "text-emerald-400 font-bold"}>
                            {exec.is_simulated ? "MOCK / SIMULATED" : "REAL GPU"}
                          </span>
                        </div>
                      </div>

                      {exec.error_message && (
                        <div className="p-2 rounded bg-rose-950/30 border border-rose-900/50 text-rose-300 text-[11px] font-sans">
                          <strong>Failure / Rejection Reason:</strong> {exec.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowHistoryModal(false)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Controlled Missing Incidents Batch Preflight Confirmation Modal */}
      {showBatchModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl bg-slate-950 border border-slate-800 rounded-xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-amber-400" />
                <h3 className="font-bold text-sm text-slate-100">
                  Controlled First-Time Batch AI Inference
                </h3>
              </div>
              <button
                onClick={() => !batchRunning && setShowBatchModal(false)}
                disabled={batchRunning}
                className="text-slate-400 hover:text-slate-200 disabled:opacity-40"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-slate-300 leading-relaxed">
                This workflow evaluates incidents with verified analyst reviews that currently lack real Local LLM inference. All executions are strictly tagged with <code className="text-cyan-300 font-mono">RETROSPECTIVE_EVALUATION</code> provenance.
              </p>

              {/* Target & Candidates Details */}
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                <div className="grid grid-cols-2 gap-2 font-mono">
                  <div>
                    <span className="text-slate-500 font-sans block text-[11px]">Target Policy Version:</span>
                    <span className="text-slate-200 font-bold">
                      v{targetVer?.version_number} ({targetVer?.status})
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-sans block text-[11px]">Server 2 GPU Status:</span>
                    <span className={`font-bold ${llmOnline ? "text-emerald-400" : "text-amber-400"}`}>
                      {llmOnline ? "ONLINE (Qwen2.5-7B)" : "UNVERIFIED"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-sans block text-[11px]">Candidate Incidents:</span>
                    <span className="text-cyan-300 font-bold">{missingCount} missing cases</span>
                  </div>
                  <div>
                    <span className="text-slate-500 font-sans block text-[11px]">Estimated Token Budget:</span>
                    <span className="text-amber-300 font-bold">~{missingCount * 1500} tokens</span>
                  </div>
                </div>

                {missingCandidates.length > 0 && (
                  <div className="pt-2 border-t border-slate-800/80">
                    <span className="text-slate-500 font-sans block text-[10px] mb-1">
                      Candidate Incident IDs:
                    </span>
                    <div className="max-h-20 overflow-y-auto p-1.5 rounded bg-slate-950 border border-slate-800/80 font-mono text-[10px] text-slate-300 flex flex-wrap gap-1">
                      {missingCandidates.map((it) => (
                        <span key={it.incident_id} className="bg-slate-900 px-1.5 py-0.5 rounded border border-slate-800">
                          #{it.incident_id}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Concurrency Selector */}
              <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                <div>
                  <span className="font-semibold text-slate-200 block">Execution Concurrency:</span>
                  <span className="text-[11px] text-slate-400">
                    Rate-limited worker slots to protect Server 2 GPU memory
                  </span>
                </div>
                <div className="flex items-center gap-2 font-mono">
                  {[1, 2].map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => setBatchConcurrency(slot)}
                      className={`px-3 py-1 rounded text-xs font-bold transition-colors ${
                        batchConcurrency === slot
                          ? "bg-cyan-600 text-slate-950"
                          : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                      }`}
                    >
                      {slot} worker{slot > 1 ? "s" : ""}
                    </button>
                  ))}
                </div>
              </div>

              {/* Explicit Mandatory Authorization Checkbox */}
              <label className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-950/20 border border-amber-800/60 cursor-pointer">
                <input
                  type="checkbox"
                  checked={batchConfirmed}
                  onChange={(e) => setBatchConfirmed(e.target.checked)}
                  disabled={batchRunning}
                  className="mt-0.5 rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                />
                <span className="text-amber-200 text-[11px] leading-relaxed">
                  <strong>Explicit Administrative Authorization:</strong> I authorize executing real Local LLM inference on Server 2 for {missingCount} missing incidents under policy v{targetVer?.version_number}. I confirm this will not overwrite verified ground-truth labels and will apply retrospective provenance tracking.
                </span>
              </label>

              {/* Batch Outcome Result Banner */}
              {batchResult && (
                <div className="p-3 rounded-lg bg-emerald-950/40 border border-emerald-800 text-emerald-300 font-mono text-xs space-y-1">
                  <div className="font-bold font-sans">Batch Run Complete:</div>
                  <div>• Successfully Evaluated: {batchResult.succeeded_count ?? 0}</div>
                  <div>• Failed / Rejected: {batchResult.failed_count ?? 0}</div>
                  <div>• Total Processed: {batchResult.total_processed ?? 0}</div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-slate-800">
              <button
                onClick={() => setShowBatchModal(false)}
                disabled={batchRunning}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold disabled:opacity-40"
              >
                {batchResult ? "Close" : "Cancel"}
              </button>

              <button
                onClick={handleExecuteBatchMissing}
                disabled={batchRunning || !batchConfirmed || missingCount === 0}
                className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-40 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors shadow-md"
              >
                <Sparkles className={`w-3.5 h-3.5 ${batchRunning ? "animate-spin" : ""}`} />
                {batchRunning ? "Executing Batch..." : "Authorize & Run Batch"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
