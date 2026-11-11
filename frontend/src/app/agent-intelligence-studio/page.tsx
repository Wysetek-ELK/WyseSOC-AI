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
  X,
  Eye,
  Copy,
  ExternalLink,
  Sliders,
  Award,
  Database,
  GitBranch,
} from "lucide-react";
import {
  api,
  User,
  RuleItem,
  RulePrompt,
  PromptVersion,
  RulePromptSummaryItem,
  RuleIntelligenceData,
  PolicyQualityAssessmentResponse,
  QualityGateResult,
  QualitySummaryItem,
  PolicyDriftEventItem,
  PolicySimulationResult,
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
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const isViewer = currentUser?.role === "Read-Only Viewer";

  // Policy Simulation State
  const [simulationResult, setSimulationResult] = useState<PolicySimulationResult | null>(null);
  const [loadingSimulation, setLoadingSimulation] = useState(false);
  const [showExclusions, setShowExclusions] = useState(false);

  // Funnel & Card Drilldown Pop-up Modal State
  const [drilldownModal, setDrilldownModal] = useState<{
    isOpen: boolean;
    cardType: "scanned" | "rule_matched" | "analyst_labeled" | "eligible" | "excluded" | "evaluated" | "confusion_tp" | "confusion_tn" | "confusion_fp" | "confusion_fn" | "confusion_abstained" | null;
    title: string;
    description: string;
    badgeCount: number;
    items: Array<any>;
  } | null>(null);
  const [drilldownSearch, setDrilldownSearch] = useState("");
  const [drilldownReasonFilter, setDrilldownReasonFilter] = useState<string>("ALL");
  const [drilldownCopied, setDrilldownCopied] = useState(false);

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
      api.getMe().then(setCurrentUser).catch(() => null);
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

  const fetchQualityPreview = async (ruleId: string, versionId?: string) => {
    if (!ruleId) return;
    setLoadingQuality(true);
    try {
      const qRes = await api.previewPolicyQuality(ruleId, versionId);
      setQualityAssessment(qRes);
    } catch (err: any) {
      console.error("Failed to preview policy quality:", err);
    } finally {
      setLoadingQuality(false);
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
      setFeedback({ type: "error", text: err.message || "Failed to validate policy quality" });
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
      fetchQualityPreview(selectedRuleId, selectedVersionId);
    }
  }, [selectedRuleId, selectedVersionId]);

  // Close drilldown modal on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && drilldownModal?.isOpen) {
        setDrilldownModal(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [drilldownModal]);

  // Open modal for Funnel Cards (1. Scanned, 2. Rule-Matched, 3. Analyst-Labeled, 4. Eligible, 5. Excluded, 6. Evaluated)
  const openFunnelCardModal = (cardType: "scanned" | "rule_matched" | "analyst_labeled" | "eligible" | "excluded" | "evaluated") => {
    if (!simulationResult) return;
    setDrilldownSearch("");
    setDrilldownReasonFilter("ALL");

    if (cardType === "excluded") {
      const excludedItems = simulationResult.exclusions_detail || simulationResult.stage_details?.excluded || [];
      setDrilldownModal({
        isOpen: true,
        cardType: "excluded",
        title: "5. Excluded Incidents",
        description: "Historical incidents excluded from empirical ground-truth validation with documented exclusion justifications.",
        badgeCount: simulationResult.excluded_count ?? excludedItems.length,
        items: excludedItems,
      });
    } else if (cardType === "scanned") {
      const scannedItems = simulationResult.stage_details?.scanned || [
        ...(simulationResult.exclusions_detail || []).map((ex) => ({
          incident_id: ex.incident_id,
          rule_id: (ex as any).rule_id || "Unassigned / Mismatched",
          status: "EXCLUDED",
          reason: ex.reason,
          detail: ex.detail,
        })),
        ...(simulationResult.per_incident_results || []).map((res) => ({
          incident_id: res.incident_id,
          rule_id: res.rule_id,
          status: "RULE_MATCHED",
          reason: res.ground_truth || "EVALUATED",
          detail: `Effective verdict: ${res.effective_verdict} (Trust: ${res.trust_score}/10)`,
        })),
      ];
      setDrilldownModal({
        isOpen: true,
        cardType: "scanned",
        title: "1. Scanned Incidents",
        description: "All historical incidents retrieved and inspected from the historical dataset during simulation.",
        badgeCount: simulationResult.total_scanned ?? scannedItems.length,
        items: scannedItems,
      });
    } else if (cardType === "rule_matched") {
      const matchedItems = simulationResult.stage_details?.rule_matched || [
        ...(simulationResult.per_incident_results || []).map((res) => ({
          incident_id: res.incident_id,
          rule_id: res.rule_id,
          has_analyst_label: Boolean(res.ground_truth),
          resolution: res.ground_truth || "Unlabeled / Pending",
          detail: `Effective verdict: ${res.effective_verdict} (Trust: ${res.trust_score}/10)`,
        })),
      ];
      setDrilldownModal({
        isOpen: true,
        cardType: "rule_matched",
        title: "2. Rule-Matched Incidents",
        description: "Incidents whose alert rule association strictly matches the target rule under evaluation.",
        badgeCount: simulationResult.rule_matched ?? matchedItems.length,
        items: matchedItems,
      });
    } else if (cardType === "analyst_labeled") {
      const labeledItems = simulationResult.stage_details?.analyst_labeled || [
        ...(simulationResult.per_incident_results || [])
          .filter((res) => Boolean(res.ground_truth))
          .map((res) => ({
            incident_id: res.incident_id,
            rule_id: res.rule_id,
            resolution: res.ground_truth,
            comments: res.escalation_reason || "Documented in SIEM incident resolution",
            detail: `Resolution: ${res.ground_truth}`,
          })),
      ];
      setDrilldownModal({
        isOpen: true,
        cardType: "analyst_labeled",
        title: "3. Analyst-Labeled Incidents",
        description: "Incidents with closed resolution metadata recorded by human SOC analysts.",
        badgeCount: simulationResult.analyst_labeled ?? labeledItems.length,
        items: labeledItems,
      });
    } else if (cardType === "eligible") {
      const eligibleItems = simulationResult.stage_details?.eligible || [
        ...(simulationResult.per_incident_results || [])
          .filter((res) => res.ground_truth === "VERIFIED_TP" || res.ground_truth === "VERIFIED_FP")
          .map((res) => ({
            incident_id: res.incident_id,
            rule_id: res.rule_id,
            ground_truth: res.ground_truth,
            resolution: res.ground_truth === "VERIFIED_TP" ? "Confirmed True Positive" : "Verified False Positive",
            detail: `Independently verified ground-truth label: ${res.ground_truth}`,
          })),
      ];
      setDrilldownModal({
        isOpen: true,
        cardType: "eligible",
        title: "4. Eligible Ground Truth Incidents",
        description: "Independently verified human True Positive and False Positive benchmark controls eligible for empirical scoring.",
        badgeCount: simulationResult.eligible_ground_truth_count ?? eligibleItems.length,
        items: eligibleItems,
      });
    } else if (cardType === "evaluated") {
      const evalItems = simulationResult.per_incident_results || [];
      setDrilldownModal({
        isOpen: true,
        cardType: "evaluated",
        title: "6. Evaluated Incidents",
        description: "Incidents evaluated through policy directives, evidence contracts, and verdict trustworthiness scoring.",
        badgeCount: simulationResult.evaluated_cases ?? evalItems.length,
        items: evalItems,
      });
    }
  };

  // Open modal for Confusion Matrix cards
  const openConfusionModal = (bucket: "tp" | "tn" | "fp" | "fn" | "abstained") => {
    if (!simulationResult || !simulationResult.per_incident_results) return;
    setDrilldownSearch("");
    setDrilldownReasonFilter("ALL");

    const mapping = {
      tp: {
        title: "True Positives (Confirmed Attack Detected)",
        desc: "Incidents correctly identified as TRUE_POSITIVE aligned with verified malicious ground truth.",
        filter: (r: any) => r.effective_verdict === "TRUE_POSITIVE" && (r.ground_truth === "VERIFIED_TP" || r.is_correct === true),
      },
      tn: {
        title: "True Negatives (Benign Activity Cleared)",
        desc: "Incidents correctly identified as FALSE_POSITIVE aligned with verified benign ground truth.",
        filter: (r: any) => r.effective_verdict === "FALSE_POSITIVE" && (r.ground_truth === "VERIFIED_FP" || r.is_correct === true),
      },
      fp: {
        title: "False Positives (Benign Flagged as Attack)",
        desc: "Benign activity incorrectly classified as True Positive (Over-alerting).",
        filter: (r: any) =>
          r.effective_verdict === "TRUE_POSITIVE" &&
          (r.ground_truth === "VERIFIED_FP" ||
            (Boolean(r.ground_truth) && r.is_correct === false && r.is_critical_error === false)),
      },
      fn: {
        title: "False Negatives (Critical Missed Attacks)",
        desc: "Confirmed malicious incidents incorrectly dismissed as False Positive (Safety violation).",
        filter: (r: any) => r.effective_verdict === "FALSE_POSITIVE" && (r.ground_truth === "VERIFIED_TP" || r.is_critical_error === true),
      },
      abstained: {
        title: "Abstentions (Requires Analyst Review)",
        desc: "Incidents abstained due to missing mandatory evidence or contradictory telemetry.",
        filter: (r: any) => r.effective_verdict === "REQUIRES_ANALYST_ATTENTION" || r.is_abstained,
      },
    };

    const target = mapping[bucket];
    const filtered = simulationResult.per_incident_results.filter(target.filter);
    setDrilldownModal({
      isOpen: true,
      cardType: `confusion_${bucket}` as any,
      title: target.title,
      description: target.desc,
      badgeCount: filtered.length,
      items: filtered,
    });
  };

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
          <div className="p-2.5 rounded-xl theme-glass-card">
            <div className="text-[10px] uppercase font-semibold text-slate-400 flex items-center justify-between">
              Monitored Rules
              <FileCode className="w-3.5 h-3.5 text-slate-500" />
            </div>
            <div className="text-lg font-bold text-slate-100 mt-1">{totalRulesCount}</div>
            <div className="text-[9px] text-slate-500 mt-0.5">Active SIEM rules</div>
          </div>

          <div className="p-2.5 rounded-xl theme-glass-card border-emerald-900/50">
            <div className="text-[10px] uppercase font-semibold text-emerald-400 flex items-center justify-between">
              Approved
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-lg font-bold text-emerald-300 mt-1">{approvedPromptsCount}</div>
            <div className="text-[9px] text-emerald-500/80 mt-0.5">
              {totalRulesCount ? Math.round((approvedPromptsCount / totalRulesCount) * 100) : 0}% active
            </div>
          </div>

          <div className="p-2.5 rounded-xl theme-glass-card border-sky-900/50">
            <div className="text-[10px] uppercase font-semibold text-sky-400 flex items-center justify-between">
              Template Drafts
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
            </div>
            <div className="text-lg font-bold text-sky-300 mt-1">{draftOnlyCount}</div>
            <div className="text-[9px] text-sky-500/80 mt-0.5">Drafts awaiting review</div>
          </div>

          <div className="p-2.5 rounded-xl theme-glass-card border-cyan-900/50">
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

  const studioQualityScore = qualityAssessment?.quality_score ?? null;
  const filledSegments =
    studioQualityScore !== null
      ? Math.max(0, Math.min(20, Math.round((studioQualityScore / 100) * 20)))
      : 0;
  const passedGatesCount = gateList.filter((g) => g.status === "PASSED").length;

  return (
    <div className="space-y-3.5">
      {/* Page Header with Back Navigation & Rule Switcher */}
      <div className="p-3 sm:px-4 rounded-xl theme-glass-panel flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={handleBackToTable}
            className="px-2.5 py-1.5 rounded-lg theme-secondary-btn text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5 text-cyan-400" />
            <Table className="w-3.5 h-3.5 text-slate-400" />
            Rules List
          </button>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100">
                Agent Intelligence Studio 2.0
              </h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-950/80 text-slate-300 border border-slate-700/80 font-mono uppercase tracking-wide">
                {intelligenceData?.classification?.primary_archetype || "DETECTION ENGINE"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Governed policy generation, 8-gate quality validation, evidence contract alignment, and simulation regression checks.
            </p>
          </div>
        </div>

        {/* SIEM Rule Selector */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider shrink-0">
            Select Rule:
          </label>
          <select
            value={selectedRuleId}
            onChange={(e) => handleSwitchRuleInStudio(e.target.value)}
            disabled={loadingRules}
            className="px-2.5 py-1.5 text-xs rounded-lg border border-cyan-500/40 bg-slate-950/90 text-slate-200 font-medium focus:outline-none focus:border-cyan-400 min-w-[240px] max-w-[380px] truncate w-full sm:w-auto"
          >
            {rules.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name} ({r.severity})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* AIS 2.0 Hero Policy Governance Banner: Score Meter & Action Stack */}
      <div className="p-4 sm:p-5 rounded-2xl theme-hero-score-card flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 sm:gap-6 min-w-0">
          {/* Large Hero Quality Score Readout */}
          <div className="flex items-baseline gap-0.5 shrink-0">
            <span className="text-4xl sm:text-5xl font-extrabold tracking-tight text-sky-400 tabular-nums drop-shadow-sm">
              {studioQualityScore !== null ? studioQualityScore : "—"}
            </span>
            <span className="text-lg sm:text-xl font-bold text-slate-400">/100</span>
          </div>

          {/* Eligibility Pill + Segmented Progress Meter + Structural Telemetry */}
          <div className="space-y-2 min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              {isApprovalEligible ? (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-sky-950/80 text-sky-300 border border-sky-500/50 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-sky-400" /> APPROVAL ELIGIBLE
                </span>
              ) : selectedVersion?.status === "APPROVED" ? (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/70 flex items-center gap-1.5">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> ACTIVE PRODUCTION
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-rose-950/80 text-rose-300 border border-rose-700/70 flex items-center gap-1.5">
                  <XCircle className="w-3.5 h-3.5 text-rose-400" /> REWORK REQUIRED
                </span>
              )}

              {isIncompleteDefinition ? (
                <span
                  className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-950/80 text-amber-300 border border-amber-700/70 flex items-center gap-1"
                  title="Authoritative threshold is missing. Draft remains provisional."
                >
                  <AlertCircle className="w-3 h-3 text-amber-400" /> DEFINITION: INCOMPLETE
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950/60 text-emerald-300 border border-emerald-700/60">
                  DEFINITION: VERIFIED
                </span>
              )}
            </div>

            {/* 20-Segment Progress Bar */}
            <div className="flex items-center gap-1 max-w-md" aria-hidden="true">
              {Array.from({ length: 20 }).map((_, idx) => {
                const active = idx < filledSegments;
                return (
                  <span
                    key={idx}
                    className={`h-2 flex-1 rounded-full transition-all ${
                      active
                        ? idx < 10
                          ? "bg-sky-400 shadow-[0_0_8px_rgba(251,191,36,0.45)]"
                          : "bg-cyan-500 shadow-[0_0_8px_rgba(249,115,22,0.45)]"
                        : "bg-slate-800/80 border border-slate-700/50"
                    }`}
                  />
                );
              })}
            </div>

            <div className="text-[11px] font-mono text-slate-300 flex flex-wrap items-center gap-2">
              <span className="text-slate-400 uppercase">Quality Score:</span>
              <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold border ${getScoreBadge(qualityAssessment?.quality_score)}`}>
                {qualityAssessment ? `${qualityAssessment.quality_score}/100` : "Pending"}
              </span>
              <span className="text-slate-600">•</span>
              <span>
                GATES PASSED:{" "}
                <strong className="text-slate-100">
                  {gateList.length > 0 ? `${passedGatesCount}/${gateList.length}` : "—"}
                </strong>
              </span>
              {selectedVersion && (
                <>
                  <span className="text-slate-600">•</span>
                  <span className="text-emerald-400 font-semibold">
                    VERSION {selectedVersion.version_number} ({selectedVersion.status})
                  </span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Action Controls Stack */}
        <div className="flex flex-col sm:flex-row lg:flex-col gap-1.5 lg:min-w-[220px] shrink-0">
          <button
            type="button"
            disabled={actionLoading || loadingPrompt}
            onClick={handleGenerateIntelligentDraft}
            className="px-3.5 py-1.5 text-xs rounded-lg theme-primary-btn font-semibold flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
          >
            <Sparkles className="w-3.5 h-3.5" />
            Synthesize Intelligent Draft
          </button>

          <button
            type="button"
            disabled={loadingQuality || !selectedVersionId || isViewer}
            onClick={() => fetchQualityValidation(selectedRuleId, selectedVersionId)}
            title={isViewer ? "Requires SOC Analyst or Administrator role to persist validation scores" : "Persist validated quality score & audit log"}
            className="px-3.5 py-1.5 text-xs rounded-lg theme-secondary-btn disabled:opacity-50 font-medium flex items-center justify-center gap-1.5 transition-colors"
          >
            <Award className="w-3.5 h-3.5 text-sky-400" />
            Validate Quality
          </button>

          <button
            type="button"
            disabled={loadingSimulation || !selectedVersionId}
            onClick={handleRunSimulation}
            className="px-3.5 py-1.5 text-xs rounded-lg theme-secondary-btn disabled:opacity-50 font-medium flex items-center justify-center gap-1.5 transition-colors"
          >
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            Run Simulation
          </button>

          <div className="flex items-center gap-1.5 empty:hidden">
            {/* Approve Button */}
            {selectedVersion && selectedVersion.status !== "APPROVED" && (
              <button
                type="button"
                disabled={actionLoading || !selectedVersionId || !isApprovalEligible}
                onClick={() => setShowApprovalModal(true)}
                className={`flex-1 px-3 py-1.5 rounded-lg text-xs font-bold flex items-center justify-center gap-1 shadow-sm transition-colors ${
                  isApprovalEligible
                    ? "bg-emerald-700 hover:bg-emerald-600 text-white border border-emerald-500/60"
                    : "bg-slate-900/70 text-slate-500 cursor-not-allowed border border-slate-800"
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
                className="flex-1 px-2.5 py-1.5 bg-amber-950/80 hover:bg-amber-900/80 text-amber-300 border border-amber-800/70 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors"
              >
                <RotateCcw className="w-3 h-3" /> Rollback to This
              </button>
            )}
          </div>
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
      <div className="flex flex-wrap border-b border-slate-800/90 space-x-1 text-xs">
        <button
          onClick={() => setStudioTab("editor")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 rounded-t-md ${
            studioTab === "editor"
              ? "theme-tab-active"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <FileCode className="w-3.5 h-3.5" />
          Policy Editor (9 Sections)
        </button>

        <button
          onClick={() => setStudioTab("quality")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 rounded-t-md ${
            studioTab === "quality"
              ? "theme-tab-active"
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
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 rounded-t-md ${
            studioTab === "intelligence"
              ? "theme-tab-active"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          SIEM Semantics &amp; Archetype
        </button>

        <button
          onClick={() => setStudioTab("contract")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 rounded-t-md ${
            studioTab === "contract"
              ? "theme-tab-active"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Database className="w-3.5 h-3.5" />
          Evidence Contract
        </button>

        <button
          onClick={() => setStudioTab("simulation")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 rounded-t-md ${
            studioTab === "simulation"
              ? "theme-tab-active"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          Simulation Lab
        </button>

        <button
          onClick={() => setStudioTab("drift")}
          className={`px-3 py-2 font-semibold border-b-2 transition-colors flex items-center gap-1.5 rounded-t-md ${
            studioTab === "drift"
              ? "theme-tab-active"
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
            <div className="p-3.5 rounded-xl theme-glass-panel space-y-2.5">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-200 flex items-center gap-1.5">
                  <History className="w-3.5 h-3.5 text-sky-400" /> Version History
                </span>
                <span className="text-[10px] text-slate-400 font-mono">
                  {rulePrompt.versions.length} versions
                </span>
              </div>

              {/* Version List */}
              <div className="space-y-2 max-h-[460px] overflow-y-auto pr-0.5">
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
                        className={`p-2.5 rounded-xl text-xs cursor-pointer transition-all ${
                          isSelected
                            ? "theme-version-selected"
                            : "theme-glass-sunken hover:border-slate-700"
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-slate-100 flex items-center gap-1.5 text-xs">
                            v{ver.version_number}
                            {isActive && (
                              <span className="px-1.5 py-0.2 rounded text-[9px] bg-emerald-950/90 text-emerald-400 border border-emerald-800/80 font-semibold">
                                ACTIVE
                              </span>
                            )}
                          </span>
                          <span className={`px-1.5 py-0.2 rounded-full text-[9px] font-semibold ${
                            ver.status === "APPROVED"
                              ? "bg-emerald-950/90 text-emerald-400 border border-emerald-800/80"
                              : ver.status === "DRAFT"
                              ? "bg-amber-950/90 text-amber-300 border border-amber-700/80"
                              : "bg-slate-900 text-slate-400 border border-slate-800"
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
                className="w-full py-2 px-2.5 theme-secondary-btn rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
              >
                <Sparkles className="w-3.5 h-3.5 text-cyan-400" /> Generate Intelligent Draft
              </button>
            </div>
          </div>

          {/* Right Column: Tabbed Workspace */}
          <div className="lg:col-span-3 space-y-3">
            {/* TAB 1: POLICY EDITOR */}
            {studioTab === "editor" && (
              <>
                {!selectedVersion ? (
                  <div className="p-8 rounded-xl theme-glass-card text-center space-y-3">
                    <Sparkles className="w-8 h-8 text-cyan-400 mx-auto" />
                    <h3 className="text-sm font-semibold text-slate-200">No Policy Baseline for This Rule</h3>
                    <p className="text-xs text-slate-400 max-w-md mx-auto">
                      Generate an intelligent policy draft synthesized from SIEM rule specifications and detection archetypes.
                    </p>
                    <button
                      type="button"
                      disabled={actionLoading}
                      onClick={handleGenerateIntelligentDraft}
                      className="px-4 py-2 theme-primary-btn rounded-lg text-xs font-semibold inline-flex items-center gap-1.5 transition-all"
                    >
                      <Sparkles className="w-3.5 h-3.5" /> Synthesize Intelligent Draft Now
                    </button>
                  </div>
                ) : (
                  <>
                    {/* Top Toolbar */}
                    <div className="p-3 sm:px-4 rounded-xl theme-glass-panel flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-slate-100">
                            Version {selectedVersion.version_number}
                          </span>
                          {isSelectedActive && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 flex items-center gap-1">
                              <CheckCircle2 className="w-3 h-3" /> Production Active
                            </span>
                          )}
                          {selectedVersion.is_template_draft && (
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-sky-950/80 text-sky-300 border border-sky-700/70">
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
                          className="px-2.5 py-1.5 theme-secondary-btn rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
                        >
                          <Download className="w-3.5 h-3.5 text-cyan-400" /> Download
                        </button>

                        {!isEditing ? (
                          <button
                            type="button"
                            onClick={() => setIsEditing(true)}
                            className="px-2.5 py-1.5 theme-secondary-btn rounded-lg text-xs font-semibold transition-colors"
                          >
                            Edit as New Draft
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setIsEditing(false)}
                            className="px-2.5 py-1.5 bg-slate-900 hover:bg-slate-800 text-slate-400 border border-slate-800 rounded-lg text-xs font-semibold transition-colors"
                          >
                            Cancel Editing
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Structured 9-Section Policy Form */}
                    <form onSubmit={handleSaveManualDraft} className="space-y-3">
                      {/* Section 1: Common SOC Baseline */}
                      <div className="p-3.5 rounded-xl theme-glass-card space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-bold text-sky-400 flex items-center gap-1.5 tracking-wide">
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
                            className="w-full p-2.5 text-xs font-mono rounded-lg border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none focus:border-sky-500"
                          />
                        ) : (
                          <div className="p-3 text-xs font-mono rounded-lg theme-glass-sunken text-slate-300 whitespace-pre-wrap max-h-48 overflow-y-auto leading-relaxed">
                            {selectedVersion.common_prompt}
                          </div>
                        )}
                      </div>

                      {/* Section 2: Rule-Specific Guidance */}
                      <div className="p-3.5 rounded-xl theme-glass-card space-y-2">
                        <div className="flex items-center justify-between">
                          <label className="text-xs font-bold text-sky-400 flex items-center gap-1.5 tracking-wide">
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
                            className="w-full p-2.5 text-xs font-mono rounded-lg border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none focus:border-cyan-500"
                            required
                          />
                        ) : (
                          <div className="p-3 text-xs font-mono rounded-lg theme-glass-sunken text-slate-300 whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed">
                            {selectedVersion.rule_specific_prompt}
                          </div>
                        )}
                      </div>

                      {/* Section 3 & 4: Detection Conditions & Evidence */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <div className="p-3.5 rounded-xl theme-glass-card space-y-2">
                          <label className="text-xs font-bold text-sky-400 block tracking-wide">
                            3. DETECTION CONDITIONS &amp; PATTERN LOGIC
                          </label>
                          {isEditing ? (
                            <textarea
                              rows={4}
                              value={editConditions}
                              onChange={(e) => setEditConditions(e.target.value)}
                              className="w-full p-2.5 text-xs font-mono rounded-lg border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none"
                            />
                          ) : (
                            <div className="p-3 text-xs font-mono rounded-lg theme-glass-sunken text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto">
                              {selectedVersion.detection_conditions || "No conditions specified."}
                            </div>
                          )}
                        </div>

                        <div className="p-3.5 rounded-xl theme-glass-card space-y-2">
                          <label className="text-xs font-bold text-sky-400 block tracking-wide">
                            4. MANDATORY EVIDENCE GATHERING CHECKLIST
                          </label>
                          {isEditing ? (
                            <textarea
                              rows={4}
                              value={editEvidence}
                              onChange={(e) => setEditEvidence(e.target.value)}
                              className="w-full p-2.5 text-xs font-mono rounded-lg border border-slate-700 bg-slate-950 text-slate-200 focus:outline-none"
                            />
                          ) : (
                            <div className="p-3 text-xs font-mono rounded-lg theme-glass-sunken text-slate-300 whitespace-pre-wrap max-h-36 overflow-y-auto">
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
                      <div className="p-3.5 rounded-xl theme-glass-card space-y-2">
                        <label className="text-xs font-bold text-sky-400 block tracking-wide">
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
                      disabled={loadingQuality || isViewer}
                      title={isViewer ? "Requires SOC Analyst or Administrator role" : "Re-run and persist validation"}
                      className="px-2.5 py-1 text-xs rounded border border-slate-700 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 flex items-center gap-1.5"
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
                        <div className="text-[10px] text-slate-500 uppercase">Structural Approval</div>
                        <div className={`text-sm font-bold mt-1 ${isApprovalEligible ? "text-emerald-400" : "text-amber-400"}`}>
                          {isApprovalEligible ? "ELIGIBLE (G1–G7)" : "NO (REWORK)"}
                        </div>
                      </div>
                    </div>

                    {/* Explicit Separation of Structural vs Empirical vs Autonomous Eligibility */}
                    <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-900/40 flex flex-wrap items-center justify-between gap-2 text-[11px]">
                      <div className="flex flex-wrap items-center gap-3">
                        <span>
                          <span className="text-slate-400">Structural (G1–G7): </span>
                          <strong className={(isApprovalEligible && (qualityAssessment.structural_approval_eligible ?? true)) ? "text-emerald-400" : "text-rose-400"}>
                            {(isApprovalEligible && (qualityAssessment.structural_approval_eligible ?? true)) ? "ELIGIBLE" : "BLOCKED"}
                          </strong>
                        </span>
                        <span>
                          <span className="text-slate-400">Empirical G8: </span>
                          <strong className={(qualityAssessment.empirical_validation_eligible ?? (qualityAssessment.empirical_validation_status === "EVALUATED_PASSED")) ? "text-emerald-400" : "text-amber-400"}>
                            {(qualityAssessment.empirical_validation_eligible ?? (qualityAssessment.empirical_validation_status === "EVALUATED_PASSED"))
                              ? "VERIFIED"
                              : `NOT CERTIFIED (${qualityAssessment.empirical_validation_status || qualityAssessment.simulation_status || "NOT_EVALUATED"})`}
                          </strong>
                        </span>
                        <span>
                          <span className="text-slate-400">Autonomous Ops: </span>
                          <strong className={(qualityAssessment.autonomous_operation_eligible ?? false) ? "text-emerald-400" : "text-amber-300"}>
                            {(qualityAssessment.autonomous_operation_eligible ?? false) ? "ELIGIBLE" : "REQUIRES G8 PASS"}
                          </strong>
                        </span>
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
              <div className="space-y-4">
                <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/40">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                        <Activity className="w-4 h-4 text-purple-400" />
                        Simulation Lab &amp; Empirical Accuracy Validation
                      </h3>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Dry-run replay against historical incidents to evaluate verdict trustworthiness, evidence confidence, empirical confusion matrix, and paired regression.
                      </p>
                    </div>
                    <button
                      onClick={handleRunSimulation}
                      disabled={loadingSimulation}
                      className="px-3 py-1.5 text-xs rounded border border-purple-800 bg-purple-950/70 hover:bg-purple-900/80 text-purple-200 font-semibold flex items-center gap-1.5 transition-colors shadow-sm"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 text-purple-400 ${loadingSimulation ? "animate-spin" : ""}`} />
                      {loadingSimulation ? "Running Simulation..." : "Run Simulation"}
                    </button>
                  </div>
                </div>

                {loadingSimulation ? (
                  <div className="py-16 text-center text-slate-400 text-xs space-y-3">
                    <RefreshCw className="w-8 h-8 animate-spin mx-auto text-purple-400" />
                    <p className="text-sm font-medium text-slate-200">Replaying historical incidents through dry-run validation pipeline...</p>
                    <p className="text-[11px] text-slate-500">Evaluating Evidence Sufficiency, Verdict Trustworthiness, and Empirical Accuracy</p>
                  </div>
                ) : simulationResult ? (
                  <div className="space-y-4 text-xs">
                    {/* Messaging Banner */}
                    <div className={`p-3 rounded-lg border flex items-start gap-2.5 text-xs ${
                      (simulationResult.status === "PASSED" || simulationResult.simulation_status === "EVALUATED_PASSED")
                        ? "bg-emerald-950/30 border-emerald-900/60 text-emerald-200"
                        : (simulationResult.status === "INSUFFICIENT_DATA" || simulationResult.simulation_status === "INSUFFICIENT_DATA")
                        ? "bg-amber-950/30 border-amber-900/60 text-amber-200"
                        : "bg-rose-950/30 border-rose-900/60 text-rose-200"
                    }`}>
                      {(simulationResult.status === "PASSED" || simulationResult.simulation_status === "EVALUATED_PASSED") ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                      ) : (simulationResult.status === "INSUFFICIENT_DATA" || simulationResult.simulation_status === "INSUFFICIENT_DATA") ? (
                        <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      ) : (
                        <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                      )}
                      <div className="space-y-0.5">
                        <div className="font-semibold text-slate-100">
                          {simulationResult.message || "Simulation evaluation completed."}
                        </div>
                        <div className="text-[11px] opacity-80">
                          Simulation Status: <span className="font-mono font-bold">{simulationResult.status || simulationResult.simulation_status}</span> | Empirical Validation: <span className="font-mono font-bold">{simulationResult.empirical_validation_status}</span> | Regression Check: <span className="font-mono font-bold">{simulationResult.regression_status}</span>
                        </div>
                      </div>
                    </div>

                    {/* Funnel: Historical Incident Eligibility Funnel */}
                    <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-950 space-y-2.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                          <Layers className="w-3.5 h-3.5 text-cyan-400" />
                          Historical Incident Eligibility Funnel
                        </span>
                        {simulationResult.excluded_count ? (
                          <button
                            type="button"
                            onClick={() => openFunnelCardModal("excluded")}
                            className="text-[10px] text-cyan-400 hover:text-cyan-300 font-mono underline cursor-pointer flex items-center gap-1"
                            title="Click to view detailed excluded incidents pop-up"
                          >
                            <Eye className="w-3 h-3" />
                            View {simulationResult.excluded_count} Exclusions
                          </button>
                        ) : null}
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                        {/* 1. Scanned */}
                        <button
                          type="button"
                          onClick={() => openFunnelCardModal("scanned")}
                          className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-cyan-500/60 hover:bg-slate-850 hover:shadow-md hover:shadow-cyan-950/20 text-left transition-all cursor-pointer group relative"
                          title="Click to inspect all scanned historical incidents"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] text-slate-400 uppercase font-semibold">1. Scanned</span>
                            <ExternalLink className="w-2.5 h-2.5 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                          </div>
                          <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                            {simulationResult.total_scanned ?? simulationResult.sample_count ?? 0}
                          </div>
                          <span className="text-[8px] text-slate-500 group-hover:text-cyan-400 transition-colors block mt-0.5 font-sans">
                            Click to inspect →
                          </span>
                        </button>

                        {/* 2. Rule-Matched */}
                        <button
                          type="button"
                          onClick={() => openFunnelCardModal("rule_matched")}
                          className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-cyan-500/60 hover:bg-slate-850 hover:shadow-md hover:shadow-cyan-950/20 text-left transition-all cursor-pointer group relative"
                          title="Click to inspect rule-matched incidents"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] text-slate-400 uppercase font-semibold">2. Rule-Matched</span>
                            <ExternalLink className="w-2.5 h-2.5 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                          </div>
                          <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                            {simulationResult.rule_matched ?? simulationResult.sample_count ?? 0}
                          </div>
                          <span className="text-[8px] text-slate-500 group-hover:text-cyan-400 transition-colors block mt-0.5 font-sans">
                            Click to inspect →
                          </span>
                        </button>

                        {/* 3. Analyst-Labeled */}
                        <button
                          type="button"
                          onClick={() => openFunnelCardModal("analyst_labeled")}
                          className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-purple-500/60 hover:bg-slate-850 hover:shadow-md hover:shadow-purple-950/20 text-left transition-all cursor-pointer group relative"
                          title="Click to inspect analyst-labeled incidents"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] text-slate-400 uppercase font-semibold">3. Analyst-Labeled</span>
                            <ExternalLink className="w-2.5 h-2.5 text-slate-600 group-hover:text-purple-400 transition-colors" />
                          </div>
                          <div className="text-base font-bold font-mono text-purple-300 mt-0.5">
                            {simulationResult.analyst_labeled ?? simulationResult.eligible_ground_truth_count ?? 0}
                          </div>
                          <span className="text-[8px] text-slate-500 group-hover:text-purple-400 transition-colors block mt-0.5 font-sans">
                            Click to inspect →
                          </span>
                        </button>

                        {/* 4. Eligible GT */}
                        <button
                          type="button"
                          onClick={() => openFunnelCardModal("eligible")}
                          className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-emerald-500/60 hover:bg-slate-850 hover:shadow-md hover:shadow-emerald-950/20 text-left transition-all cursor-pointer group relative"
                          title="Click to inspect eligible verified ground truth cases"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] text-slate-400 uppercase font-semibold">4. Eligible GT</span>
                            <ExternalLink className="w-2.5 h-2.5 text-slate-600 group-hover:text-emerald-400 transition-colors" />
                          </div>
                          <div className="text-base font-bold font-mono text-emerald-400 mt-0.5">
                            {simulationResult.eligible_ground_truth_count ?? simulationResult.verified_ground_truth_cases ?? 0}
                          </div>
                          <span className="text-[8px] text-slate-500 group-hover:text-emerald-400 transition-colors block mt-0.5 font-sans">
                            Click to inspect →
                          </span>
                        </button>

                        {/* 5. Excluded */}
                        <button
                          type="button"
                          onClick={() => openFunnelCardModal("excluded")}
                          className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-amber-500/60 hover:bg-slate-850 hover:shadow-md hover:shadow-amber-950/20 text-left transition-all cursor-pointer group relative"
                          title="Click to view pop-up window of excluded incidents with exact reasons"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] text-slate-400 uppercase font-semibold">5. Excluded</span>
                            <ExternalLink className="w-2.5 h-2.5 text-slate-600 group-hover:text-amber-400 transition-colors" />
                          </div>
                          <div className={`text-base font-bold font-mono mt-0.5 ${(simulationResult.excluded_count ?? 0) > 0 ? "text-amber-400" : "text-slate-400"}`}>
                            {simulationResult.excluded_count ?? 0}
                          </div>
                          <span className="text-[8px] text-slate-500 group-hover:text-amber-400 transition-colors block mt-0.5 font-sans">
                            Click to inspect →
                          </span>
                        </button>

                        {/* 6. Evaluated */}
                        <button
                          type="button"
                          onClick={() => openFunnelCardModal("evaluated")}
                          className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-cyan-500/60 hover:bg-slate-850 hover:shadow-md hover:shadow-cyan-950/20 text-left transition-all cursor-pointer group relative"
                          title="Click to inspect evaluated simulation cases"
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] text-slate-400 uppercase font-semibold">6. Evaluated</span>
                            <ExternalLink className="w-2.5 h-2.5 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                          </div>
                          <div className="text-base font-bold font-mono text-cyan-300 mt-0.5">
                            {simulationResult.evaluated_cases ?? simulationResult.sample_count ?? 0}
                          </div>
                          <span className="text-[8px] text-slate-500 group-hover:text-cyan-400 transition-colors block mt-0.5 font-sans">
                            Click to inspect →
                          </span>
                        </button>
                      </div>

                      {/* Expandable Exclusion Breakdown */}
                      {showExclusions && simulationResult.exclusion_reasons && (
                        <div className="p-2.5 rounded bg-slate-900/90 border border-slate-800 space-y-1.5 text-[11px]">
                          <span className="font-semibold text-slate-300 block">Exclusion Breakdown (Why incidents were excluded from empirical ground truth):</span>
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-[10px]">
                            {Object.entries(simulationResult.exclusion_reasons).map(([reason, count]) => (
                              <div key={reason} className="p-1.5 rounded bg-slate-950/80 border border-slate-800 flex justify-between">
                                <span className="font-mono text-slate-400">{reason}:</span>
                                <span className="font-bold text-amber-300 font-mono">{count} incidents</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Key Status Row: Empirical Validation & Regression Status */}
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Empirical Accuracy Status</div>
                        <div className={`text-sm font-bold font-mono mt-1 ${
                          simulationResult.empirical_validation_status === "EVALUATED_PASSED"
                            ? "text-emerald-400"
                            : simulationResult.empirical_validation_status === "INSUFFICIENT_DATA"
                            ? "text-amber-400"
                            : "text-rose-400"
                        }`}>
                          {simulationResult.empirical_validation_status || "INSUFFICIENT_DATA"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Version Regression Status</div>
                        <div className={`text-sm font-bold font-mono mt-1 ${
                          simulationResult.regression_status === "PASS"
                            ? "text-emerald-400"
                            : simulationResult.regression_status === "REGRESSION_DETECTED"
                            ? "text-rose-400"
                            : simulationResult.regression_status === "INSUFFICIENT_DATA"
                            ? "text-amber-400"
                            : "text-slate-400"
                        }`}>
                          {simulationResult.regression_status || "NOT_ASSESSED"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Decision Coverage</div>
                        <div className="text-xl font-bold font-mono text-slate-100 mt-0.5">
                          {simulationResult.decision_coverage != null
                            ? `${Math.round(simulationResult.decision_coverage * 100)}%`
                            : "N/A"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Abstention Rate</div>
                        <div className="text-xl font-bold font-mono text-slate-100 mt-0.5">
                          {simulationResult.abstention_rate != null
                            ? `${Math.round(simulationResult.abstention_rate * 100)}%`
                            : "N/A"}
                        </div>
                      </div>
                    </div>

                    {/* Confusion Matrix Card & Ground Truth Distribution */}
                    <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/60 space-y-2.5">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                          <Table className="w-3.5 h-3.5 text-purple-400" />
                          Empirical Confusion Matrix &amp; Ground Truth Distribution
                        </span>
                        <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                          <span>Verified TP: <strong className="text-emerald-400">{simulationResult.ground_truth_distribution?.tp ?? simulationResult.confusion_matrix?.tp ?? 0}</strong></span>
                          <span>|</span>
                          <span>Verified FP: <strong className="text-sky-400">{simulationResult.ground_truth_distribution?.fp ?? simulationResult.confusion_matrix?.tn ?? 0}</strong></span>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
                        <button
                          type="button"
                          onClick={() => openConfusionModal("tp")}
                          className="p-2 rounded bg-emerald-950/40 border border-emerald-900/60 hover:bg-emerald-900/50 hover:border-emerald-600 transition-all text-left flex flex-col justify-between group cursor-pointer"
                          title="Click to inspect True Positive incidents"
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="text-[9px] uppercase tracking-wider text-emerald-300 font-semibold">True Positives (TP)</span>
                            <Eye className="w-3 h-3 text-emerald-500 opacity-60 group-hover:opacity-100" />
                          </div>
                          <span className="text-lg font-bold font-mono text-emerald-400 mt-0.5 block text-center">
                            {simulationResult.confusion_matrix?.tp ?? 0}
                          </span>
                          <span className="text-[9px] text-slate-400 block text-center">Confirmed Attack Detected</span>
                          <span className="text-[9px] text-emerald-400/70 group-hover:text-emerald-300 text-center block pt-0.5">Click to inspect →</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => openConfusionModal("tn")}
                          className="p-2 rounded bg-sky-950/40 border border-sky-900/60 hover:bg-sky-900/50 hover:border-sky-600 transition-all text-left flex flex-col justify-between group cursor-pointer"
                          title="Click to inspect True Negative incidents"
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="text-[9px] uppercase tracking-wider text-sky-300 font-semibold">True Negatives (TN)</span>
                            <Eye className="w-3 h-3 text-sky-500 opacity-60 group-hover:opacity-100" />
                          </div>
                          <span className="text-lg font-bold font-mono text-sky-400 mt-0.5 block text-center">
                            {simulationResult.confusion_matrix?.tn ?? 0}
                          </span>
                          <span className="text-[9px] text-slate-400 block text-center">Benign Verified Safe</span>
                          <span className="text-[9px] text-sky-400/70 group-hover:text-sky-300 text-center block pt-0.5">Click to inspect →</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => openConfusionModal("fp")}
                          className="p-2 rounded bg-rose-950/40 border border-rose-900/60 hover:bg-rose-900/50 hover:border-rose-600 transition-all text-left flex flex-col justify-between group cursor-pointer"
                          title="Click to inspect False Positive incidents"
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="text-[9px] uppercase tracking-wider text-rose-300 font-semibold">False Positives (FP)</span>
                            <Eye className="w-3 h-3 text-rose-500 opacity-60 group-hover:opacity-100" />
                          </div>
                          <span className="text-lg font-bold font-mono text-rose-400 mt-0.5 block text-center">
                            {simulationResult.confusion_matrix?.fp ?? 0}
                          </span>
                          <span className="text-[9px] text-slate-400 block text-center">Benign Flagged as Attack</span>
                          <span className="text-[9px] text-rose-400/70 group-hover:text-rose-300 text-center block pt-0.5">Click to inspect →</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => openConfusionModal("fn")}
                          className="p-2 rounded bg-red-950/60 border border-red-800 hover:bg-red-900/60 hover:border-red-600 transition-all text-left flex flex-col justify-between group cursor-pointer"
                          title="Click to inspect False Negative incidents"
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="text-[9px] uppercase tracking-wider text-red-300 font-semibold">False Negatives (FN)</span>
                            <Eye className="w-3 h-3 text-red-400 opacity-60 group-hover:opacity-100" />
                          </div>
                          <span className="text-lg font-bold font-mono text-red-400 mt-0.5 block text-center">
                            {simulationResult.confusion_matrix?.fn ?? 0}
                          </span>
                          <span className="text-[9px] text-red-300/80 block font-bold text-center">Critical Missed Attacks</span>
                          <span className="text-[9px] text-red-400/80 group-hover:text-red-300 text-center block pt-0.5">Click to inspect →</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => openConfusionModal("abstained")}
                          className="p-2 rounded bg-amber-950/40 border border-amber-900/60 hover:bg-amber-900/50 hover:border-amber-600 transition-all text-left flex flex-col justify-between group cursor-pointer"
                          title="Click to inspect Abstained incidents"
                        >
                          <div className="flex items-center justify-between w-full">
                            <span className="text-[9px] uppercase tracking-wider text-amber-300 font-semibold">Abstentions</span>
                            <Eye className="w-3 h-3 text-amber-500 opacity-60 group-hover:opacity-100" />
                          </div>
                          <span className="text-lg font-bold font-mono text-amber-400 mt-0.5 block text-center">
                            {simulationResult.confusion_matrix?.abstained ?? 0}
                          </span>
                          <span className="text-[9px] text-slate-400 block text-center">Routed to Analyst Review</span>
                          <span className="text-[9px] text-amber-400/70 group-hover:text-amber-300 text-center block pt-0.5">Click to inspect →</span>
                        </button>
                      </div>
                    </div>

                    {/* Empirical Accuracy Metrics Grid (displays N/A instead of 0%) */}
                    <div className="p-3.5 rounded-lg border border-slate-800 bg-slate-900/40 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Balanced Accuracy</div>
                        <div className="text-base font-bold font-mono text-cyan-400 mt-0.5">
                          {simulationResult.balanced_accuracy != null &&
                          simulationResult.recall != null &&
                          simulationResult.specificity != null
                            ? `${Math.round(simulationResult.balanced_accuracy * 100)}%`
                            : "NOT_CALCULABLE"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Precision / Recall</div>
                        <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                          {simulationResult.precision != null ? `${Math.round(simulationResult.precision * 100)}%` : "N/A"}
                          {" / "}
                          {simulationResult.recall != null ? `${Math.round(simulationResult.recall * 100)}%` : "N/A"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Specificity (TNR)</div>
                        <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                          {simulationResult.specificity != null
                            ? `${Math.round(simulationResult.specificity * 100)}%`
                            : "N/A"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">False Positive Rate (FPR)</div>
                        <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                          {simulationResult.false_positive_rate != null
                            ? `${Math.round(simulationResult.false_positive_rate * 100)}%`
                            : "N/A"}
                        </div>
                      </div>
                    </div>

                    {/* Calibration & Regression Stats Row */}
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Calibration Status</div>
                        <div className={`text-xs font-bold font-mono mt-1 ${simulationResult.is_calibrated ? "text-emerald-400" : "text-amber-400"}`}>
                          {simulationResult.calibration_status || (simulationResult.is_calibrated ? "CALIBRATED (N>=30)" : "NOT_CALIBRATED (N<30)")}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Brier Calibration Score</div>
                        <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                          {simulationResult.brier_score != null ? simulationResult.brier_score.toFixed(4) : "N/A"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Expected Calibration Error (ECE)</div>
                        <div className="text-base font-bold font-mono text-slate-200 mt-0.5">
                          {simulationResult.ece != null ? simulationResult.ece.toFixed(4) : "N/A"}
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 uppercase">Critical Regressions</div>
                        <div className={`text-base font-bold font-mono mt-0.5 ${simulationResult.critical_regressions > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                          {simulationResult.critical_regressions}
                        </div>
                      </div>
                    </div>

                    {/* Per-Incident Simulation Results Drilldown Table */}
                    {simulationResult.per_incident_results && simulationResult.per_incident_results.length > 0 && (
                      <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-2">
                        <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                          <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                            Per-Incident Simulation Verdicts &amp; Trust Scores ({simulationResult.per_incident_results.length} cases)
                          </span>
                        </div>
                        <div className="max-h-60 overflow-y-auto space-y-1">
                          {simulationResult.per_incident_results.map((r, i) => (
                            <div key={i} className="p-2 rounded bg-slate-900/60 border border-slate-800 flex items-center justify-between text-[11px]">
                              <div className="space-y-0.5">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono font-bold text-slate-200">{r.incident_id}</span>
                                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-mono border ${
                                    r.ground_truth === "VERIFIED_TP"
                                      ? "bg-rose-950 text-rose-300 border-rose-800"
                                      : r.ground_truth === "VERIFIED_FP"
                                      ? "bg-sky-950 text-sky-300 border-sky-800"
                                      : "bg-slate-900 text-slate-400 border-slate-800"
                                  }`}>
                                    GT: {r.ground_truth || "UNLABELED"}
                                  </span>
                                </div>
                                <div className="text-[10px] text-slate-400">
                                  AI Suggested: <span className="font-mono text-slate-300">{r.suggested_verdict}</span> | Effective: <span className="font-mono font-bold text-slate-200">{r.effective_verdict}</span>
                                </div>
                              </div>
                              <div className="text-right space-y-0.5">
                                <div className="flex items-center justify-end gap-1.5">
                                  <span className="text-[10px] text-slate-500 uppercase">Trust Score:</span>
                                  <span className="font-mono font-bold text-indigo-400">
                                    {r.trust_score != null ? `${r.trust_score}/10` : "NOT_CALCULABLE"}
                                  </span>
                                </div>
                                <div>
                                  <span className={`px-1.5 py-0.2 rounded text-[9px] font-semibold border ${
                                    r.is_critical_error
                                      ? "bg-red-950 text-red-300 border-red-800"
                                      : r.is_abstained
                                      ? "bg-amber-950 text-amber-300 border-amber-800"
                                      : r.is_correct
                                      ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                                      : "bg-slate-900 text-slate-400 border-slate-800"
                                  }`}>
                                    {r.is_critical_error ? "MISSED TP (FN)" : r.is_abstained ? "ABSTAINED" : r.is_correct ? "CORRECT" : "WRONG"}
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
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

      {/* Simulation Diagnostic Drilldown Modal */}
      {drilldownModal?.isOpen && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6 animate-in fade-in duration-150"
          onClick={(e) => {
            if (e.target === e.currentTarget) setDrilldownModal(null);
          }}
        >
          <div className="bg-slate-950 border border-slate-800 rounded-xl max-w-5xl w-full max-h-[88vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 bg-slate-900/80 flex items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <span className="p-1.5 rounded-lg bg-purple-950/80 border border-purple-800/80 text-purple-300">
                    <Database className="w-4 h-4" />
                  </span>
                  <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                    {drilldownModal.title}
                    <span className="px-2 py-0.5 rounded-full text-xs font-mono font-bold bg-purple-950 text-purple-300 border border-purple-800">
                      {drilldownModal.badgeCount}
                    </span>
                  </h3>
                </div>
                <p className="text-xs text-slate-400 pl-8">
                  {drilldownModal.description}
                </p>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  type="button"
                  onClick={() => {
                    const ids = (drilldownModal.items || [])
                      .map((it: any) => it.incident_id || it.id)
                      .filter(Boolean)
                      .join("\n");
                    if (ids) {
                      navigator.clipboard.writeText(ids);
                      setDrilldownCopied(true);
                      setTimeout(() => setDrilldownCopied(false), 2000);
                    }
                  }}
                  className="px-2.5 py-1 text-xs rounded border border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-300 flex items-center gap-1.5 transition-colors"
                  title="Copy list of incident IDs to clipboard"
                >
                  {drilldownCopied ? (
                    <>
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-emerald-300 font-semibold">Copied!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5 text-slate-400" />
                      <span>Copy IDs</span>
                    </>
                  )}
                </button>
                <button
                  type="button"
                  onClick={() => setDrilldownModal(null)}
                  className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition-colors"
                  title="Close (Esc)"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Filter & Search Bar */}
            <div className="p-3 border-b border-slate-800 bg-slate-950/60 flex flex-wrap items-center justify-between gap-3 text-xs">
              <div className="relative flex-1 min-w-[240px]">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter by Incident ID, Rule, Reason, or Detail..."
                  value={drilldownSearch}
                  onChange={(e) => setDrilldownSearch(e.target.value)}
                  className="w-full pl-8 pr-7 py-1.5 rounded bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 text-xs focus:outline-none focus:border-purple-600"
                />
                {drilldownSearch && (
                  <button
                    type="button"
                    onClick={() => setDrilldownSearch("")}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </div>

              {/* Exclusion Reason Quick Filters if available */}
              {(() => {
                const uniqueReasons = Array.from(
                  new Set(
                    (drilldownModal.items || [])
                      .map((it: any) => it.reason)
                      .filter(Boolean)
                  )
                ) as string[];

                if (uniqueReasons.length > 0) {
                  return (
                    <div className="flex items-center gap-1.5 overflow-x-auto pb-0.5 max-w-full">
                      <span className="text-[10px] uppercase font-bold text-slate-500 flex items-center gap-1">
                        <Filter className="w-3 h-3 text-slate-500" /> Reason:
                      </span>
                      <button
                        type="button"
                        onClick={() => setDrilldownReasonFilter("ALL")}
                        className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold transition-colors ${
                          drilldownReasonFilter === "ALL"
                            ? "bg-purple-950 text-purple-300 border border-purple-800"
                            : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                        }`}
                      >
                        ALL ({drilldownModal.items?.length || 0})
                      </button>
                      {uniqueReasons.map((rsn) => {
                        const count = (drilldownModal.items || []).filter((it: any) => it.reason === rsn).length;
                        return (
                          <button
                            key={rsn}
                            type="button"
                            onClick={() => setDrilldownReasonFilter(rsn)}
                            className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold transition-colors ${
                              drilldownReasonFilter === rsn
                                ? "bg-purple-950 text-purple-300 border border-purple-800"
                                : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                            }`}
                          >
                            {rsn} ({count})
                          </button>
                        );
                      })}
                    </div>
                  );
                }
                return null;
              })()}
            </div>

            {/* Modal Body / Table */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {(() => {
                const q = drilldownSearch.toLowerCase().trim();
                const filtered = (drilldownModal.items || []).filter((it: any) => {
                  if (drilldownReasonFilter !== "ALL" && it.reason !== drilldownReasonFilter) {
                    return false;
                  }
                  if (!q) return true;
                  const idStr = String(it.incident_id || it.id || "").toLowerCase();
                  const ruleStr = String(it.rule_id || it.incident_rule || "").toLowerCase();
                  const rsnStr = String(it.reason || it.ground_truth || it.status || it.effective_verdict || "").toLowerCase();
                  const detailStr = String(it.detail || it.comments || it.escalation_reason || "").toLowerCase();
                  return idStr.includes(q) || ruleStr.includes(q) || rsnStr.includes(q) || detailStr.includes(q);
                });

                if (filtered.length === 0) {
                  return (
                    <div className="py-12 text-center text-slate-500 space-y-2">
                      <AlertCircle className="w-8 h-8 text-slate-600 mx-auto" />
                      <p className="text-sm font-medium text-slate-400">No matching incident records found.</p>
                      <p className="text-xs text-slate-600">
                        {drilldownSearch
                          ? `No items matched search query "${drilldownSearch}"`
                          : "No items present for this stage."}
                      </p>
                    </div>
                  );
                }

                return (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-[11px] text-slate-500 px-1">
                      <span>Showing <strong>{filtered.length}</strong> of <strong>{drilldownModal.items?.length || 0}</strong> records</span>
                      <span className="font-mono text-[10px]">Rule: {selectedRuleId}</span>
                    </div>

                    <div className="rounded-lg border border-slate-800 overflow-hidden">
                      <table className="w-full text-left text-xs border-collapse">
                        <thead className="bg-slate-900/90 text-slate-400 text-[10px] uppercase font-bold border-b border-slate-800">
                          <tr>
                            <th className="py-2 px-3 w-12 text-center">#</th>
                            <th className="py-2 px-3 w-28">Incident ID</th>
                            <th className="py-2 px-3 w-48">Rule Association</th>
                            <th className="py-2 px-3 w-40">Status / Category</th>
                            <th className="py-2 px-3">Diagnostic Justification / Telemetry Detail</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/80 bg-slate-950/40">
                          {filtered.map((item: any, idx: number) => {
                            const incidentId = item.incident_id || item.id || `INC-${idx + 1}`;
                            const ruleAssoc = item.rule_id || item.incident_rule || (item.rule_id === null ? "None" : selectedRuleId);
                            const reasonBadge = item.reason || item.ground_truth || item.status || item.effective_verdict || "INSPECTED";
                            const detailText = item.detail || item.comments || item.escalation_reason || (
                              item.suggested_verdict ? `AI Suggested: ${item.suggested_verdict} | Effective: ${item.effective_verdict} (Trust: ${item.trust_score ?? 'N/A'}/10)` : "—"
                            );

                            // Reason badge color styling
                            let badgeStyle = "bg-slate-900 text-slate-300 border-slate-800";
                            if (reasonBadge === "RULE_MISMATCH") {
                              badgeStyle = "bg-indigo-950/60 text-indigo-300 border-indigo-800";
                            } else if (reasonBadge === "HEURISTIC_OR_ML_LABEL" || reasonBadge === "UNRESOLVED") {
                              badgeStyle = "bg-amber-950/60 text-amber-300 border-amber-800";
                            } else if (reasonBadge === "VERIFIED_TP" || reasonBadge === "TRUE_POSITIVE") {
                              badgeStyle = "bg-emerald-950/60 text-emerald-300 border-emerald-800";
                            } else if (reasonBadge === "VERIFIED_FP" || reasonBadge === "FALSE_POSITIVE") {
                              badgeStyle = "bg-sky-950/60 text-sky-300 border-sky-800";
                            } else if (reasonBadge === "EXCLUDED") {
                              badgeStyle = "bg-rose-950/60 text-rose-300 border-rose-800";
                            } else if (reasonBadge === "REQUIRES_ANALYST_ATTENTION" || reasonBadge === "ABSTAINED") {
                              badgeStyle = "bg-amber-950/60 text-amber-300 border-amber-800";
                            }

                            return (
                              <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                                <td className="py-2.5 px-3 text-center text-slate-500 font-mono text-[10px]">
                                  {idx + 1}
                                </td>
                                <td className="py-2.5 px-3">
                                  <span className="font-mono font-bold text-cyan-400 bg-cyan-950/30 px-1.5 py-0.5 rounded border border-cyan-900/50">
                                    {incidentId}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3">
                                  <span className="font-mono text-[11px] text-slate-300 break-all">
                                    {ruleAssoc}
                                  </span>
                                </td>
                                <td className="py-2.5 px-3">
                                  <div className="flex flex-col gap-1 items-start">
                                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${badgeStyle}`}>
                                      {reasonBadge}
                                    </span>
                                    {item.trust_score != null && (
                                      <span className="text-[10px] font-mono text-purple-400">
                                        Trust: {item.trust_score}/10
                                      </span>
                                    )}
                                    {item.is_critical_error && (
                                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-red-950 text-red-300 border border-red-800">
                                        CRITICAL MISSED TP
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="py-2.5 px-3 text-[11px] text-slate-300 leading-relaxed">
                                  {detailText}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                );
              })()}
            </div>

            {/* Modal Footer */}
            <div className="p-3 border-t border-slate-800 bg-slate-900/80 flex items-center justify-between text-xs text-slate-400">
              <span className="text-[11px] text-slate-500">
                🛡️ <strong>Governance Gating:</strong> Verification requires strict rule matching and independent analyst resolution.
              </span>
              <button
                type="button"
                onClick={() => setDrilldownModal(null)}
                className="px-4 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition-colors"
              >
                Close
              </button>
            </div>
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
