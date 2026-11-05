"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  Search,
  Filter,
  UserCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  HelpCircle,
  FileText,
  Plus,
  Send,
  Eye,
  X,
  RefreshCw,
  Tag,
  Paperclip,
  Check,
  ShieldCheck,
  Info,
} from "lucide-react";
import { api, InvestigationListItem, InvestigationDetail, User } from "@/lib/api";

export default function AnalystAttentionPage() {
  const [items, setItems] = useState<InvestigationListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [verdictFilter, setVerdictFilter] = useState("");
  const [disputedFilter, setDisputedFilter] = useState<boolean | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [selectedInvestigation, setSelectedInvestigation] = useState<InvestigationDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [users, setUsers] = useState<User[]>([]);

  // Form states inside investigation drawer
  const [newQuestion, setNewQuestion] = useState("");
  const [activeAnswerId, setActiveAnswerId] = useState<string | null>(null);
  const [answerText, setAnswerText] = useState("");

  const [evidenceType, setEvidenceType] = useState("TELEMETRY");
  const [evidenceKey, setEvidenceKey] = useState("");
  const [evidenceContent, setEvidenceContent] = useState("");
  const [evidenceRationale, setEvidenceRationale] = useState("");

  const [verdictChoice, setVerdictChoice] = useState<string>("TRUE_POSITIVE");
  const [verdictReason, setVerdictReason] = useState("");
  const [analystNotes, setAnalystNotes] = useState("");
  const [insufficientReason, setInsufficientReason] = useState("");
  const [isDisputed, setIsDisputed] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [submittingVerdict, setSubmittingVerdict] = useState(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchQueue = async () => {
    setLoading(true);
    try {
      const res = await api.getInvestigationsQueue({
        page,
        page_size: 20,
        status: statusFilter || undefined,
        verdict: verdictFilter || undefined,
        is_disputed: disputedFilter,
        search: search || undefined,
      });
      setItems(res.items);
      setTotal(res.total);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
  }, [page, statusFilter, verdictFilter, disputedFilter]);

  useEffect(() => {
    api.getUsers().then(setUsers).catch(() => {});
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchQueue();
  };

  const openInvestigation = async (id: string) => {
    setLoadingDetail(true);
    setFeedbackMsg(null);
    try {
      const detail = await api.getInvestigation(id);
      setSelectedInvestigation(detail);
      setVerdictChoice(detail.analyst_verdict || "TRUE_POSITIVE");
      setVerdictReason(detail.verdict_reason || "");
      setAnalystNotes(detail.analyst_notes || "");
      setInsufficientReason(detail.insufficient_evidence_reason || "");
      setIsDisputed(detail.is_disputed);
      setIsVerified(detail.is_independently_verified);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleAssign = async (userId: string | null) => {
    if (!selectedInvestigation) return;
    try {
      await api.assignInvestigation(selectedInvestigation.id, userId);
      const updated = await api.getInvestigation(selectedInvestigation.id);
      setSelectedInvestigation(updated);
      fetchQueue();
      setFeedbackMsg({ type: "success", text: "Analyst assignment updated." });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    }
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!selectedInvestigation) return;
    try {
      await api.updateInvestigationStatus(selectedInvestigation.id, newStatus);
      const updated = await api.getInvestigation(selectedInvestigation.id);
      setSelectedInvestigation(updated);
      fetchQueue();
      setFeedbackMsg({ type: "success", text: `Status updated to ${newStatus}` });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    }
  };

  const handleAddQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvestigation || !newQuestion.trim()) return;
    try {
      await api.addInvestigationQuestion(selectedInvestigation.id, newQuestion);
      setNewQuestion("");
      const updated = await api.getInvestigation(selectedInvestigation.id);
      setSelectedInvestigation(updated);
      fetchQueue();
      setFeedbackMsg({ type: "success", text: "Investigation question added." });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    }
  };

  const handleAnswerQuestion = async (questionId: string) => {
    if (!selectedInvestigation || !answerText.trim()) return;
    try {
      await api.answerInvestigationQuestion(questionId, answerText);
      setAnswerText("");
      setActiveAnswerId(null);
      const updated = await api.getInvestigation(selectedInvestigation.id);
      setSelectedInvestigation(updated);
      setFeedbackMsg({ type: "success", text: "Question answered." });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    }
  };

  const handleAttachEvidence = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvestigation || !evidenceContent.trim()) return;
    try {
      await api.attachInvestigationEvidence(selectedInvestigation.id, {
        evidence_type: evidenceType,
        reference_key: evidenceKey,
        evidence_content: evidenceContent,
        analyst_rationale: evidenceRationale,
      });
      setEvidenceKey("");
      setEvidenceContent("");
      setEvidenceRationale("");
      const updated = await api.getInvestigation(selectedInvestigation.id);
      setSelectedInvestigation(updated);
      fetchQueue();
      setFeedbackMsg({ type: "success", text: "Evidence artifact attached." });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    }
  };

  const handleSubmitVerdict = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedInvestigation) return;
    setSubmittingVerdict(true);
    setFeedbackMsg(null);
    try {
      await api.submitInvestigationVerdict(selectedInvestigation.id, {
        analyst_verdict: verdictChoice,
        verdict_reason: verdictReason,
        analyst_notes: analystNotes,
        insufficient_evidence_reason: verdictChoice === "REQUIRES_ATTENTION" ? insufficientReason : null,
        is_disputed: isDisputed,
        is_independently_verified: isVerified,
        status: "REVIEWED",
      });
      const updated = await api.getInvestigation(selectedInvestigation.id);
      setSelectedInvestigation(updated);
      fetchQueue();
      setFeedbackMsg({ type: "success", text: `Verdict ${verdictChoice} submitted and verified successfully!` });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err.message });
    } finally {
      setSubmittingVerdict(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PENDING_REVIEW":
        return "bg-amber-950/60 text-amber-400 border-amber-800/60";
      case "ASSIGNED":
        return "bg-blue-950/60 text-blue-400 border-blue-800/60";
      case "IN_PROGRESS":
        return "bg-indigo-950/60 text-indigo-400 border-indigo-800/60";
      case "AWAITING_INFORMATION":
        return "bg-purple-950/60 text-purple-400 border-purple-800/60";
      case "REVIEWED":
        return "bg-emerald-950/60 text-emerald-400 border-emerald-800/60";
      case "CLOSED_DRY_RUN":
        return "bg-zinc-800 text-zinc-300 border-zinc-700";
      default:
        return "bg-zinc-800 text-zinc-400 border-zinc-700";
    }
  };

  const getVerdictBadge = (verdict: string | null | undefined) => {
    if (!verdict) return <span className="text-xs text-zinc-500">Unlabeled</span>;
    switch (verdict) {
      case "TRUE_POSITIVE":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/50"><ShieldAlert className="w-3 h-3" /> True Positive</span>;
      case "FALSE_POSITIVE":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/50"><ShieldCheck className="w-3 h-3" /> False Positive</span>;
      case "REQUIRES_ATTENTION":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold bg-amber-950/60 text-amber-400 border border-amber-800/50"><AlertTriangle className="w-3 h-3" /> Requires Attention</span>;
      default:
        return <span className="text-xs text-zinc-400">{verdict}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-zinc-100">Analyst Attention Queue</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-sky-950/80 text-sky-400 border border-sky-800/60">
              Phase 2 Active
            </span>
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Enterprise investigation console, Q&amp;A threads, evidence attribution, and verified verdict recording.
          </p>
        </div>
        <button
          onClick={fetchQueue}
          className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-zinc-200 border border-zinc-700 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Queue
        </button>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <div className="p-3.5 rounded-lg border border-zinc-800 bg-zinc-900/60">
          <div className="text-xs font-medium text-zinc-400">Total Incidents</div>
          <div className="text-2xl font-bold text-zinc-100 mt-1">{total}</div>
        </div>
        <div className="p-3.5 rounded-lg border border-amber-900/30 bg-amber-950/10">
          <div className="text-xs font-medium text-amber-400">Pending Review</div>
          <div className="text-2xl font-bold text-amber-300 mt-1">
            {items.filter((i) => i.status === "PENDING_REVIEW").length}
          </div>
        </div>
        <div className="p-3.5 rounded-lg border border-indigo-900/30 bg-indigo-950/10">
          <div className="text-xs font-medium text-indigo-400">In Progress / Assigned</div>
          <div className="text-2xl font-bold text-indigo-300 mt-1">
            {items.filter((i) => i.status === "ASSIGNED" || i.status === "IN_PROGRESS" || i.status === "AWAITING_INFORMATION").length}
          </div>
        </div>
        <div className="p-3.5 rounded-lg border border-emerald-900/30 bg-emerald-950/10">
          <div className="text-xs font-medium text-emerald-400">Analyst Reviewed</div>
          <div className="text-2xl font-bold text-emerald-300 mt-1">
            {items.filter((i) => i.status === "REVIEWED").length}
          </div>
        </div>
        <div className="p-3.5 rounded-lg border border-rose-900/30 bg-rose-950/10">
          <div className="text-xs font-medium text-rose-400">Disputed Cases</div>
          <div className="text-2xl font-bold text-rose-300 mt-1">
            {items.filter((i) => i.is_disputed).length}
          </div>
        </div>
      </div>

      {/* Filters & Search */}
      <div className="p-4 rounded-lg border border-zinc-800 bg-zinc-900/40 space-y-3">
        <div className="flex flex-col md:flex-row gap-3">
          <form onSubmit={handleSearchSubmit} className="flex-1 flex gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3 top-2.5 text-zinc-500" />
              <input
                type="text"
                placeholder="Search incident ID, title, IP, command line..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs rounded-md border border-zinc-800 bg-zinc-950 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium rounded-md border border-zinc-700 transition-colors"
            >
              Filter
            </button>
          </form>

          <div className="flex flex-wrap gap-2 items-center">
            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 text-xs rounded-md border border-zinc-800 bg-zinc-950 text-zinc-300 focus:outline-none focus:border-zinc-700"
            >
              <option value="">All Review Statuses</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="AWAITING_INFORMATION">Awaiting Info</option>
              <option value="REVIEWED">Reviewed</option>
              <option value="CLOSED_DRY_RUN">Closed (Dry-Run)</option>
            </select>

            {/* Verdict Filter */}
            <select
              value={verdictFilter}
              onChange={(e) => {
                setVerdictFilter(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1.5 text-xs rounded-md border border-zinc-800 bg-zinc-950 text-zinc-300 focus:outline-none focus:border-zinc-700"
            >
              <option value="">All Analyst Verdicts</option>
              <option value="TRUE_POSITIVE">True Positive</option>
              <option value="FALSE_POSITIVE">False Positive</option>
              <option value="REQUIRES_ATTENTION">Requires Attention</option>
            </select>

            {/* Disputed Toggle */}
            <button
              onClick={() => {
                setDisputedFilter(disputedFilter === true ? undefined : true);
                setPage(1);
              }}
              className={`px-3 py-1.5 text-xs font-medium rounded-md border transition-colors ${
                disputedFilter === true
                  ? "bg-rose-950 text-rose-300 border-rose-800"
                  : "bg-zinc-950 text-zinc-400 border-zinc-800 hover:bg-zinc-800"
              }`}
            >
              {disputedFilter === true ? "Showing Disputed Only" : "Disputed Only"}
            </button>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="border border-zinc-800 rounded-lg overflow-hidden bg-zinc-900/30">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-zinc-300">
            <thead className="bg-zinc-900/80 text-zinc-400 uppercase tracking-wider text-[11px] border-b border-zinc-800">
              <tr>
                <th className="py-3 px-4 font-semibold">Incident ID / Title</th>
                <th className="py-3 px-3 font-semibold">Rule / Event Type</th>
                <th className="py-3 px-3 font-semibold">Severity</th>
                <th className="py-3 px-3 font-semibold">Status</th>
                <th className="py-3 px-3 font-semibold">Assigned Analyst</th>
                <th className="py-3 px-3 font-semibold">Analyst Verdict</th>
                <th className="py-3 px-3 font-semibold text-center">Telemetry</th>
                <th className="py-3 px-4 text-right font-semibold">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-850">
              {loading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-zinc-500">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-zinc-600" />
                    Loading investigation queue...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-zinc-500">
                    No incidents matching selected filters in queue.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="hover:bg-zinc-800/40 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-zinc-100 flex items-center gap-1.5">
                        {item.incident_vendor_id || item.incident_id}
                        {item.is_disputed && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-rose-950 text-rose-400 border border-rose-800">
                            Disputed
                          </span>
                        )}
                      </div>
                      <div className="text-zinc-400 text-[11px] line-clamp-1 max-w-sm mt-0.5">
                        {item.title}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-zinc-300">
                      <div className="font-medium text-zinc-200 line-clamp-1">{item.rule_name || item.event_type}</div>
                      <div className="text-[10px] text-zinc-500 font-mono">{item.event_type}</div>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        item.severity === "CRITICAL"
                          ? "bg-rose-950/70 text-rose-400 border border-rose-800/60"
                          : item.severity === "HIGH"
                          ? "bg-orange-950/70 text-orange-400 border border-orange-800/60"
                          : "bg-amber-950/70 text-amber-400 border border-amber-800/60"
                      }`}>
                        {item.severity || "MEDIUM"}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-medium border ${getStatusBadge(item.status)}`}>
                        {item.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-zinc-300">
                      {item.assigned_to_username ? (
                        <span className="inline-flex items-center gap-1 text-zinc-200 font-medium">
                          <UserCheck className="w-3.5 h-3.5 text-sky-400" />
                          {item.assigned_to_username}
                        </span>
                      ) : (
                        <span className="text-zinc-500 text-xs italic">Unassigned</span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      {getVerdictBadge(item.analyst_verdict)}
                    </td>
                    <td className="py-3 px-3 text-center">
                      <div className="inline-flex gap-2 text-zinc-400 text-xs">
                        <span title="Questions & Answers" className="flex items-center gap-0.5">
                          <HelpCircle className="w-3.5 h-3.5 text-zinc-500" /> {item.question_count}
                        </span>
                        <span title="Evidence Artifacts" className="flex items-center gap-0.5">
                          <Paperclip className="w-3.5 h-3.5 text-zinc-500" /> {item.evidence_count}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={() => openInvestigation(item.id)}
                        className="px-3 py-1 bg-sky-950/60 hover:bg-sky-900/60 text-sky-300 border border-sky-800/60 rounded text-xs font-medium transition-colors"
                      >
                        Investigate
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Investigation Detail Workspace Drawer / Modal */}
      {selectedInvestigation && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-3xl bg-zinc-950 border-l border-zinc-800 h-full overflow-y-auto flex flex-col p-6 space-y-6 shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="flex items-start justify-between border-b border-zinc-800 pb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                    {selectedInvestigation.incident_vendor_id}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getStatusBadge(selectedInvestigation.status)}`}>
                    {selectedInvestigation.status.replace("_", " ")}
                  </span>
                  {selectedInvestigation.is_disputed && (
                    <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-950 text-rose-400 border border-rose-800">
                      Disputed
                    </span>
                  )}
                </div>
                <h2 className="text-lg font-bold text-zinc-100 mt-1.5">{selectedInvestigation.title}</h2>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Rule: <span className="text-zinc-300 font-medium">{selectedInvestigation.rule_name}</span> &bull; Event: <span className="font-mono">{selectedInvestigation.event_type}</span>
                </p>
              </div>
              <button
                onClick={() => setSelectedInvestigation(null)}
                className="p-1 rounded-md text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {feedbackMsg && (
              <div className={`p-3 rounded-md text-xs border ${
                feedbackMsg.type === "success"
                  ? "bg-emerald-950/60 border-emerald-800 text-emerald-300"
                  : "bg-rose-950/60 border-rose-800 text-rose-300"
              }`}>
                {feedbackMsg.text}
              </div>
            )}

            {/* Quick Actions Bar: Assignment & Status */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-3.5 rounded-lg border border-zinc-800 bg-zinc-900/40">
              <div>
                <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block mb-1.5">
                  Analyst Assignment
                </label>
                <div className="flex gap-2">
                  <select
                    value={selectedInvestigation.assigned_to_user_id || ""}
                    onChange={(e) => handleAssign(e.target.value || null)}
                    className="flex-1 px-2.5 py-1.5 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none"
                  >
                    <option value="">Unassigned</option>
                    {users.map((u) => (
                      <option key={u.id} value={u.id}>
                        {u.full_name || u.username} ({u.role})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider block mb-1.5">
                  Workflow Status
                </label>
                <select
                  value={selectedInvestigation.status}
                  onChange={(e) => handleStatusChange(e.target.value)}
                  className="w-full px-2.5 py-1.5 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none"
                >
                  <option value="PENDING_REVIEW">Pending Review</option>
                  <option value="ASSIGNED">Assigned</option>
                  <option value="IN_PROGRESS">In Progress</option>
                  <option value="AWAITING_INFORMATION">Awaiting Information</option>
                  <option value="REVIEWED">Reviewed</option>
                  <option value="CLOSED_DRY_RUN">Closed in Dry-Run Environment</option>
                </select>
              </div>
            </div>

            {/* Incident Telemetry Summary */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 p-3 rounded-lg border border-zinc-800/80 bg-zinc-900/20 text-xs">
              <div>
                <span className="text-zinc-500 block text-[10px] uppercase">Source IP</span>
                <span className="font-mono text-zinc-200">{selectedInvestigation.source_ip || "N/A"}</span>
              </div>
              <div>
                <span className="text-zinc-500 block text-[10px] uppercase">Reporting Device</span>
                <span className="font-medium text-zinc-200">{selectedInvestigation.reporting_device || "N/A"}</span>
              </div>
              <div>
                <span className="text-zinc-500 block text-[10px] uppercase">Severity</span>
                <span className="font-medium text-zinc-200">{selectedInvestigation.severity || "MEDIUM"}</span>
              </div>
              <div>
                <span className="text-zinc-500 block text-[10px] uppercase">Full Dossier</span>
                <Link
                  href={`/incidents/${selectedInvestigation.incident_id}`}
                  className="text-sky-400 hover:underline flex items-center gap-1 font-medium"
                >
                  <Eye className="w-3.5 h-3.5" /> View Incident
                </Link>
              </div>
            </div>

            {/* Section 1: Investigation Q&A */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                  <HelpCircle className="w-4 h-4 text-sky-400" />
                  Investigation Questions &amp; Answers
                </h3>
                <span className="text-xs text-zinc-500 font-mono">
                  {selectedInvestigation.questions.length} items
                </span>
              </div>

              {selectedInvestigation.questions.length === 0 ? (
                <div className="p-4 border border-dashed border-zinc-800 rounded-lg text-center text-xs text-zinc-500">
                  No investigation questions recorded yet. Add investigative hypotheses below.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {selectedInvestigation.questions.map((q) => (
                    <div key={q.id} className="p-3 rounded-lg border border-zinc-800/90 bg-zinc-900/40 text-xs space-y-2">
                      <div className="font-semibold text-zinc-200 flex items-start gap-2">
                        <span className="text-sky-400 font-bold">Q:</span>
                        <span>{q.question}</span>
                      </div>
                      {q.answer ? (
                        <div className="pl-4 border-l-2 border-emerald-600 text-zinc-300">
                          <span className="text-emerald-400 font-semibold block text-[11px]">Analyst Response:</span>
                          <span className="text-zinc-200 whitespace-pre-wrap">{q.answer}</span>
                        </div>
                      ) : (
                        <div className="pl-4">
                          {activeAnswerId === q.id ? (
                            <div className="space-y-2 mt-2">
                              <textarea
                                value={answerText}
                                onChange={(e) => setAnswerText(e.target.value)}
                                placeholder="Enter investigative answer..."
                                rows={2}
                                className="w-full p-2 text-xs rounded border border-zinc-700 bg-zinc-950 text-zinc-200 focus:outline-none"
                              />
                              <div className="flex gap-2 justify-end">
                                <button
                                  type="button"
                                  onClick={() => setActiveAnswerId(null)}
                                  className="px-2.5 py-1 text-xs text-zinc-400 hover:text-zinc-200"
                                >
                                  Cancel
                                </button>
                                <button
                                  type="button"
                                  onClick={() => handleAnswerQuestion(q.id)}
                                  className="px-3 py-1 bg-emerald-700 hover:bg-emerald-600 text-zinc-100 rounded text-xs font-medium"
                                >
                                  Save Answer
                                </button>
                              </div>
                            </div>
                          ) : (
                            <button
                              type="button"
                              onClick={() => {
                                setActiveAnswerId(q.id);
                                setAnswerText("");
                              }}
                              className="text-xs text-sky-400 hover:underline"
                            >
                              + Answer this question
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Add Question Input */}
              <form onSubmit={handleAddQuestion} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Record an investigation question (e.g. Is parent process signed?)..."
                  value={newQuestion}
                  onChange={(e) => setNewQuestion(e.target.value)}
                  className="flex-1 px-3 py-1.5 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-xs font-medium border border-zinc-700 transition-colors"
                >
                  Add Question
                </button>
              </form>
            </div>

            {/* Section 2: Supporting Evidence Artifacts */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-zinc-200 flex items-center gap-2">
                  <Paperclip className="w-4 h-4 text-emerald-400" />
                  Supporting Evidence Artifacts
                </h3>
                <span className="text-xs text-zinc-500 font-mono">
                  {selectedInvestigation.evidence_items.length} artifacts
                </span>
              </div>

              {selectedInvestigation.evidence_items.length > 0 && (
                <div className="space-y-2">
                  {selectedInvestigation.evidence_items.map((ev) => (
                    <div key={ev.id} className="p-3 rounded-lg border border-zinc-800 bg-zinc-900/30 text-xs space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-zinc-800 text-zinc-300 font-mono">
                          {ev.evidence_type}
                        </span>
                        <span className="text-[10px] text-zinc-500 font-mono">{ev.reference_key}</span>
                      </div>
                      <div className="font-mono text-zinc-300 bg-zinc-950 p-2 rounded border border-zinc-850 mt-1 whitespace-pre-wrap">
                        {ev.evidence_content}
                      </div>
                      {ev.analyst_rationale && (
                        <div className="text-zinc-400 text-[11px] pt-1">
                          <span className="text-zinc-500 font-semibold">Rationale: </span>
                          {ev.analyst_rationale}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Attach Evidence Form */}
              <form onSubmit={handleAttachEvidence} className="p-3 rounded-lg border border-zinc-800 bg-zinc-900/30 space-y-2 text-xs">
                <div className="font-semibold text-zinc-300">Attach New Evidence Artifact</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] uppercase text-zinc-500">Type</label>
                    <select
                      value={evidenceType}
                      onChange={(e) => setEvidenceType(e.target.value)}
                      className="w-full px-2 py-1 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-300"
                    >
                      <option value="TELEMETRY">Telemetry Log</option>
                      <option value="PROCESS_TREE">Process Tree</option>
                      <option value="FILE_HASH">File Hash (SHA256/MD5)</option>
                      <option value="NETWORK">Network Artifact / IP</option>
                      <option value="REGISTRY">Registry Key</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] uppercase text-zinc-500">Reference Key / Artifact</label>
                    <input
                      type="text"
                      placeholder="e.g. powershell.exe -enc"
                      value={evidenceKey}
                      onChange={(e) => setEvidenceKey(e.target.value)}
                      className="w-full px-2 py-1 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-300"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-[10px] uppercase text-zinc-500">Artifact Content</label>
                  <textarea
                    rows={2}
                    placeholder="Raw artifact details or decoded command payload..."
                    value={evidenceContent}
                    onChange={(e) => setEvidenceContent(e.target.value)}
                    className="w-full px-2 py-1 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-300 font-mono"
                  />
                </div>
                <div>
                  <label className="text-[10px] uppercase text-zinc-500">Analyst Rationale</label>
                  <input
                    type="text"
                    placeholder="Why this artifact proves malicious or benign activity..."
                    value={evidenceRationale}
                    onChange={(e) => setEvidenceRationale(e.target.value)}
                    className="w-full px-2 py-1 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-300"
                  />
                </div>
                <button
                  type="submit"
                  className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded text-xs font-medium border border-zinc-700"
                >
                  Save Evidence
                </button>
              </form>
            </div>

            {/* Section 3: Final Analyst Verdict Console */}
            <form onSubmit={handleSubmitVerdict} className="p-4 rounded-lg border border-sky-900/50 bg-sky-950/10 space-y-4">
              <div className="flex items-center justify-between border-b border-sky-900/40 pb-2">
                <h3 className="text-sm font-bold text-sky-300 flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-sky-400" />
                  Record Verified Analyst Verdict
                </h3>
                <span className="text-[10px] text-zinc-400 font-mono">Dual-Verdict Architecture</span>
              </div>

              {/* Notice regarding ground truth safety */}
              <div className="flex items-start gap-2 p-2.5 rounded bg-zinc-900/90 border border-zinc-800 text-[11px] text-zinc-400">
                <Info className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
                <span>
                  <strong>Ground Truth Isolation Guarantee:</strong> Your verified verdict is stored in the analyst investigation repository. The imported SIEM historical ground truth remains permanently isolated in its dedicated table to ensure zero training contamination.
                </span>
              </div>

              {/* Verdict Selection */}
              <div>
                <label className="text-xs font-semibold text-zinc-300 block mb-2">Verdict Outcome</label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    type="button"
                    onClick={() => setVerdictChoice("TRUE_POSITIVE")}
                    className={`py-2 px-3 text-xs font-bold rounded border transition-colors flex items-center justify-center gap-1.5 ${
                      verdictChoice === "TRUE_POSITIVE"
                        ? "bg-rose-950 text-rose-300 border-rose-700 shadow-sm"
                        : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:bg-zinc-800"
                    }`}
                  >
                    <ShieldAlert className="w-3.5 h-3.5" /> True Positive
                  </button>
                  <button
                    type="button"
                    onClick={() => setVerdictChoice("FALSE_POSITIVE")}
                    className={`py-2 px-3 text-xs font-bold rounded border transition-colors flex items-center justify-center gap-1.5 ${
                      verdictChoice === "FALSE_POSITIVE"
                        ? "bg-emerald-950 text-emerald-300 border-emerald-700 shadow-sm"
                        : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:bg-zinc-800"
                    }`}
                  >
                    <ShieldCheck className="w-3.5 h-3.5" /> False Positive
                  </button>
                  <button
                    type="button"
                    onClick={() => setVerdictChoice("REQUIRES_ATTENTION")}
                    className={`py-2 px-3 text-xs font-bold rounded border transition-colors flex items-center justify-center gap-1.5 ${
                      verdictChoice === "REQUIRES_ATTENTION"
                        ? "bg-amber-950 text-amber-300 border-amber-700 shadow-sm"
                        : "bg-zinc-900 text-zinc-400 border-zinc-800 hover:bg-zinc-800"
                    }`}
                  >
                    <AlertTriangle className="w-3.5 h-3.5" /> Requires Attention
                  </button>
                </div>
              </div>

              {/* Insufficient Evidence Reason (Conditional or Highlighted) */}
              {verdictChoice === "REQUIRES_ATTENTION" && (
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-amber-300 flex items-center gap-1">
                    <AlertTriangle className="w-3.5 h-3.5" />
                    Explicit Insufficient Evidence Reason (Mandatory)
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="Specify why evidence is insufficient (e.g., Parent command line truncated in raw event)..."
                    value={insufficientReason}
                    onChange={(e) => setInsufficientReason(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded border border-amber-800/80 bg-zinc-950 text-amber-200 placeholder-zinc-500 focus:outline-none"
                  />
                </div>
              )}

              {/* Rationale & Notes */}
              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-300">Investigation Verdict Rationale</label>
                <textarea
                  rows={2}
                  required
                  placeholder="Explain the definitive rationale for this verdict..."
                  value={verdictReason}
                  onChange={(e) => setVerdictReason(e.target.value)}
                  className="w-full p-2.5 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-300">Analyst Handover Notes (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Remediation steps taken, host isolation notes, or follow-ups..."
                  value={analystNotes}
                  onChange={(e) => setAnalystNotes(e.target.value)}
                  className="w-full p-2.5 text-xs rounded border border-zinc-800 bg-zinc-950 text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-zinc-700"
                />
              </div>

              {/* Quality Flags */}
              <div className="space-y-2 pt-2 border-t border-zinc-800/80">
                <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isDisputed}
                    onChange={(e) => setIsDisputed(e.target.checked)}
                    className="rounded border-zinc-700 bg-zinc-950 text-rose-500 focus:ring-0"
                  />
                  <span>
                    <strong>Mark as Disputed:</strong> Historical resolution disagrees with technical telemetry.
                  </span>
                </label>

                <label className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={isVerified}
                    onChange={(e) => setIsVerified(e.target.checked)}
                    className="rounded border-zinc-700 bg-zinc-950 text-emerald-500 focus:ring-0"
                  />
                  <span>
                    <strong>Independently Verified:</strong> This case has been rigorously verified and qualifies for promotion into the verified AI learning knowledge base.
                  </span>
                </label>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={submittingVerdict}
                  className="w-full py-2.5 bg-sky-700 hover:bg-sky-600 disabled:opacity-50 text-white rounded text-xs font-bold transition-colors flex items-center justify-center gap-2"
                >
                  {submittingVerdict ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Recording Verdict...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" /> Finalize &amp; Save Verified Verdict
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
