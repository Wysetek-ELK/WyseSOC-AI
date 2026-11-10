"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Cpu,
  ShieldCheck,
  AlertTriangle,
  XCircle,
  CheckCircle2,
  ArrowRight,
  Award,
  FlaskConical,
  ExternalLink,
  ChevronRight,
  ChevronDown,
  FileCode2,
  GitBranch,
  Radar,
  Lock,
} from "lucide-react";
import {
  ARCHETYPE_SPOTLIGHT,
  HEAVY_TCP_V1_VS_V2_COMPARISON,
  NINE_POLICY_SECTIONS,
  QUALITY_GATES_DOCS,
  SIMULATION_FUNNEL_STAGES,
  STUDIO_LIFECYCLE_STAGES,
} from "@/data/admin-guide/studioGuideData";
import { GlossaryTerm } from "./GlossaryTerm";

interface StudioGuideSectionProps {
  onJumpToGlossary?: (termId: string) => void;
  highlightedGateId?: string | null;
  jumpNonce?: number;
}

export function StudioGuideSection({
  onJumpToGlossary,
  highlightedGateId,
  jumpNonce = 0,
}: StudioGuideSectionProps) {
  const [selectedStageIdx, setSelectedStageIdx] = useState<number>(0);
  const [gateFilter, setGateFilter] = useState<"ALL" | "STRUCTURAL" | "EMPIRICAL">("ALL");
  const [expandedGateId, setExpandedGateId] = useState<string | null>(highlightedGateId || "G5");
  const [prevGateJump, setPrevGateJump] = useState<string>(
    `${highlightedGateId || ""}:${jumpNonce}`
  );
  const currentGateJump = `${highlightedGateId || ""}:${jumpNonce}`;
  if (currentGateJump !== prevGateJump) {
    setPrevGateJump(currentGateJump);
    if (highlightedGateId) {
      setExpandedGateId(highlightedGateId);
      setGateFilter("ALL");
    }
  }

  useEffect(() => {
    if (highlightedGateId && jumpNonce > 0) {
      const el = document.getElementById(`gate-card-${highlightedGateId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [highlightedGateId, jumpNonce]);
  const [expandedPolicySection, setExpandedPolicySection] = useState<number>(1);
  const [showAllArchetypes, setShowAllArchetypes] = useState<boolean>(false);

  const selectedStage = STUDIO_LIFECYCLE_STAGES[selectedStageIdx];
  const filteredGates = QUALITY_GATES_DOCS.filter((g) =>
    gateFilter === "ALL" ? true : g.category === gateFilter
  );

  return (
    <div className="space-y-5">
      {/* Section Header & Core Principle Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Cpu className="h-4 w-4 text-cyan-400" />
              <h2 className="text-base font-bold text-slate-100">
                Agent Intelligence Studio 2.0 — Policy Governance &amp; Validation
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl">
              Explains how SIEM rules move from raw FortiSIEM definitions into{" "}
              <GlossaryTerm termId="detection-archetype" onJumpToGlossary={onJumpToGlossary}>
                Detection Archetypes
              </GlossaryTerm>
              , machine-verifiable{" "}
              <GlossaryTerm termId="evidence-contract" onJumpToGlossary={onJumpToGlossary}>
                Evidence Contracts
              </GlossaryTerm>
              , 9-section policies, Quality Gates G1–G8, and Administrator-approved runtime enforcement.
            </p>
          </div>
          <Link
            href="/agent-intelligence-studio"
            className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/40 bg-cyan-950/50 px-3 py-1.5 text-xs font-semibold text-cyan-300 hover:bg-cyan-900/60 transition-colors"
          >
            <span>Open Agent Intelligence Studio</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </Link>
        </div>

        {/* Structural Policy Quality != Empirical Verdict Accuracy Callout */}
        <div className="rounded-lg border border-amber-500/40 bg-amber-950/20 p-3 flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <div className="font-bold text-amber-200">
              Critical Governance Principle: Structural Policy Quality ≠ Empirical Verdict Accuracy
            </div>
            <p className="text-[11px] text-amber-200/85 leading-relaxed">
              <GlossaryTerm termId="structural-quality-score" onJumpToGlossary={onJumpToGlossary}>
                Structural Quality (Gates G1–G7)
              </GlossaryTerm>{" "}
              audits how well a policy is constructed (up to 85 raw points scaled to 0–100).{" "}
              <GlossaryTerm termId="gate-g8" onJumpToGlossary={onJumpToGlossary}>
                Gate G8 (Empirical Simulation, 15 pts)
              </GlossaryTerm>{" "}
              measures actual accuracy against verified human historical incidents. A policy can achieve high structural quality while G8 honestly remains{" "}
              <code className="px-1 py-0.5 rounded bg-slate-900 font-mono text-amber-300">
                INSUFFICIENT_DATA
              </code>{" "}
              when fewer than 5 verified rule-matched incidents exist. Furthermore, a{" "}
              <GlossaryTerm termId="hard-gate-failure" onJumpToGlossary={onJumpToGlossary}>
                Hard Gate Failure
              </GlossaryTerm>{" "}
              strictly blocks approval regardless of numeric score.
            </p>
          </div>
        </div>
      </div>

      {/* 1. Interactive 8-Stage AIS 2.0 Lifecycle Explorer */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-cyan-400" />
            End-to-End Studio 2.0 Policy Lifecycle (8 Interactive Stages)
          </h3>
          <span className="text-[10px] font-mono text-slate-400">
            Click any stage to inspect service, guarantee, and UI tab
          </span>
        </div>

        {/* Horizontal Interactive Flow Nodes */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
          {STUDIO_LIFECYCLE_STAGES.map((st, idx) => {
            const active = idx === selectedStageIdx;
            return (
              <button
                key={st.id}
                type="button"
                onClick={() => setSelectedStageIdx(idx)}
                className={`relative rounded-lg border p-2.5 text-left transition-all ${
                  active
                    ? "border-cyan-400 bg-cyan-950/40 ring-1 ring-cyan-400/50"
                    : "border-slate-800 bg-slate-900/50 hover:border-slate-600"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-bold ${
                      active
                        ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                        : "bg-slate-800 text-slate-400"
                    }`}
                  >
                    Stage {st.step}
                  </span>
                  {idx < STUDIO_LIFECYCLE_STAGES.length - 1 && (
                    <ArrowRight className="h-3 w-3 text-slate-600 hidden lg:block" />
                  )}
                </div>
                <div className="text-[11px] font-semibold text-slate-100 leading-snug line-clamp-2">
                  {st.title}
                </div>
              </button>
            );
          })}
        </div>

        {/* Selected Stage Deep Card */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3.5 space-y-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
            <div>
              <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400">
                Stage {selectedStage.step} · AIS Tab: {selectedStage.uiTab}
              </span>
              <h4 className="text-sm font-bold text-slate-100">{selectedStage.title}</h4>
            </div>
            <span className="rounded border border-slate-700 bg-slate-950 px-2 py-0.5 text-[10px] font-mono text-slate-300">
              {selectedStage.service}
            </span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">{selectedStage.summary}</p>
          <div className="rounded border border-emerald-800/50 bg-emerald-950/20 p-2.5 text-[11px] text-emerald-200">
            <strong className="text-emerald-300">Deterministic Guarantee:</strong>{" "}
            {selectedStage.keyGuarantee}
          </div>
          <ul className="space-y-1 text-[11px] text-slate-300">
            {selectedStage.details.map((d, i) => (
              <li key={i} className="flex items-start gap-1.5">
                <CheckCircle2 className="h-3.5 w-3.5 text-cyan-400 shrink-0 mt-0.5" />
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 2. Detection Archetype Registry & NETWORK_SCAN Spotlight */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Radar className="h-4 w-4 text-cyan-400" />
              Detection Archetype Registry &amp; <code className="font-mono text-cyan-300">NETWORK_SCAN</code> Contract
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              {ARCHETYPE_SPOTLIGHT.totalRegisteredEnumEntries} registered <code className="font-mono">ArchetypeId</code> taxonomy entries ensure every rule binds domain-accurate telemetry.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowAllArchetypes((v) => !v)}
            className="rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
          >
            {showAllArchetypes ? "Hide All Archetype IDs" : "Show All Registered Archetype IDs"}
          </button>
        </div>

        {showAllArchetypes && (
          <div className="flex flex-wrap gap-1.5 rounded-lg border border-slate-800 bg-slate-900/40 p-2.5">
            {ARCHETYPE_SPOTLIGHT.allArchetypes.map((arch) => (
              <span
                key={arch}
                className={`rounded px-2 py-0.5 text-[10px] font-mono border ${
                  arch === "NETWORK_SCAN"
                    ? "bg-cyan-950/90 text-cyan-300 border-cyan-600/70 font-bold"
                    : arch === "UNKNOWN"
                    ? "bg-amber-950/70 text-amber-300 border-amber-700/60"
                    : "bg-slate-950 text-slate-300 border-slate-800"
                }`}
              >
                {arch}
              </span>
            ))}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <div className="rounded-lg border border-cyan-900/50 bg-cyan-950/15 p-3 space-y-1.5">
            <div className="text-[10px] font-mono uppercase tracking-wider text-cyan-300 font-bold">
              Mandatory Core Fields (NETWORK_SCAN)
            </div>
            <p className="text-[11px] text-slate-400">
              Required in Evidence Contract &amp; runtime Preflight checks:
            </p>
            <div className="flex flex-wrap gap-1">
              {ARCHETYPE_SPOTLIGHT.networkScan.mandatoryCoreFields.map((f) => (
                <code
                  key={f}
                  className="rounded bg-slate-950 border border-cyan-800/50 px-1.5 py-0.5 text-[10px] font-mono text-cyan-200"
                >
                  {f}
                </code>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-indigo-900/50 bg-indigo-950/15 p-3 space-y-1.5">
            <div className="text-[10px] font-mono uppercase tracking-wider text-indigo-300 font-bold">
              Conditional Scan Telemetry
            </div>
            <p className="text-[11px] text-slate-400">
              Strengthens scan rate and target-breadth evaluation:
            </p>
            <div className="flex flex-wrap gap-1">
              {ARCHETYPE_SPOTLIGHT.networkScan.conditionalFields.map((f) => (
                <code
                  key={f}
                  className="rounded bg-slate-950 border border-indigo-800/50 px-1.5 py-0.5 text-[10px] font-mono text-indigo-200"
                >
                  {f}
                </code>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-rose-900/50 bg-rose-950/15 p-3 space-y-1.5">
            <div className="text-[10px] font-mono uppercase tracking-wider text-rose-300 font-bold">
              Unsupported Fields (Blocked in G2/G3)
            </div>
            <p className="text-[11px] text-slate-400">
              Never demanded for pure network firewall scan rules:
            </p>
            <div className="flex flex-wrap gap-1">
              {ARCHETYPE_SPOTLIGHT.networkScan.unsupportedFields.map((f) => (
                <code
                  key={f}
                  className="rounded bg-slate-950 border border-rose-800/50 px-1.5 py-0.5 text-[10px] font-mono text-rose-200"
                >
                  {f}
                </code>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Nine-Section Intelligent Policy Specification Explorer */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div>
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <FileCode2 className="h-4 w-4 text-cyan-400" />
            Nine-Section Investigation Policy Structure
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Every policy compiled by <code className="font-mono text-slate-300">PolicyCompilerService v3.0.0</code> enforces these ordered 9 sections identically across Live Triage and Simulation Lab.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
          <div className="lg:col-span-5 space-y-1">
            {NINE_POLICY_SECTIONS.map((sec) => {
              const active = expandedPolicySection === sec.sectionNumber;
              return (
                <button
                  key={sec.sectionId}
                  type="button"
                  onClick={() => setExpandedPolicySection(sec.sectionNumber)}
                  className={`w-full flex items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left text-xs transition-colors ${
                    active
                      ? "border-cyan-500/60 bg-cyan-950/35 text-cyan-200 font-semibold"
                      : "border-slate-800 bg-slate-900/40 text-slate-300 hover:border-slate-700"
                  }`}
                >
                  <span className="truncate">
                    <span className="font-mono text-cyan-400 mr-1.5">{sec.sectionNumber}.</span>
                    {sec.title}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 shrink-0">
                    {sec.gateDependencies.join(", ")}
                  </span>
                </button>
              );
            })}
          </div>

          <div className="lg:col-span-7">
            {NINE_POLICY_SECTIONS.filter((s) => s.sectionNumber === expandedPolicySection).map((sec) => (
              <div
                key={sec.sectionId}
                className="rounded-lg border border-slate-800 bg-slate-900/40 p-3.5 space-y-2.5 h-full"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
                  <div>
                    <span className="text-[10px] font-mono text-cyan-400">
                      SECTION {sec.sectionNumber} · {sec.sectionId}
                    </span>
                    <h4 className="text-sm font-bold text-slate-100">{sec.title}</h4>
                  </div>
                  <span className="rounded bg-slate-950 border border-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-400">
                    {sec.owner}
                  </span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{sec.description}</p>
                <div className="text-xs text-slate-300">
                  <strong className="text-slate-100">Role in Verdict Triage:</strong>{" "}
                  {sec.purposeInTriage}
                </div>
                <div className="rounded border border-slate-800 bg-slate-950 p-2.5 font-mono text-[11px] text-cyan-200/90">
                  {sec.exampleSnippet}
                </div>
                <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-400">
                  <span>Audited by Gates:</span>
                  {sec.gateDependencies.map((g) => (
                    <span
                      key={g}
                      className="rounded bg-cyan-950/70 border border-cyan-800/60 px-1.5 py-0.5 text-cyan-300"
                    >
                      {g}
                    </span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 4. Quality Gates G1–G8 Complete Reference Matrix */}
      <div id="quality-gates-section" className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Award className="h-4 w-4 text-cyan-400" />
              Policy Quality Gates G1–G8 (Descriptions, Pass/Warn/Blocker Conditions &amp; Remediation)
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Structural score = <code className="font-mono text-cyan-300">(G1/G2 [20] + G3 [20] + G4+G5 [20] + G6 [15] + G7 [10]) / 85 × 100</code>. Gate G8 adds up to 15 empirical points.
            </p>
          </div>
          <div className="flex items-center rounded-md border border-slate-700 bg-slate-900 p-0.5 text-[11px]">
            {(["ALL", "STRUCTURAL", "EMPIRICAL"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setGateFilter(tab)}
                className={`px-2.5 py-1 rounded transition-colors ${
                  gateFilter === tab
                    ? "bg-cyan-600/30 text-cyan-300 font-semibold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {tab === "ALL" ? "All (G1–G8)" : tab === "STRUCTURAL" ? "Structural (G1–G7)" : "Empirical (G8)"}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2">
          {filteredGates.map((gate) => {
            const isOpen = expandedGateId === gate.gateId;
            return (
              <div
                key={gate.gateId}
                id={`gate-card-${gate.gateId}`}
                className={`rounded-lg border transition-colors ${
                  gate.category === "EMPIRICAL"
                    ? "border-amber-800/60 bg-amber-950/10"
                    : isOpen
                    ? "border-cyan-700/60 bg-slate-900/60"
                    : "border-slate-800 bg-slate-900/30"
                }`}
              >
                <button
                  type="button"
                  onClick={() => setExpandedGateId(isOpen ? null : gate.gateId)}
                  className="w-full flex flex-wrap items-center justify-between gap-2 px-3.5 py-2.5 text-left"
                >
                  <div className="flex items-center gap-2.5">
                    {isOpen ? (
                      <ChevronDown className="h-4 w-4 text-cyan-400 shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />
                    )}
                    <span className="rounded bg-cyan-950/90 border border-cyan-700/60 px-2 py-0.5 text-[11px] font-mono font-bold text-cyan-300">
                      {gate.gateId}
                    </span>
                    <div>
                      <span className="text-xs font-bold text-slate-100">{gate.gateName}</span>
                      <span className="ml-2 text-[10px] font-mono text-slate-500">{gate.gateCode}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`rounded px-2 py-0.5 text-[10px] font-mono border ${
                        gate.category === "EMPIRICAL"
                          ? "bg-amber-950/80 text-amber-300 border-amber-700/60"
                          : "bg-slate-950 text-slate-300 border-slate-700"
                      }`}
                    >
                      {gate.weightNote}
                    </span>
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-slate-800/80 px-3.5 py-3 space-y-3 text-xs">
                    <p className="text-slate-300 leading-relaxed">{gate.description}</p>
                    <div className="text-[10px] font-mono text-slate-400">
                      Score Breakdown Bucket: <span className="text-slate-200">{gate.breakdownBucket}</span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-2.5">
                      <div className="rounded border border-emerald-900/50 bg-emerald-950/15 p-2.5 space-y-1">
                        <div className="text-[10px] font-mono font-bold uppercase text-emerald-300 flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" /> Pass Conditions
                        </div>
                        <ul className="space-y-1 text-[11px] text-emerald-100/90">
                          {gate.passConditions.map((c, i) => (
                            <li key={i}>• {c}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="rounded border border-amber-900/50 bg-amber-950/15 p-2.5 space-y-1">
                        <div className="text-[10px] font-mono font-bold uppercase text-amber-300 flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" /> Warning Conditions
                        </div>
                        <ul className="space-y-1 text-[11px] text-amber-100/90">
                          {gate.warningConditions.map((c, i) => (
                            <li key={i}>• {c}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="rounded border border-rose-900/50 bg-rose-950/15 p-2.5 space-y-1">
                        <div className="text-[10px] font-mono font-bold uppercase text-rose-300 flex items-center gap-1">
                          <XCircle className="h-3 w-3" /> Hard Blockers
                        </div>
                        <ul className="space-y-1 text-[11px] text-rose-100/90">
                          {gate.blockerConditions.map((c, i) => (
                            <li key={i}>• {c}</li>
                          ))}
                        </ul>
                      </div>

                      <div className="rounded border border-cyan-900/50 bg-cyan-950/15 p-2.5 space-y-1">
                        <div className="text-[10px] font-mono font-bold uppercase text-cyan-300 flex items-center gap-1">
                          <ShieldCheck className="h-3 w-3" /> Remediation Guidance
                        </div>
                        <ul className="space-y-1 text-[11px] text-cyan-100/90">
                          {gate.remediationGuidance.map((c, i) => (
                            <li key={i}>• {c}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Historical Simulation Funnel & V1 vs V2 Remediation Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* 6-Stage Funnel */}
        <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-amber-400" />
              Gate G8: 6-Stage Historical Simulation Funnel
            </h3>
            <Link
              href="/agent-simulation-lab"
              className="text-[10px] font-semibold text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1"
            >
              Simulation Lab <ExternalLink className="h-2.5 w-2.5" />
            </Link>
          </div>
          <p className="text-[11px] text-slate-400">
            <code className="font-mono text-slate-300">PolicySimulationService</code> strictly isolates rule-matched verified human labels and requires <strong className="text-slate-200">N &ge; 5</strong> eligible cases to pass G8.
          </p>
          <div className="space-y-1.5">
            {SIMULATION_FUNNEL_STAGES.map((st) => (
              <div
                key={st.stage}
                className="rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2 flex items-start gap-2.5"
              >
                <span className="mt-0.5 rounded bg-slate-950 border border-slate-700 px-1.5 py-0.5 text-[10px] font-mono font-bold text-cyan-300">
                  {st.stage}
                </span>
                <div>
                  <div className="text-xs font-semibold text-slate-100">{st.name}</div>
                  <div className="text-[11px] text-slate-400">{st.description}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* V1 vs V2 Remediation Comparison & Versioning */}
        <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Lock className="h-4 w-4 text-emerald-400" />
                Candidate Versioning &amp; V1 vs V2 Comparison ({HEAVY_TCP_V1_VS_V2_COMPARISON.ruleName})
              </h3>
              <p className="text-[11px] text-slate-400">
                Shows how non-destructive versioning lets administrators remediate drafts without overwriting prior versions, and why G8 remains honest.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left text-[11px]">
              <thead className="bg-slate-900 text-slate-300 font-mono text-[10px] uppercase border-b border-slate-800">
                <tr>
                  <th className="px-3 py-2">Dimension</th>
                  <th className="px-3 py-2">Version 1 (Legacy)</th>
                  <th className="px-3 py-2">Version 2 (Remediated Candidate)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {HEAVY_TCP_V1_VS_V2_COMPARISON.rows.map((row) => (
                  <tr key={row.dimension} className="bg-slate-950/60">
                    <td className="px-3 py-2 font-semibold text-slate-200">{row.dimension}</td>
                    <td className="px-3 py-2 text-slate-400">{row.v1}</td>
                    <td
                      className={`px-3 py-2 ${
                        row.improved ? "text-emerald-300 font-medium" : "text-slate-300"
                      }`}
                    >
                      {row.v2}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
