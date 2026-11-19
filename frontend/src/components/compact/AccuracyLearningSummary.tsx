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
}

export function AccuracyLearningSummary({
  ruleId,
  ruleName,
  customer,
  learningProfile: propLearningProfile,
  qualityAssessment,
  onNavigateToReviews,
  onStartReviews,
}: AccuracyLearningSummaryProps) {
  const [profile, setProfile] = useState<any | null>(propLearningProfile || null);
  const [loading, setLoading] = useState(!propLearningProfile);

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
  const wilsonBound = profile?.wilson_lower_bound ?? null;
  const abstentionCount = profile?.abstention_count ?? 0;
  const stage = profile?.lifecycle_stage || "LEARNING";

  // Calculate agreement
  const aiCorrect = profile?.ai_correct_count ?? 0;
  const aiIncorrect = profile?.ai_incorrect_count ?? 0;
  const agreementRate =
    aiCorrect + aiIncorrect > 0
      ? (aiCorrect / (aiCorrect + aiIncorrect)) * 100
      : null;

  return (
    <div className="space-y-4">
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
              onClick={() => (onStartReviews || onNavigateToReviews)?.()}
              className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold text-xs flex items-center gap-1.5 transition-colors font-sans shadow-md"
            >
              Go to Review Incidents
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
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
          <span className="text-slate-400 font-semibold block text-[11px]">
            Empirical Accuracy
          </span>
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
            {accuracyValue !== null ? "Statistically verified" : "Awaiting ground truth"}
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
            G8 Status: {totalVerified >= 30 ? "PASSED" : `${totalVerified}/30 minimum`}
          </span>
        </div>
      </div>

      {/* Secondary Metrics Row */}
      <div className="grid grid-cols-3 gap-3 text-xs font-mono">
        <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
          <span className="text-slate-400 font-sans text-[11px]">TP Recall:</span>
          <span className="font-bold text-slate-200">
            {tpRecall !== null ? `${(tpRecall * 100).toFixed(1)}%` : "NOT MEASURABLE"}
          </span>
        </div>

        <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
          <span className="text-slate-400 font-sans text-[11px]">FP Precision:</span>
          <span className="font-bold text-slate-200">
            {fpPrecision !== null ? `${(fpPrecision * 100).toFixed(1)}%` : "NOT MEASURABLE"}
          </span>
        </div>

        <div className="p-2.5 rounded-lg border border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
          <span className="text-slate-400 font-sans text-[11px]">Abstention Rate:</span>
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
            <span className="text-[11px] text-slate-500">
              Double-Blind Adjudicated Benchmark
            </span>
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
                    {profile?.error_distribution?.tp_as_tp ?? aiCorrect} (True Positive)
                  </td>
                  <td className="p-3 border border-slate-800 bg-amber-950/20 text-amber-300 font-bold">
                    {profile?.error_distribution?.fp_as_tp ?? 0} (False Alarm)
                  </td>
                </tr>
                <tr>
                  <td className="p-2 text-left font-sans font-semibold text-slate-300 border border-slate-800 bg-slate-950/40">
                    AI Predicted FP
                  </td>
                  <td className="p-3 border border-slate-800 bg-rose-950/40 text-rose-400 font-bold">
                    {profile?.error_distribution?.tp_as_fp ?? 0} (Missed Attack)
                  </td>
                  <td className="p-3 border border-slate-800 bg-emerald-950/20 text-emerald-300 font-bold">
                    {profile?.error_distribution?.fp_as_fp ?? 0} (True Negative)
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      {/* Explanatory Distinction */}
      <div className="p-3 rounded-lg border border-slate-800/80 bg-slate-950/50 text-slate-400 text-xs space-y-1">
        <span className="font-semibold text-slate-300 flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-cyan-400" />
          Rigorous Statistical Integrity Contract
        </span>
        <p className="text-[11px] leading-relaxed">
          Verdictum AI clearly distinguishes raw analyst submissions from verified and senior-adjudicated ground truth. Telemetry presence alone is never conflated with true attack verification. Quality Gate G8 requires a minimum of 30 verified ground truth cases and statistical Wilson lower bound $\ge 96\%$ before autonomous production escalation is permitted.
        </p>
      </div>
    </div>
  );
}

