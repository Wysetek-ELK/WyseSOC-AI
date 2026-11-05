"use client";

import React from "react";
import { Settings, Shield, Database, Cpu, Lock, Sliders } from "lucide-react";
import { useApp } from "@/context/AppContext";

export default function SettingsPage() {
  const { blindReviewMode, setBlindReviewMode, theme, toggleTheme } = useApp();

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
          <Settings className="h-5 w-5 text-cyan-400" />
          Application & SOC Settings
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Configuration parameters for Server 1 Application Foundation and security governance
        </p>
      </div>

      <div className="space-y-5">
        {/* Investigation Controls */}
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 space-y-4">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2">
            <Sliders className="h-4 w-4 text-cyan-400" />
            Analyst Investigation Safeguards
          </h2>

          <div className="flex items-center justify-between border-t border-slate-800 pt-4">
            <div>
              <span className="text-xs font-semibold text-slate-200 block">
                Default Blind Review Mode
              </span>
              <span className="text-xs text-slate-400">
                Mask historical resolution and machine-generated verdicts to prevent analyst confirmation bias.
              </span>
            </div>
            <button
              onClick={() => setBlindReviewMode(!blindReviewMode)}
              className={`rounded-lg px-3.5 py-1.5 text-xs font-bold transition-all border ${
                blindReviewMode
                  ? "bg-amber-950 text-amber-300 border-amber-800 shadow-sm"
                  : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"
              }`}
            >
              {blindReviewMode ? "ENABLED" : "DISABLED"}
            </button>
          </div>

          <div className="flex items-center justify-between border-t border-slate-800 pt-4">
            <div>
              <span className="text-xs font-semibold text-slate-200 block">Theme Preference</span>
              <span className="text-xs text-slate-400">
                Toggle between Enterprise SOC Dark Mode and Light Mode.
              </span>
            </div>
            <button
              onClick={toggleTheme}
              className="rounded-lg border border-slate-800 bg-slate-900 px-3.5 py-1.5 text-xs font-bold text-slate-200 hover:bg-slate-800"
            >
              {theme.toUpperCase()} MODE
            </button>
          </div>
        </div>

        {/* Server & Architecture Info */}
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 space-y-4 font-mono text-xs">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center gap-2 font-sans">
            <Database className="h-4 w-4 text-cyan-400" />
            Infrastructure Topology & Deployment Profile
          </h2>

          <div className="space-y-2.5 text-[11px] pt-1">
            <div className="flex justify-between py-1.5 border-b border-slate-800/80">
              <span className="text-slate-400">Active Node:</span>
              <span className="text-slate-200 font-bold">Server 1 — Application Server</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800/80">
              <span className="text-slate-400">Target Operating System:</span>
              <span className="text-slate-200">Ubuntu Server LTS (systemd + Nginx)</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800/80">
              <span className="text-slate-400">Database Engine:</span>
              <span className="text-slate-200">PostgreSQL (Production) / SQLite (Local Dev)</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-slate-800/80">
              <span className="text-slate-400">Future LLM Host (Server 2):</span>
              <span className="text-amber-400">Gated / Disconnected (Phase 1 Governance)</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-slate-400">SIEM Write-Back & Auto Closure:</span>
              <span className="text-slate-400">Disabled (Dry-run read-only phase)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
