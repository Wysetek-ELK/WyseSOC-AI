"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  UploadCloud,
  FileArchive,
  CheckCircle2,
  AlertCircle,
  Clock,
  ShieldCheck,
  FileCode2,
  Server,
  Zap,
  ArrowRight,
  RefreshCw,
  Settings,
  Sparkles,
  Bot,
  Play,
  Pause,
  DownloadCloud,
} from "lucide-react";
import {
  api,
  FortiSIEMStatusResponse,
  FortiSIEMPullResponse,
  FortiSIEMBatchPullResponse,
  FortiSIEMSchedulerStatusResponse,
} from "@/lib/api";

export default function TelemetryHubPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [summary, setSummary] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

  // FortiSIEM Single Pull States
  const [siemIncidentId, setSiemIncidentId] = useState("");
  const [forceRefresh, setForceRefresh] = useState(false);
  const [isPullingSiem, setIsPullingSiem] = useState(false);
  const [siemStatus, setSiemStatus] = useState<FortiSIEMStatusResponse | null>(null);
  const [siemResult, setSiemResult] = useState<FortiSIEMPullResponse | null>(null);
  const [siemError, setSiemError] = useState<string | null>(null);

  // Batch Pull (No ID required) & Continuous Poller States
  const [isPullingBatch, setIsPullingBatch] = useState(false);
  const [batchPullResult, setBatchPullResult] = useState<FortiSIEMBatchPullResponse | null>(null);
  const [batchPullError, setBatchPullError] = useState<string | null>(null);
  const [autoTriageWithLLM, setAutoTriageWithLLM] = useState(true);
  const [batchMaxCount, setBatchMaxCount] = useState(50);

  // Continuous Scheduler States
  const [schedulerStatus, setSchedulerStatus] = useState<FortiSIEMSchedulerStatusResponse | null>(null);
  const [isOperatingScheduler, setIsOperatingScheduler] = useState(false);
  const [isProcessingPending, setIsProcessingPending] = useState(false);
  const [schedulerMsg, setSchedulerMsg] = useState<string | null>(null);

  const loadJobs = async () => {
    setLoadingJobs(true);
    try {
      const data = await api.getImportJobs();
      setJobs(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingJobs(false);
    }
  };

  const loadSiemStatus = async () => {
    try {
      const status = await api.getFortiSiemStatus();
      setSiemStatus(status);
    } catch (err) {
      console.error("Failed to load FortiSIEM status", err);
    }
  };

  const loadSchedulerStatus = async () => {
    try {
      const status = await api.getFortiSiemSchedulerStatus();
      setSchedulerStatus(status);
    } catch (err) {
      console.error("Failed to load scheduler status", err);
    }
  };

  useEffect(() => {
    loadJobs();
    loadSiemStatus();
    loadSchedulerStatus();

    // Poll scheduler status every 10s to keep countdown/status fresh
    const interval = setInterval(loadSchedulerStatus, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setError(null);
      setSummary(null);
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);
    setSummary(null);

    try {
      const res = await api.uploadImport(selectedFile);
      setSummary(res);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      loadJobs();
    } catch (err: any) {
      setError(err.message || "Upload and ingestion failed");
    } finally {
      setIsUploading(false);
    }
  };

  const handlePullFortiSiem = async (e?: React.FormEvent, overrideId?: string) => {
    if (e) e.preventDefault();
    const targetId = (overrideId || siemIncidentId).trim();
    if (!targetId) return;

    setIsPullingSiem(true);
    setSiemError(null);
    setSiemResult(null);

    try {
      const res = await api.pullFortiSiemIncident(targetId, forceRefresh);
      setSiemResult(res);
      setSiemIncidentId("");
      loadJobs();
    } catch (err: any) {
      setSiemError(err.message || "Failed to pull incident from FortiSIEM");
    } finally {
      setIsPullingSiem(false);
    }
  };

  const handlePullAllIncidents = async () => {
    setIsPullingBatch(true);
    setBatchPullError(null);
    setBatchPullResult(null);

    try {
      const res = await api.pullAllFortiSiemIncidents({
        max_count: batchMaxCount,
        auto_triage_llm: autoTriageWithLLM,
        force_refresh: forceRefresh,
      });
      setBatchPullResult(res);
      loadJobs();
      loadSchedulerStatus();
    } catch (err: any) {
      setBatchPullError(err.message || "Failed to pull all incidents from FortiSIEM");
    } finally {
      setIsPullingBatch(false);
    }
  };

  const handleToggleScheduler = async () => {
    setIsOperatingScheduler(true);
    setSchedulerMsg(null);
    try {
      if (schedulerStatus?.is_running) {
        const res = await api.stopFortiSiemScheduler();
        setSchedulerStatus(res);
        setSchedulerMsg("Continuous poller paused.");
      } else {
        const res = await api.startFortiSiemScheduler({
          interval_seconds: 180,
          auto_ai_verdict: autoTriageWithLLM,
        });
        setSchedulerStatus(res);
        setSchedulerMsg("Continuous poller started! Polling FortiSIEM every 3 minutes.");
      }
    } catch (err: any) {
      setSchedulerMsg(err.message || "Scheduler operation failed");
    } finally {
      setIsOperatingScheduler(false);
    }
  };

  const handleTriggerSchedulerNow = async () => {
    setIsOperatingScheduler(true);
    setSchedulerMsg(null);
    try {
      await api.triggerFortiSiemScheduler();
      await loadSchedulerStatus();
      await loadJobs();
      setSchedulerMsg("Triggered immediate sync cycle successfully!");
    } catch (err: any) {
      setSchedulerMsg(err.message || "Immediate trigger failed");
    } finally {
      setIsOperatingScheduler(false);
    }
  };

  const handleProcessPending = async () => {
    setIsProcessingPending(true);
    setSchedulerMsg(null);
    try {
      const res = await api.processPendingFortiSiemVerdicts(100);
      await loadSchedulerStatus();
      await loadJobs();
      setSchedulerMsg(res.message || "Processed pending incidents with Local LLM.");
    } catch (err: any) {
      setSchedulerMsg(err.message || "Failed processing pending incidents.");
    } finally {
      setIsProcessingPending(false);
    }
  };

  const formatEpoch = (isoStr: string) => {
    return new Date(isoStr).toLocaleString();
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev?.toUpperCase()) {
      case "CRITICAL":
        return "bg-rose-950 text-rose-300 border-rose-800";
      case "HIGH":
        return "bg-orange-950 text-orange-300 border-orange-800";
      case "MEDIUM":
        return "bg-amber-950 text-amber-300 border-amber-800";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="space-y-3.5 max-w-5xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
          <DownloadCloud className="h-4 w-4 text-cyan-400" />
          Telemetry Hub
        </h1>
        <p className="text-[11px] text-slate-400 mt-0.5">
          Sentinel Ingest Worker &amp; Continuous Telemetry Pipeline · Pull all incidents automatically and auto-evaluate with Verdict Triage Agent
        </p>
      </div>

      {/* 1. Continuous 3-Minute Sync & Batch Ingestion Banner */}
      <div className="rounded-lg border border-cyan-800/60 bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950/30 p-3 sm:p-4 shadow-md space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2.5 border-b border-slate-800">
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-1.5">
              <Bot className="h-4 w-4 text-cyan-400" />
              Sentinel Ingest Worker &amp; Continuous Telemetry Poller
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              First pull all historical alerts without Incident IDs, then continuously poll every 3 minutes with automatic LLM verdict generation
            </p>
          </div>

          {/* Status Pills */}
          <div className="flex flex-wrap items-center gap-2">
            {schedulerStatus?.is_llm_online ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-700 font-mono shadow-sm">
                <span className="h-2 w-2 rounded-full bg-emerald-400" />
                Local LLM Online
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-950/80 text-amber-300 border border-amber-700 font-mono shadow-sm">
                <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
                Local LLM Offline (Queued)
              </span>
            )}
            {schedulerStatus?.is_running ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-700 font-mono shadow-sm">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                Active Poller (Every 3 Mins)
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-900 text-slate-400 border border-slate-700 font-mono">
                <span className="h-2 w-2 rounded-full bg-slate-500" />
                Continuous Poller Idle
              </span>
            )}
          </div>
        </div>

        {/* Poller Control Bar & Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs font-mono">
          <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
            <span className="text-[10px] text-slate-400 block font-sans">Polling Interval</span>
            <span className="font-bold text-cyan-300 text-sm">{schedulerStatus?.interval_seconds || 180}s (3m)</span>
          </div>
          <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
            <span className="text-[10px] text-slate-400 block font-sans">Total Pulled</span>
            <span className="font-bold text-emerald-400 text-sm">{schedulerStatus?.total_pulled_count || 0} alerts</span>
          </div>
          <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
            <span className="text-[10px] text-slate-400 block font-sans">AI Verdicts Generated</span>
            <span className="font-bold text-sky-400 text-sm">{schedulerStatus?.total_ai_verdicts_count || 0}</span>
          </div>
          <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
            <span className="text-[10px] text-slate-400 block font-sans">Pending LLM Queue</span>
            <span className={`font-bold text-sm ${(schedulerStatus?.pending_ai_verdicts_count ?? 0) > 0 ? "text-amber-400 animate-pulse" : "text-slate-400"}`}>
              {schedulerStatus?.pending_ai_verdicts_count ?? 0} pending
            </span>
          </div>
          <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
            <span className="text-[10px] text-slate-400 block font-sans">Last Cycle Status</span>
            <span className="font-bold text-slate-200 text-sm">{schedulerStatus?.last_status || "IDLE"}</span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center justify-between gap-2.5 pt-1">
          <div className="flex flex-wrap items-center gap-2">
            {/* 1. Pull All Button */}
            <button
              type="button"
              onClick={handlePullAllIncidents}
              disabled={isPullingBatch || isPullingSiem}
              className="inline-flex items-center gap-1.5 rounded-md bg-cyan-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isPullingBatch ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Pulling All Incidents...
                </>
              ) : (
                <>
                  <DownloadCloud className="h-3.5 w-3.5" />
                  Pull All Incidents Now
                </>
              )}
            </button>

            {/* 2. Start/Pause 3-min Poller Button */}
            <button
              type="button"
              onClick={handleToggleScheduler}
              disabled={isOperatingScheduler}
              className={`inline-flex items-center gap-1.5 rounded-md px-3.5 py-1.5 text-xs font-bold text-white transition-colors shadow-sm ${
                schedulerStatus?.is_running
                  ? "bg-amber-600 hover:bg-amber-500"
                  : "bg-emerald-600 hover:bg-emerald-500"
              }`}
            >
              {isOperatingScheduler ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
              ) : schedulerStatus?.is_running ? (
                <Pause className="h-3.5 w-3.5" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
              {schedulerStatus?.is_running ? "Pause Continuous Sync" : "Start Continuous 3-Min Sync"}
            </button>

            {/* 3. Sync Now Button */}
            <button
              type="button"
              onClick={handleTriggerSchedulerNow}
              disabled={isOperatingScheduler}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <Zap className="h-3.5 w-3.5 text-cyan-400" />
              Sync Cycle Now
            </button>

            {/* 4. Process Pending Button */}
            {(schedulerStatus?.pending_ai_verdicts_count ?? 0) > 0 && (
              <button
                type="button"
                onClick={handleProcessPending}
                disabled={isProcessingPending || !schedulerStatus?.is_llm_online}
                className="inline-flex items-center gap-1.5 rounded-md border border-amber-600 bg-amber-950/60 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:text-white hover:bg-amber-900 disabled:opacity-50 transition-colors shadow-sm"
                title={schedulerStatus?.is_llm_online ? "Process pending incidents with Local LLM one by one" : "Local LLM is offline. Backlog will auto-process once Local LLM comes online."}
              >
                {isProcessingPending ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                )}
                <span>Reconcile Pending ({schedulerStatus?.pending_ai_verdicts_count})</span>
              </button>
            )}
          </div>

          {/* Options: Auto AI Verdict checkbox */}
          <div className="flex items-center gap-3 text-xs text-slate-300">
            <label className="flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoTriageWithLLM}
                onChange={(e) => setAutoTriageWithLLM(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
              />
              <span className="flex items-center gap-1 text-[11px] text-cyan-300 font-medium">
                <Sparkles className="h-3 w-3 text-cyan-400" />
                Auto AI Verdict (LLM)
              </span>
            </label>
          </div>
        </div>

        {/* Scheduler Notification */}
        {schedulerMsg && (
          <div className="p-2.5 rounded bg-cyan-950/60 border border-cyan-800 text-xs text-cyan-200 font-mono">
            {schedulerMsg}
          </div>
        )}

        {/* Batch Pull Error */}
        {batchPullError && (
          <div className="p-3 rounded bg-rose-950/50 border border-rose-800 text-xs text-rose-300 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
            <span>{batchPullError}</span>
          </div>
        )}

        {/* Batch Pull Success Banner */}
        {batchPullResult && (
          <div className="p-3.5 rounded-lg bg-slate-900/90 border border-emerald-800/80 space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between text-emerald-400 font-bold">
              <span className="flex items-center gap-1.5">
                <CheckCircle2 className="h-4 w-4" />
                Batch Pull Complete ({batchPullResult.source})
              </span>
              <span className="text-[10px] text-slate-400 font-sans">
                Watermark Checkpoint: {batchPullResult.checkpoint_epoch}
              </span>
            </div>
            <div className="flex flex-wrap gap-2 text-[11px]">
              <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                +{batchPullResult.newly_ingested} Newly Ingested
              </span>
              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {batchPullResult.already_cached} Already In Database
              </span>
              <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold flex items-center gap-1">
                <Sparkles className="h-3 w-3 text-cyan-300" />
                {batchPullResult.ai_verdicts_generated} AI Verdicts Generated
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-sans">{batchPullResult.message}</p>
          </div>
        )}
      </div>

      {/* 2. FortiSIEM On-Demand Single ID Pull Card */}
      <div className="rounded-lg border border-cyan-900/60 bg-gradient-to-br from-slate-950 via-slate-900/90 to-cyan-950/20 p-3 sm:p-3.5 shadow-md shadow-cyan-950/10 space-y-2.5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-1.5">
              <Server className="h-3.5 w-3.5 text-cyan-400" />
              Pull Individual Incident by ID
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Target a specific FortiSIEM Incident ID for single-incident deep inspection
            </p>
          </div>

          {/* Mode & Connection Status Badge */}
          <div className="flex items-center gap-1.5">
            {siemStatus?.is_configured ? (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live FortiSIEM ({siemStatus.host})
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-sky-950 text-sky-300 border border-sky-800 font-mono">
                <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                Fixture Fallback Mode (Ready)
              </span>
            )}

            <Link
              href="/rules"
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium border border-slate-700 bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <FileCode2 className="h-3 w-3 text-cyan-400" />
              <span>SIEM Rules</span>
            </Link>

            <Link
              href="/agent-configuration#fortisiem"
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium border border-slate-700 bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <Settings className="h-3 w-3 text-cyan-400" />
              <span>Configure SIEM</span>
            </Link>
          </div>
        </div>

        {/* Pull Form */}
        <form onSubmit={handlePullFortiSiem} className="space-y-2">
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="flex-1 relative">
              <input
                type="text"
                value={siemIncidentId}
                onChange={(e) => setSiemIncidentId(e.target.value)}
                placeholder={
                  siemStatus?.live_incident_ids && siemStatus.live_incident_ids.length > 0
                    ? `Enter FortiSIEM Incident ID (e.g., ${siemStatus.live_incident_ids.slice(0, 2).join(" or ")})...`
                    : "Enter FortiSIEM Incident ID (e.g., 171005 or 157803)..."
                }
                className="w-full rounded-md border border-slate-700 bg-slate-900/90 py-1.5 pl-3 pr-8 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none"
              />
              {siemIncidentId && (
                <button
                  type="button"
                  onClick={() => setSiemIncidentId("")}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-xs font-mono"
                >
                  Clear
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={!siemIncidentId.trim() || isPullingSiem}
              className="rounded-md bg-cyan-600 px-4 py-1.5 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5 shadow-sm shadow-cyan-900/40"
            >
              {isPullingSiem ? (
                <>
                  <RefreshCw className="h-3 w-3 animate-spin" />
                  Querying FortiSIEM...
                </>
              ) : (
                <>
                  <Zap className="h-3 w-3 text-cyan-200" />
                  Pull Incident
                </>
              )}
            </button>
          </div>

          {/* Quick Select Sample IDs (Offline Fixtures) */}
          {siemStatus && siemStatus.sample_incident_ids.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
              <span className="text-[11px] text-slate-400 font-mono mr-1">Sample Fixture IDs:</span>
              {siemStatus.sample_incident_ids.slice(0, 6).map((id) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    setSiemIncidentId(id);
                    handlePullFortiSiem(undefined, id);
                  }}
                  disabled={isPullingSiem}
                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-900 border border-slate-800 text-sky-300 hover:bg-sky-950/60 hover:border-sky-700 transition-colors"
                >
                  #{id}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-center gap-2">
            <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={forceRefresh}
                onChange={(e) => setForceRefresh(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
              />
              Force re-fetch from FortiSIEM if incident already exists locally
            </label>
          </div>
        </form>

        {/* Pull Error Message */}
        {siemError && (
          <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-3 text-xs text-rose-300 flex items-start justify-between gap-3">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <div className="space-y-1">
                <span className="font-semibold block text-rose-200">Incident Query Failed</span>
                <span className="text-slate-300 leading-relaxed block">{siemError}</span>
              </div>
            </div>
          </div>
        )}

        {/* Pull Success Result Banner */}
        {siemResult && (
          <div className="rounded-xl border border-emerald-800/80 bg-emerald-950/20 p-4 space-y-2.5 font-mono text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                <CheckCircle2 className="h-4 w-4" />
                Incident Retrieved Successfully
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                {siemResult.source}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-200 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-bold text-slate-100 text-sm">{siemResult.title}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadge(siemResult.severity)}`}>
                  {siemResult.severity}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                  ID: #{siemResult.incident_id}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans">{siemResult.message}</p>
            </div>

            <div className="flex items-center gap-2 pt-0.5">
              {siemResult.db_id && (
                <Link
                  href={`/ai-triage-workbench/${siemResult.db_id}`}
                  className="inline-flex items-center gap-1.5 rounded-md bg-cyan-600 px-3 py-1 text-xs font-bold text-white hover:bg-cyan-500 transition-colors shadow-sm"
                >
                  View Incident &amp; Investigate
                  <ArrowRight className="h-3 w-3" />
                </Link>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 3. Manual ZIP Archive Ingestion Card */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 sm:p-3.5 space-y-2.5">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800">
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-1.5">
              <FileArchive className="h-3.5 w-3.5 text-cyan-400" />
              Upload Telemetry Archive (PayloadSanitizationGuard Protected)
            </h2>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Bulk upload FortiSIEM JSON export archives with automated ground-truth isolation
            </p>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
            <ShieldCheck className="h-3.5 w-3.5" />
            SanitizationGuard Safe
          </div>
        </div>

        <form onSubmit={handleUpload} className="space-y-2.5">
          <div className="flex flex-col sm:flex-row items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip,.json"
              onChange={handleFileChange}
              className="w-full text-xs text-slate-400 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border file:border-slate-700 file:text-xs file:font-semibold file:bg-slate-900 file:text-cyan-400 hover:file:bg-slate-800 file:cursor-pointer cursor-pointer border border-slate-800 rounded-md p-1 bg-slate-950/60"
            />
            <button
              type="submit"
              disabled={!selectedFile || isUploading}
              className="w-full sm:w-auto rounded-md bg-slate-800 border border-slate-700 px-4 py-1.5 text-xs font-bold text-slate-100 hover:bg-slate-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5 shrink-0"
            >
              {isUploading ? (
                <>
                  <RefreshCw className="h-3 w-3 animate-spin text-cyan-400" />
                  Ingesting...
                </>
              ) : (
                <>
                  <UploadCloud className="h-3 w-3 text-cyan-400" />
                  Upload Archive
                </>
              )}
            </button>
          </div>
        </form>

        {error && (
          <div className="rounded border border-rose-800 bg-rose-950/40 p-2.5 text-xs text-rose-300 flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}

        {summary && (
          <div className="rounded border border-emerald-800 bg-emerald-950/30 p-2.5 text-xs text-emerald-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <span>
                Processed {summary.total_files} files ({summary.imported_incidents} imported, {summary.duplicate_incidents} duplicates)
              </span>
            </div>
          </div>
        )}
      </div>

      {/* 4. Import Jobs History */}
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 sm:p-3.5 space-y-2">
        <div className="flex items-center justify-between">
          <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-cyan-400" />
            Ingestion History &amp; Audit Logs
          </h2>
          <button
            onClick={loadJobs}
            disabled={loadingJobs}
            className="text-[10px] text-slate-400 hover:text-slate-200 flex items-center gap-1 font-mono"
          >
            <RefreshCw className={`h-3 w-3 ${loadingJobs ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-[10px] text-slate-400">
                <th className="pb-1.5 px-2 font-medium">Filename</th>
                <th className="pb-1.5 px-2 font-medium">Format</th>
                <th className="pb-1.5 px-2 font-medium">Status</th>
                <th className="pb-1.5 px-2 font-medium">Imported</th>
                <th className="pb-1.5 px-2 font-medium">Duplicates</th>
                <th className="pb-1.5 px-2 font-medium">Errors</th>
                <th className="pb-1.5 px-2 font-medium text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-6 text-center text-slate-500 font-sans text-xs">
                    No import jobs recorded yet.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-900/40">
                    <td className="py-1.5 px-2 font-semibold text-slate-200">{job.filename}</td>
                    <td className="py-1.5 px-2 text-slate-400">{job.file_type}</td>
                    <td className="py-1.5 px-2">
                      <span
                        className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                          job.status === "COMPLETED"
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            : "bg-amber-950 text-amber-300 border border-amber-800"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="py-1.5 px-2 text-emerald-400 font-bold">{job.imported_count}</td>
                    <td className="py-1.5 px-2 text-amber-400">{job.duplicate_count}</td>
                    <td className="py-1.5 px-2 text-rose-400">{job.error_count}</td>
                    <td className="py-1.5 px-2 text-right text-slate-500 text-[10px]">
                      {formatEpoch(job.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
