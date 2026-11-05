"use client";

import React, { useEffect, useState, use } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  ArrowLeft,
  Eye,
  EyeOff,
  Copy,
  Check,
  FileCode,
  Layers,
  Clock,
  ShieldCheck,
  Server,
  Network,
  Tag,
  Cpu,
  FileCheck2,
} from "lucide-react";
import { api, IncidentDetail } from "@/lib/api";
import { useApp } from "@/context/AppContext";

export default function IncidentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const incidentId = resolvedParams.id;
  const { blindReviewMode, setBlindReviewMode } = useApp();

  const [incident, setIncident] = useState<IncidentDetail | null>(null);
  const [modelPayload, setModelPayload] = useState<any | null>(null);
  const [activeTab, setActiveTab] = useState<
    "overview" | "events" | "rule" | "ground_truth" | "raw_json" | "model_payload" | "timeline"
  >("overview");
  const [isLoading, setIsLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getIncidentDetail(incidentId, blindReviewMode);
        setIncident(data);

        // Also fetch model payload to demonstrate allowlist compliance
        try {
          const mp = await api.getIncidentModelPayload(incidentId);
          setModelPayload(mp);
        } catch {
          // ignore if model payload fails
        }
      } catch (err: any) {
        setError(err.message || "Failed to load incident detail");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [incidentId, blindReviewMode]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatEpoch = (epoch?: number) => {
    if (!epoch) return "N/A";
    return new Date(epoch).toLocaleString();
  };

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center text-slate-400 text-xs">
        Loading incident {incidentId}...
      </div>
    );
  }

  if (error || !incident) {
    return (
      <div className="space-y-4">
        <Link href="/incidents" className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:underline">
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Incidents
        </Link>
        <div className="rounded-xl border border-rose-800 bg-rose-950/40 p-6 text-rose-300 text-xs">
          {error || "Incident not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Link
            href="/incidents"
            className="flex h-8 w-8 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-slate-300 hover:bg-slate-800 hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-slate-400">Incident</span>
              <span className="font-mono font-bold text-slate-100 text-sm">{incident.incident_id}</span>
              <span className="rounded bg-slate-800 border border-slate-700 px-2 py-0.5 text-[10px] font-bold text-slate-200">
                {incident.severity}
              </span>
              <span
                className={`rounded px-2 py-0.5 text-[10px] font-mono border ${
                  incident.status_code === 2
                    ? "bg-slate-900 text-slate-400 border-slate-800"
                    : "bg-cyan-950 text-cyan-300 border-cyan-800"
                }`}
              >
                {incident.status_name}
              </span>
            </div>
            <h1 className="text-base font-bold text-slate-100 mt-1">{incident.title}</h1>
          </div>
        </div>

        {/* Blind Review Mode Toggle */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => setBlindReviewMode(!blindReviewMode)}
            className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all ${
              blindReviewMode
                ? "border-amber-500/80 bg-amber-950/80 text-amber-300 shadow-md shadow-amber-950/50"
                : "border-slate-800 bg-slate-900 text-slate-400 hover:text-slate-200"
            }`}
          >
            {blindReviewMode ? (
              <>
                <EyeOff className="h-3.5 w-3.5 text-amber-400" />
                <span>Blind Review: ON</span>
              </>
            ) : (
              <>
                <Eye className="h-3.5 w-3.5 text-slate-400" />
                <span>Blind Review: OFF</span>
              </>
            )}
          </button>
        </div>
      </div>

      {blindReviewMode && (
        <div className="rounded-xl border border-amber-800/80 bg-amber-950/40 p-3.5 text-xs text-amber-300 flex items-center gap-3">
          <EyeOff className="h-4 w-4 shrink-0 text-amber-400" />
          <div>
            <strong className="font-semibold text-amber-200">Blind Review Active:</strong> Historical ground truth tab and resolution verdicts are masked from view for this incident.
          </div>
        </div>
      )}

      {/* Tabs Header */}
      <div className="flex border-b border-slate-800 space-x-1 overflow-x-auto text-xs font-medium">
        <button
          onClick={() => setActiveTab("overview")}
          className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "overview"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Incident Overview
        </button>

        <button
          onClick={() => setActiveTab("events")}
          className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "events"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Raw Events
          <span className="rounded bg-slate-800 px-1.5 py-0.2 text-[10px] font-mono text-slate-300">
            {incident.events.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("rule")}
          className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "rule"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          SIEM Rule Information
        </button>

        <button
          onClick={() => setActiveTab("ground_truth")}
          className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "ground_truth"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Historical Ground Truth
          {blindReviewMode && <EyeOff className="h-3 w-3 text-amber-400" />}
        </button>

        <button
          onClick={() => setActiveTab("raw_json")}
          className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "raw_json"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Raw Payload JSON
        </button>

        <button
          onClick={() => setActiveTab("model_payload")}
          className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap flex items-center gap-1.5 ${
            activeTab === "model_payload"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <Cpu className="h-3.5 w-3.5 text-cyan-400" />
          Model-Facing Payload Allowlist
        </button>

        <button
          onClick={() => setActiveTab("timeline")}
          className={`px-4 py-2.5 border-b-2 transition-colors whitespace-nowrap ${
            activeTab === "timeline"
              ? "border-cyan-500 text-cyan-300 font-semibold"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          Lifecycle Timeline
        </button>
      </div>

      {/* Tab 1: Overview */}
      {activeTab === "overview" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Description & Detail */}
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Investigation Description & Details
              </h2>
              <div className="space-y-3 text-xs leading-relaxed text-slate-300">
                <div>
                  <span className="text-[11px] font-mono text-slate-500 block mb-0.5">Description:</span>
                  <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono">
                    {incident.description || "No description provided by SIEM."}
                  </div>
                </div>
                {incident.detail && (
                  <div>
                    <span className="text-[11px] font-mono text-slate-500 block mb-0.5">Detail Telemetry:</span>
                    <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-[11px] overflow-x-auto whitespace-pre-wrap">
                      {incident.detail}
                    </pre>
                  </div>
                )}
              </div>
            </div>

            {/* Network & Device Evidence */}
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
                Network & Reporting Entities
              </h2>
              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">Source IP:</span>
                  <span className="text-slate-200 font-bold">{incident.source_ip || "Internal / Host"}</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">Reporting IP:</span>
                  <span className="text-slate-200">{incident.reporting_ip || "N/A"}</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">Reporting Device:</span>
                  <span className="text-slate-200 truncate block">{incident.reporting_device || "N/A"}</span>
                </div>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                  <span className="text-slate-500 text-[10px] block">Category / Subcategory:</span>
                  <span className="text-slate-200">
                    {incident.category || "General"} {incident.subcategory ? `· ${incident.subcategory}` : ""}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Summary Column */}
          <div className="space-y-6">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4 text-xs">
              <h2 className="font-bold uppercase tracking-wider text-slate-300">Metadata Summary</h2>
              <div className="space-y-2.5 font-mono text-[11px]">
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">SIEM Event Type:</span>
                  <span className="text-slate-200 truncate max-w-[150px]">{incident.event_type}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Rule Name:</span>
                  <span className="text-slate-200 truncate max-w-[150px]">{incident.rule_name || "Unmapped"}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">First Seen:</span>
                  <span className="text-slate-200">{formatEpoch(incident.first_seen_epoch)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Last Seen:</span>
                  <span className="text-slate-200">{formatEpoch(incident.last_seen_epoch)}</span>
                </div>
                <div className="flex justify-between py-1 border-b border-slate-800">
                  <span className="text-slate-400">Created At:</span>
                  <span className="text-slate-200">{formatEpoch(incident.created_at_epoch)}</span>
                </div>
                <div className="flex justify-between py-1">
                  <span className="text-slate-400">Customer:</span>
                  <span className="text-slate-200">{incident.customer || "Enterprise Default"}</span>
                </div>
              </div>

              {incident.rule_id && (
                <div className="pt-2">
                  <Link
                    href={`/rules/${incident.rule_id}`}
                    className="block w-full text-center rounded-lg bg-slate-900 border border-slate-800 py-2 text-xs font-semibold text-cyan-400 hover:bg-slate-800"
                  >
                    View Detection Rule →
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Raw Events Explorer */}
      {activeTab === "events" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 font-mono">
              Displaying all {incident.events.length} raw security event logs and vendor attributes
            </span>
          </div>

          <div className="space-y-4">
            {incident.events.map((evt, idx) => (
              <div key={evt.id} className="rounded-xl border border-slate-800 bg-slate-950 p-4 space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-cyan-950/70 border border-cyan-800 px-2 py-0.5 text-[10px] text-cyan-300 font-bold">
                      EVENT #{idx + 1}
                    </span>
                    <span className="text-slate-400 text-[11px]">ID: {evt.event_id}</span>
                    <span className="text-slate-400 text-[11px]">· {evt.event_type}</span>
                  </div>
                  <span className="text-[10px] text-slate-500">
                    Received: {formatEpoch(evt.event_receive_time)}
                  </span>
                </div>

                {evt.raw_log && (
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase">Raw Event Log:</span>
                    <pre className="mt-1 p-2.5 rounded bg-slate-900 border border-slate-800 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap">
                      {evt.raw_log}
                    </pre>
                  </div>
                )}

                {/* Generic Vendor Attributes Grid */}
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block mb-1.5">
                    Parsed Vendor Attributes ({Object.keys(evt.attributes || {}).length}):
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-2">
                    {Object.entries(evt.attributes || {}).map(([attrKey, attrVal]) => (
                      <div key={attrKey} className="p-2 rounded bg-slate-900/60 border border-slate-800/80 overflow-hidden">
                        <span className="text-[10px] text-slate-400 block truncate" title={attrKey}>
                          {attrKey}
                        </span>
                        <span className="text-slate-200 text-xs font-medium break-all" title={String(attrVal)}>
                          {typeof attrVal === "object" ? JSON.stringify(attrVal) : String(attrVal)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 3: SIEM Rule Information */}
      {activeTab === "rule" && (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-100">{incident.rule_name || incident.event_type}</h2>
              <span className="text-xs font-mono text-cyan-400">{incident.event_type}</span>
            </div>
            {incident.rule_id && (
              <Link
                href={`/rules/${incident.rule_id}`}
                className="rounded bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500"
              >
                Open Full Rule Spec
              </Link>
            )}
          </div>

          <div className="text-xs text-slate-300">
            <span className="text-[11px] font-mono text-slate-500 block mb-1">Rule Description:</span>
            <p className="p-3 rounded-lg bg-slate-900 border border-slate-800">
              {incident.rule_description || "No standalone description available."}
            </p>
          </div>
        </div>
      )}

      {/* Tab 4: Historical Ground Truth */}
      {activeTab === "ground_truth" && (
        <div className="space-y-4">
          {blindReviewMode || !incident.ground_truth ? (
            <div className="rounded-xl border border-dashed border-amber-800/80 bg-amber-950/20 p-8 text-center text-xs">
              <EyeOff className="h-8 w-8 text-amber-400 mx-auto mb-2" />
              <h3 className="font-bold text-amber-300 text-sm">Ground Truth Masked in Blind Review Mode</h3>
              <p className="text-slate-400 mt-1 max-w-md mx-auto">
                Historical resolution and comments are hidden so you can test independent verdicts without bias.
              </p>
              <button
                onClick={() => setBlindReviewMode(false)}
                className="mt-4 rounded bg-amber-700/80 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-600"
              >
                Disable Blind Review to Reveal
              </button>
            </div>
          ) : (
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 space-y-5 text-xs font-mono">
              <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase block">Historical Verdict Label:</span>
                  <span
                    className={`mt-1 inline-block px-3 py-1 rounded border text-sm font-bold ${
                      incident.ground_truth.resolution.includes("True")
                        ? "bg-rose-950 text-rose-300 border-rose-800"
                        : "bg-emerald-950 text-emerald-300 border-emerald-800"
                    }`}
                  >
                    {incident.ground_truth.resolution || "Unlabeled"}
                  </span>
                </div>
                {incident.ground_truth.is_ml_generated && (
                  <span className="rounded bg-purple-950 text-purple-300 border border-purple-800 px-2 py-1 text-[10px] uppercase font-bold">
                    Machine Learning Resolution Note
                  </span>
                )}
              </div>

              <div>
                <span className="text-[10px] text-slate-500 uppercase block mb-1">Cleared Reason:</span>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-200">
                  {incident.ground_truth.cleared_reason || "None recorded."}
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 uppercase block mb-1">Analyst / System Comments:</span>
                <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-slate-200">
                  {incident.ground_truth.comments || "No historical comments."}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-[11px] text-slate-400 border-t border-slate-800 pt-3">
                <div>Cleared User: {incident.ground_truth.cleared_user || "System / Unspecified"}</div>
                <div>Cleared Time: {formatEpoch(incident.ground_truth.cleared_time_epoch)}</div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Raw JSON Viewer */}
      {activeTab === "raw_json" && (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-slate-400">
              Unmodified original SIEM ingestion payload
            </span>
            <button
              onClick={() => copyToClipboard(JSON.stringify(incident.raw_payload, null, 2))}
              className="flex items-center gap-1.5 rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-300 hover:text-white"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "Copied JSON" : "Copy Payload"}
            </button>
          </div>
          <pre className="rounded-lg bg-slate-900 border border-slate-800 p-4 font-mono text-[11px] text-cyan-300 overflow-x-auto max-h-[600px] overflow-y-auto">
            {JSON.stringify(incident.raw_payload, null, 2)}
          </pre>
        </div>
      )}

      {/* Tab 6: Model-Facing Payload Allowlist */}
      {activeTab === "model_payload" && (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-5 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                <ShieldCheck className="h-4 w-4" />
                Model-Facing Feature Allowlist (Zero Leakage Verification)
              </h2>
              <p className="text-[11px] text-slate-400 mt-1">
                This payload represents the strict whitelist sent to future LLM pipelines. All resolution verdicts, cleared reasons, analyst comments, and closure timestamps are strictly excluded.
              </p>
            </div>
            <button
              onClick={() => copyToClipboard(JSON.stringify(modelPayload, null, 2))}
              className="flex items-center gap-1.5 rounded border border-slate-800 bg-slate-900 px-2.5 py-1 text-xs text-slate-300 hover:text-white"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? "Copied" : "Copy Model Input"}
            </button>
          </div>

          <pre className="rounded-lg bg-slate-900 border border-slate-800 p-4 font-mono text-[11px] text-emerald-400 overflow-x-auto max-h-[600px] overflow-y-auto">
            {JSON.stringify(modelPayload, null, 2)}
          </pre>
        </div>
      )}

      {/* Tab 7: Timeline */}
      {activeTab === "timeline" && (
        <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 space-y-6">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-300">
            Incident Lifecycle Milestones
          </h2>
          <div className="relative border-l border-slate-800 pl-6 space-y-6 text-xs font-mono">
            {/* First Seen */}
            <div className="relative">
              <span className="absolute -left-[31px] flex h-4 w-4 items-center justify-center rounded-full bg-cyan-950 border border-cyan-500 text-cyan-300 text-[10px]">
                ●
              </span>
              <div className="font-semibold text-slate-200">First Telemetry Observed</div>
              <div className="text-slate-500 text-[11px]">{formatEpoch(incident.first_seen_epoch)}</div>
            </div>

            {/* Created */}
            <div className="relative">
              <span className="absolute -left-[31px] flex h-4 w-4 items-center justify-center rounded-full bg-blue-950 border border-blue-500 text-blue-300 text-[10px]">
                ●
              </span>
              <div className="font-semibold text-slate-200">SIEM Incident Alert Created</div>
              <div className="text-slate-500 text-[11px]">{formatEpoch(incident.created_at_epoch)}</div>
            </div>

            {/* Last Seen */}
            <div className="relative">
              <span className="absolute -left-[31px] flex h-4 w-4 items-center justify-center rounded-full bg-slate-800 border border-slate-600 text-slate-300 text-[10px]">
                ●
              </span>
              <div className="font-semibold text-slate-200">Last Telemetry Observed</div>
              <div className="text-slate-500 text-[11px]">{formatEpoch(incident.last_seen_epoch)}</div>
            </div>

            {/* Cleared / Resolved */}
            {incident.ground_truth?.cleared_time_epoch && !blindReviewMode && (
              <div className="relative">
                <span className="absolute -left-[31px] flex h-4 w-4 items-center justify-center rounded-full bg-emerald-950 border border-emerald-500 text-emerald-300 text-[10px]">
                  ●
                </span>
                <div className="font-semibold text-slate-200">
                  SIEM Ticket Cleared ({incident.ground_truth.resolution})
                </div>
                <div className="text-slate-500 text-[11px]">
                  {formatEpoch(incident.ground_truth.cleared_time_epoch)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

