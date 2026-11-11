"use client";

import React from "react";
import { Lock, Clock, ArrowRight, ShieldCheck, Cpu, FlaskConical } from "lucide-react";
import { BrandLogo } from "@/components/common/BrandLogo";

interface PhasePlaceholderProps {
  title: string;
  phase: 2 | 3;
  description: string;
  milestones: string[];
  plannedArchitecture: string;
}

export function PhasePlaceholder({
  title,
  phase,
  description,
  milestones,
  plannedArchitecture,
}: PhasePlaceholderProps) {
  const isPhase2 = phase === 2;

  return (
    <div className="flex flex-col items-center justify-center p-3 max-w-3xl mx-auto my-4">
      <div className="w-full rounded-xl border border-slate-800 bg-slate-900/60 p-4 sm:p-5 backdrop-blur-md shadow-xl">
        {/* Phase Header Tag */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3 pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div
              className={`p-2 rounded-lg border ${
                isPhase2
                  ? "bg-amber-950/40 text-amber-400 border-amber-800/60"
                  : "bg-purple-950/40 text-purple-400 border-purple-800/60"
              }`}
            >
              {isPhase2 ? <Clock className="h-4 w-4" /> : <FlaskConical className="h-4 w-4" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-[9px] font-mono uppercase px-1.5 py-0.2 rounded-full border ${
                    isPhase2
                      ? "bg-amber-950/80 text-amber-400 border-amber-700/60"
                      : "bg-purple-950/80 text-purple-400 border-purple-700/60"
                  }`}
                >
                  Scheduled for Phase {phase}
                </span>
                <span className="text-[10px] text-slate-500 font-mono">STRICT RESTRICTION GOVERNANCE</span>
              </div>
              <h1 className="text-lg font-bold text-slate-100 mt-0.5">{title}</h1>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 font-mono bg-slate-950 px-2.5 py-1 rounded-md border border-slate-800">
            <Lock className="h-3 w-3 text-slate-500" />
            <span>Gated until Phase 1 approval</span>
          </div>
        </div>

        {/* Description */}
        <p className="text-slate-300 text-xs leading-relaxed mb-3">
          {description}
        </p>

        {/* Milestones */}
        <div className="mb-3 rounded-lg bg-slate-950/80 p-3 border border-slate-800">
          <h2 className="text-[11px] font-semibold text-slate-200 uppercase tracking-wider mb-2">
            Phase {phase} Implementation Milestones
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {milestones.map((m, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs text-slate-400">
                <span
                  className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold ${
                    isPhase2 ? "bg-amber-900/60 text-amber-300" : "bg-purple-900/60 text-purple-300"
                  }`}
                >
                  {idx + 1}
                </span>
                <span className="text-[11px]">{m}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Architecture Spec */}
        <div className="rounded-lg bg-slate-950/60 p-2.5 border border-slate-800 text-xs">
          <span className="font-semibold text-slate-300 text-[11px]">Planned Architecture: </span>
          <span className="text-slate-400 font-mono text-[11px]">{plannedArchitecture}</span>
        </div>

        {/* Footer Guarantee */}
        <div className="mt-3 flex items-center justify-between text-[10px] text-slate-500 font-mono">
          <span>Zero LLM dependencies active during Phase 1 foundation.</span>
          <span className="inline-flex items-center gap-1.5">
            <BrandLogo size={16} />
            Verdictum AI Protocol v1.0
          </span>
        </div>
      </div>
    </div>
  );
}

