"use client";

import React, { useState, useEffect } from "react";
import {
  TrendingUp,
  Award,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  RefreshCw,
  Scale,
  Activity,
  Layers,
  ArrowRight,
  Shield,
  FileCheck2,
  Info,
  ShieldAlert,
  Cpu,
} from "lucide-react";
import { api, AisEvaluationSummary } from "@/lib/api";

interface AccuracyLearningSummaryProps {
  ruleId: string;
  ruleName?: string;
  customer?: string;
  selectedVersionId?: string;
  learningProfile?: any;
  qualityAssessment?: any;
  onNavigateToReviews?: () => void;
  onStartReviews?: () => void;
  onNavigateToTest?: () => void;
  onProfileUpdate?: (profile: any) => void;
}

export function AccuracyLearningSummary({
  ruleId,
  ruleName,
  customer = "DEFAULT",
  selectedVersionId,
  learningProfile: propLearningProfile,
  qualityAssessment,
  onNavigateToReviews,
  onStartReviews,
  onNavigateToTest,
  onProfileUpdate,
}: AccuracyLearningSummaryProps) {
  const [profile, setProfile] = useState<any | null>(propLearningProfile || null);
  const [evalSummary, setEvalSummary] = useState<AisEvaluationSummary | null>(null);
  const [loading, setLoading] = useState(!propLearningProfile);
  const [evaluating, setEvaluating] = useState(false);
  const [evaluationFeedback, setEvaluationFeedback] = useState<{
    type: "success" | "warning" | "error";
    text: string;
  } | null>(null);

  // Population Scope Selection: "current" (operational incident inventory) or "historical" (cumulative cohort)
  const [populationScope, setPopulationScope] = useState<"current" | "historical">("current");

  const fetchData = async () => {
    if (!ruleId) return;
    setLoading(true);
    try {
      const [profileData, evalStatusData] = await Promise.allSettled([
        propLearningProfile ? Promise.resolve(propLearningProfile) : api.getRuleLearningProfileDetail(ruleId, customer),
        api.getRuleEvaluationStatus(ruleId, { customer, policy_version_id: selectedVersionId }),
      ]);

      if (profileData.status === "fulfilled") {
        setProfile(profileData.value);
      }
      if (evalStatusData.status === "fulfilled") {
        setEvalSummary(evalStatusData.value.summary);
      }
    } catch (err: any) {
      console.error("Failed to load accuracy or evaluation tracking data:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleEvaluateAccuracy = async () => {
    if (!ruleId) return;
    setEvaluating(true);
    setEvaluationFeedback(null);
    try {
      const res = await api.evaluateRuleAccuracy(ruleId, customer);
      const [freshProfile, freshEvalStatus] = await Promise.all([
        api.getRuleLearningProfileDetail(ruleId, customer),
        api.getRuleEvaluationStatus(ruleId, { customer, policy_version_id: selectedVersionId }),
      ]);
      setProfile(freshProfile);
      setEvalSummary(freshEvalStatus.summary);
      onProfileUpdate?.(freshProfile);
      setEvaluationFeedback({
        type: res.empirical_accuracy !== null ? "success" : "warning",
        text: res.message || "Accuracy evaluation completed.",
      });
    } catch (err: any) {
      setEvaluationFeedback({
        type: "error",
        text: err.message || "Failed to evaluate rule accuracy",
      });
    } finally {
      setEvaluating(false);
    }
  };

  useEffect(() => {
    if (propLearningProfile) {
      setProfile(propLearningProfile);
    }
    fetchData();
  }, [ruleId, selectedVersionId, propLearningProfile]);

  if (loading) {
    return (
      <div className="py-16 text-center text-slate-500 text-xs">
        <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2 text-cyan-400" />
        Loading empirical accuracy and evaluation tracking reconciliation data...
      </div>
    );
  }

  // --- Authoritative Population Scope Metrics ---
  const isCurrentScope = populationScope === "current";

  // Current scope metrics (Current Incident Inventory: dynamic from evaluation summary)
  const currentTotal = evalSummary?.current_inventory?.verified_reviews ?? evalSummary?.matched_verified_reviews ?? evalSummary?.total_incidents ?? 0;
  const currentTp = evalSummary?.current_inventory?.verified_tp ?? evalSummary?.verified_tp_count ?? 0;
  const currentFp = evalSummary?.current_inventory?.verified_fp ?? evalSummary?.verified_fp_count ?? Math.max(0, currentTotal - currentTp);
  const currentAbstained = evalSummary?.current_inventory?.abstained ?? evalSummary?.abstained ?? 0;
  const currentMissing = evalSummary?.current_inventory?.missing_evaluations_among_reviewed ?? evalSummary?.missing_evaluations_among_reviewed ?? 0;
  const currentDecisive = evalSummary?.current_inventory?.evaluated_decisive ?? evalSummary?.evaluated_decisive ?? 0;
  const currentRejected = evalSummary?.current_inventory?.validation_rejected ?? evalSummary?.validation_rejected ?? 0;
  const currentFailed = evalSummary?.current_inventory?.failed ?? evalSummary?.evaluation_failed ?? 0;

  // Historical scope metrics (Cumulative Historical Ground Truth: dynamic from learning profile)
  const histTotal = profile?.total_analyst_reviews ?? evalSummary?.historical_cohort?.total_reviews ?? 0;
  const histTp = profile?.verified_tp_count ?? evalSummary?.historical_cohort?.verified_tp ?? 0;
  const histFp = profile?.verified_fp_count ?? evalSummary?.historical_cohort?.verified_fp ?? Math.max(0, histTotal - histTp);
  const histAbstained = profile?.error_distribution?.analyst_resolved_abstention ?? evalSummary?.historical_cohort?.abstained ?? 0;
  const histMissing = profile?.error_distribution?.analyst_only_initial_benchmark ?? evalSummary?.historical_cohort?.initial_benchmarks_missing_inference ?? 0;
  const histDecisive = profile?.error_distribution?.decisive_evaluations ?? evalSummary?.historical_cohort?.decisive ?? 0;
  const histRejected = evalSummary?.validation_rejected ?? 0;
  const histFailed = evalSummary?.evaluation_failed ?? 0;

  // Active Scope Selected Values: STRICT GUARANTEE: totalVerified = verifiedTp + verifiedFp
  const totalVerified = isCurrentScope ? currentTotal : histTotal;
  const verifiedTp = isCurrentScope ? currentTp : histTp;
  const verifiedFp = isCurrentScope ? currentFp : histFp;
  const abstainedCount = isCurrentScope ? currentAbstained : histAbstained;
  const missingInferenceCount = isCurrentScope ? currentMissing : histMissing;
  const decisiveEvaluations = isCurrentScope ? currentDecisive : histDecisive;
  const validationRejectedCount = isCurrentScope ? currentRejected : histRejected;
  const evaluationFailedCount = isCurrentScope ? currentFailed : histFailed;
  const matchedRealAiCount = decisiveEvaluations + abstainedCount + validationRejectedCount;
  const rawReviews = totalVerified;
  const scopeLabel = isCurrentScope ? "Current Incident Inventory" : "Cumulative Historical Cohort";

  const hasVerifiedLabels = totalVerified > 0;
  const accuracyValue = isCurrentScope ? (evalSummary?.selective_accuracy ?? null) : (profile?.empirical_accuracy ?? null);
  const tpRecall = isCurrentScope ? (evalSummary?.tp_recall ?? null) : (profile?.tp_recall ?? null);
  const fpPrecision = isCurrentScope ? (evalSummary?.fp_precision ?? null) : (profile?.fp_precision ?? null);
  const specificity = isCurrentScope ? (evalSummary?.specificity ?? null) : (profile?.error_distribution?.specificity ?? null);
  const wilsonBound = isCurrentScope ? (evalSummary?.wilson_lower_bound ?? null) : (profile?.wilson_lower_bound ?? null);
  const stage = profile?.lifecycle_stage || "LEARNING";

  // Authoritative G8 Multi-Tier Evaluation Status
  const g8StatusText =
    totalVerified === 0
      ? "UNCALIBRATED (0/5 Cases)"
      : totalVerified < 30
      ? `EXPLORATORY (${totalVerified}/30 Pilot)`
      : totalVerified < 100
      ? `SUPERVISED PILOT (${totalVerified}/100 Prod)`
      : "PRODUCTION ELIGIBLE";

  // Calculate agreement
  const aiCorrect = profile?.ai_correct_count ?? 0;
  const aiIncorrect = profile?.ai_incorrect_count ?? 0;
  const agreementRate =
    aiCorrect + aiIncorrect > 0
      ? (aiCorrect / (aiCorrect + aiIncorrect)) * 100
      : null;

  return (
    <div className="space-y-4">
      {/* Feedback Banner if Evaluate was clicked */}
      {evaluationFeedback && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
            evaluationFeedback.type === "success"
              ? "bg-emerald-950/40 border-emerald-800 text-emerald-300"
              : evaluationFeedback.type === "warning"
              ? "bg-amber-950/40 border-amber-800 text-amber-300"
              : "bg-rose-950/40 border-rose-800 text-rose-300"
          }`}
        >
          <span>{evaluationFeedback.text}</span>
          <button
            onClick={() => setEvaluationFeedback(null)}
            className="text-slate-400 hover:text-slate-200 font-bold ml-2"
          >
            ×
          </button>
        </div>
      )}

      {/* Top Banner: Condition check if accuracy is measurable */}
      {!hasVerifiedLabels ? (
        <div className="p-4 rounded-xl border border-amber-800/60 bg-amber-950/20 text-xs space-y-3">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-amber-300 text-sm">
                  Accuracy: NOT MEASURABLE
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-900/60 text-amber-200">
                  ZERO GROUND TRUTH LABELS
                </span>
              </div>
              <p className="text-slate-300 text-xs leading-relaxed">
                Objective empirical accuracy cannot be computed until independent double-blind analyst determinations are recorded on real telemetry samples. Antigravity strictly suppresses fabricated 100% scores and empty charts.
              </p>
            </div>
          </div>

          <div className="p-3 rounded-lg border border-amber-900/80 bg-slate-950/80 flex flex-wrap items-center justify-between gap-3 font-mono">
            <div>
              <span className="text-slate-400 font-sans text-[11px] block">Next Recommended Action:</span>
              <span className="text-cyan-300 font-bold text-xs">
                Begin Independent Analyst Reviews
              </span>
            </div>

            <button
              onClick={() => {
                (onStartReviews || onNavigateToReviews)?.();
                setTimeout(() => {
                  const el = document.getElementById("incident-review-workbench");
                  if (el) {
                    el.scrollIntoView({ behavior: "smooth", block: "start" });
                  }
                }, 80);
              }}
              className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors font-sans shadow-md"
            >
              Go to Review Incidents
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      ) : decisiveEvaluations === 0 || accuracyValue === null ? (
        <div className="p-4 rounded-xl border border-cyan-800/60 bg-cyan-950/20 text-xs space-y-3">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
            <div className="space-y-2 flex-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-cyan-300 text-sm">
                  Empirical Accuracy: NOT MEASURABLE (0 Decisive AI Predictions)
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-900/60 text-cyan-200">
                  DECISIVE PREDICTIONS NEEDED
                </span>
              </div>

              <p className="text-xs font-semibold text-slate-200">
                Accuracy Not Measurable — No eligible decisive AI predictions are matched to verified analyst verdicts.
              </p>

              {/* Scope Selector Control */}
              <div className="flex flex-wrap items-center gap-2 pt-1 pb-1">
                <span className="text-[11px] text-slate-400 font-sans">Active Population Scope:</span>
                <div className="inline-flex rounded-lg border border-slate-800 bg-slate-950/90 p-0.5 text-[11px]">
                  <button
                    onClick={() => setPopulationScope("current")}
                    className={`px-2.5 py-1 rounded font-medium transition-colors ${
                      isCurrentScope
                        ? "bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Current Incident Inventory ({currentTotal})
                  </button>
                  <button
                    onClick={() => setPopulationScope("historical")}
                    className={`px-2.5 py-1 rounded font-medium transition-colors ${
                      !isCurrentScope
                        ? "bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    Cumulative Historical Cohort ({histTotal})
                  </button>
                </div>
              </div>

              <div className="text-slate-300 text-xs leading-relaxed space-y-1.5">
                <p>
                  Objective empirical accuracy is mathematically undefined because <strong>0 eligible decisive AI predictions (TP or FP)</strong> exist to pair against verified analyst ground truth:
                </p>
                <ul className="list-disc pl-5 space-y-0.5 text-slate-300 font-mono text-[11px]">
                  <li><strong>{totalVerified} analyst ground-truth reviews</strong> exist in the {scopeLabel} ({verifiedTp} TP / {verifiedFp} FP).</li>
                  <li><strong>{abstainedCount} reviews</strong> resolved AI abstentions (<code className="text-amber-300">REQUIRES_ATTENTION</code>).</li>
                  <li><strong>{missingInferenceCount} reviews</strong> represent initial benchmarks without stored AI inference.</li>
                  <li><strong>0 decisive AI predictions</strong> (TP or FP) are available for comparison.</li>
                </ul>
                <p className="text-[11px] text-slate-400 font-sans pt-1">
                  Under Verdictum AI mathematical governance, Selective Accuracy measures AI decision correctness and requires decisive predictions. Abstentions safely defer to human analysts and are excluded from the accuracy denominator.
                </p>
              </div>

              {/* Explicit One-Class Dataset & Pilot Class Balance Deficit Notice */}
              <div className="p-3 rounded-lg bg-amber-950/40 border border-amber-800/80 text-amber-200 text-xs space-y-1 mt-2">
                <div className="flex items-center gap-2 font-bold">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <span>One-Class Dataset &amp; Pilot Class Balance Deficit:</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  One-Class Dataset — Verified FP performance can be evaluated, but TP recall and two-class certification require genuine TP cases.
                </p>
                <p className="text-[11px] text-amber-300/80">
                  Current verified ground truth contains <strong>{verifiedFp} False Positives (100%)</strong> and <strong>{verifiedTp} True Positives (0%)</strong>. Supervised Pilot baseline calibration requires at least <strong>10 True Positive</strong> and <strong>10 False Positive</strong> verified cases to establish representative statistical significance.
                </p>
              </div>
            </div>
          </div>

          <div className="p-3 rounded-lg border border-cyan-900/80 bg-slate-950/80 flex flex-wrap items-center justify-between gap-3 font-mono">
            <div>
              <span className="text-slate-400 font-sans text-[11px] block">Next Recommended Action:</span>
              <span className="text-cyan-300 font-bold text-xs">
                {missingInferenceCount > 0
                  ? `Run Controlled Batch Inference on ${missingInferenceCount} Missing Incidents`
                  : "Collect True Positive Reviews & Re-evaluate"}
              </span>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={handleEvaluateAccuracy}
                disabled={evaluating}
                className="px-3.5 py-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors font-sans shadow-md"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${evaluating ? "animate-spin" : ""}`} />
                {evaluating ? "Evaluating..." : "Evaluate Accuracy"}
              </button>

              <button
                onClick={onNavigateToTest}
                className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors font-sans shadow-md"
              >
                Go to Test AI
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Comprehensive AI Evaluation Tracking & Coverage Breakdown Grid */}
      <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/70 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <h3 className="font-bold text-slate-200 text-xs">
              AI Evaluation Tracking &amp; Decision Coverage Breakdown
            </h3>
          </div>
          <span className="text-[11px] text-cyan-400 font-mono">
            Scope: {scopeLabel}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-2.5 text-xs font-mono">
          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 font-sans block text-[10px] mb-1">Total Reviewed:</span>
            <span className="font-bold text-slate-100 text-sm">{totalVerified}</span>
            <span className="text-[10px] text-slate-500 block font-sans">Incidents</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 font-sans block text-[10px] mb-1">Matched Real AI:</span>
            <span className="font-bold text-cyan-300 text-sm">{matchedRealAiCount}</span>
            <span className="text-[10px] text-slate-500 block font-sans">Real GPU Inferences</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 font-sans block text-[10px] mb-1">Decisive Verdicts:</span>
            <span className={`font-bold text-sm ${decisiveEvaluations > 0 ? "text-emerald-400" : "text-slate-500"}`}>
              {decisiveEvaluations}
            </span>
            <span className="text-[10px] text-slate-500 block font-sans">TP or FP</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 font-sans block text-[10px] mb-1">AI Abstentions:</span>
            <span className="font-bold text-amber-400 text-sm">{abstainedCount}</span>
            <span className="text-[10px] text-slate-500 block font-sans">Requires Attention</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 font-sans block text-[10px] mb-1">Validation Rejected:</span>
            <span className={`font-bold text-sm ${validationRejectedCount > 0 ? "text-rose-400" : "text-slate-500"}`}>
              {validationRejectedCount}
            </span>
            <span className="text-[10px] text-slate-500 block font-sans">Schema/Grounding</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 font-sans block text-[10px] mb-1">Missing AI Inference:</span>
            <span className="font-bold text-amber-300 text-sm">{missingInferenceCount}</span>
            <span className="text-[10px] text-slate-500 block font-sans">Unexecuted</span>
          </div>

          <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800">
            <span className="text-slate-400 font-sans block text-[10px] mb-1">Failed Runs:</span>
            <span className={`font-bold text-sm ${evaluationFailedCount > 0 ? "text-rose-400" : "text-slate-500"}`}>
              {evaluationFailedCount}
            </span>
            <span className="text-[10px] text-slate-500 block font-sans">Timeouts/Errors</span>
          </div>
        </div>
      </div>

      {/* Summary KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        {/* Card 1: Verified Ground Truth */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-semibold block text-[11px]">
              Verified Ground Truth
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-cyan-300">
              {isCurrentScope ? "Current Queue" : "Historical"}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono text-cyan-300">
              {totalVerified}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              ({verifiedTp} TP / {verifiedFp} FP)
            </span>
          </div>
          <span className="text-[10px] text-slate-500 block">
            {isCurrentScope ? `${currentTotal} operational incidents in queue` : `${histTotal} cumulative reviewed cases in profile`}
          </span>
        </div>

        {/* Card 2: Empirical Accuracy */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 font-semibold block text-[11px]">
              Empirical Accuracy
            </span>
            <button
              onClick={handleEvaluateAccuracy}
              disabled={evaluating}
              title="Click to evaluate empirical accuracy from paired analyst ground truth"
              className="text-[10px] text-cyan-400 hover:text-cyan-300 font-sans flex items-center gap-1 cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-2.5 h-2.5 ${evaluating ? "animate-spin" : ""}`} />
              Re-evaluate
            </button>
          </div>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-xl font-bold font-mono ${
                accuracyValue !== null ? "text-emerald-400" : "text-slate-400 text-sm"
              }`}
            >
              {accuracyValue !== null ? `${(accuracyValue * 100).toFixed(1)}%` : "NOT MEASURABLE"}
            </span>
            {wilsonBound !== null && (
              <span className="text-[10px] text-slate-500 font-mono">
                (Wilson: {(wilsonBound * 100).toFixed(0)}%)
              </span>
            )}
          </div>
          <span className="text-[10px] text-slate-500 block">
            {accuracyValue !== null ? "Statistically verified" : "Awaiting decisive predictions"}
          </span>
        </div>

        {/* Card 3: AI / Analyst Agreement */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-1">
          <span className="text-slate-400 font-semibold block text-[11px]">
            AI / Analyst Agreement
          </span>
          <div className="flex items-baseline gap-2">
            <span
              className={`text-xl font-bold font-mono ${
                agreementRate !== null ? "text-cyan-300" : "text-slate-400 text-sm"
              }`}
            >
              {agreementRate !== null ? `${agreementRate.toFixed(1)}%` : "NOT MEASURABLE"}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 block">
            {decisiveEvaluations > 0 ? `${aiCorrect} agreed, ${aiIncorrect} disagreed` : "0 decisive comparison pairs"}
          </span>
        </div>

        {/* Card 4: Learning Readiness (G8) */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-1">
          <span className="text-slate-400 font-semibold block text-[11px]">
            Learning Lifecycle &amp; G8
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-sm font-bold font-mono text-indigo-300">
              {stage}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 block">
            G8 Status: {g8StatusText} (0/10 TP Pilot Deficit)
          </span>
        </div>
      </div>

      {/* Secondary Metrics Grid: Full Decisive Diagnostic Spectrum */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 text-xs font-mono">
        <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between" title="Sensitivity: TP / (TP + FN)">
          <span className="text-slate-400 font-sans text-[11px]">TP Recall:</span>
          <span className="font-bold text-slate-200">
            {tpRecall !== null ? `${(tpRecall * 100).toFixed(1)}%` : "NOT MEASURABLE"}
          </span>
        </div>

        <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between" title="FP Precision: TN / (TN + FN)">
          <span className="text-slate-400 font-sans text-[11px]">FP Precision:</span>
          <span className="font-bold text-slate-200">
            {fpPrecision !== null ? `${(fpPrecision * 100).toFixed(1)}%` : "NOT MEASURABLE"}
          </span>
        </div>

        <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between" title="True Negative Rate: TN / (TN + FP)">
          <span className="text-slate-400 font-sans text-[11px]">Specificity:</span>
          <span className="font-bold text-slate-200">
            {specificity !== null ? `${(specificity * 100).toFixed(1)}%` : "NOT MEASURABLE"}
          </span>
        </div>

        <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between" title="Abstentions requiring human analyst review">
          <span className="text-slate-400 font-sans text-[11px]">Abstentions:</span>
          <span className="font-bold text-slate-200">
            {abstainedCount} case(s)
          </span>
        </div>
      </div>

      {/* Simple Confusion Matrix (Displayed only when verified ground truth exists) */}
      {hasVerifiedLabels ? (
        <div className="p-4 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <span className="font-bold text-slate-200 text-xs flex items-center gap-2">
              <Scale className="w-4 h-4 text-cyan-400" />
              Verified Confusion Matrix
            </span>
            <div className="flex items-center gap-3">
              <span className="text-[11px] text-slate-500 hidden sm:inline">
                Double-Blind Adjudicated Benchmark
              </span>
              <button
                onClick={handleEvaluateAccuracy}
                disabled={evaluating}
                className="px-2.5 py-1 rounded-lg bg-teal-600/30 hover:bg-teal-600/50 border border-teal-500/50 text-teal-300 text-[11px] font-sans font-bold flex items-center gap-1 transition-colors cursor-pointer disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${evaluating ? "animate-spin" : ""}`} />
                {evaluating ? "Evaluating..." : "Evaluate Accuracy"}
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-center text-xs font-mono border-collapse">
              <thead>
                <tr className="text-slate-400 text-[11px]">
                  <th className="p-2 text-left font-sans">AI Determination \ Verified</th>
                  <th className="p-2 bg-slate-950/60 border border-slate-800 text-rose-300">
                    Verified True Positive
                  </th>
                  <th className="p-2 bg-slate-950/60 border border-slate-800 text-emerald-300">
                    Verified False Positive
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="p-2 text-left font-sans font-semibold text-slate-300 border border-slate-800 bg-slate-950/40">
                    AI Predicted TP
                  </td>
                  <td className="p-3 border border-slate-800 bg-rose-950/20 text-rose-300 font-bold">
                    {profile?.error_distribution?.tp ?? profile?.error_distribution?.tp_as_tp ?? profile?.error_distribution?.agreement_tp ?? aiCorrect} (True Positive)
                  </td>
                  <td className="p-3 border border-slate-800 bg-amber-950/20 text-amber-300 font-bold">
                    {profile?.error_distribution?.fp ?? profile?.error_distribution?.fp_as_tp ?? profile?.error_distribution?.ai_false_alarm ?? 0} (False Alarm)
                  </td>
                </tr>
                <tr>
                  <td className="p-2 text-left font-sans font-semibold text-slate-300 border border-slate-800 bg-slate-950/40">
                    AI Predicted FP
                  </td>
                  <td className="p-3 border border-slate-800 bg-rose-950/40 text-rose-400 font-bold">
                    {profile?.error_distribution?.fn ?? profile?.error_distribution?.tp_as_fp ?? profile?.error_distribution?.critical_missed_tp ?? 0} (Missed Attack)
                  </td>
                  <td className="p-3 border border-slate-800 bg-emerald-950/20 text-emerald-300 font-bold">
                    {profile?.error_distribution?.tn ?? profile?.error_distribution?.fp_as_fp ?? profile?.error_distribution?.agreement_fp ?? 0} (True Negative)
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {totalVerified > 0 && accuracyValue === null && (
            <div className="mt-2 p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div className="flex items-center gap-2 text-cyan-400 font-semibold">
                <Info className="w-3.5 h-3.5" />
                <span>Why is the confusion matrix currently zero?</span>
              </div>
              <p className="text-[11px] leading-relaxed">
                All {totalVerified} verified reviews in the database are currently non-decisive paired samples:{" "}
                <strong>{abstainedCount}</strong> cases resolved AI abstentions (<code className="text-amber-300">analyst_resolved_abstention</code>), and{" "}
                <strong>{missingInferenceCount}</strong> cases were initial baseline reviews (<code className="text-cyan-300">analyst_only_initial_benchmark</code>) where AI inference had not yet been run. Decisive cells (True Positive, True Negative, False Alarm, Missed Attack) populate only when a decisive model prediction (TP or FP) is compared against verified analyst ground truth.
              </p>
            </div>
          )}
        </div>
      ) : null}

      {/* Explanatory Distinction */}
      <div className="p-3 rounded-lg border border-slate-800/80 bg-slate-950/50 text-slate-400 text-xs space-y-1">
        <span className="font-semibold text-slate-300 flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-cyan-400" />
          Authoritative Three-Tier Governance Contract
        </span>
        <p className="text-[11px] leading-relaxed">
          Verdictum AI enforces 3 distinct evaluation tiers: <strong>Tier 1 Exploratory</strong> (&ge;5 verified cases, exploratory diagnostics); <strong>Tier 2 Supervised Pilot</strong> (&ge;30 verified cases with &ge;10 TP and &ge;10 FP, &ge;90% accuracy); and <strong>Tier 3 Production Certification</strong> (&ge;100 verified cases, &ge;25 TP, &ge;50 FP, Empirical Accuracy &ge;95.0%, FP-Class Precision &ge;99.0%, Wilson 95% Lower Bound &ge;96.0%, TP Recall &ge;95.0%, and 0 Critical Missed TPs). Production automation remains strictly disabled until Tier 3 criteria and human approval are met.
        </p>
      </div>
    </div>
  );
}
