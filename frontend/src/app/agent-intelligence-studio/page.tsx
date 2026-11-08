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
  Activity,
  Cpu,
  XCircle,
  ExternalLink,
  Sliders,
  Award,
  Database,
  GitBranch,
} from "lucide-react";
import {
  api,
  RuleItem,
  RulePrompt,
  PromptVersion,
  RulePromptSummaryItem,
  RuleIntelligenceData,
  PolicyQualityAssessmentResponse,
  QualityGateResult,
  QualitySummaryItem,
  PolicyDriftEventItem,
} from "@/lib/api";

export default function AgentIntelligenceStudioPage() {
  // Navigation / View mode
  const [viewMode, setViewMode] = useState<"table" | "studio">("table");
  const [studioTab, setStudioTab] = useState<"editor" | "intelligence" | "contract" | "quality" | "simulation" | "drift">("editor");

  // Rules & Summaries State
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [summaries, setSummaries] = useState<RulePromptSummaryItem[]>([]);
  const [qualitySummary, setQualitySummary] = useState<QualitySummaryItem | null>(null);
  const [loadingRules, setLoadingRules] = useState(true);
  const [loadingSummaries, setLoadingSummaries] = useState(true);

  // Table Filters State
  const [searchFilter, setSearchFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [baselineFilter, setBaselineFilter] = useState("");
  const [archetypeFilter, setArchetypeFilter] = useState("");
  const [completenessFilter, setCompletenessFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 15;

  // Studio / Editor State
  const [selectedRuleId, setSelectedRuleId] = useState<string>("");
  const [rulePrompt, setRulePrompt] = useState<RulePrompt | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error" | "warning"; text: string } | null>(null);

  // Rule Intelligence & Semantics State
  const [intelligenceData, setIntelligenceData] = useState<RuleIntelligenceData | null>(null);
  const [loadingIntelligence, setLoadingIntelligence] = useState(false);

  // Policy Quality Validation State
  const [qualityAssessment, setQualityAssessment] = useState<PolicyQualityAssessmentResponse | null>(null);
  const [loadingQuality, setLoadingQuality] = useState(false);

  // Policy Simulation State
  const [simulationResult, setSimulationResult] = useState<any | null>(null);
  const [loadingSimulation, setLoadingSimulation] = useState(false);

  // Drift Events State
  const [driftEvents, setDriftEvents] = useState<PolicyDriftEventItem[]>([]);
  const [loadingDrift, setLoadingDrift] = useState(false);

  // Bulk Audit Modal State
  const [showBulkAuditModal, setShowBulkAuditModal] = useState(false);
  const [bulkAuditJob, setBulkAuditJob] = useState<any | null>(null);
  const [bulkAuditLoading, setBulkAuditLoading] = useState(false);

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
      const qSummary = await api.getPolicyQualitySummary();
      setQualitySummary(qSummary);
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
    setIntelligenceData(null);
    setQualityAssessment(null);
    setSimulationResult(null);
    setDriftEvents([]);
  };

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

  const fetchIntelligence = async (ruleId: string) => {
    if (!ruleId) return;
    setLoadingIntelligence(true);
    try {
      const intel = await api.getRuleIntelligence(ruleId);
      setIntelligenceData(intel);
    } catch (err: any) {
      console.error("Failed to load rule intelligence:", err);
    } finally {
      setLoadingIntelligence(false);
    }
  };

  const fetchQualityValidation = async (ruleId: string, versionId?: string) => {
    if (!ruleId) return;
    setLoadingQuality(true);
    try {
      const qRes = await api.validatePolicyQuality(ruleId, versionId);
      setQualityAssessment(qRes);
    } catch (err: any) {
      console.error("Failed to validate policy quality:", err);
    } finally {
      setLoadingQuality(false);
    }
  };

  const fetchDriftEvents = async (ruleId: string) => {
    if (!ruleId) return;
    setLoadingDrift(true);
    try {
      const evs = await api.getRuleDriftEvents(ruleId);
      setDriftEvents(evs);
    } catch (err: any) {
      console.error("Failed to load drift events:", err);
    } finally {
      setLoadingDrift(false);
    }
  };

  useEffect(() => {
    if (viewMode === "studio" && selectedRuleId) {
      fetchPrompt(selectedRuleId);
      fetchIntelligence(selectedRuleId);
      fetchDriftEvents(selectedRuleId);
    }
  }, [viewMode, selectedRuleId]);

  useEffect(() => {
    if (selectedRuleId && selectedVersionId) {
      fetchQualityValidation(selectedRuleId, selectedVersionId);
    }
  }, [selectedRuleId, selectedVersionId]);

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

  const handleOpenStudioForRule = (ruleId: string) => {
    setSelectedRuleId(ruleId);
    clearForm();
    setViewMode("studio");
    setStudioTab("editor");
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("rule_id", ruleId);
      window.history.pushState({}, "", url.toString());
    }
  };

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

  const handleSwitchRuleInStudio = (ruleId: string) => {
    setSelectedRuleId(ruleId);
    clearForm();
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("rule_id", ruleId);
      window.history.pushState({}, "", url.toString());
    }
  };

  // Generate AIS 2.0 Intelligent Draft
  const handleGenerateIntelligentDraft = async () => {
    if (!selectedRuleId) return;
    setActionLoading(true);
    setFeedback(null);
    try {
      const newDraft = await api.generateIntelligentDraft(selectedRuleId);
      await fetchPrompt(selectedRuleId);
      await fetchIntelligence(selectedRuleId);
      setSelectedVersionId(newDraft.id);
      loadVersionIntoForm(newDraft);
      setFeedback({
        type: "success",
        text: `Intelligent policy Version ${newDraft.version_number} synthesized from detection semantics and archetype rules.`,
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
        text: `Manual draft Version ${newDraft.version_number} saved successfully. Quality revalidation required.`,
      });
      loadSummaries();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message });
    } finally {
      setActionLoading(false);
    }
  };

  // Run Simulation Lab evaluation
  const handleRunSimulation = async () => {
    if (!selectedRuleId) return;
    setLoadingSimulation(true);
    setFeedback(null);
    try {
      const res = await api.evaluatePolicySimulation(selectedRuleId, selectedVersionId);
      setSimulationResult(res);
      setStudioTab("simulation");
      const stat = res.status || res.simulation_status || "COMPLETED";
      setFeedback({
        type: stat === "FAILED" || stat === "EVALUATED_FAILED" ? "warning" : "success",
        text: `Simulation Lab completed: ${res.sample_count} historical incidents evaluated. Status: ${stat}`,
      });
      // Synchronize G8 quality gate with fresh simulation results
      if (selectedVersionId) {
        await fetchQualityValidation(selectedRuleId, selectedVersionId);
      }
    } catch (err: any) {
      setFeedback({ type: "error", text: `Simulation failed: ${err.message}` });
    } finally {
      setLoadingSimulation(false);
    }
  };

  // Acknowledge Drift
  const handleAcknowledgeDrift = async () => {
    if (!selectedRuleId) return;
    setActionLoading(true);
    try {
      const res = await api.acknowledgeDriftEvents(selectedRuleId);
      await fetchDriftEvents(selectedRuleId);
      setFeedback({
        type: "success",
        text: `Acknowledged ${res.acknowledged_count} drift event(s). Policy monitoring updated.`,
      });
      loadSummaries();
    } catch (err: any) {
      setFeedback({ type: "error", text: `Failed to acknowledge drift: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  // Bulk Quality Audit trigger
  const handleStartBulkAudit = async () => {
    setBulkAuditLoading(true);
    setShowBulkAuditModal(true);
    try {
      const job = await api.startBulkQualityAudit();
      setBulkAuditJob(job);
      await loadSummaries();
    } catch (err: any) {
      setFeedback({ type: "error", text: `Bulk audit failed: ${err.message}` });
    } finally {
      setBulkAuditLoading(false);
    }
  };

  const handleApprove = async () => {
    if (!selectedRuleId || !selectedVersionId) return;
    const versionBelongs = rulePrompt?.versions?.some((v) => v.id === selectedVersionId);
    if (!versionBelongs) {
      setFeedback({
        type: "error",
        text: "The selected prompt version does not match this rule.",
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
        text: `Version ${approved.version_number} approved and activated as production baseline. Evidence Contract synchronized.`,
      });
      loadSummaries();
    } catch (err: any) {
      setFeedback({ type: "error", text: `Approval blocked: ${err.message}` });
    } finally {
      setActionLoading(false);
    }
  };

  const handleRollback = async () => {
    if (!selectedRuleId || !selectedVersionId) return;
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

  const getScoreBadge = (score: number | null | undefined) => {
    if (score === null || score === undefined) {
      return "bg-slate-900 text-slate-400 border-slate-800";
    }
    if (score >= 80) {
      return "bg-emerald-950/80 text-emerald-300 border-emerald-800";
    }
    if (score >= 60) {
      return "bg-amber-950/80 text-amber-300 border-amber-800";
    }
    return "bg-rose-950/80 text-rose-300 border-rose-800";
  };

  // Filter summaries for table
  const filteredSummaries = summaries.filter((item) => {
    if (searchFilter) {
      const q = searchFilter.toLowerCase();
      const matchName = item.rule_name.toLowerCase().includes(q);
      const matchEvent = item.event_type.toLowerCase().includes(q);
      const matchSource = (item.data_source || "").toLowerCase().includes(q);
      const matchArchetype = (item.detection_archetype || "").toLowerCase().includes(q);
      if (!matchName && !matchEvent && !matchSource && !matchArchetype) return false;
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
    if (archetypeFilter && item.detection_archetype !== archetypeFilter) {
      return false;
    }
    if (completenessFilter && item.definition_completeness !== completenessFilter) {
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
  const incompleteDefinitionCount = summaries.filter((s) => s.definition_completeness === "INCOMPLETE").length;
  const driftAlertCount = summaries.filter((s) => s.revalidation_required).length;

  const selectedVersion = rulePrompt?.versions.find((v) => v.id === selectedVersionId);
  const isSelectedActive = selectedVersion?.id === rulePrompt?.active_version_id;

  // Archetypes List for Filter
  const archetypeOptions = Array.from(
    new Set(summaries.map((s) => s.detection_archetype).filter(Boolean))
  );

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
                Agent Intelligence Studio 2.0
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono">
                Detection-Aware Policy Engine
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              SIEM semantics parsing, 12 detection archetypes, 8-gate quality validation, simulation regression testing, and drift governance.
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

            {/* Bulk Quality Audit Trigger */}
            <button
              onClick={handleStartBulkAudit}
              disabled={bulkAuditLoading}
              className="px-2.5 py-1 text-xs rounded border border-indigo-800/80 bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-200 font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
              title="Execute bulk policy quality assessment across all rules (chunked in 100s)"
            >
              <Layers className="w-3.5 h-3.5 text-indigo-400" />
              Bulk Audit Rules
            </button>

            {/* Download Rule-Wise Prompts */}
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
                  {downloadingExport ? "Exporting..." : "Download Config"}
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
                Open Studio <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
        </div>

        {/* Top Metrics Cards (AIS 2.0 Enhanced) */}
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
          <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/40">
            <div className="text-[10px] uppercase font-semibold text-slate-400 flex items-center justify-between">
              Monitored Rules
              <FileCode className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <div className="text-lg font-bold text-slate-100 mt-1">{totalRulesCount}</div>
            <div className="text-[9px] text-slate-500 mt-0.5">Active SIEM rules</div>
          </div>

          <div className="p-2.5 rounded-lg border border-emerald-900/50 bg-emerald-950/20">
            <div className="text-[10px] uppercase font-semibold text-emerald-400 flex items-center justify-between">
              Approved
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-lg font-bold text-emerald-300 mt-1">{approvedPromptsCount}</div>
            <div className="text-[9px] text-emerald-500/80 mt-0.5">
              {totalRulesCount ? Math.round((approvedPromptsCount / totalRulesCount) * 100) : 0}% active
            </div>
          </div>

          <div className="p-2.5 rounded-lg border border-sky-900/50 bg-sky-950/20">
            <div className="text-[10px] uppercase font-semibold text-sky-400 flex items-center justify-between">
              Template Drafts
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            </div>
            <div className="text-lg font-bold text-sky-300 mt-1">{draftOnlyCount}</div>
            <div className="text-[9px] text-sky-500/80 mt-0.5">Drafts awaiting review</div>
          </div>

          <div className="p-2.5 rounded-lg border border-cyan-900/50 bg-cyan-950/20">
            <div className="text-[10px] uppercase font-semibold text-cyan-400 flex items-center justify-between">
              Avg Quality Score
              <Award className="w-3.5 h-3.5 text-cyan-400" />
            </div>
            <div className="text-lg font-bold text-cyan-300 mt-1">
              {qualitySummary ? `${Math.round(qualitySummary.quality_score_average)}/100` : "—"}
            </div>
            <div className="text-[9px] text-cyan-500/80 mt-0.5">Static verification index</div>
          </div>

          <div className="p-2.5 rounded-lg border border-amber-900/50 bg-amber-950/20">
            <div className="text-[10px] uppercase font-semibold text-amber-400 flex items-center justify-between">
              Incomplete Specs
              <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-lg font-bold text-amber-300 mt-1">{incompleteDefinitionCount}</div>
            <div className="text-[9px] text-amber-500/80 mt-0.5">Unresolved SIEM logic</div>
          </div>

          <div className="p-2.5 rounded-lg border border-rose-900/50 bg-rose-950/20">
            <div className="text-[10px] uppercase font-semibold text-rose-400 flex items-center justify-between">
              Drift / Revalidate
              <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />
            </div>
            <div className="text-lg font-bold text-rose-300 mt-1">{driftAlertCount}</div>
            <div className="text-[9px] text-rose-500/80 mt-0.5">Requires re-audit</div>
          </div>
        </div>

        {/* Informational Architecture Banner */}
        <div className="p-2.5 rounded-lg border border-cyan-900/40 bg-cyan-950/20 text-xs text-slate-300 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
          <div className="text-[11px] leading-tight space-y-0.5">
            <div>
              <strong className="text-cyan-300">Agent Intelligence Studio 2.0 Governance:</strong> SIEM detection rules are parsed via authoritative telemetry distinction. 
              Policies are classified into 12 archetypes and validated through 8 mandatory quality gates (G1–G8). Drafts with missing definitions (e.g. unverified thresholds) remain provisional and cannot be approved.
            </div>
          </div>
        </div>

        {/* Filter & Search Toolbar */}
        <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-900/30 flex flex-wrap items-center justify-between gap-2">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchFilter}
              onChange={(e) => {
                setSearchFilter(e.target.value);
                setPage(1);
              }}
              placeholder="Search rules, archetypes, event types, or data sources..."
              className="w-full pl-8 pr-3 py-1.5 text-xs rounded border border-slate-800 bg-slate-950 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <select
              value={archetypeFilter}
              onChange={(e) => {
                setArchetypeFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Archetypes</option>
              {archetypeOptions.map((arch) => (
                <option key={arch} value={arch}>
                  {arch}
                </option>
              ))}
            </select>

            <select
              value={completenessFilter}
              onChange={(e) => {
                setCompletenessFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Definitions</option>
              <option value="VERIFIED">Verified Definition</option>
              <option value="INCOMPLETE">Incomplete / Unresolved</option>
              <option value="UNKNOWN">Unknown Status</option>
            </select>

            <select
              value={severityFilter}
              onChange={(e) => {
                setSeverityFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:border-cyan-500"
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
              className="px-2.5 py-1 text-xs rounded border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="">All Baselines</option>
              <option value="APPROVED">Production Approved</option>
              <option value="DRAFT">Template Draft</option>
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
                  <th className="py-2.5 px-2 font-semibold">Severity</th>
                  <th className="py-2.5 px-2 font-semibold">Archetype</th>
                  <th className="py-2.5 px-2 font-semibold">Definition</th>
                  <th className="py-2.5 px-2 font-semibold">Quality Score</th>
                  <th className="py-2.5 px-3 font-semibold">Baseline Status</th>
                  <th className="py-2.5 px-2 font-semibold">Drift Flag</th>
                  <th className="py-2.5 px-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loadingSummaries ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-400 text-xs">
                      <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
                      Loading Agent Intelligence Studio rule directory...
                    </td>
                  </tr>
                ) : paginatedSummaries.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-500 text-xs">
                      No detection rules match the specified search or filter criteria.
                    </td>
                  </tr>
                ) : (
                  paginatedSummaries.map((item) => {
                    const isApproved = item.has_approved_prompt;
                    const hasDraft = !isApproved && item.total_versions > 0;
                    const isIncomplete = item.definition_completeness === "INCOMPLETE";

                    return (
                      <tr
                        key={item.rule_id}
                        onClick={() => handleOpenStudioForRule(item.rule_id)}
                        className="hover:bg-slate-900/60 cursor-pointer transition-colors group"
                      >
                        <td className="py-2 px-3">
                          <div className="font-semibold text-slate-200 group-hover:text-cyan-400 transition-colors">
                            {item.rule_name}
                          </div>
                          <div className="text-[10px] font-mono text-slate-400 mt-0.5 flex items-center gap-1.5">
                            <span>{item.event_type}</span>
                            {item.data_source && (
                              <span className="text-slate-500">({item.data_source})</span>
                            )}
                          </div>
                        </td>

                        <td className="py-2 px-2">
                          <span className={`px-1.5 py-0.5 rounded border text-[9px] font-bold ${getSeverityBadge(item.severity)}`}>
                            {item.severity}
                          </span>
                        </td>

                        <td className="py-2 px-2">
                          <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-sky-950/80 text-sky-300 border border-sky-800/70">
                            {item.detection_archetype || "UNKNOWN"}
                          </span>
                        </td>

                        <td className="py-2 px-2">
                          {item.definition_completeness === "VERIFIED" ? (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                              <CheckCircle2 className="w-2.5 h-2.5" /> VERIFIED
                            </span>
                          ) : isIncomplete ? (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-800" title="Authoritative threshold or logic missing. Blocked from approval.">
                              <AlertCircle className="w-2.5 h-2.5" /> INCOMPLETE
                            </span>
                          ) : (
                            <span className="px-1.5 py-0.5 rounded text-[9px] text-slate-400 font-mono">
                              {item.definition_completeness || "UNKNOWN"}
                            </span>
                          )}
                        </td>

                        <td className="py-2 px-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${getScoreBadge(item.quality_score)}`}>
                            {item.quality_score !== null && item.quality_score !== undefined
                              ? `${item.quality_score}/100`
                              : "—"}
                          </span>
                        </td>

                        <td className="py-2 px-3">
                          {isApproved ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800">
                              <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                              v{item.active_version_number || 1} Active
                            </span>
                          ) : hasDraft ? (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-sky-950 text-sky-400 border border-sky-800">
                              <Sparkles className="w-3 h-3 text-sky-400" />
                              v{item.active_version_number || 1} Draft
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-900 text-slate-400 border border-slate-800">
                              No Baseline
                            </span>
                          )}
                        </td>

                        <td className="py-2 px-2">
                          {item.revalidation_required ? (
                            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-bold bg-rose-950 text-rose-300 border border-rose-800 animate-pulse" title="SIEM rule changed or feedback logged. Revalidation required.">
                              <AlertTriangle className="w-2.5 h-2.5" /> DRIFT
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-600 font-mono">Clean</span>
                          )}
                        </td>

                        <td className="py-2 px-3 text-right">
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

        {/* Bulk Audit Modal */}
        {showBulkAuditModal && (
          <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-slate-950 border border-slate-800 rounded-lg max-w-lg w-full p-4 space-y-3 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2 text-indigo-400">
                  <Layers className="w-4 h-4" />
                  <h3 className="text-sm font-bold text-slate-100">Bulk Quality Audit Engine</h3>
                </div>
                <button
                  onClick={() => setShowBulkAuditModal(false)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  ✕
                </button>
              </div>

              {bulkAuditLoading ? (
                <div className="py-8 text-center text-slate-400 text-xs space-y-2">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto text-indigo-400" />
                  <p>Processing batch audit across detection rules (bounded chunking: 100/chunk)...</p>
                </div>
              ) : bulkAuditJob ? (
                <div className="space-y-3 text-xs">
                  <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 space-y-1">
                    <div className="flex justify-between text-slate-400">
                      <span>Job ID:</span>
                      <span className="font-mono text-slate-200">{bulkAuditJob.job_id}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Rules Evaluated:</span>
                      <span className="font-bold text-slate-100">{bulkAuditJob.total_rules_processed}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Static Checks Passed:</span>
                      <span className="text-emerald-400 font-semibold">{bulkAuditJob.passed_count}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Reviews Required:</span>
                      <span className="text-amber-400 font-semibold">{bulkAuditJob.review_required_count}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Critical / Hard Blockers:</span>
                      <span className="text-rose-400 font-semibold">{bulkAuditJob.critical_count}</span>
                    </div>
                  </div>
                  <p className="text-[11px] text-slate-400 italic">
                    Bulk assessment operates in strict read-only mode and does not alter approved baselines.
                  </p>
                </div>
              ) : (
                <p className="text-xs text-slate-400">Ready to initiate bulk static validation.</p>
              )}

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setShowBulkAuditModal(false)}
                  className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-semibold"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // =========================================================================
  // VIEW 2: RULE PROMPT STUDIO (EDITOR & INSPECTION VIEW)
  // =========================================================================
  const isIncompleteDefinition = intelligenceData?.semantics?.definition_status === "INCOMPLETE";
  const blockingIssuesList = qualityAssessment?.blocking_issues || qualityAssessment?.blocking_findings || [];
  const hasHardGateFailure = blockingIssuesList.length > 0;
  const isApprovalEligible = (qualityAssessment?.approval_eligible ?? false) && !isIncompleteDefinition && !hasHardGateFailure;
  const gateList: QualityGateResult[] = qualityAssessment?.gate_results
    ? Object.values(qualityAssessment.gate_results)
    : qualityAssessment?.gates || [];

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
            Rules List
          </button>

          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100">
                Agent Intelligence Studio 2.0
              </h1>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-semibold bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono">
                {intelligenceData?.classification?.primary_archetype || "DETECTION ENGINE"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Governed policy generation, 8-gate quality validation, evidence contract alignment, and simulation regression checks.
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

      {/* AIS 2.0 Policy Governance Bar: Quality Score & Approval Gate Status */}
      <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {/* Quality Score Indicator */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold text-slate-400">Quality Score:</span>
            <span className={`px-2 py-0.5 rounded text-xs font-mono font-bold border ${getScoreBadge(qualityAssessment?.quality_score)}`}>
              {qualityAssessment ? `${qualityAssessment.quality_score}/100` : "—"}
            </span>
          </div>

          {/* Validation Status Badge */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase font-bold text-slate-400">Status:</span>
            {isApprovalEligible ? (
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> APPROVAL ELIGIBLE
              </span>
            ) : selectedVersion?.status === "APPROVED" ? (
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> ACTIVE PRODUCTION
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-950 text-rose-300 border border-rose-800 flex items-center gap-1">
                <XCircle className="w-3 h-3" /> REWORK REQUIRED
              </span>
            )}
          </div>

          {/* Definition Status */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase font-bold text-slate-400">Definition:</span>
            {isIncompleteDefinition ? (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-amber-950 text-amber-300 border border-amber-800 flex items-center gap-1" title="Authoritative threshold is missing. Draft remains provisional.">
                <AlertCircle className="w-3 h-3 text-amber-400" /> INCOMPLETE
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800">
                VERIFIED
              </span>
            )}
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            disabled={actionLoading || loadingPrompt}
            onClick={handleGenerateIntelligentDraft}
            className="px-2.5 py-1 text-xs rounded border border-cyan-800/80 bg-cyan-950/60 hover:bg-cyan-900/80 text-cyan-200 font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Synthesize Intelligent Draft
          </button>

          <button
            type="button"
            disabled={loadingQuality || !selectedVersionId}
            onClick={() => fetchQualityValidation(selectedRuleId, selectedVersionId)}
            className="px-2.5 py-1 text-xs rounded border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium flex items-center gap-1.5 transition-colors"
          >
            <Award className="w-3.5 h-3.5 text-cyan-400" />
            Validate Quality
          </button>

          <button
            type="button"
            disabled={loadingSimulation || !selectedVersionId}
            onClick={handleRunSimulation}
            className="px-2.5 py-1 text-xs rounded border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium flex items-center gap-1.5 transition-colors"
          >
            <Cpu className="w-3.5 h-3.5 text-purple-400" />
            Run Simulation
          </button>

          {/* Approve Button */}
          {selectedVersion && selectedVersion.status !== "APPROVED" && (
            <button
              type="button"
              disabled={actionLoading || !selectedVersionId || !isApprovalEligible}
              onClick={() => setShowApprovalModal(true)}
              className={`px-3 py-1 rounded text-xs font-bold flex items-center gap-1 shadow-sm transition-colors ${
                isApprovalEligible
                  ? "bg-emerald-700 hover:bg-emerald-600 text-white"
                  : "bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700"
              }`}
              title={
                !isApprovalEligible
                  ? "Approval blocked by hard quality gate failures or incomplete rule specifications."
                  : "Approve policy for production active baseline"
              }
            >
              <Check className="w-3.5 h-3.5" /> Approve &amp; Activate
            </button>
          )}

          {/* Rollback Button */}
          {!isSelectedActive && selectedVersion && (
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

      {/* Critical Incomplete Definition Alert (e.g. PH_RULE_LARGE_OUTBOUND_XFER) */}
      {isIncompleteDefinition && (
        <div className="p-3 rounded-lg border border-amber-800/80 bg-amber-950/30 text-xs text-amber-200 flex items-start gap-2.5">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <div className="font-bold text-amber-300">
              Rule Definition Incomplete — Approval Gate 1 (G1) Blocked
            </div>
            <p className="text-[11px] text-amber-200/90 leading-relaxed">
              Authoritative SIEM detection rule specifications are missing or unverified. Observed telemetry fields (such as byte counts) are not assumed to be detection thresholds. 
              The synthesized policy remains a <strong>provisional draft</strong> with explicit unresolved requirements. It cannot be approved for autonomous production use until authoritative criteria are supplied.
            </p>
          </div>
        </div>
      )}

      {/* Feedback Alert */}
      {feedback && (
        <div className={`p-2.5 rounded-md text-xs border ${
          feedback.type === "success"
            ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
            : feedback.type === "warning"
            ? "bg-amber-950/60 border-amber-800 text-amber-300"
            : "bg-rose-950/60 border-rose-800 text-rose-300"
        }`}>
          {feedback.text}
        </div>
      )}

      {/* Sub-Navigation Tabs */}
      <div className="flex border-b border-slate-800 space-x-1 text-xs">
        <button
          onClick={() => setStudioTab("editor")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            studioTab === "editor"
              ? "border-cyan-400 text-cyan-300 bg-slate-900/40"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileCode className="w-3.5 h-3.5" />
          Policy Editor (9 Sections)
        </button>

        <button
          onClick={() => setStudioTab("quality")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            studioTab === "quality"
              ? "border-cyan-400 text-cyan-300 bg-slate-900/40"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Award className="w-3.5 h-3.5" />
          Quality Gates (G1–G8)
          {blockingIssuesList.length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[9px] bg-rose-950 text-rose-300 border border-rose-800">
              {blockingIssuesList.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setStudioTab("intelligence")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            studioTab === "intelligence"
              ? "border-cyan-400 text-cyan-300 bg-slate-900/40"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          SIEM Semantics &amp; Archetype
        </button>

        <button
          onClick={() => setStudioTab("contract")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            studioTab === "contract"
              ? "border-cyan-400 text-cyan-300 bg-slate-900/40"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          Evidence Contract
        </button>

        <button
          onClick={() => setStudioTab("simulation")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            studioTab === "simulation"
              ? "border-cyan-400 text-cyan-300 bg-slate-900/40"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          Simulation Lab
        </button>

        <button
          onClick={() => setStudioTab("drift")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
            studioTab === "drift"
              ? "border-cyan-400 text-cyan-300 bg-slate-900/40"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <GitBranch className="w-3.5 h-3.5" />
          Drift &amp; Monitoring
          {driftEvents.filter((d) => !d.acknowledged).length > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[9px] bg-rose-950 text-rose-300 border border-rose-800">
              {driftEvents.filter((d) => !d.acknowledged).length}
            </span>
          )}
        </button>
      </div>

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

              {/* Action: Generate Intelligent Draft */}
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleGenerateIntelligentDraft}
                className="w-full py-1.5 px-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
              >
                <Sparkles className="w-3 h-3 text-cyan-400" /> Generate Intelligent Draft
              </button>
            </div>
          </div>

          {/* Right Column: Tabbed Workspace */}
          <div className="lg:col-span-3 space-y-3">
            {/* TAB 1: POLICY EDITOR */}
            {studioTab === "editor" && (
              <>
                {!selectedVersion ? (
                  <div className="p-8 border border-slate-800 rounded-lg bg-slate-900/40 text-center space-y-3">
                    <Sparkles className="w-8 h-8 text-cyan-400 mx-auto" />
                    <h3 className="text-sm font-semibold text-slate-200">No Policy Baseline for This Rule</h3>
                    <p className="text-xs text-slate-400 max-w-md mx-auto">
                      Generate an intelligent policy draft synthesized from SIEM rule specifications and detection archetypes.
                    </p>
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={handleGenerateIntelligentDraft}
                      className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded text-xs font-semibold inline-flex items-center gap-1.5 transition-colors shadow-sm"
                    >
                      <Sparkles className="w-3.5 h-3.5" /> Synthesize Intelligent Draft Now
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
                              INTELLIGENT DRAFT
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          Change Note: <span className="text-slate-300 italic">{selectedVersion.change_summary}</span>
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleExportSingleRule(selectedRuleId, "json")}
                          disabled={downloadingExport}
                          className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded text-xs font-semibold flex items-center gap-1.5 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5 text-cyan-400" /> Download
                        </button>

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
                      </div>
                    </div>

                    {/* Structured 9-Section Policy Form */}
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
                            <Check className="w-3.5 h-3.5" /> 5. TRUE POSITIVE INDICATORS (ATTACK EVIDENCE)
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
                            <CheckCircle2 className="w-3.5 h-3.5" /> 6. FALSE POSITIVE INDICATORS (BENIGN NOISE)
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
              </>
            )}

            {/* TAB 2: QUALITY GATES (G1–G8) */}
            {studioTab === "quality" && (
              <div className="space-y-3">
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                        <Award className="w-4 h-4 text-cyan-400" />
                        Policy Quality Assessment (8 Mandatory Gates)
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Deterministic static analysis of policy integrity, relevance, evidence feasibility, and escalation safety.
                      </p>
                    </div>
                    <button
                      onClick={() => fetchQualityValidation(selectedRuleId, selectedVersionId)}
                      disabled={loadingQuality}
                      className="px-2.5 py-1 text-xs rounded border border-slate-700 bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center gap-1.5"
                    >
                      <RefreshCw className={`w-3 h-3 text-cyan-400 ${loadingQuality ? "animate-spin" : ""}`} />
                      Revalidate
                    </button>
                  </div>
                </div>

                {qualityAssessment ? (
                  <div className="space-y-3">
                    {/* Score Summary Box - Separates Structural Quality from Empirical Validation */}
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-xs">
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Overall Quality</div>
                        <div className="text-xl font-bold font-mono text-slate-100">{qualityAssessment.quality_score} / 100</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Structural (G1–G7)</div>
                        <div className="text-xl font-bold font-mono text-cyan-400">
                          {qualityAssessment.structural_quality_score !== null && qualityAssessment.structural_quality_score !== undefined
                            ? `${qualityAssessment.structural_quality_score} / 100`
                            : `${Math.round(qualityAssessment.quality_score)} / 100`}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Empirical (G8)</div>
                        <div className={`text-sm font-bold font-mono mt-1 ${
                          (qualityAssessment.empirical_validation_status === "EVALUATED_PASSED" || qualityAssessment.simulation_status === "EVALUATED_PASSED")
                            ? "text-emerald-400"
                            : (qualityAssessment.empirical_validation_status === "INSUFFICIENT_DATA" || qualityAssessment.simulation_status === "INSUFFICIENT_DATA")
                            ? "text-amber-400"
                            : "text-slate-400"
                        }`}>
                          {qualityAssessment.empirical_validation_status || qualityAssessment.simulation_status || "NOT_EVALUATED"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Blocking Issues</div>
                        <div className="text-xl font-bold font-mono text-rose-400">{blockingIssuesList.length}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Approval Eligible</div>
                        <div className={`text-sm font-bold mt-1 ${isApprovalEligible ? "text-emerald-400" : "text-amber-400"}`}>
                          {isApprovalEligible ? "YES" : "NO (REWORK)"}
                        </div>
                      </div>
                    </div>

                    {/* Blocking Findings Box */}
                    {blockingIssuesList.length > 0 && (
                      <div className="p-3 rounded-lg border border-rose-900/60 bg-rose-950/20 text-xs text-rose-300 space-y-1.5">
                        <div className="font-bold flex items-center gap-1.5 text-rose-300">
                          <XCircle className="w-4 h-4 text-rose-400" />
                          Blocking Issues Detected ({blockingIssuesList.length}):
                        </div>
                        <ul className="list-disc list-inside space-y-0.5 text-[11px] font-mono text-rose-200">
                          {blockingIssuesList.map((finding: string, idx: number) => (
                            <li key={idx}>{finding}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* 8 Gates Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                      {gateList.map((gate: QualityGateResult) => {
                        const isPass = gate.status === "PASSED";
                        const isWarn = gate.status === "WARNING";
                        return (
                          <div
                            key={gate.gate_id}
                            className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                              isPass
                                ? "bg-slate-900/30 border-slate-800"
                                : isWarn
                                ? "bg-amber-950/20 border-amber-900/60"
                                : "bg-rose-950/20 border-rose-900/60"
                            }`}
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-slate-200 flex items-center gap-1.5">
                                {isPass ? (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                                ) : isWarn ? (
                                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                                ) : (
                                  <XCircle className="w-3.5 h-3.5 text-rose-400" />
                                )}
                                {gate.gate_id}: {gate.gate_name}
                              </span>
                              <span className="font-mono text-[10px] text-slate-400">
                                {gate.score}/{gate.max_score} pts
                              </span>
                            </div>

                            <p className="text-[11px] text-slate-400 leading-relaxed">
                              {gate.details}
                            </p>

                            {gate.blocking_findings && gate.blocking_findings.length > 0 && (
                              <div className="pt-1 text-[10px] text-rose-400 font-mono space-y-0.5">
                                {gate.blocking_findings.map((bf: string, i: number) => (
                                  <div key={i}>• {bf}</div>
                                ))}
                              </div>
                            )}

                            {gate.warnings && gate.warnings.length > 0 && (
                              <div className="pt-1 text-[10px] text-amber-400 font-mono space-y-0.5">
                                {gate.warnings.map((wf: string, i: number) => (
                                  <div key={i}>• {wf}</div>
                                ))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>

                    {/* Recommendations Box */}
                    {qualityAssessment.recommendations && qualityAssessment.recommendations.length > 0 && (
                      <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 text-xs text-slate-300 space-y-1.5">
                        <div className="font-bold text-cyan-300 flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                          Remediation Recommendations:
                        </div>
                        <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-400">
                          {qualityAssessment.recommendations.map((rec: string, idx: number) => (
                            <li key={idx}>{rec}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    No quality assessment available. Click &quot;Revalidate&quot; to inspect policy quality.
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: SIEM SEMANTICS & ARCHETYPE */}
            {studioTab === "intelligence" && (
              <div className="space-y-3">
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-cyan-400" />
                    Detection Semantics &amp; Behavioral Archetype
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Analyzed SIEM detection rule logic, verified parameters vs observed telemetry, and behavioral classification.
                  </p>
                </div>

                {intelligenceData ? (
                  <div className="space-y-3 text-xs">
                    {/* Semantics Breakdown */}
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-2">
                      <div className="font-bold text-slate-200 border-b border-slate-800 pb-1 flex justify-between">
                        <span>Rule Semantics &amp; Provenance</span>
                        <span className="font-mono text-cyan-400 text-[10px]">{intelligenceData.semantics?.siem_vendor}</span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
                        <div>
                          <span className="text-slate-500 block">Definition Status:</span>
                          <span className={`font-semibold ${isIncompleteDefinition ? "text-amber-400" : "text-emerald-400"}`}>
                            {intelligenceData.semantics?.definition_status}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Data Source Provenance:</span>
                          <span className="text-slate-200 font-mono">{intelligenceData.semantics?.source_provenance}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Primary Behavior:</span>
                          <span className="text-slate-200 font-mono">{intelligenceData.semantics?.primary_behavior}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Configured Threshold:</span>
                          <span className="text-slate-200 font-mono">
                            {intelligenceData.semantics?.threshold !== null && intelligenceData.semantics?.threshold !== undefined
                              ? `${intelligenceData.semantics.threshold} ${intelligenceData.semantics.threshold_unit || ""}`
                              : "Unspecified (None)"}
                          </span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Aggregation Window:</span>
                          <span className="text-slate-200 font-mono">{intelligenceData.semantics?.aggregation_window || "Unspecified"}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Review Required:</span>
                          <span className={intelligenceData.semantics?.review_required ? "text-amber-400 font-semibold" : "text-emerald-400"}>
                            {intelligenceData.semantics?.review_required ? "YES" : "NO"}
                          </span>
                        </div>
                      </div>

                      {intelligenceData.semantics?.missing_requirements && intelligenceData.semantics.missing_requirements.length > 0 && (
                        <div className="p-2 rounded bg-amber-950/20 border border-amber-900/40 text-amber-300 text-[11px] space-y-1">
                          <span className="font-bold">Missing Rule Specifications:</span>
                          <ul className="list-disc list-inside">
                            {intelligenceData.semantics.missing_requirements.map((mr, i) => (
                              <li key={i}>{mr}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>

                    {/* Archetype Classification */}
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-2">
                      <div className="font-bold text-slate-200 border-b border-slate-800 pb-1 flex justify-between">
                        <span>Archetype Classification</span>
                        <span className="font-mono text-cyan-400 text-[10px]">Registry v{intelligenceData.classification?.registry_version}</span>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-[11px]">
                        <div>
                          <span className="text-slate-500 block">Primary Archetype:</span>
                          <span className="text-slate-100 font-bold font-mono text-sm">{intelligenceData.classification?.primary_archetype}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Classification Confidence:</span>
                          <span className="text-slate-200 font-mono">{Math.round((intelligenceData.classification?.confidence_score || 0) * 100)}%</span>
                        </div>
                      </div>

                      <div className="text-[11px] text-slate-400">
                        <span className="text-slate-500 block">Reason:</span>
                        {intelligenceData.classification?.classification_reason}
                      </div>

                      {intelligenceData.classification?.matched_features && (
                        <div>
                          <span className="text-slate-500 block text-[10px] uppercase">Matched Semantic Features:</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {intelligenceData.classification.matched_features.map((mf, i) => (
                              <span key={i} className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-300 border border-slate-800 text-[10px] font-mono">
                                {mf}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    Loading detection semantics...
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: EVIDENCE CONTRACT */}
            {studioTab === "contract" && (
              <div className="space-y-3">
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                    <Database className="w-4 h-4 text-cyan-400" />
                    Synchronized Evidence Contract
                  </h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">
                    Machine-verifiable evidence schema required by the Independent Verdict Validator and Preflight Guard.
                  </p>
                </div>

                {intelligenceData?.candidate_evidence_contract ? (
                  <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-3 text-xs">
                    <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                      <span className="font-bold text-slate-200">
                        Contract Schema: {intelligenceData.candidate_evidence_contract.contract_id || intelligenceData.candidate_evidence_contract.rule_id}
                      </span>
                      <span className="text-cyan-400 font-mono text-[10px]">
                        Target Archetype: {intelligenceData.candidate_evidence_contract.target_archetype || intelligenceData.candidate_evidence_contract.detection_archetype}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                      <div className="p-2.5 rounded bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <span className="font-bold text-emerald-400 uppercase text-[10px]">Core Required Fields:</span>
                        <div className="space-y-1">
                          {(
                            intelligenceData.candidate_evidence_contract.core_fields ||
                            intelligenceData.candidate_evidence_contract.required_evidence?.filter((r: any) => r.requirement_level === "CORE").map((r: any) => ({
                              field_name: r.field,
                              field_type: r.evidence_type,
                              critical: r.critical,
                            })) ||
                            []
                          ).map((f: any, i: number) => (
                            <div key={i} className="font-mono text-slate-300 flex justify-between">
                              <span className="flex items-center gap-1">
                                • {f.field_name}
                                {f.critical && <span className="text-[9px] px-1 rounded bg-rose-950 text-rose-300 border border-rose-800">CRITICAL</span>}
                              </span>
                              <span className="text-[9px] text-slate-500">[{f.field_type}]</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="p-2.5 rounded bg-slate-900/40 border border-slate-800 space-y-1.5">
                        <span className="font-bold text-sky-400 uppercase text-[10px]">Conditional Fields:</span>
                        <div className="space-y-1">
                          {(() => {
                            const conds =
                              intelligenceData.candidate_evidence_contract.conditional_fields ||
                              intelligenceData.candidate_evidence_contract.required_evidence?.filter((r: any) => r.requirement_level === "CONDITIONAL").map((r: any) => ({
                                field_name: r.field,
                                condition: r.description || "Conditional",
                              })) ||
                              [];
                            return conds.length > 0 ? (
                              conds.map((f: any, i: number) => (
                                <div key={i} className="font-mono text-slate-300 flex justify-between">
                                  <span>• {f.field_name}</span>
                                  <span className="text-[9px] text-slate-500">[{f.condition}]</span>
                                </div>
                              ))
                            ) : (
                              <span className="text-slate-500 italic">None</span>
                            );
                          })()}
                        </div>
                      </div>
                    </div>

                    {(() => {
                      const unsupp =
                        intelligenceData.candidate_evidence_contract.unsupported_fields ||
                        intelligenceData.candidate_evidence_contract.required_evidence?.filter((r: any) => r.requirement_level === "UNAVAILABLE").map((r: any) => r.field) ||
                        [];
                      return (
                        unsupp.length > 0 && (
                          <div className="p-2.5 rounded bg-rose-950/20 border border-rose-900/40 text-rose-300 text-[11px] space-y-1">
                            <span className="font-bold text-[10px] uppercase">Prohibited / Unsupported Telemetry Assumptions:</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {unsupp.map((uf: string, i: number) => (
                                <span key={i} className="px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800 text-[10px] font-mono">
                                  {uf}
                                </span>
                              ))}
                            </div>
                          </div>
                        )
                      );
                    })()}

                    <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800 grid grid-cols-2 gap-2 text-[10px] text-slate-400">
                      <div>
                        <span className="text-slate-500 block uppercase">On Critical Missing Evidence:</span>
                        <span className="font-mono text-amber-300 font-bold">{intelligenceData.candidate_evidence_contract.on_critical_missing_evidence || "REQUIRES_ATTENTION"}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block uppercase">Contradiction Rules:</span>
                        <span className="font-mono text-cyan-300">{intelligenceData.candidate_evidence_contract.contradiction_rules?.length || 0} active rules</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    No evidence contract available for this rule.
                  </div>
                )}
              </div>
            )}

            {/* TAB 5: SIMULATION LAB */}
            {studioTab === "simulation" && (
              <div className="space-y-3">
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-purple-400" />
                        Simulation Lab &amp; Regression Validator
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Evaluate policy candidate against historical incidents. Verifies false positive avoidance and decisive stability.
                      </p>
                    </div>
                    <button
                      onClick={handleRunSimulation}
                      disabled={loadingSimulation}
                      className="px-2.5 py-1 text-xs rounded border border-purple-800 bg-purple-950/60 hover:bg-purple-900/60 text-purple-200 font-semibold flex items-center gap-1.5"
                    >
                      <RefreshCw className={`w-3 h-3 text-purple-400 ${loadingSimulation ? "animate-spin" : ""}`} />
                      Run Simulation
                    </button>
                  </div>
                </div>

                {loadingSimulation ? (
                  <div className="py-12 text-center text-slate-400 text-xs space-y-2">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-purple-400" />
                    <p>Executing historical incident simulation test suite...</p>
                  </div>
                ) : simulationResult ? (
                  <div className="space-y-3 text-xs">
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Simulation Status</div>
                        <div className={`text-sm font-bold font-mono mt-1 ${
                          (simulationResult.status === "PASSED" || simulationResult.simulation_status === "EVALUATED_PASSED")
                            ? "text-emerald-400"
                            : (simulationResult.status === "INSUFFICIENT_DATA" || simulationResult.simulation_status === "INSUFFICIENT_DATA")
                            ? "text-amber-400"
                            : "text-rose-400"
                        }`}>
                          {simulationResult.status || simulationResult.simulation_status || "COMPLETED"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Sample Count</div>
                        <div className="text-xl font-bold font-mono text-slate-100">{simulationResult.sample_count ?? 0}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Regression Detected</div>
                        <div className={`text-sm font-bold mt-1 ${simulationResult.regression_detected ? "text-rose-400" : "text-emerald-400"}`}>
                          {simulationResult.regression_detected ? "YES (BLOCKED)" : "NO"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Abstention Rate</div>
                        <div className="text-xl font-bold font-mono text-slate-100">
                          {Math.round((simulationResult.abstention_rate || 0) * 100)}%
                        </div>
                      </div>
                    </div>

                    {simulationResult.balanced_accuracy !== undefined && (
                      <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Balanced Accuracy</div>
                          <div className="text-base font-bold font-mono text-cyan-400">
                            {Math.round((simulationResult.balanced_accuracy || 0) * 100)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Precision / Recall</div>
                          <div className="text-base font-bold font-mono text-slate-200">
                            {Math.round((simulationResult.precision || 0) * 100)}% / {Math.round((simulationResult.recall || 0) * 100)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Decision Coverage</div>
                          <div className="text-base font-bold font-mono text-slate-200">
                            {Math.round((simulationResult.decision_coverage || 0) * 100)}%
                          </div>
                        </div>
                        <div>
                          <div className="text-[10px] text-slate-500 uppercase">Calibration Status</div>
                          <div className={`text-xs font-bold font-mono mt-1 ${simulationResult.is_calibrated ? "text-emerald-400" : "text-amber-400"}`}>
                            {simulationResult.is_calibrated ? "CALIBRATED (N>=30)" : "NOT_CALIBRATED (N<30)"}
                          </div>
                        </div>
                      </div>
                    )}

                    {simulationResult.status === "INSUFFICIENT_DATA" && (
                      <div className="p-3 rounded-lg border border-amber-900/60 bg-amber-950/20 text-xs text-amber-300 flex items-start gap-2">
                        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <div>
                          <strong>Insufficient Historical Incident Data (N &lt; 5):</strong> Fewer than 5 historical incidents exist for this detection rule. 
                          The policy is validated statically, but historical regression verification cannot be confirmed. Gate 8 reports warning only.
                        </div>
                      </div>
                    )}

                    <div className="flex justify-end pt-1">
                      <a
                        href={`/verdict-intelligence?rule_id=${selectedRuleId}`}
                        className="px-3 py-1.5 rounded border border-cyan-800 bg-cyan-950/60 hover:bg-cyan-900/60 text-cyan-200 text-xs font-semibold flex items-center gap-1.5 transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
                        Open in Verdict Intelligence &amp; Calibration Dashboard (Dashboards A–E)
                      </a>
                    </div>
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-500 text-xs space-y-2">
                    <p>No simulation run yet for this prompt version.</p>
                    <button
                      onClick={handleRunSimulation}
                      className="px-3 py-1 bg-purple-900/40 hover:bg-purple-900/60 text-purple-300 border border-purple-800 rounded text-xs font-semibold"
                    >
                      Run Simulation Now
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* TAB 6: DRIFT & MONITORING */}
            {studioTab === "drift" && (
              <div className="space-y-3">
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/40">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-bold text-slate-200 flex items-center gap-2">
                        <GitBranch className="w-4 h-4 text-rose-400" />
                        Policy Lifecycle Drift &amp; Verified Analyst Feedback
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Detects changes in SIEM rule definitions, schema evolution, and verified human corrections without silently modifying approved policies.
                      </p>
                    </div>
                    {driftEvents.filter((d) => !d.acknowledged).length > 0 && (
                      <button
                        onClick={handleAcknowledgeDrift}
                        disabled={actionLoading}
                        className="px-2.5 py-1 text-xs rounded border border-rose-800 bg-rose-950 hover:bg-rose-900 text-rose-200 font-semibold flex items-center gap-1.5"
                      >
                        <Check className="w-3 h-3" /> Acknowledge Drift
                      </button>
                    )}
                  </div>
                </div>

                {driftEvents.length > 0 ? (
                  <div className="space-y-2">
                    {driftEvents.map((ev) => (
                      <div
                        key={ev.id}
                        className={`p-3 rounded-lg border text-xs space-y-1 ${
                          ev.acknowledged
                            ? "bg-slate-950/60 border-slate-800 text-slate-400"
                            : "bg-rose-950/20 border-rose-900/60 text-rose-300"
                        }`}
                      >
                        <div className="flex items-center justify-between font-bold">
                          <span className="flex items-center gap-1.5">
                            <AlertTriangle className="w-3.5 h-3.5" />
                            {ev.trigger_type}
                          </span>
                          <span className="font-mono text-[10px] text-slate-500">
                            {new Date(ev.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-[11px] leading-relaxed">{ev.summary}</p>
                        {ev.revalidation_required && !ev.acknowledged && (
                          <div className="text-[10px] font-bold text-rose-400 pt-1">
                            ⚠️ Policy revalidation required before next deployment.
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-500 text-xs">
                    No drift events recorded for this detection rule. Policy specifications are in sync.
                  </div>
                )}
              </div>
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
              <h3 className="text-sm font-bold text-slate-100">Approve Policy for Production</h3>
            </div>
            <p className="text-xs text-slate-400">
              Approving Version {selectedVersion?.version_number} will set it as the production baseline for <strong>{rulePrompt?.rule_name}</strong> and synchronize the machine-verifiable Evidence Contract.
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
