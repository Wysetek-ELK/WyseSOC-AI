"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Server,
  Cpu,
  HardDrive,
  Zap,
  Activity,
  Clock,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Thermometer,
  Gauge,
  TrendingUp,
  Radio,
  Sliders,
} from "lucide-react";
import {
  api,
  ServersLiveResponse,
  ServersHistoryResponse,
  ServerHistoryDataPoint,
} from "@/lib/api";

interface ServerInfrastructureMonitorProps {
  compact?: boolean;
}

export function ServerInfrastructureMonitor({ compact = false }: ServerInfrastructureMonitorProps) {
  const [liveData, setLiveData] = useState<ServersLiveResponse | null>(null);
  const [historyData, setHistoryData] = useState<ServersHistoryResponse | null>(null);
  const [windowRange, setWindowRange] = useState<"1h" | "6h" | "24h" | "7d">("24h");
  const [activeMetricTab, setActiveMetricTab] = useState<"compute" | "memory" | "latency">("compute");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [hoveredPointIdx, setHoveredPointIdx] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const lastS2StatusRef = useRef<string | null>(null);

  const loadMetrics = async (isManual = false) => {
    if (isManual) setIsRefreshing(true);
    setError(null);
    try {
      const live = await api.getServersLive();
      setLiveData(live);
      const nextS2Status = live?.server_2?.status ?? null;
      if (
        typeof window !== "undefined" &&
        nextS2Status &&
        (isManual || lastS2StatusRef.current !== nextS2Status)
      ) {
        lastS2StatusRef.current = nextS2Status;
        window.dispatchEvent(
          new CustomEvent("llm-status-change", {
            detail: {
              is_healthy: nextS2Status === "ONLINE",
              model: live.server_2?.details?.model_name,
            },
          })
        );
      }
    } catch (err: any) {
      console.warn("Failed to load live server telemetry:", err);
    }

    try {
      const hist = await api.getServersHistory(windowRange);
      setHistoryData(hist);
    } catch (err: any) {
      console.warn("Failed to load historical telemetry:", err);
      setError(err.message || "Failed to load server historical telemetry");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, [windowRange]);

  useEffect(() => {
    if (!autoRefresh) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    timerRef.current = setInterval(() => {
      loadMetrics(false);
    }, 15000); // 15-second polling interval

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [autoRefresh, windowRange]);

  const s1 = liveData?.server_1;
  const s2 = liveData?.server_2;

  const formatLocalTime = (isoString?: string) => {
    if (!isoString) return "";
    try {
      const normalized =
        isoString.endsWith("Z") || isoString.includes("+")
          ? isoString
          : `${isoString}Z`;
      const d = new Date(normalized);
      if (isNaN(d.getTime())) return isoString;

      if (windowRange === "7d") {
        return (
          d.toLocaleDateString([], { month: "short", day: "numeric" }) +
          " " +
          d.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          })
        );
      }
      return d.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    } catch {
      return isoString;
    }
  };

  // Build SVG Path helper for chart
  const renderAreaChart = () => {
    if (!historyData) return null;
    const s1Series = historyData.server_1_series;
    const s2Series = historyData.server_2_series;
    const maxLen = Math.max(s1Series.length, s2Series.length);
    if (maxLen < 2) return null;

    const width = 800;
    const height = 220;
    const paddingX = 40;
    const paddingY = 25;
    const chartW = width - paddingX * 2;
    const chartH = height - paddingY * 2;

    // Determine max Y scale depending on selected metric
    let maxY = 100;
    if (activeMetricTab === "latency") {
      const maxLat = Math.max(...s2Series.map((p) => p.latency_ms || 0), 50);
      maxY = Math.ceil((maxLat * 1.2) / 10) * 10;
    }

    const getX = (idx: number, total: number) => {
      if (total <= 1) return paddingX;
      return paddingX + (idx / (total - 1)) * chartW;
    };

    const getY = (val: number) => {
      const clamped = Math.max(0, Math.min(val, maxY));
      return height - paddingY - (clamped / maxY) * chartH;
    };

    // Series 1 Points
    const s1Points = s1Series.map((pt, i) => {
      let val = 0;
      if (activeMetricTab === "compute") val = pt.cpu_percent;
      else if (activeMetricTab === "memory") val = pt.memory_percent;
      else if (activeMetricTab === "latency") val = pt.latency_ms || 1.2;
      return { x: getX(i, s1Series.length), y: getY(val), val, raw: pt };
    });

    // Series 2 Points
    const s2Points = s2Series.map((pt, i) => {
      let val = 0;
      if (activeMetricTab === "compute") val = pt.gpu_percent ?? pt.cpu_percent;
      else if (activeMetricTab === "memory") val = pt.gpu_memory_percent ?? pt.memory_percent;
      else if (activeMetricTab === "latency") val = pt.latency_ms || 20.0;
      return { x: getX(i, s2Series.length), y: getY(val), val, raw: pt };
    });

    const createPath = (pts: { x: number; y: number }[]) => {
      if (pts.length === 0) return "";
      return pts.reduce((acc, pt, i) => `${acc} ${i === 0 ? "M" : "L"} ${pt.x} ${pt.y}`, "");
    };

    const createArea = (pts: { x: number; y: number }[]) => {
      if (pts.length === 0) return "";
      const line = createPath(pts);
      const bottom = height - paddingY;
      return `${line} L ${pts[pts.length - 1].x} ${bottom} L ${pts[0].x} ${bottom} Z`;
    };

    return (
      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-48 sm:h-56 select-none"
          preserveAspectRatio="none"
        >
          <defs>
            {/* Server 1 Gradient (Cyan) */}
            <linearGradient id="s1Grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>

            {/* Server 2 Gradient (Purple/Indigo) */}
            <linearGradient id="s2Grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#a855f7" stopOpacity="0.35" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map((pct) => {
            const y = height - paddingY - (pct / 100) * chartH;
            const labelVal = activeMetricTab === "latency" ? Math.round((pct / 100) * maxY) : pct;
            return (
              <g key={pct}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="#334155"
                  strokeDasharray="3 3"
                  strokeOpacity="0.4"
                />
                <text
                  x={paddingX - 8}
                  y={y + 3}
                  textAnchor="end"
                  fontSize="9"
                  fill="#64748b"
                  fontFamily="monospace"
                >
                  {labelVal}
                  {activeMetricTab === "latency" ? "ms" : "%"}
                </text>
              </g>
            );
          })}

          {/* Series 1 Fill & Line (Cyan) */}
          <path d={createArea(s1Points)} fill="url(#s1Grad)" />
          <path
            d={createPath(s1Points)}
            fill="none"
            stroke="#06b6d4"
            strokeWidth="2"
            strokeLinecap="round"
          />

          {/* Series 2 Fill & Line (Purple) */}
          <path d={createArea(s2Points)} fill="url(#s2Grad)" />
          <path
            d={createPath(s2Points)}
            fill="none"
            stroke="#a855f7"
            strokeWidth="2"
            strokeLinecap="round"
          />

          {/* Hover guideline and dots */}
          {hoveredPointIdx !== null && s1Points[hoveredPointIdx] && (
            <g>
              <line
                x1={s1Points[hoveredPointIdx].x}
                y1={paddingY}
                x2={s1Points[hoveredPointIdx].x}
                y2={height - paddingY}
                stroke="#94a3b8"
                strokeWidth="1"
                strokeDasharray="2 2"
              />
              <circle
                cx={s1Points[hoveredPointIdx].x}
                cy={s1Points[hoveredPointIdx].y}
                r="4"
                fill="#06b6d4"
                stroke="#0f172a"
                strokeWidth="2"
              />
              {s2Points[hoveredPointIdx] && (
                <circle
                  cx={s2Points[hoveredPointIdx].x}
                  cy={s2Points[hoveredPointIdx].y}
                  r="4"
                  fill="#a855f7"
                  stroke="#0f172a"
                  strokeWidth="2"
                />
              )}
            </g>
          )}

          {/* Transparent interactive hover overlay segments */}
          {s1Points.map((pt, i) => (
            <rect
              key={i}
              x={pt.x - chartW / (s1Points.length * 2)}
              y={paddingY}
              width={chartW / s1Points.length}
              height={chartH}
              fill="transparent"
              className="cursor-pointer"
              onMouseEnter={() => setHoveredPointIdx(i)}
              onMouseLeave={() => setHoveredPointIdx(null)}
            />
          ))}

          {/* X Axis Time Labels */}
          {s1Series.map((pt, i) => {
            // Show every Nth label depending on count
            const step = Math.max(1, Math.floor(s1Series.length / 6));
            if (i % step !== 0 && i !== s1Series.length - 1) return null;
            return (
              <text
                key={i}
                x={getX(i, s1Series.length)}
                y={height - 6}
                textAnchor="middle"
                fontSize="9"
                fill="#64748b"
                fontFamily="monospace"
              >
                {formatLocalTime(pt.timestamp)}
              </text>
            );
          })}
        </svg>

        {/* Hover Floating Tooltip */}
        {hoveredPointIdx !== null && s1Points[hoveredPointIdx] && (
          <div
            className="absolute top-2 pointer-events-none rounded-md bg-slate-900/95 border border-slate-700 p-2 shadow-xl text-xs font-mono backdrop-blur-sm z-20 space-y-1"
            style={{
              left: `${Math.min(
                Math.max(15, (s1Points[hoveredPointIdx].x / width) * 100),
                80
              )}%`,
            }}
          >
            <div className="text-[10px] text-slate-400 border-b border-slate-800 pb-1">
              Time: {formatLocalTime(s1Points[hoveredPointIdx].raw.timestamp)}
            </div>
            <div className="flex items-center gap-2 text-cyan-300">
              <span className="h-2 w-2 rounded-full bg-cyan-400"></span>
              <span>Server 1: </span>
              <strong>
                {s1Points[hoveredPointIdx].val}
                {activeMetricTab === "latency" ? " ms" : "%"}
              </strong>
            </div>
            {s2Points[hoveredPointIdx] && (
              <div className="flex items-center gap-2 text-purple-300">
                <span className="h-2 w-2 rounded-full bg-purple-400"></span>
                <span>Server 2: </span>
                <strong>
                  {s2Points[hoveredPointIdx].val}
                  {activeMetricTab === "latency" ? " ms" : "%"}
                </strong>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-950 p-3.5 space-y-3.5 shadow-sm">
      {/* Header Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2.5">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-indigo-950/60 text-indigo-400 border border-indigo-800/60">
            <Radio className="h-4 w-4 animate-pulse" />
          </div>
          <div>
            <h2 className="text-xs sm:text-sm font-bold text-slate-100 flex items-center gap-2">
              Dual-Server Infrastructure & Telemetry Monitor
              <span className="inline-flex items-center gap-1 rounded bg-emerald-950/60 border border-emerald-800/80 px-1.5 py-0.2 text-[9px] font-semibold text-emerald-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                LIVE CLUSTER
              </span>
            </h2>
            <p className="text-[10px] text-slate-400">
              Real-time resource utilization & historical analytics across Server 1 (Platform) & Server 2 (vLLM AI)
            </p>
          </div>
        </div>

        {/* Global Controls */}
        <div className="flex items-center gap-2">
          {/* Auto Refresh Toggle */}
          <button
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={`flex items-center gap-1 rounded px-2 py-0.5 text-[10px] font-mono border transition-all ${
              autoRefresh
                ? "bg-cyan-950/50 text-cyan-300 border-cyan-800/80"
                : "bg-slate-900 text-slate-500 border-slate-800 hover:text-slate-300"
            }`}
            title="Auto refresh every 15 seconds"
          >
            <Clock className="h-2.5 w-2.5" />
            {autoRefresh ? "Auto (15s)" : "Paused"}
          </button>

          {/* Refresh Button */}
          <button
            onClick={() => loadMetrics(true)}
            disabled={isRefreshing}
            className="flex items-center gap-1 rounded border border-slate-800 bg-slate-900 hover:bg-slate-800 px-2 py-0.5 text-[10px] text-slate-300 font-medium transition-colors"
          >
            <RefreshCw className={`h-2.5 w-2.5 ${isRefreshing ? "animate-spin text-cyan-400" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-amber-800/80 bg-amber-950/40 p-2 text-xs text-amber-300 flex items-center gap-2">
          <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Dual Server Live Utilization Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* ================= SERVER 1 (Platform Host) ================= */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
            <div className="flex items-center gap-2">
              <Server className="h-4 w-4 text-cyan-400" />
              <div>
                <span className="text-xs font-bold text-slate-100">Server 1 (Platform Core)</span>
                <span className="text-[10px] text-slate-500 block font-mono">App / SIEM Ingestion / DB</span>
              </div>
            </div>
            <span
              className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-semibold border ${
                s1?.status === "ONLINE"
                  ? "bg-emerald-950/70 text-emerald-300 border-emerald-800"
                  : "bg-rose-950/70 text-rose-300 border-rose-800"
              }`}
            >
              ● {s1?.status || "CHECKING"}
            </span>
          </div>

          {/* Progress Bars */}
          <div className="space-y-2 text-xs">
            {/* CPU */}
            <div className="space-y-0.5">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-slate-400 flex items-center gap-1">
                  <Cpu className="h-3 w-3 text-cyan-400" /> CPU Utilization
                </span>
                <span className="text-slate-200 font-bold">{s1?.cpu_percent ?? 0}%</span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className={`h-full transition-all duration-500 ${
                    (s1?.cpu_percent || 0) > 80
                      ? "bg-rose-500"
                      : (s1?.cpu_percent || 0) > 50
                      ? "bg-amber-500"
                      : "bg-cyan-400"
                  }`}
                  style={{ width: `${Math.min(100, Math.max(3, s1?.cpu_percent || 0))}%` }}
                />
              </div>
            </div>

            {/* RAM */}
            <div className="space-y-0.5">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-slate-400 flex items-center gap-1">
                  <Activity className="h-3 w-3 text-blue-400" /> Memory (RAM)
                </span>
                <span className="text-slate-200 font-bold">
                  {s1?.memory_percent ?? 0}%{" "}
                  <span className="text-[10px] text-slate-400 font-normal">
                    ({s1?.memory_used_gb ?? 0} / {s1?.memory_total_gb ?? 0} GB)
                  </span>
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(3, s1?.memory_percent || 0))}%` }}
                />
              </div>
            </div>

            {/* Storage */}
            <div className="space-y-0.5">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-slate-400 flex items-center gap-1">
                  <HardDrive className="h-3 w-3 text-indigo-400" /> Disk Storage
                </span>
                <span className="text-slate-200 font-bold">
                  {s1?.disk_percent ?? 0}%{" "}
                  <span className="text-[10px] text-slate-400 font-normal">
                    ({s1?.disk_used_gb ?? 0} / {s1?.disk_total_gb ?? 0} GB)
                  </span>
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-indigo-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, Math.max(3, s1?.disk_percent || 0))}%` }}
                />
              </div>
            </div>
          </div>

          {/* Footer Metadata */}
          <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-800/80">
            <span>Uptime: <strong className="text-slate-300">{s1?.details?.uptime_formatted || "Active"}</strong></span>
            <span>Load Avg: <strong className="text-slate-300">{s1?.details?.load_avg?.join(", ") || "0.20, 0.25"}</strong></span>
          </div>
        </div>

        {/* ================= SERVER 2 (GPU Inference Engine) ================= */}
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 space-y-2.5">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-purple-400" />
              <div>
                <span className="text-xs font-bold text-slate-100">Server 2 (vLLM AI Engine)</span>
                <span className="text-[10px] text-purple-400 block font-mono">
                  {s2?.details?.model_name || "Qwen/Qwen2.5-7B-Instruct-AWQ"}
                </span>
              </div>
            </div>
            <span
              className={`px-1.5 py-0.2 rounded text-[9px] font-mono font-semibold border ${
                s2?.status === "ONLINE"
                  ? "bg-purple-950/70 text-purple-300 border-purple-800"
                  : "bg-rose-950/70 text-rose-300 border-rose-800"
              }`}
            >
              ● {s2?.status === "ONLINE" ? "GPU LIVE" : s2?.status || "OFFLINE"}
            </span>
          </div>

          {/* Progress Bars */}
          <div className="space-y-2 text-xs">
            {/* GPU Compute Load */}
            <div className="space-y-0.5">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-slate-400 flex items-center gap-1">
                  <Gauge className="h-3 w-3 text-purple-400" /> GPU Compute Load
                </span>
                <span className="text-purple-300 font-bold">
                  {s2?.gpu_percent != null ? `${s2.gpu_percent}%` : "Unavailable"}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-purple-500 transition-all duration-500"
                  style={{ width: `${s2?.gpu_percent != null ? Math.min(100, Math.max(3, s2.gpu_percent)) : 0}%` }}
                />
              </div>
            </div>

            {/* GPU VRAM Allocation */}
            <div className="space-y-0.5">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-slate-400 flex items-center gap-1">
                  <Layers className="h-3 w-3 text-pink-400" /> VRAM & KV Cache
                </span>
                <span className="text-pink-300 font-bold">
                  {s2?.gpu_memory_percent != null ? (
                    <>
                      {s2.gpu_memory_percent}%{" "}
                      <span className="text-[10px] text-slate-400 font-normal">
                        ({s2?.gpu_memory_used_gb ?? 0} / {s2?.gpu_memory_total_gb ?? 24} GB)
                      </span>
                    </>
                  ) : (
                    "Unavailable"
                  )}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-pink-500 transition-all duration-500"
                  style={{ width: `${s2?.gpu_memory_percent != null ? Math.min(100, Math.max(3, s2.gpu_memory_percent)) : 0}%` }}
                />
              </div>
            </div>

            {/* Inference Latency */}
            <div className="space-y-0.5">
              <div className="flex justify-between text-[11px] font-mono">
                <span className="text-slate-400 flex items-center gap-1">
                  <Clock className="h-3 w-3 text-emerald-400" /> API Latency & Queue
                </span>
                <span className="text-emerald-300 font-bold">
                  {s2?.latency_ms != null ? `${s2.latency_ms} ms` : "N/A"}{" "}
                  {s2?.active_requests != null && (
                    <span className="text-[10px] text-slate-400 font-normal">
                      ({s2.active_requests} active reqs)
                    </span>
                  )}
                </span>
              </div>
              <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-500"
                  style={{ width: `${s2?.latency_ms != null ? Math.min(100, Math.max(3, (s2.latency_ms / 200) * 100)) : 0}%` }}
                />
              </div>
            </div>
          </div>

          {/* Footer Metadata */}
          <div className="flex items-center justify-between text-[10px] font-mono text-slate-400 pt-1 border-t border-slate-800/80">
            <span className="flex items-center gap-1">
              <Thermometer className="h-3 w-3 text-amber-400" />
              Temp: <strong className="text-slate-300">{s2?.gpu_temp_c != null ? `${s2.gpu_temp_c}°C` : "N/A"}</strong>
            </span>
            <span>
              Metrics:{" "}
              <strong className={s2?.details?.metrics_available ? "text-emerald-400" : "text-slate-400"}>
                {s2?.details?.metrics_available ? "Prometheus Live" : "Metrics Unavailable"}
              </strong>
            </span>
          </div>
        </div>
      </div>

      {/* ================= HISTORICAL UTILIZATION TRENDS ================= */}
      <div className="pt-2 border-t border-slate-800/80 space-y-2.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-3.5 w-3.5 text-cyan-400" />
            <span className="text-xs font-bold text-slate-200">Historical Telemetry Timeline</span>
            {/* Metric Mode Filter */}
            <div className="flex rounded-md bg-slate-900 border border-slate-800 p-0.5 text-[10px] font-mono">
              <button
                onClick={() => setActiveMetricTab("compute")}
                className={`px-2 py-0.5 rounded transition-all ${
                  activeMetricTab === "compute"
                    ? "bg-slate-800 text-white font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                CPU / GPU Load
              </button>
              <button
                onClick={() => setActiveMetricTab("memory")}
                className={`px-2 py-0.5 rounded transition-all ${
                  activeMetricTab === "memory"
                    ? "bg-slate-800 text-white font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                RAM / VRAM
              </button>
              <button
                onClick={() => setActiveMetricTab("latency")}
                className={`px-2 py-0.5 rounded transition-all ${
                  activeMetricTab === "latency"
                    ? "bg-slate-800 text-white font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Inference Latency
              </button>
            </div>
          </div>

          {/* Time Window Pills */}
          <div className="flex items-center gap-1 text-[10px] font-mono">
            {(["1h", "6h", "24h", "7d"] as const).map((w) => (
              <button
                key={w}
                onClick={() => setWindowRange(w)}
                className={`px-2 py-0.5 rounded border transition-all ${
                  windowRange === w
                    ? "bg-cyan-950 text-cyan-300 border-cyan-700 font-bold"
                    : "bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200"
                }`}
              >
                {w.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-[10px] font-mono text-slate-400">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-cyan-400"></span>
            <span>Server 1 ({activeMetricTab === "compute" ? "CPU %" : activeMetricTab === "memory" ? "RAM %" : "Platform Ping"})</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-purple-400"></span>
            <span>Server 2 ({activeMetricTab === "compute" ? "GPU Compute %" : activeMetricTab === "memory" ? "VRAM %" : "vLLM Latency ms"})</span>
          </div>
        </div>

        {/* The SVG Chart */}
        <div className="rounded-lg border border-slate-800/80 bg-slate-900/40 p-2">
          {isLoading && !historyData ? (
            <div className="flex h-48 items-center justify-center text-xs font-mono text-slate-500">
              <RefreshCw className="h-4 w-4 animate-spin text-cyan-400 mr-2" />
              Loading Historical Telemetry Series...
            </div>
          ) : (
            renderAreaChart()
          )}
        </div>

        {/* Historical Aggregates Badges */}
        {historyData?.stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-[11px] font-mono">
            <div className="rounded border border-slate-800/80 bg-slate-900/60 p-1.5">
              <span className="text-slate-400 text-[10px] block">Server 1 Avg CPU</span>
              <strong className="text-cyan-300 text-xs">{historyData.stats.server_1.cpu.avg}%</strong>{" "}
              <span className="text-[10px] text-slate-500">(Peak: {historyData.stats.server_1.cpu.max}%)</span>
            </div>

            <div className="rounded border border-slate-800/80 bg-slate-900/60 p-1.5">
              <span className="text-slate-400 text-[10px] block">Server 1 Avg RAM</span>
              <strong className="text-blue-300 text-xs">{historyData.stats.server_1.memory.avg}%</strong>{" "}
              <span className="text-[10px] text-slate-500">(Peak: {historyData.stats.server_1.memory.max}%)</span>
            </div>

            <div className="rounded border border-slate-800/80 bg-slate-900/60 p-1.5">
              <span className="text-slate-400 text-[10px] block">Server 2 Avg GPU</span>
              <strong className="text-purple-300 text-xs">{historyData.stats.server_2.gpu.avg}%</strong>{" "}
              <span className="text-[10px] text-slate-500">(Peak: {historyData.stats.server_2.gpu.max}%)</span>
            </div>

            <div className="rounded border border-slate-800/80 bg-slate-900/60 p-1.5">
              <span className="text-slate-400 text-[10px] block">Server 2 Avg Latency</span>
              <strong className="text-emerald-300 text-xs">{historyData.stats.server_2.latency.avg} ms</strong>{" "}
              <span className="text-[10px] text-slate-500">(Min: {historyData.stats.server_2.latency.min} ms)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

