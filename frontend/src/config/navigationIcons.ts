/**
 * Centralized Semantic Navigation Icon Configuration for Verdictum AI.
 *
 * Single source of truth for all 14 primary sidebar destinations across:
 * - Main application Sidebar (expanded & collapsed modes)
 * - Verdictum AI Admin Guide internal sidebar, search results, page headers, and workspace links
 *
 * Note: Semantic colors are defined as explicit hex/RGB values rather than Tailwind `cyan`/`sky`
 * utility classes so they remain true multicolor identities under both Obsidian Glass (which
 * remaps `--color-cyan-*` and `--color-sky-*` to warm amber/gold) and Classic Slate themes.
 */

export type NavigationGroupTitle =
  | "SOC OPERATIONS"
  | "AGENT INTELLIGENCE"
  | "VALIDATION & TRUST"
  | "PLATFORM CONTROL";

export type NavigationPageId =
  | "agent-mission-control"
  | "ai-triage-workbench"
  | "telemetry-hub"
  | "human-review-queue"
  | "soc-chatbot"
  | "agent-intelligence-studio"
  | "detection-intelligence"
  | "agent-memory"
  | "agent-simulation-lab"
  | "verdict-intelligence"
  | "inference-control"
  | "agent-configuration"
  | "governance-access"
  | "admin-guide";

export interface NavigationIconMetadata {
  /** Canonical page identifier (matches Admin Guide slug and route segment). */
  id: NavigationPageId;
  /** Exact user-facing page title. */
  title: string;
  /** Canonical App Router route. */
  href: string;
  /** Sidebar category group title. */
  groupTitle: NavigationGroupTitle;
  /** Lucide icon kebab-case identifier. */
  iconName: string;
  /** Lucide React PascalCase component name. */
  componentName: string;
  /** Semantic accent hex color (WCAG AA compliant on Obsidian & Classic dark surfaces). */
  color: string;
  /** RGB triplet matching `color`, used for subtle 8–12% opacity semantic background tints. */
  rgb: string;
  /** Default semantic container tint opacity (0.08–0.12). */
  tintOpacity: number;
  /** Hover semantic container tint opacity. */
  hoverTintOpacity: number;
  /** Active semantic container tint opacity. */
  activeTintOpacity: number;
  /** Optional navigation badge label (e.g., COPILOT). */
  badge?: string;
  /** Optional Tailwind classes for the badge. */
  badgeColor?: string;
}

export const NAVIGATION_PAGE_IDS: readonly NavigationPageId[] = [
  "agent-mission-control",
  "ai-triage-workbench",
  "telemetry-hub",
  "human-review-queue",
  "soc-chatbot",
  "agent-intelligence-studio",
  "detection-intelligence",
  "agent-memory",
  "agent-simulation-lab",
  "verdict-intelligence",
  "inference-control",
  "agent-configuration",
  "governance-access",
  "admin-guide",
] as const;

export const NAVIGATION_GROUP_ORDER: readonly NavigationGroupTitle[] = [
  "SOC OPERATIONS",
  "AGENT INTELLIGENCE",
  "VALIDATION & TRUST",
  "PLATFORM CONTROL",
] as const;

export const NAVIGATION_ICON_METADATA: Record<NavigationPageId, NavigationIconMetadata> = {
  "agent-mission-control": {
    id: "agent-mission-control",
    title: "Agent Mission Control",
    href: "/agent-mission-control",
    groupTitle: "SOC OPERATIONS",
    iconName: "layout-dashboard",
    componentName: "LayoutDashboard",
    color: "#38BDF8",
    rgb: "56, 189, 248",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "ai-triage-workbench": {
    id: "ai-triage-workbench",
    title: "AI Triage Workbench",
    href: "/ai-triage-workbench",
    groupTitle: "SOC OPERATIONS",
    iconName: "shield-alert",
    componentName: "ShieldAlert",
    color: "#FB923C",
    rgb: "251, 146, 60",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "telemetry-hub": {
    id: "telemetry-hub",
    title: "Telemetry Hub",
    href: "/telemetry-hub",
    groupTitle: "SOC OPERATIONS",
    iconName: "radio-tower",
    componentName: "RadioTower",
    color: "#22D3EE",
    rgb: "34, 211, 238",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "human-review-queue": {
    id: "human-review-queue",
    title: "Human Review Queue",
    href: "/human-review-queue",
    groupTitle: "SOC OPERATIONS",
    iconName: "user-round-check",
    componentName: "UserRoundCheck",
    color: "#4ADE80",
    rgb: "74, 222, 128",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "soc-chatbot": {
    id: "soc-chatbot",
    title: "Verdictum Sentinel",
    href: "/soc-chatbot",
    groupTitle: "SOC OPERATIONS",
    iconName: "bot",
    componentName: "Bot",
    color: "#A78BFA",
    rgb: "167, 139, 250",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
    badge: "COPILOT",
    badgeColor: "bg-indigo-950 text-indigo-300 border border-indigo-800",
  },
  "agent-intelligence-studio": {
    id: "agent-intelligence-studio",
    title: "Agent Intelligence Studio",
    href: "/agent-intelligence-studio",
    groupTitle: "AGENT INTELLIGENCE",
    iconName: "brain-circuit",
    componentName: "BrainCircuit",
    color: "#C084FC",
    rgb: "192, 132, 252",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "detection-intelligence": {
    id: "detection-intelligence",
    title: "Detection Intelligence",
    href: "/detection-intelligence",
    groupTitle: "AGENT INTELLIGENCE",
    iconName: "radar",
    componentName: "Radar",
    color: "#FBBF24",
    rgb: "251, 191, 36",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "agent-memory": {
    id: "agent-memory",
    title: "Agent Memory",
    href: "/agent-memory",
    groupTitle: "AGENT INTELLIGENCE",
    iconName: "database",
    componentName: "Database",
    color: "#818CF8",
    rgb: "129, 140, 248",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "agent-simulation-lab": {
    id: "agent-simulation-lab",
    title: "Agent Simulation Lab",
    href: "/agent-simulation-lab",
    groupTitle: "VALIDATION & TRUST",
    iconName: "flask-conical",
    componentName: "FlaskConical",
    color: "#FB923C",
    rgb: "251, 146, 60",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "verdict-intelligence": {
    id: "verdict-intelligence",
    title: "Verdict Intelligence",
    href: "/verdict-intelligence",
    groupTitle: "VALIDATION & TRUST",
    iconName: "chart-no-axes-combined",
    componentName: "ChartNoAxesCombined",
    color: "#2DD4BF",
    rgb: "45, 212, 191",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "inference-control": {
    id: "inference-control",
    title: "Inference Control",
    href: "/inference-control",
    groupTitle: "PLATFORM CONTROL",
    iconName: "server-cog",
    componentName: "ServerCog",
    color: "#60A5FA",
    rgb: "96, 165, 250",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "agent-configuration": {
    id: "agent-configuration",
    title: "Agent Configuration",
    href: "/agent-configuration",
    groupTitle: "PLATFORM CONTROL",
    iconName: "sliders-horizontal",
    componentName: "SlidersHorizontal",
    color: "#CBD5E1",
    rgb: "203, 213, 225",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "governance-access": {
    id: "governance-access",
    title: "Governance & Access",
    href: "/governance-access",
    groupTitle: "PLATFORM CONTROL",
    iconName: "shield-check",
    componentName: "ShieldCheck",
    color: "#4ADE80",
    rgb: "74, 222, 128",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
  "admin-guide": {
    id: "admin-guide",
    title: "Verdictum AI Admin Guide",
    href: "/admin-guide",
    groupTitle: "PLATFORM CONTROL",
    iconName: "book-open-text",
    componentName: "BookOpenText",
    color: "#FBBF24",
    rgb: "251, 191, 36",
    tintOpacity: 0.1,
    hoverTintOpacity: 0.16,
    activeTintOpacity: 0.18,
  },
};

export const ROUTE_TO_PAGE_ID: Record<string, NavigationPageId> = {
  "/": "agent-mission-control",
  "/agent-mission-control": "agent-mission-control",
  "/ai-triage-workbench": "ai-triage-workbench",
  "/telemetry-hub": "telemetry-hub",
  "/human-review-queue": "human-review-queue",
  "/soc-chatbot": "soc-chatbot",
  "/agent-intelligence-studio": "agent-intelligence-studio",
  "/detection-intelligence": "detection-intelligence",
  "/agent-memory": "agent-memory",
  "/agent-simulation-lab": "agent-simulation-lab",
  "/verdict-intelligence": "verdict-intelligence",
  "/inference-control": "inference-control",
  "/agent-configuration": "agent-configuration",
  "/governance-access": "governance-access",
  "/admin-guide": "admin-guide",
};

/**
 * Resolves a page slug (e.g. "telemetry-hub") or route path (e.g. "/telemetry-hub" or "/")
 * into a canonical NavigationPageId, or null if not registered.
 */
export function resolveNavigationPageId(identifier: string): NavigationPageId | null {
  if (!identifier) return null;
  const trimmed = identifier.trim();
  if (trimmed in NAVIGATION_ICON_METADATA) {
    return trimmed as NavigationPageId;
  }
  const cleanPath = trimmed.split("?")[0].split("#")[0].replace(/\/+$/, "") || "/";
  if (cleanPath in ROUTE_TO_PAGE_ID) {
    return ROUTE_TO_PAGE_ID[cleanPath];
  }
  const withoutLeadingSlash = cleanPath.replace(/^\//, "");
  if (withoutLeadingSlash in NAVIGATION_ICON_METADATA) {
    return withoutLeadingSlash as NavigationPageId;
  }
  return null;
}

/**
 * Returns the centralized semantic icon metadata for a given page ID or route.
 */
export function getNavigationIconMetadata(identifier: string): NavigationIconMetadata | null {
  const pageId = resolveNavigationPageId(identifier);
  return pageId ? NAVIGATION_ICON_METADATA[pageId] : null;
}

export interface SemanticIconCssVars {
  "--nav-icon-color": string;
  "--nav-icon-bg": string;
  "--nav-icon-bg-hover": string;
  "--nav-icon-bg-active": string;
  "--nav-icon-border": string;
  "--nav-icon-border-active": string;
}

const FALLBACK_CSS_VARS: SemanticIconCssVars = {
  "--nav-icon-color": "#CBD5E1",
  "--nav-icon-bg": "rgba(203, 213, 225, 0.1)",
  "--nav-icon-bg-hover": "rgba(203, 213, 225, 0.16)",
  "--nav-icon-bg-active": "rgba(203, 213, 225, 0.18)",
  "--nav-icon-border": "rgba(203, 213, 225, 0.16)",
  "--nav-icon-border-active": "rgba(203, 213, 225, 0.34)",
};

/**
 * Produces CSS custom properties for semantic icon coloring and subtle 8–12% opacity
 * tinted icon containers. Works identically under Obsidian Glass and Classic Slate themes.
 */
export function getSemanticIconCssVars(
  meta: NavigationIconMetadata | null
): SemanticIconCssVars {
  if (!meta) return FALLBACK_CSS_VARS;
  return {
    "--nav-icon-color": meta.color,
    "--nav-icon-bg": `rgba(${meta.rgb}, ${meta.tintOpacity})`,
    "--nav-icon-bg-hover": `rgba(${meta.rgb}, ${meta.hoverTintOpacity})`,
    "--nav-icon-bg-active": `rgba(${meta.rgb}, ${meta.activeTintOpacity})`,
    "--nav-icon-border": `rgba(${meta.rgb}, 0.16)`,
    "--nav-icon-border-active": `rgba(${meta.rgb}, 0.36)`,
  };
}
