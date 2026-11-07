"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  UploadCloud,
  FileCheck2,
  AlertCircle,
  CheckCircle2,
  Clock,
  Layers,
  FileCode2,
  RefreshCw,
  Server,
  DownloadCloud,
  ArrowRight,
  ShieldAlert,
  Zap,
} from "lucide-react";
import { api, FortiSIEMStatusResponse, FortiSIEMPullResponse } from "@/lib/api";

export default function ImportsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [summary, setSummary] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

  // FortiSIEM Pull States
  const [siemIncidentId, setSiemIncidentId] = useState("");
  const [forceRefresh, setForceRefresh] = useState(false);
  const [isPullingSiem, setIsPullingSiem] = useState(false);
  const [siemStatus, setSiemStatus] = useState<FortiSIEMStatusResponse | null>(null);
  const [siemResult, setSiemResult] = useState<FortiSIEMPullResponse | null>(null);
  const [siemError, setSiemError] = useState<string | null>(null);

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

  useEffect(() => {
    loadJobs();
    loadSiemStatus();
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
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
          <DownloadCloud className="h-5 w-5 text-cyan-400" />
          FortiSIEM Incident Ingestion & Sync Portal
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Pull live security incidents on-demand by FortiSIEM Incident ID, or upload batch telemetry archives with zero ground-truth leakage
        </p>
      </div>

      {/* 1. FortiSIEM On-Demand Pull Card */}
      <div className="rounded-xl border border-cyan-900/60 bg-gradient-to-br from-slate-950 via-slate-900/90 to-cyan-950/20 p-6 shadow-lg shadow-cyan-950/10 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <Server className="h-4 w-4 text-cyan-400" />
              Pull Incident by FortiSIEM Incident ID
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Enter any FortiSIEM Incident ID to query the Supervisor API, ingest triggering logs, and isolate ground-truth
            </p>
          </div>

          {/* Mode & Connection Status Badge */}
          <div className="flex items-center gap-2">
            {siemStatus?.is_configured ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live FortiSIEM Connected ({siemStatus.host})
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium bg-sky-950 text-sky-300 border border-sky-800 font-mono">
                <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                Fixture Fallback Mode (Ready)
              </span>
            )}
          </div>
        </div>

        {/* Pull Form */}
        <form onSubmit={handlePullFortiSiem} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1 relative">
              <input
                type="text"
                value={siemIncidentId}
                onChange={(e) => setSiemIncidentId(e.target.value)}
                placeholder="Enter Incident ID (e.g., 132438483 or 132499009)..."
                className="w-full rounded-lg border border-slate-700 bg-slate-900/90 py-2.5 pl-3.5 pr-10 text-xs font-mono text-slate-100 placeholder-slate-500 focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 focus:outline-none"
              />
              {siemIncidentId && (
                <button
                  type="button"
                  onClick={() => setSiemIncidentId("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 text-xs font-mono"
                >
                  Clear
                </button>
              )}
            </div>

            <button
              type="submit"
              disabled={!siemIncidentId.trim() || isPullingSiem}
              className="rounded-lg bg-cyan-600 px-6 py-2.5 text-xs font-bold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors flex items-center justify-center gap-2 shadow-sm shadow-cyan-900/40"
            >
              {isPullingSiem ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Querying FortiSIEM...
                </>
              ) : (
                <>
                  <Zap className="h-3.5 w-3.5 text-cyan-200" />
                  Pull Incident
                </>
              )}
            </button>
          </div>

          {/* Quick Select Sample IDs */}
          {siemStatus && siemStatus.sample_incident_ids.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 pt-1">
              <span className="text-[11px] text-slate-400 font-mono mr-1">Quick Select Samples:</span>
              {siemStatus.sample_incident_ids.slice(0, 6).map((id) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    setSiemIncidentId(id);
                    handlePullFortiSiem(undefined, id);
                  }}
                  disabled={isPullingSiem}
                  className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-900 border border-slate-800 text-cyan-300 hover:bg-cyan-950/60 hover:border-cyan-700 transition-colors"
                >
                  #{id}
                </button>
              ))}
              {siemStatus.sample_incident_ids.length > 6 && (
                <span className="text-[10px] text-slate-500 font-mono">
                  +{siemStatus.sample_incident_ids.length - 6} more
                </span>
              )}
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
          <div className="rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
            <div>
              <span className="font-semibold block">FortiSIEM Query Failed</span>
              <span>{siemError}</span>
            </div>
          </div>
        )}

        {/* Pull Success Result Banner */}
        {siemResult && (
          <div className="rounded-xl border border-emerald-800/80 bg-emerald-950/20 p-5 space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                <CheckCircle2 className="h-4 w-4" />
                Incident Retrieved Successfully
              </div>
              <span className="text-[11px] text-slate-400">
                Source: <span className="text-cyan-300 font-bold">{siemResult.source}</span>
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-200 space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-bold text-slate-100 text-sm">{siemResult.title}</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getSeverityBadge(siemResult.severity)}`}>
                  {siemResult.severity}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                  ID: #{siemResult.incident_id}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950 text-cyan-300 border border-cyan-800">
                  {siemResult.event_count} Raw Events Ingested
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans">
                {siemResult.message} Ground truth isolation applied: resolution and closure data segregated into protected storage.
              </p>
            </div>

            <div className="flex items-center gap-3 pt-1">
              {siemResult.db_id && (
                <Link
                  href={`/incidents/${siemResult.db_id}`}
                  className="inline-flex items-center gap-2 rounded-lg bg-cyan-600 px-4 py-2 text-xs font-bold text-white hover:bg-cyan-500 transition-colors shadow-sm"
                >
                  View Incident & Run AI Investigation
                  <ArrowRight className="h-3.5 w-3.5" />
                </Link>
              )}
              <Link
                href="/analyst-attention"
                className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors"
              >
                Go to Analyst Queue
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* 2. File Upload Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 shadow-sm">
        <h2 className="text-sm font-bold text-slate-200 mb-1">Batch Archive or JSON Telemetry Upload</h2>
        <p className="text-xs text-slate-400 mb-4">
          Supports <code className="text-cyan-400 font-mono">.zip</code> archives containing nested JSON files and <code className="text-cyan-400 font-mono">Rule_info.txt</code> specifications, or standalone <code className="text-cyan-400 font-mono">.json</code> incident files.
        </p>

        <form onSubmit={handleUpload} className="space-y-4">
          <div
            onClick={() => fileInputRef.current?.click()}
            className="flex flex-col items-center justify-center border-2 border-dashed border-slate-800 rounded-xl p-8 cursor-pointer hover:border-cyan-500/60 bg-slate-900/40 transition-colors"
          >
            <UploadCloud className="h-10 w-10 text-cyan-400 mb-3" />
            <span className="text-xs font-semibold text-slate-200">
              {selectedFile ? selectedFile.name : "Click to select a file or drag and drop here"}
            </span>
            <span className="text-[11px] text-slate-500 font-mono mt-1">
              {selectedFile
                ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB · Ready to upload`
                : "ZIP or JSON up to 50 MB"}
            </span>
            <input
              ref={fileInputRef}
              type="file"
              accept=".zip,.json"
              onChange={handleFileChange}
              className="hidden"
            />
          </div>

          <div className="flex items-center justify-between">
            <span className="text-[11px] text-slate-500 font-mono">
              Safeguards: Zip slip path traversal defense · Decompression bomb limits active
            </span>
            <button
              type="submit"
              disabled={!selectedFile || isUploading}
              className="rounded-lg bg-cyan-600 px-5 py-2 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors flex items-center gap-2"
            >
              {isUploading ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Processing Ingestion...
                </>
              ) : (
                "Start Ingestion"
              )}
            </button>
          </div>
        </form>

        {/* Error Alert */}
        {error && (
          <div className="mt-4 rounded-lg border border-rose-800 bg-rose-950/40 p-4 text-xs text-rose-300 flex items-start gap-2.5">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
            <div>
              <span className="font-semibold block">Ingestion Failed</span>
              <span>{error}</span>
            </div>
          </div>
        )}

        {/* Ingestion Summary Report */}
        {summary && (
          <div className="mt-5 rounded-xl border border-emerald-800/80 bg-emerald-950/20 p-5 space-y-3 font-mono text-xs">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
              <CheckCircle2 className="h-4 w-4" />
              Ingestion Completed Successfully
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-slate-200 pt-2">
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 block">Total Entries:</span>
                <span className="text-base font-bold">{summary.total_found}</span>
              </div>
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-emerald-400 block">Imported Incidents:</span>
                <span className="text-base font-bold text-emerald-400">{summary.imported}</span>
              </div>
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-blue-400 block">Rules Detected:</span>
                <span className="text-base font-bold text-blue-400">{summary.rules_detected}</span>
              </div>
              <div className="p-3 rounded bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-amber-400 block">Duplicates Handled:</span>
                <span className="text-base font-bold text-amber-400">{summary.duplicates}</span>
              </div>
            </div>

            {summary.error_messages && summary.error_messages.length > 0 && (
              <div className="pt-2">
                <span className="text-rose-400 block font-semibold mb-1">Warnings / Errors:</span>
                <ul className="list-disc list-inside text-rose-300 space-y-0.5 text-[11px]">
                  {summary.error_messages.map((m: string, idx: number) => (
                    <li key={idx}>{m}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 3. Historical Ingestion Jobs Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-200">Recent Ingestion Jobs</h2>
          <button
            onClick={loadJobs}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200"
          >
            <RefreshCw className={`h-3 w-3 ${loadingJobs ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] text-slate-400">
                <th className="pb-2 font-medium">Filename</th>
                <th className="pb-2 font-medium">Format</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2 font-medium">Imported</th>
                <th className="pb-2 font-medium">Duplicates</th>
                <th className="pb-2 font-medium">Errors</th>
                <th className="pb-2 font-medium text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                    No import jobs recorded yet.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-900/40">
                    <td className="py-2.5 font-semibold text-slate-200">{job.filename}</td>
                    <td className="py-2.5 text-slate-400">{job.file_type}</td>
                    <td className="py-2.5">
                      <span
                        className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          job.status === "COMPLETED"
                            ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                            : "bg-amber-950 text-amber-300 border border-amber-800"
                        }`}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td className="py-2.5 text-emerald-400 font-bold">{job.imported_count}</td>
                    <td className="py-2.5 text-amber-400">{job.duplicate_count}</td>
                    <td className="py-2.5 text-rose-400">{job.error_count}</td>
                    <td className="py-2.5 text-right text-slate-500 text-[11px]">
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
