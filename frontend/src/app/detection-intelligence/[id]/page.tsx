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

export default function DetectionIntelligenceDetailPage({
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
        setError(err.message || "Failed to load detection rule");
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
        Loading detection intelligence details...
      </div>
    );
  }

  if (error || !rule) {
    return (
      <div className="space-y-4">
        <Link href="/detection-intelligence" className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:underline">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Detection Intelligence
        </Link>
        <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-6 text-rose-300 text-xs">
          {error || "Detection Rule not found"}
        </div>
      </div>
    );
  }

  const triggeredAttrs = rule.parsed_metadata?.triggered_attributes || [];

  return (
    <div className="space-y-3.5">
      {/* Top Header */}
      <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2.5">
          <Link
            href="/detection-intelligence"
            className="flex h-7 w-7 items-center justify-center rounded-md border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white"
            title="Back to Detection Intelligence"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
          </Link>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-mono text-[11px] text-slate-400">Detection Rule:</span>
              <span className="font-mono font-bold text-cyan-400 text-xs">{rule.event_type}</span>
              <span className="rounded bg-slate-800 border border-slate-700 px-1.5 py-0.2 text-[9px] font-bold text-slate-200">
                {rule.severity}
              </span>
              <span
                className={`rounded px-1.5 py-0.2 text-[9px] font-mono border ${
                  rule.status === "ACTIVE"
                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                    : "bg-slate-900 text-slate-400 border-slate-800"
                }`}
              >
                {rule.status}
              </span>
            </div>
            <h1 className="text-sm sm:text-base font-bold text-slate-100 mt-0.5">{rule.name}</h1>
          </div>
        </div>

        <div>
          <Link
            href={`/ai-triage-workbench?rule_id=${encodeURIComponent(rule.event_type)}`}
            className="flex items-center gap-1.5 rounded-md bg-cyan-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-cyan-500 shadow-sm"
          >
            <AlertTriangle className="h-3.5 w-3.5" />
            View {rule.incident_count} Linked Incidents
          </Link>
        </div>
      </div>

      {/* Main Metadata Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="lg:col-span-2 space-y-3">
          {/* Rule Description & Remediation */}
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2.5 text-xs">
            <h2 className="font-bold uppercase tracking-wider text-slate-300 text-xs">
              Rule Overview &amp; Context Description
            </h2>
            <div className="p-2.5 rounded-md bg-slate-900 border border-slate-800 leading-relaxed text-slate-200 text-xs">
              {rule.description || "No description provided."}
            </div>

            {rule.remediation && (
              <div className="space-y-1">
                <span className="text-[10px] uppercase font-mono text-cyan-400 block">
                  Remediation &amp; Triage Guidance:
                </span>
                <div className="p-2.5 rounded-md bg-cyan-950/20 border border-cyan-800/60 leading-relaxed text-cyan-200 font-mono text-[11px]">
                  {rule.remediation}
                </div>
              </div>
            )}
          </div>

          {/* Detection Logic & Pattern */}
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <h2 className="font-bold uppercase tracking-wider text-slate-300 text-xs">
                Detection Logic &amp; Correlation Pattern
              </h2>
              <button
                onClick={() => copyToClipboard(rule.pattern_logic)}
                className="flex items-center gap-1 rounded bg-slate-900 border border-slate-800 px-2 py-0.5 text-[11px] text-slate-300 hover:text-white"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                Copy Pattern
              </button>
            </div>
            <pre className="p-2.5 rounded-md bg-slate-900 border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-56">
              {rule.pattern_logic || "No pattern condition defined."}
            </pre>
          </div>

          {/* Raw Rule Definition Text */}
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 sm:p-3.5 space-y-2 text-xs">
            <div className="flex items-center justify-between">
              <h2 className="font-bold uppercase tracking-wider text-slate-300 text-xs">
                Raw Rule Definition Specification
              </h2>
              <button
                onClick={() => copyToClipboard(rule.raw_rule_text)}
                className="flex items-center gap-1 rounded bg-slate-900 border border-slate-800 px-2 py-0.5 text-[11px] text-slate-300 hover:text-white"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                Copy Raw Spec
              </button>
            </div>
            <pre className="p-2.5 rounded-md bg-slate-900 border border-slate-800 font-mono text-[10px] text-slate-400 overflow-x-auto whitespace-pre-wrap leading-relaxed max-h-64">
              {rule.raw_rule_text || "No raw text available."}
            </pre>
          </div>
        </div>

        {/* Right Info Sidebar */}
        <div className="space-y-3 font-mono text-xs">
          <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-2">
            <h2 className="font-bold uppercase tracking-wider text-slate-300 border-b border-slate-800 pb-1 font-sans">
              Rule Attributes
            </h2>
            <div className="space-y-1.5 text-[11px]">
              <div>
                <span className="text-slate-500 block">Rule ID</span>
                <span className="text-slate-200">{rule.rule_id}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Data Source</span>
                <span className="text-slate-200">{rule.data_source || "SIEM Telemetry"}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Detection Technology</span>
                <span className="text-slate-200">{rule.detection_tech || "Standard Correlation"}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Evaluation Mode</span>
                <span className="text-slate-200">{rule.evaluation_mode || "Continuous"}</span>
              </div>
            </div>
          </div>

          {triggeredAttrs.length > 0 && (
            <div className="rounded-lg border border-slate-800 bg-slate-950 p-3 space-y-2">
              <h2 className="font-bold uppercase tracking-wider text-slate-300 border-b border-slate-800 pb-1 font-sans">
                Triggered Attributes ({triggeredAttrs.length})
              </h2>
              <div className="flex flex-wrap gap-1">
                {triggeredAttrs.map((attr: string) => (
                  <span
                    key={attr}
                    className="rounded bg-slate-900 px-1.5 py-0.2 text-[10px] text-cyan-300 border border-slate-800"
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

