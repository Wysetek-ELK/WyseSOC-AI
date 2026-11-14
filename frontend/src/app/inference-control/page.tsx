"use client";

import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ServerInfrastructureMonitor } from "@/components/system/ServerInfrastructureMonitor";
import { TokenBifurcationWidget } from "@/components/telemetry/TokenBifurcationWidget";
import { Server } from "lucide-react";

export default function InferenceControlPage() {
  const [s2Online, setS2Online] = useState<boolean | null>(null);
  const [s2Provenance, setS2Provenance] = useState<string | null>(null);
  const [testEnv, setTestEnv] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api.getServersLive()
      .then((res) => {
        if (mounted) {
          setS2Online(res?.server_2?.status === "ONLINE");
          setS2Provenance((res?.server_2?.details as any)?.endpoint_provenance || null);
          setTestEnv((res?.server_2?.details as any)?.test_environment || null);
        }
      })
      .catch(() => {
        if (mounted) {
          setS2Online(false);
          setS2Provenance("OFFLINE");
        }
      });

    const onStatus = (e: Event) => {
      const detail = (e as CustomEvent).detail;
      if (mounted && detail && typeof detail.is_healthy === "boolean") {
        setS2Online(detail.is_healthy);
        if (detail.endpoint_provenance) setS2Provenance(detail.endpoint_provenance);
        if (detail.test_environment !== undefined) setTestEnv(detail.test_environment);
      }
    };
    window.addEventListener("llm-status-change", onStatus);
    return () => {
      mounted = false;
      window.removeEventListener("llm-status-change", onStatus);
    };
  }, []);

  return (
    <div className="space-y-3.5">
      {/* Page Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-2.5">
        <div>
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <Server className="h-4 w-4 text-cyan-400" />
            Inference Control
          </h1>
          <p className="text-[11px] text-slate-400 mt-0.5">
            LLM infrastructure monitoring, resource utilization, CPU, memory, GPU KV cache &amp; historical health analytics
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          {testEnv && (
            <span className="px-2 py-1 rounded bg-cyan-950/70 border border-cyan-800 text-cyan-300">
              TEST ENV: {testEnv}
            </span>
          )}
          {s2Online === null ? (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-400">
              <span className="h-2 w-2 rounded-full bg-slate-500"></span>
              Cluster Status: <strong className="text-slate-300">CHECKING</strong>
            </span>
          ) : s2Provenance === "HTTP_MOCK" ? (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-cyan-950/50 border border-cyan-700/70 text-cyan-200">
              <span className="h-2 w-2 rounded-full bg-cyan-400"></span>
              Cluster Status: <strong className="text-cyan-300">HTTP_MOCK (TEST ENDPOINT)</strong>
            </span>
          ) : s2Online ? (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-emerald-800/60 text-slate-300">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
              Cluster Status: <strong className="text-emerald-400">ONLINE (S1 + S2)</strong>
            </span>
          ) : (
            <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950/40 border border-amber-800/60 text-amber-200">
              <span className="h-2 w-2 rounded-full bg-amber-400"></span>
              Cluster Status: <strong className="text-amber-300">DEGRADED (CORTEX OFFLINE)</strong>
            </span>
          )}
        </div>
      </div>

      {/* Main Inference Health Monitor */}
      <ServerInfrastructureMonitor />

      {/* Token Consumption & Bifurcation Ledger on Verdictum Core */}
      <TokenBifurcationWidget />
    </div>
  );
}

