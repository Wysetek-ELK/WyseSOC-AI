"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  HelpCircle,
  BookOpen,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Search,
  CheckCircle2,
  AlertTriangle,
  Wrench,
  Compass,
} from "lucide-react";
import {
  GLOSSARY_ENTRIES,
  PLATFORM_PAGE_LINKS,
  TROUBLESHOOTING_SCENARIOS,
} from "@/data/admin-guide/glossaryAndTroubleshootingData";

interface GlossaryTroubleshootingSectionProps {
  highlightedGlossaryId?: string | null;
  highlightedScenarioId?: string | null;
}

export function GlossaryTroubleshootingSection({
  highlightedGlossaryId,
  highlightedScenarioId,
}: GlossaryTroubleshootingSectionProps) {
  const [expandedScenarioIds, setExpandedScenarioIds] = useState<Record<string, boolean>>(() => ({
    "ts-high-quality-g8-insufficient": true,
    ...(highlightedScenarioId ? { [highlightedScenarioId]: true } : {}),
  }));
  const [scenarioCategory, setScenarioCategory] = useState<string>("ALL");
  const [glossaryQuery, setGlossaryQuery] = useState<string>("");
  const [glossaryCategory, setGlossaryCategory] = useState<string>("ALL");

  useEffect(() => {
    if (highlightedGlossaryId) {
      const el = document.getElementById(`glossary-${highlightedGlossaryId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [highlightedGlossaryId]);

  const toggleScenario = (id: string) => {
    setExpandedScenarioIds((prev) => {
      const currentlyOpen =
        prev[id] !== undefined ? prev[id] : highlightedScenarioId === id;
      return { ...prev, [id]: !currentlyOpen };
    });
  };

  const filteredScenarios = useMemo(() => {
    return TROUBLESHOOTING_SCENARIOS.filter((sc) =>
      scenarioCategory === "ALL" ? true : sc.category === scenarioCategory
    );
  }, [scenarioCategory]);

  const filteredGlossary = useMemo(() => {
    const q = glossaryQuery.trim().toLowerCase();
    return GLOSSARY_ENTRIES.filter((entry) => {
      if (glossaryCategory !== "ALL" && entry.category !== glossaryCategory) return false;
      if (!q) return true;
      return (
        entry.term.toLowerCase().includes(q) ||
        entry.definition.toLowerCase().includes(q) ||
        entry.codeReference.toLowerCase().includes(q) ||
        (entry.aliases || []).some((a) => a.toLowerCase().includes(q))
      );
    });
  }, [glossaryQuery, glossaryCategory]);

  return (
    <div className="space-y-5">
      {/* 1. Expandable Troubleshooting Examples */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Wrench className="h-4 w-4 text-amber-400" />
              Troubleshooting &amp; Diagnostic Playbook
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Expandable explanations for Quality Score vs G8 status, abstentions on FP incidents, missing labels, trustworthiness caps, and V1/V2 divergence.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-1 rounded-md border border-slate-700 bg-slate-900 p-0.5 text-[10px] font-mono">
            {["ALL", "Policy & Gates", "Verdict & Trust", "Simulation & Metrics", "Operations"].map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setScenarioCategory(cat)}
                className={`px-2 py-0.5 rounded transition-colors ${
                  scenarioCategory === cat
                    ? "bg-cyan-600/30 text-cyan-300 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="space-y-2.5">
          {filteredScenarios.map((sc) => {
            const isOpen =
              expandedScenarioIds[sc.id] !== undefined
                ? Boolean(expandedScenarioIds[sc.id])
                : highlightedScenarioId === sc.id;
            const isHighlighted = highlightedScenarioId === sc.id;
            return (
              <div
                key={sc.id}
                id={`scenario-${sc.id}`}
                className={`rounded-lg border transition-colors ${
                  isHighlighted
                    ? "border-cyan-400 bg-cyan-950/20"
                    : isOpen
                    ? "border-amber-700/50 bg-slate-900/50"
                    : "border-slate-800 bg-slate-900/30"
                }`}
              >
                <button
                  type="button"
                  onClick={() => toggleScenario(sc.id)}
                  className="w-full flex items-center justify-between gap-2 px-3.5 py-2.5 text-left"
                  aria-expanded={isOpen}
                >
                  <div className="flex items-center gap-2">
                    {isOpen ? (
                      <ChevronDown className="h-4 w-4 text-amber-400 shrink-0" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-slate-400 shrink-0" />
                    )}
                    <span className="text-xs font-bold text-slate-100">{sc.question}</span>
                  </div>
                  <span className="shrink-0 rounded border border-slate-700 bg-slate-950 px-2 py-0.5 text-[9px] font-mono text-slate-400">
                    {sc.category}
                  </span>
                </button>

                {isOpen && (
                  <div className="border-t border-slate-800/80 px-3.5 py-3 space-y-3 text-xs">
                    <div className="rounded border border-cyan-900/50 bg-cyan-950/20 p-2.5 text-[11px] text-cyan-100 leading-relaxed">
                      <strong className="text-cyan-300">Direct Explanation:</strong> {sc.shortAnswer}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                      <div className="rounded border border-slate-800 bg-slate-950/70 p-2.5 space-y-1">
                        <div className="text-[10px] font-mono font-bold uppercase text-amber-300">
                          Why This Happens
                        </div>
                        <ul className="space-y-1 text-[11px] text-slate-300">
                          {sc.rootCauses.map((rc, i) => (
                            <li key={i} className="flex items-start gap-1.5">
                              <AlertTriangle className="h-3 w-3 text-amber-400 shrink-0 mt-0.5" />
                              <span>{rc}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="rounded border border-slate-800 bg-slate-950/70 p-2.5 space-y-1">
                        <div className="text-[10px] font-mono font-bold uppercase text-indigo-300">
                          System Behavior
                        </div>
                        <ul className="space-y-1 text-[11px] text-slate-300">
                          {sc.howSystemBehaves.map((hb, i) => (
                            <li key={i} className="flex items-start gap-1.5">
                              <span className="text-indigo-400 mt-0.5">•</span>
                              <span>{hb}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="rounded border border-slate-800 bg-slate-950/70 p-2.5 space-y-1">
                        <div className="text-[10px] font-mono font-bold uppercase text-emerald-300">
                          Admin Remediation Steps
                        </div>
                        <ul className="space-y-1 text-[11px] text-slate-300">
                          {sc.adminResolutionSteps.map((step, i) => (
                            <li key={i} className="flex items-start gap-1.5">
                              <CheckCircle2 className="h-3 w-3 text-emerald-400 shrink-0 mt-0.5" />
                              <span>{step}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {sc.relatedRoute && (
                      <div className="flex justify-end">
                        <Link
                          href={sc.relatedRoute}
                          className="inline-flex items-center gap-1 rounded-md border border-cyan-700/60 bg-cyan-950/50 px-2.5 py-1 text-[11px] font-semibold text-cyan-300 hover:bg-cyan-900/60"
                        >
                          <span>{sc.relatedRouteLabel || "Open Workspace"}</span>
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Searchable Platform Terminology Glossary */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2.5">
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-cyan-400" />
              Terminology &amp; Architecture Glossary ({filteredGlossary.length} Terms)
            </h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Hover or click underlined terms anywhere in the Admin Guide for inline definitions, or filter below.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
              <input
                type="text"
                value={glossaryQuery}
                onChange={(e) => setGlossaryQuery(e.target.value)}
                placeholder="Filter glossary terms..."
                className="rounded-md border border-slate-700 bg-slate-900 pl-8 pr-3 py-1 text-xs text-slate-200 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
              />
            </div>

            <select
              value={glossaryCategory}
              onChange={(e) => setGlossaryCategory(e.target.value)}
              className="rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none"
              aria-label="Filter glossary category"
            >
              <option value="ALL">All Categories</option>
              <option value="Architecture">Architecture</option>
              <option value="AIS 2.0 & Gates">AIS 2.0 &amp; Gates</option>
              <option value="Decision & Trust">Decision &amp; Trust</option>
              <option value="Empirical & Stats">Empirical &amp; Stats</option>
              <option value="Operations">Operations</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
          {filteredGlossary.map((entry) => {
            const isHighlighted = highlightedGlossaryId === entry.id;
            return (
              <div
                key={entry.id}
                id={`glossary-${entry.id}`}
                className={`rounded-lg border p-3 space-y-1.5 transition-colors ${
                  isHighlighted
                    ? "border-cyan-400 bg-cyan-950/30 ring-1 ring-cyan-400/50"
                    : "border-slate-800 bg-slate-900/40"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="text-xs font-bold text-cyan-300 flex items-center gap-1">
                    <HelpCircle className="h-3.5 w-3.5 shrink-0" />
                    <span>{entry.term}</span>
                  </div>
                  <span className="shrink-0 rounded bg-slate-950 border border-slate-800 px-1.5 py-0.5 text-[9px] font-mono text-slate-400">
                    {entry.category}
                  </span>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed">{entry.definition}</p>
                <div className="text-[10px] font-mono text-slate-500 border-t border-slate-800/70 pt-1">
                  {entry.codeReference}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Direct Platform Navigation Matrix */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div>
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Compass className="h-4 w-4 text-cyan-400" />
            Direct Navigation to Existing AI Verdict Workspaces
          </h3>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Jump directly to live operational, intelligence, simulation, or platform control views.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
          {PLATFORM_PAGE_LINKS.map((page) => (
            <Link
              key={page.href}
              href={page.href}
              className="group rounded-lg border border-slate-800 bg-slate-900/40 hover:border-cyan-500/60 hover:bg-slate-900/80 p-3 space-y-1 transition-all"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-[9px] font-mono uppercase text-cyan-400">{page.category}</span>
                <ExternalLink className="h-3 w-3 text-slate-500 group-hover:text-cyan-300" />
              </div>
              <div className="text-xs font-bold text-slate-100 group-hover:text-cyan-200">
                {page.title}
              </div>
              <p className="text-[11px] text-slate-400 leading-snug">{page.summary}</p>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
