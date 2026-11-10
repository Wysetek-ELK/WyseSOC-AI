"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ExternalLink,
  RefreshCw,
  Info,
  ShieldCheck,
  Filter,
  Server,
} from "lucide-react";
import { REQUIREMENT_DOMAINS } from "@/data/admin-guide/requirementsData";
import type { RequirementCriticality } from "@/data/admin-guide/types";
import { useApp } from "@/context/AppContext";

interface LiveReadOnlyStatus {
  checkedAt: string;
  available: boolean;
  reason?: string;
  fortisiem?: { is_configured: boolean; mode: string; host: string } | null;
  llm?: { is_healthy: boolean; model?: string; status?: string } | null;
  policies?: {
    total_rules: number;
    rules_with_approved_policies: number;
    policies_with_critical_issues: number;
  } | null;
  verdictMetrics?: {
    total_evaluated_incidents: number;
    analyst_attention_decisions: number;
    low_trust_verdicts_count: number;
  } | null;
}

async function safeReadOnlyGet<T>(url: string): Promise<T | null> {
  try {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("ai_verdict_token") : null;
    const headers: Record<string, string> = {};
    if (token) headers.Authorization = `Bearer ${token}`;

    const res = await fetch(url, {
      method: "GET",
      credentials: "include",
      headers,
    });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export function RequirementsSection() {
  const { user } = useApp();
  const [criticalityFilter, setCriticalityFilter] = useState<"ALL" | RequirementCriticality>("ALL");
  const [liveStatus, setLiveStatus] = useState<LiveReadOnlyStatus | null>(null);
  const [checkingLive, setCheckingLive] = useState<boolean>(false);

  const fetchReadOnlySnapshot = useCallback(async (): Promise<LiveReadOnlyStatus> => {
    const [forti, llm, pol, vm] = await Promise.all([
      safeReadOnlyGet<{ is_configured: boolean; mode: string; host: string }>("/api/fortisiem/status"),
      safeReadOnlyGet<{ is_healthy: boolean; model?: string; status?: string }>("/api/dashboard/llm-status"),
      safeReadOnlyGet<{
        total_rules: number;
        rules_with_approved_policies: number;
        policies_with_critical_issues: number;
      }>("/api/prompts/quality/summary"),
      safeReadOnlyGet<{
        total_evaluated_incidents: number;
        analyst_attention_decisions: number;
        low_trust_verdicts_count: number;
      }>("/api/verdict-intelligence/metrics/summary"),
    ]);

    const anyOk = Boolean(forti || llm || pol || vm);
    return {
      checkedAt: new Date().toLocaleTimeString(),
      available: anyOk,
      reason: anyOk
        ? undefined
        : user
        ? "Read-only status endpoints did not return data."
        : "Sign in or connect backend API to view optional read-only status.",
      fortisiem: forti,
      llm,
      policies: pol,
      verdictMetrics: vm,
    };
  }, [user]);

  const loadReadOnlyStatus = async () => {
    setCheckingLive(true);
    try {
      const snapshot = await fetchReadOnlySnapshot();
      setLiveStatus(snapshot);
    } finally {
      setCheckingLive(false);
    }
  };

  useEffect(() => {
    if (!user) return;
    let active = true;
    fetchReadOnlySnapshot().then((snapshot) => {
      if (active) setLiveStatus(snapshot);
    });
    return () => {
      active = false;
    };
  }, [user, fetchReadOnlySnapshot]);

  const badgeForCriticality = (crit: RequirementCriticality) => {
    switch (crit) {
      case "REQUIRED":
        return "bg-rose-950/80 text-rose-300 border-rose-700/70";
      case "CONDITIONAL":
        return "bg-amber-950/80 text-amber-300 border-amber-700/70";
      case "OPTIONAL":
        return "bg-sky-950/80 text-sky-300 border-sky-700/70";
    }
  };

  const renderLiveStatusPill = (key?: "fortisiem" | "llm" | "policies" | "verdict_metrics") => {
    if (!key) return null;
    if (!liveStatus?.available) {
      return (
        <span className="rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 text-[9px] font-mono text-slate-400">
          Doc Reference Only
        </span>
      );
    }

    if (key === "fortisiem" && liveStatus.fortisiem) {
      return (
        <span
          className={`rounded border px-1.5 py-0.5 text-[9px] font-mono ${
            liveStatus.fortisiem.is_configured
              ? "bg-emerald-950/80 text-emerald-300 border-emerald-700/60"
              : "bg-amber-950/80 text-amber-300 border-amber-700/60"
          }`}
        >
          Live Read-Only: {liveStatus.fortisiem.mode}
        </span>
      );
    }
    if (key === "llm" && liveStatus.llm) {
      return (
        <span
          className={`rounded border px-1.5 py-0.5 text-[9px] font-mono ${
            liveStatus.llm.is_healthy
              ? "bg-emerald-950/80 text-emerald-300 border-emerald-700/60"
              : "bg-amber-950/80 text-amber-300 border-amber-700/60"
          }`}
        >
          Live Read-Only: {liveStatus.llm.is_healthy ? "ONLINE" : "OFFLINE"}
        </span>
      );
    }
    if (key === "policies" && liveStatus.policies) {
      return (
        <span className="rounded border border-cyan-800/60 bg-cyan-950/70 px-1.5 py-0.5 text-[9px] font-mono text-cyan-300">
          Live Read-Only: {liveStatus.policies.rules_with_approved_policies}/{liveStatus.policies.total_rules} Rules Approved
        </span>
      );
    }
    if (key === "verdict_metrics" && liveStatus.verdictMetrics) {
      return (
        <span className="rounded border border-indigo-800/60 bg-indigo-950/70 px-1.5 py-0.5 text-[9px] font-mono text-indigo-300">
          Live Read-Only: {liveStatus.verdictMetrics.total_evaluated_incidents} Evaluated
        </span>
      );
    }
    return (
      <span className="rounded border border-slate-700 bg-slate-900 px-1.5 py-0.5 text-[9px] font-mono text-slate-400">
        Doc Reference Only
      </span>
    );
  };

  return (
    <div className="space-y-4">
      {/* Header + Read-Only Live Check Banner */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-cyan-400" />
              Requirements &amp; Admin Setup Guide (11 Operational Domains)
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              What administrators must configure or verify at every stage, criticality levels, and the exact operational impact if omitted.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Filter by Criticality */}
            <div className="flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 p-0.5 text-[10px] font-mono">
              <Filter className="h-3 w-3 text-slate-400 ml-1" />
              {(["ALL", "REQUIRED", "CONDITIONAL", "OPTIONAL"] as const).map((lvl) => (
                <button
                  key={lvl}
                  type="button"
                  onClick={() => setCriticalityFilter(lvl)}
                  className={`px-2 py-0.5 rounded transition-colors ${
                    criticalityFilter === lvl
                      ? "bg-cyan-600/30 text-cyan-300 font-bold"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {lvl}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={loadReadOnlyStatus}
              disabled={checkingLive}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-2.5 py-1 text-[11px] text-slate-200 hover:bg-slate-800 disabled:opacity-60"
            >
              <RefreshCw className={`h-3 w-3 ${checkingLive ? "animate-spin" : ""}`} />
              <span>{checkingLive ? "Checking..." : "Check Read-Only Status"}</span>
            </button>
          </div>
        </div>

        {/* Read-Only Status Summary Box */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-start gap-2">
            <Server className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
            <div>
              <div className="font-semibold text-slate-200 flex items-center gap-2">
                <span>Optional Read-Only Environment Status</span>
                {liveStatus && (
                  <span
                    className={`text-[10px] font-mono ${
                      liveStatus.available ? "text-emerald-400" : "text-amber-400"
                    }`}
                  >
                    Last checked {liveStatus.checkedAt}
                  </span>
                )}
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5">
                {liveStatus?.available
                  ? "Showing actual read-only values from existing GET endpoints. Items without live probes remain labeled as documentation."
                  : liveStatus?.reason ||
                    "Requirements below are reference documentation, not live health checks."}
              </p>
            </div>
          </div>

          {liveStatus?.available && (
            <div className="flex flex-wrap gap-2 text-[10px] font-mono">
              {liveStatus.fortisiem && (
                <span className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-300">
                  FortiSIEM:{" "}
                  <strong className={liveStatus.fortisiem.is_configured ? "text-emerald-300" : "text-amber-300"}>
                    {liveStatus.fortisiem.mode}
                  </strong>
                </span>
              )}
              {liveStatus.llm && (
                <span className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-300">
                  Server 2 LLM:{" "}
                  <strong className={liveStatus.llm.is_healthy ? "text-emerald-300" : "text-amber-300"}>
                    {liveStatus.llm.is_healthy ? "HEALTHY" : "OFFLINE"}
                  </strong>
                </span>
              )}
              {liveStatus.policies && (
                <span className="rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-300">
                  Approved Rules:{" "}
                  <strong className="text-cyan-300">
                    {liveStatus.policies.rules_with_approved_policies}/{liveStatus.policies.total_rules}
                  </strong>
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 11 Prerequisite Domain Cards */}
      <div className="space-y-3">
        {REQUIREMENT_DOMAINS.map((domain) => {
          const items = domain.items.filter((it) =>
            criticalityFilter === "ALL" ? true : it.criticality === criticalityFilter
          );
          if (items.length === 0) return null;

          return (
            <div
              key={domain.id}
              id={domain.id}
              className="rounded-xl border border-slate-800 bg-slate-950/90 p-4 space-y-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-2">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400">
                    Domain {domain.domainNumber} · {domain.stageTag}
                  </span>
                  <h3 className="text-sm font-bold text-slate-100">{domain.title}</h3>
                  <p className="text-[11px] text-slate-400 mt-0.5">{domain.summary}</p>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-2.5">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="rounded-lg border border-slate-800 bg-slate-900/40 p-3 space-y-2 text-xs"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="font-bold text-slate-100 leading-snug">{item.title}</div>
                      <div className="flex flex-wrap items-center gap-1.5 shrink-0">
                        {renderLiveStatusPill(item.liveStatusKey)}
                        <span
                          className={`rounded border px-1.5 py-0.5 text-[9px] font-mono font-bold ${badgeForCriticality(
                            item.criticality
                          )}`}
                        >
                          {item.criticality}
                        </span>
                      </div>
                    </div>

                    <p className="text-[11px] text-slate-300 leading-relaxed">{item.description}</p>

                    <div className="rounded border border-rose-900/40 bg-rose-950/15 p-2 text-[11px] text-rose-200/90">
                      <strong className="text-rose-300">If Missing:</strong>{" "}
                      {item.consequenceIfMissing}
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[10px] text-slate-400 border-t border-slate-800/80">
                      <span>
                        <strong className="text-slate-300">Verify:</strong> {item.verificationCheck}
                      </span>
                      {item.route && (
                        <Link
                          href={item.route}
                          className="inline-flex items-center gap-1 font-semibold text-cyan-400 hover:text-cyan-300 shrink-0"
                        >
                          <span>{item.routeLabel || "Configure"}</span>
                          <ExternalLink className="h-2.5 w-2.5" />
                        </Link>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Explicit Documentation Disclaimer */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3 flex items-start gap-2 text-[11px] text-slate-400">
        <Info className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
        <span>
          Documentation Notice: Requirements marked <code className="font-mono text-slate-300">Doc Reference Only</code> describe static administrative prerequisites and are not live health probes. No configuration or policy data is modified from this guide.
        </span>
      </div>
    </div>
  );
}
