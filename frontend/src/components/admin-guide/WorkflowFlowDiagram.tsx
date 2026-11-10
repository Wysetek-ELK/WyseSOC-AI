"use client";

import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  Play,
  Pause,
  RotateCcw,
  SkipBack,
  SkipForward,
  Maximize2,
  Minimize2,
  Scan,
  ZoomIn,
  ZoomOut,
  EyeOff,
  ExternalLink,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  ArrowRight,
  Layers,
  ListChecks,
  Network,
  Settings2,
  ShieldAlert,
} from "lucide-react";
import type {
  NodeAccent,
  SwimlaneBoxSpec,
  WorkflowEdgeSpec,
  WorkflowStepSpec,
} from "@/data/admin-guide/types";
import { usePrefersReducedMotion } from "./usePrefersReducedMotion";

type SpeedOption = 0.5 | 1 | 1.5 | 2;
type HandleSide = "left" | "right" | "top" | "bottom";

const SPEED_INTERVAL_MS: Record<SpeedOption, number> = {
  0.5: 3200,
  1: 1800,
  1.5: 1200,
  2: 850,
};

const NODE_WIDTH = 205;
const NODE_HEIGHT = 82;
const NODE_OUTCOME_HEIGHT = 96;

const ACCENT_STYLES: Record<
  NodeAccent,
  {
    border: string;
    activeBorder: string;
    badgeBg: string;
    stroke: string;
    packet: string;
    dot: string;
  }
> = {
  cyan: {
    border: "border-cyan-800/70",
    activeBorder: "border-cyan-400 ring-2 ring-cyan-400/50 shadow-lg shadow-cyan-500/20",
    badgeBg: "bg-cyan-950/90 text-cyan-300 border-cyan-700/70",
    stroke: "#22d3ee",
    packet: "#67e8f9",
    dot: "bg-cyan-400",
  },
  sky: {
    border: "border-sky-800/70",
    activeBorder: "border-sky-400 ring-2 ring-sky-400/50 shadow-lg shadow-sky-500/20",
    badgeBg: "bg-sky-950/90 text-sky-300 border-sky-700/70",
    stroke: "#38bdf8",
    packet: "#7dd3fc",
    dot: "bg-sky-400",
  },
  indigo: {
    border: "border-indigo-800/70",
    activeBorder: "border-indigo-400 ring-2 ring-indigo-400/50 shadow-lg shadow-indigo-500/20",
    badgeBg: "bg-indigo-950/90 text-indigo-300 border-indigo-700/70",
    stroke: "#818cf8",
    packet: "#a5b4fc",
    dot: "bg-indigo-400",
  },
  emerald: {
    border: "border-emerald-800/70",
    activeBorder: "border-emerald-400 ring-2 ring-emerald-400/50 shadow-lg shadow-emerald-500/20",
    badgeBg: "bg-emerald-950/90 text-emerald-300 border-emerald-700/70",
    stroke: "#34d399",
    packet: "#6ee7b7",
    dot: "bg-emerald-400",
  },
  amber: {
    border: "border-amber-800/70",
    activeBorder: "border-amber-400 ring-2 ring-amber-400/50 shadow-lg shadow-amber-500/20",
    badgeBg: "bg-amber-950/90 text-amber-300 border-amber-700/70",
    stroke: "#fbbf24",
    packet: "#fde68a",
    dot: "bg-amber-400",
  },
  rose: {
    border: "border-rose-800/70",
    activeBorder: "border-rose-400 ring-2 ring-rose-400/50 shadow-lg shadow-rose-500/20",
    badgeBg: "bg-rose-950/90 text-rose-300 border-rose-700/70",
    stroke: "#fb7185",
    packet: "#fda4af",
    dot: "bg-rose-400",
  },
  slate: {
    border: "border-slate-700",
    activeBorder: "border-slate-400 ring-2 ring-slate-400/50 shadow-lg shadow-slate-500/20",
    badgeBg: "bg-slate-900 text-slate-300 border-slate-700",
    stroke: "#94a3b8",
    packet: "#cbd5e1",
    dot: "bg-slate-400",
  },
};

function parseSide(handleId: string | undefined, fallback: HandleSide): HandleSide {
  if (!handleId) return fallback;
  if (handleId.startsWith("left")) return "left";
  if (handleId.startsWith("right")) return "right";
  if (handleId.startsWith("top")) return "top";
  if (handleId.startsWith("bottom")) return "bottom";
  return fallback;
}

function getHandleAnchor(
  step: WorkflowStepSpec,
  side: HandleSide
): { x: number; y: number } {
  const h = step.outcomeBadge ? NODE_OUTCOME_HEIGHT : NODE_HEIGHT;
  switch (side) {
    case "left":
      return { x: step.position.x, y: step.position.y + h / 2 };
    case "right":
      return { x: step.position.x + NODE_WIDTH, y: step.position.y + h / 2 };
    case "top":
      return { x: step.position.x + NODE_WIDTH / 2, y: step.position.y };
    case "bottom":
      return { x: step.position.x + NODE_WIDTH / 2, y: step.position.y + h };
  }
}

function buildOrthogonalPath(
  sx: number,
  sy: number,
  sSide: HandleSide,
  tx: number,
  ty: number,
  tSide: HandleSide
): { pathD: string; labelX: number; labelY: number } {
  const stub = 22;
  const dx = sSide === "left" ? -stub : sSide === "right" ? stub : 0;
  const dy = sSide === "top" ? -stub : sSide === "bottom" ? stub : 0;
  const tdx = tSide === "left" ? -stub : tSide === "right" ? stub : 0;
  const tdy = tSide === "top" ? -stub : tSide === "bottom" ? stub : 0;

  const p1x = sx + dx;
  const p1y = sy + dy;
  const p2x = tx + tdx;
  const p2y = ty + tdy;

  const pts: Array<[number, number]> = [[sx, sy], [p1x, p1y]];

  const sVert = sSide === "top" || sSide === "bottom";
  const tVert = tSide === "top" || tSide === "bottom";

  if (sVert && tVert) {
    if (sSide === "bottom" && tSide === "bottom") {
      const belowY = Math.max(sy, ty) + 34;
      pts.push([p1x, belowY], [p2x, belowY]);
    } else if (Math.abs(p1x - p2x) >= 2) {
      const midY = (p1y + p2y) / 2;
      pts.push([p1x, midY], [p2x, midY]);
    }
  } else if (!sVert && !tVert) {
    if (Math.abs(p1y - p2y) >= 2) {
      const midX = (p1x + p2x) / 2;
      pts.push([midX, p1y], [midX, p2y]);
    }
  } else if (sVert && !tVert) {
    pts.push([p1x, p2y]);
  } else {
    pts.push([p2x, p1y]);
  }

  pts.push([p2x, p2y], [tx, ty]);

  const clean: Array<[number, number]> = [];
  for (const pt of pts) {
    const prev = clean[clean.length - 1];
    if (!prev || Math.abs(prev[0] - pt[0]) > 0.5 || Math.abs(prev[1] - pt[1]) > 0.5) {
      clean.push(pt);
    }
  }

  const pathD = clean
    .map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`)
    .join(" ");

  const midIdx = Math.floor(clean.length / 2);
  const a = clean[Math.max(0, midIdx - 1)];
  const b = clean[midIdx] || a;
  const labelX = (a[0] + b[0]) / 2;
  const labelY = (a[1] + b[1]) / 2;

  return { pathD, labelX, labelY };
}

interface WorkflowFlowDiagramProps {
  title: string;
  subtitle: string;
  steps: WorkflowStepSpec[];
  edges: WorkflowEdgeSpec[];
  swimlanes: SwimlaneBoxSpec[];
  initialStepId?: string;
  jumpNonce?: number;
}

export function WorkflowFlowDiagram({
  title,
  subtitle,
  steps,
  edges,
  swimlanes,
  initialStepId,
  jumpNonce = 0,
}: WorkflowFlowDiagramProps) {
  const markerPrefix = useId().replace(/:/g, "");
  const viewportRef = useRef<HTMLDivElement>(null);
  const scrubberRef = useRef<HTMLDivElement>(null);

  const initialIdx = useMemo(() => {
    if (!initialStepId) return 0;
    const found = steps.findIndex((s) => s.id === initialStepId);
    return found >= 0 ? found : 0;
  }, [initialStepId, steps]);

  const [activeIndex, setActiveIndex] = useState<number>(initialIdx);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [prevJumpTarget, setPrevJumpTarget] = useState<string>(
    `${initialStepId || ""}:${jumpNonce}`
  );
  const currentJumpTarget = `${initialStepId || ""}:${jumpNonce}`;
  if (currentJumpTarget !== prevJumpTarget) {
    setPrevJumpTarget(currentJumpTarget);
    if (initialStepId) {
      const targetIdx = steps.findIndex((s) => s.id === initialStepId);
      if (targetIdx >= 0) {
        setActiveIndex(targetIdx);
        setIsPlaying(false);
      }
    }
  }
  const [speed, setSpeed] = useState<SpeedOption>(1);
  const osReducedMotion = usePrefersReducedMotion();
  const [manualReducedMotion, setManualReducedMotion] = useState<boolean | null>(null);
  const reducedMotion = manualReducedMotion ?? osReducedMotion;
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [mobileListMode, setMobileListMode] = useState<boolean>(false);

  const canvasBounds = useMemo(() => {
    const maxLaneX = swimlanes.reduce((m, l) => Math.max(m, l.position.x + l.width), 0);
    const maxLaneY = swimlanes.reduce((m, l) => Math.max(m, l.position.y + l.height), 0);
    const maxStepX = steps.reduce((m, s) => Math.max(m, s.position.x + NODE_WIDTH), 0);
    const maxStepY = steps.reduce((m, s) => Math.max(m, s.position.y + NODE_OUTCOME_HEIGHT), 0);
    return {
      width: Math.max(maxLaneX, maxStepX) + 24,
      height: Math.max(maxLaneY, maxStepY) + 40,
    };
  }, [swimlanes, steps]);

  const [viewportSize, setViewportSize] = useState<{ w: number; h: number }>({
    w: 920,
    h: 560,
  });
  const [manualTransform, setManualTransform] = useState<{
    zoom: number;
    panX: number;
    panY: number;
  } | null>(null);

  const dragStateRef = useRef<{
    dragging: boolean;
    startX: number;
    startY: number;
    origPanX: number;
    origPanY: number;
  } | null>(null);

  useEffect(() => {
    const el = viewportRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const obs = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect && rect.width > 50 && rect.height > 50) {
        setViewportSize({ w: rect.width, h: rect.height });
      }
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [mobileListMode, isFullscreen]);

  const fittedTransform = useMemo(() => {
    const pad = 28;
    const scaleX = (viewportSize.w - pad) / canvasBounds.width;
    const scaleY = (viewportSize.h - pad) / canvasBounds.height;
    const zoom = Math.max(0.35, Math.min(scaleX, scaleY, 1.05));
    const panX = (viewportSize.w - canvasBounds.width * zoom) / 2;
    const panY = (viewportSize.h - canvasBounds.height * zoom) / 2;
    return { zoom, panX, panY };
  }, [viewportSize, canvasBounds]);

  const activeTransform = manualTransform || fittedTransform;

  useEffect(() => {
    if (!isFullscreen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullscreen]);

  useEffect(() => {
    const strip = scrubberRef.current;
    if (!strip) return;
    const btn = strip.querySelector<HTMLButtonElement>(`[data-scrubber-idx="${activeIndex}"]`);
    if (!btn) return;
    const targetLeft = btn.offsetLeft - strip.clientWidth / 2 + btn.clientWidth / 2;
    strip.scrollTo({
      left: Math.max(0, targetLeft),
      behavior: reducedMotion ? "auto" : "smooth",
    });
  }, [activeIndex, reducedMotion]);

  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % steps.length);
    }, SPEED_INTERVAL_MS[speed]);
    return () => clearInterval(timer);
  }, [isPlaying, speed, steps.length]);

  const activeStep = steps[activeIndex] || steps[0];

  const stepMap = useMemo(() => {
    const map = new Map<string, WorkflowStepSpec>();
    for (const s of steps) map.set(s.id, s);
    return map;
  }, [steps]);

  const computedEdges = useMemo(() => {
    return edges
      .map((edge) => {
        const src = stepMap.get(edge.source);
        const dst = stepMap.get(edge.target);
        if (!src || !dst) return null;
        const sSide = parseSide(edge.sourceHandle, "right");
        const tSide = parseSide(edge.targetHandle, "left");
        const a = getHandleAnchor(src, sSide);
        const b = getHandleAnchor(dst, tSide);
        const { pathD, labelX, labelY } = buildOrthogonalPath(
          a.x,
          a.y,
          sSide,
          b.x,
          b.y,
          tSide
        );
        const isActiveEdge =
          edge.source === activeStep.id || edge.target === activeStep.id;
        return {
          edge,
          pathD,
          labelX,
          labelY,
          isActiveEdge,
        };
      })
      .filter((x): x is NonNullable<typeof x> => x !== null);
  }, [edges, stepMap, activeStep.id]);

  const handleSelectStepById = useCallback(
    (stepId: string) => {
      const idx = steps.findIndex((s) => s.id === stepId);
      if (idx >= 0) {
        setActiveIndex(idx);
        setIsPlaying(false);
      }
    },
    [steps]
  );

  const handleFitView = () => setManualTransform(null);

  const handleZoomBy = (factor: number) => {
    const cur = manualTransform || fittedTransform;
    const nextZoom = Math.max(0.35, Math.min(1.85, cur.zoom * factor));
    const cx = viewportSize.w / 2;
    const cy = viewportSize.h / 2;
    const ratio = nextZoom / cur.zoom;
    setManualTransform({
      zoom: nextZoom,
      panX: cx - (cx - cur.panX) * ratio,
      panY: cy - (cy - cur.panY) * ratio,
    });
  };

  const handlePointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    const target = e.target as HTMLElement | null;
    if (target?.closest("button, a, [data-flow-node], [data-no-pan]")) return;
    const cur = manualTransform || fittedTransform;
    dragStateRef.current = {
      dragging: true,
      startX: e.clientX,
      startY: e.clientY,
      origPanX: cur.panX,
      origPanY: cur.panY,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const d = dragStateRef.current;
    if (!d?.dragging) return;
    const cur = manualTransform || fittedTransform;
    setManualTransform({
      zoom: cur.zoom,
      panX: d.origPanX + (e.clientX - d.startX),
      panY: d.origPanY + (e.clientY - d.startY),
    });
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLDivElement>) => {
    if (dragStateRef.current) {
      dragStateRef.current = null;
      try {
        e.currentTarget.releasePointerCapture(e.pointerId);
      } catch {
        // Ignore if not captured
      }
    }
  };

  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    handleZoomBy(e.deltaY < 0 ? 1.12 : 0.89);
  };

  const handleRestart = () => {
    setActiveIndex(0);
    setIsPlaying(true);
  };

  const handlePrev = () => {
    setIsPlaying(false);
    setActiveIndex((prev) => (prev - 1 + steps.length) % steps.length);
  };

  const handleNext = () => {
    setIsPlaying(false);
    setActiveIndex((prev) => (prev + 1) % steps.length);
  };

  const packetDur = `${(1.4 / speed).toFixed(2)}s`;

  return (
    <div
      className={`${reducedMotion ? "guide-reduced-motion" : ""} ${isFullscreen
          ? "fixed inset-0 z-50 bg-slate-950 p-3 sm:p-4 flex flex-col overflow-hidden"
          : "rounded-xl border border-slate-800 bg-slate-950/90 overflow-hidden"
        }`}
    >
      {/* Toolbar Header */}
      <div className="border-b border-slate-800 bg-slate-900/70 px-3 py-2.5 flex flex-wrap items-center justify-between gap-2.5">
        <div>
          <div className="flex items-center gap-2">
            <Network className="h-4 w-4 text-cyan-400 shrink-0" />
            <h2 className="text-sm font-bold text-slate-100">{title}</h2>
            <span className="shrink-0 whitespace-nowrap rounded-full bg-cyan-950/80 border border-cyan-800/60 px-2 py-0.5 text-[10px] font-mono text-cyan-300">
              Step {activeIndex + 1} / {steps.length}
            </span>
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>
        </div>

        {/* Playback & Accessibility Controls */}
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            type="button"
            onClick={() => setIsPlaying((p) => !p)}
            className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold border transition-colors ${isPlaying
                ? "bg-amber-950/70 text-amber-300 border-amber-700/70 hover:bg-amber-900/70"
                : "bg-cyan-600/20 text-cyan-300 border-cyan-500/50 hover:bg-cyan-600/30"
              }`}
            aria-label={isPlaying ? "Pause workflow animation" : "Play workflow animation"}
          >
            {isPlaying ? <Pause className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            <span>{isPlaying ? "Pause" : "Play"}</span>
          </button>

          <button
            type="button"
            onClick={handlePrev}
            className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
            title="Previous Step"
            aria-label="Previous Step"
          >
            <SkipBack className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Prev</span>
          </button>

          <button
            type="button"
            onClick={handleNext}
            className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
            title="Next Step"
            aria-label="Next Step"
          >
            <span className="hidden sm:inline">Next</span>
            <SkipForward className="h-3.5 w-3.5" />
          </button>

          <button
            type="button"
            onClick={handleRestart}
            className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
            title="Restart Animation"
            aria-label="Restart Animation"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Restart</span>
          </button>

          {/* Speed Selector */}
          <div className="flex items-center rounded-md border border-slate-700 bg-slate-900 p-0.5 text-[10px] font-mono">
            {([0.5, 1, 1.5, 2] as SpeedOption[]).map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => setSpeed(opt)}
                className={`px-1.5 py-0.5 rounded transition-colors ${speed === opt
                    ? "bg-cyan-600/30 text-cyan-300 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                  }`}
                aria-label={`Animation speed ${opt}x`}
              >
                {opt}x
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={() => setManualReducedMotion(!reducedMotion)}
            className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${reducedMotion
                ? "bg-emerald-950/70 text-emerald-300 border-emerald-700/70"
                : "bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200"
              }`}
            title="Toggle accessible reduced-motion mode"
            aria-pressed={reducedMotion}
          >
            <EyeOff className="h-3.5 w-3.5" />
            <span className="hidden md:inline">Reduced Motion</span>
          </button>

          <button
            type="button"
            onClick={() => setMobileListMode((m) => !m)}
            className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${mobileListMode
                ? "bg-cyan-950/70 text-cyan-300 border-cyan-700/70"
                : "bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200"
              }`}
            title="Switch between Interactive Graph and Accessible Step List"
          >
            <ListChecks className="h-3.5 w-3.5" />
            <span className="hidden md:inline">{mobileListMode ? "Graph View" : "Step List"}</span>
          </button>

          {!mobileListMode && (
            <button
              type="button"
              onClick={handleFitView}
              className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
              title="Fit diagram to screen"
            >
              <Scan className="h-3.5 w-3.5" />
              <span className="hidden lg:inline">Fit</span>
            </button>
          )}

          <button
            type="button"
            onClick={() => setIsFullscreen((f) => !f)}
            className="inline-flex items-center gap-1 rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800"
            title={isFullscreen ? "Exit Fullscreen (Esc)" : "Fullscreen Diagram Mode"}
            aria-label={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}
          >
            {isFullscreen ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Step Scrubber Strip */}
      <div
        ref={scrubberRef}
        className="border-b border-slate-800/80 bg-slate-950 px-3 py-1.5 flex items-center gap-1 overflow-x-auto"
      >
        {steps.map((s, idx) => {
          const active = idx === activeIndex;
          return (
            <button
              key={s.id}
              type="button"
              data-scrubber-idx={idx}
              onClick={() => {
                setActiveIndex(idx);
                setIsPlaying(false);
              }}
              className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-mono transition-colors border ${active
                  ? "bg-cyan-950/90 text-cyan-300 border-cyan-500/60 font-bold"
                  : idx < activeIndex
                    ? "bg-slate-900 text-slate-300 border-slate-700"
                    : "bg-slate-950 text-slate-500 border-slate-800 hover:text-slate-300"
                }`}
            >
              {s.stepNumber}. {s.shortLabel}
            </button>
          );
        })}
      </div>

      {/* Main Split: Interactive Diagram + Step Inspector */}
      <div
        className={`grid grid-cols-1 xl:grid-cols-12 ${isFullscreen ? "flex-1 min-h-0" : ""
          }`}
      >
        {/* Left / Top: Interactive Pan/Zoom SVG Diagram OR Accessible Step List */}
        <div
          className={`xl:col-span-8 flex flex-col border-b xl:border-b-0 xl:border-r border-slate-800 ${isFullscreen ? "h-full min-h-[380px]" : "h-[520px] sm:h-[600px] lg:h-[640px]"
            }`}
        >
          {mobileListMode ? (
            <div className="flex-1 min-h-0 overflow-y-auto p-3 space-y-2 bg-slate-950">
              {steps.map((s, idx) => {
                const active = idx === activeIndex;
                return (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => {
                      setActiveIndex(idx);
                      setIsPlaying(false);
                    }}
                    className={`w-full text-left rounded-lg border p-3 transition-colors ${active
                        ? "border-cyan-500/70 bg-cyan-950/25"
                        : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
                      }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1">
                      <span className="text-xs font-bold text-slate-100 break-words">
                        {s.stepNumber}. {s.title}
                      </span>
                      <span className="text-[10px] font-mono text-cyan-400 shrink-0">{s.laneLabel}</span>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-1">{s.summary}</p>
                  </button>
                );
              })}
            </div>
          ) : (
            <>
              <div
                ref={viewportRef}
                onPointerDown={handlePointerDown}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
                onPointerCancel={handlePointerUp}
                onWheel={handleWheel}
                className="relative flex-1 min-h-0 w-full overflow-hidden bg-slate-950 cursor-grab active:cursor-grabbing select-none"
                style={{
                  backgroundImage: "radial-gradient(#1e293b 1px, transparent 1px)",
                  backgroundSize: "18px 18px",
                }}
              >
                {/* Transformed Pan/Zoom Plane */}
                <div
                  data-flow-plane="true"
                  style={{
                    width: canvasBounds.width,
                    height: canvasBounds.height,
                    transform: `translate(${activeTransform.panX}px, ${activeTransform.panY}px) scale(${activeTransform.zoom})`,
                    transformOrigin: "0 0",
                  }}
                  className="relative will-change-transform"
                >
                {/* Layer 1: Swimlane Group Backdrops */}
                {swimlanes.map((lane) => {
                  const isCyan = lane.accent === "cyan";
                  return (
                    <div
                      key={lane.id}
                      style={{
                        left: lane.position.x,
                        top: lane.position.y,
                        width: lane.width,
                        height: lane.height,
                      }}
                      className={`pointer-events-none absolute rounded-xl border border-dashed ${isCyan
                          ? "border-cyan-500/30 bg-cyan-950/10"
                          : "border-emerald-500/30 bg-emerald-950/10"
                        } p-3 flex flex-col justify-between`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span
                          className={`text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${isCyan
                              ? "bg-cyan-950/80 text-cyan-300 border-cyan-800/60"
                              : "bg-emerald-950/80 text-emerald-300 border-emerald-800/60"
                            }`}
                        >
                          {lane.title}
                        </span>
                        <span className="text-[10px] text-slate-400 font-medium">
                          {lane.subtitle}
                        </span>
                      </div>
                    </div>
                  );
                })}

                {/* Layer 2: SVG Directional Connections & Animated Packets */}
                <svg
                  width={canvasBounds.width}
                  height={canvasBounds.height}
                  className="pointer-events-none absolute inset-0 overflow-visible"
                >
                  <defs>
                    {(Object.keys(ACCENT_STYLES) as NodeAccent[]).map((acc) => (
                      <marker
                        key={acc}
                        id={`${markerPrefix}-arrow-${acc}`}
                        viewBox="0 0 10 10"
                        refX="8.5"
                        refY="5"
                        markerWidth="6"
                        markerHeight="6"
                        orient="auto"
                      >
                        <path d="M 0 1.5 L 8.5 5 L 0 8.5 z" fill={ACCENT_STYLES[acc].stroke} />
                      </marker>
                    ))}
                    <marker
                      id={`${markerPrefix}-arrow-muted`}
                      viewBox="0 0 10 10"
                      refX="8.5"
                      refY="5"
                      markerWidth="6"
                      markerHeight="6"
                      orient="auto"
                    >
                      <path d="M 0 1.5 L 8.5 5 L 0 8.5 z" fill="#64748b" />
                    </marker>
                  </defs>

                  {computedEdges.map(({ edge, pathD, isActiveEdge }) => {
                    const accent = edge.accent || "cyan";
                    const style = ACCENT_STYLES[accent];
                    const isBridge = Boolean(edge.isBridge);
                    const strokeColor = isActiveEdge
                      ? style.stroke
                      : isBridge
                        ? "rgba(129, 140, 248, 0.55)"
                        : "rgba(100, 116, 139, 0.45)";
                    const markerId = isActiveEdge
                      ? `${markerPrefix}-arrow-${accent}`
                      : isBridge
                        ? `${markerPrefix}-arrow-indigo`
                        : `${markerPrefix}-arrow-muted`;

                    return (
                      <g key={edge.id}>
                        <path
                          d={pathD}
                          fill="none"
                          stroke={strokeColor}
                          strokeWidth={isActiveEdge ? 2.6 : isBridge ? 1.8 : 1.5}
                          strokeDasharray={isBridge && !isActiveEdge ? "5 5" : undefined}
                          className={isActiveEdge && !reducedMotion ? "flow-edge-animated" : undefined}
                          markerEnd={`url(#${markerId})`}
                        />
                        {isActiveEdge && !reducedMotion && (
                          <circle r={4} fill={style.packet}>
                            <animateMotion dur={packetDur} repeatCount="indefinite" path={pathD} />
                          </circle>
                        )}
                      </g>
                    );
                  })}
                </svg>

                {/* Layer 3: Edge Pill Labels */}
                {computedEdges.map(({ edge, labelX, labelY, isActiveEdge }) =>
                  edge.label ? (
                    <div
                      key={`${edge.id}-label`}
                      style={{
                        left: labelX,
                        top: labelY,
                        transform: "translate(-50%, -50%)",
                      }}
                      className={`pointer-events-none absolute z-10 rounded px-1.5 py-0.5 text-[9px] font-mono border backdrop-blur-sm whitespace-nowrap ${isActiveEdge
                          ? "bg-slate-950/95 text-cyan-200 border-cyan-500/60 shadow-md"
                          : edge.isBridge
                            ? "bg-indigo-950/90 text-indigo-200 border-indigo-700/60"
                            : "bg-slate-950/85 text-slate-400 border-slate-800"
                        }`}
                    >
                      {edge.label}
                    </div>
                  ) : null
                )}

                {/* Layer 4: Clickable Workflow Step Nodes */}
                {steps.map((step, idx) => {
                  const isActive = idx === activeIndex;
                  const isVisited = idx < activeIndex;
                  const style = ACCENT_STYLES[step.accent];

                  return (
                    <button
                      key={step.id}
                      type="button"
                      data-flow-node="true"
                      onClick={() => handleSelectStepById(step.id)}
                      aria-label={`Step ${step.stepNumber}: ${step.title}`}
                      aria-pressed={isActive}
                      style={{
                        left: step.position.x,
                        top: step.position.y,
                        width: NODE_WIDTH,
                      }}
                      className={`flow-step-node group absolute z-20 rounded-lg border px-2.5 py-2 text-left transition-all cursor-pointer select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${isActive
                          ? `bg-slate-900 ${style.activeBorder} scale-[1.03]`
                          : isVisited
                            ? `bg-slate-950/95 ${style.border} opacity-95 hover:border-slate-500`
                            : "bg-slate-950/90 border-slate-800 hover:border-slate-600"
                        }`}
                    >
                      <div className="flex items-center justify-between gap-1.5 mb-1">
                        <span
                          className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-mono font-bold border ${style.badgeBg}`}
                        >
                          <span>#{step.stepNumber}</span>
                          {isActive && (
                            <span
                              className={`h-1.5 w-1.5 rounded-full ${style.dot} ${reducedMotion ? "" : "animate-pulse"
                                }`}
                            />
                          )}
                        </span>
                        <span className="text-[9px] font-mono uppercase tracking-wider text-slate-500 truncate">
                          {step.laneLabel}
                        </span>
                      </div>

                      <div className="text-xs font-bold text-slate-100 leading-tight group-hover:text-cyan-200 transition-colors">
                        {step.shortLabel}
                      </div>
                      <div className="mt-0.5 text-[10px] text-slate-400 font-mono truncate">
                        {step.componentName}
                      </div>

                      {step.outcomeBadge && (
                        <div className="mt-1.5">
                          <span
                            className={`inline-block rounded px-1.5 py-0.5 text-[9px] font-mono font-bold border ${step.outcomeBadge === "TRUE_POSITIVE"
                                ? "bg-rose-950/80 text-rose-300 border-rose-700/70"
                                : step.outcomeBadge === "FALSE_POSITIVE"
                                  ? "bg-emerald-950/80 text-emerald-300 border-emerald-700/70"
                                  : "bg-amber-950/80 text-amber-300 border-amber-700/70"
                              }`}
                          >
                            {step.outcomeBadge}
                          </span>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
              </div>

              {/* Dedicated Non-Overlapping Zoom, Pan Hint & Color Legend HUD Bar (Outside viewportRef so clicks never trigger pan capture) */}
              <div
                data-no-pan="true"
                className="shrink-0 border-t border-slate-800 bg-slate-950/95 px-2.5 py-1.5 flex flex-wrap items-center justify-between gap-2 text-[10px] font-mono"
              >
                <div className="flex items-center gap-1.5">
                  <div className="inline-flex items-center rounded-md border border-slate-800 bg-slate-900 overflow-hidden">
                    <button
                      type="button"
                      onClick={() => handleZoomBy(1.18)}
                      className="p-1.5 text-slate-300 hover:bg-slate-800 hover:text-cyan-300 border-r border-slate-800 transition-colors"
                      title="Zoom In"
                      aria-label="Zoom In"
                    >
                      <ZoomIn className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleZoomBy(0.85)}
                      className="p-1.5 text-slate-300 hover:bg-slate-800 hover:text-cyan-300 border-r border-slate-800 transition-colors"
                      title="Zoom Out"
                      aria-label="Zoom Out"
                    >
                      <ZoomOut className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={handleFitView}
                      className="inline-flex items-center gap-1 px-2 py-1 text-slate-300 hover:bg-slate-800 hover:text-cyan-300 transition-colors"
                      title="Fit to Screen"
                      aria-label="Fit to Screen"
                    >
                      <Scan className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">Fit</span>
                    </button>
                  </div>
                  <span className="rounded border border-slate-800 bg-slate-900/80 px-1.5 py-0.5 text-cyan-300 tabular-nums">
                    {Math.round(activeTransform.zoom * 100)}%
                  </span>
                  <span className="hidden md:inline text-slate-500">
                    Drag to pan · Ctrl+Wheel to zoom
                  </span>
                </div>

                {/* Color Legend */}
                <div className="hidden sm:flex flex-wrap items-center gap-2.5 text-slate-400">
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-cyan-400" />
                    Governance Plane
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-emerald-400" />
                    Runtime Plane
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-indigo-400" />
                    Cross-Plane Bridge
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <span className="h-2 w-2 rounded-full bg-amber-400" />
                    Safety / Abstention
                  </span>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Right / Bottom: 6-Part Component Step Inspector */}
        <div
          className={`xl:col-span-4 bg-slate-900/30 p-3.5 space-y-3 overflow-y-auto ${isFullscreen ? "h-full" : "max-h-[620px]"
            }`}
        >
          <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-2.5">
            <div>
              <div className="flex items-center gap-1.5">
                <span className="rounded bg-cyan-950/90 border border-cyan-700/60 px-1.5 py-0.5 text-[10px] font-mono font-bold text-cyan-300">
                  STEP {activeStep.stepNumber}
                </span>
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                  {activeStep.laneLabel}
                </span>
              </div>
              <h3 className="text-sm font-bold text-slate-100 mt-1">{activeStep.title}</h3>
              <p className="text-[11px] text-slate-300 mt-1 leading-relaxed">{activeStep.summary}</p>
            </div>
          </div>

          {/* 1. Component Name & Live Route Link */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 space-y-1">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 flex items-center gap-1">
                <Cpu className="h-3 w-3" /> 1. Component Name
              </span>
              {activeStep.uiRoute && (
                <Link
                  href={activeStep.uiRoute}
                  className="inline-flex items-center gap-1 text-[10px] font-semibold text-cyan-300 hover:text-cyan-200 underline"
                >
                  <span>{activeStep.uiLabel || activeStep.uiRoute}</span>
                  <ExternalLink className="h-2.5 w-2.5" />
                </Link>
              )}
            </div>
            <div className="text-xs font-semibold text-slate-100">{activeStep.componentName}</div>
            <div className="text-[10px] font-mono text-slate-400 break-all">{activeStep.serviceModule}</div>
          </div>

          {/* 2. Input Data */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-sky-400 flex items-center gap-1">
              <ArrowRight className="h-3 w-3" /> 2. Input Data
            </div>
            <ul className="space-y-1 text-[11px] text-slate-300">
              {activeStep.inputData.map((item, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-sky-400 mt-0.5">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 3. Processing Logic */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-indigo-400 flex items-center gap-1">
              <Layers className="h-3 w-3" /> 3. Processing Logic
            </div>
            <ul className="space-y-1 text-[11px] text-slate-300">
              {activeStep.processingLogic.map((item, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-indigo-400 mt-0.5">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 4. Output Data */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> 4. Output Data
            </div>
            <ul className="space-y-1 text-[11px] text-slate-300">
              {activeStep.outputData.map((item, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-emerald-400 mt-0.5">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 5. Required Configuration */}
          <div className="rounded-lg border border-slate-800 bg-slate-950/80 p-2.5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1">
              <Settings2 className="h-3 w-3" /> 5. Required Configuration
            </div>
            <ul className="space-y-1 text-[11px] text-slate-300">
              {activeStep.requiredConfig.map((item, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-slate-400 mt-0.5">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* 6. Possible Failure or Abstention Conditions */}
          <div className="rounded-lg border border-amber-900/50 bg-amber-950/15 p-2.5 space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-amber-300 flex items-center gap-1">
              <ShieldAlert className="h-3 w-3" /> 6. Failure or Abstention Conditions
            </div>
            <ul className="space-y-1 text-[11px] text-amber-200/90">
              {activeStep.failureOrAbstention.map((item, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <AlertTriangle className="h-3 w-3 text-amber-400 shrink-0 mt-0.5" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
