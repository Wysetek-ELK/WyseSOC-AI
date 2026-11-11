"use client";

import React from "react";
import Link from "next/link";
import {
  ShieldAlert,
  Gauge,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  ExternalLink,
  Scale,
  ShieldCheck,
} from "lucide-react";
import { WorkflowFlowDiagram } from "./WorkflowFlowDiagram";
import {
  DECISION_EDGES,
  DECISION_STEPS,
  DECISION_SWIMLANES,
} from "@/data/admin-guide/decisionFlowData";
import {
  DETERMINISTIC_GUARDRAILS,
  EVIDENCE_SUFFICIENCY_DIMENSIONS,
  TRUSTWORTHINESS_DIMENSIONS,
  TRUST_SCORE_BANDS,
} from "@/data/admin-guide/studioGuideData";
import { GlossaryTerm } from "./GlossaryTerm";

interface DecisionEngineSectionProps {
  onJumpToGlossary?: (termId: string) => void;
  initialStepId?: string;
  jumpNonce?: number;
}

export function DecisionEngineSection({
  onJumpToGlossary,
  initialStepId,
  jumpNonce = 0,
}: DecisionEngineSectionProps) {
  return (
    <div className="space-y-5">
      {/* Separate Animated Decision Workflow */}
      <WorkflowFlowDiagram
        title="Verdictum AI Decision Engine — Animated Runtime Decision Flow"
        subtitle="New Incident → Rule Match → Approved Policy → Evidence Validation → Local LLM → Deterministic Guardrails → Trustworthiness Score → Three-State Verdict"
        steps={DECISION_STEPS}
        edges={DECISION_EDGES}
        swimlanes={DECISION_SWIMLANES}
        initialStepId={initialStepId}
        jumpNonce={jumpNonce}
      />

      {/* Explicit Calibration vs Raw LLM Confidence Guardrail Callout */}
      <div className="rounded-xl border border-indigo-500/40 bg-indigo-950/20 p-3.5 flex items-start gap-3">
        <Scale className="h-4 w-4 text-indigo-300 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <div className="font-bold text-indigo-200">
            Calibration Integrity Rule: LLM Confidence Is NOT Calibrated Probability
          </div>
          <p className="text-[11px] text-indigo-200/85 leading-relaxed">
            The raw 0–100 confidence returned by the Local LLM is treated strictly as an{" "}
            <GlossaryTerm termId="raw-llm-confidence" onJumpToGlossary={onJumpToGlossary}>
              uncalibrated subjective model score
            </GlossaryTerm>
            . Calibrated probabilities,{" "}
            <GlossaryTerm termId="brier-ece" onJumpToGlossary={onJumpToGlossary}>
              Brier Score, and Expected Calibration Error (ECE across 5 bins)
            </GlossaryTerm>{" "}
            are reported only after{" "}
            <code className="px-1 py-0.5 rounded bg-slate-900 font-mono text-indigo-300">
              CalibrationEvaluator
            </code>{" "}
            verifies at least <strong className="text-slate-100">N &ge; 30</strong> decisive, human-verified evaluations with balanced representation (&ge; 3 TP and &ge; 3 FP). Until then, status remains{" "}
            <code className="px-1 py-0.5 rounded bg-slate-900 font-mono text-amber-300">
              NOT_CALIBRATED
            </code>{" "}
            and ordinal Trust Scores are strictly capped at <strong className="text-amber-300">&le; 6/10</strong>.
          </p>
        </div>
      </div>

      {/* Three Outcomes Comparison */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="rounded-xl border border-rose-800/60 bg-rose-950/15 p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="rounded bg-rose-950/90 border border-rose-700/70 px-2 py-0.5 text-[10px] font-mono font-bold text-rose-300">
              TRUE_POSITIVE
            </span>
            <XCircle className="h-4 w-4 text-rose-400" />
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed">
            Confirmed unauthorized or malicious activity supported by grounded{" "}
            <code className="font-mono text-rose-200">OBSERVED_FACT</code> claims,{" "}
            <code className="font-mono">SUFFICIENT</code> mandatory telemetry, calibrated Trust Score &ge; 7/10, and zero guardrail triggers. Alert firing alone never proves TP (Guardrail G7).
          </p>
        </div>

        <div className="rounded-xl border border-emerald-800/60 bg-emerald-950/15 p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="rounded bg-emerald-950/90 border border-emerald-700/70 px-2 py-0.5 text-[10px] font-mono font-bold text-emerald-300">
              FALSE_POSITIVE
            </span>
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed">
            Confirmed authorized or benign activity backed by affirmative, grounded operational proof (e.g. verified vulnerability scanner, approved change ticket, authorized backup). Private RFC-1918 IPs or lack of malware never prove FP alone (Guardrail G6).
          </p>
        </div>

        <div className="rounded-xl border border-amber-800/60 bg-amber-950/15 p-3.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="rounded bg-amber-950/90 border border-amber-700/70 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-300">
              REQUIRES_ANALYST_ATTENTION
            </span>
            <AlertTriangle className="h-4 w-4 text-amber-400" />
          </div>
          <p className="text-[11px] text-slate-300 leading-relaxed">
            Safe{" "}
            <GlossaryTerm termId="abstention" onJumpToGlossary={onJumpToGlossary}>
              abstention
            </GlossaryTerm>{" "}
            emitted whenever mandatory Evidence Contract fields are absent, telemetry conflicts, LLM claims are ungrounded, authorization context is missing, policy is unapproved, or Trust Score &lt; 7/10.
          </p>
        </div>
      </div>

      {/* Evidence Confidence Engine & Verdict Trustworthiness Engine */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Evidence Sufficiency Engine */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-cyan-400" />
                Evidence Confidence Engine (EvidenceSufficiencyEngine)
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Scores telemetry sufficiency from 0–100 across 4 deterministic weights.
              </p>
            </div>
            <span className="rounded bg-cyan-950/70 border border-cyan-800/60 px-2 py-0.5 text-[10px] font-mono text-cyan-300">
              Threshold: &ge; 70.0
            </span>
          </div>

          <div className="space-y-2">
            {EVIDENCE_SUFFICIENCY_DIMENSIONS.map((dim) => (
              <div
                key={dim.name}
                className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5 flex items-start justify-between gap-3"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-100">{dim.name}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{dim.description}</div>
                </div>
                <span className="shrink-0 rounded bg-slate-950 border border-slate-700 px-2 py-0.5 text-[10px] font-mono font-bold text-cyan-300">
                  {dim.weight}
                </span>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-rose-800/60 bg-rose-950/20 p-2.5 text-[11px] text-rose-200">
            <strong className="text-rose-300">
              <GlossaryTerm termId="infallible-rule" onJumpToGlossary={onJumpToGlossary}>
                Infallible Rule
              </GlossaryTerm>
              :
            </strong>{" "}
            If any mandatory field is missing or a material contradiction exists, overall sufficiency is capped at <strong className="font-mono">&le; 49.0</strong>, status becomes <code className="font-mono">INSUFFICIENT</code> or <code className="font-mono">CONFLICTING</code>, and automated TP/FP is strictly blocked.
          </div>
        </div>

        {/* Verdict Trustworthiness Engine */}
        <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Gauge className="h-4 w-4 text-amber-400" />
                Verdict Trustworthiness Engine (v2.2.0)
              </h3>
              <p className="text-[11px] text-slate-400 mt-0.5">
                5 transparent dimensions (100 raw pts) normalized to a 1–10 ordinal Trust Score.
              </p>
            </div>
            <Link
              href="/verdict-intelligence"
              className="text-[10px] font-semibold text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1"
            >
              Verdict Intelligence <ExternalLink className="h-2.5 w-2.5" />
            </Link>
          </div>

          <div className="space-y-2">
            {TRUSTWORTHINESS_DIMENSIONS.map((dim) => (
              <div
                key={dim.name}
                className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5 flex items-start justify-between gap-3"
              >
                <div>
                  <div className="text-xs font-semibold text-slate-100">{dim.name}</div>
                  <div className="text-[11px] text-slate-400 mt-0.5">{dim.description}</div>
                </div>
                <span className="shrink-0 rounded bg-slate-950 border border-slate-700 px-2 py-0.5 text-[10px] font-mono font-bold text-amber-300">
                  Max {dim.maxPoints}
                </span>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-amber-800/60 bg-amber-950/20 p-2.5 text-[11px] text-amber-200 space-y-1">
            <div>
              <strong className="text-amber-300">Mandatory Trust Caps:</strong> Uncalibrated rules (N &lt; 30) cap at <code className="font-mono">6/10</code>; missing mandatory evidence or conflicts cap at <code className="font-mono">3/10</code>; empty telemetry returns <code className="font-mono">NOT_CALCULABLE</code>.
            </div>
          </div>
        </div>
      </div>

      {/* Ordinal Trust Scale + Guardrails G1-G7 */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-2.5">
          <h3 className="text-sm font-bold text-slate-100">1–10 Ordinal Trust Score Mapping</h3>
          <div className="space-y-1.5">
            {TRUST_SCORE_BANDS.map((b) => (
              <div
                key={b.range}
                className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 text-[11px]"
              >
                <div className="flex items-center justify-between font-mono">
                  <span className="font-bold text-cyan-300">Score {b.range}/10</span>
                  <span className="text-slate-400">{b.raw} · {b.label}</span>
                </div>
                <div className="text-slate-300 mt-0.5">{b.decisionRule}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-2.5">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-rose-400" />
            Deterministic Verdict Guardrails (VerdictGuardrailsEngine)
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {DETERMINISTIC_GUARDRAILS.map((g) => (
              <div
                key={g.code}
                className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5 space-y-1 text-[11px]"
              >
                <div className="font-mono font-bold text-amber-300 text-[10px]">{g.code}</div>
                <div className="text-slate-200">{g.trigger}</div>
                <div className="text-slate-400">{g.effect}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

