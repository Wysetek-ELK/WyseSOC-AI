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
  Scale
} from "lucide-react";
import { api } from "@/lib/api";

interface RuleLearningDashboardProps {
  ruleId: string;
  ruleName?: string;
}

export function RuleLearningDashboard({ ruleId, ruleName }: RuleLearningDashboardProps) {
  const [profile, setProfile] = useState<any | null>(null);
  const [loading, setLoading] = useState(true);
  const [transitioning, setTransitioning] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const fetchProfile = async () => {
    if (!ruleId) return;
    setLoading(true);
    try {
      const data = await api.getRuleLearningProfileDetail(ruleId);
      setProfile(data);
    } catch (err: any) {
      console.error(err);
      setFeedback({ type: "error", text: err.message || "Failed to load learning profile" });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, [ruleId]);

  const handleTransition = async (newStage: string, reason: string) => {
    setTransitioning(true);
    setFeedback(null);
    try {
      await api.transitionRuleLifecycle(ruleId, newStage, reason);
      setFeedback({ type: "success", text: `Rule successfully transitioned to ${newStage}` });
      await fetchProfile();
    } catch (err: any) {
      setFeedback({ type: "error", text: err.message || "Transition failed" });
    } finally {
      setTransitioning(false);
    }
  };

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
      <div className="p-4 rounded-lg border border-slate-800 bg-slate-900/40 text-slate-400 text-xs text-center">
        No learning profile found for rule {ruleId}.
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
  };

  const currentColors = stageColorMap[stage] || stageColorMap.LEARNING;
  const isEligible = profile.is_production_eligible;
  const eligibilityReasons: string[] = profile.eligibility_reasons || [];

  return (
    <div className="space-y-4">
      {/* Top Banner: Stage & Feedback */}
      {feedback && (
        <div className={`p-2.5 rounded-lg border text-xs flex items-center justify-between ${
          feedback.type === "success" ? "bg-emerald-950/40 border-emerald-800 text-emerald-300" : "bg-rose-950/40 border-rose-800 text-rose-300"
        }`}>
          <span>{feedback.text}</span>
          <button onClick={() => setFeedback(null)} className="text-slate-400 hover:text-slate-200 text-xs">✕</button>
        </div>
      )}

      {/* Lifecycle Stage Header */}
      <div className={`p-3.5 rounded-xl border ${currentColors.border} ${currentColors.bg} flex flex-wrap items-center justify-between gap-3`}>
        <div className="flex items-center gap-3">
          <GitBranch className={`w-5 h-5 ${currentColors.text}`} />
          <div>
            <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Detection Rule Lifecycle Stage</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-base font-black ${currentColors.text}`}>{stage}</span>
              <span className="text-xs text-slate-400">• Tenant: {profile.customer}</span>
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
              disabled={transitioning}
              className="px-3 py-1.5 rounded-lg bg-amber-900/50 hover:bg-amber-800 text-amber-200 border border-amber-700 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
            >
              Advance to SUPERVISED PILOT
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

      {/* Production Eligibility Gating Checklist */}
      <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/40 space-y-2.5">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            Autonomous False-Positive Closure Eligibility Checklist
          </h3>
          <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
            isEligible
              ? "bg-emerald-950 text-emerald-300 border-emerald-800"
              : "bg-amber-950 text-amber-300 border-amber-800"
          }`}>
            {isEligible ? "QUALIFIED FOR PRODUCTION" : "INELIGIBLE (TRAINING REQUIRED)"}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
          <div className={`p-2 rounded border flex items-center justify-between ${
            profile.total_analyst_reviews >= 100
              ? "bg-emerald-950/20 border-emerald-900 text-emerald-300"
              : "bg-slate-950/40 border-slate-800 text-slate-400"
          }`}>
            <span>Verified Sample Size (≥100 reviews)</span>
            <span className="font-bold">{profile.total_analyst_reviews}/100</span>
          </div>

          <div className={`p-2 rounded border flex items-center justify-between ${
            (profile.fp_precision || 0) >= 0.98
              ? "bg-emerald-950/20 border-emerald-900 text-emerald-300"
              : "bg-slate-950/40 border-slate-800 text-slate-400"
          }`}>
            <span>Observed FP Precision (≥98.0%)</span>
            <span className="font-bold">{((profile.fp_precision || 0) * 100).toFixed(1)}%</span>
          </div>

          <div className={`p-2 rounded border flex items-center justify-between ${
            (profile.wilson_lower_bound || 0) >= 0.96
              ? "bg-emerald-950/20 border-emerald-900 text-emerald-300"
              : "bg-slate-950/40 border-slate-800 text-slate-400"
          }`}>
            <span>Wilson 95% Confidence Lower Bound (≥96.0%)</span>
            <span className="font-bold">{((profile.wilson_lower_bound || 0) * 100).toFixed(1)}%</span>
          </div>

          <div className={`p-2 rounded border flex items-center justify-between ${
            (profile.tp_recall || 0) >= 0.95
              ? "bg-emerald-950/20 border-emerald-900 text-emerald-300"
              : "bg-slate-950/40 border-slate-800 text-slate-400"
          }`}>
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
  );
}

