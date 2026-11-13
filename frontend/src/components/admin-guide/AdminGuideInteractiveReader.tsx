"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  LayoutDashboard,
  AlertTriangle,
  UploadCloud,
  UserCheck,
  MessageSquareCode,
  Cpu,
  FileCode2,
  Brain,
  FlaskConical,
  BarChart3,
  Server,
  Settings,
  ShieldCheck,
  BookOpenCheck,
  Search,
  X,
  ExternalLink,
  ChevronRight,
  ChevronLeft,
  CheckCircle2,
  HelpCircle,
  Shield,
  ArrowRight,
  Workflow,
  Info,
  ListOrdered,
  Lock,
  Layers,
  Sparkles,
  Database,
  Radio,
  FileText,
  AlertCircle,
} from "lucide-react";
import {
  ALL_GUIDE_PAGES,
  WORKFLOW_STAGES,
  GuidePageDetail,
  WorkflowStageDetail,
} from "@/data/admin-guide/pagesGuideData";

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  "agent-mission-control": LayoutDashboard,
  "ai-triage-workbench": AlertTriangle,
  "telemetry-hub": UploadCloud,
  "human-review-queue": UserCheck,
  "soc-chatbot": MessageSquareCode,
  "agent-intelligence-studio": Cpu,
  "detection-intelligence": FileCode2,
  "agent-memory": Brain,
  "agent-simulation-lab": FlaskConical,
  "verdict-intelligence": BarChart3,
  "inference-control": Server,
  "agent-configuration": Settings,
  "governance-access": ShieldCheck,
  "admin-guide": BookOpenCheck,
};

const GROUP_ORDER = [
  "SOC OPERATIONS",
  "AGENT INTELLIGENCE",
  "VALIDATION & TRUST",
  "PLATFORM CONTROL",
] as const;

export function AdminGuideInteractiveReader() {
  const [selectedId, setSelectedId] = useState<string>("workflow");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [activeStageStep, setActiveStageStep] = useState<number>(1);

  // Group pages by groupTitle
  const groupedPages = useMemo(() => {
    const map = new Map<string, GuidePageDetail[]>();
    GROUP_ORDER.forEach((grp) => map.set(grp, []));

    ALL_GUIDE_PAGES.forEach((page) => {
      const list = map.get(page.groupTitle) || [];
      list.push(page);
      map.set(page.groupTitle, list);
    });

    return map;
  }, []);

  // Filtered pages based on search
  const searchResults = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return null;

    return ALL_GUIDE_PAGES.filter(
      (page) =>
        page.title.toLowerCase().includes(q) ||
        page.slug.toLowerCase().includes(q) ||
        page.whatIsThis.toLowerCase().includes(q) ||
        page.whyDoWeNeedIt.toLowerCase().includes(q) ||
        page.practicalUseCase.toLowerCase().includes(q) ||
        page.howToUse.some((step) => step.toLowerCase().includes(q))
    );
  }, [searchQuery]);

  // Current page or workflow
  const currentPage = useMemo(() => {
    return ALL_GUIDE_PAGES.find((p) => p.slug === selectedId || p.id === selectedId);
  }, [selectedId]);

  // Navigation: flat sequence [workflow, ...ALL_GUIDE_PAGES]
  const sequence = useMemo(() => {
    return [
      { id: "workflow", slug: "workflow", title: "How Verdictum AI Works" },
      ...ALL_GUIDE_PAGES.map((p) => ({ id: p.id, slug: p.slug, title: p.title })),
    ];
  }, []);

  const currentIndex = sequence.findIndex((item) => item.slug === selectedId || item.id === selectedId);
  const prevItem = currentIndex > 0 ? sequence[currentIndex - 1] : null;
  const nextItem = currentIndex < sequence.length - 1 ? sequence[currentIndex + 1] : null;

  return (
    <div className="flex flex-col lg:flex-row gap-6 min-h-[calc(100vh-140px)]">
      {/* LEFT SIDEBAR: Table of Contents & Search */}
      <aside className="w-full lg:w-80 shrink-0 flex flex-col gap-4">
        {/* Search Input */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search pages, steps, keywords..."
            className="w-full pl-9 pr-9 py-2.5 bg-slate-900 border border-slate-700/80 rounded-lg text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500 transition-all"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Navigation List */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3 flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-220px)] shadow-lg shadow-black/20">
          {/* Top Item: How Verdictum AI Works */}
          <div>
            <button
              onClick={() => {
                setSelectedId("workflow");
                setSearchQuery("");
              }}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                selectedId === "workflow"
                  ? "bg-gradient-to-r from-sky-600 to-indigo-600 text-white shadow-md shadow-sky-900/30"
                  : "text-slate-300 hover:bg-slate-800/80 hover:text-white"
              }`}
            >
              <Workflow className="w-4 h-4 shrink-0 text-sky-400" />
              <span className="truncate">How Verdictum AI Works</span>
              <span className="ml-auto text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-sky-950/70 border border-sky-800/60 text-sky-300">
                Core
              </span>
            </button>
          </div>

          {/* Search Hits Dropdown (if searching) */}
          {searchResults !== null ? (
            <div className="flex flex-col gap-1.5">
              <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 px-2 py-1">
                Matching Pages ({searchResults.length})
              </div>
              {searchResults.length === 0 ? (
                <div className="text-xs text-slate-400 px-3 py-4 text-center">
                  No matching pages or workflows found.
                </div>
              ) : (
                searchResults.map((page) => {
                  const PageIcon = ICON_MAP[page.slug] || FileText;
                  const isSelected = selectedId === page.slug;
                  return (
                    <button
                      key={page.slug}
                      onClick={() => setSelectedId(page.slug)}
                      className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left text-xs transition-all ${
                        isSelected
                          ? "bg-sky-500/20 text-sky-200 border border-sky-500/40 font-medium"
                          : "text-slate-300 hover:bg-slate-800 hover:text-slate-100"
                      }`}
                    >
                      <PageIcon className="w-3.5 h-3.5 shrink-0 text-sky-400" />
                      <div className="truncate">
                        <div className="truncate font-medium">{page.title}</div>
                        <div className="text-[10px] text-slate-400 truncate">{page.groupTitle}</div>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          ) : (
            /* Standard Grouped Navigation */
            GROUP_ORDER.map((group) => {
              const pages = groupedPages.get(group) || [];
              return (
                <div key={group} className="flex flex-col gap-1">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 py-1 flex items-center justify-between">
                    <span>{group}</span>
                    <span className="text-slate-400 font-mono text-[9px]">{pages.length}</span>
                  </div>
                  {pages.map((page) => {
                    const PageIcon = ICON_MAP[page.slug] || FileText;
                    const isSelected = selectedId === page.slug;
                    return (
                      <button
                        key={page.slug}
                        onClick={() => setSelectedId(page.slug)}
                        className={`w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left text-xs transition-all ${
                          isSelected
                            ? "bg-sky-600/20 text-sky-200 border border-sky-500/40 font-medium shadow-sm"
                            : "text-slate-300 hover:bg-slate-800/70 hover:text-slate-100"
                        }`}
                      >
                        <PageIcon className="w-3.5 h-3.5 shrink-0 text-sky-400" />
                        <span className="truncate">{page.title}</span>
                        {page.badge && (
                          <span
                            className={`ml-auto text-[9px] font-semibold px-1 py-0.2 rounded border ${page.badgeColor}`}
                          >
                            {page.badge}
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="flex-1 bg-slate-900/60 border border-slate-800 rounded-xl p-6 lg:p-8 flex flex-col gap-6 shadow-xl shadow-black/30">
        {selectedId === "workflow" ? (
          /* ========================================================================= */
          /* SECTION 1: HOW VERDICTUM AI WORKS (End-to-End Workflow)                   */
          /* ========================================================================= */
          <div className="flex flex-col gap-8">
            {/* Header */}
            <div className="border-b border-slate-800 pb-5">
              <div className="flex items-center gap-2 text-xs font-semibold text-sky-400 uppercase tracking-wider mb-1">
                <Workflow className="w-4 h-4" />
                End-to-End System Architecture
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight">
                How Verdictum AI Works
              </h1>
              <p className="text-slate-300 text-sm mt-2 max-w-3xl leading-relaxed">
                Verdictum AI operates on a strict human-in-the-loop, evidence-validated pipeline.
                Security incidents are ingested from FortiSIEM, triaged by on-prem local AI, validated
                against source facts, and independently evaluated by SOC analysts to continuously qualify
                detection rules for production.
              </p>
            </div>

            {/* Visual Workflow Diagram */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-6 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-sky-400" />
                  Interactive Workflow Pipeline (7 Core Stages)
                </h3>
                <span className="text-[11px] text-slate-400">Click any stage to view details</span>
              </div>

              {/* Stage Flow Nodes */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
                {WORKFLOW_STAGES.map((st) => {
                  const isActive = activeStageStep === st.stepNumber;
                  return (
                    <button
                      key={st.stepNumber}
                      onClick={() => setActiveStageStep(st.stepNumber)}
                      className={`flex flex-col gap-1.5 p-3.5 rounded-lg border text-left transition-all ${
                        isActive
                          ? "bg-sky-500/15 border-sky-500 text-white shadow-md shadow-sky-950/50"
                          : "bg-slate-900/80 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-850"
                      }`}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono text-sky-400 font-bold">Stage {st.stepNumber}</span>
                        {isActive && <CheckCircle2 className="w-3.5 h-3.5 text-sky-400" />}
                      </div>
                      <div className="text-xs font-semibold leading-snug">{st.title}</div>
                      <div className="text-[11px] text-slate-400 line-clamp-2 mt-0.5">
                        {st.shortDescription}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Active Stage Details Card */}
            {(() => {
              const currentStage =
                WORKFLOW_STAGES.find((s) => s.stepNumber === activeStageStep) || WORKFLOW_STAGES[0];
              return (
                <div className="bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 rounded-xl p-6 flex flex-col gap-5">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                    <div>
                      <div className="text-xs font-semibold text-sky-400 uppercase tracking-wider">
                        Stage {currentStage.stepNumber} of 7
                      </div>
                      <h2 className="text-xl font-bold text-white mt-1">{currentStage.title}</h2>
                    </div>
                    <Link
                      href={currentStage.targetUIPage.route}
                      className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-medium transition-all shadow-sm shrink-0"
                    >
                      <span>Open {currentStage.targetUIPage.title}</span>
                      <ExternalLink className="w-3.5 h-3.5" />
                    </Link>
                  </div>

                  <div className="flex flex-col gap-3">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Technical & Operational Description
                    </h4>
                    <p className="text-sm text-slate-300 leading-relaxed">
                      {currentStage.detailedExplanation}
                    </p>
                  </div>

                  {/* Incident #176061 Walkthrough Example */}
                  <div className="bg-slate-950/80 border border-slate-800/90 rounded-lg p-4 flex flex-col gap-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-amber-400">
                      <Sparkles className="w-3.5 h-3.5" />
                      Incident Walkthrough (Incident #176061)
                    </div>
                    <p className="text-xs font-mono text-slate-300 leading-relaxed">
                      {currentStage.exampleWalkthrough}
                    </p>
                  </div>

                  {/* Offline Resilience Behavior */}
                  <div className="bg-emerald-950/20 border border-emerald-800/40 rounded-lg p-4 flex flex-col gap-2">
                    <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
                      <Shield className="w-3.5 h-3.5" />
                      Offline Mode & Outage Behavior
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">
                      {currentStage.offlineBehavior}
                    </p>
                  </div>
                </div>
              );
            })()}

            {/* Offline LLM Behavior Summary Callout */}
            <div className="bg-amber-950/20 border border-amber-800/50 rounded-xl p-5 flex flex-col sm:flex-row items-start gap-4">
              <AlertCircle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
              <div className="flex flex-col gap-1.5 text-xs text-slate-300 leading-relaxed">
                <span className="font-bold text-amber-300 text-sm">
                  What happens when the Server 2 LLM server is offline?
                </span>
                <p>
                  Verdictum AI never produces hallucinations or unverified automated closures during an
                  inference outage. Ingested incidents bypass LLM triage and are tagged with{" "}
                  <code className="text-amber-300 bg-amber-950/50 px-1 py-0.5 rounded font-mono">
                    LLM_OFFLINE_ADVISORY
                  </code>
                  . Incidents remain open in the Human Review Queue where analysts conduct standard
                  independent investigations.
                </p>
              </div>
            </div>
          </div>
        ) : currentPage ? (
          /* ========================================================================= */
          /* SECTION 2: INDIVIDUAL SIDEBAR PAGE (1 OF 14)                              */
          /* ========================================================================= */
          <div className="flex flex-col gap-8">
            {/* Page Header */}
            <div className="border-b border-slate-800 pb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold text-sky-400 uppercase tracking-wider mb-1">
                  <span>{currentPage.groupTitle}</span>
                  <span>•</span>
                  <span className="font-mono text-slate-400">{currentPage.route}</span>
                </div>
                <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight flex items-center gap-3">
                  {currentPage.title}
                  {currentPage.badge && (
                    <span
                      className={`text-xs font-semibold px-2 py-0.5 rounded border ${currentPage.badgeColor}`}
                    >
                      {currentPage.badge}
                    </span>
                  )}
                </h1>
                <div className="mt-2 flex items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                    <CheckCircle2 className="w-3 h-3" />
                    {currentPage.implementationStatus === "FULLY_AVAILABLE"
                      ? "Fully Available"
                      : "Available with Offline Fallback"}
                  </span>
                  <span className="text-xs text-slate-400">{currentPage.statusDescription}</span>
                </div>
              </div>

              {/* Direct Open Link */}
              <Link
                href={currentPage.route}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition-all shadow-md shadow-sky-900/30 shrink-0 self-start sm:self-center"
              >
                <span>Open in Verdictum AI</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </Link>
            </div>

            {/* 7 Standardized Sections */}
            <div className="grid grid-cols-1 gap-6">
              {/* 1. What is this page? */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-5 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-bold text-sky-400 uppercase tracking-wider">
                  <Info className="w-4 h-4" />
                  1. What is this page?
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-normal">
                  {currentPage.whatIsThis}
                </p>
              </div>

              {/* 2. Why do we need it? */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-5 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                  <HelpCircle className="w-4 h-4" />
                  2. Why do we need it?
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-normal">
                  {currentPage.whyDoWeNeedIt}
                </p>
              </div>

              {/* 3. Practical Use Case */}
              <div className="bg-gradient-to-br from-amber-950/20 to-slate-950 border border-amber-800/30 rounded-xl p-5 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-400 uppercase tracking-wider">
                  <Sparkles className="w-4 h-4" />
                  3. Practical SOC Use Case
                </div>
                <p className="text-sm text-amber-100/90 leading-relaxed font-normal">
                  {currentPage.practicalUseCase}
                </p>
              </div>

              {/* 4. How to Use (Step-by-Step) */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-5 flex flex-col gap-3">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-wider">
                  <ListOrdered className="w-4 h-4" />
                  4. How to Use (Step-by-Step Instructions)
                </div>
                <div className="flex flex-col gap-2.5 pt-1">
                  {currentPage.howToUse.map((step, idx) => (
                    <div key={idx} className="flex items-start gap-3 text-xs text-slate-300">
                      <span className="w-5 h-5 rounded-full bg-emerald-950 border border-emerald-700/80 text-emerald-300 font-bold flex items-center justify-center shrink-0 text-[10px]">
                        {idx + 1}
                      </span>
                      <span className="mt-0.5 leading-relaxed">{step}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 5. Prerequisites */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-5 flex flex-col gap-3">
                <div className="flex items-center gap-2 text-xs font-bold text-purple-400 uppercase tracking-wider">
                  <Lock className="w-4 h-4" />
                  5. Prerequisites & Requirements
                </div>
                <div className="flex flex-col gap-2 pt-1">
                  {currentPage.prerequisites.map((req, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-300">
                      <CheckCircle2 className="w-3.5 h-3.5 text-purple-400 shrink-0 mt-0.5" />
                      <span className="leading-relaxed">{req}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 6. Expected Result */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-5 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-xs font-bold text-cyan-400 uppercase tracking-wider">
                  <CheckCircle2 className="w-4 h-4" />
                  6. Expected Result
                </div>
                <p className="text-sm text-cyan-100/90 leading-relaxed font-normal">
                  {currentPage.expectedResult}
                </p>
              </div>

              {/* 7. Related Pages */}
              <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-5 flex flex-col gap-3">
                <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
                  <Layers className="w-4 h-4" />
                  7. Related Pages & Workflows
                </div>
                <div className="flex flex-wrap gap-2 pt-1">
                  {currentPage.relatedPages.map((rel, idx) => (
                    <button
                      key={idx}
                      onClick={() => {
                        const targetSlug = rel.route.replace(/^\//, "");
                        setSelectedId(targetSlug);
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700/80 hover:border-sky-500 hover:text-sky-300 text-xs text-slate-300 transition-all font-medium"
                    >
                      <span>{rel.title}</span>
                      <ArrowRight className="w-3 h-3 text-slate-400" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {/* BOTTOM NAVIGATION: Previous / Next Buttons */}
        <div className="border-t border-slate-800 pt-5 mt-auto flex items-center justify-between">
          {prevItem ? (
            <button
              onClick={() => setSelectedId(prevItem.slug)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-850 hover:bg-slate-800 border border-slate-700/70 text-xs font-semibold text-slate-200 transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Previous: {prevItem.title}</span>
            </button>
          ) : (
            <div />
          )}

          {nextItem && (
            <button
              onClick={() => setSelectedId(nextItem.slug)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-850 hover:bg-slate-800 border border-slate-700/70 text-xs font-semibold text-slate-200 transition-all ml-auto"
            >
              <span>Next: {nextItem.title}</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
