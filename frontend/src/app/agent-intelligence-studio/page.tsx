"use client";

import React, { useState, useEffect } from "react";
import {
  FileCode,
  FileCode2,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  History,
  RotateCcw,
  Sparkles,
  Save,
  Check,
  Shield,
  Layers,
  Info,
  Clock,
  ArrowRight,
  ArrowLeft,
  Table,
  Search,
  Filter,
  RefreshCw,
  Plus,
  Download,
  ChevronDown,
} from "lucide-react";
import {
  api,
  RuleItem,
  RulePrompt,
  PromptVersion,
  RulePromptSummaryItem,
} from "@/lib/api";

export default function AgentIntelligenceStudioPage() {
  // Navigation / View mode
  const [viewMode, setViewMode] = useState<"table" | "studio">("table");

  // Rules & Summaries State
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [summaries, setSummaries] = useState<RulePromptSummaryItem[]>([]);
  const [loadingRules, setLoadingRules] = useState(true);
  const [loadingSummaries, setLoadingSummaries] = useState(true);

  // Table Filters State
  const [searchFilter, setSearchFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [baselineFilter, setBaselineFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Studio / Editor State
  const [selectedRuleId, setSelectedRuleId] = useState<string>("");
  const [rulePrompt, setRulePrompt] = useState<RulePrompt | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Edit / Form state
  const [isEditing, setIsEditing] = useState(false);
  const [editCommon, setEditCommon] = useState("");
  const [editRuleSpecific, setEditRuleSpecific] = useState("");
  const [editConditions, setEditConditions] = useState("");
  const [editEvidence, setEditEvidence] = useState("");
  const [editTpIndicators, setEditTpIndicators] = useState("");
  const [editFpIndicators, setEditFpIndicators] = useState("");
  const [editMissingInfo, setEditMissingInfo] = useState("");
  const [editEscalation, setEditEscalation] = useState("");
  const [editQuestions, setEditQuestions] = useState<string[]>([]);
  const [newQuestionInput, setNewQuestionInput] = useState("");
  const [changeSummary, setChangeSummary] = useState("");

  // Approval modal state
  const [showApprovalModal, setShowApprovalModal] = useState(false);
  const [approvalSummary, setApprovalSummary] = useState("Approved by SOC Lead");

  // Download / Export state
  const [downloadingExport, setDownloadingExport] = useState(false);
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showStudioExportMenu, setShowStudioExportMenu] = useState(false);

  const handleExportAll = async (format: "json" | "markdown" = "json") => {
    setDownloadingExport(true);
    setFeedback(null);
    setShowExportMenu(false);
    try {
      const { blob, filename } = await api.exportRulePrompts(format);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setFeedback({
        type: "success",
        text: `Successfully exported rule-wise prompts and configuration (${format.toUpperCase()}).`,
      });
    } catch (err: any) {
      setFeedback({ type: "error", text: `Export failed: ${err.message}` });
    } finally {
      setDownloadingExport(false);
    }
  };

  const handleExportSingleRule = async (ruleId: string, format: "json" | "markdown" = "json") => {
    if (!ruleId) return;
    setDownloadingExport(true);
    setFeedback(null);
    setShowStudioExportMenu(false);
    try {
      const { blob, filename } = await api.exportSingleRulePrompt(ruleId, format);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      setFeedback({
        type: "success",
        text: `Downloaded rule prompt configuration (${format.toUpperCase()}).`,
      });
    } catch (err: any) {
      setFeedback({ type: "error", text: `Download failed: ${err.message}` });
    } finally {
      setDownloadingExport(false);
    }
  };

  const loadSummaries = async () => {
    setLoadingSummaries(true);
    try {
      const data = await api.getRulePromptsSummary();
      setSummaries(data);
    } catch (err: any) {
      console.error("Failed to load prompt summaries:", err);
    } finally {
      setLoadingSummaries(false);
    }
  };

  const loadRules = async () => {
    setLoadingRules(true);
    try {
      const res = await api.getRules({ page_size: 100 });
      setRules(res.items);
    } catch (err: any) {
      console.error("Failed to load rules:", err);
    } finally {
      setLoadingRules(false);
    }
  };

  // Initial data loading & URL query parameter check
  useEffect(() => {
    async function init() {
      await Promise.all([loadRules(), loadSummaries()]);

      // Check URL search parameters
      if (typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        const ruleParam = params.get("rule_id") || params.get("ruleId");
        if (ruleParam) {
          setSelectedRuleId(ruleParam);
          setViewMode("studio");
        }
      }
    }
    init();
  }, []);

  const clearForm = () => {
    setSelectedVersionId("");
    setEditCommon("");
    setEditRuleSpecific("");
    setEditConditions("");
    setEditEvidence("");
    setEditTpIndicators("");
    setEditFpIndicators("");
    setEditMissingInfo("");
    setEditEscalation("");
    setEditQuestions([]);
    setIsEditing(false);
  };

  // Load rule prompt when rule changes in studio
  const fetchPrompt = async (ruleId: string) => {
    if (!ruleId) return;
    setLoadingPrompt(true);
    setFeedback(null);
    try {
      const rp = await api.getRulePrompt(ruleId);
      setRulePrompt(rp);
      if (rp.versions && rp.versions.length > 0) {
        const targetId = rp.active_version_id || rp.versions[0].id;
        setSelectedVersionId(targetId);
        loadVersionIntoForm(rp.versions.find((v) => v.id === targetId) || rp.versions[0]);
      } else {
        clearForm();
      }
    } catch (err: any) {
      console.error(err);
      clearForm();
      setFeedback({ type: "error", text: err.message });
    } finally {
      setLoadingPrompt(false);
    }
  };

  useEffect(() => {
    if (viewMode === "studio" && selectedRuleId) {
      fetchPrompt(selectedRuleId);
    }
  }, [viewMode, selectedRuleId]);

  const loadVersionIntoForm = (v: PromptVersion) => {
    setEditCommon(v.common_prompt || "");
    setEditRuleSpecific(v.rule_specific_prompt || "");
    setEditConditions(v.detection_conditions || "");
    setEditEvidence(v.required_evidence || "");
    setEditTpIndicators(v.tp_indicators || "");
    setEditFpIndicators(v.fp_indicators || "");
    setEditMissingInfo(v.missing_info_criteria || "");
    setEditEscalation(v.escalation_conditions || "");
    setEditQuestions(v.analyst_questions || []);
    setIsEditing(false);
  };

  const handleSelectVersion = (versionId: string) => {
    setSelectedVersionId(versionId);
    const v = rulePrompt?.versions.find((item) => item.id === versionId);
    if (v) {
      loadVersionIntoForm(v);
    }
  };

  // Open Studio view for a specific rule from the table
  const handleOpenStudioForRule = (ruleId: string) => {
    setSelectedRuleId(ruleId);
    clearForm();
    setViewMode("studio");
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("rule_id", ruleId);
      window.history.pushState({}, "", url.toString());
    }
  };

  // Return to the Rules Directory table view
  const handleBackToTable = () => {
    setViewMode("table");
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.delete("rule_id");
      url.searchParams.delete("ruleId");
      window.history.pushState({}, "", url.toString());
    }
    loadSummaries();
  };

  // Switch rule directly within studio
  const handleSwitchRuleInStudio = (ruleId: string) => {
    setSelectedRuleId(ruleId);
    clearForm();
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("rule_id", ruleId);
      window.history.pushState({}, "", url.toString());
    }
  };

  const handleGenerateTemplateDraft = async () => {
    if (!selectedRuleId) return;
    setActionLoading(true);
    setFeedback(null);
    try {
      const newDraft = await api.generateTemplateDraft(selectedRuleId);
      await fetchPrompt(selectedRuleId);
      setSelectedVersionId(newDraft.id);
      loadVersionIntoForm(newDraft);
      setFeedback({
        type: "success",
        text: `Template-generated draft Version ${newDraft.version_number} synthesized from SIEM rule specifications (Not AI-generated).`,
      });
      loadSummaries();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleSaveManualDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRuleId) return;
    setActionLoading(true);
    setFeedback(null);
    try {
      const newDraft = await api.createManualDraft(selectedRuleId, {
        common_prompt: editCommon,
        rule_specific_prompt: editRuleSpecific,
        detection_conditions: editConditions,
        required_evidence: editEvidence,
        tp_indicators: editTpIndicators,
        fp_indicators: editFpIndicators,
        missing_info_criteria: editMissingInfo,
        escalation_conditions: editEscalation,
        analyst_questions: editQuestions,
        change_summary: changeSummary || "Manual prompt update",
      });
      await fetchPrompt(selectedRuleId);
      setSelectedVersionId(newDraft.id);
      loadVersionIntoForm(newDraft);
      setIsEditing(false);
      setChangeSummary("");
      setFeedback({
        type: "success",
        text: `Manual draft Version ${newDraft.version_number} saved successfully.`,
      });
      loadSummaries();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedRuleId || !selectedVersionId) return;
    const versionBelongs = rulePrompt?.versions?.some((v) => v.id === selectedVersionId);
    if (!versionBelongs) {
      setFeedback({
        type: "error",
        text: "The selected prompt version does not match this rule. Please select a valid version before approving.",
      });
      setShowApprovalModal(false);
      return;
    }
    setActionLoading(true);
    setFeedback(null);
    try {
      const approved = await api.approvePromptVersion(selectedRuleId, selectedVersionId, approvalSummary);
      await fetchPrompt(selectedRuleId);
      setShowApprovalModal(false);
      setFeedback({
        type: "success",
        text: `Version ${approved.version_number} approved and activated as production baseline.`,
      });
      loadSummaries();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!selectedRuleId || !selectedVersionId) return;
    const versionBelongs = rulePrompt?.versions?.some((v) => v.id === selectedVersionId);
    if (!versionBelongs) {
      setFeedback({
        type: "error",
        text: "The selected prompt version does not match this rule.",
      });
      return;
    }
    if (!confirm(`Are you sure you want to rollback production prompt to Version content from ${selectedVersion?.version_number}? This will create a new approved version.`)) return;
    setActionLoading(true);
    setFeedback(null);
    try {
      const rolled = await api.rollbackPromptVersion(selectedRuleId, selectedVersionId);
      await fetchPrompt(selectedRuleId);
      setSelectedVersionId(rolled.id);
      loadVersionIntoForm(rolled);
      setFeedback({
        type: "success",
        text: `Rollback successful: Activated new Version ${rolled.version_number}.`,
      });
      loadSummaries();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setActionLoading(false);
    }
  };

  const handleAddQuestion = () => {
    if (newQuestionInput.trim()) {
      setEditQuestions([...editQuestions, newQuestionInput.trim()]);
      setNewQuestionInput("");
    }
  };

  const handleRemoveQuestion = (idx: number) => {
    setEditQuestions(editQuestions.filter((_, i) => i !== idx));
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev?.toUpperCase()) {
      case "CRITICAL":
        return "bg-rose-950/80 text-rose-300 border-rose-800";
      case "HIGH":
        return "bg-orange-950/80 text-orange-300 border-orange-800";
      case "MEDIUM":
        return "bg-amber-950/80 text-amber-300 border-amber-800";
      default:
        return "bg-blue-950/80 text-blue-300 border-blue-800";
    }
  };

  // Filter summaries for table
  const filteredSummaries = summaries.filter((item) => {
    if (searchFilter) {
      const q = searchFilter.toLowerCase();
      const matchName = item.rule_name.toLowerCase().includes(q);
      const matchEvent = item.event_type.toLowerCase().includes(q);
      const matchSource = (item.data_source || "").toLowerCase().includes(q);
      if (!matchName && !matchEvent && !matchSource) return false;
    }
    if (severityFilter && item.severity.toUpperCase() !== severityFilter.toUpperCase()) {
      return false;
    }
    if (baselineFilter === "APPROVED" && !item.has_approved_prompt) {
      return false;
    }
    if (baselineFilter === "DRAFT" && (item.has_approved_prompt || item.total_versions === 0)) {
      return false;
    }
    if (baselineFilter === "NONE" && item.total_versions > 0) {
      return false;
    }
    return true;
  });

  const totalPages = Math.ceil(filteredSummaries.length / pageSize) || 1;
  const paginatedSummaries = filteredSummaries.slice((page - 1) * pageSize, page * pageSize);

  // Metrics Counters
  const totalRulesCount = summaries.length;
  const approvedPromptsCount = summaries.filter((s) => s.has_approved_prompt).length;
  const draftOnlyCount = summaries.filter((s) => !s.has_approved_prompt && s.total_versions > 0).length;
  const missingBaselineCount = summaries.filter((s) => s.total_versions === 0).length;

  const selectedVersion = rulePrompt?.versions.find((v) => v.id === selectedVersionId);
  const isSelectedActive = selectedVersion?.id === rulePrompt?.active_version_id;

  // =========================================================================
  // VIEW 1: RULES DIRECTORY TABLE
  // =========================================================================
  if (viewMode === "table") {
    return (
      <div className="space-y-4">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-800 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
                <FileCode2 className="w-5 h-5 text-cyan-400" />
                Agent Intelligence Studio
              </h1>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-semibold bg-sky-950/80 text-sky-400 border border-sky-800/60 font-mono">
                Agent Policy Engine
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Select any detection rule to inspect policy prompt history, synthesize deterministic criteria drafts, or approve production policies.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                loadSummaries();
                loadRules();
              }}
              disabled={loadingSummaries}
              className="px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 font-medium flex items-center gap-1.5 transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${loadingSummaries ? "animate-spin" : ""}`} />
              Refresh
            </button>

            {/* Download Rule-Wise Prompts & Configurations */}
            <div className="relative">
              <div className="inline-flex rounded-md shadow-sm">
                <button
                  type="button"
                  onClick={() => handleExportAll("json")}
                  disabled={downloadingExport}
                  className="px-2.5 py-1 text-xs rounded-l border border-cyan-800/80 bg-cyan-950/60 hover:bg-cyan-900/80 text-cyan-200 font-semibold flex items-center gap-1.5 transition-colors"
                  title="Download all rules and prompt configurations as JSON"
                >
                  <Download className={`w-3.5 h-3.5 text-cyan-400 ${downloadingExport ? "animate-bounce" : ""}`} />
                  {downloadingExport ? "Exporting..." : "Download Rules Config"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowExportMenu((prev) => !prev)}
                  disabled={downloadingExport}
                  className="px-1.5 py-1 text-xs rounded-r border-t border-b border-r border-cyan-800/80 bg-cyan-950/60 hover:bg-cyan-900/80 text-cyan-200 transition-colors"
                  title="Choose export format"
                >
                  <ChevronDown className="w-3 h-3 text-cyan-400" />
                </button>
              </div>

              {showExportMenu && (
                <div className="absolute right-0 mt-1 w-48 rounded-md border border-slate-800 bg-slate-950 py-1 shadow-xl z-20 text-xs">
                  <button
                    type="button"
                    onClick={() => handleExportAll("json")}
                    className="w-full text-left px-3 py-1.5 hover:bg-slate-900 text-slate-200 flex items-center justify-between"
                  >
                    <span>Download JSON</span>
                    <span className="text-[10px] text-slate-500 font-mono">.json</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleExportAll("markdown")}
                    className="w-full text-left px-3 py-1.5 hover:bg-slate-900 text-slate-200 flex items-center justify-between"
                  >
                    <span>Download Markdown</span>
                    <span className="text-[10px] text-slate-500 font-mono">.md</span>
                  </button>
                </div>
              )}
            </div>

            {selectedRuleId && (
              <button
                onClick={() => setViewMode("studio")}
                className="px-3 py-1 text-xs rounded bg-sky-600 hover:bg-sky-500 text-white font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
              >
                Resume Studio Editor <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Top Metrics Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
            <div className="text-[10px] uppercase font-semibold text-slate-400 flex items-center justify-between">
              Total Monitored Rules
              <FileCode className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <div className="text-xl font-bold text-slate-100 mt-1">{totalRulesCount}</div>
            <div className="text-[10px] text-slate-500 mt-0.5">Active detection rules</div>
          </div>

          <div className="p-3 rounded-lg border border-emerald-900/50 bg-emerald-950/20">
            <div className="text-[10px] uppercase font-semibold text-emerald-400 flex items-center justify-between">
              Production Approved
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-xl font-bold text-emerald-300 mt-1">{approvedPromptsCount}</div>
            <div className="text-[10px] text-emerald-500/80 mt-0.5">
              {totalRulesCount ? Math.round((approvedPromptsCount / totalRulesCount) * 100) : 0}% rules covered
            </div>
          </div>

          <div className="p-3 rounded-lg border border-sky-900/50 bg-sky-950/20">
            <div className="text-[10px] uppercase font-semibold text-sky-400 flex items-center justify-between">
              Template Drafts
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            </div>
            <div className="text-xl font-bold text-sky-300 mt-1">{draftOnlyCount}</div>
            <div className="text-[10px] text-sky-500/80 mt-0.5">Synthesized & awaiting review</div>
          </div>

          <div className="p-3 rounded-lg border border-amber-900/50 bg-amber-950/20">
            <div className="text-[10px] uppercase font-semibold text-amber-400 flex items-center justify-between">
              Need Baseline
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-xl font-bold text-amber-300 mt-1">{missingBaselineCount}</div>
            <div className="text-[10px] text-amber-500/80 mt-0.5">Auto-generates on selection</div>
          </div>
        </div>

        {/* Non-LLM Governance Notice */}
        <div className="p-2.5 rounded-lg border border-indigo-900/40 bg-indigo-950/20 text-xs text-slate-300 flex items-start gap-2.5">
          <Info className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-tight">
            <strong className="text-indigo-300">Phase 2 Rule Prompt Governance:</strong> All prompt templates are synthesized deterministically from ingested SIEM rule definitions. Click any rule in the table below to inspect its prompt version history, edit investigation directives, or approve the active production baseline.
          </div>
        </div>

        {/* Filter & Search Toolbar */}
        <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/30 flex flex-wrap items-center justify-between gap-2.5">
          <div className="flex-1 min-w-[240px] relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => {
                setSearchFilter(e.target.value);
                setPage(1);
              }}
              placeholder="Search rules by name, event type, or data source..."
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 text-xs rounded border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

            <select
              value={baselineFilter}
              onChange={(e) => {
                setBaselineFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 text-xs rounded border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Prompt Statuses</option>
              <option value="APPROVED">Production Approved</option>
              <option value="DRAFT">Template Draft Only</option>
              <option value="NONE">No Baseline</option>
            </select>
          </div>
        </div>

        {/* Rules Table */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-[10px] font-mono text-slate-400">
                  <th className="py-2.5 px-3 font-semibold">Rule Name &amp; Event Type</th>
                  <th className="py-2.5 px-3 font-semibold">Severity</th>
                  <th className="py-2.5 px-3 font-semibold">Data Source</th>
                  <th className="py-2.5 px-3 font-semibold">Prompt Baseline Status</th>
                  <th className="py-2.5 px-3 font-semibold">Versions</th>
                  <th className="py-2.5 px-3 font-semibold">Last Updated</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loadingSummaries ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400 text-xs">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
                      Loading SIEM rule prompt registry...
                    </td>
                  </tr>
                ) : paginatedSummaries.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-500 text-xs">
                      No detection rules match the specified search or filter criteria.
                    </td>
                  </tr>
                ) : (
                  paginatedSummaries.map((item) => {
                    const isApproved = item.has_approved_prompt;
                    const hasDraft = !isApproved && item.total_versions > 0;
                    return (
                      <tr
                        key={item.rule_id}
                        onClick={() => handleOpenStudioForRule(item.rule_id)}
                        className="hover:bg-slate-900/60 cursor-pointer transition-colors group"
                      >
                        <td className="py-2.5 px-3">
                          <div className="font-semibold text-slate-200 group-hover:text-cyan-400 transition-colors">
                            {item.rule_name}
                          </div>
                          <div className="text-[10px] font-mono text-slate-400 mt-0.5">
                            {item.event_type}
                          </div>
                        </td>

                        <td className="py-2.5 px-3">
                          <span className={`px-1.5 py-0.5 rounded border text-[9px] font-bold ${getSeverityBadge(item.severity)}`}>
                            {item.severity}
                          </span>
                        </td>

                        <td className="py-2.5 px-3 text-slate-400 text-[11px] truncate max-w-[160px]" title={item.data_source || "SIEM Ingestion"}>
                          {item.data_source || "SIEM Ingestion"}
                        </td>

                        <td className="py-2.5 px-3">
                          {isApproved ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              v{item.active_version_number || 1} Production Active
                            </span>
                          ) : hasDraft ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-950 text-sky-400 border border-sky-800">
                              <Sparkles className="w-3 h-3 text-sky-400" />
                              v{item.active_version_number || 1} Template Draft
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-900 text-slate-400 border border-slate-800">
                              No Baseline
                            </span>
                          )}
                        </td>

                        <td className="py-2.5 px-3 text-slate-300 font-mono text-xs">
                          {item.total_versions > 0 ? (
                            <span>{item.total_versions} {item.total_versions === 1 ? "version" : "versions"}</span>
                          ) : (
                            <span className="text-slate-500 italic">0 versions</span>
                          )}
                        </td>

                        <td className="py-2.5 px-3 text-slate-400 text-[11px]">
                          {item.last_updated ? new Date(item.last_updated).toLocaleDateString() : "—"}
                        </td>

                        <td className="py-2.5 px-3 text-right">
                          <div className="inline-flex items-center gap-1.5 justify-end">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleExportSingleRule(item.rule_id, "json");
                              }}
                              disabled={downloadingExport}
                              title="Download rule prompt configuration (JSON)"
                              className="p-1 rounded border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-cyan-300 transition-colors"
                            >
                              <Download className="w-3.5 h-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenStudioForRule(item.rule_id);
                              }}
                              className="px-2.5 py-1 text-xs rounded border border-cyan-800/80 bg-cyan-950/40 hover:bg-cyan-900/60 text-cyan-300 font-semibold inline-flex items-center gap-1 transition-colors shadow-sm"
                            >
                              Open Studio <ArrowRight className="w-3 h-3" />
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

          {/* Table Pagination */}
          <div className="p-3 border-t border-slate-800 bg-slate-900/40 flex items-center justify-between text-xs text-slate-400">
            <div>
              Showing {filteredSummaries.length > 0 ? (page - 1) * pageSize + 1 : 0} to{" "}
              {Math.min(page * pageSize, filteredSummaries.length)} of {filteredSummaries.length} rules
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                className="px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 hover:bg-slate-900 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300"
              >
                Previous
              </button>
              <span className="font-mono text-slate-300">
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                className="px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 hover:bg-slate-900 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // =========================================================================
  // VIEW 2: RULE PROMPT STUDIO (EDITOR VIEW)
  // =========================================================================
  return (
    <div className="space-y-3">
      {/* Page Header with Back Navigation & Rule Switcher */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-800 pb-2.5">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handleBackToTable}
            className="px-2.5 py-1 rounded-md border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-cyan-400" />
            <Table className="w-3.5 h-3.5 text-slate-400" />
            Back to Rules List
          </button>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100">
                Agent Intelligence Studio
              </h1>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-semibold bg-sky-950/80 text-sky-400 border border-sky-800/60 font-mono">
                Agent Policy Engine
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Deterministic agent policy template engineering, version management, approval gating, and safe rollback.
            </p>
          </div>
        </div>

        {/* SIEM Rule Selector */}
        <div className="flex items-center gap-2">
          <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
            Select Rule:
          </label>
          <select
            value={selectedRuleId}
            onChange={(e) => handleSwitchRuleInStudio(e.target.value)}
            disabled={loadingRules}
            className="px-2.5 py-1 text-xs rounded-md border border-slate-800 bg-slate-950 text-slate-200 font-medium focus:outline-none focus:border-cyan-500 min-w-[240px] max-w-[380px] truncate"
          >
            {rules.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.severity})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Non-LLM Governance Notice */}
      <div className="p-2.5 rounded-lg border border-indigo-900/40 bg-indigo-950/20 text-xs text-slate-300 flex items-start gap-2.5">
        <Info className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
        <div className="text-[11px] leading-tight">
          <strong className="text-indigo-300">Phase 2 Rule Prompt Governance:</strong> All prompt templates are synthesized deterministically from ingested SIEM rule definitions. No local or external LLM is invoked during this phase.
        </div>
      </div>

      {feedback && (
        <div className={`p-2.5 rounded-md text-xs border ${
          feedback.type === "success"
            ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
            : "bg-rose-950/60 border-rose-800 text-rose-300"
        }`}>
          {feedback.text}
        </div>
      )}

      {loadingPrompt ? (
        <div className="py-12 text-center text-slate-500 text-xs">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-1.5 text-cyan-400" />
          Loading agent policy and intelligence specifications...
        </div>
      ) : !rulePrompt ? (
        <div className="p-8 border border-slate-800 rounded-lg text-center text-slate-500 text-xs space-y-2">
          <p>No prompt found for this SIEM rule.</p>
          <button
            type="button"
            onClick={handleBackToTable}
            className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs"
          >
            Return to Rules List
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-3 items-start">
          {/* Left Column: Version History Sidebar */}
          <div className="lg:col-span-1 space-y-3">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40 space-y-2">
              <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <History className="w-3.5 h-3.5 text-sky-400" /> Version History
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  {rulePrompt.versions.length} versions
                </span>
              </div>

              {/* Version List */}
              <div className="space-y-1.5 max-h-[460px] overflow-y-auto pr-0.5">
                {rulePrompt.versions.length === 0 ? (
                  <div className="p-3 text-center text-slate-500 text-xs italic">
                    No versions created yet.
                  </div>
                ) : (
                  rulePrompt.versions.map((ver) => {
                    const isActive = ver.id === rulePrompt.active_version_id;
                    const isSelected = ver.id === selectedVersionId;
                    return (
                      <div
                        key={ver.id}
                        onClick={() => handleSelectVersion(ver.id)}
                        className={`p-2 rounded-md border text-xs cursor-pointer transition-all ${
                          isSelected
                            ? "bg-slate-800 border-sky-500/80 shadow-sm"
                            : "bg-slate-950/80 border-slate-800/80 hover:bg-slate-900"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-100 flex items-center gap-1 text-[11px]">
                            v{ver.version_number}
                            {isActive && (
                              <span className="px-1 py-0.2 rounded text-[9px] bg-emerald-950 text-emerald-400 border border-emerald-800 font-semibold">
                                ACTIVE
                              </span>
                            )}
                          </span>
                          <span className={`px-1 py-0.2 rounded text-[9px] font-semibold ${
                            ver.status === "APPROVED"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                              : ver.status === "DRAFT"
                              ? "bg-amber-950 text-amber-400 border border-amber-800"
                              : "bg-slate-900 text-slate-500 border border-slate-800"
                          }`}>
                            {ver.status}
                          </span>
                        </div>

                        <div className="mt-1 text-[10px] text-slate-400 line-clamp-2">
                          {ver.change_summary}
                        </div>

                        <div className="mt-1.5 pt-1 border-t border-slate-800/60 flex items-center justify-between text-[9px] text-slate-500">
                          <span>{new Date(ver.created_at).toLocaleDateString()}</span>
                          {ver.is_template_draft ? (
                            <span className="text-sky-400 font-medium">Template</span>
                          ) : (
                            <span className="text-slate-400">Manual</span>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Action: Generate Template Draft */}
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleGenerateTemplateDraft}
                className="w-full py-1.5 px-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
              >
                <Sparkles className="w-3 h-3 text-sky-400" /> Generate Template Draft
              </button>
            </div>
          </div>

          {/* Right Column: Prompt Details & Structured Editor */}
          <div className="lg:col-span-3 space-y-3">
            {!selectedVersion ? (
              <div className="p-8 border border-slate-800 rounded-lg bg-slate-900/40 text-center space-y-3">
                <Sparkles className="w-8 h-8 text-sky-400 mx-auto" />
                <h3 className="text-sm font-semibold text-slate-200">No Prompt Baseline for This Rule</h3>
                <p className="text-xs text-slate-400 max-w-md mx-auto">
                  No prompt version currently exists for this SIEM rule. Generate a deterministic template draft from the SIEM rule specifications to establish the initial baseline.
                </p>
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={handleGenerateTemplateDraft}
                  className="px-4 py-2 bg-sky-600 hover:bg-sky-500 text-white rounded text-xs font-semibold inline-flex items-center gap-1.5 transition-colors shadow-sm"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Generate Template Draft Now
                </button>
              </div>
            ) : (
              <>
                {/* Top Toolbar */}
                <div className="p-2.5 sm:p-3 rounded-lg border border-slate-800 bg-slate-900/40 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs sm:text-sm font-bold text-slate-100">
                        Version {selectedVersion.version_number}
                      </span>
                      {isSelectedActive && (
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" /> Production Active
                        </span>
                      )}
                      {selectedVersion.is_template_draft && (
                        <span className="px-1.5 py-0.2 rounded text-[10px] font-semibold bg-sky-950 text-sky-400 border border-sky-800">
                          TEMPLATE DRAFT
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Change Note: <span className="text-slate-300 italic">{selectedVersion.change_summary}</span>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    {/* Download Rule Prompt & Configuration */}
                    <div className="relative">
                      <div className="inline-flex rounded shadow-sm">
                        <button
                          type="button"
                          onClick={() => handleExportSingleRule(selectedRuleId, "json")}
                          disabled={downloadingExport}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-l text-xs font-semibold flex items-center gap-1.5 transition-colors"
                          title="Download this rule's prompt & configuration as JSON"
                        >
                          <Download className={`w-3.5 h-3.5 text-cyan-400 ${downloadingExport ? "animate-bounce" : ""}`} />
                          Download Config
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowStudioExportMenu((prev) => !prev)}
                          disabled={downloadingExport}
                          className="px-1.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border-t border-b border-r border-slate-700 rounded-r text-xs transition-colors"
                          title="Choose export format"
                        >
                          <ChevronDown className="w-3 h-3 text-cyan-400" />
                        </button>
                      </div>

                      {showStudioExportMenu && (
                        <div className="absolute right-0 mt-1 w-44 rounded-md border border-slate-800 bg-slate-950 py-1 shadow-xl z-20 text-xs">
                          <button
                            type="button"
                            onClick={() => handleExportSingleRule(selectedRuleId, "json")}
                            className="w-full text-left px-3 py-1.5 hover:bg-slate-900 text-slate-200 flex items-center justify-between"
                          >
                            <span>JSON Format</span>
                            <span className="text-[10px] text-slate-500 font-mono">.json</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleExportSingleRule(selectedRuleId, "markdown")}
                            className="w-full text-left px-3 py-1.5 hover:bg-slate-900 text-slate-200 flex items-center justify-between"
                          >
                            <span>Markdown Doc</span>
                            <span className="text-[10px] text-slate-500 font-mono">.md</span>
                          </button>
                        </div>
                      )}
                    </div>

                    {!isEditing ? (
                      <button
                        type="button"
                        onClick={() => setIsEditing(true)}
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-semibold transition-colors"
                      >
                        Edit as New Draft
                      </button>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setIsEditing(false)}
                        className="px-2.5 py-1 bg-slate-900 hover:bg-slate-800 text-slate-400 border border-slate-800 rounded text-xs font-semibold transition-colors"
                      >
                        Cancel Editing
                      </button>
                    )}

                    {/* Approve Version Button (Gate) */}
                    {selectedVersion.status !== "APPROVED" && (
                      <button
                        type="button"
                        disabled={actionLoading || !selectedVersionId}
                        onClick={() => setShowApprovalModal(true)}
                        className="px-2.5 py-1 bg-emerald-800 hover:bg-emerald-700 text-white rounded text-xs font-semibold flex items-center gap-1 shadow-sm transition-colors"
                      >
                        <Check className="w-3 h-3" /> Approve &amp; Activate
                      </button>
                    )}

                    {/* Rollback Button (if not already active) */}
                    {!isSelectedActive && (
                      <button
                        type="button"
                        disabled={actionLoading || !selectedVersionId}
                        onClick={handleRollback}
                        className="px-2.5 py-1 bg-amber-950/80 hover:bg-amber-900/80 text-amber-300 border border-amber-800/70 rounded text-xs font-semibold flex items-center gap-1 transition-colors"
                      >
                        <RotateCcw className="w-3 h-3" /> Rollback to This
                      </button>
                    )}
                  </div>
                </div>

                {/* Structured Prompt Form */}
                <form onSubmit={handleSaveManualDraft} className="space-y-3">
                  {/* Section 1: Common SOC Baseline */}
                  <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                        <Shield className="w-3.5 h-3.5 text-sky-400" />
                        1. COMMON SOC BASELINE PROTOCOL
                      </label>
                      <span className="text-[10px] text-slate-500 font-mono">Shared across all rules</span>
                    </div>
                    {isEditing ? (
                      <textarea
                        rows={5}
                        value={editCommon}
                        onChange={(e) => setEditCommon(e.target.value)}
                        className="w-full p-2 text-xs font-mono rounded border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none focus:border-sky-500"
                      />
                    ) : (
                      <div className="p-2 text-xs font-mono rounded border border-slate-800/80 bg-slate-950 text-slate-300 whitespace-pre-wrap max-h-48 overflow-y-auto">
                        {selectedVersion.common_prompt}
                      </div>
                    )}
                  </div>

                  {/* Section 2: Rule-Specific Guidance */}
                  <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                        <FileCode className="w-3.5 h-3.5 text-cyan-400" />
                        2. RULE-SPECIFIC DIRECTIVE &amp; PATTERN DETAILS
                      </label>
                      <span className="text-[10px] text-slate-500 font-mono">Custom tailored per detection</span>
                    </div>
                    {isEditing ? (
                      <textarea
                        rows={6}
                        value={editRuleSpecific}
                        onChange={(e) => setEditRuleSpecific(e.target.value)}
                        className="w-full p-2 text-xs font-mono rounded border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none focus:border-cyan-500"
                        required
                      />
                    ) : (
                      <div className="p-2 text-xs font-mono rounded border border-slate-800/80 bg-slate-950 text-slate-300 whitespace-pre-wrap max-h-60 overflow-y-auto">
                        {selectedVersion.rule_specific_prompt}
                      </div>
                    )}
                  </div>

                  {/* Section 3 & 4: Detection Conditions & Evidence */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-1.5">
                      <label className="text-xs font-bold text-slate-200 block">
                        3. DETECTION CONDITIONS &amp; PATTERN LOGIC
                      </label>
                      {isEditing ? (
                        <textarea
                          rows={4}
                          value={editConditions}
                          onChange={(e) => setEditConditions(e.target.value)}
                          className="w-full p-2 text-xs font-mono rounded border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none"
                        />
                      ) : (
                        <div className="p-2 text-xs font-mono rounded border border-slate-800/80 bg-slate-950 text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto">
                          {selectedVersion.detection_conditions || "No conditions specified."}
                        </div>
                      )}
                    </div>

                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-1.5">
                      <label className="text-xs font-bold text-slate-200 block">
                        4. MANDATORY EVIDENCE GATHERING CHECKLIST
                      </label>
                      {isEditing ? (
                        <textarea
                          rows={4}
                          value={editEvidence}
                          onChange={(e) => setEditEvidence(e.target.value)}
                          className="w-full p-2 text-xs font-mono rounded border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none"
                        />
                      ) : (
                        <div className="p-2 text-xs font-mono rounded border border-slate-800/80 bg-slate-950 text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto">
                          {selectedVersion.required_evidence || "Standard telemetry artifacts."}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Section 5 & 6: TP / FP Indicators */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg border border-emerald-950/40 bg-emerald-950/10 space-y-1.5">
                      <label className="text-xs font-bold text-emerald-300 flex items-center gap-1.5">
                        <Check className="w-3.5 h-3.5" /> 5. TRUE POSITIVE INDICATORS (MALICIOUS ATTACK)
                      </label>
                      {isEditing ? (
                        <textarea
                          rows={4}
                          value={editTpIndicators}
                          onChange={(e) => setEditTpIndicators(e.target.value)}
                          className="w-full p-2 text-xs font-mono rounded border border-emerald-900/60 bg-slate-950 text-slate-200 focus:outline-none"
                        />
                      ) : (
                        <div className="p-2 text-xs font-mono rounded border border-emerald-900/40 bg-slate-950 text-emerald-200/90 whitespace-pre-wrap max-h-36 overflow-y-auto">
                          {selectedVersion.tp_indicators || "No specific TP indicators listed."}
                        </div>
                      )}
                    </div>

                    <div className="p-3 rounded-lg border border-blue-950/40 bg-blue-950/10 space-y-1.5">
                      <label className="text-xs font-bold text-blue-300 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" /> 6. FALSE POSITIVE INDICATORS (BENIGN OPERATIONAL NOISE)
                      </label>
                      {isEditing ? (
                        <textarea
                          rows={4}
                          value={editFpIndicators}
                          onChange={(e) => setEditFpIndicators(e.target.value)}
                          className="w-full p-2 text-xs font-mono rounded border border-blue-900/60 bg-slate-950 text-slate-200 focus:outline-none"
                        />
                      ) : (
                        <div className="p-2 text-xs font-mono rounded border border-blue-900/40 bg-slate-950 text-blue-200/90 whitespace-pre-wrap max-h-36 overflow-y-auto">
                          {selectedVersion.fp_indicators || "No specific FP indicators listed."}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Section 7 & 8: Abstention & Escalation */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-3 rounded-lg border border-amber-950/40 bg-amber-950/10 space-y-1.5">
                      <label className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
                        <AlertTriangle className="w-3.5 h-3.5" /> 7. WHEN TO ABSTAIN (REQUIRES ATTENTION)
                      </label>
                      {isEditing ? (
                        <textarea
                          rows={3}
                          value={editMissingInfo}
                          onChange={(e) => setEditMissingInfo(e.target.value)}
                          className="w-full p-2 text-xs font-mono rounded border border-amber-900/60 bg-slate-950 text-slate-200 focus:outline-none"
                        />
                      ) : (
                        <div className="p-2 text-xs font-mono rounded border border-amber-900/40 bg-slate-950 text-amber-200/90 whitespace-pre-wrap max-h-32 overflow-y-auto">
                          {selectedVersion.missing_info_criteria || "Telemetry truncated or crucial context absent."}
                        </div>
                      )}
                    </div>

                    <div className="p-3 rounded-lg border border-rose-950/40 bg-rose-950/10 space-y-1.5">
                      <label className="text-xs font-bold text-rose-300 flex items-center gap-1.5">
                        <AlertCircle className="w-3.5 h-3.5" /> 8. P1/P2 ESCALATION CONDITIONS
                      </label>
                      {isEditing ? (
                        <textarea
                          rows={3}
                          value={editEscalation}
                          onChange={(e) => setEditEscalation(e.target.value)}
                          className="w-full p-2 text-xs font-mono rounded border border-rose-900/60 bg-slate-950 text-slate-200 focus:outline-none"
                        />
                      ) : (
                        <div className="p-2 text-xs font-mono rounded border border-rose-900/40 bg-slate-950 text-rose-200/90 whitespace-pre-wrap max-h-32 overflow-y-auto">
                          {selectedVersion.escalation_conditions || "High impact asset compromise or active exfiltration."}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Section 9: Standard Q&A Checklist */}
                  <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-2">
                    <label className="text-xs font-bold text-slate-200 block">
                      9. STANDARD INVESTIGATIVE Q&amp;A CHECKLIST
                    </label>
                    <div className="space-y-1.5">
                      {isEditing ? (
                        editQuestions.map((q, idx) => (
                          <div key={idx} className="flex items-center gap-2">
                            <span className="text-[10px] text-slate-500 font-mono w-4">{idx + 1}.</span>
                            <input
                              type="text"
                              value={q}
                              onChange={(e) => {
                                const updated = [...editQuestions];
                                updated[idx] = e.target.value;
                                setEditQuestions(updated);
                              }}
                              className="flex-1 px-2.5 py-1 text-xs rounded border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none"
                            />
                            <button
                              type="button"
                              onClick={() => handleRemoveQuestion(idx)}
                              className="px-2 py-1 text-[11px] text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 rounded"
                            >
                              ✕
                            </button>
                          </div>
                        ))
                      ) : (
                        selectedVersion.analyst_questions && selectedVersion.analyst_questions.length > 0 ? (
                          <ol className="list-decimal list-inside space-y-1 text-xs text-slate-300">
                            {selectedVersion.analyst_questions.map((q, idx) => (
                              <li key={idx} className="font-mono text-[11px]">{q}</li>
                            ))}
                          </ol>
                        ) : (
                          <div className="text-xs text-slate-500 italic">No checklist questions defined.</div>
                        )
                      )}
                    </div>

                    {isEditing && (
                      <div className="flex items-center gap-2 pt-1 border-t border-slate-800/80">
                        <input
                          type="text"
                          placeholder="Add an investigative checklist question..."
                          value={newQuestionInput}
                          onChange={(e) => setNewQuestionInput(e.target.value)}
                          className="flex-1 px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200 focus:outline-none"
                        />
                        <button
                          type="button"
                          onClick={handleAddQuestion}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium border border-slate-700"
                        >
                          + Add
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Editing Controls: Save as New Version */}
                  {isEditing && (
                    <div className="p-3 rounded-lg border border-sky-900/70 bg-sky-950/20 space-y-2">
                      <div className="font-bold text-xs text-sky-300">Commit Prompt Updates as New Version</div>
                      <input
                        type="text"
                        required
                        placeholder="Enter change summary (e.g. Added LOLBin process exclusions)..."
                        value={changeSummary}
                        onChange={(e) => setChangeSummary(e.target.value)}
                        className="w-full px-2.5 py-1 text-xs rounded border border-slate-700 bg-slate-950 text-slate-200 placeholder-slate-500 focus:outline-none"
                      />
                      <div className="flex justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => setIsEditing(false)}
                          className="px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200"
                        >
                          Cancel
                        </button>
                        <button
                          type="submit"
                          disabled={actionLoading}
                          className="px-3.5 py-1 bg-sky-700 hover:bg-sky-600 text-white rounded text-xs font-bold flex items-center gap-1.5"
                        >
                          <Save className="w-3.5 h-3.5" /> Save as New Draft Version
                        </button>
                      </div>
                    </div>
                  )}
                </form>
              </>
            )}
          </div>
        </div>
      )}

      {/* Approval Gating Modal */}
      {showApprovalModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-950 border border-slate-800 rounded-lg max-w-md w-full p-4 space-y-3 shadow-2xl">
            <div className="flex items-center gap-2 text-emerald-400">
              <CheckCircle2 className="w-4 h-4" />
              <h3 className="text-sm font-bold text-slate-100">Approve Prompt Version</h3>
            </div>
            <p className="text-xs text-slate-400">
              Approving Version {selectedVersion?.version_number} will set it as the production baseline prompt for <strong>{rulePrompt?.rule_name}</strong> and archive previous active versions.
            </p>
            <div>
              <label className="text-[11px] font-semibold text-slate-300 block mb-1">Approval Sign-off Summary</label>
              <input
                type="text"
                value={approvalSummary}
                onChange={(e) => setApprovalSummary(e.target.value)}
                className="w-full px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-900 text-slate-200 focus:outline-none"
              />
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={() => setShowApprovalModal(false)}
                className="px-2.5 py-1 text-xs text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleApprove}
                className="px-3.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs font-bold"
              >
                Confirm Approval &amp; Activate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
