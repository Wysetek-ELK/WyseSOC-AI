"use client";

import React, { Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  BookOpenCheck,
  Compass,
  Network,
  Cpu,
  ShieldAlert,
  FileSearch,
  Wrench,
  HelpCircle,
  Search,
  X,
  ExternalLink,
  ArrowRight,
  Lock,
  Layers,
} from "lucide-react";
import type { GuideMode } from "@/data/admin-guide/types";
import {
  ARCHITECTURE_EDGES,
  ARCHITECTURE_STEPS,
  ARCHITECTURE_SWIMLANES,
} from "@/data/admin-guide/architectureFlowData";
import { DECISION_STEPS } from "@/data/admin-guide/decisionFlowData";
import {
  NINE_POLICY_SECTIONS,
  QUALITY_GATES_DOCS,
} from "@/data/admin-guide/studioGuideData";
import { REQUIREMENT_DOMAINS } from "@/data/admin-guide/requirementsData";
import {
  GLOSSARY_ENTRIES,
  PLATFORM_PAGE_LINKS,
  TROUBLESHOOTING_SCENARIOS,
} from "@/data/admin-guide/glossaryAndTroubleshootingData";
import { WorkflowFlowDiagram } from "@/components/admin-guide/WorkflowFlowDiagram";
import { GuidedTourSection } from "@/components/admin-guide/GuidedTourSection";
import { StudioGuideSection } from "@/components/admin-guide/StudioGuideSection";
import { DecisionEngineSection } from "@/components/admin-guide/DecisionEngineSection";
import { IncidentWalkthroughSection } from "@/components/admin-guide/IncidentWalkthroughSection";
import { RequirementsSection } from "@/components/admin-guide/RequirementsSection";
import { GlossaryTroubleshootingSection } from "@/components/admin-guide/GlossaryTroubleshootingSection";

interface SearchHit {
  id: string;
  title: string;
  category: string;
  snippet: string;
  mode: GuideMode;
  glossaryId?: string;
  scenarioId?: string;
  gateId?: string;
  stepId?: string;
}

const MODE_TABS: Array<{
  id: GuideMode;
  label: string;
  shortLabel: string;
  icon: React.ComponentType<{ className?: string }>;
}> = [
  { id: "guided-tour", label: "Guided Tour", shortLabel: "Tour", icon: Compass },
  { id: "architecture", label: "Explore Architecture", shortLabel: "Architecture", icon: Network },
  { id: "policy-lifecycle", label: "Policy Lifecycle (AIS 2.0)", shortLabel: "AIS 2.0", icon: Cpu },
  { id: "decision-engine", label: "Decision Engine", shortLabel: "Decision", icon: ShieldAlert },
  { id: "incident-walkthrough", label: "Incident 165233 Walkthrough", shortLabel: "Case 165233", icon: FileSearch },
  { id: "requirements", label: "Admin Setup & Prerequisites", shortLabel: "Setup", icon: Wrench },
  { id: "troubleshooting", label: "Glossary & Troubleshooting", shortLabel: "Help & Glossary", icon: HelpCircle },
];

function AdminGuideContent() {
  const searchParams = useSearchParams();
  const initialModeParam = (searchParams.get("mode") as GuideMode) || "guided-tour";
  const validMode = MODE_TABS.some((t) => t.id === initialModeParam)
    ? initialModeParam
    : "guided-tour";

  const [activeMode, setActiveMode] = useState<GuideMode>(validMode);
  const [prevModeParam, setPrevModeParam] = useState<GuideMode>(validMode);
  if (validMode !== prevModeParam) {
    setPrevModeParam(validMode);
    setActiveMode(validMode);
  }

  const [helpQuery, setHelpQuery] = useState<string>("");
  const [highlightedGlossaryId, setHighlightedGlossaryId] = useState<string | null>(null);
  const [highlightedScenarioId, setHighlightedScenarioId] = useState<string | null>(null);
  const [highlightedGateId, setHighlightedGateId] = useState<string | null>(null);
  const [architectureInitialStep, setArchitectureInitialStep] = useState<string | undefined>(undefined);
  const [decisionInitialStep, setDecisionInitialStep] = useState<string | undefined>(undefined);
  const [jumpNonce, setJumpNonce] = useState<number>(0);

  const searchIndex: SearchHit[] = useMemo(() => {
    const hits: SearchHit[] = [];

    ARCHITECTURE_STEPS.forEach((st) => {
      hits.push({
        id: `arch-${st.id}`,
        title: `${st.stepNumber}. ${st.title} — ${st.componentName}`,
        category: "End-to-End Architecture",
        snippet: st.summary,
        mode: "architecture",
        stepId: st.id,
      });
    });

    DECISION_STEPS.forEach((st) => {
      hits.push({
        id: `dec-${st.id}`,
        title: `Decision Step ${st.stepNumber}: ${st.title}`,
        category: "AI Verdict Decision Engine",
        snippet: st.summary,
        mode: "decision-engine",
        stepId: st.id,
      });
    });

    QUALITY_GATES_DOCS.forEach((g) => {
      hits.push({
        id: `gate-${g.gateId}`,
        title: `${g.gateId}: ${g.gateName} (${g.gateCode})`,
        category: "Quality Gates G1–G8",
        snippet: g.description,
        mode: "policy-lifecycle",
        gateId: g.gateId,
      });
    });

    NINE_POLICY_SECTIONS.forEach((s) => {
      hits.push({
        id: `sec-${s.sectionNumber}`,
        title: `Policy Section ${s.sectionNumber}: ${s.title}`,
        category: "AIS 2.0 Nine-Section Policy",
        snippet: s.description,
        mode: "policy-lifecycle",
      });
    });

    REQUIREMENT_DOMAINS.forEach((dom) => {
      dom.items.forEach((item) => {
        hits.push({
          id: `req-${item.id}`,
          title: `${item.title} [${item.criticality}]`,
          category: `Setup · ${dom.title}`,
          snippet: item.description,
          mode: "requirements",
        });
      });
    });

    GLOSSARY_ENTRIES.forEach((g) => {
      hits.push({
        id: `gloss-${g.id}`,
        title: g.term,
        category: `Glossary · ${g.category}`,
        snippet: g.definition,
        mode: "troubleshooting",
        glossaryId: g.id,
      });
    });

    TROUBLESHOOTING_SCENARIOS.forEach((sc) => {
      hits.push({
        id: `ts-${sc.id}`,
        title: sc.question,
        category: `Troubleshooting · ${sc.category}`,
        snippet: sc.shortAnswer,
        mode: "troubleshooting",
        scenarioId: sc.id,
      });
    });

    return hits;
  }, []);

  const searchResults = useMemo(() => {
    const q = helpQuery.trim().toLowerCase();
    if (!q) return [];
    return searchIndex
      .filter(
        (h) =>
          h.title.toLowerCase().includes(q) ||
          h.category.toLowerCase().includes(q) ||
          h.snippet.toLowerCase().includes(q)
      )
      .slice(0, 12);
  }, [helpQuery, searchIndex]);

  const handleSelectSearchHit = (hit: SearchHit) => {
    setHelpQuery("");
    setActiveMode(hit.mode);
    setHighlightedGlossaryId(hit.glossaryId || null);
    setHighlightedScenarioId(hit.scenarioId || null);
    setHighlightedGateId(hit.gateId || null);
    if (hit.mode === "architecture" && hit.stepId) {
      setArchitectureInitialStep(hit.stepId);
    }
    if (hit.mode === "decision-engine" && hit.stepId) {
      setDecisionInitialStep(hit.stepId);
    }
    setJumpNonce((n) => n + 1);
  };

  const handleJumpToGlossary = (termId: string) => {
    setHighlightedGlossaryId(termId);
    setHighlightedScenarioId(null);
    setJumpNonce((n) => n + 1);
    setActiveMode("troubleshooting");
  };

  return (
    <div className="space-y-4 w-full">
      {/* Top Command-Center Header */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-3.5 sm:p-4 space-y-3">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <BookOpenCheck className="h-5 w-5 text-cyan-400 shrink-0" />
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-slate-100">
                AI Verdict Admin Guide
              </h1>
              <span className="inline-flex items-center gap-1 rounded-full border border-emerald-700/60 bg-emerald-950/60 px-2 py-0.5 text-[10px] font-mono text-emerald-300">
                <Lock className="h-2.5 w-2.5" />
                READ-ONLY ARCHITECTURE &amp; ADMIN REFERENCE
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Interactive architecture explorer, Agent Intelligence Studio 2.0 lifecycle, Quality Gates G1–G8, Evidence &amp; Trustworthiness engines, Incident 165233 walkthrough, and operational prerequisites.
            </p>
          </div>

          {/* Searchable Help Topics Bar */}
          <div className="relative w-full lg:w-96">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            <input
              type="text"
              value={helpQuery}
              onChange={(e) => setHelpQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setHelpQuery("");
              }}
              placeholder="Search help topics, G1–G8, 165233, NETWORK_SCAN, glossary..."
              aria-label="Search AI Verdict Admin Guide topics"
              className="w-full rounded-lg border border-slate-700 bg-slate-900/90 py-1.5 pl-9 pr-8 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            />
            {helpQuery && (
              <button
                type="button"
                onClick={() => setHelpQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
                aria-label="Clear help search"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}

            {/* Live Search Dropdown */}
            {helpQuery.trim() && (
              <div className="absolute left-0 right-0 top-full mt-1.5 z-50 rounded-xl border border-slate-700 bg-slate-950/95 shadow-2xl shadow-black/70 backdrop-blur-md max-h-96 overflow-y-auto divide-y divide-slate-800/70">
                {searchResults.length === 0 ? (
                  <div className="p-3 text-xs text-slate-400">
                    No matching topics found for &ldquo;{helpQuery}&rdquo;.
                  </div>
                ) : (
                  searchResults.map((hit) => (
                    <button
                      key={hit.id}
                      type="button"
                      onClick={() => handleSelectSearchHit(hit)}
                      className="w-full text-left p-2.5 hover:bg-slate-900/90 transition-colors block"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-[10px] font-mono uppercase text-cyan-400">
                          {hit.category}
                        </span>
                        <ArrowRight className="h-3 w-3 text-slate-500" />
                      </div>
                      <div className="text-xs font-semibold text-slate-100 mt-0.5">
                        {hit.title}
                      </div>
                      <div className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">
                        {hit.snippet}
                      </div>
                    </button>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Interactive Learning Mode Switcher */}
        <div
          role="tablist"
          aria-label="Admin Guide Interactive Modes"
          className="flex flex-wrap items-center gap-1.5 pt-1 border-t border-slate-800/80"
        >
          {MODE_TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeMode === tab.id;
            return (
              <button
                key={tab.id}
                role="tab"
                type="button"
                aria-selected={active}
                onClick={() => {
                  setActiveMode(tab.id);
                  if (tab.id !== "troubleshooting") {
                    setHighlightedGlossaryId(null);
                    setHighlightedScenarioId(null);
                  }
                }}
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition-colors duration-75 ${
                  active
                    ? "border-cyan-500/70 bg-cyan-950/70 text-cyan-200 shadow-sm shadow-cyan-950/40 font-semibold"
                    : "border-slate-800 bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${active ? "text-cyan-400" : "text-slate-400"}`} />
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="sm:hidden">{tab.shortLabel}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Mode Content Panels */}
      {activeMode === "guided-tour" && (
        <GuidedTourSection onNavigateMode={(mode) => setActiveMode(mode)} />
      )}

      {activeMode === "architecture" && (
        <div className="space-y-4">
          <WorkflowFlowDiagram
            title="End-to-End AI Verdict Workflow (Governance Plane ↔ Runtime Investigation Plane)"
            subtitle="17-stage interactive pipeline separating AIS 2.0 Policy Creation & Governance from Runtime Triage, Guardrails, and Calibration Monitoring"
            steps={ARCHITECTURE_STEPS}
            edges={ARCHITECTURE_EDGES}
            swimlanes={ARCHITECTURE_SWIMLANES}
            initialStepId={architectureInitialStep}
            jumpNonce={jumpNonce}
          />

          {/* Cross-Lane Integration Bridges Summary */}
          <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                <Layers className="h-4 w-4 text-indigo-400" />
                Where Policy Governance &amp; Runtime Incident Investigation Connect
              </h3>
              <span className="text-[10px] font-mono text-indigo-300">
                4 Audited Cross-Plane Bridges
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 text-xs">
              <div className="rounded-lg border border-cyan-900/50 bg-cyan-950/15 p-3 space-y-1">
                <div className="text-[10px] font-mono font-bold text-cyan-300">
                  1. Telemetry Hub → Verdict Triage Agent
                </div>
                <p className="text-[11px] text-slate-300">
                  Ingested live incidents enter runtime evaluation via SentinelIngestWorker without mixing historical resolution fields into model payloads.
                </p>
              </div>
              <div className="rounded-lg border border-emerald-900/50 bg-emerald-950/15 p-3 space-y-1">
                <div className="text-[10px] font-mono font-bold text-emerald-300">
                  2. Approved Policy Registry → Verdict Triage Agent
                </div>
                <p className="text-[11px] text-slate-300">
                  Only <code className="font-mono">APPROVED</code> 9-section policies compiled by PolicyCompilerService can execute live inference; unapproved drafts trigger abstention.
                </p>
              </div>
              <div className="rounded-lg border border-indigo-900/50 bg-indigo-950/15 p-3 space-y-1">
                <div className="text-[10px] font-mono font-bold text-indigo-300">
                  3. Evidence Contract → Evidence Evaluation
                </div>
                <p className="text-[11px] text-slate-300">
                  The active RuleEvidenceContract dictates mandatory core fields checked by EvidencePreflightValidator and EvidenceSufficiencyEngine.
                </p>
              </div>
              <div className="rounded-lg border border-amber-900/50 bg-amber-950/15 p-3 space-y-1">
                <div className="text-[10px] font-mono font-bold text-amber-300">
                  4. Calibration &amp; Drift → Policy Generator
                </div>
                <p className="text-[11px] text-slate-300">
                  Diverged analyst feedback and SIEM rule changes create PolicyDriftEvents and inform candidate drafts—never silently altering live approved policies.
                </p>
              </div>
            </div>

            {/* Direct Workspace Shortcuts */}
            <div className="pt-2 border-t border-slate-800 flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-mono uppercase text-slate-400">
                Open Live Workspaces:
              </span>
              {PLATFORM_PAGE_LINKS.map((p) => (
                <Link
                  key={p.href}
                  href={p.href}
                  className="inline-flex items-center gap-1 rounded border border-slate-800 bg-slate-900/60 px-2 py-1 text-[10px] text-slate-300 hover:border-cyan-600/60 hover:text-cyan-300 transition-colors"
                >
                  <span>{p.title}</span>
                  <ExternalLink className="h-2.5 w-2.5" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeMode === "policy-lifecycle" && (
        <StudioGuideSection
          onJumpToGlossary={handleJumpToGlossary}
          highlightedGateId={highlightedGateId}
          jumpNonce={jumpNonce}
        />
      )}

      {activeMode === "decision-engine" && (
        <DecisionEngineSection
          onJumpToGlossary={handleJumpToGlossary}
          initialStepId={decisionInitialStep}
          jumpNonce={jumpNonce}
        />
      )}

      {activeMode === "incident-walkthrough" && (
        <IncidentWalkthroughSection onJumpToGlossary={handleJumpToGlossary} />
      )}

      {activeMode === "requirements" && <RequirementsSection />}

      {activeMode === "troubleshooting" && (
        <GlossaryTroubleshootingSection
          highlightedGlossaryId={highlightedGlossaryId}
          highlightedScenarioId={highlightedScenarioId}
          jumpNonce={jumpNonce}
        />
      )}
    </div>
  );
}

export default function AdminGuidePage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 text-xs text-slate-400">
          Loading AI Verdict Admin Guide...
        </div>
      }
    >
      <AdminGuideContent />
    </Suspense>
  );
}
