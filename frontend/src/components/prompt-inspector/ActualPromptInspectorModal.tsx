"use client";

import React, { useState, useEffect } from "react";
import {
  X,
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Info,
  CheckCircle2,
  Copy,
  Download,
  Search,
  RefreshCw,
  Terminal,
  Cpu,
  FileCode,
  Layers,
  Database,
  Lock,
  ExternalLink,
  ChevronDown,
  Sparkles,
  Eye,
  History,
} from "lucide-react";
import {
  api,
  ActualPromptResponse,
  ExecutionHistoryItem,
  RuleCaptureSummaryItem,
} from "@/lib/api";

interface ActualPromptInspectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  incidentId?: string | null;
  ruleId?: string | null;
  ruleName?: string | null;
  versionId?: string | null;
  initialMode?: "capture" | "preview";
}

export function ActualPromptInspectorModal({
  isOpen,
  onClose,
  incidentId: initialIncidentId,
  ruleId,
  ruleName,
  versionId,
  initialMode = "capture",
}: ActualPromptInspectorModalProps) {
  const [activeTab, setActiveTab] = useState<
    "summary" | "system_prompt" | "incident_payload" | "precedents" | "contract" | "technical"
  >("summary");
  const [inspectorMode, setInspectorMode] = useState<"capture" | "preview">(initialMode);
  const [data, setData] = useState<ActualPromptResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchIncidentId, setSearchIncidentId] = useState(initialIncidentId || "");
  const [selectedCaptureId, setSelectedCaptureId] = useState<string | null>(null);
  const [ruleCaptures, setRuleCaptures] = useState<RuleCaptureSummaryItem[]>([]);
  const [loadingRuleCaptures, setLoadingRuleCaptures] = useState(false);
  const [copySuccess, setCopySuccess] = useState<string | null>(null);
  const [exporting, setExporting] = useState<"json" | "markdown" | null>(null);

  useEffect(() => {
    if (initialIncidentId) {
      setSearchIncidentId(initialIncidentId);
    }
  }, [initialIncidentId]);

  useEffect(() => {
    if (initialMode) {
      setInspectorMode(initialMode);
    }
  }, [initialMode]);

  useEffect(() => {
    if (isOpen) {
      const incToLoad = initialIncidentId || searchIncidentId || undefined;
      if (ruleId) {
        loadRecentRuleCaptures(ruleId, incToLoad);
      }
      if (inspectorMode === "preview" && ruleId) {
        loadPreview(ruleId, versionId || undefined);
      } else if (incToLoad) {
        loadCapture(incToLoad, selectedCaptureId || undefined);
      }
    }
  }, [isOpen, initialIncidentId, ruleId, versionId, inspectorMode]);

  const loadRecentRuleCaptures = async (targetRuleId: string, currentIncidentId?: string) => {
    setLoadingRuleCaptures(true);
    try {
      const captures = await api.getRulePromptCaptures(targetRuleId, 25);
      setRuleCaptures(captures);
      if (!currentIncidentId && captures.length > 0 && inspectorMode !== "preview") {
        const first = captures[0];
        setSearchIncidentId(first.incident_id);
        setSelectedCaptureId(first.capture_id);
        loadCapture(first.incident_id, first.capture_id);
      } else if (!currentIncidentId && captures.length === 0 && inspectorMode !== "preview" && ruleId) {
        loadPreview(ruleId, versionId || undefined);
        setInspectorMode("preview");
      }
    } catch {
      setRuleCaptures([]);
    } finally {
      setLoadingRuleCaptures(false);
    }
  };

  const loadCapture = async (targetIncidentId?: string, captureId?: string) => {
    setLoading(true);
    setError(null);
    try {
      if (targetIncidentId && targetIncidentId.trim()) {
        const res = await api.getActualPromptForIncident(targetIncidentId.trim(), captureId);
        setData(res);
        if (res.capture_id) {
          setSelectedCaptureId(res.capture_id);
        }
      } else if (ruleCaptures.length > 0 && !targetIncidentId) {
        // Default to first captured incident if available
        const first = ruleCaptures[0];
        setSearchIncidentId(first.incident_id);
        const res = await api.getActualPromptForIncident(first.incident_id, first.capture_id);
        setData(res);
        setSelectedCaptureId(first.capture_id);
      } else if (ruleId) {
        // If no incident selected and no rule captures found, load live preview
        const res = await api.getPromptPreviewForRule(ruleId, versionId || undefined);
        setData(res);
        setInspectorMode("preview");
      } else {
        setData(null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load actual prompt data");
    } finally {
      setLoading(false);
    }
  };

  const loadPreview = async (targetRuleId: string, targetVersionId?: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getPromptPreviewForRule(targetRuleId, targetVersionId);
      setData(res);
      setInspectorMode("preview");
    } catch (err: any) {
      setError(err.message || "Failed to compile prompt preview");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchIncidentId.trim()) {
      setInspectorMode("capture");
      setSelectedCaptureId(null);
      loadCapture(searchIncidentId.trim());
    }
  };

  const handleSelectExecution = (exec: ExecutionHistoryItem) => {
    setSelectedCaptureId(exec.id);
    loadCapture(exec.incident_id, exec.id);
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopySuccess(label);
    setTimeout(() => setCopySuccess(null), 2500);
  };

  const handleExport = async (format: "json" | "markdown") => {
    if (!data?.execution_summary?.incident_id) return;
    setExporting(format);
    try {
      const { blob, filename } = await api.exportActualPrompt(
        data.execution_summary.incident_id,
        format,
        data.capture_id || undefined
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      alert(`Export failed: ${err.message}`);
    } finally {
      setExporting(null);
    }
  };

  if (!isOpen) return null;

  const renderBanner = () => {
    if (!data) return null;
    if (data.capture_status === "CAPTURED_RUNTIME") {
      const isSim = data.execution_summary?.is_simulated || data.execution_summary?.provider_type === "SIMULATED";
      return (
        <div className="bg-emerald-950/70 border border-emerald-500/50 text-emerald-300 px-4 py-2.5 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 relative shrink-0">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="font-bold text-sm tracking-wide text-white">Captured Runtime Prompt</span>
            <span className="text-xs text-emerald-300/80 border-l border-emerald-500/30 pl-2 ml-1 hidden md:inline">
              Authoritative request payload recorded at Server 1 → Server 2 provider boundary.
            </span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span
              className={`text-[10px] px-2 py-0.5 rounded font-mono uppercase font-bold border ${
                isSim
                  ? "bg-slate-900 text-amber-300 border-amber-800"
                  : "bg-emerald-900/80 text-emerald-200 border-emerald-600"
              }`}
            >
              {isSim ? "Provider: SIMULATED" : "Provider: LOCAL LLM (Live)"}
            </span>
            <span className="text-[11px] font-mono bg-emerald-900/50 text-emerald-200 px-2 py-0.5 rounded border border-emerald-500/30">
              SHA256: {data.technical_details.request_sha256.substring(0, 10)}...
            </span>
          </div>
        </div>
      );
    }

    if (data.capture_status === "HISTORICAL_CAPTURE_UNAVAILABLE") {
      return (
        <div className="bg-amber-950/70 border border-amber-500/50 text-amber-300 px-4 py-2.5 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span className="font-bold text-sm tracking-wide text-white">Historical Capture Unavailable</span>
            <span className="text-xs text-amber-300/80 border-l border-amber-500/30 pl-2 ml-1">
              Evaluated prior to runtime capture deployment; outbound payload was not recorded.
            </span>
          </div>
          <button
            onClick={() => ruleId && loadPreview(ruleId, versionId || undefined)}
            className="text-xs font-semibold px-2.5 py-1 bg-amber-900/60 hover:bg-amber-800 text-amber-100 rounded border border-amber-600 transition"
          >
            View Policy Preview
          </button>
        </div>
      );
    }

    return (
      <div className="bg-sky-950/70 border border-sky-500/50 text-sky-300 px-4 py-2.5 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2 shadow-sm">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-sky-400 shrink-0" />
          <span className="font-bold text-sm tracking-wide text-white">Preview Only (Simulated Specification)</span>
          <span className="text-xs text-sky-300/80 border-l border-sky-500/30 pl-2 ml-1">
            Live compiled specification representation. Not proof of historical runtime execution.
          </span>
        </div>
        <span className="text-[11px] font-mono bg-sky-900/50 text-sky-200 px-2 py-0.5 rounded border border-sky-500/30">
          Status: UNVERIFIED PREVIEW
        </span>
      </div>
    );
  };

  const renderDeliveryBadge = () => {
    if (!data) return null;
    const st = data.delivery_status || data.execution_summary?.dispatch_status || "COMPLETED";
    if (st === "COMPLETED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-950 border border-emerald-500/50 text-emerald-300">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          Delivery: Completed
        </span>
      );
    }
    if (st === "SEND_ATTEMPTED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-cyan-950 border border-cyan-500/50 text-cyan-300">
          <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          Delivery: Send Attempted
        </span>
      );
    }
    if (st === "FAILED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-950 border border-rose-500/50 text-rose-300">
          <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
          Delivery: Failed
        </span>
      );
    }
    if (st === "NOT_DISPATCHED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-amber-950 border border-amber-500/50 text-amber-300">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
          Delivery: Not Dispatched (Safety Gate)
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-sky-950 border border-sky-500/50 text-sky-300">
        <Sparkles className="w-3.5 h-3.5 text-sky-400" />
        Delivery: Preview Only
      </span>
    );
  };

  const renderIntegrityBadge = () => {
    if (!data) return null;
    const st = data.integrity_status;
    if (st === "VERIFIED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-950 border border-emerald-500/60 text-emerald-300">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          Prompt Integrity: Verified
        </span>
      );
    }
    if (st === "MISMATCH") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold bg-rose-950 border border-rose-500/70 text-rose-300 animate-pulse">
          <ShieldAlert className="w-3.5 h-3.5 text-rose-400" />
          Prompt Integrity: Mismatch Detected
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 border border-slate-600 text-slate-300">
        <Shield className="w-3.5 h-3.5 text-slate-400" />
        Prompt Integrity: Unverified
      </span>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-sm p-2 sm:p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 w-full max-w-6xl rounded-xl shadow-2xl flex flex-col max-h-[94vh] overflow-hidden">
        {/* Modal Header */}
        <div className="px-4 sm:px-6 py-3.5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950/80">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/30 rounded-lg text-indigo-400 shrink-0">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base sm:text-lg font-bold text-white tracking-wide">
                  Actual LLM Prompt Inspector
                </h2>
                <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono font-semibold">
                  AIS 2.0
                </span>
                {data?.is_redacted && (
                  <span className="text-[10px] bg-amber-950 text-amber-300 border border-amber-800 px-2 py-0.5 rounded font-semibold">
                    ROLE REDACTED
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Authoritative instructions and telemetry transmitted from Server 1 to Local LLM (Server 2)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            {/* View Mode Toggle: Runtime Captures vs Compiled Preview */}
            {ruleId && (
              <div className="inline-flex rounded-lg border border-slate-700 bg-slate-950 p-0.5 text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setInspectorMode("capture");
                    loadCapture(searchIncidentId || initialIncidentId || undefined);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold transition ${
                    inspectorMode === "capture"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Runtime Captures
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setInspectorMode("preview");
                    loadPreview(ruleId, versionId || undefined);
                  }}
                  className={`px-2.5 py-1 rounded-md font-semibold transition ${
                    inspectorMode === "preview"
                      ? "bg-sky-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Compiled Preview
                </button>
              </div>
            )}

            {/* Quick Incident Lookup Bar */}
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-1.5">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Incident ID (e.g. INC-001)"
                  value={searchIncidentId}
                  onChange={(e) => setSearchIncidentId(e.target.value)}
                  className="bg-slate-800/90 border border-slate-700 text-xs text-slate-200 rounded-md pl-8 pr-2.5 py-1.5 focus:outline-none focus:border-indigo-500 w-40 sm:w-52 font-mono"
                />
              </div>
              <button
                type="submit"
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-2.5 py-1.5 rounded-md font-semibold transition shrink-0"
              >
                Inspect
              </button>
            </form>

            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
              title="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Rule Recent Captures Selector Strip */}
        {ruleCaptures.length > 0 && inspectorMode === "capture" && (
          <div className="px-4 sm:px-6 py-2 bg-slate-950/60 border-b border-slate-800 flex items-center gap-2 overflow-x-auto text-xs">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1">
              <History className="w-3 h-3 text-cyan-400" /> Recent Cases:
            </span>
            <div className="flex items-center gap-1.5 flex-nowrap">
              {ruleCaptures.slice(0, 8).map((rc) => (
                <button
                  key={rc.capture_id}
                  type="button"
                  onClick={() => {
                    setSearchIncidentId(rc.incident_id);
                    setSelectedCaptureId(rc.capture_id);
                    loadCapture(rc.incident_id, rc.capture_id);
                  }}
                  className={`px-2 py-0.5 rounded text-[11px] font-mono shrink-0 border transition ${
                    selectedCaptureId === rc.capture_id || searchIncidentId === rc.incident_id
                      ? "bg-indigo-950 border-indigo-500 text-indigo-300 font-bold"
                      : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {rc.incident_id}
                  {rc.verdict && (
                    <span
                      className={`ml-1 text-[9px] px-1 rounded ${
                        rc.verdict === "TRUE_POSITIVE"
                          ? "text-rose-400"
                          : rc.verdict === "FALSE_POSITIVE"
                          ? "text-emerald-400"
                          : "text-amber-400"
                      }`}
                    >
                      {rc.verdict === "TRUE_POSITIVE" ? "TP" : rc.verdict === "FALSE_POSITIVE" ? "FP" : "REQ"}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Status Banner */}
        <div className="px-4 sm:px-6 pt-3 pb-2 bg-slate-950/40 border-b border-slate-800/80">
          {renderBanner()}
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-400 mb-3" />
              <p className="text-sm font-medium">Fetching authoritative request payload from provider boundary...</p>
            </div>
          )}

          {error && (
            <div className="bg-rose-950/40 border border-rose-500/40 rounded-lg p-4 text-rose-300 text-sm flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Unable to load actual prompt data</p>
                <p className="text-xs text-rose-400 mt-1">{error}</p>
                {ruleId && (
                  <button
                    onClick={() => loadPreview(ruleId, versionId || undefined)}
                    className="mt-2 text-xs font-semibold text-sky-400 hover:text-sky-300 underline"
                  >
                    Open Compiled Prompt Preview instead
                  </button>
                )}
              </div>
            </div>
          )}

          {!loading && !error && data && (
            <>
              {/* L1 Engineer Plain-Language Explanation Panel */}
              <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4 space-y-3 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-700/60 pb-2.5">
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-indigo-400 shrink-0" />
                    <h3 className="text-sm font-bold text-slate-100">
                      L1 Investigation &amp; Evidence Summary
                    </h3>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {renderDeliveryBadge()}
                    {renderIntegrityBadge()}
                  </div>
                </div>

                <p className="text-xs text-slate-200 leading-relaxed bg-slate-900/80 p-3 rounded-lg border border-slate-800 font-sans">
                  <strong className="text-white">Explanation:</strong> {data.l1_explanation.headline}
                </p>

                {/* 5 Highlights Grid */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2.5 pt-1">
                  <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block font-medium">Policy Version</span>
                    <span className="text-xs font-bold text-slate-100 block truncate mt-0.5">
                      {data.l1_explanation.policy_version_used}
                    </span>
                  </div>

                  <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block font-medium">Mandatory Evidence</span>
                    <span
                      className={`text-xs font-bold block mt-0.5 ${
                        data.l1_explanation.mandatory_evidence_available
                          ? "text-emerald-400"
                          : "text-amber-400"
                      }`}
                    >
                      {data.l1_explanation.mandatory_evidence_available
                        ? "Available & Verified"
                        : "Missing / Incomplete"}
                    </span>
                  </div>

                  <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block font-medium">RAG Precedents</span>
                    <span className="text-xs font-bold text-slate-100 block mt-0.5">
                      {data.l1_explanation.historical_precedents_included > 0
                        ? `${data.l1_explanation.historical_precedents_included} Included`
                        : "None (Zero RAG)"}
                    </span>
                  </div>

                  <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block font-medium">Verdict Returned</span>
                    <span
                      className={`text-xs font-bold block mt-0.5 ${
                        data.l1_explanation.verdict_returned === "TRUE_POSITIVE"
                          ? "text-rose-400"
                          : data.l1_explanation.verdict_returned === "FALSE_POSITIVE"
                          ? "text-emerald-400"
                          : "text-amber-400"
                      }`}
                    >
                      {data.l1_explanation.verdict_returned || "UNKNOWN"}
                    </span>
                  </div>

                  <div className="bg-slate-900/90 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block font-medium">Policy Approval</span>
                    <span
                      className={`text-xs font-bold block mt-0.5 ${
                        data.l1_explanation.prompt_matches_approved_policy
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }`}
                    >
                      {data.l1_explanation.prompt_matches_approved_policy
                        ? "Approved Baseline"
                        : "Unapproved Policy"}
                    </span>
                  </div>
                </div>

                <div className="text-[11px] text-slate-400 italic pt-1">
                  * Note: Prompt Integrity evaluates cryptographic SHA-256 matching and policy provenance. It is independent of delivery status and verdict correctness.
                </div>
              </div>

              {/* Execution Attempt History Selector (Task 3) */}
              {data.available_executions && data.available_executions.length > 1 && (
                <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs">
                  <div className="flex items-center gap-2">
                    <History className="w-4 h-4 text-indigo-400 shrink-0" />
                    <span className="font-semibold text-slate-200">
                      Multiple Execution Attempts Detected ({data.available_executions.length} recorded runs):
                    </span>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {data.available_executions.map((ex) => {
                      const isSelected = ex.id === data.capture_id;
                      return (
                        <button
                          key={ex.id}
                          type="button"
                          onClick={() => handleSelectExecution(ex)}
                          className={`px-2.5 py-1 rounded text-xs font-mono font-medium border transition ${
                            isSelected
                              ? "bg-indigo-600 text-white border-indigo-400 shadow-sm"
                              : "bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800"
                          }`}
                        >
                          Run #{ex.attempt_number} ({ex.dispatch_status})
                          {ex.is_active_verdict && " ★ Active"}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* 6 Tabs Navigation */}
              <div className="border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-2">
                <nav className="flex space-x-1 sm:space-x-2 overflow-x-auto">
                  <button
                    onClick={() => setActiveTab("summary")}
                    className={`px-3 py-2 text-xs font-bold rounded-t-lg transition border-b-2 whitespace-nowrap ${
                      activeTab === "summary"
                        ? "border-indigo-500 text-indigo-300 bg-slate-800/60"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    1. Execution Summary
                  </button>
                  <button
                    onClick={() => setActiveTab("system_prompt")}
                    className={`px-3 py-2 text-xs font-bold rounded-t-lg transition border-b-2 whitespace-nowrap ${
                      activeTab === "system_prompt"
                        ? "border-indigo-500 text-indigo-300 bg-slate-800/60"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    2. System Prompt
                  </button>
                  <button
                    onClick={() => setActiveTab("incident_payload")}
                    className={`px-3 py-2 text-xs font-bold rounded-t-lg transition border-b-2 whitespace-nowrap ${
                      activeTab === "incident_payload"
                        ? "border-indigo-500 text-indigo-300 bg-slate-800/60"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    3. Incident Payload
                  </button>
                  <button
                    onClick={() => setActiveTab("precedents")}
                    className={`px-3 py-2 text-xs font-bold rounded-t-lg transition border-b-2 whitespace-nowrap ${
                      activeTab === "precedents"
                        ? "border-indigo-500 text-indigo-300 bg-slate-800/60"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    4. Precedents ({data.rag_precedents?.length || 0})
                  </button>
                  <button
                    onClick={() => setActiveTab("contract")}
                    className={`px-3 py-2 text-xs font-bold rounded-t-lg transition border-b-2 whitespace-nowrap ${
                      activeTab === "contract"
                        ? "border-indigo-500 text-indigo-300 bg-slate-800/60"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    5. Output Contract
                  </button>
                  <button
                    onClick={() => setActiveTab("technical")}
                    className={`px-3 py-2 text-xs font-bold rounded-t-lg transition border-b-2 whitespace-nowrap ${
                      activeTab === "technical"
                        ? "border-indigo-500 text-indigo-300 bg-slate-800/60"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    6. Technical Details
                  </button>
                </nav>

                {/* Quick Copy & Export Bar */}
                <div className="flex items-center gap-2 pb-1 shrink-0">
                  {copySuccess && (
                    <span className="text-xs text-emerald-400 flex items-center gap-1 font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {copySuccess} copied!
                    </span>
                  )}
                  <button
                    onClick={() =>
                      copyToClipboard(data.system_prompt, "System Prompt")
                    }
                    className="p-1.5 text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded text-xs flex items-center gap-1 border border-slate-700 transition"
                    title="Copy System Prompt"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    Copy Prompt
                  </button>
                  {data.capture_status === "CAPTURED_RUNTIME" && (
                    <>
                      <button
                        onClick={() => handleExport("json")}
                        disabled={exporting !== null}
                        className="px-2 py-1 text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded text-xs flex items-center gap-1 border border-slate-700 transition"
                        title="Download redacted/unredacted JSON dossier"
                      >
                        <Download className="w-3 h-3" />
                        JSON
                      </button>
                      <button
                        onClick={() => handleExport("markdown")}
                        disabled={exporting !== null}
                        className="px-2 py-1 text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded text-xs flex items-center gap-1 border border-slate-700 transition"
                        title="Download structured Markdown audit report"
                      >
                        <Download className="w-3 h-3" />
                        Markdown
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Tab 1: Execution Summary */}
              {activeTab === "summary" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 space-y-2.5">
                      <h4 className="text-xs uppercase font-bold text-indigo-400 tracking-wider">
                        Incident &amp; Policy Provenance
                      </h4>
                      <div className="text-xs space-y-1.5">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Incident ID:</span>
                          <span className="font-mono text-slate-200 font-bold">
                            {data.execution_summary.incident_id}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Rule Name:</span>
                          <span className="text-slate-200 font-medium truncate max-w-[260px]">
                            {data.execution_summary.rule_name}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Rule ID:</span>
                          <span className="font-mono text-slate-400 text-[11px]">
                            {data.execution_summary.rule_id}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Policy Version:</span>
                          <span className="text-slate-200 font-semibold">
                            v{data.execution_summary.policy_version_number || "None"} (
                            {data.execution_summary.policy_status})
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Policy Source:</span>
                          <span className="text-slate-300">
                            {data.execution_summary.policy_source}
                          </span>
                        </div>
                        {data.execution_summary.policy_snapshot_hash && (
                          <div className="flex justify-between">
                            <span className="text-slate-400">Policy Hash:</span>
                            <span className="font-mono text-slate-400 text-[10px]">
                              {data.execution_summary.policy_snapshot_hash.substring(0, 16)}...
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="bg-slate-950/70 border border-slate-800 rounded-lg p-4 space-y-2.5">
                      <h4 className="text-xs uppercase font-bold text-indigo-400 tracking-wider">
                        Execution &amp; Provider Dispatch
                      </h4>
                      <div className="text-xs space-y-1.5">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Model Name:</span>
                          <span className="font-mono text-slate-200 font-bold">
                            {data.execution_summary.model_name}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Provider:</span>
                          <span className="text-slate-200 font-semibold">
                            {data.execution_summary.provider_type}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Delivery Status:</span>
                          <span
                            className={`font-bold ${
                              data.execution_summary.dispatch_status === "COMPLETED"
                                ? "text-emerald-400"
                                : data.execution_summary.dispatch_status === "FAILED"
                                ? "text-rose-400"
                                : "text-amber-400"
                            }`}
                          >
                            {data.execution_summary.dispatch_status}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Attempt Sequence:</span>
                          <span className="text-slate-200">
                            Attempt #{data.execution_summary.attempt_number} (Retry count: {data.execution_summary.retry_count})
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Captured At:</span>
                          <span className="text-slate-300">
                            {new Date(data.execution_summary.captured_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Inference Latency:</span>
                          <span className="text-slate-200 font-mono">
                            {data.execution_summary.latency_ms} ms
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-950/50 border border-slate-800 rounded-lg p-4">
                    <h4 className="text-xs font-bold text-slate-200 mb-2.5">
                      Cryptographic &amp; Boundary Integrity Checks
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 text-xs">
                      <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Payload Hash</span>
                        <span
                          className={`font-bold mt-0.5 block ${
                            data.integrity_details?.hash_match ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {data.integrity_details?.hash_match ? "MATCHED (SHA-256)" : "MISMATCH"}
                        </span>
                      </div>
                      <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Policy Baseline</span>
                        <span
                          className={`font-bold mt-0.5 block ${
                            data.integrity_details?.policy_approved
                              ? "text-emerald-400"
                              : "text-amber-400"
                          }`}
                        >
                          {data.integrity_details?.policy_approved ? "APPROVED" : "UNAPPROVED"}
                        </span>
                      </div>
                      <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Untrusted Boundary</span>
                        <span
                          className={`font-bold mt-0.5 block ${
                            data.integrity_details?.untrusted_data_boundaries_present
                              ? "text-emerald-400"
                              : "text-amber-400"
                          }`}
                        >
                          {data.integrity_details?.untrusted_data_boundaries_present
                            ? "DELIMITED"
                            : "NONE"}
                        </span>
                      </div>
                      <div className="bg-slate-900 p-2.5 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Access Level</span>
                        <span className="text-slate-200 font-bold mt-0.5 block">
                          {data.is_redacted ? "ROLE-REDACTED" : "FULL ACCESS"}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: System Prompt */}
              {activeTab === "system_prompt" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>
                      Complete compiled system directive with all 9 policy sections and injection guardrails.
                    </span>
                    <button
                      onClick={() =>
                        copyToClipboard(data.system_prompt, "System Prompt")
                      }
                      className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                    >
                      <Copy className="w-3 h-3" />
                      Copy text
                    </button>
                  </div>
                  <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-slate-200 text-xs font-mono leading-relaxed overflow-x-auto whitespace-pre-wrap max-h-[500px]">
                    {data.system_prompt}
                  </pre>
                </div>
              )}

              {/* Tab 3: Incident Payload */}
              {activeTab === "incident_payload" && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>
                      Exact user message containing FortiSIEM normalized telemetry inside &lt;UNTRUSTED_INCIDENT_DATA&gt; tags.
                    </span>
                    <button
                      onClick={() =>
                        copyToClipboard(data.incident_payload, "Incident Payload")
                      }
                      className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-semibold"
                    >
                      <Copy className="w-3 h-3" />
                      Copy text
                    </button>
                  </div>
                  <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-slate-200 text-xs font-mono leading-relaxed overflow-x-auto whitespace-pre-wrap max-h-[500px]">
                    {data.incident_payload}
                  </pre>
                </div>
              )}

              {/* Tab 4: Historical Precedents */}
              {activeTab === "precedents" && (
                <div className="space-y-3">
                  <p className="text-xs text-slate-400">
                    Historical RAG precedents actually supplied to the model during this specific execution.
                  </p>
                  {data.has_rag_precedents && data.rag_precedents.length > 0 ? (
                    <div className="space-y-2">
                      {data.rag_precedents.map((prec, i) => (
                        <div
                          key={i}
                          className="bg-slate-950/70 border border-slate-800 p-3 rounded-lg text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-indigo-400">
                              {prec.incident_id || prec.precedent_id || `Precedent #${i + 1}`}
                            </span>
                            <span
                              className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                                prec.verdict === "TRUE_POSITIVE"
                                  ? "bg-rose-950 text-rose-300 border border-rose-800"
                                  : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                              }`}
                            >
                              {prec.verdict || "UNKNOWN"}
                            </span>
                          </div>
                          <p className="text-slate-300 font-sans text-xs">
                            {prec.reason || prec.summary || JSON.stringify(prec)}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="bg-slate-950/40 border border-slate-800/80 rounded-lg p-8 text-center text-slate-400 text-xs">
                      <Database className="w-8 h-8 mx-auto text-slate-600 mb-2" />
                      <p className="font-semibold text-slate-300">No Historical RAG Precedents Included</p>
                      <p className="text-slate-500 mt-1">
                        This execution was evaluated purely on rule detection criteria and normalized telemetry without few-shot examples.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 5: Output Contract */}
              {activeTab === "contract" && (
                <div className="space-y-3">
                  <p className="text-xs text-slate-400">
                    Mandatory JSON schema and verdict requirements enforced on Server 2 (Local LLM).
                  </p>
                  <pre className="bg-slate-950 p-4 rounded-lg border border-slate-800 text-emerald-400 text-xs font-mono leading-relaxed overflow-x-auto max-h-[500px]">
                    {JSON.stringify(data.verdict_schema, null, 2)}
                  </pre>
                </div>
              )}

              {/* Tab 6: Technical Details */}
              {activeTab === "technical" && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-lg">
                      <span className="text-[11px] text-slate-400 block font-medium">Prompt Tokens</span>
                      <span className="text-base font-bold text-white">
                        {data.technical_details.prompt_tokens ?? "N/A"}
                      </span>
                    </div>
                    <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-lg">
                      <span className="text-[11px] text-slate-400 block font-medium">Completion Tokens</span>
                      <span className="text-base font-bold text-white">
                        {data.technical_details.completion_tokens ?? "N/A"}
                      </span>
                    </div>
                    <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-lg">
                      <span className="text-[11px] text-slate-400 block font-medium">Total Tokens</span>
                      <span className="text-base font-bold text-indigo-400">
                        {data.technical_details.total_tokens ?? "N/A"}
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-950/70 border border-slate-800 p-3 rounded-lg space-y-1.5 text-xs">
                    <span className="text-[11px] text-slate-400 uppercase font-bold tracking-wide">
                      Outbound Canonical Request Hash (SHA-256)
                    </span>
                    <p className="font-mono text-slate-300 break-all bg-slate-900 p-2.5 rounded border border-slate-800">
                      {data.technical_details.request_sha256}
                    </p>
                    <span className="text-[10px] text-slate-500 block">
                      Representation: {data.technical_details.payload_format || "CANONICAL_JSON"}
                    </span>
                  </div>

                  {data.raw_request_payload && (
                    <div className="space-y-1.5">
                      <span className="text-xs font-bold text-slate-300">
                        Canonical Outbound Request JSON
                      </span>
                      <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-60 leading-tight">
                        {JSON.stringify(data.raw_request_payload, null, 2)}
                      </pre>
                    </div>
                  )}

                  {data.raw_model_response && (
                    <div className="space-y-1.5">
                      <span className="text-xs font-bold text-slate-300">
                        Raw LLM Response String
                      </span>
                      <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-40 leading-tight">
                        {data.raw_model_response}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-4 sm:px-6 py-3 border-t border-slate-800 bg-slate-950/90 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-slate-500" />
            <span>Read-Only Audit Record • Confidential Security Telemetry</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-semibold transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
