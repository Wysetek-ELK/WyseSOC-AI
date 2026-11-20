"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  Activity,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  EyeOff,
  Eye,
  Send,
  Lock,
  Radio,
  FileCheck2,
  RefreshCw,
  FileText,
  Sliders,
  Database,
  ChevronRight,
  Sparkles,
  FileCode,
  Search,
  Filter,
  History,
  X,
  ExternalLink,
  Play,
  Clock,
  Cpu,
} from "lucide-react";
import {
  api,
  formatApiErrorMessage,
  AisEvaluationItem,
  AisEvaluationSummary,
  AisEvaluationHistoryItem,
} from "@/lib/api";

interface ReviewIncidentsWorkbenchProps {
  ruleId: string;
  ruleName?: string;
  customer?: string;
  isViewer?: boolean;
  isAdmin?: boolean;
  selectedVersionId?: string;
  learningProfile?: any;
  onReviewSubmitted?: () => void;
  onOpenActualPrompt?: (incidentId: string) => void;
  onNavigateToTest?: (incidentId?: string) => void;
}

export function ReviewIncidentsWorkbench({
  ruleId,
  ruleName,
  customer = "DEFAULT",
  isViewer = false,
  isAdmin = true,
  selectedVersionId,
  learningProfile: propLearningProfile,
  onReviewSubmitted,
  onOpenActualPrompt,
  onNavigateToTest,
}: ReviewIncidentsWorkbenchProps) {
  // Mode toggle: "queue" (analyst review) vs "tracking" (admin evaluation tracking table)
  const [activeViewMode, setActiveViewMode] = useState<"queue" | "tracking">("queue");

  // Queue state
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState<{
    pending: number;
    reviewed: number;
    verifiedGt: number;
  }>({
    pending: 0,
    reviewed: propLearningProfile?.total_analyst_reviews ?? 0,
    verifiedGt: (propLearningProfile?.verified_tp_count ?? 0) + (propLearningProfile?.verified_fp_count ?? 0),
  });

  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);
  const [incidentDetail, setIncidentDetail] = useState<any | null>(null);
  const [normalizedEvidence, setNormalizedEvidence] = useState<any[]>([]);
  const [rawLogs, setRawLogs] = useState<string>("");
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Review submission state
  const [analystVerdict, setAnalystVerdict] = useState<"TRUE_POSITIVE" | "FALSE_POSITIVE" | "INSUFFICIENT_EVIDENCE">("FALSE_POSITIVE");
  const [analystNotes, setAnalystNotes] = useState("");
  const [evidenceRefs, setEvidenceRefs] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);
  const [revealedResult, setRevealedResult] = useState<any | null>(null);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Administrative Tracking Table state
  const [trackingData, setTrackingData] = useState<{
    summary: AisEvaluationSummary | null;
    items: AisEvaluationItem[];
    total: number;
  }>({
    summary: null,
    items: [],
    total: 0,
  });
  const [loadingTracking, setLoadingTracking] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Modals state
  const [selectedEvaluationDetail, setSelectedEvaluationDetail] = useState<AisEvaluationItem | null>(null);
  const [historyModalIncidentId, setHistoryModalIncidentId] = useState<string | null>(null);
  const [historyItems, setHistoryItems] = useState<AisEvaluationHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fetchIncidents = async () => {
    if (!ruleId) return;
    setLoading(true);
    try {
      const [reviewData, profileData] = await Promise.all([
        api.getPendingDoubleBlindReviews(ruleId, 50, 0).catch(() => ({ items: [], total: 0 })),
        api.getRuleLearningProfileDetail(ruleId, customer).catch(() => null),
      ]);

      const items = reviewData.items || [];
      const effectiveProfile = profileData || propLearningProfile;
      setIncidents(items);
      setCounts({
        pending: reviewData.total ?? items.length,
        reviewed: effectiveProfile?.total_analyst_reviews ?? 0,
        verifiedGt: (effectiveProfile?.verified_tp_count ?? 0) + (effectiveProfile?.verified_fp_count ?? 0),
      });

      if (items.length > 0) {
        setSelectedIncident((prev: any) => prev || items[0]);
      }
    } catch (err: any) {
      console.error("Failed to load review queue:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchTrackingData = async () => {
    if (!ruleId) return;
    setLoadingTracking(true);
    try {
      const res = await api.getRuleEvaluationStatus(ruleId, {
        policy_version_id: selectedVersionId,
        customer,
        status: statusFilter !== "ALL" ? statusFilter : undefined,
        search: searchQuery || undefined,
        page: 1,
        page_size: 100,
      });
      setTrackingData({
        summary: res.summary,
        items: res.items || [],
        total: res.total || 0,
      });
    } catch (err: any) {
      console.error("Failed to load evaluation tracking data:", err);
    } finally {
      setLoadingTracking(false);
    }
  };

  useEffect(() => {
    setSelectedIncident(null);
    setRevealedResult(null);
    fetchIncidents();
    if (activeViewMode === "tracking") {
      fetchTrackingData();
    }
  }, [ruleId, selectedVersionId]);

  useEffect(() => {
    if (activeViewMode === "tracking") {
      fetchTrackingData();
    }
  }, [activeViewMode, statusFilter, selectedVersionId]);

  // Synchronize counts whenever parent passes updated learning profile
  useEffect(() => {
    if (propLearningProfile) {
      setCounts((prev) => ({
        ...prev,
        reviewed: propLearningProfile.total_analyst_reviews ?? prev.reviewed,
        verifiedGt:
          (propLearningProfile.verified_tp_count ?? 0) +
          (propLearningProfile.verified_fp_count ?? 0),
      }));
    }
  }, [propLearningProfile]);

  // Load detailed incident evidence and raw logs whenever selected incident changes
  useEffect(() => {
    if (!selectedIncident?.incident_id) {
      setIncidentDetail(null);
      setNormalizedEvidence([]);
      setRawLogs("");
      return;
    }

    let isMounted = true;
    setLoadingDetail(true);
    setRevealedResult(null);
    setFeedback(null);
    setAnalystNotes("");
    setEvidenceRefs("");

    Promise.allSettled([
      api.getIncidentDetail(String(selectedIncident.incident_id), true),
      api.getIncidentModelPayload(String(selectedIncident.incident_id)),
    ])
      .then(([incRes, payloadRes]) => {
        if (!isMounted) return;

        if (incRes.status === "fulfilled") {
          setIncidentDetail(incRes.value);
          const raw =
            incRes.value?.events?.[0]?.raw_log ||
            (incRes.value?.raw_payload ? JSON.stringify(incRes.value.raw_payload, null, 2) : "");
          setRawLogs(raw);
        }

        if (payloadRes.status === "fulfilled") {
          const mp = payloadRes.value;
          setNormalizedEvidence(Array.isArray(mp?.canonical_evidence) ? mp.canonical_evidence : []);
          if (!rawLogs && mp?.raw_log) {
            setRawLogs(mp.raw_log);
          }
        }
      })
      .finally(() => {
        if (isMounted) setLoadingDetail(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedIncident?.incident_id]);

  const handleSubmitReview = async () => {
    if (!selectedIncident) return;
    setSubmittingReview(true);
    setFeedback(null);
    setRevealedResult(null);

    try {
      const payload = {
        analyst_verdict: analystVerdict,
        analyst_notes: analystNotes || "",
        evidence_references: evidenceRefs ? evidenceRefs.split(",").map((s) => s.trim()).filter(Boolean) : [],
        blind_mode_active: true,
      };

      const result = await api.submitAnalystReview(selectedIncident.incident_id, payload);
      setRevealedResult(result);
      setFeedback({
        type: "success",
        text: `Review recorded. AI Comparison: ${result.comparison_outcome || "VERIFIED"}.`,
      });
      onReviewSubmitted?.();
      await fetchIncidents();
      if (activeViewMode === "tracking") {
        await fetchTrackingData();
      }
    } catch (err: any) {
      setFeedback({
        type: "error",
        text: formatApiErrorMessage(err, "Failed to submit analyst review"),
      });
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleNextIncident = () => {
    if (!incidents.length) return;
    const currentIndex = incidents.findIndex((i) => i.incident_id === selectedIncident?.incident_id);
    const nextItem = incidents[currentIndex + 1] || incidents[0];
    setSelectedIncident(nextItem);
    setRevealedResult(null);
  };

  const openHistoryModal = async (incidentId: string) => {
    setHistoryModalIncidentId(incidentId);
    setLoadingHistory(true);
    setHistoryItems([]);
    try {
      const res = await api.getIncidentEvaluationHistory(incidentId);
      setHistoryItems(res.history || []);
    } catch (err) {
      console.error("Failed to load evaluation history:", err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const renderBadge = (status: string, display: string, color: string) => {
    let colorClasses = "bg-slate-800 text-slate-300 border-slate-700";
    if (color === "green") colorClasses = "bg-emerald-950/80 text-emerald-300 border-emerald-800";
    else if (color === "amber") colorClasses = "bg-amber-950/80 text-amber-300 border-amber-800";
    else if (color === "red") colorClasses = "bg-rose-950/80 text-rose-300 border-rose-800";
    else if (color === "blue") colorClasses = "bg-sky-950/80 text-sky-300 border-sky-800";

    return (
      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border ${colorClasses}`}>
        {display || status}
      </span>
    );
  };

  return (
    <div id="incident-review-workbench" className="space-y-4 scroll-mt-6 transition-all duration-300">
      {/* Top Header Bar with Mode Toggle & Stats */}
      <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/70 flex flex-wrap items-center justify-between gap-3 text-xs">
        {/* Left: View Mode Segmented Switch */}
        <div className="flex items-center gap-1.5 p-1 rounded-lg bg-slate-900 border border-slate-800">
          <button
            onClick={() => setActiveViewMode("queue")}
            className={`px-3 py-1 rounded-md font-semibold text-xs transition-colors flex items-center gap-1.5 ${
              activeViewMode === "queue"
                ? "bg-cyan-600 text-slate-950 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            Double-Blind Review Queue
          </button>

          <button
            onClick={() => setActiveViewMode("tracking")}
            className={`px-3 py-1 rounded-md font-semibold text-xs transition-colors flex items-center gap-1.5 ${
              activeViewMode === "tracking"
                ? "bg-cyan-600 text-slate-950 shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            AI Evaluation Tracking (Admin)
          </button>
        </div>

        {/* Center/Right: Counts & Blind Indicator */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3 text-slate-300">
            <span className="text-slate-400">Pending:</span>
            <span className="font-bold text-cyan-300 font-mono">{counts.pending}</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">Reviewed:</span>
            <span className="font-bold text-slate-200 font-mono">{counts.reviewed}</span>
            <span className="text-slate-600">|</span>
            <span className="text-slate-400">Verified GT:</span>
            <span className="font-bold text-emerald-400 font-mono">{counts.verifiedGt}</span>
          </div>

          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-950/40 border border-indigo-800/60 text-indigo-300 text-[11px] font-semibold">
            <EyeOff className="w-3.5 h-3.5 text-indigo-400" />
            <span>Double-Blind Active (AI Determination Masked)</span>
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

      {/* VIEW MODE 1: Standard Double-Blind Analyst Review Queue */}
      {activeViewMode === "queue" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start">
          {/* LEFT PANEL: Compact Incident Queue (5 cols on lg) */}
          <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden flex flex-col max-h-[750px]">
            <div className="p-3 border-b border-slate-800 bg-slate-950/60 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan-400" />
                <span className="font-bold text-slate-200 text-xs">Incident Review Queue</span>
              </div>
              <button
                onClick={fetchIncidents}
                disabled={loading}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
                title="Refresh Queue"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>

            <div className="overflow-y-auto divide-y divide-slate-800/60 flex-1">
              {loading ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-cyan-400" />
                  Loading pending incidents...
                </div>
              ) : incidents.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs p-4">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto mb-2 opacity-60" />
                  No unreviewed incidents pending for this rule.
                </div>
              ) : (
                incidents.map((inc) => {
                  const isSelected = selectedIncident?.incident_id === inc.incident_id;
                  return (
                    <div
                      key={inc.incident_id}
                      onClick={() => setSelectedIncident(inc)}
                      className={`p-3 cursor-pointer transition-colors text-xs ${
                        isSelected
                          ? "bg-cyan-950/30 border-l-4 border-cyan-400"
                          : "hover:bg-slate-900/80 border-l-4 border-transparent"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono font-bold text-slate-200">
                          #{inc.incident_id}
                        </span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                            inc.severity === "CRITICAL"
                              ? "bg-rose-950 text-rose-300 border border-rose-800"
                              : inc.severity === "HIGH"
                              ? "bg-amber-950 text-amber-300 border border-amber-800"
                              : "bg-blue-950 text-blue-300 border border-blue-800"
                          }`}
                        >
                          {inc.severity || "MEDIUM"}
                        </span>
                      </div>

                      <p className="text-slate-300 text-[11px] truncate mb-1.5 font-medium">
                        {inc.title || inc.event_type}
                      </p>

                      <div className="flex items-center justify-between text-[10px] text-slate-400">
                        <span>Source: {inc.source_ip || "Internal"}</span>
                        <span className="text-slate-500">
                          {inc.created_at ? new Date(inc.created_at).toLocaleTimeString() : ""}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* RIGHT PANEL: Review & Evidence Investigation Workspace (7 cols on lg) */}
          <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-slate-900/60 p-4 space-y-4">
            {selectedIncident ? (
              <>
                {/* Incident Header */}
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-950/80 flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-sm text-cyan-300">
                        Incident #{selectedIncident.incident_id}
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300">
                        {selectedIncident.event_type}
                      </span>
                    </div>
                    <p className="text-slate-400 text-xs mt-1">
                      {incidentDetail?.title || selectedIncident.title}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleNextIncident}
                      className="px-2.5 py-1 rounded bg-sky-950 hover:bg-sky-900 text-sky-300 border border-sky-800 text-xs font-semibold flex items-center gap-1 transition-colors"
                    >
                      Next Incident
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                {/* Normalized Evidence Summary Table */}
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-slate-300 font-semibold">
                    <span className="flex items-center gap-1.5">
                      <Database className="w-3.5 h-3.5 text-cyan-400" />
                      Normalized Evidence Artifacts
                    </span>
                    <span className="text-[11px] text-slate-500">
                      {normalizedEvidence.length} attribute(s) mapped
                    </span>
                  </div>

                  {loadingDetail ? (
                    <div className="py-6 text-center text-slate-500 text-xs">
                      <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-cyan-400" />
                      Extracting normalized evidence...
                    </div>
                  ) : normalizedEvidence.length > 0 ? (
                    <div className="max-h-48 overflow-y-auto rounded-lg border border-slate-800 bg-slate-950">
                      <table className="w-full text-left text-[11px] font-mono">
                        <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
                          <tr>
                            <th className="py-1 px-2.5">Field</th>
                            <th className="py-1 px-2.5">Value</th>
                            <th className="py-1 px-2.5">EV-ID</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800/60">
                          {normalizedEvidence.map((ev, idx) => (
                            <tr key={idx} className="hover:bg-slate-900/40">
                              <td className="py-1 px-2.5 text-cyan-400 font-semibold">{ev.field}</td>
                              <td className="py-1 px-2.5 text-slate-200 truncate max-w-xs">{String(ev.value ?? "-")}</td>
                              <td className="py-1 px-2.5 text-slate-500 font-bold">{ev.evidence_id || `EV-${idx + 1}`}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 text-slate-400 text-xs">
                      Standard normalized fields: Source IP: {selectedIncident.source_ip || "-"}, Device: {selectedIncident.reporting_device || "-"}
                    </div>
                  )}
                </div>

                {/* Raw Logs Section */}
                <div className="space-y-1.5">
                  <span className="text-xs text-slate-300 font-semibold flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-slate-400" />
                    Original Raw Logs
                  </span>
                  <pre className="p-2.5 rounded-lg border border-slate-800 bg-slate-950 text-[11px] font-mono text-slate-300 max-h-36 overflow-y-auto whitespace-pre-wrap">
                    {rawLogs || "Raw log payload not available."}
                  </pre>
                </div>

                {/* Double-Blind Determination Form */}
                <div id="analyst-determination-form" className="p-3.5 rounded-xl border border-indigo-950/80 bg-indigo-950/20 space-y-3 scroll-mt-6 transition-all duration-300">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200 text-xs flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      Analyst Independent Determination
                    </span>
                    <span className="text-[11px] text-indigo-300 font-mono">
                      Mode: DOUBLE-BLIND
                    </span>
                  </div>

                  {/* Radio Selector */}
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setAnalystVerdict("TRUE_POSITIVE")}
                      className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center gap-1 transition-colors ${
                        analystVerdict === "TRUE_POSITIVE"
                          ? "bg-rose-950/80 border-rose-500 text-rose-200 ring-1 ring-rose-500"
                          : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <span>True Positive (TP)</span>
                      <span className="text-[10px] font-normal text-slate-400">Confirmed Malicious</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setAnalystVerdict("FALSE_POSITIVE")}
                      className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center gap-1 transition-colors ${
                        analystVerdict === "FALSE_POSITIVE"
                          ? "bg-emerald-950/80 border-emerald-500 text-emerald-200 ring-1 ring-emerald-500"
                          : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <span>False Positive (FP)</span>
                      <span className="text-[10px] font-normal text-slate-400">Benign Noise</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setAnalystVerdict("INSUFFICIENT_EVIDENCE")}
                      className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center gap-1 transition-colors ${
                        analystVerdict === "INSUFFICIENT_EVIDENCE"
                          ? "bg-amber-950/80 border-amber-500 text-amber-200 ring-1 ring-amber-500"
                          : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      <span>Insufficient Evidence</span>
                      <span className="text-[10px] font-normal text-slate-400">Requires Information</span>
                    </button>
                  </div>

                  {/* Notes & Evidence references */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
                    <div>
                      <label className="block text-slate-300 font-semibold mb-1 text-[11px]">
                        Investigation Notes / Rationale:
                      </label>
                      <textarea
                        rows={2}
                        value={analystNotes}
                        onChange={(e) => setAnalystNotes(e.target.value)}
                        placeholder="Explain investigative findings..."
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500"
                      />
                    </div>

                    <div>
                      <label className="block text-slate-300 font-semibold mb-1 text-[11px]">
                        Evidence Citations (comma-separated):
                      </label>
                      <input
                        type="text"
                        value={evidenceRefs}
                        onChange={(e) => setEvidenceRefs(e.target.value)}
                        placeholder="e.g. EV-01, EV-03, DestinationPort:80"
                        className="w-full px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-950 text-slate-200 text-xs focus:ring-1 focus:ring-cyan-500 font-mono"
                      />
                    </div>
                  </div>

                  {/* Submit Action */}
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[11px] text-slate-500">
                      AI determination will be revealed immediately following submission.
                    </span>
                    <button
                      onClick={handleSubmitReview}
                      disabled={submittingReview || isViewer}
                      className="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors disabled:opacity-40"
                    >
                      <Send className="w-3.5 h-3.5" />
                      {submittingReview ? "Recording Review..." : "Submit Review"}
                    </button>
                  </div>
                </div>

                {/* POST-SUBMISSION: Revealed AI Comparison */}
                {revealedResult && (
                  <div className="p-3.5 rounded-xl border border-cyan-800/80 bg-cyan-950/20 space-y-2.5 animate-fadeIn text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-cyan-300 flex items-center gap-1.5">
                        <Sparkles className="w-4 h-4 text-cyan-400" />
                        Post-Submission AI Determination Comparison
                      </span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-900/60 text-cyan-200 font-mono">
                        {revealedResult.comparison_outcome || "COMPARISON COMPLETE"}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-3 font-mono">
                      <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
                        <span className="text-slate-400 font-sans block text-[11px]">Your Determination:</span>
                        <span className="font-bold text-slate-100 text-sm">
                          {revealedResult.analyst_verdict || analystVerdict}
                        </span>
                      </div>

                      <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
                        <span className="text-slate-400 font-sans block text-[11px]">AI Model Determination:</span>
                        <span className="font-bold text-cyan-300 text-sm">
                          {revealedResult.revealed_ai_verdict || "AI Evaluation Not Available"}
                        </span>
                        {revealedResult.effective_verdict && revealedResult.effective_verdict !== revealedResult.revealed_ai_verdict && (
                          <span className="block text-[10px] text-amber-400 font-sans mt-0.5">
                            Governed: {revealedResult.effective_verdict}
                          </span>
                        )}
                        {revealedResult.policy_version && (
                          <span className="block text-[10px] text-slate-500 font-sans mt-0.5">
                            Policy Version: v{revealedResult.policy_version}
                          </span>
                        )}
                      </div>
                    </div>

                    {revealedResult.disagreement_reason && (
                      <div className="p-2 rounded bg-amber-950/30 border border-amber-800/60 text-amber-200 text-[11px]">
                        <span className="font-semibold block mb-0.5">Outcome Rationale:</span>
                        {revealedResult.disagreement_reason}
                      </div>
                    )}

                    {revealedResult.revealed_ai_rationale && (
                      <div className="p-2 rounded bg-slate-950 border border-slate-800 text-slate-300 text-[11px]">
                        <span className="font-semibold text-slate-400 block mb-0.5">Model Reasoning:</span>
                        <p className="line-clamp-3">{revealedResult.revealed_ai_rationale}</p>
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-1">
                      {onOpenActualPrompt && (
                        <button
                          onClick={() => onOpenActualPrompt(String(selectedIncident.incident_id))}
                          className="px-2.5 py-1.5 rounded bg-slate-900 hover:bg-slate-800 text-cyan-400 border border-slate-800 font-semibold text-xs flex items-center gap-1.5 transition-colors"
                        >
                          <FileCode className="w-3.5 h-3.5" />
                          Inspect LLM Prompt Capture
                        </button>
                      )}
                      <button
                        onClick={handleNextIncident}
                        className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center gap-1 transition-colors ml-auto"
                      >
                        Continue to Next Incident
                        <ArrowRight className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="py-24 text-center text-slate-500 text-xs">
                Select an incident from the queue to inspect normalized evidence, review raw logs, and record an independent determination.
              </div>
            )}
          </div>
        </div>
      )}

      {/* VIEW MODE 2: Compact Incident-Level AI Evaluation Tracking Table (Admin) */}
      {activeViewMode === "tracking" && (
        <div className="space-y-3">
          {/* Controls & Filter Bar */}
          <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400 font-semibold">Status Filter:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-2.5 py-1 rounded bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono focus:ring-1 focus:ring-cyan-500"
              >
                <option value="ALL">All Statuses</option>
                <option value="EVALUATED_DECISIVE">Evaluated — Decisive</option>
                <option value="ABSTAINED">Abstained</option>
                <option value="VALIDATION_REJECTED">Validation Rejected</option>
                <option value="EVALUATION_FAILED">Evaluation Failed</option>
                <option value="NOT_EVALUATED">Not Evaluated</option>
                <option value="QUEUED">Queued</option>
                <option value="RUNNING">Running</option>
              </select>
            </div>

            <div className="flex items-center gap-2 flex-1 max-w-sm">
              <Search className="w-3.5 h-3.5 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") fetchTrackingData();
                }}
                placeholder="Search Incident ID..."
                className="w-full px-2.5 py-1 rounded bg-slate-950 border border-slate-700 text-slate-200 text-xs font-mono focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={fetchTrackingData}
                disabled={loadingTracking}
                className="px-3 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold text-xs flex items-center gap-1.5 transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${loadingTracking ? "animate-spin" : ""}`} />
                Refresh
              </button>
            </div>
          </div>

          {/* Compact Incident Table */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-sans">
                <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 text-[11px] uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="py-2.5 px-3">Incident</th>
                    <th className="py-2.5 px-3">Analyst Review</th>
                    <th className="py-2.5 px-3">AI Evaluation</th>
                    <th className="py-2.5 px-3">Policy</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {loadingTracking ? (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-slate-500 text-xs">
                        <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-cyan-400" />
                        Loading authoritative evaluation records...
                      </td>
                    </tr>
                  ) : trackingData.items.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-slate-500 text-xs">
                        No incidents match the selected evaluation status filters.
                      </td>
                    </tr>
                  ) : (
                    trackingData.items.map((item) => {
                      const rev = item.analyst_review;
                      let revBadge = <span className="text-slate-500 text-[11px]">Unreviewed</span>;
                      if (rev) {
                        const av = rev.analyst_verdict;
                        if (av === "FALSE_POSITIVE") {
                          revBadge = (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                              Verified FP
                            </span>
                          );
                        } else if (av === "TRUE_POSITIVE") {
                          revBadge = (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-950/80 text-rose-300 border border-rose-800">
                              Verified TP
                            </span>
                          );
                        } else {
                          revBadge = (
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950/80 text-amber-300 border border-amber-800">
                              Insufficient Evidence
                            </span>
                          );
                        }
                      }

                      return (
                        <tr key={item.incident_id} className="hover:bg-slate-800/30 transition-colors">
                          {/* Incident ID */}
                          <td className="py-2.5 px-3 font-mono font-bold text-slate-200">
                            <div>
                              <span>#{item.incident_id}</span>
                              <span className="block text-[10px] font-normal text-slate-500 font-sans truncate max-w-xs">
                                {item.title || item.event_type}
                              </span>
                            </div>
                          </td>

                          {/* Analyst Review */}
                          <td className="py-2.5 px-3">
                            {revBadge}
                          </td>

                          {/* AI Evaluation Status Badge */}
                          <td className="py-2.5 px-3">
                            <div className="flex items-center gap-2">
                              {renderBadge(item.status, item.status_display, item.badge_color)}
                              {item.effective_verdict && item.effective_verdict !== "[Hidden - Blind Review]" && (
                                <span className="text-[10px] font-mono text-slate-400">
                                  ({item.effective_verdict})
                                </span>
                              )}
                            </div>
                          </td>

                          {/* Policy Version */}
                          <td className="py-2.5 px-3 font-mono text-slate-300 text-xs">
                            {item.policy_version_number ? `v${item.policy_version_number}` : "—"}
                          </td>

                          {/* Actions */}
                          <td className="py-2.5 px-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              {/* Primary Inspect/View Button */}
                              {item.status === "VALIDATION_REJECTED" ? (
                                <button
                                  onClick={() => setSelectedEvaluationDetail(item)}
                                  className="px-2 py-1 rounded bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800 text-[11px] font-semibold"
                                >
                                  Inspect Error
                                </button>
                              ) : item.status === "EVALUATION_FAILED" ? (
                                <button
                                  onClick={() => setSelectedEvaluationDetail(item)}
                                  className="px-2 py-1 rounded bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800 text-[11px] font-semibold"
                                >
                                  Inspect Error
                                </button>
                              ) : item.status === "NOT_EVALUATED" ? (
                                <button
                                  onClick={() => onNavigateToTest?.(item.incident_id)}
                                  className="px-2 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-950 text-[11px] font-bold"
                                >
                                  Run AI Test
                                </button>
                              ) : item.status === "ABSTAINED" ? (
                                <button
                                  onClick={() => setSelectedEvaluationDetail(item)}
                                  className="px-2 py-1 rounded bg-amber-950 hover:bg-amber-900 text-amber-300 border border-amber-800 text-[11px] font-semibold"
                                >
                                  Inspect
                                </button>
                              ) : (
                                <button
                                  onClick={() => setSelectedEvaluationDetail(item)}
                                  className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[11px] font-semibold"
                                >
                                  View
                                </button>
                              )}

                              {/* History Modal Trigger */}
                              <button
                                onClick={() => openHistoryModal(item.incident_id)}
                                title="Evaluation History"
                                className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                              >
                                <History className="w-3.5 h-3.5" />
                              </button>

                              {/* Prompt Inspector Trigger */}
                              {item.has_existing_prompt_capture && onOpenActualPrompt && (
                                <button
                                  onClick={() => onOpenActualPrompt(item.incident_id)}
                                  title="Inspect Prompt Capture"
                                  className="p-1 rounded text-cyan-400 hover:text-cyan-200 hover:bg-slate-800"
                                >
                                  <FileCode className="w-3.5 h-3.5" />
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

            {/* Tracking Summary Footer Bar */}
            {trackingData.summary && (
              <div className="p-3 bg-slate-950/90 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
                <div className="flex items-center gap-4">
                  <span>
                    Total: <strong className="text-slate-200">{trackingData.summary.total_incidents}</strong>
                  </span>
                  <span>
                    Decisive: <strong className="text-emerald-400">{trackingData.summary.evaluated_decisive}</strong>
                  </span>
                  <span>
                    Abstained: <strong className="text-amber-400">{trackingData.summary.abstained}</strong>
                  </span>
                  <span>
                    Rejected: <strong className="text-rose-400">{trackingData.summary.validation_rejected}</strong>
                  </span>
                  <span>
                    Missing Inference: <strong className="text-slate-200">{trackingData.summary.not_evaluated}</strong>
                  </span>
                </div>

                <div className="flex items-center gap-3 font-mono text-[11px]">
                  <span>Decision Coverage: <strong>{trackingData.summary.decision_coverage_percent}%</strong></span>
                  <span>Accuracy: <strong className={trackingData.summary.accuracy_status === "MEASURABLE" ? "text-emerald-400" : "text-amber-400"}>{trackingData.summary.accuracy_status}</strong></span>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* MODAL 1: Evaluation Detail & Validation Failure Inspector */}
      {selectedEvaluationDetail && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-fadeIn">
          <div className="w-full max-w-xl rounded-xl border border-slate-800 bg-slate-900 p-5 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-cyan-400" />
                <span className="font-bold text-slate-200 text-sm">
                  Evaluation Record — Incident #{selectedEvaluationDetail.incident_id}
                </span>
              </div>
              <button
                onClick={() => setSelectedEvaluationDetail(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {/* Status Header */}
              <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 flex items-center justify-between">
                <div>
                  <span className="text-slate-500 block text-[11px]">Evaluation Status:</span>
                  <div className="mt-1">
                    {renderBadge(
                      selectedEvaluationDetail.status,
                      selectedEvaluationDetail.status_display,
                      selectedEvaluationDetail.badge_color
                    )}
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-slate-500 block text-[11px]">Policy Version:</span>
                  <span className="font-mono font-bold text-slate-200">
                    {selectedEvaluationDetail.policy_version_number ? `v${selectedEvaluationDetail.policy_version_number}` : "—"}
                  </span>
                </div>
              </div>

              {/* Execution Metadata Grid */}
              <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-500 font-sans block text-[10px]">Model:</span>
                  <span className="text-slate-200 font-bold">
                    {selectedEvaluationDetail.model_name || "Qwen/Qwen2.5-7B-Instruct-AWQ"}
                  </span>
                </div>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-500 font-sans block text-[10px]">Inference Type:</span>
                  <span className={selectedEvaluationDetail.is_simulated ? "text-amber-400" : "text-emerald-400"}>
                    {selectedEvaluationDetail.is_simulated ? "Simulated / Mock" : "Real Server 2 vLLM"}
                  </span>
                </div>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-500 font-sans block text-[10px]">Raw Model Verdict:</span>
                  <span className="text-cyan-300 font-bold">
                    {selectedEvaluationDetail.raw_model_verdict || "—"}
                  </span>
                </div>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800">
                  <span className="text-slate-500 font-sans block text-[10px]">Governed Effective Verdict:</span>
                  <span className="text-slate-200 font-bold">
                    {selectedEvaluationDetail.effective_verdict || "—"}
                  </span>
                </div>
              </div>

              {/* Validation Failure / Rejection Notice */}
              {selectedEvaluationDetail.status === "VALIDATION_REJECTED" && (
                <div className="p-3 rounded-lg border border-rose-800/80 bg-rose-950/30 text-rose-300 space-y-1">
                  <span className="font-bold flex items-center gap-1.5 text-rose-200">
                    <AlertTriangle className="w-4 h-4 text-rose-400" />
                    Deterministic Validation Rejected
                  </span>
                  <p className="text-[11px] leading-relaxed">
                    Failure Reason: <strong>{selectedEvaluationDetail.validation_failure_reason || selectedEvaluationDetail.validation_status}</strong>
                  </p>
                  <p className="text-[10px] text-slate-400 mt-1">
                    The model generated output, but deterministic evidence grounding or reasoning integrity verification rejected the proposal. The effective outcome was converted to REQUIRES_ATTENTION for safety.
                  </p>
                </div>
              )}

              {/* Execution Error Notice */}
              {selectedEvaluationDetail.status === "EVALUATION_FAILED" && (
                <div className="p-3 rounded-lg border border-rose-800/80 bg-rose-950/30 text-rose-300 space-y-1">
                  <span className="font-bold flex items-center gap-1.5 text-rose-200">
                    <XCircle className="w-4 h-4 text-rose-400" />
                    Inference Execution Failed
                  </span>
                  <p className="text-[11px] leading-relaxed font-mono">
                    {selectedEvaluationDetail.validation_failure_reason || "Inference dispatch failed or timed out"}
                  </p>
                </div>
              )}

              {/* Reasoning / Rationale */}
              {selectedEvaluationDetail.reason && (
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-950 space-y-1">
                  <span className="text-slate-400 font-semibold block text-[11px]">Model Rationale:</span>
                  <p className="text-slate-300 text-[11px] leading-relaxed whitespace-pre-wrap">
                    {selectedEvaluationDetail.reason}
                  </p>
                </div>
              )}

              {/* Token & Latency Telemetry */}
              {selectedEvaluationDetail.token_usage && (
                <div className="p-2.5 rounded-lg border border-slate-800 bg-slate-950 flex items-center justify-between text-[11px] font-mono text-slate-400">
                  <span>Tokens: {selectedEvaluationDetail.token_usage.total_tokens || "—"}</span>
                  <span>Latency: {selectedEvaluationDetail.latency_ms ? `${selectedEvaluationDetail.latency_ms} ms` : "—"}</span>
                  <span>Execution: #{selectedEvaluationDetail.execution_id?.slice(0, 8) || "—"}</span>
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 border-t border-slate-800 pt-3">
              {selectedEvaluationDetail.has_existing_prompt_capture && onOpenActualPrompt && (
                <button
                  onClick={() => {
                    const incId = selectedEvaluationDetail.incident_id;
                    setSelectedEvaluationDetail(null);
                    onOpenActualPrompt(incId);
                  }}
                  className="px-3 py-1.5 rounded bg-cyan-950 hover:bg-cyan-900 text-cyan-300 border border-cyan-800 text-xs font-semibold flex items-center gap-1.5"
                >
                  <FileCode className="w-3.5 h-3.5" />
                  View Prompt Capture
                </button>
              )}
              <button
                onClick={() => setSelectedEvaluationDetail(null)}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: Full Chronological Evaluation History */}
      {historyModalIncidentId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs animate-fadeIn">
          <div className="w-full max-w-2xl rounded-xl border border-slate-800 bg-slate-900 p-5 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-cyan-400" />
                <span className="font-bold text-slate-200 text-sm">
                  AI Evaluation History — Incident #{historyModalIncidentId}
                </span>
              </div>
              <button
                onClick={() => setHistoryModalIncidentId(null)}
                className="p-1 rounded text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              {loadingHistory ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-1 text-cyan-400" />
                  Loading historical attempts...
                </div>
              ) : historyItems.length === 0 ? (
                <div className="py-12 text-center text-slate-500 text-xs">
                  No prior evaluation attempts recorded for this incident.
                </div>
              ) : (
                <div className="space-y-2">
                  {historyItems.map((attempt, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg border border-slate-800 bg-slate-950/80 space-y-1.5"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold text-cyan-300">
                          Attempt #{historyItems.length - idx}: v{attempt.policy_version_number || "1"} ({attempt.policy_status || "APPROVED"})
                        </span>
                        <span className="text-[11px] text-slate-500 font-mono">
                          {attempt.captured_at ? new Date(attempt.captured_at).toLocaleString() : ""}
                        </span>
                      </div>

                      <div className="grid grid-cols-3 gap-2 font-mono text-[11px]">
                        <div>
                          <span className="text-slate-500 block text-[10px]">Dispatch:</span>
                          <span className="text-slate-200">{attempt.dispatch_status}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[10px]">Model Verdict:</span>
                          <span className="text-cyan-300 font-bold">{attempt.raw_verdict || "—"}</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block text-[10px]">Tokens / Latency:</span>
                          <span className="text-slate-300">{attempt.total_tokens || 0} tok / {attempt.latency_ms || 0}ms</span>
                        </div>
                      </div>

                      {attempt.error_message && (
                        <div className="p-2 rounded bg-rose-950/40 border border-rose-800/60 text-rose-300 text-[10px] font-mono">
                          Error: {attempt.error_message}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end border-t border-slate-800 pt-3">
              <button
                onClick={() => setHistoryModalIncidentId(null)}
                className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
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
