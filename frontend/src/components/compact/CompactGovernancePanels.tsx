"use client";

import React, { useState, ReactNode } from "react";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Send,
  Eye,
  EyeOff,
  Shield,
  RotateCcw,
  AlertOctagon,
  Award,
  Layers,
  ArrowRight,
} from "lucide-react";
import { StatusBadge } from "./CompactDesignSystem";

// =============================================================================
// PRODUCTION ELIGIBILITY CHECKLIST
// =============================================================================
export interface ProductionEligibilityChecklistProps {
  isEligible: boolean;
  lifecycleStage: string;
  totalAnalystReviews: number;
  qualityScore: number | null;
  empiricalAccuracy: number | null | undefined;
  eligibilityReasons?: string[];
  onRequestPromotion?: () => void;
  canRequestPromotion?: boolean;
}

export function ProductionEligibilityChecklist({
  isEligible,
  lifecycleStage,
  totalAnalystReviews,
  qualityScore,
  empiricalAccuracy,
  eligibilityReasons = [],
  onRequestPromotion,
  canRequestPromotion,
}: ProductionEligibilityChecklistProps) {
  // Filter for blockers only (ignore satisfied requirements to reduce clutter)
  const blockers = eligibilityReasons.filter(
    (r) =>
      !r.toLowerCase().includes("passed") &&
      !r.toLowerCase().includes("satisfied") &&
      !r.toLowerCase().includes("achieved")
  );

  return (
    <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40 text-xs space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Award className="w-4 h-4 text-sky-400" />
          <span className="font-bold text-slate-100">Production Promotion Eligibility</span>
        </div>
        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-bold border flex items-center gap-1 ${
            isEligible
              ? "bg-emerald-950 text-emerald-300 border-emerald-800"
              : "bg-amber-950 text-amber-300 border-amber-800"
          }`}
        >
          {isEligible ? (
            <>
              <CheckCircle2 className="w-3 h-3 text-emerald-400" /> ELIGIBLE FOR PRODUCTION
            </>
          ) : (
            <>
              <XCircle className="w-3 h-3 text-amber-400" /> PROMOTION BLOCKED
            </>
          )}
        </span>
      </div>

      {isEligible ? (
        <div className="p-2.5 rounded-lg bg-emerald-950/30 border border-emerald-900/60 text-emerald-300 flex items-center justify-between">
          <span>All statistical quality and accuracy thresholds met. Ready for formal promotion review.</span>
          {onRequestPromotion && (
            <button
              type="button"
              disabled={!canRequestPromotion}
              onClick={onRequestPromotion}
              className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-semibold inline-flex items-center gap-1 transition-colors disabled:opacity-50"
            >
              Request Promotion <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-1.5">
          <p className="text-[11px] text-slate-400 font-medium">
            Active criteria preventing promotion to Controlled Production:
          </p>
          <div className="space-y-1">
            {blockers.length > 0 ? (
              blockers.map((blocker, idx) => (
                <div
                  key={idx}
                  className="p-2 rounded-lg bg-slate-950/70 border border-amber-900/40 text-amber-300 text-[11px] flex items-start gap-2"
                >
                  <XCircle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                  <span>{blocker}</span>
                </div>
              ))
            ) : (
              <div className="p-2 rounded-lg bg-slate-950/70 border border-slate-800 text-slate-400 text-[11px]">
                Requires minimum 100 verified reviews (current: {totalAnalystReviews}) and G1–G8 validation score ≥ 70.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// =============================================================================
// REVIEW DECISION PANEL (DOUBLE-BLIND WORKBENCH)
// =============================================================================
export interface ReviewDecisionPanelProps {
  selectedIncident: any;
  onSubmitReview: (payload: {
    verdict: "TRUE_POSITIVE" | "FALSE_POSITIVE" | "INSUFFICIENT_EVIDENCE";
    notes: string;
    evidenceRefs: string[];
  }) => Promise<void>;
  submitting: boolean;
  revealedResult?: any | null;
  onAdjudicate?: (verdict: "TRUE_POSITIVE" | "FALSE_POSITIVE", notes: string) => Promise<void>;
}

export function ReviewDecisionPanel({
  selectedIncident,
  onSubmitReview,
  submitting,
  revealedResult,
  onAdjudicate,
}: ReviewDecisionPanelProps) {
  const [verdict, setVerdict] = useState<"TRUE_POSITIVE" | "FALSE_POSITIVE" | "INSUFFICIENT_EVIDENCE">("FALSE_POSITIVE");
  const [notes, setNotes] = useState("");
  const [evidenceRefs, setEvidenceRefs] = useState("");

  if (!selectedIncident) {
    return (
      <div className="p-8 text-center rounded-xl border border-slate-800 bg-slate-950/40 text-slate-400 text-xs">
        Select a pending incident from the queue to conduct independent evaluation.
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmitReview({
      verdict,
      notes,
      evidenceRefs: evidenceRefs ? evidenceRefs.split(",").map((s) => s.trim()) : [],
    });
  };

  return (
    <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 space-y-3 text-xs">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <EyeOff className="w-4 h-4 text-amber-400" />
          <span className="font-bold text-slate-100">
            Independent Double-Blind Evaluation: Incident #{selectedIncident.incident_id}
          </span>
        </div>
        <span className="px-2 py-0.5 rounded text-[10px] bg-amber-950/70 border border-amber-800 text-amber-300 font-bold uppercase">
          Blind Mode Active
        </span>
      </div>

      {/* Incident Summary Card */}
      <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800/80 grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
        <div>
          <span className="text-slate-500 block text-[10px] uppercase">Severity</span>
          <span className="font-semibold text-slate-200">{selectedIncident.severity}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase">Rule Matched</span>
          <span className="font-mono text-cyan-300 truncate block">{selectedIncident.rule_name || selectedIncident.rule_id}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase">Customer / Tenant</span>
          <span className="text-slate-200">{selectedIncident.customer || "Default"}</span>
        </div>
        <div>
          <span className="text-slate-500 block text-[10px] uppercase">Detection Status</span>
          <span className="text-slate-200">{selectedIncident.status || "NEW"}</span>
        </div>
      </div>

      {/* Post-submission Result Revelation */}
      {revealedResult ? (
        <div className="p-3 rounded-lg border border-cyan-800/80 bg-cyan-950/30 text-cyan-200 space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-bold flex items-center gap-1.5 text-slate-100">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Evaluation Saved &amp; AI Verdict Revealed
            </span>
            <span
              className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                revealedResult.comparison_outcome === "AGREED"
                  ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                  : "bg-rose-950 text-rose-300 border border-rose-800"
              }`}
            >
              {revealedResult.comparison_outcome}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-[11px] pt-1">
            <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase">Stored AI Verdict:</span>
              <strong className="text-slate-100">{revealedResult.ai_verdict}</strong>
            </div>
            <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 block text-[10px] uppercase">Analyst Verdict:</span>
              <strong className="text-slate-100">{revealedResult.analyst_verdict}</strong>
            </div>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-3">
          {/* Decision Buttons */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-300 block">
              Analyst Determination (AI verdict hidden until submission):
            </label>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setVerdict("TRUE_POSITIVE")}
                className={`py-2 px-3 rounded-lg border text-xs font-bold transition-all ${
                  verdict === "TRUE_POSITIVE"
                    ? "bg-rose-950 border-rose-600 text-rose-200 shadow-sm"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                True Positive
              </button>
              <button
                type="button"
                onClick={() => setVerdict("FALSE_POSITIVE")}
                className={`py-2 px-3 rounded-lg border text-xs font-bold transition-all ${
                  verdict === "FALSE_POSITIVE"
                    ? "bg-emerald-950 border-emerald-600 text-emerald-200 shadow-sm"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                False Positive
              </button>
              <button
                type="button"
                onClick={() => setVerdict("INSUFFICIENT_EVIDENCE")}
                className={`py-2 px-3 rounded-lg border text-xs font-bold transition-all ${
                  verdict === "INSUFFICIENT_EVIDENCE"
                    ? "bg-amber-950 border-amber-600 text-amber-200 shadow-sm"
                    : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                Insufficient Evidence
              </button>
            </div>
          </div>

          {/* Notes & Evidence Refs */}
          <div className="space-y-1">
            <label className="text-[11px] font-semibold text-slate-400 block">
              Analyst Rationale / Justification:
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Provide evidence-grounded reasoning for your verdict..."
              rows={2}
              className="w-full px-2.5 py-1.5 text-xs rounded-lg border border-slate-800 bg-slate-950 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <span className="text-[10px] text-slate-500">
              Double-blind review protocol prevents confirmation bias.
            </span>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-1.5 rounded-lg theme-primary-btn text-xs font-semibold inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              {submitting ? "Submitting..." : "Submit Review"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

// =============================================================================
// CONFIRMATION DIALOG MODAL
// =============================================================================
export function ConfirmationDialog({
  isOpen,
  title,
  message,
  confirmLabel = "Confirm",
  confirmVariant = "primary",
  isLoading = false,
  onConfirm,
  onCancel,
}: {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  confirmVariant?: "primary" | "danger" | "success";
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!isOpen) return null;

  const variantClass = {
    primary: "theme-primary-btn",
    danger: "bg-rose-600 hover:bg-rose-500 text-white",
    success: "bg-emerald-600 hover:bg-emerald-500 text-white",
  }[confirmVariant];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3 shadow-2xl">
        <h3 className="text-sm font-bold text-slate-100">{title}</h3>
        <p className="text-xs text-slate-300 leading-relaxed">{message}</p>
        <div className="flex justify-end gap-2 pt-2 border-t border-slate-800/80">
          <button
            type="button"
            disabled={isLoading}
            onClick={onCancel}
            className="px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isLoading}
            onClick={onConfirm}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50 ${variantClass}`}
          >
            {isLoading ? "Processing..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
