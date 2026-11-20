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
} from "lucide-react";
import { api, formatApiErrorMessage } from "@/lib/api";

interface ReviewIncidentsWorkbenchProps {
  ruleId: string;
  ruleName?: string;
  customer?: string;
  isViewer?: boolean;
  onReviewSubmitted?: () => void;
  onOpenActualPrompt?: (incidentId: string) => void;
  onNavigateToTest?: () => void;
}

export function ReviewIncidentsWorkbench({
  ruleId,
  ruleName,
  customer,
  isViewer = false,
  onReviewSubmitted,
  onOpenActualPrompt,
  onNavigateToTest,
}: ReviewIncidentsWorkbenchProps) {
  const [incidents, setIncidents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [counts, setCounts] = useState<{
    pending: number;
    reviewed: number;
    verifiedGt: number;
  }>({ pending: 0, reviewed: 0, verifiedGt: 0 });

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

  const fetchIncidents = async () => {
    if (!ruleId) return;
    setLoading(true);
    try {
      const [reviewData, profileData] = await Promise.all([
        api.getPendingDoubleBlindReviews(ruleId, 50, 0).catch(() => ({ items: [], total: 0 })),
        api.getRuleLearningProfileDetail(ruleId, customer).catch(() => null),
      ]);

      const items = reviewData.items || [];
      setIncidents(items);
      setCounts({
        pending: reviewData.total ?? items.length,
        reviewed: profileData?.total_analyst_reviews ?? 0,
        verifiedGt: (profileData?.verified_tp_count ?? 0) + (profileData?.verified_fp_count ?? 0),
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

  useEffect(() => {
    setSelectedIncident(null);
    setRevealedResult(null);
    fetchIncidents();
  }, [ruleId]);

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
          // Extract raw logs if present
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
        analyst_notes: analystNotes,
        evidence_references: evidenceRefs ? evidenceRefs.split(",").map((s) => s.trim()) : [],
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

  return (
    <div id="incident-review-workbench" className="space-y-4 scroll-mt-6 transition-all duration-300">
      {/* Top Counts & Blind Status Bar */}
      <div className="p-3 rounded-xl border border-slate-800 bg-slate-950/70 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-slate-400 font-semibold">Pending Review:</span>
            <span className="font-bold text-cyan-300 font-mono text-sm">{counts.pending}</span>
          </div>

          <div className="text-slate-600">|</div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-semibold">Reviewed:</span>
            <span className="font-bold text-slate-200 font-mono">{counts.reviewed}</span>
          </div>

          <div className="text-slate-600">|</div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-semibold">Verified Ground Truth:</span>
            <span className="font-bold text-emerald-400 font-mono">{counts.verifiedGt}</span>
          </div>
        </div>

        {/* Double-Blind Indicator */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-lg bg-indigo-950/40 border border-indigo-800/60 text-indigo-300 text-[11px] font-semibold">
          <EyeOff className="w-3.5 h-3.5 text-indigo-400" />
          <span>Double-Blind Active (AI Determination Masked)</span>
        </div>
      </div>

      {feedback && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between ${feedback.type === "success"
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

      {/* Split-Panel Workbench Layout */}
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
                    className={`p-3 cursor-pointer transition-colors text-xs ${isSelected
                      ? "bg-cyan-950/30 border-l-4 border-cyan-400"
                      : "hover:bg-slate-900/80 border-l-4 border-transparent"
                      }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-mono font-bold text-slate-200">
                        #{inc.incident_id}
                      </span>
                      <span
                        className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${inc.severity === "CRITICAL"
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
              <div className="p-3.5 rounded-xl border border-indigo-950/80 bg-indigo-950/20 space-y-3">
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
                    className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center gap-1 transition-colors ${analystVerdict === "TRUE_POSITIVE"
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
                    className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center gap-1 transition-colors ${analystVerdict === "FALSE_POSITIVE"
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
                    className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center gap-1 transition-colors ${analystVerdict === "INSUFFICIENT_EVIDENCE"
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
    </div>
  );
}

