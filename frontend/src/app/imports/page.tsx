"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  UploadCloud,
  FileCheck2,
  AlertCircle,
  CheckCircle2,
  Clock,
  Layers,
  FileCode2,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";

export default function ImportsPage() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [summary, setSummary] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [jobs, setJobs] = useState<any[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(true);

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

  useEffect(() => {
    loadJobs();
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

  const formatEpoch = (isoStr: string) => {
    return new Date(isoStr).toLocaleString();
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <div>
        <h1 className="text-xl font-bold tracking-tight text-slate-100 flex items-center gap-2.5">
          <UploadCloud className="h-5 w-5 text-cyan-400" />
          SIEM Incident & Rule Ingestion Portal
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Ingest raw incident JSONs or nested ZIP archives with automatic SIEM rule extraction and ground-truth isolation
        </p>
      </div>

      {/* Upload Card */}
      <div className="rounded-xl border border-slate-800 bg-slate-950 p-6 shadow-sm">
        <h2 className="text-sm font-bold text-slate-200 mb-1">Upload Archive or JSON Telemetry</h2>
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

      {/* Historical Import Jobs */}
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
