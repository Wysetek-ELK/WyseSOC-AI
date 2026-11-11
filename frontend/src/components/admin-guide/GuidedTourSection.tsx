"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  Compass,
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  Sparkles,
  ExternalLink,
  Layers,
  ShieldCheck,
  Cpu,
  FileSearch,
  Wrench,
  Activity,
} from "lucide-react";
import { GUIDED_TOUR_STOPS, PLATFORM_PAGE_LINKS } from "@/data/admin-guide/glossaryAndTroubleshootingData";
import type { GuideMode } from "@/data/admin-guide/types";

interface GuidedTourSectionProps {
  onNavigateMode: (mode: GuideMode) => void;
}

export function GuidedTourSection({ onNavigateMode }: GuidedTourSectionProps) {
  const [activeStopIdx, setActiveStopIdx] = useState<number>(0);
  const currentStop = GUIDED_TOUR_STOPS[activeStopIdx];

  return (
    <div className="space-y-4">
      {/* Architecture Overview Hero */}
      <div className="rounded-xl border border-cyan-900/40 bg-gradient-to-br from-slate-950 via-slate-900/70 to-cyan-950/20 p-4 sm:p-5 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1 max-w-3xl">
            <div className="inline-flex items-center gap-1.5 rounded-full border border-cyan-700/60 bg-cyan-950/80 px-2.5 py-0.5 text-[10px] font-mono text-cyan-300">
              <Sparkles className="h-3 w-3" />
              GUIDED ADMINISTRATOR TOUR · READ-ONLY DOCUMENTATION &amp; ARCHITECTURE
            </div>
            <h2 className="text-base sm:text-lg font-bold text-slate-100">
              How Verdictum AI Governs Agentic SOC Triage from FortiSIEM Ingestion to Verified Accuracy
            </h2>
            <p className="text-xs text-slate-300 leading-relaxed">
              Verdictum AI separates <strong className="text-cyan-300">Policy Governance (Agent Intelligence Studio 2.0)</strong> from{" "}
              <strong className="text-emerald-300">Runtime Investigation (Verdict Triage Agent)</strong>. No LLM prompt runs in production without an Administrator-approved 9-section policy, a machine-verifiable Evidence Contract, deterministic safety guardrails, and honest empirical validation.
            </p>
          </div>
          <button
            type="button"
            onClick={() => onNavigateMode("architecture")}
            className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/60 bg-cyan-600/20 px-3 py-1.5 text-xs font-semibold text-cyan-200 hover:bg-cyan-600/30 transition-colors"
          >
            <span>Jump to Animated Architecture</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* 4 Core Platform Pillars Summary */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 text-xs">
          <button
            type="button"
            onClick={() => onNavigateMode("policy-lifecycle")}
            className="rounded-lg border border-slate-800 bg-slate-950/80 hover:border-cyan-500/60 p-3 text-left transition-all"
          >
            <div className="flex items-center justify-between text-cyan-400 mb-1">
              <Cpu className="h-4 w-4" />
              <span className="text-[10px] font-mono">AIS 2.0</span>
            </div>
            <div className="font-bold text-slate-100">Policy &amp; Quality Gates G1–G8</div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Authoritative rule parsing, archetypes (NETWORK_SCAN), Evidence Contracts, and simulation gating.
            </p>
          </button>

          <button
            type="button"
            onClick={() => onNavigateMode("decision-engine")}
            className="rounded-lg border border-slate-800 bg-slate-950/80 hover:border-emerald-500/60 p-3 text-left transition-all"
          >
            <div className="flex items-center justify-between text-emerald-400 mb-1">
              <ShieldCheck className="h-4 w-4" />
              <span className="text-[10px] font-mono">AIS 2.1</span>
            </div>
            <div className="font-bold text-slate-100">Evidence &amp; Trustworthiness</div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              4-dimension sufficiency Infallible Rule, G1–G7 guardrails, and 1–10 explainable Trust Scores.
            </p>
          </button>

          <button
            type="button"
            onClick={() => onNavigateMode("incident-walkthrough")}
            className="rounded-lg border border-slate-800 bg-slate-950/80 hover:border-amber-500/60 p-3 text-left transition-all"
          >
            <div className="flex items-center justify-between text-amber-400 mb-1">
              <FileSearch className="h-4 w-4" />
              <span className="text-[10px] font-mono">CASE 165233</span>
            </div>
            <div className="font-bold text-slate-100">Incident 165233 Walkthrough</div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Why Heavy TCP Host Scan (SIEM FP) received AI abstention (3/10) and G8 INSUFFICIENT_DATA.
            </p>
          </button>

          <button
            type="button"
            onClick={() => onNavigateMode("requirements")}
            className="rounded-lg border border-slate-800 bg-slate-950/80 hover:border-indigo-500/60 p-3 text-left transition-all"
          >
            <div className="flex items-center justify-between text-indigo-400 mb-1">
              <Wrench className="h-4 w-4" />
              <span className="text-[10px] font-mono">11 DOMAINS</span>
            </div>
            <div className="font-bold text-slate-100">Admin Prerequisites</div>
            <p className="text-[11px] text-slate-400 mt-0.5">
              FortiSIEM sync, Server 2 LLM, RBAC approvals, label provenance, and calibration thresholds.
            </p>
          </button>
        </div>
      </div>

      {/* Interactive 6-Stop Sequential Guided Tour */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 overflow-hidden">
        <div className="border-b border-slate-800 bg-slate-900/60 px-4 py-2.5 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Compass className="h-4 w-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-slate-100">
              Interactive Administrator Tour ({activeStopIdx + 1} of {GUIDED_TOUR_STOPS.length})
            </h3>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setActiveStopIdx((p) => Math.max(0, p - 1))}
              disabled={activeStopIdx === 0}
              className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-40"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              <span>Previous Stop</span>
            </button>
            <button
              type="button"
              onClick={() =>
                setActiveStopIdx((p) => Math.min(GUIDED_TOUR_STOPS.length - 1, p + 1))
              }
              disabled={activeStopIdx === GUIDED_TOUR_STOPS.length - 1}
              className="inline-flex items-center gap-1 rounded border border-cyan-600/60 bg-cyan-950/60 px-2.5 py-1 text-xs font-semibold text-cyan-200 hover:bg-cyan-900/60 disabled:opacity-40"
            >
              <span>Next Stop</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12">
          {/* Stop Selector Rail */}
          <div className="lg:col-span-4 border-b lg:border-b-0 lg:border-r border-slate-800 p-3 space-y-1.5 bg-slate-950">
            {GUIDED_TOUR_STOPS.map((stop, idx) => {
              const active = idx === activeStopIdx;
              return (
                <button
                  key={stop.id}
                  type="button"
                  onClick={() => setActiveStopIdx(idx)}
                  className={`w-full rounded-lg border px-3 py-2 text-left transition-all ${
                    active
                      ? "border-cyan-500/70 bg-cyan-950/35"
                      : idx < activeStopIdx
                      ? "border-slate-800 bg-slate-900/50 text-slate-300"
                      : "border-slate-800/80 bg-slate-950 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 text-[10px] font-mono">
                    <span className={active ? "text-cyan-300 font-bold" : "text-slate-500"}>
                      STOP {stop.stopNumber}
                    </span>
                    <span className="text-slate-500">{stop.estimatedMinutes}</span>
                  </div>
                  <div className="text-xs font-semibold text-slate-100 mt-0.5">{stop.title}</div>
                </button>
              );
            })}
          </div>

          {/* Active Tour Stop Details */}
          <div className="lg:col-span-8 p-4 space-y-3.5 bg-slate-900/20">
            <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-800 pb-2.5">
              <div>
                <div className="text-[10px] font-mono uppercase tracking-wider text-cyan-400">
                  Tour Stop {currentStop.stopNumber} · {currentStop.estimatedMinutes}
                </div>
                <h4 className="text-base font-bold text-slate-100">{currentStop.title}</h4>
                <p className="text-xs text-slate-400">{currentStop.subtitle}</p>
              </div>
              <button
                type="button"
                onClick={() => onNavigateMode(currentStop.targetMode)}
                className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/60 bg-cyan-600/20 px-3 py-1.5 text-xs font-semibold text-cyan-200 hover:bg-cyan-600/30 transition-colors"
              >
                <span>{currentStop.actionLabel}</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </button>
            </div>

            <p className="text-xs text-slate-200 leading-relaxed">{currentStop.narrative}</p>

            <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-3 space-y-2">
              <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-bold flex items-center gap-1">
                <Layers className="h-3.5 w-3.5" /> Key Takeaways for This Stage
              </div>
              <ul className="space-y-1.5 text-xs text-slate-300">
                {currentStop.keyTakeaways.map((item, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Quick Workspace Shortcuts */}
            <div className="pt-1 flex flex-wrap items-center gap-2 text-[11px]">
              <span className="text-slate-400 font-mono text-[10px] flex items-center gap-1">
                <Activity className="h-3 w-3 text-cyan-400" /> Quick Links:
              </span>
              {PLATFORM_PAGE_LINKS.slice(0, 6).map((lnk) => (
                <Link
                  key={lnk.href}
                  href={lnk.href}
                  className="inline-flex items-center gap-1 rounded border border-slate-800 bg-slate-950 px-2 py-0.5 text-[10px] text-slate-300 hover:border-cyan-700 hover:text-cyan-300"
                >
                  <span>{lnk.title}</span>
                  <ExternalLink className="h-2.5 w-2.5" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

