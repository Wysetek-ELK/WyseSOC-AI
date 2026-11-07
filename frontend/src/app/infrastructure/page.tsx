"use client";

import React from "react";
import { ServerInfrastructureMonitor } from "@/components/system/ServerInfrastructureMonitor";
import { Server, Activity, ShieldCheck, Cpu } from "lucide-react";

export default function InfrastructurePage() {
  return (
    <div className="space-y-3.5">
      {/* Page Header */}
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-2.5">
        <div>
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <Server className="h-4 w-4 text-cyan-400" />
            Dual-Server Infrastructure & Telemetry
          </h1>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Resource utilization, CPU, memory, GPU KV cache & historical analytics across Server 1 and Server 2
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono">
          <span className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Cluster Status: <strong className="text-emerald-400">HEALTHY</strong>
          </span>
        </div>
      </div>

      {/* Main Infrastructure Monitor */}
      <ServerInfrastructureMonitor />
    </div>
  );
}

