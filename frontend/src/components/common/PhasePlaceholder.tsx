"use client";

import React from "react";
import { Lock, Clock, ArrowRight, ShieldCheck, Cpu, FlaskConical } from "lucide-react";

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
    <div className="flex flex-col items-center justify-center p-8 max-w-4xl mx-auto my-12">
      <div className="w-full rounded-2xl border border-slate-800 bg-slate-900/60 p-8 backdrop-blur-md shadow-xl">
        {/* Phase Header Tag */}
        <div className="flex items-center justify-between mb-6 pb-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div
              className={`p-3 rounded-xl border ${
                isPhase2
                  ? "bg-amber-950/40 text-amber-400 border-amber-800/60"
                  : "bg-purple-950/40 text-purple-400 border-purple-800/60"
              }`}
            >
              {isPhase2 ? <Clock className="h-6 w-6" /> : <FlaskConical className="h-6 w-6" />}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border ${
                    isPhase2
                      ? "bg-amber-950/80 text-amber-400 border-amber-700/60"
                      : "bg-purple-950/80 text-purple-400 border-purple-700/60"
                  }`}
                >
                  Scheduled for Phase {phase}
                </span>
                <span className="text-xs text-slate-500 font-mono">STRICT RESTRICTION GOVERNANCE</span>
              </div>
              <h1 className="text-2xl font-bold text-slate-100 mt-1">{title}</h1>
            </div>
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800">
            <Lock className="h-3.5 w-3.5 text-slate-500" />
            <span>Gated until Phase 1 approval</span>
          </div>
        </div>

        {/* Description */}
        <p className="text-slate-300 text-sm leading-relaxed mb-6">
          {description}
        </p>

        {/* Milestones */}
        <div className="mb-6 rounded-xl bg-slate-950/80 p-5 border border-slate-800">
          <h2 className="text-xs font-semibold text-slate-200 uppercase tracking-wider mb-3">
            Phase {phase} Implementation Milestones
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {milestones.map((m, idx) => (
              <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-400">
                <span
                  className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-[10px] font-bold ${
                    isPhase2 ? "bg-amber-900/60 text-amber-300" : "bg-purple-900/60 text-purple-300"
                  }`}
                >
                  {idx + 1}
                </span>
                <span>{m}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Architecture Spec */}
        <div className="rounded-xl bg-slate-950/60 p-4 border border-slate-800 text-xs">
          <span className="font-semibold text-slate-300">Planned Architecture: </span>
          <span className="text-slate-400 font-mono">{plannedArchitecture}</span>
        </div>

        {/* Footer Guarantee */}
        <div className="mt-6 flex items-center justify-between text-[11px] text-slate-500 font-mono">
          <span>Zero LLM dependencies active during Phase 1 foundation.</span>
          <span>AI Verdict Protocol v1.0</span>
        </div>
      </div>
    </div>
  );
}

