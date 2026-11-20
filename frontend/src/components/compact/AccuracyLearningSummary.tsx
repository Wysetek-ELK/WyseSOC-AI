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
} from "lucide-react";
import { api } from "@/lib/api";

interface AccuracyLearningSummaryProps {
  ruleId: string;
  ruleName?: string;
  customer?: string;
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
  learningProfile: propLearningProfile,
  qualityAssessment,
  onNavigateToReviews,
  onStartReviews,
  onNavigateToTest,
  onProfileUpdate,
}: AccuracyLearningSummaryProps) {
  const [profile, setProfile] = useState<any | null>(propLearningProfile || null);
  const [loading, setLoading] = useState(!propLearningProfile);
  const [evaluating, setEvaluating] = useState(false);
  const [evaluationFeedback, setEvaluationFeedback] = useState<{
    type: "success" | "warning" | "error";
    text: string;
  } | null>(null);

  const fetchProfile = async () => {
    if (!ruleId) return;
    if (propLearningProfile) {
      setProfile(propLearningProfile);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const data = await api.getRuleLearningProfileDetail(ruleId, customer);
      setProfile(data);
    } catch (err: any) {
      console.error("Failed to load learning profile for accuracy summary:", err);
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
      const freshProfile = await api.getRuleLearningProfileDetail(ruleId, customer);
      setProfile(freshProfile);
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
      setLoading(false);
    } else {
      fetchProfile();
    }
  }, [ruleId, propLearningProfile]);

  if (loading) {
    return (
      <div className="py-16 text-center text-slate-500 text-xs">
        <RefreshCw className="w-4 h-4 animate-spin mx-auto mb-2 text-cyan-400" />
        Loading empirical accuracy and learning verification data...
      </div>
    );
  }

  const verifiedTp = profile?.verified_tp_count ?? 0;
  const verifiedFp = profile?.verified_fp_count ?? 0;
  const totalVerified = verifiedTp + verifiedFp;
  const rawReviews = profile?.total_analyst_reviews ?? 0;

  const hasVerifiedLabels = totalVerified > 0;
  const accuracyValue = profile?.empirical_accuracy ?? null;
  const tpRecall = profile?.tp_recall ?? null;
  const fpPrecision = profile?.fp_precision ?? null;
  const tpPrecision = profile?.error_distribution?.tp_precision ?? null;
  const specificity = profile?.error_distribution?.specificity ?? null;
  const wilsonBound = profile?.wilson_lower_bound ?? null;
  const abstentionCount = profile?.abstention_count ?? 0;
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
                    el.classList.add("ring-2", "ring-cyan-500/80");
                    setTimeout(() => {
                      el.classList.remove("ring-2", "ring-cyan-500/80");
                    }, 1500);
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
      ) : accuracyValue === null ? (
        <div className="p-4 rounded-xl border border-cyan-800/60 bg-cyan-950/20 text-xs space-y-3">
          <div className="flex items-start gap-3">
            <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-cyan-300 text-sm">
                  Empirical Accuracy: NOT MEASURABLE (0 Decisive AI Predictions)
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-900/60 text-cyan-200">
                  DECISIVE PREDICTIONS NEEDED
                </span>
              </div>
              <p className="text-slate-300 text-xs leading-relaxed">
                While <strong>{totalVerified} verified ground truth reviews</strong> ({verifiedTp} TP / {verifiedFp} FP) are recorded in the database, <strong>0 decisive AI predictions</strong> (TP or FP) have been matched against them: {profile?.error_distribution?.analyst_resolved_abstention ?? 16} reviews resolved AI abstentions, and {profile?.error_distribution?.analyst_only_initial_benchmark ?? 15} were initial benchmarks without AI inference. Under Verdictum AI mathematical governance, Selective Accuracy measures AI decision correctness and requires decisive predictions.
              </p>
              {verifiedTp < 10 && (
                <div className="p-2 rounded bg-amber-950/40 border border-amber-800/60 text-amber-300 text-[11px] flex items-center gap-2 mt-2">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                  <span>
                    <strong>Pilot Class Balance Deficit:</strong> {verifiedTp}/10 True Positives confirmed. At least 10 TP cases and 10 FP cases are required for Supervised Pilot calibration baseline.
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="p-3 rounded-lg border border-cyan-900/80 bg-slate-950/80 flex flex-wrap items-center justify-between gap-3 font-mono">
            <div>
              <span className="text-slate-400 font-sans text-[11px] block">Next Recommended Action:</span>
              <span className="text-cyan-300 font-bold text-xs">
                {verifiedTp < 10 ? "Collect True Positive Reviews & Run Model Evaluation" : "Evaluate Accuracy Against Paired AI Predictions"}
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
                onClick={() => {
                  (onStartReviews || onNavigateToReviews)?.();
                  setTimeout(() => {
                    const el = document.getElementById("incident-review-workbench");
                    if (el) {
                      el.scrollIntoView({ behavior: "smooth", block: "start" });
                      el.classList.add("ring-2", "ring-cyan-500/80");
                      setTimeout(() => {
                        el.classList.remove("ring-2", "ring-cyan-500/80");
                      }, 1500);
                    }
                  }, 80);
                }}
                className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors font-sans shadow-md"
              >
                Review Queue
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Summary KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        {/* Card 1: Verified Ground Truth */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 space-y-1">
          <span className="text-slate-400 font-semibold block text-[11px]">
            Verified Ground Truth
          </span>
          <div className="flex items-baseline gap-2">
            <span className="text-xl font-bold font-mono text-cyan-300">
              {totalVerified}
            </span>
            <span className="text-[10px] text-slate-500 font-mono">
              ({verifiedTp} TP / {verifiedFp} FP)
            </span>
          </div>
          <span className="text-[10px] text-slate-500 block">
            From {rawReviews} total analyst review(s)
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
              className={`text-xl font-bold font-mono ${accuracyValue !== null ? "text-emerald-400" : "text-slate-500"
                }`}
            >
              {accuracyValue !== null ? `${(accuracyValue * 100).toFixed(1)}%` : "N/A"}
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
              className={`text-xl font-bold font-mono ${agreementRate !== null ? "text-cyan-300" : "text-slate-500"
                }`}
            >
              {agreementRate !== null ? `${agreementRate.toFixed(1)}%` : "N/A"}
            </span>
          </div>
          <span className="text-[10px] text-slate-500 block">
            {aiCorrect} agreed, {aiIncorrect} disagreed
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
            G8 Status: {g8StatusText}
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
            {abstentionCount} case(s)
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
                All {rawReviews} verified reviews in the database are currently non-decisive paired samples:{" "}
                <strong>{profile?.error_distribution?.analyst_resolved_abstention ?? 16}</strong> cases resolved AI abstentions, and{" "}
                <strong>{profile?.error_distribution?.analyst_only_initial_benchmark ?? 15}</strong> cases were initial baseline reviews where AI inference had not yet been run. Decisive cells (True Positive, True Negative, False Alarm, Missed Attack) populate only when a decisive model prediction (TP or FP) is compared against verified analyst ground truth.
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

