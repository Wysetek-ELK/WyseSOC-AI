"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Play,
  Pause,
  SkipBack,
  SkipForward,
  RotateCcw,
  EyeOff,
  AlertTriangle,
  CheckCircle2,
  ShieldAlert,
  Info,
  ExternalLink,
  ArrowRight,
  FileSearch,
} from "lucide-react";
import {
  INCIDENT_165233_METADATA,
  INCIDENT_165233_STEPS,
} from "@/data/admin-guide/incidentExampleData";
import { GlossaryTerm } from "./GlossaryTerm";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

interface IncidentWalkthroughSectionProps {
  onJumpToGlossary?: (termId: string) => void;
}

export function IncidentWalkthroughSection({
  onJumpToGlossary,
}: IncidentWalkthroughSectionProps) {
  const [stepIndex, setStepIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<0.5 | 1 | 1.5 | 2>(1);
  const osReducedMotion = usePrefersReducedMotion();
  const [manualReducedMotion, setManualReducedMotion] = useState<boolean | null>(null);
  const reducedMotion = manualReducedMotion ?? osReducedMotion;

  useEffect(() => {
    if (!isPlaying) return;
    const ms = speed === 0.5 ? 3400 : speed === 1 ? 2000 : speed === 1.5 ? 1300 : 900;
    const timer = setInterval(() => {
      setStepIndex((prev) => (prev + 1) % INCIDENT_165233_STEPS.length);
    }, ms);
    return () => clearInterval(timer);
  }, [isPlaying, speed]);

  const currentStep = INCIDENT_165233_STEPS[stepIndex];

  const toneBadgeClass = (tone: typeof currentStep.statusTone) => {
    switch (tone) {
      case "cyan":
        return "bg-cyan-950/90 text-cyan-300 border-cyan-700/60";
      case "amber":
        return "bg-amber-950/90 text-amber-300 border-amber-700/60";
      case "rose":
        return "bg-rose-950/90 text-rose-300 border-rose-700/60";
      case "emerald":
        return "bg-emerald-950/90 text-emerald-300 border-emerald-700/60";
      default:
        return "bg-slate-900 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="space-y-4">
      {/* Case Study Header */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <FileSearch className="h-4 w-4 text-cyan-400" />
              <h2 className="text-base font-bold text-slate-100">
                Interactive Real-World Example — Incident ID {INCIDENT_165233_METADATA.incidentId}
              </h2>
              <span className="rounded-full border border-indigo-700/60 bg-indigo-950/70 px-2 py-0.5 text-[10px] font-mono text-indigo-300">
                ILLUSTRATIVE WALKTHROUGH
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mt-1 max-w-3xl">
              {INCIDENT_165233_METADATA.disclaimer}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Link
              href="/ai-triage-workbench?search=165233"
              className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1 text-[11px] text-slate-200 hover:bg-slate-800"
            >
              <span>Search 165233 in Triage Workbench</span>
              <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
        </div>

        {/* Observed Case Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5 text-xs">
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-2.5">
            <div className="text-[10px] font-mono uppercase text-slate-500">Incident ID</div>
            <div className="text-sm font-bold font-mono text-cyan-300 mt-0.5">
              {INCIDENT_165233_METADATA.incidentId}
            </div>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-2.5">
            <div className="text-[10px] font-mono uppercase text-slate-500">Rule &amp; Archetype</div>
            <div className="text-xs font-bold text-slate-100 mt-0.5">
              {INCIDENT_165233_METADATA.ruleName}
            </div>
            <div className="text-[10px] font-mono text-cyan-400">{INCIDENT_165233_METADATA.archetype}</div>
          </div>
          <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/15 p-2.5">
            <div className="text-[10px] font-mono uppercase text-emerald-400">SIEM Resolution</div>
            <div className="text-sm font-bold text-emerald-300 mt-0.5">
              {INCIDENT_165233_METADATA.siemResolution}
            </div>
          </div>
          <div className="rounded-lg border border-amber-900/50 bg-amber-950/15 p-2.5">
            <div className="text-[10px] font-mono uppercase text-amber-400">Historical AI Decision</div>
            <div className="text-xs font-bold font-mono text-amber-300 mt-0.5">
              Requires Analyst Attention
            </div>
          </div>
          <div className="rounded-lg border border-rose-900/50 bg-rose-950/15 p-2.5">
            <div className="text-[10px] font-mono uppercase text-rose-400">Observed Trust Score</div>
            <div className="text-sm font-bold font-mono text-rose-300 mt-0.5">
              {INCIDENT_165233_METADATA.observedTrustScore}
            </div>
          </div>
        </div>
      </div>

      {/* Animated Walkthrough Player */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 overflow-hidden">
        {/* Player Toolbar */}
        <div className="border-b border-slate-800 bg-slate-900/70 px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold text-slate-100">
              Incident 165233 Animated Trace
            </span>
            <span className="rounded bg-cyan-950/80 border border-cyan-800/60 px-2 py-0.5 text-[10px] font-mono text-cyan-300">
              Stage {stepIndex + 1} / {INCIDENT_165233_STEPS.length}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setIsPlaying((p) => !p)}
              className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold border transition-colors ${
                isPlaying
                  ? "bg-amber-950/70 text-amber-300 border-amber-700/70"
                  : "bg-cyan-600/20 text-cyan-300 border-cyan-500/50"
              }`}
            >
              {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
              <span>{isPlaying ? "Pause" : "Play"}</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setIsPlaying(false);
                setStepIndex((p) => (p - 1 + INCIDENT_165233_STEPS.length) % INCIDENT_165233_STEPS.length);
              }}
              className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
            >
              <SkipBack className="h-3.5 w-3.5" />
              <span>Prev</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setIsPlaying(false);
                setStepIndex((p) => (p + 1) % INCIDENT_165233_STEPS.length);
              }}
              className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
            >
              <span>Next</span>
              <SkipForward className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => {
                setStepIndex(0);
                setIsPlaying(true);
              }}
              className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Restart</span>
            </button>

            <div className="flex items-center rounded-md border border-slate-700 bg-slate-900 p-0.5 text-[10px] font-mono">
              {([0.5, 1, 1.5, 2] as const).map((opt) => (
                <button
                  key={opt}
                  type="button"
                  onClick={() => setSpeed(opt)}
                  className={`px-1.5 py-0.5 rounded ${
                    speed === opt ? "bg-cyan-600/30 text-cyan-300 font-bold" : "text-slate-400"
                  }`}
                >
                  {opt}x
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setManualReducedMotion(!reducedMotion)}
              className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] ${
                reducedMotion
                  ? "bg-emerald-950/70 text-emerald-300 border-emerald-700/70"
                  : "bg-slate-900 text-slate-400 border-slate-700"
              }`}
              aria-pressed={reducedMotion}
            >
              <EyeOff className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Reduced Motion</span>
            </button>
          </div>
        </div>

        {/* Visual Animated Node Chain */}
        <div className="p-4 border-b border-slate-800 bg-slate-950/70">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-2.5">
            {INCIDENT_165233_STEPS.map((st, idx) => {
              const isActive = idx === stepIndex;
              const isPast = idx < stepIndex;
              return (
                <button
                  key={st.id}
                  type="button"
                  onClick={() => {
                    setStepIndex(idx);
                    setIsPlaying(false);
                  }}
                  className={`relative rounded-lg border p-2.5 text-left transition-all ${
                    isActive
                      ? "border-cyan-400 bg-cyan-950/35 ring-2 ring-cyan-400/40"
                      : isPast
                      ? "border-slate-700 bg-slate-900/70"
                      : "border-slate-800 bg-slate-900/30 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 mb-1">
                    <span className="text-[10px] font-mono font-bold text-cyan-400">
                      STEP {st.stepNumber}
                    </span>
                    {isActive && (
                      <span
                        className={`h-2 w-2 rounded-full bg-cyan-400 ${
                          reducedMotion ? "" : "animate-ping"
                        }`}
                      />
                    )}
                    {isPast && <CheckCircle2 className="h-3 w-3 text-emerald-400" />}
                  </div>
                  <div className="text-[11px] font-semibold text-slate-100 leading-snug">
                    {st.stageName.replace(/^\d+\.\s*/, "")}
                  </div>
                  <div className="mt-1 text-[9px] font-mono text-slate-400 truncate">
                    {st.componentName}
                  </div>
                  {idx < INCIDENT_165233_STEPS.length - 1 && (
                    <ArrowRight
                      className={`hidden lg:block absolute -right-2.5 top-1/2 -translate-y-1/2 z-10 h-4 w-4 ${
                        isActive ? "text-cyan-400" : "text-slate-700"
                      }`}
                    />
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Active Step Detail View */}
        <div className="p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
            <div>
              <span className="text-[10px] font-mono text-cyan-400">
                {currentStep.componentName}
              </span>
              <h3 className="text-sm font-bold text-slate-100">{currentStep.stageName}</h3>
            </div>
            <span
              className={`rounded border px-2.5 py-0.5 text-[10px] font-mono font-bold ${toneBadgeClass(
                currentStep.statusTone
              )}`}
            >
              {currentStep.statusBadge}
            </span>
          </div>

          <p className="text-xs text-slate-200 leading-relaxed">{currentStep.whatHappens}</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3 space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-emerald-400 font-bold">
                Verified &amp; Policy-Grounded Facts
              </div>
              <ul className="space-y-1 text-[11px] text-slate-300">
                {currentStep.observedFacts.map((fact, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{fact}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-lg border border-indigo-900/50 bg-indigo-950/15 p-3 space-y-1.5">
              <div className="text-[10px] font-mono uppercase text-indigo-300 font-bold flex items-center gap-1">
                <Info className="h-3.5 w-3.5" />
                Illustrative Placeholders (Raw Telemetry Not Fabricated)
              </div>
              <ul className="space-y-1 text-[11px] text-indigo-200/90">
                {currentStep.illustrativePlaceholders.map((p, i) => (
                  <li key={i} className="flex items-start gap-1.5">
                    <span className="text-indigo-400 mt-0.5">•</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="rounded-lg border border-amber-900/50 bg-amber-950/15 p-3 text-[11px] text-amber-200">
              <strong className="text-amber-300 flex items-center gap-1 mb-0.5">
                <ShieldAlert className="h-3.5 w-3.5" /> Guardrail / Score Effect
              </strong>
              {currentStep.guardrailOrScoreImpact}
            </div>
            <div className="rounded-lg border border-cyan-900/50 bg-cyan-950/15 p-3 text-[11px] text-cyan-200">
              <strong className="text-cyan-300 flex items-center gap-1 mb-0.5">
                <AlertTriangle className="h-3.5 w-3.5" /> Administrator Takeaway
              </strong>
              {currentStep.takeaway}
            </div>
          </div>
        </div>
      </div>

      {/* Five Essential Governance Takeaways */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-2.5">
        <h3 className="text-sm font-bold text-slate-100">
          What Incident 165233 Proves About AI Verdict Governance
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2.5 text-[11px]">
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5">
            <div className="font-bold text-amber-300 mb-1">1. Safe Abstention</div>
            <p className="text-slate-300">
              The AI abstained (<code className="font-mono">REQUIRES_ANALYST_ATTENTION</code>, Trust{" "}
              <code className="font-mono">3/10</code>) rather than forcing TP or FP without verified authorization.
            </p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5">
            <div className="font-bold text-emerald-300 mb-1">2. SIEM FP Resolution</div>
            <p className="text-slate-300">
              SIEM history shows <code className="font-mono">False Positive</code>, isolated from model inference via zero-leakage allowlisting.
            </p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5">
            <div className="font-bold text-cyan-300 mb-1">3. Provenance Audit</div>
            <p className="text-slate-300">
              <GlossaryTerm termId="ground-truth-provenance" onJumpToGlossary={onJumpToGlossary}>
                Ground-truth provenance
              </GlossaryTerm>{" "}
              requires human verification whenever analyst identity (<code className="font-mono">clearedUser</code>) or rationale is unavailable.
            </p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5">
            <div className="font-bold text-indigo-300 mb-1">4. N=1 Is Insufficient</div>
            <p className="text-slate-300">
              One labeled incident cannot establish reliable empirical accuracy, precision, recall, or calibration.
            </p>
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-2.5">
            <div className="font-bold text-rose-300 mb-1">5. G8 Remains Honest</div>
            <p className="text-slate-300">
              Historical simulation Gate G8 remains <code className="font-mono">INSUFFICIENT_DATA</code> until N &ge; 5 verified rule-matched cases exist.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
