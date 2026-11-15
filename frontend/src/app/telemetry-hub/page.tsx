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
  Database,
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
  const [countdownSeconds, setCountdownSeconds] = useState<number | null>(null);

  useEffect(() => {
    if (!schedulerStatus?.next_sync_time || !schedulerStatus?.is_running) {
      setCountdownSeconds(null);
      return;
    }
    const tick = () => {
      const diffMs = new Date(schedulerStatus.next_sync_time!).getTime() - Date.now();
      setCountdownSeconds(Math.max(0, Math.round(diffMs / 1000)));
    };
    tick();
    const timer = setInterval(tick, 1000);
    return () => clearInterval(timer);
  }, [schedulerStatus?.next_sync_time, schedulerStatus?.is_running]);

  // Global Telemetry Timeline State on Server 1
  const [globalTimeline, setGlobalTimeline] = useState<any[]>([]);
  const [loadingTimeline, setLoadingTimeline] = useState(false);

  // Compact Tab State
  const [onDemandTab, setOnDemandTab] = useState<"single" | "archive">("single");
  const [historyTab, setHistoryTab] = useState<"jobs" | "timeline">("jobs");

  const loadGlobalTimeline = async () => {
    setLoadingTimeline(true);
    try {
      const res = await api.getGlobalTelemetryTimeline(30);
      setGlobalTimeline(res.timeline || []);
    } catch {
      // fallback
    } finally {
      setLoadingTimeline(false);
    }
  };

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
    loadGlobalTimeline();

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
      const res = await api.processPendingFortiSiemVerdicts(100, true);
      await loadSchedulerStatus();
      await loadJobs();
      setSchedulerMsg(res.message || "Started background pending AI verdict processing with Local LLM.");
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
    <div className="space-y-3 w-full">
      {/* 1. COMPACT PAGE HEADER */}
      <div className="p-3 sm:px-4 rounded-xl border border-slate-800/80 bg-slate-950/70 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h1 className="text-base sm:text-lg font-bold tracking-tight text-slate-100 flex items-center gap-2">
            <DownloadCloud className="h-4 w-4 text-cyan-400" />
            Telemetry Hub
          </h1>
          <p className="text-[11px] text-slate-400 mt-0.5">
            Sentinel Ingest Worker &amp; Continuous Telemetry Pipeline · Automated ingestion, queue scheduling, and AI triage
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Link
            href="/rules"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <FileCode2 className="h-3.5 w-3.5 text-cyan-400" />
            <span>SIEM Rules</span>
          </Link>
          <Link
            href="/agent-configuration#fortisiem"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium border border-slate-700 bg-slate-900 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <Settings className="h-3.5 w-3.5 text-cyan-400" />
            <span>SIEM Config</span>
          </Link>
        </div>
      </div>

      {/* 2. TOP 4 COMPACT KPI TILES */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
        {/* Poller Status */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
            <span>Continuous Poller</span>
            <span className={`w-2 h-2 rounded-full ${schedulerStatus?.is_running ? "bg-emerald-400 animate-pulse" : "bg-slate-500"}`} />
          </div>
          <div className="my-1">
            <span className={`text-base sm:text-lg font-extrabold tracking-tight ${schedulerStatus?.is_running ? "text-emerald-400" : "text-slate-400"}`}>
              {schedulerStatus?.is_running ? "Active (Every 3m)" : "Poller Idle"}
            </span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono truncate">
            {schedulerStatus?.is_running && countdownSeconds !== null
              ? `Next sync in ${countdownSeconds >= 60 ? `${Math.floor(countdownSeconds / 60)}m ${countdownSeconds % 60}s` : `${countdownSeconds}s`}`
              : `Interval: ${schedulerStatus?.interval_seconds || 180}s`}
          </div>
        </div>

        {/* Total Alerts Ingested */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
            <span>Total Pulled</span>
            <Database className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="my-1">
            <span className="text-xl sm:text-2xl font-extrabold text-slate-100 font-mono tabular-nums">
              {schedulerStatus?.total_pulled_count || 0}
            </span>
            <span className="text-xs text-slate-400 ml-1">alerts</span>
          </div>
          <div className="text-[10px] text-slate-500 font-mono truncate">
            Status: {schedulerStatus?.last_status || "IDLE"}
          </div>
        </div>

        {/* AI Verdicts Generated */}
        <div className="p-3 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col justify-between">
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
            <span>AI Verdicts</span>
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="my-1">
            <span className="text-xl sm:text-2xl font-extrabold text-cyan-300 font-mono tabular-nums">
              {schedulerStatus?.total_ai_verdicts_count || 0}
            </span>
            <span className="text-xs text-slate-400 ml-1">verdicts</span>
          </div>
          <div className="text-[10px] text-slate-500 truncate">
            {autoTriageWithLLM ? "Auto-Triage Active" : "Manual Execution"}
          </div>
        </div>

        {/* LLM Status & Backlog Queue */}
        <div className={`p-3 rounded-xl border flex flex-col justify-between ${
          (schedulerStatus?.pending_ai_verdicts_count ?? 0) > 0
            ? "border-amber-800/60 bg-amber-950/20"
            : "border-slate-800 bg-slate-900/60"
        }`}>
          <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
            <span>Local LLM Engine</span>
            <span className={`w-2 h-2 rounded-full ${schedulerStatus?.is_llm_online ? "bg-emerald-400" : "bg-amber-400 animate-pulse"}`} />
          </div>
          <div className="my-1">
            <span className={`text-base sm:text-lg font-extrabold tracking-tight ${schedulerStatus?.is_llm_online ? "text-emerald-300" : "text-amber-400"}`}>
              {schedulerStatus?.is_llm_online ? "Online" : "Offline"}
            </span>
          </div>
          <div className="text-[10px] font-mono truncate text-slate-400">
            {(schedulerStatus?.pending_ai_verdicts_count ?? 0) > 0 ? (
              <span className="text-amber-300 font-bold">{schedulerStatus?.pending_ai_verdicts_count} pending in queue</span>
            ) : (
              <span className="text-slate-500">Queue clear (0 pending)</span>
            )}
          </div>
        </div>
      </div>

      {/* 3. DUAL-COLUMN INGESTION CONTROL CENTER */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* LEFT COLUMN (7 COLS): SENTINEL INGEST WORKER & CONTINUOUS POLLER */}
        <div className="lg:col-span-7 rounded-xl border border-cyan-800/60 bg-slate-950/90 p-3.5 space-y-3 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2.5">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-cyan-400" />
              <div>
                <h2 className="text-xs sm:text-sm font-bold text-slate-100">
                  Sentinel Ingest Worker &amp; Poller
                </h2>
                <p className="text-[10px] text-slate-400">
                  Continuous automated ingestion &amp; AI triage with Local LLM
                </p>
              </div>
            </div>

            <label className="flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoTriageWithLLM}
                onChange={(e) => setAutoTriageWithLLM(e.target.checked)}
                className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
              />
              <span className="flex items-center gap-1 text-[11px] text-cyan-300 font-medium">
                <Sparkles className="h-3 w-3 text-cyan-400" />
                Auto-Triage LLM
              </span>
            </label>
          </div>

          {/* Action Toolbar */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Pull All Button */}
            <button
              type="button"
              onClick={handlePullAllIncidents}
              disabled={isPullingBatch || isPullingSiem}
              className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors shadow-sm"
            >
              {isPullingBatch ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Pulling All Incidents...
                </>
              ) : (
                <>
                  <DownloadCloud className="h-3.5 w-3.5" />
                  Pull All Incidents
                </>
              )}
            </button>

            {/* Start/Pause Continuous Sync */}
            <button
              type="button"
              onClick={handleToggleScheduler}
              disabled={isOperatingScheduler}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-bold text-white transition-colors shadow-sm ${
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
              {schedulerStatus?.is_running ? "Pause Poller" : "Start Continuous Sync"}
            </button>

            {/* Sync Now */}
            <button
              type="button"
              onClick={handleTriggerSchedulerNow}
              disabled={isOperatingScheduler}
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <Zap className="h-3.5 w-3.5 text-cyan-400" />
              Sync Cycle Now
            </button>

            {/* Reconcile Pending Queue */}
            {(schedulerStatus?.pending_ai_verdicts_count ?? 0) > 0 && (
              <button
                type="button"
                onClick={handleProcessPending}
                disabled={isProcessingPending || !schedulerStatus?.is_llm_online}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-600 bg-amber-950/60 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:text-white hover:bg-amber-900 disabled:opacity-50 transition-colors shadow-sm"
                title={schedulerStatus?.is_llm_online ? "Process pending incidents with Local LLM one by one" : "Local LLM is offline. Backlog will auto-process once Local LLM comes online."}
              >
                {isProcessingPending ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                )}
                <span>Reconcile Queue ({schedulerStatus?.pending_ai_verdicts_count})</span>
              </button>
            )}
          </div>

          {/* Polling Metadata Strip */}
          <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px] font-mono">
            <span className="flex items-center gap-1.5 text-slate-300">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              Next Sync:{" "}
              <strong className="text-cyan-300">
                {countdownSeconds !== null && schedulerStatus?.is_running
                  ? countdownSeconds >= 60
                    ? `${Math.floor(countdownSeconds / 60)}m ${countdownSeconds % 60}s`
                    : `${countdownSeconds}s`
                  : schedulerStatus?.is_running
                  ? "Scheduled..."
                  : "Poller Idle"}
              </strong>
            </span>
            {schedulerStatus?.last_sync_time && (
              <span className="text-slate-400">
                Last Synced: {new Date(schedulerStatus.last_sync_time).toLocaleTimeString()}
              </span>
            )}
          </div>

          {/* Warnings & Result Notifications */}
          {schedulerStatus?.last_error && schedulerStatus?.is_running && (
            <div className="px-3 py-1.5 rounded bg-amber-950/40 border border-amber-800/60 text-[11px] text-amber-300 flex items-center justify-between gap-2">
              <span className="truncate">
                <strong>Cycle Warning:</strong> {schedulerStatus.last_error}
              </span>
              <span className="text-[10px] text-amber-400 shrink-0 font-mono">Auto-retrying</span>
            </div>
          )}

          {schedulerMsg && (
            <div className="p-2.5 rounded bg-cyan-950/60 border border-cyan-800 text-xs text-cyan-200 font-mono">
              {schedulerMsg}
            </div>
          )}

          {batchPullError && (
            <div className="p-3 rounded bg-rose-950/50 border border-rose-800 text-xs text-rose-300 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
              <span>{batchPullError}</span>
            </div>
          )}

          {batchPullResult && (
            <div className="p-3 rounded-lg bg-slate-900 border border-emerald-800/80 space-y-1.5 text-xs font-mono">
              <div className="flex items-center justify-between text-emerald-400 font-bold">
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4" />
                  Batch Pull Complete ({batchPullResult.source})
                </span>
                <span className="text-[10px] text-slate-400 font-sans">
                  Checkpoint: {batchPullResult.checkpoint_epoch}
                </span>
              </div>
              <div className="flex flex-wrap gap-1.5 text-[10px]">
                <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
                  +{batchPullResult.newly_ingested} Newly Ingested
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                  {batchPullResult.already_cached} In DB
                </span>
                <span className="px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold flex items-center gap-1">
                  <Sparkles className="h-3 w-3 text-cyan-300" />
                  {batchPullResult.ai_verdicts_generated} AI Verdicts
                </span>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN (5 COLS): ON-DEMAND INGESTION (TABBED: SINGLE ID vs ARCHIVE UPLOAD) */}
        <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-950/90 p-3.5 space-y-3 shadow-sm flex flex-col justify-between">
          <div className="space-y-3">
            {/* Sub-Tabs: Single ID vs Archive */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setOnDemandTab("single")}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                    onDemandTab === "single"
                      ? "bg-cyan-950 text-cyan-300 border border-cyan-800 shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Pull by ID
                </button>
                <button
                  type="button"
                  onClick={() => setOnDemandTab("archive")}
                  className={`px-2.5 py-1 text-xs font-semibold rounded-md transition-colors ${
                    onDemandTab === "archive"
                      ? "bg-cyan-950 text-cyan-300 border border-cyan-800 shadow-sm"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Archive Upload
                </button>
              </div>

              {onDemandTab === "single" ? (
                siemStatus?.is_configured ? (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    Live SIEM
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium bg-sky-950 text-sky-300 border border-sky-800 font-mono">
                    <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                    Fixture Mode
                  </span>
                )
              ) : (
                <span className="inline-flex items-center gap-1 text-[10px] text-emerald-400 font-mono">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  SanitizationGuard
                </span>
              )}
            </div>

            {/* TAB 1: SINGLE INCIDENT PULL */}
            {onDemandTab === "single" && (
              <div className="space-y-2.5">
                <form onSubmit={handlePullFortiSiem} className="space-y-2">
                  <div className="flex gap-2">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        value={siemIncidentId}
                        onChange={(e) => setSiemIncidentId(e.target.value)}
                        placeholder={
                          siemStatus?.live_incident_ids && siemStatus.live_incident_ids.length > 0
                            ? `Enter Incident ID (e.g. ${siemStatus.live_incident_ids[0]})...`
                            : "Enter Incident ID (e.g., 171005)..."
                        }
                        className="w-full rounded-lg border border-slate-700 bg-slate-900 py-1.5 pl-2.5 pr-8 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                      />
                      {siemIncidentId && (
                        <button
                          type="button"
                          onClick={() => setSiemIncidentId("")}
                          className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-xs font-mono"
                        >
                          ✕
                        </button>
                      )}
                    </div>

                    <button
                      type="submit"
                      disabled={!siemIncidentId.trim() || isPullingSiem}
                      className="rounded-lg bg-cyan-600 px-3.5 py-1.5 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors flex items-center justify-center gap-1 shrink-0 shadow-sm"
                    >
                      {isPullingSiem ? (
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Zap className="h-3.5 w-3.5 text-cyan-200" />
                      )}
                      <span>Pull</span>
                    </button>
                  </div>

                  {/* Sample Fixtures Quick-Click */}
                  {siemStatus && siemStatus.sample_incident_ids.length > 0 && (
                    <div className="flex flex-wrap items-center gap-1 pt-0.5">
                      <span className="text-[10px] text-slate-400 font-mono mr-1">Fixtures:</span>
                      {siemStatus.sample_incident_ids.slice(0, 5).map((id) => (
                        <button
                          key={id}
                          type="button"
                          onClick={() => {
                            setSiemIncidentId(id);
                            handlePullFortiSiem(undefined, id);
                          }}
                          disabled={isPullingSiem}
                          className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-slate-900 border border-slate-800 text-sky-300 hover:bg-sky-950/60 hover:border-sky-700 transition-colors"
                        >
                          #{id}
                        </button>
                      ))}
                    </div>
                  )}

                  <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer select-none pt-0.5">
                    <input
                      type="checkbox"
                      checked={forceRefresh}
                      onChange={(e) => setForceRefresh(e.target.checked)}
                      className="rounded border-slate-700 bg-slate-900 text-cyan-500 focus:ring-0"
                    />
                    Force re-fetch from FortiSIEM if cached
                  </label>
                </form>

                {siemError && (
                  <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-2.5 text-xs text-rose-300 flex items-start gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                    <span className="leading-tight">{siemError}</span>
                  </div>
                )}

                {siemResult && (
                  <div className="rounded-lg border border-emerald-800/80 bg-emerald-950/20 p-3 space-y-1.5 font-mono text-xs">
                    <div className="flex items-center justify-between text-emerald-400 font-bold">
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Incident Retrieved
                      </span>
                      <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-emerald-950 text-emerald-300 border border-emerald-800">
                        {siemResult.source}
                      </span>
                    </div>

                    <div className="text-slate-200">
                      <span className="font-bold text-slate-100">{siemResult.title}</span>
                      <div className="flex items-center gap-1.5 mt-0.5 text-[10px]">
                        <span className={`px-1.5 py-0.2 rounded border font-bold ${getSeverityBadge(siemResult.severity)}`}>
                          {siemResult.severity}
                        </span>
                        <span className="text-slate-400">#{siemResult.incident_id}</span>
                      </div>
                    </div>

                    {siemResult.db_id && (
                      <div className="pt-1">
                        <Link
                          href={`/incidents/${siemResult.db_id}`}
                          className="inline-flex items-center gap-1 rounded bg-cyan-600 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-cyan-500 transition-colors shadow-sm"
                        >
                          View Incident &amp; Investigate
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: ARCHIVE UPLOAD */}
            {onDemandTab === "archive" && (
              <div className="space-y-2.5">
                <form onSubmit={handleUpload} className="space-y-2.5">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".zip,.json"
                    onChange={handleFileChange}
                    className="w-full text-xs text-slate-400 file:mr-2 file:py-1 file:px-2.5 file:rounded file:border file:border-slate-700 file:text-[11px] file:font-semibold file:bg-slate-900 file:text-cyan-400 hover:file:bg-slate-800 file:cursor-pointer cursor-pointer border border-slate-800 rounded-lg p-1 bg-slate-900/40"
                  />
                  <button
                    type="submit"
                    disabled={!selectedFile || isUploading}
                    className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-xs font-bold text-slate-100 hover:bg-slate-700 disabled:opacity-50 transition-colors flex items-center justify-center gap-1.5"
                  >
                    {isUploading ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin text-cyan-400" />
                        Ingesting Archive...
                      </>
                    ) : (
                      <>
                        <UploadCloud className="h-3.5 w-3.5 text-cyan-400" />
                        Upload &amp; Process Archive
                      </>
                    )}
                  </button>
                </form>

                {error && (
                  <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-2.5 text-xs text-rose-300 flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                    <span>{error}</span>
                  </div>
                )}

                {summary && (
                  <div className="rounded-lg border border-emerald-800 bg-emerald-950/30 p-2.5 text-xs text-emerald-300 flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                    <span>
                      Processed {summary.total_files} files ({summary.imported_incidents} imported, {summary.duplicate_incidents} duplicates)
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 4. TABBED INGESTION HISTORY & TIMELINE SECTION */}
      <div className="rounded-xl border border-slate-800 bg-slate-950/80 p-3 sm:p-3.5 space-y-3 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2">
          {/* Sub-Tabs: Jobs vs Timeline */}
          <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
            <button
              type="button"
              onClick={() => setHistoryTab("jobs")}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                historyTab === "jobs"
                  ? "bg-cyan-950 text-cyan-300 border border-cyan-800 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>Ingestion History ({jobs.length})</span>
            </button>
            <button
              type="button"
              onClick={() => setHistoryTab("timeline")}
              className={`px-3 py-1 text-xs font-semibold rounded-md transition-colors flex items-center gap-1.5 ${
                historyTab === "timeline"
                  ? "bg-cyan-950 text-cyan-300 border border-cyan-800 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Verdictum Core Timeline ({globalTimeline.length})</span>
            </button>
          </div>

          <div>
            {historyTab === "jobs" ? (
              <button
                type="button"
                onClick={loadJobs}
                disabled={loadingJobs}
                className="text-[10px] text-slate-400 hover:text-slate-200 flex items-center gap-1 font-mono px-2 py-1 rounded bg-slate-900 border border-slate-800"
              >
                <RefreshCw className={`h-3 w-3 ${loadingJobs ? "animate-spin text-cyan-400" : ""}`} />
                Refresh Jobs
              </button>
            ) : (
              <button
                type="button"
                onClick={loadGlobalTimeline}
                disabled={loadingTimeline}
                className="text-[10px] text-slate-400 hover:text-slate-200 flex items-center gap-1 font-mono px-2 py-1 rounded bg-slate-900 border border-slate-800"
              >
                <RefreshCw className={`h-3 w-3 ${loadingTimeline ? "animate-spin text-cyan-400" : ""}`} />
                Refresh Timeline
              </button>
            )}
          </div>
        </div>

        {/* TAB A: INGESTION JOBS TABLE */}
        {historyTab === "jobs" && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-[10px] text-slate-400">
                  <th className="pb-2 px-2.5 font-medium">Filename</th>
                  <th className="pb-2 px-2.5 font-medium">Format</th>
                  <th className="pb-2 px-2.5 font-medium">Status</th>
                  <th className="pb-2 px-2.5 font-medium">Imported</th>
                  <th className="pb-2 px-2.5 font-medium">Duplicates</th>
                  <th className="pb-2 px-2.5 font-medium">Errors</th>
                  <th className="pb-2 px-2.5 font-medium text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500 font-sans text-xs">
                      No import jobs recorded yet.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr key={job.id} className="hover:bg-slate-900/40">
                      <td className="py-2 px-2.5 font-semibold text-slate-200">{job.filename}</td>
                      <td className="py-2 px-2.5 text-slate-400">{job.file_type}</td>
                      <td className="py-2 px-2.5">
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
                      <td className="py-2 px-2.5 text-emerald-400 font-bold">{job.imported_count}</td>
                      <td className="py-2 px-2.5 text-amber-400">{job.duplicate_count}</td>
                      <td className="py-2 px-2.5 text-rose-400">{job.error_count}</td>
                      <td className="py-2 px-2.5 text-right text-slate-500 text-[10px]">
                        {formatEpoch(job.created_at)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* TAB B: CORE STORAGE TIMELINE */}
        {historyTab === "timeline" && (
          <div>
            {globalTimeline.length === 0 ? (
              <div className="py-8 text-center text-slate-500 font-mono text-xs">
                No global telemetry timeline milestones recorded yet. Telemetry batches will appear here as they are ingested on Verdictum Core.
              </div>
            ) : (
              <div className="relative border-l border-slate-800 pl-4 space-y-2.5 text-xs font-mono max-h-[400px] overflow-y-auto pr-1">
                {globalTimeline.map((item, idx) => (
                  <div key={item.id || idx} className="relative">
                    <span className="absolute -left-[23px] flex h-3 w-3 items-center justify-center rounded-full bg-cyan-950 border border-cyan-500 text-cyan-300 text-[7px]">
                      ●
                    </span>
                    <div className="rounded-lg bg-slate-900/70 border border-slate-800/80 p-2.5 space-y-1">
                      <div className="flex items-center justify-between text-[10px]">
                        <div className="flex items-center gap-1.5">
                          <span className="px-1.5 py-0.2 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold text-[9px]">
                            {item.stage || "INGESTION"}
                          </span>
                          {item.incident_id && (
                            <Link
                              href={`/incidents/${item.incident_id}`}
                              className="text-cyan-400 hover:underline font-bold"
                            >
                              Incident #{item.incident_id}
                            </Link>
                          )}
                        </div>
                        <span className="text-slate-500">{new Date(item.timestamp).toLocaleString()}</span>
                      </div>
                      <p className="text-slate-300 text-xs font-sans">{item.summary}</p>
                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-0.5 border-t border-slate-900">
                        <span>Source: {item.source}</span>
                        {item.token_count > 0 && (
                          <span className="text-purple-300 font-bold">
                            Tokens: {item.token_count.toLocaleString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
