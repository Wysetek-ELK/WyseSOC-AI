"use client";

import React, { useState, useEffect } from "react";
import {
  FileCode,
  CheckCircle2,
  AlertTriangle,
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
  GitBranch,
  FileCheck,
  RefreshCw,
  Plus,
} from "lucide-react";
import { api, RuleItem, RulePrompt, PromptVersion } from "@/lib/api";

export default function PromptStudioPage() {
  const [rules, setRules] = useState<RuleItem[]>([]);
  const [selectedRuleId, setSelectedRuleId] = useState<string>("");
  const [rulePrompt, setRulePrompt] = useState<RulePrompt | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState<string>("");
  const [loadingRules, setLoadingRules] = useState(true);
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

  // Load rules on mount
  useEffect(() => {
    async function loadRules() {
      try {
        const res = await api.getRules({ page_size: 50 });
        setRules(res.items);
        if (res.items.length > 0) {
          setSelectedRuleId(res.items[0].id);
        }
      } catch (err: any) {
        console.error(err);
      } finally {
        setLoadingRules(false);
      }
    }
    loadRules();
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

  // Load rule prompt when rule changes
  const fetchPrompt = async (ruleId: string) => {
    if (!ruleId) return;
    setLoadingPrompt(true);
    setFeedback(null);
    try {
      const rp = await api.getRulePrompt(ruleId);
      setRulePrompt(rp);
      if (rp.versions && rp.versions.length > 0) {
        // Default to active version if set, else first version
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
    if (selectedRuleId) {
      fetchPrompt(selectedRuleId);
    }
  }, [selectedRuleId]);

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

  const selectedVersion = rulePrompt?.versions.find((v) => v.id === selectedVersionId);
  const isSelectedActive = selectedVersion?.id === rulePrompt?.active_version_id;

  return (
    <div className="space-y-3">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-800 pb-2.5">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100">Rule Prompt Studio</h1>
            <span className="px-1.5 py-0.2 rounded-full text-[10px] font-semibold bg-sky-950/80 text-sky-400 border border-sky-800/60 font-mono">
              Phase 2 Active
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Deterministic prompt template engineering, version management, approval gating, and safe rollback.
          </p>
        </div>

        {/* SIEM Rule Selector */}
        <div className="flex items-center gap-2">
          <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Select Rule:</label>
          <select
            value={selectedRuleId}
            onChange={(e) => {
              const newRuleId = e.target.value;
              setSelectedRuleId(newRuleId);
              clearForm();
            }}
            disabled={loadingRules}
            className="px-2.5 py-1 text-xs rounded-md border border-slate-800 bg-slate-950 text-slate-200 font-medium focus:outline-none focus:border-cyan-500 min-w-[240px]"
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
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-1.5 text-slate-600" />
          Loading prompt studio specifications...
        </div>
      ) : !rulePrompt ? (
        <div className="p-6 border border-slate-800 rounded-lg text-center text-slate-500 text-xs">
          No prompt found for this SIEM rule.
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
                  <label className="text-[11px] font-bold text-slate-200 uppercase tracking-wider flex items-center gap-1.5">
                    <Layers className="w-3 h-3 text-slate-400" />
                    1. Common SOC Baseline Protocol
                  </label>
                  <span className="text-[9px] text-slate-500">Shared across all rules</span>
                </div>
                <textarea
                  rows={3}
                  disabled={!isEditing}
                  value={editCommon}
                  onChange={(e) => setEditCommon(e.target.value)}
                  className={`w-full p-2 text-xs rounded border bg-slate-950 text-slate-200 font-mono focus:outline-none ${
                    isEditing ? "border-slate-700" : "border-slate-850 opacity-90"
                  }`}
                />
              </div>

              {/* Section 2: Rule-Specific Directive */}
              <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-bold text-sky-300 uppercase tracking-wider flex items-center gap-1.5">
                    <FileCode className="w-3 h-3 text-sky-400" />
                    2. Rule-Specific Directive &amp; Pattern Details
                  </label>
                  <span className="text-[9px] text-sky-500 font-medium">Custom tailored per detection</span>
                </div>
                <textarea
                  rows={3}
                  disabled={!isEditing}
                  value={editRuleSpecific}
                  onChange={(e) => setEditRuleSpecific(e.target.value)}
                  className={`w-full p-2 text-xs rounded border bg-slate-950 text-slate-200 font-mono focus:outline-none ${
                    isEditing ? "border-slate-700" : "border-slate-850 opacity-90"
                  }`}
                />
              </div>

              {/* Grid 3 & 4: Detection Conditions & Required Evidence */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                    3. Detection Conditions &amp; Pattern Logic
                  </label>
                  <textarea
                    rows={3}
                    disabled={!isEditing}
                    value={editConditions}
                    onChange={(e) => setEditConditions(e.target.value)}
                    className={`w-full p-2 text-xs rounded border bg-slate-950 text-slate-200 font-mono focus:outline-none ${
                      isEditing ? "border-slate-700" : "border-slate-850 opacity-90"
                    }`}
                  />
                </div>

                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                    4. Mandatory Evidence Gathering Checklist
                  </label>
                  <textarea
                    rows={3}
                    disabled={!isEditing}
                    value={editEvidence}
                    onChange={(e) => setEditEvidence(e.target.value)}
                    className={`w-full p-2 text-xs rounded border bg-slate-950 text-slate-200 font-mono focus:outline-none ${
                      isEditing ? "border-slate-700" : "border-slate-850 opacity-90"
                    }`}
                  />
                </div>
              </div>

              {/* Grid 5 & 6: TP Indicators vs FP Indicators */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                <div className="p-3 rounded-lg border border-rose-950/40 bg-rose-950/10 space-y-1.5">
                  <label className="text-[11px] font-bold text-rose-300 uppercase tracking-wider block">
                    5. True Positive (Malicious) Indicators
                  </label>
                  <textarea
                    rows={3}
                    disabled={!isEditing}
                    value={editTpIndicators}
                    onChange={(e) => setEditTpIndicators(e.target.value)}
                    className={`w-full p-2 text-xs rounded border bg-slate-950 text-slate-200 font-mono focus:outline-none ${
                      isEditing ? "border-rose-900/70" : "border-slate-850 opacity-90"
                    }`}
                  />
                </div>

                <div className="p-3 rounded-lg border border-emerald-950/40 bg-emerald-950/10 space-y-1.5">
                  <label className="text-[11px] font-bold text-emerald-300 uppercase tracking-wider block">
                    6. False Positive (Benign) Indicators
                  </label>
                  <textarea
                    rows={3}
                    disabled={!isEditing}
                    value={editFpIndicators}
                    onChange={(e) => setEditFpIndicators(e.target.value)}
                    className={`w-full p-2 text-xs rounded border bg-slate-950 text-slate-200 font-mono focus:outline-none ${
                      isEditing ? "border-emerald-900/70" : "border-slate-850 opacity-90"
                    }`}
                  />
                </div>
              </div>

              {/* Grid 7 & 8: Missing Info Criteria & Escalation Conditions */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                <div className="p-3 rounded-lg border border-amber-950/40 bg-amber-950/10 space-y-1.5">
                  <label className="text-[11px] font-bold text-amber-300 uppercase tracking-wider block">
                    7. Insufficient Evidence Criteria
                  </label>
                  <textarea
                    rows={2.5}
                    disabled={!isEditing}
                    value={editMissingInfo}
                    onChange={(e) => setEditMissingInfo(e.target.value)}
                    className={`w-full p-2 text-xs rounded border bg-slate-950 text-slate-200 font-mono focus:outline-none ${
                      isEditing ? "border-amber-900/70" : "border-slate-850 opacity-90"
                    }`}
                  />
                </div>

                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-1.5">
                  <label className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                    8. Escalation &amp; Containment Conditions
                  </label>
                  <textarea
                    rows={2.5}
                    disabled={!isEditing}
                    value={editEscalation}
                    onChange={(e) => setEditEscalation(e.target.value)}
                    className={`w-full p-2 text-xs rounded border bg-slate-950 text-slate-200 font-mono focus:outline-none ${
                      isEditing ? "border-slate-700" : "border-slate-850 opacity-90"
                    }`}
                  />
                </div>
              </div>

              {/* Section 9: Standard Investigative Questions Checklist */}
              <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/30 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-bold text-slate-200 uppercase tracking-wider block">
                    9. Standard Investigative Q&amp;A Checklist ({editQuestions.length})
                  </label>
                </div>

                {editQuestions.length === 0 ? (
                  <div className="text-xs text-slate-500 italic">No checklist questions specified.</div>
                ) : (
                  <div className="space-y-1">
                    {editQuestions.map((q, idx) => (
                      <div key={idx} className="flex items-center justify-between p-1.5 rounded bg-slate-950 border border-slate-800 text-xs">
                        <span className="text-slate-200 font-mono text-[11px]">{idx + 1}. {q}</span>
                        {isEditing && (
                          <button
                            type="button"
                            onClick={() => handleRemoveQuestion(idx)}
                            className="text-slate-500 hover:text-rose-400 text-xs"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {isEditing && (
                  <div className="flex gap-1.5 pt-1.5 border-t border-slate-800">
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
