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
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { api, ActualPromptResponse } from "@/lib/api";

interface ActualPromptInspectorModalProps {
  isOpen: boolean;
  onClose: () => void;
  incidentId?: string | null;
  ruleId?: string | null;
  ruleName?: string | null;
  versionId?: string | null;
}

export function ActualPromptInspectorModal({
  isOpen,
  onClose,
  incidentId: initialIncidentId,
  ruleId,
  ruleName,
  versionId,
}: ActualPromptInspectorModalProps) {
  const [activeTab, setActiveTab] = useState<
    "summary" | "system_prompt" | "incident_payload" | "precedents" | "contract" | "technical"
  >("summary");
  const [data, setData] = useState<ActualPromptResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchIncidentId, setSearchIncidentId] = useState(initialIncidentId || "");
  const [copySuccess, setCopySuccess] = useState<string | null>(null);
  const [exporting, setExporting] = useState<"json" | "markdown" | null>(null);

  useEffect(() => {
    if (initialIncidentId) {
      setSearchIncidentId(initialIncidentId);
    }
  }, [initialIncidentId]);

  useEffect(() => {
    if (isOpen) {
      loadData(searchIncidentId || initialIncidentId || undefined);
    }
  }, [isOpen, initialIncidentId, ruleId, versionId]);

  const loadData = async (targetIncidentId?: string) => {
    setLoading(true);
    setError(null);
    try {
      if (targetIncidentId && targetIncidentId.trim()) {
        const res = await api.getActualPromptForIncident(targetIncidentId.trim());
        setData(res);
      } else if (ruleId) {
        const res = await api.getPromptPreviewForRule(ruleId, versionId || undefined);
        setData(res);
      } else {
        setData(null);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load actual prompt data");
    } finally {
      setLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchIncidentId.trim()) {
      loadData(searchIncidentId.trim());
    }
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
        format
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
      return (
        <div className="bg-emerald-950/60 border border-emerald-500/40 text-emerald-300 px-4 py-2.5 rounded-lg flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="font-semibold text-sm tracking-wide">Captured Runtime Prompt</span>
            <span className="text-xs text-emerald-400/80 border-l border-emerald-500/30 pl-2 ml-1">
              Authoritative outbound request payload recorded at Server 1 → Server 2 provider boundary.
            </span>
          </div>
          <span className="text-xs font-mono bg-emerald-900/60 text-emerald-200 px-2 py-0.5 rounded border border-emerald-500/30">
            SHA256: {data.technical_details.request_sha256.substring(0, 10)}...
          </span>
        </div>
      );
    }

    if (data.capture_status === "HISTORICAL_CAPTURE_UNAVAILABLE") {
      return (
        <div className="bg-amber-950/60 border border-amber-500/40 text-amber-300 px-4 py-2.5 rounded-lg flex items-center justify-between shadow-sm">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span className="font-semibold text-sm tracking-wide">Historical Capture Unavailable</span>
            <span className="text-xs text-amber-400/80 border-l border-amber-500/30 pl-2 ml-1">
              Evaluated prior to runtime capture deployment; outbound payload was not recorded.
            </span>
          </div>
          <span className="text-xs bg-amber-900/50 text-amber-200 px-2 py-0.5 rounded border border-amber-500/30">
            Unrecorded
          </span>
        </div>
      );
    }

    return (
      <div className="bg-sky-950/60 border border-sky-500/40 text-sky-300 px-4 py-2.5 rounded-lg flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-sky-400" />
          <span className="font-semibold text-sm tracking-wide">Preview Only</span>
          <span className="text-xs text-sky-400/80 border-l border-sky-500/30 pl-2 ml-1">
            Live compiled specification representation. Not proof of historical runtime execution.
          </span>
        </div>
        <span className="text-xs font-mono bg-sky-900/50 text-sky-200 px-2 py-0.5 rounded border border-sky-500/30">
          Simulation
        </span>
      </div>
    );
  };

  const renderIntegrityBadge = () => {
    if (!data) return null;
    const st = data.integrity_status;
    if (st === "VERIFIED") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950 border border-emerald-500/50 text-emerald-400">
          <ShieldCheck className="w-3.5 h-3.5" />
          Prompt Integrity: Verified
        </span>
      );
    }
    if (st === "MISMATCH") {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-950 border border-rose-500/50 text-rose-400 animate-pulse">
          <ShieldAlert className="w-3.5 h-3.5" />
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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700 w-full max-w-6xl rounded-xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-indigo-500/10 border border-indigo-500/30 rounded-lg text-indigo-400">
              <Terminal className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">
                  Actual LLM Prompt Inspector
                </h2>
                <span className="text-xs bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                  AIS 2.0
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Exact investigation instructions and incident evidence transmitted from Server 1 to Local LLM (Server 2)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick Incident Lookup Bar */}
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-1.5">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Incident ID (e.g. INC-001)"
                  value={searchIncidentId}
                  onChange={(e) => setSearchIncidentId(e.target.value)}
                  className="bg-slate-800/80 border border-slate-700 text-xs text-slate-200 rounded-md pl-8 pr-2.5 py-1.5 focus:outline-none focus:border-indigo-500 w-52 font-mono"
                />
              </div>
              <button
                type="submit"
                className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-2.5 py-1.5 rounded-md font-medium transition"
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

        {/* Status Banner */}
        <div className="px-6 pt-4 pb-2 bg-slate-950/40 border-b border-slate-800/80">
          {renderBanner()}
        </div>

        {/* Main Content Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400">
              <RefreshCw className="w-8 h-8 animate-spin text-indigo-400 mb-3" />
              <p className="text-sm">Fetching authoritative runtime payload from provider boundary...</p>
            </div>
          )}

          {error && (
            <div className="bg-rose-950/40 border border-rose-500/40 rounded-lg p-4 text-rose-300 text-sm flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Unable to load actual prompt data</p>
                <p className="text-xs text-rose-400 mt-1">{error}</p>
              </div>
            </div>
          )}

          {!loading && !error && data && (
            <>
              {/* L1 Engineer Plain-Language Explanation Panel */}
              <div className="bg-slate-800/60 border border-slate-700/80 rounded-xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Info className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-sm font-semibold text-slate-200">
                      L1 Investigation & Evidence Summary
                    </h3>
                  </div>
                  {renderIntegrityBadge()}
                </div>

                <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-slate-800 font-sans">
                  <strong className="text-white">Explanation:</strong> {data.l1_explanation.headline}
                </p>

                {/* 5 Highlights Grid */}
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-1">
                  <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block">Policy Version</span>
                    <span className="text-xs font-semibold text-slate-200 block truncate">
                      {data.l1_explanation.policy_version_used}
                    </span>
                  </div>

                  <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block">Mandatory Evidence</span>
                    <span
                      className={`text-xs font-semibold block ${
                        data.l1_explanation.mandatory_evidence_available
                          ? "text-emerald-400"
                          : "text-amber-400"
                      }`}
                    >
                      {data.l1_explanation.mandatory_evidence_available
                        ? "Available"
                        : "Missing / Incomplete"}
                    </span>
                  </div>

                  <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block">RAG Precedents</span>
                    <span className="text-xs font-semibold text-slate-200 block">
                      {data.l1_explanation.historical_precedents_included > 0
                        ? `${data.l1_explanation.historical_precedents_included} Included`
                        : "None (Zero RAG)"}
                    </span>
                  </div>

                  <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block">Verdict Returned</span>
                    <span
                      className={`text-xs font-semibold block ${
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

                  <div className="bg-slate-900/80 border border-slate-800 p-2.5 rounded-lg">
                    <span className="text-[11px] text-slate-400 block">Policy Approval Match</span>
                    <span
                      className={`text-xs font-semibold block ${
                        data.l1_explanation.prompt_matches_approved_policy
                          ? "text-emerald-400"
                          : "text-rose-400"
                      }`}
                    >
                      {data.l1_explanation.prompt_matches_approved_policy
                        ? "Approved Match"
                        : "Unapproved Policy"}
                    </span>
                  </div>
                </div>

                {data.l1_explanation.key_takeaways && data.l1_explanation.key_takeaways.length > 0 && (
                  <div className="pt-1">
                    <span className="text-[11px] text-slate-400 uppercase tracking-wider font-semibold">
                      Key Takeaways:
                    </span>
                    <ul className="mt-1 space-y-1">
                      {data.l1_explanation.key_takeaways.map((item, idx) => (
                        <li key={idx} className="text-xs text-slate-300 flex items-start gap-2">
                          <span className="text-indigo-400 font-bold">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* 6 Tabs Navigation */}
              <div className="border-b border-slate-800 flex items-center justify-between">
                <nav className="flex space-x-2">
                  <button
                    onClick={() => setActiveTab("summary")}
                    className={`px-3 py-2 text-xs font-medium rounded-t-lg transition border-b-2 ${
                      activeTab === "summary"
                        ? "border-indigo-500 text-indigo-400 bg-slate-800/50"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    1. Execution Summary
                  </button>
                  <button
                    onClick={() => setActiveTab("system_prompt")}
                    className={`px-3 py-2 text-xs font-medium rounded-t-lg transition border-b-2 ${
                      activeTab === "system_prompt"
                        ? "border-indigo-500 text-indigo-400 bg-slate-800/50"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    2. System Prompt
                  </button>
                  <button
                    onClick={() => setActiveTab("incident_payload")}
                    className={`px-3 py-2 text-xs font-medium rounded-t-lg transition border-b-2 ${
                      activeTab === "incident_payload"
                        ? "border-indigo-500 text-indigo-400 bg-slate-800/50"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    3. Incident Payload
                  </button>
                  <button
                    onClick={() => setActiveTab("precedents")}
                    className={`px-3 py-2 text-xs font-medium rounded-t-lg transition border-b-2 ${
                      activeTab === "precedents"
                        ? "border-indigo-500 text-indigo-400 bg-slate-800/50"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    4. Historical Precedents ({data.rag_precedents?.length || 0})
                  </button>
                  <button
                    onClick={() => setActiveTab("contract")}
                    className={`px-3 py-2 text-xs font-medium rounded-t-lg transition border-b-2 ${
                      activeTab === "contract"
                        ? "border-indigo-500 text-indigo-400 bg-slate-800/50"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    5. Output Contract
                  </button>
                  <button
                    onClick={() => setActiveTab("technical")}
                    className={`px-3 py-2 text-xs font-medium rounded-t-lg transition border-b-2 ${
                      activeTab === "technical"
                        ? "border-indigo-500 text-indigo-400 bg-slate-800/50"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    6. Technical Details
                  </button>
                </nav>

                {/* Quick Copy & Export Bar */}
                <div className="flex items-center gap-2 pb-1">
                  {copySuccess && (
                    <span className="text-xs text-emerald-400 flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {copySuccess} copied!
                    </span>
                  )}
                  <button
                    onClick={() =>
                      copyToClipboard(data.system_prompt, "System Prompt")
                    }
                    className="p-1.5 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded text-xs flex items-center gap-1 border border-slate-700 transition"
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
                      >
                        <Download className="w-3 h-3" />
                        JSON
                      </button>
                      <button
                        onClick={() => handleExport("markdown")}
                        disabled={exporting !== null}
                        className="px-2 py-1 text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded text-xs flex items-center gap-1 border border-slate-700 transition"
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
                    <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-4 space-y-2.5">
                      <h4 className="text-xs uppercase font-semibold text-indigo-400 tracking-wider">
                        Incident & Rule Provenance
                      </h4>
                      <div className="text-xs space-y-1.5">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Incident ID:</span>
                          <span className="font-mono text-slate-200">
                            {data.execution_summary.incident_id}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Rule Name:</span>
                          <span className="text-slate-200 font-medium">
                            {data.execution_summary.rule_name}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Rule ID:</span>
                          <span className="font-mono text-slate-400">
                            {data.execution_summary.rule_id}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Policy Version:</span>
                          <span className="text-slate-200">
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
                      </div>
                    </div>

                    <div className="bg-slate-950/60 border border-slate-800 rounded-lg p-4 space-y-2.5">
                      <h4 className="text-xs uppercase font-semibold text-indigo-400 tracking-wider">
                        Execution & Dispatch Pipeline
                      </h4>
                      <div className="text-xs space-y-1.5">
                        <div className="flex justify-between">
                          <span className="text-slate-400">Model Name:</span>
                          <span className="font-mono text-slate-200">
                            {data.execution_summary.model_name}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Provider:</span>
                          <span className="text-slate-200">
                            {data.execution_summary.provider_type}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Execution Status:</span>
                          <span
                            className={`font-semibold ${
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
                          <span className="text-slate-400">Attempt Number:</span>
                          <span className="text-slate-200">
                            #{data.execution_summary.attempt_number}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Captured At:</span>
                          <span className="text-slate-400">
                            {new Date(data.execution_summary.captured_at).toLocaleString()}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-slate-400">Inference Latency:</span>
                          <span className="text-slate-200">
                            {data.execution_summary.latency_ms} ms
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-950/40 border border-slate-800/80 rounded-lg p-4">
                    <h4 className="text-xs font-semibold text-slate-300 mb-2">
                      Prompt Integrity Verification Report
                    </h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                      <div className="bg-slate-900 p-2 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Hash Verification</span>
                        <span
                          className={`font-semibold ${
                            data.integrity_details?.hash_match ? "text-emerald-400" : "text-rose-400"
                          }`}
                        >
                          {data.integrity_details?.hash_match ? "MATCHED" : "MISMATCH"}
                        </span>
                      </div>
                      <div className="bg-slate-900 p-2 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Policy Approval</span>
                        <span
                          className={`font-semibold ${
                            data.integrity_details?.policy_approved
                              ? "text-emerald-400"
                              : "text-amber-400"
                          }`}
                        >
                          {data.integrity_details?.policy_approved ? "APPROVED" : "UNAPPROVED"}
                        </span>
                      </div>
                      <div className="bg-slate-900 p-2 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Untrusted Boundary</span>
                        <span
                          className={`font-semibold ${
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
                      <div className="bg-slate-900 p-2 rounded border border-slate-800">
                        <span className="text-slate-400 block text-[11px]">Redaction Applied</span>
                        <span className="text-slate-300 font-semibold">
                          {data.integrity_details?.redacted ? "ROLE-REDACTED" : "FULL ACCESS"}
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
                      className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
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
                      className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
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
                            <span className="font-mono text-indigo-400">
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
                    <div className="bg-slate-950/40 border border-slate-800/80 rounded-lg p-6 text-center text-slate-400 text-xs">
                      <Database className="w-8 h-8 mx-auto text-slate-600 mb-2" />
                      <p className="font-medium text-slate-300">No Historical RAG Precedents Included</p>
                      <p className="text-slate-500 mt-1">
                        This execution was evaluated purely on rule detection criteria and normalized telemetry.
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
                    <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg">
                      <span className="text-[11px] text-slate-400 block">Prompt Tokens</span>
                      <span className="text-base font-bold text-white">
                        {data.technical_details.prompt_tokens}
                      </span>
                    </div>
                    <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg">
                      <span className="text-[11px] text-slate-400 block">Completion Tokens</span>
                      <span className="text-base font-bold text-white">
                        {data.technical_details.completion_tokens}
                      </span>
                    </div>
                    <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg">
                      <span className="text-[11px] text-slate-400 block">Total Tokens</span>
                      <span className="text-base font-bold text-indigo-400">
                        {data.technical_details.total_tokens}
                      </span>
                    </div>
                  </div>

                  <div className="bg-slate-950/60 border border-slate-800 p-3 rounded-lg space-y-1.5 text-xs">
                    <span className="text-[11px] text-slate-400 uppercase font-semibold">
                      Outbound Canonical Request Hash (SHA-256)
                    </span>
                    <p className="font-mono text-slate-300 break-all bg-slate-900 p-2 rounded border border-slate-800">
                      {data.technical_details.request_sha256}
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <span className="text-xs font-semibold text-slate-300">
                      Canonical Outbound Request JSON
                    </span>
                    <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-60">
                      {JSON.stringify(data.technical_details.raw_request_payload, null, 2)}
                    </pre>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-slate-500" />
            <span>Read-Only Audit Record • Confidential Security Telemetry</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded font-medium transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
