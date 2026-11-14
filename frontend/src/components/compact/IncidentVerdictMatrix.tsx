"use client";

import React from "react";
import {
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  UserCheck,
  Activity,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Clock,
  Cpu,
  ArrowRight,
  Server,
  Network,
} from "lucide-react";

export interface IncidentVerdictMatrixProps {
  proposedVerdict?: string | null;
  validatedVerdict?: string | null;
  validationStatus?: string | null;
  analystVerdict?: string | null;
  operationalStatus?: string | null;
  isBlindMode?: boolean;
  confidence?: number | null;
  groundingRatio?: number | null;
  trustScore?: number | null;
}

export function IncidentVerdictMatrix({
  proposedVerdict,
  validatedVerdict,
  validationStatus,
  analystVerdict,
  operationalStatus,
  isBlindMode = false,
  confidence,
  groundingRatio,
  trustScore,
}: IncidentVerdictMatrixProps) {
  const getBadgeStyle = (val: string | null | undefined, isOverridden = false) => {
    if (!val || val === "PENDING" || val === "UNVERIFIED") {
      return "bg-slate-900 text-slate-400 border-slate-700";
    }
    const upper = val.toUpperCase();
    if (upper.includes("TRUE_POSITIVE") || upper === "TP") {
      return "bg-rose-950/80 text-rose-300 border-rose-800";
    }
    if (upper.includes("FALSE_POSITIVE") || upper === "FP") {
      return "bg-emerald-950/80 text-emerald-300 border-emerald-800";
    }
    if (upper.includes("REQUIRES_ATTENTION") || upper.includes("INSUFFICIENT")) {
      return "bg-amber-950/80 text-amber-300 border-amber-800";
    }
    if (upper === "VALIDATED" || upper === "ACCEPTED" || upper === "CLOSED") {
      return "bg-emerald-950/80 text-emerald-300 border-emerald-800";
    }
    return "bg-slate-900 text-slate-300 border-slate-700";
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
      {/* Dimension 1: AI Proposed Verdict */}
      <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 space-y-1.5 text-xs">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5 font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            1. AI Proposed Verdict
          </span>
          {confidence != null && (
            <span className="font-mono text-[10px] text-slate-300">{Math.round(confidence)}% Conf</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded font-mono font-bold text-xs border uppercase ${getBadgeStyle(
              proposedVerdict
            )}`}
          >
            {proposedVerdict ? proposedVerdict.replace(/_/g, " ") : "Pending Ingestion"}
          </span>
        </div>
        <p className="text-[10px] text-slate-500 leading-tight">
          Uncalibrated direct proposal from Local LLM.
        </p>
      </div>

      {/* Dimension 2: Independently Validated Verdict */}
      <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 space-y-1.5 text-xs">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5 font-semibold">
            <ShieldCheck className="w-3.5 h-3.5 text-sky-400" />
            2. Platform Validation
          </span>
          {trustScore != null && (
            <span className="font-mono text-[10px] text-purple-300">Trust: {trustScore}/10</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded font-mono font-bold text-xs border uppercase ${getBadgeStyle(
              validatedVerdict || validationStatus
            )}`}
          >
            {validatedVerdict ? validatedVerdict.replace(/_/g, " ") : validationStatus || "Unverified"}
          </span>
        </div>
        <p className="text-[10px] text-slate-500 leading-tight">
          {groundingRatio != null
            ? `${Math.round(groundingRatio * 100)}% claim grounding verified`
            : "Deterministic schema & telemetry safety validator"}
        </p>
      </div>

      {/* Dimension 3: Analyst Verified Verdict */}
      <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 space-y-1.5 text-xs">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5 font-semibold">
            <UserCheck className="w-3.5 h-3.5 text-emerald-400" />
            3. Analyst Verification
          </span>
          <span className="font-mono text-[10px] text-slate-500">
            {isBlindMode ? "Blind Active" : "Human L1/L2"}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isBlindMode ? (
            <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-amber-950/60 border border-amber-800 text-amber-300 italic">
              Hidden in Blind Mode
            </span>
          ) : (
            <span
              className={`px-2 py-0.5 rounded font-mono font-bold text-xs border uppercase ${getBadgeStyle(
                analystVerdict
              )}`}
            >
              {analystVerdict ? analystVerdict.replace(/_/g, " ") : "Pending Review"}
            </span>
          )}
        </div>
        <p className="text-[10px] text-slate-500 leading-tight">
          Independent ground truth resolution benchmark.
        </p>
      </div>

      {/* Dimension 4: Operational Incident Status */}
      <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/50 space-y-1.5 text-xs">
        <div className="flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5 font-semibold">
            <Activity className="w-3.5 h-3.5 text-amber-400" />
            4. Operational SIEM Status
          </span>
          <span className="font-mono text-[10px] text-slate-500">FortiSIEM</span>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`px-2 py-0.5 rounded font-mono font-bold text-xs border uppercase ${getBadgeStyle(
              operationalStatus
            )}`}
          >
            {operationalStatus || "NEW"}
          </span>
        </div>
        <p className="text-[10px] text-slate-500 leading-tight">
          Authoritative ticket state in SIEM console.
        </p>
      </div>
    </div>
  );
}
