"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  Background,
  BackgroundVariant,
  Handle,
  Position,
  getSmoothStepPath,
  EdgeLabelRenderer,
  useReactFlow,
  MarkerType,
  type Node,
  type Edge,
  type NodeProps,
  type EdgeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Play,
  Pause,
  RotateCcw,
  SkipBack,
  SkipForward,
  Maximize2,
  Minimize2,
  Scan,
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

const SPEED_INTERVAL_MS: Record<SpeedOption, number> = {
  0.5: 3200,
  1: 1800,
  1.5: 1200,
  2: 850,
};

interface LaneNodeData extends Record<string, unknown> {
  title: string;
  subtitle: string;
  accent: "cyan" | "emerald";
  width: number;
  height: number;
}

interface StepNodeData extends Record<string, unknown> {
  step: WorkflowStepSpec;
  isActive: boolean;
  isVisited: boolean;
  reducedMotion: boolean;
  onSelect: (stepId: string) => void;
}

interface PacketEdgeData extends Record<string, unknown> {
  label?: string;
  isBridge?: boolean;
  isActiveEdge: boolean;
  reducedMotion: boolean;
  accent: NodeAccent;
  speed: SpeedOption;
}

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

function LaneBackdropNode({ data }: NodeProps<Node<LaneNodeData>>) {
  const isCyan = data.accent === "cyan";
  return (
    <div
      style={{ width: data.width, height: data.height }}
      className={`pointer-events-none rounded-xl border border-dashed ${
        isCyan
          ? "border-cyan-500/30 bg-cyan-950/10"
          : "border-emerald-500/30 bg-emerald-950/10"
      } p-3 flex flex-col justify-between`}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          className={`text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${
            isCyan
              ? "bg-cyan-950/80 text-cyan-300 border-cyan-800/60"
              : "bg-emerald-950/80 text-emerald-300 border-emerald-800/60"
          }`}
        >
          {data.title}
        </span>
        <span className="text-[10px] text-slate-400 font-medium">{data.subtitle}</span>
      </div>
    </div>
  );
}

function WorkflowStepNode({ data }: NodeProps<Node<StepNodeData>>) {
  const { step, isActive, isVisited, reducedMotion, onSelect } = data;
  const style = ACCENT_STYLES[step.accent];

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onSelect(step.id)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onSelect(step.id);
        }
      }}
      aria-label={`Step ${step.stepNumber}: ${step.title}`}
      aria-pressed={isActive}
      className={`group relative w-[205px] rounded-lg border px-2.5 py-2 text-left transition-all cursor-pointer select-none focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${
        isActive
          ? `bg-slate-900 ${style.activeBorder} scale-[1.03]`
          : isVisited
          ? `bg-slate-950/95 ${style.border} opacity-95 hover:border-slate-500`
          : "bg-slate-950/90 border-slate-800 hover:border-slate-600"
      }`}
    >
      {/* Hidden multi-side handles so directional edges never cross through node bodies */}
      <Handle id="left-in" type="target" position={Position.Left} className="!w-1.5 !h-1.5 !bg-slate-600 !border-slate-900" />
      <Handle id="right-in" type="target" position={Position.Right} className="!w-1.5 !h-1.5 !bg-slate-600 !border-slate-900" />
      <Handle id="top-in" type="target" position={Position.Top} className="!w-1.5 !h-1.5 !bg-slate-600 !border-slate-900" />
      <Handle id="bottom-in" type="target" position={Position.Bottom} className="!w-1.5 !h-1.5 !bg-slate-600 !border-slate-900" />

      <Handle id="right-out" type="source" position={Position.Right} className="!w-1.5 !h-1.5 !bg-cyan-500/80 !border-slate-900" />
      <Handle id="left-out" type="source" position={Position.Left} className="!w-1.5 !h-1.5 !bg-cyan-500/80 !border-slate-900" />
      <Handle id="bottom-out" type="source" position={Position.Bottom} className="!w-1.5 !h-1.5 !bg-cyan-500/80 !border-slate-900" />
      <Handle id="top-out" type="source" position={Position.Top} className="!w-1.5 !h-1.5 !bg-cyan-500/80 !border-slate-900" />

      <div className="flex items-center justify-between gap-1.5 mb-1">
        <span
          className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-mono font-bold border ${style.badgeBg}`}
        >
          <span>#{step.stepNumber}</span>
          {isActive && (
            <span
              className={`h-1.5 w-1.5 rounded-full ${style.dot} ${
                reducedMotion ? "" : "animate-pulse"
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
            className={`inline-block rounded px-1.5 py-0.5 text-[9px] font-mono font-bold border ${
              step.outcomeBadge === "TRUE_POSITIVE"
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
    </div>
  );
}

function AnimatedPacketEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  data,
}: EdgeProps<Edge<PacketEdgeData>>) {
  const [edgePath, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    borderRadius: 12,
  });

  const accent = data?.accent || "cyan";
  const style = ACCENT_STYLES[accent];
  const isActive = Boolean(data?.isActiveEdge);
  const isBridge = Boolean(data?.isBridge);
  const reducedMotion = Boolean(data?.reducedMotion);
  const speed = data?.speed || 1;
  const packetDur = `${(1.4 / speed).toFixed(2)}s`;

  const strokeColor = isActive
    ? style.stroke
    : isBridge
    ? "rgba(129, 140, 248, 0.55)"
    : "rgba(100, 116, 139, 0.45)";

  return (
    <>
      <path
        id={id}
        d={edgePath}
        fill="none"
        stroke={strokeColor}
        strokeWidth={isActive ? 2.6 : isBridge ? 1.8 : 1.5}
        strokeDasharray={isBridge && !isActive ? "5 5" : undefined}
        className={isActive && !reducedMotion ? "flow-edge-animated" : undefined}
        markerEnd={markerEnd}
      />
      {isActive && !reducedMotion && (
        <circle r={4} fill={style.packet} className="pointer-events-none">
          <animateMotion dur={packetDur} repeatCount="indefinite" path={edgePath} />
        </circle>
      )}
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            }}
            className={`pointer-events-none absolute rounded px-1.5 py-0.5 text-[9px] font-mono border backdrop-blur-sm ${
              isActive
                ? "bg-slate-950/95 text-cyan-200 border-cyan-500/60 shadow-md"
                : isBridge
                ? "bg-indigo-950/90 text-indigo-200 border-indigo-700/60"
                : "bg-slate-950/85 text-slate-400 border-slate-800"
            }`}
          >
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

const NODE_TYPES = {
  laneBackdrop: LaneBackdropNode,
  workflowStep: WorkflowStepNode,
};

const EDGE_TYPES = {
  animatedPacket: AnimatedPacketEdge,
};

interface WorkflowFlowInnerProps {
  title: string;
  subtitle: string;
  steps: WorkflowStepSpec[];
  edges: WorkflowEdgeSpec[];
  swimlanes: SwimlaneBoxSpec[];
  initialStepId?: string;
}

function WorkflowFlowInner({
  title,
  subtitle,
  steps,
  edges,
  swimlanes,
  initialStepId,
}: WorkflowFlowInnerProps) {
  const { fitView } = useReactFlow();

  const initialIdx = useMemo(() => {
    if (!initialStepId) return 0;
    const found = steps.findIndex((s) => s.id === initialStepId);
    return found >= 0 ? found : 0;
  }, [initialStepId, steps]);

  const [activeIndex, setActiveIndex] = useState<number>(initialIdx);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<SpeedOption>(1);
  const osReducedMotion = usePrefersReducedMotion();
  const [manualReducedMotion, setManualReducedMotion] = useState<boolean | null>(null);
  const reducedMotion = manualReducedMotion ?? osReducedMotion;
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);
  const [mobileListMode, setMobileListMode] = useState<boolean>(false);

  // Keyboard Escape exits fullscreen
  useEffect(() => {
    if (!isFullscreen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsFullscreen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isFullscreen]);

  // Fit view when fullscreen toggles
  useEffect(() => {
    const t = setTimeout(() => {
      fitView({ padding: 0.12, duration: reducedMotion ? 0 : 250 });
    }, 80);
    return () => clearTimeout(t);
  }, [isFullscreen, fitView, reducedMotion]);

  // Playback timer
  useEffect(() => {
    if (!isPlaying) return;
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % steps.length);
    }, SPEED_INTERVAL_MS[speed]);
    return () => clearInterval(timer);
  }, [isPlaying, speed, steps.length]);

  const activeStep = steps[activeIndex] || steps[0];

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

  const handleFitView = () => {
    fitView({ padding: 0.12, duration: reducedMotion ? 0 : 280 });
  };

  const flowNodes: Node[] = useMemo(() => {
    const laneNodes: Node<LaneNodeData>[] = swimlanes.map((lane) => ({
      id: lane.id,
      type: "laneBackdrop",
      position: lane.position,
      draggable: false,
      selectable: false,
      focusable: false,
      zIndex: 0,
      data: {
        title: lane.title,
        subtitle: lane.subtitle,
        accent: lane.accent,
        width: lane.width,
        height: lane.height,
      },
    }));

    const stepNodes: Node<StepNodeData>[] = steps.map((step, idx) => ({
      id: step.id,
      type: "workflowStep",
      position: step.position,
      draggable: false,
      zIndex: 10,
      data: {
        step,
        isActive: idx === activeIndex,
        isVisited: idx < activeIndex,
        reducedMotion,
        onSelect: handleSelectStepById,
      },
    }));

    return [...laneNodes, ...stepNodes];
  }, [swimlanes, steps, activeIndex, reducedMotion, handleSelectStepById]);

  const flowEdges: Edge<PacketEdgeData>[] = useMemo(() => {
    return edges.map((edge) => {
      const isConnectedToActive =
        edge.source === activeStep.id || edge.target === activeStep.id;
      const accent = edge.accent || "cyan";
      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        sourceHandle: edge.sourceHandle,
        targetHandle: edge.targetHandle,
        type: "animatedPacket",
        zIndex: isConnectedToActive ? 20 : 5,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 15,
          height: 15,
          color: isConnectedToActive
            ? ACCENT_STYLES[accent].stroke
            : edge.isBridge
            ? "#818cf8"
            : "#64748b",
        },
        data: {
          label: edge.label,
          isBridge: edge.isBridge,
          isActiveEdge: isConnectedToActive,
          reducedMotion,
          accent,
          speed,
        },
      };
    });
  }, [edges, activeStep.id, reducedMotion, speed]);

  return (
    <div
      className={`${
        reducedMotion ? "guide-reduced-motion" : ""
      } ${
        isFullscreen
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
            <span className="rounded-full bg-cyan-950/80 border border-cyan-800/60 px-2 py-0.5 text-[10px] font-mono text-cyan-300">
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
            className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1 text-xs font-semibold border transition-colors ${
              isPlaying
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
                className={`px-1.5 py-0.5 rounded transition-colors ${
                  speed === opt
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
            className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${
              reducedMotion
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
            className={`inline-flex items-center gap-1 rounded-md border px-2 py-1 text-[11px] font-medium transition-colors ${
              mobileListMode
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
      <div className="border-b border-slate-800/80 bg-slate-950 px-3 py-1.5 flex items-center gap-1 overflow-x-auto">
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
              className={`shrink-0 rounded px-2 py-0.5 text-[10px] font-mono transition-colors border ${
                active
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

      {/* Main Split: Diagram + Step Inspector */}
      <div
        className={`grid grid-cols-1 xl:grid-cols-12 ${
          isFullscreen ? "flex-1 min-h-0" : ""
        }`}
      >
        {/* Left / Top: Interactive React Flow Canvas OR Accessible Step List */}
        <div
          className={`xl:col-span-8 relative border-b xl:border-b-0 xl:border-r border-slate-800 ${
            isFullscreen ? "h-full min-h-[380px]" : "h-[480px] sm:h-[560px] lg:h-[620px]"
          }`}
        >
          {mobileListMode ? (
            <div className="h-full overflow-y-auto p-3 space-y-2 bg-slate-950">
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
                    className={`w-full text-left rounded-lg border p-3 transition-colors ${
                      active
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
            <div className="ai-verdict-flow w-full h-full bg-slate-950">
              <ReactFlow
                nodes={flowNodes}
                edges={flowEdges}
                nodeTypes={NODE_TYPES}
                edgeTypes={EDGE_TYPES}
                fitView
                fitViewOptions={{ padding: 0.12 }}
                minZoom={0.35}
                maxZoom={1.75}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={true}
                proOptions={{ hideAttribution: true }}
              >
                <Background
                  variant={BackgroundVariant.Dots}
                  gap={18}
                  size={1}
                  color="#1e293b"
                />
                <Controls showInteractive={false} />
              </ReactFlow>

              {/* Floating Legend */}
              <div className="pointer-events-none absolute bottom-3 right-3 hidden sm:flex flex-wrap items-center gap-2 rounded-lg border border-slate-800 bg-slate-950/90 px-2.5 py-1.5 text-[10px] font-mono text-slate-400 backdrop-blur-sm">
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
          )}
        </div>

        {/* Right / Bottom: 6-Part Component Step Inspector */}
        <div
          className={`xl:col-span-4 bg-slate-900/30 p-3.5 space-y-3 overflow-y-auto ${
            isFullscreen ? "h-full" : "max-h-[620px]"
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

export function WorkflowFlowDiagram(props: WorkflowFlowInnerProps) {
  return (
    <ReactFlowProvider>
      <WorkflowFlowInner {...props} />
    </ReactFlowProvider>
  );
}
