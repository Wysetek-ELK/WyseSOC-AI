"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  Activity,
  CheckCircle2,
  XCircle,
  HelpCircle,
  ArrowRight,
  TrendingUp,
  Cpu,
  RefreshCw,
  GitBranch,
  Sliders,
  Scale,
  EyeOff,
  Eye,
  Send,
  Lock,
  Radio,
  FileCheck2,
  AlertOctagon,
  Award
} from "lucide-react";
import { api, formatApiErrorMessage } from "@/lib/api";

interface RuleLearningDashboardProps {
  ruleId: string;
  ruleName?: string;
  customer?: string;
  onProfileUpdate?: (profile: any) => void;
}

export function RuleLearningDashboard({ ruleId, ruleName, customer, onProfileUpdate }: RuleLearningDashboardProps) {
  const [profile, setProfile] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [initializing, setInitializing] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Sub-Tab Navigation
  const [activeSubTab, setActiveSubTab] = useState<"metrics" | "workbench" | "governance">("metrics");

  // Double-Blind Review Workbench State
  const [pendingReviews, setPendingReviews] = useState<any[]>([]);
  const [loadingReviews, setLoadingReviews] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<any | null>(null);
  const [analystVerdict, setAnalystVerdict] = useState<"TRUE_POSITIVE" | "FALSE_POSITIVE" | "INSUFFICIENT_EVIDENCE">("FALSE_POSITIVE");
  const [analystNotes, setAnalystNotes] = useState("");
  const [evidenceRefs, setEvidenceRefs] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);
  const [revealedResult, setRevealedResult] = useState<any | null>(null);

  // Governance Promotion & Emergency State
  const [targetStage, setTargetStage] = useState("SUPERVISED_PILOT");
  const [promotionJustification, setPromotionJustification] = useState("");
  const [promotionRunId, setPromotionRunId] = useState("");
  const [requestingPromotion, setRequestingPromotion] = useState(false);
  const [killSwitchReason, setKillSwitchReason] = useState("");
  const [killSwitchModalOpen, setKillSwitchModalOpen] = useState(false);
  const [engagingKillSwitch, setEngagingKillSwitch] = useState(false);

  // Dispute Adjudication State
  const [adjudicationVerdict, setAdjudicationVerdict] = useState<"TRUE_POSITIVE" | "FALSE_POSITIVE">("FALSE_POSITIVE");
  const [adjudicationRationale, setAdjudicationRationale] = useState("");
  const [adjudicating, setAdjudicating] = useState(false);

  const fetchProfile = async () => {
    if (!ruleId) {
      setLoading(false);
      setProfile(null);
      return;
    }
    setLoading(true);
    setFeedback(null);
    try {
      const data = await api.getRuleLearningProfileDetail(ruleId, customer);
      setProfile(data);
      onProfileUpdate?.(data);
    } catch (err: any) {
      console.error(err);
      setFeedback({ type: "error", text: formatApiErrorMessage(err, "Failed to load learning profile") });
    } finally {
      setLoading(false);
    }
  };

  const handleInitializeProfile = async () => {
    if (!ruleId) return;
    setInitializing(true);
    setFeedback(null);
    try {
      const initialized = await api.initializeRuleLearningProfile(ruleId, customer);
      setProfile(initialized);
      setFeedback({ type: "success", text: "Detection rule learning profile successfully initialized in LEARNING mode." });
      await fetchPendingReviews();
    } catch (err: any) {
      setFeedback({ type: "error", text: formatApiErrorMessage(err, "Failed to initialize learning profile") });
    } finally {
      setInitializing(false);
    }
  };

  const fetchPendingReviews = async () => {
    setLoadingReviews(true);
    try {
      const data = await api.getPendingDoubleBlindReviews(ruleId, 50, 0);
      setPendingReviews(data.items || []);
      if (data.items && data.items.length > 0 && !selectedIncident) {
        setSelectedIncident(data.items[0]);
      }
    } catch (err: any) {
      console.error("Failed to fetch pending reviews:", err);
    } finally {
      setLoadingReviews(false);
    }
  };

  useEffect(() => {
    fetchProfile();
    fetchPendingReviews();
  }, [ruleId]);

  const handleTransition = async (newStage: string, reason: string) => {
    setTransitioning(true);
    setFeedback(null);
    try {
      await api.transitionRuleLifecycle(ruleId, newStage, reason);
      setFeedback({ type: "success", text: `Rule successfully transitioned to ${newStage}` });
      await fetchProfile();
    } catch (err: any) {
      setFeedback({ type: "error", text: formatApiErrorMessage(err, "Transition failed") });
    } finally {
      setTransitioning(false);
    }
  };

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
      setFeedback({ type: "success", text: `Independent review recorded. Comparison outcome: ${result.comparison_outcome}` });

      // Refresh data
      await fetchProfile();
      await fetchPendingReviews();
    } catch (err: any) {
      console.error(err);
      setFeedback({ type: "error", text: formatApiErrorMessage(err, "Failed to submit review") });
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleAdjudicateReview = async () => {
    if (!revealedResult?.review_id) return;
    setAdjudicating(true);
    try {
      const res = await api.adjudicateAnalystReview(
        revealedResult.review_id,
        adjudicationVerdict,
        adjudicationRationale || "Adjudicated by Senior Analyst"
      );
      setFeedback({ type: "success", text: `Review adjudicated. Binding verdict: ${res.final_verdict}` });
      setRevealedResult(null);
      await fetchProfile();
    } catch (err: any) {
      setFeedback({ type: "error", text: formatApiErrorMessage(err, "Failed to adjudicate review") });
    } finally {
      setAdjudicating(false);
    }
  };

  const handleRequestPromotion = async () => {
    if (!profile?.id) return;
    setRequestingPromotion(true);
    setFeedback(null);
    try {
      await api.requestRulePromotion(
        profile.id,
        targetStage,
        promotionJustification || "Qualified through verified sample benchmarks",
        promotionRunId || undefined
      );
      setFeedback({ type: "success", text: `Formal promotion request for ${targetStage} submitted.` });
      setPromotionJustification("");
    } catch (err: any) {
      setFeedback({ type: "error", text: formatApiErrorMessage(err, "Failed to submit promotion request") });
    } finally {
      setRequestingPromotion(false);
    }
  };

  const handleEngageKillSwitch = async () => {
    if (!killSwitchReason.trim()) return;
    setEngagingKillSwitch(true);
    try {
      await api.emergencyDisableAutomation(killSwitchReason);
      setFeedback({ type: "error", text: "GLOBAL EMERGENCY KILL-SWITCH ENGAGED. All automated closures halted." });
      setKillSwitchModalOpen(false);
      setKillSwitchReason("");
      await fetchProfile();
    } catch (err: any) {
      setFeedback({ type: "error", text: formatApiErrorMessage(err, "Failed to engage kill-switch") });
    } finally {
      setEngagingKillSwitch(false);
    }
  };

  if (!ruleId) {
    return (
      <div className="p-8 text-center text-slate-400 rounded-lg border border-slate-800 bg-slate-900/40">
        <p className="text-sm font-semibold text-slate-300">No Detection Rule Selected</p>
        <p className="text-xs text-slate-400 mt-1">
          Please select a detection rule from the catalog above to view its learning profile, accuracy metrics, and double-blind review workbench.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-8 text-center text-slate-400 flex items-center justify-center gap-2">
        <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
        Loading Rule Learning Profile &amp; Governance Metrics...
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="p-6 rounded-lg border border-slate-800 bg-slate-900/40 text-slate-400 text-xs text-center space-y-3">
        <p>No learning profile could be loaded for rule <span className="font-mono text-cyan-400">{ruleId}</span>.</p>
        <button
          onClick={handleInitializeProfile}
          disabled={initializing}
          className="px-3 py-1.5 rounded-lg bg-sky-900/60 hover:bg-sky-800 text-sky-200 border border-sky-700 text-xs font-semibold inline-flex items-center gap-1.5 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${initializing ? "animate-spin" : ""}`} />
          {initializing ? "Initializing Profile..." : "Initialize Learning Profile"}
        </button>
      </div>
    );
  }

  const stage = profile.lifecycle_stage || "LEARNING";
  const stageColorMap: Record<string, { bg: string; text: string; border: string }> = {
    LEARNING: { bg: "bg-blue-950/40", text: "text-blue-300", border: "border-blue-800" },
    VALIDATION: { bg: "bg-indigo-950/40", text: "text-indigo-300", border: "border-indigo-800" },
    SUPERVISED_PILOT: { bg: "bg-amber-950/40", text: "text-amber-300", border: "border-amber-800" },
    CONTROLLED_PRODUCTION: { bg: "bg-emerald-950/40", text: "text-emerald-300", border: "border-emerald-800" },
    MONITORING: { bg: "bg-teal-950/40", text: "text-teal-300", border: "border-teal-800" },
    SUSPENDED: { bg: "bg-rose-950/40", text: "text-rose-300", border: "border-rose-800" },
    REVALIDATION_REQUIRED: { bg: "bg-orange-950/40", text: "text-orange-300", border: "border-orange-800" },
  };

  const currentColors = stageColorMap[stage] || stageColorMap.LEARNING;
  const isEligible = profile.is_production_eligible;
  const eligibilityReasons: string[] = profile.eligibility_reasons || [];
  const isPilotEligible = (profile.total_analyst_reviews || 0) >= 30;
  const isPromotionTargetEligible = targetStage === "CONTROLLED_PRODUCTION"
    ? isEligible
    : targetStage === "SUPERVISED_PILOT"
    ? isPilotEligible
    : true;
  const confusion = profile.confusion_matrix || {
    agreed_fp: profile.verified_fp_count || 0,
    critical_missed_tp: 0,
    ai_false_alarm: 0,
    agreed_tp: profile.verified_tp_count || 0,
  };

  return (
    <div className="space-y-4">
      {/* Top Banner: Stage & Feedback */}
      {feedback && (
        <div
          className={`p-2.5 rounded-lg border text-xs flex items-center justify-between ${
            feedback.type === "success"
              ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
              : "bg-rose-950/40 border-rose-800 text-rose-300"
          }`}
        >
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-slate-200 text-xs">
            ✕
          </button>
        </div>
      )}

      {/* Lifecycle Stage Header & Quick Transitions */}
      <div className={`p-3.5 rounded-xl border ${currentColors.border} ${currentColors.bg} flex flex-wrap items-center justify-between gap-3`}>
        <div className="flex items-center gap-3">
          <GitBranch className={`w-5 h-5 ${currentColors.text}`} />
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Detection Rule Lifecycle State</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-base font-black ${currentColors.text}`}>{stage}</span>
              <span className="text-xs text-slate-400">• Tenant: {profile.customer}</span>
              <span className="text-xs text-slate-400">• Archetype: {profile.primary_archetype}</span>
            </div>
          </div>
        </div>

        {/* Action Controls for Transitions */}
        <div className="flex items-center gap-2 flex-wrap">
          {stage === "LEARNING" && (
            <button
              onClick={() => handleTransition("VALIDATION", "Advance from Learning to Validation stage")}
              disabled={transitioning}
              className="px-3 py-1.5 rounded-lg bg-indigo-900/50 hover:bg-indigo-800 text-indigo-200 border border-indigo-700 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              Advance to VALIDATION
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {stage === "VALIDATION" && (
            <button
              onClick={() => handleTransition("SUPERVISED_PILOT", "Advance to Supervised Pilot following simulation validation")}
              disabled={transitioning || (profile?.total_analyst_reviews || 0) < 30}
              title={
                (profile?.total_analyst_reviews || 0) < 30
                  ? `Requires at least 30 verified analyst reviews before Supervised Pilot (current: ${profile?.total_analyst_reviews || 0}/30)`
                  : "Advance to Supervised Pilot"
              }
              className="px-3 py-1.5 rounded-lg bg-amber-900/50 hover:bg-amber-800 text-amber-200 border border-amber-700 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              Advance to SUPERVISED PILOT
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-950/80 border border-amber-700/60 font-mono">
                {profile?.total_analyst_reviews || 0}/30
              </span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}

          {stage === "SUPERVISED_PILOT" && (
            <button
              onClick={() => handleTransition("CONTROLLED_PRODUCTION", "Formal promotion to Controlled Production automation")}
              disabled={transitioning || !isEligible}
              title={!isEligible ? "Rule does not satisfy production criteria (see checklist below)" : "Promote to Production"}
              className="px-3 py-1.5 rounded-lg bg-emerald-900/50 hover:bg-emerald-800 text-emerald-200 border border-emerald-700 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              Promote to CONTROLLED PRODUCTION
              <ShieldCheck className="w-3.5 h-3.5" />
            </button>
          )}

          {stage !== "SUSPENDED" && (
            <button
              onClick={() => handleTransition("SUSPENDED", "Manual emergency suspension initiated by analyst")}
              disabled={transitioning}
              className="px-2.5 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-rose-300 border border-rose-800 text-xs font-semibold flex items-center gap-1 transition-colors disabled:opacity-50"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Suspend Rule
            </button>
          )}

          {stage === "SUSPENDED" && (
            <button
              onClick={() => handleTransition("LEARNING", "Revert suspended rule back to Learning mode")}
              disabled={transitioning}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              Revert to LEARNING
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex items-center gap-1 border-b border-slate-800 pb-1 text-xs">
        <button
          onClick={() => setActiveSubTab("metrics")}
          className={`px-3 py-1.5 rounded-t-lg font-semibold flex items-center gap-1.5 transition-colors ${
            activeSubTab === "metrics"
              ? "bg-slate-800 text-cyan-300 border-t-2 border-cyan-400"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <TrendingUp className="w-3.5 h-3.5" />
          Accuracy &amp; Confusion Matrix
        </button>

        <button
          onClick={() => setActiveSubTab("workbench")}
          className={`px-3 py-1.5 rounded-t-lg font-semibold flex items-center gap-1.5 transition-colors ${
            activeSubTab === "workbench"
              ? "bg-slate-800 text-cyan-300 border-t-2 border-cyan-400"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <EyeOff className="w-3.5 h-3.5" />
          Double-Blind Review Workbench ({pendingReviews.length})
        </button>

        <button
          onClick={() => setActiveSubTab("governance")}
          className={`px-3 py-1.5 rounded-t-lg font-semibold flex items-center gap-1.5 transition-colors ${
            activeSubTab === "governance"
              ? "bg-slate-800 text-cyan-300 border-t-2 border-cyan-400"
              : "text-slate-400 hover:text-slate-200"
          }`}
        >
          <Lock className="w-3.5 h-3.5" />
          Production Promotion &amp; Safety
        </button>
      </div>

      {/* SUB-TAB 1: ACCURACY & CONFUSION MATRIX */}
      {activeSubTab === "metrics" && (
        <div className="space-y-4">
          {/* 4 Primary Metric Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
            <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40">
              <div className="text-[10px] uppercase font-bold text-slate-400">Total Analyst Reviews</div>
              <div className="text-xl font-bold text-slate-100 mt-1">{profile.total_analyst_reviews}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                {profile.verified_tp_count} TP / {profile.verified_fp_count} FP
              </div>
            </div>

            <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40">
              <div className="text-[10px] uppercase font-bold text-slate-400">Observed FP Precision</div>
              <div className="text-xl font-bold text-emerald-400 mt-1">
                {profile.fp_precision !== null ? `${(profile.fp_precision * 100).toFixed(1)}%` : "N/A"}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Target: ≥98.0%</div>
            </div>

            <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40">
              <div className="text-[10px] uppercase font-bold text-slate-400 flex items-center justify-between">
                Wilson 95% Lower Bound
                <Scale className="w-3.5 h-3.5 text-cyan-400" />
              </div>
              <div className="text-xl font-bold text-cyan-400 mt-1">
                {profile.wilson_lower_bound !== null ? `${(profile.wilson_lower_bound * 100).toFixed(1)}%` : "N/A"}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Production Gate: ≥96.0%</div>
            </div>

            <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/40">
              <div className="text-[10px] uppercase font-bold text-slate-400">TP Recall (Sensitivity)</div>
              <div className="text-xl font-bold text-amber-400 mt-1">
                {profile.tp_recall !== null ? `${(profile.tp_recall * 100).toFixed(1)}%` : "N/A"}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">Target: ≥95.0%</div>
            </div>
          </div>

          {/* 2x2 Operational Confusion Matrix */}
          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-cyan-400" />
                Rule-Specific Ground-Truth Confusion Matrix
              </h3>
              <span className="text-[10px] text-slate-500">Based on Verified Human Analyst Determinations</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              {/* Agreed FP */}
              <div className="p-3 rounded-lg border border-emerald-900/40 bg-emerald-950/20 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-emerald-300">AI: FP &bull; Analyst: FP</span>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                </div>
                <div className="text-xl font-black text-emerald-200">{confusion.agreed_fp}</div>
                <div className="text-[10px] text-emerald-400/80">Agreed Benign — Eligible for Auto-Closure</div>
              </div>

              {/* Critical Missed TP */}
              <div className={`p-3 rounded-lg border space-y-1 ${
                confusion.critical_missed_tp > 0
                  ? "border-rose-700 bg-rose-950/40 text-rose-200 animate-pulse"
                  : "border-slate-800 bg-slate-950/40 text-slate-400"
              }`}>
                <div className="flex items-center justify-between">
                  <span className="font-bold text-rose-300">AI: FP &bull; Analyst: TP</span>
                  <AlertOctagon className="w-4 h-4 text-rose-400" />
                </div>
                <div className="text-xl font-black text-rose-300">{confusion.critical_missed_tp}</div>
                <div className="text-[10px] text-rose-400/80">Missed True Attack — Immediate Suspension Trigger</div>
              </div>

              {/* AI False Alarm */}
              <div className="p-3 rounded-lg border border-amber-900/40 bg-amber-950/20 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-amber-300">AI: TP &bull; Analyst: FP</span>
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                </div>
                <div className="text-xl font-black text-amber-200">{confusion.ai_false_alarm}</div>
                <div className="text-[10px] text-amber-400/80">False Alarm — Safe Escalation, Precision Loss</div>
              </div>

              {/* Agreed TP */}
              <div className="p-3 rounded-lg border border-cyan-900/40 bg-cyan-950/20 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-cyan-300">AI: TP &bull; Analyst: TP</span>
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                </div>
                <div className="text-xl font-black text-cyan-200">{confusion.agreed_tp}</div>
                <div className="text-[10px] text-cyan-400/80">Agreed Attack — Valid Escalation Confirmed</div>
              </div>
            </div>
          </div>

          {/* Production Eligibility Gating Checklist */}
          <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2.5">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-cyan-400" />
                Autonomous False-Positive Closure Eligibility Checklist
              </h3>
              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  isEligible
                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                    : "bg-amber-950 text-amber-300 border-amber-800"
                }`}
              >
                {isEligible ? "QUALIFIED FOR PRODUCTION" : "INELIGIBLE (TRAINING REQUIRED)"}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
              <div
                className={`p-2 rounded border flex items-center justify-between ${
                  profile.total_analyst_reviews >= 100
                    ? "bg-emerald-950/20 border-emerald-900 text-emerald-300"
                    : "bg-slate-950/40 border-slate-800 text-slate-400"
                }`}
              >
                <span>Verified Sample Size (≥100 reviews)</span>
                <span className="font-bold">{profile.total_analyst_reviews}/100</span>
              </div>

              <div
                className={`p-2 rounded border flex items-center justify-between ${
                  (profile.fp_precision || 0) >= 0.98
                    ? "bg-emerald-950/20 border-emerald-900 text-emerald-300"
                    : "bg-slate-950/40 border-slate-800 text-slate-400"
                }`}
              >
                <span>Observed FP Precision (≥98.0%)</span>
                <span className="font-bold">{((profile.fp_precision || 0) * 100).toFixed(1)}%</span>
              </div>

              <div
                className={`p-2 rounded border flex items-center justify-between ${
                  (profile.wilson_lower_bound || 0) >= 0.96
                    ? "bg-emerald-950/20 border-emerald-900 text-emerald-300"
                    : "bg-slate-950/40 border-slate-800 text-slate-400"
                }`}
              >
                <span>Wilson 95% Confidence Lower Bound (≥96.0%)</span>
                <span className="font-bold">{((profile.wilson_lower_bound || 0) * 100).toFixed(1)}%</span>
              </div>

              <div
                className={`p-2 rounded border flex items-center justify-between ${
                  (profile.tp_recall || 0) >= 0.95
                    ? "bg-emerald-950/20 border-emerald-900 text-emerald-300"
                    : "bg-slate-950/40 border-slate-800 text-slate-400"
                }`}
              >
                <span>TP Recall / True Attack Coverage (≥95.0%)</span>
                <span className="font-bold">{((profile.tp_recall || 0) * 100).toFixed(1)}%</span>
              </div>
            </div>

            {!isEligible && eligibilityReasons.length > 0 && (
              <div className="p-2 rounded bg-amber-950/20 border border-amber-900/40 text-[11px] text-amber-300 space-y-1">
                <div className="font-semibold">Unsatisfied Readiness Criteria:</div>
                <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                  {eligibilityReasons.map((r, idx) => (
                    <li key={idx}>{r}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUB-TAB 2: DOUBLE-BLIND REVIEW WORKBENCH */}
      {activeSubTab === "workbench" && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Left: Pending Incidents Queue */}
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-200">Pending Review Queue</span>
                <span className="text-[10px] text-slate-400">{pendingReviews.length} incidents</span>
              </div>

              <div className="max-h-96 overflow-y-auto space-y-1.5 pr-1">
                {pendingReviews.length === 0 ? (
                  <div className="p-6 text-center text-slate-500 text-xs">
                    No pending double-blind reviews for this rule.
                  </div>
                ) : (
                  pendingReviews.map((inc) => (
                    <div
                      key={inc.incident_id || inc.db_id}
                      onClick={() => {
                        setSelectedIncident(inc);
                        setRevealedResult(null);
                      }}
                      className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                        selectedIncident?.incident_id === inc.incident_id
                          ? "bg-cyan-950/40 border-cyan-700 text-cyan-200"
                          : "bg-slate-950/60 border-slate-800 text-slate-300 hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between font-mono font-bold">
                        <span>Incident #{inc.incident_id}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                          {inc.customer}
                        </span>
                      </div>
                      <div className="truncate text-[11px] text-slate-400 mt-1">{inc.title}</div>
                      <div className="flex items-center justify-between text-[10px] text-slate-500 mt-1">
                        <span>{inc.source_ip || "N/A"}</span>
                        <span>{inc.investigation_status || "PENDING"}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Right: Blind Assessment & Post-Submission Reveal */}
            <div className="lg:col-span-2 space-y-3">
              {selectedIncident ? (
                <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-4">
                  {/* Incident Header in Blind Mode */}
                  <div className="flex items-start justify-between border-b border-slate-800 pb-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-sm text-cyan-400">
                          Incident #{selectedIncident.incident_id}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-purple-950 text-purple-300 border border-purple-800 flex items-center gap-1">
                          <EyeOff className="w-3 h-3" />
                          DOUBLE-BLIND MODE ACTIVE
                        </span>
                      </div>
                      <h4 className="text-xs font-semibold text-slate-200 mt-1">{selectedIncident.title}</h4>
                    </div>
                  </div>

                  {/* Masked AI Shield Indicator */}
                  <div className="p-3 rounded-lg border border-indigo-900/40 bg-indigo-950/20 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 text-indigo-300">
                      <Lock className="w-4 h-4 text-indigo-400" />
                      <span>AI Model Verdict is masked to prevent analyst confirmation bias.</span>
                    </div>
                    <span className="text-[10px] text-indigo-400 font-mono">Revealed upon submission</span>
                  </div>

                  {/* Incident Telemetry Summary */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
                    <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                      <div className="text-slate-500 text-[10px]">Source IP</div>
                      <div className="font-mono text-slate-200">{selectedIncident.source_ip || "N/A"}</div>
                    </div>
                    <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                      <div className="text-slate-500 text-[10px]">Reporting Device</div>
                      <div className="font-mono text-slate-200">{selectedIncident.reporting_device || "N/A"}</div>
                    </div>
                    <div className="p-2 rounded bg-slate-950/60 border border-slate-800">
                      <div className="text-slate-500 text-[10px]">Severity</div>
                      <div className="font-mono text-slate-200">{selectedIncident.severity || "MEDIUM"}</div>
                    </div>
                  </div>

                  {/* Independent Analyst Radio Controls */}
                  <div className="space-y-2">
                    <label className="text-xs font-bold text-slate-300">Independent Analyst Determination:</label>
                    <div className="grid grid-cols-3 gap-2">
                      <button
                        type="button"
                        onClick={() => setAnalystVerdict("FALSE_POSITIVE")}
                        className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center justify-center gap-1 transition-colors ${
                          analystVerdict === "FALSE_POSITIVE"
                            ? "bg-emerald-950/60 border-emerald-600 text-emerald-300"
                            : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        FALSE POSITIVE
                        <span className="text-[9px] font-normal text-slate-500">Benign / Expected</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setAnalystVerdict("TRUE_POSITIVE")}
                        className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center justify-center gap-1 transition-colors ${
                          analystVerdict === "TRUE_POSITIVE"
                            ? "bg-rose-950/60 border-rose-600 text-rose-300"
                            : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        <AlertTriangle className="w-4 h-4 text-rose-400" />
                        TRUE POSITIVE
                        <span className="text-[9px] font-normal text-slate-500">Malicious / Attack</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => setAnalystVerdict("INSUFFICIENT_EVIDENCE")}
                        className={`p-2.5 rounded-lg border text-xs font-bold flex flex-col items-center justify-center gap-1 transition-colors ${
                          analystVerdict === "INSUFFICIENT_EVIDENCE"
                            ? "bg-amber-950/60 border-amber-600 text-amber-300"
                            : "bg-slate-950/40 border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        <HelpCircle className="w-4 h-4 text-amber-400" />
                        INCONCLUSIVE
                        <span className="text-[9px] font-normal text-slate-500">Missing Evidence</span>
                      </button>
                    </div>
                  </div>

                  {/* Analyst Notes & References */}
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-300">Analyst Investigation Notes &amp; Rationale:</label>
                    <textarea
                      value={analystNotes}
                      onChange={(e) => setAnalystNotes(e.target.value)}
                      placeholder="Explain findings, authorized change orders, or indicators observed..."
                      rows={2}
                      className="w-full p-2.5 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <button
                    onClick={handleSubmitReview}
                    disabled={submittingReview}
                    className="w-full py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                  >
                    {submittingReview ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    Submit Independent Review &amp; Reveal AI Comparison
                  </button>

                  {/* POST-SUBMISSION COMPARISON & REVEAL CARD */}
                  {revealedResult && (
                    <div className="mt-4 p-4 rounded-xl border border-cyan-800/60 bg-slate-950/90 space-y-3 animate-in fade-in duration-200">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                        <div className="flex items-center gap-2">
                          <Award className="w-4 h-4 text-cyan-400" />
                          <span className="text-xs font-bold text-slate-100">Comparison &amp; Agreement Outcome</span>
                        </div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono">
                          {revealedResult.comparison_outcome}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
                          <div className="text-[10px] uppercase font-bold text-slate-400">Analyst Ground Truth</div>
                          <div className="text-sm font-black text-cyan-300 mt-1">{revealedResult.analyst_verdict}</div>
                        </div>

                        <div className="p-2.5 rounded bg-slate-900/60 border border-slate-800">
                          <div className="text-[10px] uppercase font-bold text-slate-400">Revealed AI Verdict</div>
                          <div className="text-sm font-black text-purple-300 mt-1">
                            {revealedResult.revealed_ai_verdict || "NO_PREDICTION"}
                          </div>
                          {revealedResult.revealed_ai_confidence && (
                            <div className="text-[10px] text-slate-500 mt-0.5">
                              Confidence: {(revealedResult.revealed_ai_confidence * 100).toFixed(1)}%
                            </div>
                          )}
                        </div>
                      </div>

                      {revealedResult.disagreement_reason && (
                        <div className="p-2.5 rounded bg-rose-950/30 border border-rose-900/60 text-xs text-rose-300">
                          {revealedResult.disagreement_reason}
                        </div>
                      )}

                      {/* L2 Adjudication Controls if Disputed */}
                      {revealedResult.comparison_outcome === "DISPUTED" && (
                        <div className="p-3 rounded-lg border border-amber-900/40 bg-amber-950/20 space-y-2 text-xs">
                          <span className="font-bold text-amber-300">L2 Adjudication Required:</span>
                          <div className="flex items-center gap-2">
                            <select
                              value={adjudicationVerdict}
                              onChange={(e: any) => setAdjudicationVerdict(e.target.value)}
                              className="p-1.5 rounded border border-slate-800 bg-slate-900 text-xs text-slate-200"
                            >
                              <option value="FALSE_POSITIVE">Binding FALSE POSITIVE</option>
                              <option value="TRUE_POSITIVE">Binding TRUE POSITIVE</option>
                              <option value="INSUFFICIENT_EVIDENCE">Binding INSUFFICIENT EVIDENCE</option>
                            </select>
                            <input
                              type="text"
                              value={adjudicationRationale}
                              onChange={(e) => setAdjudicationRationale(e.target.value)}
                              placeholder="Adjudication rationale..."
                              className="flex-1 p-1.5 rounded border border-slate-800 bg-slate-900 text-xs text-slate-200"
                            />
                            <button
                              onClick={handleAdjudicateReview}
                              disabled={adjudicating}
                              className="px-3 py-1.5 rounded bg-amber-700 hover:bg-amber-600 text-slate-950 font-bold text-xs"
                            >
                              Adjudicate
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ) : (
                <div className="p-8 text-center text-slate-500 border border-slate-800 rounded-xl text-xs">
                  Select an incident from the queue to start double-blind review.
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* SUB-TAB 3: PRODUCTION PROMOTION & SAFETY */}
      {activeSubTab === "governance" && (
        <div className="space-y-4">
          {/* Formal Promotion Request Card */}
          <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 space-y-3">
            <h3 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <FileCheck2 className="w-4 h-4 text-cyan-400" />
              Formal Promotion Request
            </h3>
            <p className="text-[11px] text-slate-400">
              Submit an audited promotion request to advance this rule to Supervised Pilot or Controlled Production.
              Requires SOC Manager / Administrator dual-key approval.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="text-[10px] uppercase font-bold text-slate-400">Target Lifecycle Stage</label>
                <select
                  value={targetStage}
                  onChange={(e) => setTargetStage(e.target.value)}
                  className="w-full mt-1 p-2 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-200"
                >
                  <option value="VALIDATION">VALIDATION</option>
                  <option value="SUPERVISED_PILOT">SUPERVISED_PILOT</option>
                  <option value="CONTROLLED_PRODUCTION">CONTROLLED_PRODUCTION</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase font-bold text-slate-400">Simulation Run ID (Optional)</label>
                <input
                  type="text"
                  value={promotionRunId}
                  onChange={(e) => setPromotionRunId(e.target.value)}
                  placeholder="e.g. run-20261113-eval-01"
                  className="w-full mt-1 p-2 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-200"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400">Operational Justification</label>
              <textarea
                value={promotionJustification}
                onChange={(e) => setPromotionJustification(e.target.value)}
                placeholder="Provide rationale, verified sample validation, and change management reference..."
                rows={2}
                className="w-full mt-1 p-2 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-200"
              />
            </div>

            {!isPromotionTargetEligible && (
              <div className="p-2.5 rounded-lg bg-amber-950/40 border border-amber-800/80 text-amber-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-400" />
                <span>
                  {targetStage === "CONTROLLED_PRODUCTION"
                    ? `Rule is currently ineligible for CONTROLLED_PRODUCTION (${eligibilityReasons.length} requirements unsatisfied). See Production Eligibility checklist above.`
                    : `Supervised Pilot requires at least 30 verified analyst reviews (current: ${profile?.total_analyst_reviews || 0}/30).`}
                </span>
              </div>
            )}

            <button
              onClick={handleRequestPromotion}
              disabled={requestingPromotion || !isPromotionTargetEligible}
              title={!isPromotionTargetEligible ? "Prerequisites for requested target stage not satisfied" : "Submit Formal Promotion Request"}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-slate-100 font-bold text-xs flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              {requestingPromotion ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <FileCheck2 className="w-3.5 h-3.5" />}
              Submit Formal Promotion Request
            </button>
          </div>

          {/* Emergency Safety Controls */}
          <div className="p-4 rounded-xl border border-rose-900/40 bg-rose-950/10 space-y-3">
            <h3 className="text-xs font-bold text-rose-300 flex items-center gap-1.5">
              <AlertOctagon className="w-4 h-4 text-rose-400" />
              Emergency Safety Governance &amp; Global Kill-Switch
            </h3>
            <p className="text-[11px] text-slate-400">
              Immediately halts all automated incident closures across every detection rule. Fail-closed policy enforces
              that all incidents route directly to human analyst queues.
            </p>

            <button
              onClick={() => setKillSwitchModalOpen(true)}
              className="px-4 py-2 rounded-lg bg-rose-900/60 hover:bg-rose-900 text-rose-200 border border-rose-700 font-bold text-xs flex items-center gap-2 transition-colors"
            >
              <AlertOctagon className="w-4 h-4" />
              Engage Global Emergency Kill-Switch
            </button>
          </div>
        </div>
      )}

      {/* Emergency Kill-Switch Confirmation Modal */}
      {killSwitchModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-950 border border-rose-800 rounded-xl max-w-md w-full p-5 space-y-4 shadow-2xl">
            <div className="flex items-center gap-2 text-rose-400">
              <AlertOctagon className="w-6 h-6" />
              <h3 className="font-bold text-sm">ENGAGE GLOBAL EMERGENCY KILL-SWITCH</h3>
            </div>
            <p className="text-xs text-slate-300">
              This will immediately deactivate all autonomous incident closures on all detection rules. All incidents
              will revert to manual analyst review until cleared by SOC Leadership.
            </p>

            <div>
              <label className="text-[10px] uppercase font-bold text-slate-400">Emergency Reason (Mandatory):</label>
              <input
                type="text"
                value={killSwitchReason}
                onChange={(e) => setKillSwitchReason(e.target.value)}
                placeholder="e.g. Critical Missed True Positive detected in production"
                className="w-full mt-1 p-2 rounded-lg border border-slate-800 bg-slate-900 text-xs text-slate-200 focus:outline-none focus:border-rose-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setKillSwitchModalOpen(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleEngageKillSwitch}
                disabled={engagingKillSwitch || !killSwitchReason.trim()}
                className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition-colors disabled:opacity-50"
              >
                {engagingKillSwitch ? "Engaging..." : "Confirm Emergency Halt"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
