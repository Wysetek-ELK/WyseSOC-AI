"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Cpu,
  Layers,
  Activity,
  Clock,
  Sparkles,
  RefreshCw,
  Database,
  ArrowRight,
  TrendingUp,
  BarChart3,
  Bot,
  Zap,
} from "lucide-react";
import { api, TokenAnalyticsResponse, TokenProcessBifurcation, TokenModelBifurcation, TokenLedgerItem } from "@/lib/api";

export function TokenBifurcationWidget() {
  const [data, setData] = useState<TokenAnalyticsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [windowDays, setWindowDays] = useState<number>(30);
  const [selectedProcess, setSelectedProcess] = useState<string>("ALL");

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const pType = selectedProcess === "ALL" ? undefined : selectedProcess;
      const res = await api.getTokenAnalytics(windowDays, pType);
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load token bifurcation metrics");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [windowDays, selectedProcess]);

  const formatNumber = (num?: number) => {
    if (num === undefined || num === null) return "0";
    return num.toLocaleString();
  };

  const getProcessBadge = (pType: string) => {
    switch (pType?.toUpperCase()) {
      case "INCIDENT_TRIAGE":
        return "bg-cyan-950 text-cyan-300 border-cyan-800";
      case "BATCH_TRIAGE":
        return "bg-blue-950 text-blue-300 border-blue-800";
      case "SIMULATION_REPLAY":
        return "bg-purple-950 text-purple-300 border-purple-800";
      case "POLICY_TESTING":
        return "bg-emerald-950 text-emerald-300 border-emerald-800";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="space-y-3.5">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2.5">
        <div>
          <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-1.5">
            <Cpu className="h-4 w-4 text-purple-400" />
            Token Consumption &amp; Bifurcation Analysis
          </h2>
          <p className="text-[10px] text-slate-400 mt-0.5">
            Full ledger of input context vs output reasoning tokens across all agentic processes · Persistently archived on Verdictum Core
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Storage node badge */}
          <span className="flex items-center gap-1 text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-emerald-400">
            <Database className="h-3 w-3 text-emerald-400" />
            Verdictum Core Ledger
          </span>

          {/* Time window selector */}
          <div className="flex items-center rounded-md border border-slate-800 bg-slate-900 p-0.5 text-[10px] font-mono">
            {[7, 30, 90].map((days) => (
              <button
                key={days}
                onClick={() => setWindowDays(days)}
                className={`px-2 py-0.5 rounded transition-all ${
                  windowDays === days
                    ? "bg-purple-900/60 text-purple-200 font-bold border border-purple-700/60"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {days}d
              </button>
            ))}
          </div>

          <button
            onClick={loadData}
            disabled={isLoading}
            className="flex items-center gap-1 text-[10px] rounded-md bg-slate-900 border border-slate-800 px-2 py-1 text-slate-300 hover:text-white transition-all disabled:opacity-50"
            title="Refresh Token Ledger"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-2.5 text-xs text-rose-300 font-mono">
          {error}
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        {/* Card 1: Total Tokens */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-[10px] font-mono uppercase tracking-wider">
            <span>Total Tokens</span>
            <Sparkles className="h-3 w-3 text-purple-400" />
          </div>
          <div className="text-base sm:text-lg font-mono font-bold text-slate-100">
            {formatNumber(data?.totals.total_tokens)}
          </div>
          <div className="text-[10px] font-mono text-slate-500">
            Across {formatNumber(data?.totals.total_calls)} inferences
          </div>
        </div>

        {/* Card 2: Prompt / Input Tokens */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-[10px] font-mono uppercase tracking-wider">
            <span>Prompt (Input) Tokens</span>
            <Layers className="h-3 w-3 text-cyan-400" />
          </div>
          <div className="text-base sm:text-lg font-mono font-bold text-cyan-300">
            {formatNumber(data?.totals.prompt_tokens)}
          </div>
          <div className="text-[10px] font-mono text-cyan-400/80">
            {data?.totals.prompt_percentage || 0}% of total volume
          </div>
        </div>

        {/* Card 3: Completion / Output Tokens */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-[10px] font-mono uppercase tracking-wider">
            <span>Output (Reasoning)</span>
            <Zap className="h-3 w-3 text-emerald-400" />
          </div>
          <div className="text-base sm:text-lg font-mono font-bold text-emerald-300">
            {formatNumber(data?.totals.completion_tokens)}
          </div>
          <div className="text-[10px] font-mono text-emerald-400/80">
            {data?.totals.completion_percentage || 0}% of total volume
          </div>
        </div>

        {/* Card 4: Avg Inference Latency */}
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-2.5 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-[10px] font-mono uppercase tracking-wider">
            <span>Avg Latency</span>
            <Clock className="h-3 w-3 text-amber-400" />
          </div>
          <div className="text-base sm:text-lg font-mono font-bold text-amber-300">
            {data?.totals.avg_latency_ms || 0} ms
          </div>
          <div className="text-[10px] font-mono text-slate-500">
            Verdictum Cortex (vLLM Engine)
          </div>
        </div>
      </div>

      {/* Process Bifurcation Visual Breakdown */}
      <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 border-b border-slate-800 pb-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
            <BarChart3 className="h-3.5 w-3.5 text-cyan-400" />
            Bifurcation by Process Type
          </h3>
          <span className="text-[10px] font-mono text-slate-500">
            Prompt (Input Context) vs Completion (Model Reasoning)
          </span>
        </div>

        {(!data?.by_process || data.by_process.length === 0) ? (
          <div className="py-6 text-center text-xs font-mono text-slate-500">
            No token transactions recorded in this time window.
          </div>
        ) : (
          <div className="space-y-2.5">
            {data.by_process.map((proc: TokenProcessBifurcation) => {
              const promptPct = proc.total_tokens > 0 ? (proc.prompt_tokens / proc.total_tokens) * 100 : 0;
              const compPct = proc.total_tokens > 0 ? (proc.completion_tokens / proc.total_tokens) * 100 : 0;

              return (
                <div key={proc.process_type} className="rounded-md bg-slate-900/70 border border-slate-800/80 p-2.5 space-y-1.5 font-mono text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold border ${getProcessBadge(proc.process_type)}`}>
                        {proc.process_type}
                      </span>
                      <span className="text-slate-400 text-[11px]">
                        {proc.calls} {proc.calls === 1 ? "call" : "calls"} · {proc.avg_latency_ms} ms avg
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-[11px]">
                      <span className="text-cyan-300">
                        In: <strong>{formatNumber(proc.prompt_tokens)}</strong> ({promptPct.toFixed(0)}%)
                      </span>
                      <span className="text-emerald-300">
                        Out: <strong>{formatNumber(proc.completion_tokens)}</strong> ({compPct.toFixed(0)}%)
                      </span>
                      <span className="text-slate-200 font-bold">
                        Total: {formatNumber(proc.total_tokens)} ({proc.percentage_of_total}%)
                      </span>
                    </div>
                  </div>

                  {/* Dual Stacked Progress Bar */}
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden flex">
                    <div
                      style={{ width: `${promptPct}%` }}
                      className="bg-cyan-500 h-full"
                      title={`Prompt Tokens: ${formatNumber(proc.prompt_tokens)} (${promptPct.toFixed(1)}%)`}
                    />
                    <div
                      style={{ width: `${compPct}%` }}
                      className="bg-emerald-500 h-full"
                      title={`Completion Tokens: ${formatNumber(proc.completion_tokens)} (${compPct.toFixed(1)}%)`}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Model Bifurcation Table */}
      {data?.by_model && data.by_model.length > 0 && (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Bot className="h-3.5 w-3.5 text-purple-400" />
              Bifurcation by Model Identifier
            </h3>
            <span className="text-[10px] font-mono text-slate-500">
              Active Verdictum Cortex Providers
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] text-slate-400">
                  <th className="pb-1.5 px-2">Model</th>
                  <th className="pb-1.5 px-2">Inferences</th>
                  <th className="pb-1.5 px-2 text-cyan-300">Prompt Tokens</th>
                  <th className="pb-1.5 px-2 text-emerald-300">Completion Tokens</th>
                  <th className="pb-1.5 px-2 text-slate-200">Total Tokens</th>
                  <th className="pb-1.5 px-2 text-right">Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {data.by_model.map((m: TokenModelBifurcation) => (
                  <tr key={m.model_identifier} className="hover:bg-slate-900/40">
                    <td className="py-1.5 px-2 font-bold text-slate-200">{m.model_identifier}</td>
                    <td className="py-1.5 px-2 text-slate-400">{m.calls}</td>
                    <td className="py-1.5 px-2 text-cyan-300">{formatNumber(m.prompt_tokens)}</td>
                    <td className="py-1.5 px-2 text-emerald-300">{formatNumber(m.completion_tokens)}</td>
                    <td className="py-1.5 px-2 font-bold text-purple-300">{formatNumber(m.total_tokens)}</td>
                    <td className="py-1.5 px-2 text-right font-bold text-slate-300">{m.percentage_of_total}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent Ledger Table */}
      {data?.recent_ledger && data.recent_ledger.length > 0 && (
        <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2">
          <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-cyan-400" />
              Recent Token Ledger Transactions (Verdictum Core)
            </h3>
            <span className="text-[10px] font-mono text-slate-500">
              Showing last {data.recent_ledger.length} operations
            </span>
          </div>

          <div className="overflow-x-auto max-h-72 overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] text-slate-400 sticky top-0 bg-slate-950">
                  <th className="pb-1.5 px-2">Process</th>
                  <th className="pb-1.5 px-2">Entity ID</th>
                  <th className="pb-1.5 px-2">Model</th>
                  <th className="pb-1.5 px-2 text-cyan-300">Prompt</th>
                  <th className="pb-1.5 px-2 text-emerald-300">Output</th>
                  <th className="pb-1.5 px-2 text-purple-300 font-bold">Total</th>
                  <th className="pb-1.5 px-2">Latency</th>
                  <th className="pb-1.5 px-2 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-[11px]">
                {data.recent_ledger.map((item: TokenLedgerItem) => (
                  <tr key={item.id} className="hover:bg-slate-900/40">
                    <td className="py-1.5 px-2">
                      <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${getProcessBadge(item.process_type)}`}>
                        {item.process_type}
                      </span>
                    </td>
                    <td className="py-1.5 px-2 text-slate-300">
                      {item.incident_id ? (
                        <Link
                          href={`/ai-triage-workbench/${item.incident_id}`}
                          className="text-cyan-400 hover:underline"
                        >
                          {item.incident_id}
                        </Link>
                      ) : (
                        item.process_id || "N/A"
                      )}
                    </td>
                    <td className="py-1.5 px-2 text-slate-400 truncate max-w-[120px]">{item.model_identifier}</td>
                    <td className="py-1.5 px-2 text-cyan-300">{formatNumber(item.prompt_tokens)}</td>
                    <td className="py-1.5 px-2 text-emerald-300">{formatNumber(item.completion_tokens)}</td>
                    <td className="py-1.5 px-2 font-bold text-purple-300">{formatNumber(item.total_tokens)}</td>
                    <td className="py-1.5 px-2 text-slate-400">{item.latency_ms} ms</td>
                    <td className="py-1.5 px-2 text-right text-slate-500 text-[10px]">
                      {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

