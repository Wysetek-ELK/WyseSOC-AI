"use client";

import React, { useState, useEffect } from "react";
import {
  History,
  Archive,
  RotateCcw,
  Trash2,
  Eye,
  GitCompare,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Shield,
  RefreshCw,
  X,
  AlertOctagon,
  FileCode,
  Info,
} from "lucide-react";
import {
  api,
  PolicyVersionHistoryItem,
  VersionDeletionPreview,
  PromptVersion,
} from "@/lib/api";

interface ManageVersionHistoryProps {
  ruleId: string;
  ruleName?: string;
  activeVersionId?: string | null;
  versions?: PromptVersion[];
  isAdmin: boolean;
  isViewer: boolean;
  onSelectVersionToView?: (versionId: string) => void;
  onVersionActionCompleted?: () => void;
  onVersionChanged?: () => Promise<void> | void;
  onViewActualPrompt?: (verId?: any) => void;
}

export function ManageVersionHistory({
  ruleId,
  ruleName,
  activeVersionId,
  isAdmin,
  isViewer,
  onSelectVersionToView,
  onVersionActionCompleted,
}: ManageVersionHistoryProps) {
  const [historyItems, setHistoryItems] = useState<PolicyVersionHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<"ALL" | "ACTIVE" | "APPROVED" | "DRAFT" | "ARCHIVED">("ALL");
  const [selectedVersionIds, setSelectedVersionIds] = useState<Record<string, boolean>>({});
  const [feedback, setFeedback] = useState<{ type: "success" | "error" | "warning"; text: string } | null>(null);

  // Modals state
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [deletionPreview, setDeletionPreview] = useState<VersionDeletionPreview | null>(null);
  const [typedConfirmation, setTypedConfirmation] = useState("");
  const [deleteJustification, setDeleteJustification] = useState("Administrative cleanup of obsolete draft");
  const [deleting, setDeleting] = useState(false);

  // Archive modal
  const [archiveModalOpen, setArchiveModalOpen] = useState(false);
  const [archiveTarget, setArchiveTarget] = useState<PolicyVersionHistoryItem | null>(null);
  const [archiveReason, setArchiveReason] = useState("Archived by SOC Administrator");
  const [archiving, setArchiving] = useState(false);

  // Compare modal
  const [compareModalOpen, setCompareModalOpen] = useState(false);
  const [versionA, setVersionA] = useState<PromptVersion | null>(null);
  const [versionB, setVersionB] = useState<PromptVersion | null>(null);
  const [loadingCompare, setLoadingCompare] = useState(false);

  // Bulk cleanup modal
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkConfirmation, setBulkConfirmation] = useState("");
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const fetchHistory = async () => {
    if (!ruleId) return;
    setLoading(true);
    try {
      const items = await api.getRuleVersionHistory(ruleId);
      setHistoryItems(items);
    } catch (err: any) {
      console.error("Failed to load version history:", err);
      setFeedback({ type: "error", text: err?.message || "Failed to load policy version history" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    setSelectedVersionIds({});
  }, [ruleId]);

  const filteredItems = historyItems.filter((item) => {
    if (filterStatus === "ALL") return true;
    if (filterStatus === "ACTIVE") return item.is_active;
    if (filterStatus === "APPROVED") return item.status === "APPROVED";
    if (filterStatus === "DRAFT") return item.status === "DRAFT";
    if (filterStatus === "ARCHIVED") return item.status === "ARCHIVED";
    return true;
  });

  const eligibleForBulk = historyItems.filter((i) => i.is_eligible_for_deletion);
  const selectedEligibleCount = historyItems.filter((i) => selectedVersionIds[i.id] && i.is_eligible_for_deletion).length;
  const selectedProtectedCount = historyItems.filter((i) => selectedVersionIds[i.id] && !i.is_eligible_for_deletion).length;
  const totalSelectedCount = Object.values(selectedVersionIds).filter(Boolean).length;

  const handleOpenDeletePreview = async (item: PolicyVersionHistoryItem) => {
    setPreviewLoading(true);
    setDeletionPreview(null);
    setTypedConfirmation("");
    setPreviewModalOpen(true);
    try {
      const preview = await api.getVersionDeletionPreview(ruleId, item.id);
      setDeletionPreview(preview);
    } catch (err: any) {
      setFeedback({ type: "error", text: err?.message || "Could not generate deletion preview" });
      setPreviewModalOpen(false);
    } finally {
      setPreviewLoading(false);
    }
  };

  const handleExecuteDelete = async () => {
    if (!deletionPreview) return;
    setDeleting(true);
    try {
      await api.deletePromptVersion(ruleId, deletionPreview.version_id, deleteJustification);
      setFeedback({
        type: "success",
        text: `Successfully deleted policy version v${deletionPreview.version_number}. Audit trail recorded.`,
      });
      setPreviewModalOpen(false);
      await fetchHistory();
      onVersionActionCompleted?.();
    } catch (err: any) {
      setFeedback({ type: "error", text: err?.message || "Failed to delete policy version" });
    } finally {
      setDeleting(false);
    }
  };

  const handleOpenArchiveModal = (item: PolicyVersionHistoryItem) => {
    setArchiveTarget(item);
    setArchiveReason(`Archived obsolete draft v${item.version_number}`);
    setArchiveModalOpen(true);
  };

  const handleExecuteArchive = async () => {
    if (!archiveTarget) return;
    setArchiving(true);
    try {
      await api.archivePromptVersion(ruleId, archiveTarget.id, archiveReason);
      setFeedback({
        type: "success",
        text: `Archived version v${archiveTarget.version_number}. It is now hidden from the default selector.`,
      });
      setArchiveModalOpen(false);
      await fetchHistory();
      onVersionActionCompleted?.();
    } catch (err: any) {
      setFeedback({ type: "error", text: err?.message || "Failed to archive version" });
    } finally {
      setArchiving(false);
    }
  };

  const handleExecuteRestore = async (item: PolicyVersionHistoryItem) => {
    try {
      await api.restorePromptVersion(ruleId, item.id);
      setFeedback({
        type: "success",
        text: `Restored version v${item.version_number} to active management queue.`,
      });
      await fetchHistory();
      onVersionActionCompleted?.();
    } catch (err: any) {
      setFeedback({ type: "error", text: err?.message || "Failed to restore version" });
    }
  };

  const handleExecuteBulkDelete = async () => {
    const idsToDelete = Object.keys(selectedVersionIds).filter((id) => selectedVersionIds[id]);
    if (idsToDelete.length === 0) return;
    setBulkDeleting(true);
    try {
      const res = await api.bulkDeletePromptVersions(
        ruleId,
        idsToDelete,
        "Bulk administrator cleanup of obsolete drafts"
      );
      setFeedback({
        type: "success",
        text: `Bulk Cleanup: ${res.deleted_count} obsolete draft(s) deleted. ${res.protected_count} protected version(s) skipped and preserved.`,
      });
      setSelectedVersionIds({});
      setBulkModalOpen(false);
      await fetchHistory();
      onVersionActionCompleted?.();
    } catch (err: any) {
      setFeedback({ type: "error", text: err?.message || "Bulk deletion failed" });
    } finally {
      setBulkDeleting(false);
    }
  };

  const handleOpenCompare = async (item: PolicyVersionHistoryItem) => {
    setLoadingCompare(true);
    setCompareModalOpen(true);
    try {
      const rp = await api.getRulePrompt(ruleId, true);
      const target = rp.versions.find((v) => v.id === item.id) || null;
      // Compare with active version or newest approved
      const baseline =
        rp.versions.find((v) => v.id === rp.active_version_id && v.id !== item.id) ||
        rp.versions.find((v) => v.status === "APPROVED" && v.id !== item.id) ||
        rp.versions.find((v) => v.id !== item.id) ||
        null;
      setVersionA(baseline);
      setVersionB(target);
    } catch (err: any) {
      setFeedback({ type: "error", text: "Failed to load versions for comparison" });
      setCompareModalOpen(false);
    } finally {
      setLoadingCompare(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header & Controls Bar */}
      <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <History className="w-4 h-4 text-cyan-400" />
          <span className="font-bold text-slate-200">Policy Version Governance</span>
          <span className="text-slate-500">•</span>
          <span className="text-slate-400">Total Versions: {historyItems.length}</span>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 p-1 rounded-lg border border-slate-800">
          {(["ALL", "ACTIVE", "APPROVED", "DRAFT", "ARCHIVED"] as const).map((st) => (
            <button
              key={st}
              onClick={() => setFilterStatus(st)}
              className={`px-2.5 py-1 rounded text-[11px] font-semibold transition-colors ${
                filterStatus === st
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={fetchHistory}
            disabled={loading}
            className="p-1.5 rounded-lg border border-slate-700 bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs transition-colors"
            title="Refresh Version History"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>

          {isAdmin && (
            <button
              onClick={() => {
                setBulkConfirmation("");
                setBulkModalOpen(true);
              }}
              disabled={selectedEligibleCount === 0 || isViewer}
              className="px-3 py-1.5 rounded-lg border border-rose-800/60 bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              title={isViewer ? "Read-Only Viewer cannot delete policy versions" : "Bulk cleanup selected eligible obsolete drafts"}
            >
              <Trash2 className="w-3.5 h-3.5 text-rose-400" />
              Bulk Delete ({selectedEligibleCount})
            </button>
          )}
        </div>
      </div>

      {feedback && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between gap-2 ${
            feedback.type === "success"
              ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
              : feedback.type === "warning"
              ? "bg-amber-950/40 border-amber-800 text-amber-300"
              : "bg-rose-950/40 border-rose-800 text-rose-300"
          }`}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-slate-200">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
        <table className="w-full text-left text-xs text-slate-300 border-collapse">
          <thead>
            <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 text-[11px] font-semibold uppercase tracking-wider">
              {isAdmin && (
                <th className="py-2.5 px-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={
                      eligibleForBulk.length > 0 &&
                      eligibleForBulk.every((i) => selectedVersionIds[i.id])
                    }
                    onChange={(e) => {
                      const checked = e.target.checked;
                      const next: Record<string, boolean> = {};
                      eligibleForBulk.forEach((i) => {
                        next[i.id] = checked;
                      });
                      setSelectedVersionIds(next);
                    }}
                    className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                    title="Select all eligible drafts for cleanup"
                  />
                </th>
              )}
              <th className="py-2.5 px-3">Version</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">Created</th>
              <th className="py-2.5 px-3">Usage</th>
              <th className="py-2.5 px-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {loading ? (
              <tr>
                <td colSpan={isAdmin ? 6 : 5} className="py-8 text-center text-slate-500">
                  <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-cyan-400" />
                  Loading authoritative version records from PostgreSQL...
                </td>
              </tr>
            ) : filteredItems.length === 0 ? (
              <tr>
                <td colSpan={isAdmin ? 6 : 5} className="py-6 text-center text-slate-500 text-xs">
                  No policy versions found matching filter '{filterStatus}'.
                </td>
              </tr>
            ) : (
              filteredItems.map((item) => {
                const isSelected = Boolean(selectedVersionIds[item.id]);
                return (
                  <tr
                    key={item.id}
                    className={`hover:bg-slate-900/50 transition-colors ${
                      item.is_active ? "bg-cyan-950/15" : ""
                    }`}
                  >
                    {isAdmin && (
                      <td className="py-2 px-3 text-center">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          disabled={!item.is_eligible_for_deletion}
                          onChange={(e) => {
                            setSelectedVersionIds((prev) => ({
                              ...prev,
                              [item.id]: e.target.checked,
                            }));
                          }}
                          className={`rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0 ${
                            !item.is_eligible_for_deletion ? "opacity-30 cursor-not-allowed" : ""
                          }`}
                          title={
                            item.is_eligible_for_deletion
                              ? "Select for bulk cleanup"
                              : "Protected: cannot be bulk deleted"
                          }
                        />
                      </td>
                    )}
                    <td className="py-2 px-3 font-bold text-slate-200">
                      <div className="flex items-center gap-1.5">
                        <span className="text-cyan-300">v{item.version_number}</span>
                        {item.is_active && (
                          <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 font-sans font-bold">
                            ACTIVE
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-sans font-bold border ${
                            item.status === "APPROVED"
                              ? "bg-emerald-950/50 text-emerald-300 border-emerald-700/60"
                              : item.status === "DRAFT"
                              ? "bg-amber-950/50 text-amber-300 border-amber-700/60"
                              : item.status === "ARCHIVED"
                              ? "bg-slate-900 text-slate-400 border-slate-700"
                              : "bg-rose-950/50 text-rose-300 border-rose-700/60"
                          }`}
                        >
                          {item.status}
                        </span>
                        {item.quality_score !== null && item.quality_score !== undefined && (
                          <span
                            className={`text-[10px] font-sans font-semibold px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 ${
                              item.quality_score >= 80
                                ? "text-emerald-400"
                                : item.quality_score >= 65
                                ? "text-amber-400"
                                : "text-rose-400"
                            }`}
                            title={`Quality Score: ${item.quality_score.toFixed(0)}/100`}
                          >
                            {item.quality_score.toFixed(0)}/100
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-2 px-3 text-slate-400 text-xs font-sans">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 px-3 font-sans">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`text-xs ${
                            item.is_active
                              ? "text-emerald-400 font-semibold"
                              : item.status === "APPROVED"
                              ? "text-blue-300"
                              : item.is_eligible_for_deletion
                              ? "text-slate-400"
                              : "text-amber-300"
                          }`}
                        >
                          {item.usage_label}
                        </span>
                      </div>
                    </td>
                    <td className="py-2 px-3 text-right font-sans">
                      <div className="inline-flex items-center gap-1">
                        <button
                          onClick={() => onSelectVersionToView?.(item.id)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold inline-flex items-center gap-1 transition-colors"
                          title="View version in editor"
                        >
                          <Eye className="w-3 h-3 text-cyan-400" />
                          View
                        </button>

                        <button
                          onClick={() => handleOpenCompare(item)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold inline-flex items-center gap-1 transition-colors"
                          title="Compare with baseline"
                        >
                          <GitCompare className="w-3 h-3 text-sky-400" />
                          Diff
                        </button>

                        {/* Archive / Restore actions */}
                        {isAdmin && item.status !== "ARCHIVED" && (
                          <button
                            onClick={() => handleOpenArchiveModal(item)}
                            disabled={item.is_active || isViewer}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold inline-flex items-center gap-1 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            title={
                              isViewer
                                ? "Read-Only Viewer cannot archive policy versions"
                                : item.is_active
                                ? "Active policy cannot be archived"
                                : "Archive version (hide from normal selector)"
                            }
                          >
                            <Archive className="w-3 h-3 text-amber-400" />
                            Archive
                          </button>
                        )}

                        {isAdmin && item.status === "ARCHIVED" && (
                          <button
                            onClick={() => handleExecuteRestore(item)}
                            disabled={isViewer}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-emerald-300 text-[11px] font-semibold inline-flex items-center gap-1 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            title={
                              isViewer
                                ? "Read-Only Viewer cannot restore policy versions"
                                : "Restore archived version"
                            }
                          >
                            <RotateCcw className="w-3 h-3 text-emerald-400" />
                            Restore
                          </button>
                        )}

                        {/* Delete action */}
                        {isAdmin && (
                          <button
                            onClick={() => handleOpenDeletePreview(item)}
                            disabled={!item.is_eligible_for_deletion || isViewer}
                            className="px-2 py-1 rounded bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 text-[11px] font-semibold inline-flex items-center gap-1 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            title={
                              isViewer
                                ? "Read-Only Viewer cannot delete policy versions"
                                : item.is_eligible_for_deletion
                                ? "Permanently delete eligible draft"
                                : item.is_active
                                ? "Deletion unavailable — active policy version"
                                : item.status === "APPROVED" || (item.usage_label && item.usage_label.toLowerCase().includes("approved"))
                                ? "Deletion unavailable — historical approved policy"
                                : (item.dependency_counts && (
                                    (item.dependency_counts.actual_prompt_captures || 0) > 0 ||
                                    (item.dependency_counts.pilot_verdicts || 0) > 0 ||
                                    (item.dependency_counts.historical_evaluation_runs || 0) > 0 ||
                                    (item.dependency_counts.dry_run_configs || 0) > 0
                                  ))
                                ? "Deletion unavailable — referenced by inference history"
                                : "Protected from deletion: " + (item.blocking_reasons?.length ? item.blocking_reasons.join(", ") : "Referenced or approved")
                            }
                          >
                            <Trash2 className="w-3 h-3 text-rose-400" />
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* MODAL 1: Deletion Impact Preview Modal */}
      {previewModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <AlertOctagon className="w-5 h-5 text-rose-400" />
                <h3 className="font-bold text-slate-100 text-sm">Safe Deletion Impact Preview</h3>
              </div>
              <button
                onClick={() => setPreviewModalOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {previewLoading ? (
              <div className="py-8 text-center text-slate-400">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
                Validating foreign key relationships and inference provenance...
              </div>
            ) : deletionPreview ? (
              <div className="space-y-3">
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/80 space-y-1.5 font-mono">
                  <div className="flex justify-between">
                    <span className="text-slate-400 font-sans">Target Rule:</span>
                    <span className="text-cyan-300">{deletionPreview.rule_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 font-sans">Policy Version:</span>
                    <span className="text-slate-200 font-bold">v{deletionPreview.version_number} ({deletionPreview.status})</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 font-sans">Deletion Reversible:</span>
                    <span className="text-rose-400 font-bold font-sans">NO (IRREVERSIBLE)</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400 font-sans">Records Affected:</span>
                    <span className="text-amber-300">{deletionPreview.records_affected} record(s)</span>
                  </div>
                </div>

                {/* Eligibility banner */}
                {deletionPreview.is_eligible ? (
                  <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/60 text-emerald-300 text-xs flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold">Eligible for Permanent Deletion</p>
                      <p className="text-[11px] text-emerald-400/90 mt-0.5">
                        This version is an unreferenced draft with no protected dependencies. It has never been deployed to active production or cited in verified inference.
                      </p>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800 text-rose-300 text-xs flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-bold">Permanent Deletion Strictly Prohibited</p>
                      <ul className="list-disc pl-4 mt-1 text-[11px] space-y-1 text-rose-300/90">
                        {deletionPreview.blocking_reasons.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )}

                {deletionPreview.is_eligible && (
                  <div className="space-y-3 pt-2">
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">
                        Administrative Justification:
                      </label>
                      <input
                        type="text"
                        value={deleteJustification}
                        onChange={(e) => setDeleteJustification(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500"
                        placeholder="Reason for deletion..."
                      />
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1">
                        Typed Confirmation:
                      </label>
                      <p className="text-[11px] text-slate-400 mb-1">
                        Type <code className="px-1.5 py-0.5 rounded bg-slate-800 text-rose-300 font-bold">DELETE v{deletionPreview.version_number}</code> to confirm:
                      </p>
                      <input
                        type="text"
                        value={typedConfirmation}
                        onChange={(e) => setTypedConfirmation(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs focus:ring-1 focus:ring-rose-500 font-mono"
                        placeholder={`DELETE v${deletionPreview.version_number}`}
                      />
                    </div>

                    <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                      <button
                        onClick={() => setPreviewModalOpen(false)}
                        className="px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs font-semibold"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleExecuteDelete}
                        disabled={
                          deleting ||
                          typedConfirmation.trim() !== `DELETE v${deletionPreview.version_number}`
                        }
                        className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        {deleting ? "Deleting..." : "Permanently Delete Version"}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* MODAL 2: Archive Modal */}
      {archiveModalOpen && archiveTarget && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-5 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Archive className="w-4 h-4 text-amber-400" />
                <h3 className="font-bold text-slate-100 text-sm">
                  Archive Policy Version v{archiveTarget.version_number}
                </h3>
              </div>
              <button
                onClick={() => setArchiveModalOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <p className="text-slate-300">
                Archiving hides this version from the default version selector while preserving its historical integrity and audit records. You can restore it at any time.
              </p>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Reason for Archiving:
                </label>
                <textarea
                  rows={3}
                  value={archiveReason}
                  onChange={(e) => setArchiveReason(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs focus:ring-1 focus:ring-amber-500"
                  placeholder="Justification for archiving this version..."
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  onClick={() => setArchiveModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExecuteArchive}
                  disabled={archiving || !archiveReason.trim()}
                  className="px-3.5 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-colors disabled:opacity-40 flex items-center gap-1.5"
                >
                  <Archive className="w-3.5 h-3.5" />
                  {archiving ? "Archiving..." : "Archive Version"}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 3: Bulk Delete Modal */}
      {bulkModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-5 space-y-4 shadow-2xl text-xs">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Trash2 className="w-5 h-5 text-rose-400" />
                <h3 className="font-bold text-slate-100 text-sm">Bulk Cleanup Confirmation</h3>
              </div>
              <button
                onClick={() => setBulkModalOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Total Selected:</span>
                  <span className="text-slate-200 font-bold">{totalSelectedCount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Eligible for Deletion:</span>
                  <span className="text-emerald-400 font-bold">{selectedEligibleCount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Protected (Skipped):</span>
                  <span className="text-amber-400 font-bold">{selectedProtectedCount}</span>
                </div>
              </div>

              <p className="text-slate-300">
                Only the <strong className="text-emerald-400">{selectedEligibleCount} unreferenced draft(s)</strong> will be deleted. Any active or protected versions will be automatically preserved.
              </p>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">
                  Type <code className="px-1.5 py-0.5 rounded bg-slate-800 text-rose-300 font-bold">PERMANENTLY DELETE</code> to confirm:
                </label>
                <input
                  type="text"
                  value={bulkConfirmation}
                  onChange={(e) => setBulkConfirmation(e.target.value)}
                  className="w-full px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs focus:ring-1 focus:ring-rose-500 font-mono"
                  placeholder="PERMANENTLY DELETE"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  onClick={() => setBulkModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExecuteBulkDelete}
                  disabled={bulkDeleting || bulkConfirmation.trim() !== "PERMANENTLY DELETE"}
                  className="px-3.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-colors disabled:opacity-40 flex items-center gap-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  {bulkDeleting ? "Cleaning up..." : `Clean Up ${selectedEligibleCount} Draft(s)`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 4: Version Comparison Modal */}
      {compareModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-4xl w-full p-5 space-y-4 shadow-2xl text-xs max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <GitCompare className="w-4 h-4 text-sky-400" />
                <h3 className="font-bold text-slate-100 text-sm">
                  Compare Policy Versions {versionA ? `v${versionA.version_number}` : ""} vs {versionB ? `v${versionB.version_number}` : ""}
                </h3>
              </div>
              <button
                onClick={() => setCompareModalOpen(false)}
                className="text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {loadingCompare ? (
              <div className="py-12 text-center text-slate-400">
                <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-cyan-400" />
                Loading version specifications...
              </div>
            ) : versionA && versionB ? (
              <div className="overflow-y-auto space-y-4 flex-1 pr-1 font-mono text-[11px]">
                <div className="grid grid-cols-2 gap-3 sticky top-0 bg-slate-900 pb-2 z-10 border-b border-slate-800">
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <span className="font-bold text-cyan-300">Baseline v{versionA.version_number}</span>{" "}
                    <span className="text-slate-500">({versionA.status})</span>
                  </div>
                  <div className="p-2 rounded bg-slate-950 border border-slate-800">
                    <span className="font-bold text-amber-300">Target v{versionB.version_number}</span>{" "}
                    <span className="text-slate-500">({versionB.status})</span>
                  </div>
                </div>

                {([
                  ["Rule Specific Guidance", "rule_specific_prompt"],
                  ["True Positive Indicators", "tp_indicators"],
                  ["False Positive Indicators", "fp_indicators"],
                  ["Detection Conditions", "detection_conditions"],
                  ["Required Evidence", "required_evidence"],
                  ["Missing Info Criteria", "missing_info_criteria"],
                  ["Escalation Conditions", "escalation_conditions"],
                ] as const).map(([label, key]) => {
                  const valA = (versionA as any)[key] || "";
                  const valB = (versionB as any)[key] || "";
                  const isDiff = valA.trim() !== valB.trim();
                  return (
                    <div key={key} className="space-y-1">
                      <div className="flex items-center justify-between text-slate-400 font-sans font-semibold">
                        <span>{label}</span>
                        {isDiff ? (
                          <span className="text-amber-400 text-[10px] bg-amber-950/60 px-1.5 py-0.2 rounded border border-amber-800/60">
                            MODIFIED
                          </span>
                        ) : (
                          <span className="text-slate-500 text-[10px]">UNCHANGED</span>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <pre className="p-2.5 rounded bg-slate-950/90 border border-slate-800/80 text-slate-300 whitespace-pre-wrap max-h-48 overflow-y-auto">
                          {valA || "<Empty>"}
                        </pre>
                        <pre
                          className={`p-2.5 rounded whitespace-pre-wrap max-h-48 overflow-y-auto border ${
                            isDiff
                              ? "bg-amber-950/20 border-amber-800/50 text-amber-200"
                              : "bg-slate-950/90 border-slate-800/80 text-slate-300"
                          }`}
                        >
                          {valB || "<Empty>"}
                        </pre>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="py-8 text-center text-slate-500">
                Insufficient versions available for comparison.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
