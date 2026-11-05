"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  FileCode2,
  ArrowLeft,
  Copy,
  Check,
  AlertTriangle,
  Layers,
  Shield,
  Clock,
  ExternalLink,
} from "lucide-react";
import { api, RuleItem } from "@/lib/api";

export default function RuleDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const ruleId = resolvedParams.id;

  const [rule, setRule] = useState<RuleItem | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadRule() {
      setIsLoading(true);
      try {
        const data = await api.getRuleDetail(ruleId);
        setRule(data);
      } catch (err: any) {
        setError(err.message || "Failed to load rule");
      } finally {
        setIsLoading(false);
      }
    }
    loadRule();
  }, [ruleId]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center text-slate-400 text-xs">
        Loading SIEM rule details...
      </div>
    );
  }

  if (error || !rule) {
    return (
      <div className="space-y-4">
        <Link href="/rules" className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:underline">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Rules
        </Link>
        <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-6 text-rose-300 text-xs">
          {error || "SIEM Rule not found"}
        </div>
      </div>
    );
  }

  const triggeredAttrs = rule.parsed_metadata?.triggered_attributes || [];

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/rules"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-slate-400">SIEM Rule:</span>
              <span className="font-mono font-bold text-cyan-400 text-xs">{rule.event_type}</span>
              <span className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-bold text-slate-200">
                {rule.severity}
              </span>
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-mono border ${
                  rule.status === "ACTIVE"
                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                    : "bg-slate-900 text-slate-400 border-slate-800"
                }`}
              >
                {rule.status}
              </span>
            </div>
            <h1 className="text-base font-bold text-slate-100 mt-1">{rule.name}</h1>
          </div>
        </div>

        <div>
          <Link
            href={`/incidents?rule_id=${encodeURIComponent(rule.event_type)}`}
            className="flex items-center gap-2 rounded-lg bg-cyan-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-cyan-500 shadow-sm"
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            View {rule.incident_count} Linked Incidents
          </Link>
        </div>
      </div>

      {/* Main Metadata Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Rule Description & Remediation */}
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4 text-xs">
            <h2 className="font-bold uppercase tracking-wider text-slate-300">
              Rule Overview & Description
            </h2>
            <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 leading-relaxed text-slate-200">
              {rule.description || "No description provided."}
            </div>

            {rule.remediation && (
              <div className="space-y-1.5">
                <span className="text-[10px] uppercase font-mono text-cyan-400 block">
                  Remediation & Triage Guidance:
                </span>
                <div className="p-3.5 rounded-lg bg-cyan-950/20 border border-cyan-800/60 leading-relaxed text-cyan-200 font-mono text-[11px]">
                  {rule.remediation}
                </div>
              </div>
            )}
          </div>

          {/* Detection Logic & Pattern */}
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <h2 className="font-bold uppercase tracking-wider text-slate-300">
                Detection Logic & Correlation Pattern
              </h2>
              <button
                onClick={() => copyToClipboard(rule.pattern_logic)}
                className="flex items-center gap-1 rounded bg-slate-900 border border-slate-800 px-2 py-1 text-[11px] text-slate-300 hover:text-white"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                Copy Pattern
              </button>
            </div>
            <pre className="p-4 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
              {rule.pattern_logic || "No pattern condition defined."}
            </pre>
          </div>

          {/* Original SIEM Rule File Raw Text */}
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-3 text-xs">
            <div className="flex items-center justify-between">
              <h2 className="font-bold uppercase tracking-wider text-slate-300">
                Original SIEM Rule Specification File
              </h2>
              <button
                onClick={() => copyToClipboard(rule.raw_rule_text)}
                className="flex items-center gap-1 rounded bg-slate-900 border border-slate-800 px-2 py-1 text-[11px] text-slate-300 hover:text-white"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                Copy Raw Spec
              </button>
            </div>
            <pre className="p-4 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[11px] text-cyan-300 overflow-x-auto max-h-96 whitespace-pre-wrap leading-relaxed">
              {rule.raw_rule_text}
            </pre>
          </div>
        </div>

        {/* Right Info Sidebar */}
        <div className="space-y-6">
          <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4 text-xs font-mono">
            <h2 className="font-bold uppercase tracking-wider text-slate-300">Rule Parameters</h2>
            <div className="space-y-3 text-[11px]">
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Data Source:</span>
                <span className="text-slate-200 truncate max-w-[150px]">{rule.data_source || "N/A"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Technology:</span>
                <span className="text-slate-200">{rule.detection_tech || "Correlation"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Evaluation:</span>
                <span className="text-slate-200">{rule.evaluation_mode || "Streaming"}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-800">
                <span className="text-slate-400">Associated Cases:</span>
                <span className="text-cyan-400 font-bold">{rule.incident_count}</span>
              </div>
            </div>
          </div>

          {/* Triggered Attributes List */}
          {triggeredAttrs.length > 0 && (
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-3 text-xs">
              <h2 className="font-bold uppercase tracking-wider text-slate-300">
                Triggered Attributes ({triggeredAttrs.length})
              </h2>
              <div className="flex flex-wrap gap-1.5 font-mono text-[10px]">
                {triggeredAttrs.map((attr: string) => (
                  <span
                    key={attr}
                    className="rounded bg-slate-900 border border-slate-800 px-2 py-1 text-slate-300"
                  >
                    {attr}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

