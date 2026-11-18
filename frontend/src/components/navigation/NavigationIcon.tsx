"use client";

import React from "react";
import {
  LayoutDashboard,
  ShieldAlert,
  RadioTower,
  UserRoundCheck,
  Bot,
  BrainCircuit,
  Radar,
  Database,
  FlaskConical,
  ChartNoAxesCombined,
  ServerCog,
  SlidersHorizontal,
  ShieldCheck,
  BookOpenText,
  FileText,
  type LucideIcon,
} from "lucide-react";
import {
  getNavigationIconMetadata,
  getSemanticIconCssVars,
  resolveNavigationPageId,
  type NavigationPageId,
} from "@/config/navigationIcons";

/**
 * Centralized Lucide icon component registry for all 14 Verdictum AI sidebar pages.
 * All navigation consumers (main Sidebar, Admin Guide sidebar, workspace links) resolve
 * icons exclusively through this mapping to prevent duplicated definitions.
 */
export const NAVIGATION_ICON_COMPONENTS: Record<NavigationPageId, LucideIcon> = {
  "agent-mission-control": LayoutDashboard,
  "ai-triage-workbench": ShieldAlert,
  "telemetry-hub": RadioTower,
  "human-review-queue": UserRoundCheck,
  "soc-chatbot": Bot,
  "agent-intelligence-studio": BrainCircuit,
  "detection-intelligence": Radar,
  "agent-memory": Database,
  "agent-simulation-lab": FlaskConical,
  "verdict-intelligence": ChartNoAxesCombined,
  "inference-control": ServerCog,
  "agent-configuration": SlidersHorizontal,
  "governance-access": ShieldCheck,
  "admin-guide": BookOpenText,
};

export type NavigationIconSize = "expanded" | "collapsed" | "compact" | "xs";

interface SizeSpec {
  iconPx: number;
  containerClass: string;
}

const SIZE_SPECS: Record<NavigationIconSize, SizeSpec> = {
  /** Expanded main sidebar: ~18px icon inside a compact 26px semantic-tinted badge */
  expanded: {
    iconPx: 18,
    containerClass: "w-[26px] h-[26px] rounded-[7px]",
  },
  /** Collapsed main sidebar: ~20px icon inside a centered 32px semantic-tinted badge */
  collapsed: {
    iconPx: 20,
    containerClass: "w-8 h-8 rounded-lg",
  },
  /** Admin Guide internal sidebar & compact navigation cards: 16px icon inside 24px badge */
  compact: {
    iconPx: 16,
    containerClass: "w-6 h-6 rounded-md",
  },
  /** Inline chips / quick workspace shortcuts: 14px icon */
  xs: {
    iconPx: 14,
    containerClass: "w-5 h-5 rounded",
  },
};

export interface NavigationIconProps {
  /** Page slug (e.g. "telemetry-hub") or route path (e.g. "/telemetry-hub"). */
  pageId: string;
  /** Icon sizing profile aligned with sidebar and Admin Guide layouts. */
  size?: NavigationIconSize;
  /** Highlights the semantic icon container when its parent item is active/selected. */
  active?: boolean;
  /** Renders the subtle 8–12% opacity semantic-tinted icon container (default: true). */
  withContainer?: boolean;
  /** Optional className applied to the outer container (or SVG when withContainer=false). */
  className?: string;
  /** Lucide stroke width (default: 1.9 for crisp contrast on Obsidian surfaces). */
  strokeWidth?: number;
}

/**
 * Reusable semantic multicolor navigation icon component.
 * Renders the canonical Lucide icon with its centralized semantic color and subtle
 * tinted background badge across main navigation and Admin Guide references.
 */
export function NavigationIcon({
  pageId,
  size = "expanded",
  active = false,
  withContainer = true,
  className = "",
  strokeWidth = 1.9,
}: NavigationIconProps) {
  const resolvedId = resolveNavigationPageId(pageId);
  const meta = getNavigationIconMetadata(pageId);
  const IconComponent: LucideIcon = resolvedId
    ? NAVIGATION_ICON_COMPONENTS[resolvedId]
    : FileText;

  const spec = SIZE_SPECS[size];
  const cssVars = getSemanticIconCssVars(meta);
  const style = cssVars as unknown as React.CSSProperties;

  if (!withContainer) {
    return (
      <IconComponent
        size={spec.iconPx}
        strokeWidth={strokeWidth}
        aria-hidden="true"
        style={{ color: meta?.color ?? "#CBD5E1" }}
        className={`shrink-0 nav-icon-glyph ${className}`.trim()}
        data-nav-icon={meta?.iconName ?? "file-text"}
      />
    );
  }

  return (
    <span
      aria-hidden="true"
      style={style}
      data-nav-icon-badge={meta?.id ?? "fallback"}
      data-nav-icon-color={meta?.color ?? "#CBD5E1"}
      data-nav-icon-active={active ? "true" : "false"}
      className={`nav-icon-badge inline-flex items-center justify-center shrink-0 ${spec.containerClass} ${
        active ? "nav-icon-badge-active" : ""
      } ${className}`.trim()}
    >
      <IconComponent
        size={spec.iconPx}
        strokeWidth={strokeWidth}
        className="nav-icon-glyph shrink-0"
      />
    </span>
  );
}
