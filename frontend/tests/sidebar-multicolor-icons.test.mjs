import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  NAVIGATION_GROUP_ORDER,
  NAVIGATION_ICON_METADATA,
  NAVIGATION_PAGE_IDS,
  ROUTE_TO_PAGE_ID,
  getNavigationIconMetadata,
  getSemanticIconCssVars,
  resolveNavigationPageId,
} from "../src/config/navigationIcons.ts";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_SRC = path.resolve(__dirname, "../src");

const EXPECTED_SPECS = [
  {
    id: "agent-mission-control",
    title: "Agent Mission Control",
    href: "/agent-mission-control",
    groupTitle: "SOC OPERATIONS",
    iconName: "layout-dashboard",
    componentName: "LayoutDashboard",
    color: "#38BDF8",
  },
  {
    id: "ai-triage-workbench",
    title: "AI Triage Workbench",
    href: "/ai-triage-workbench",
    groupTitle: "SOC OPERATIONS",
    iconName: "shield-alert",
    componentName: "ShieldAlert",
    color: "#FB923C",
  },
  {
    id: "telemetry-hub",
    title: "Telemetry Hub",
    href: "/telemetry-hub",
    groupTitle: "SOC OPERATIONS",
    iconName: "radio-tower",
    componentName: "RadioTower",
    color: "#22D3EE",
  },
  {
    id: "human-review-queue",
    title: "Human Review Queue",
    href: "/human-review-queue",
    groupTitle: "SOC OPERATIONS",
    iconName: "user-round-check",
    componentName: "UserRoundCheck",
    color: "#4ADE80",
  },
  {
    id: "soc-chatbot",
    title: "Verdictum Sentinel",
    href: "/soc-chatbot",
    groupTitle: "SOC OPERATIONS",
    iconName: "bot",
    componentName: "Bot",
    color: "#A78BFA",
  },
  {
    id: "agent-intelligence-studio",
    title: "Agent Intelligence Studio",
    href: "/agent-intelligence-studio",
    groupTitle: "AGENT INTELLIGENCE",
    iconName: "brain-circuit",
    componentName: "BrainCircuit",
    color: "#C084FC",
  },
  {
    id: "detection-intelligence",
    title: "Detection Intelligence",
    href: "/detection-intelligence",
    groupTitle: "AGENT INTELLIGENCE",
    iconName: "radar",
    componentName: "Radar",
    color: "#FBBF24",
  },
  {
    id: "agent-memory",
    title: "Agent Memory",
    href: "/agent-memory",
    groupTitle: "AGENT INTELLIGENCE",
    iconName: "database",
    componentName: "Database",
    color: "#818CF8",
  },
  {
    id: "agent-simulation-lab",
    title: "Agent Simulation Lab",
    href: "/agent-simulation-lab",
    groupTitle: "VALIDATION & TRUST",
    iconName: "flask-conical",
    componentName: "FlaskConical",
    color: "#FB923C",
  },
  {
    id: "verdict-intelligence",
    title: "Verdict Intelligence",
    href: "/verdict-intelligence",
    groupTitle: "VALIDATION & TRUST",
    iconName: "chart-no-axes-combined",
    componentName: "ChartNoAxesCombined",
    color: "#2DD4BF",
  },
  {
    id: "inference-control",
    title: "Inference Control",
    href: "/inference-control",
    groupTitle: "PLATFORM CONTROL",
    iconName: "server-cog",
    componentName: "ServerCog",
    color: "#60A5FA",
  },
  {
    id: "agent-configuration",
    title: "Agent Configuration",
    href: "/agent-configuration",
    groupTitle: "PLATFORM CONTROL",
    iconName: "sliders-horizontal",
    componentName: "SlidersHorizontal",
    color: "#CBD5E1",
  },
  {
    id: "governance-access",
    title: "Governance & Access",
    href: "/governance-access",
    groupTitle: "PLATFORM CONTROL",
    iconName: "shield-check",
    componentName: "ShieldCheck",
    color: "#4ADE80",
  },
  {
    id: "admin-guide",
    title: "Verdictum AI Admin Guide",
    href: "/admin-guide",
    groupTitle: "PLATFORM CONTROL",
    iconName: "book-open-text",
    componentName: "BookOpenText",
    color: "#FBBF24",
  },
];

function hexToRelativeLuminance(hex) {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16) / 255;
  const g = parseInt(clean.slice(2, 4), 16) / 255;
  const b = parseInt(clean.slice(4, 6), 16) / 255;
  const linear = [r, g, b].map((c) =>
    c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
  );
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}

function contrastRatio(hex1, hex2) {
  const l1 = hexToRelativeLuminance(hex1);
  const l2 = hexToRelativeLuminance(hex2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

test("Centralized navigation icon registry maps all 14 sidebar pages with exact semantic icons and colors", () => {
  assert.equal(NAVIGATION_PAGE_IDS.length, 14);
  assert.deepEqual([...NAVIGATION_GROUP_ORDER], [
    "SOC OPERATIONS",
    "AGENT INTELLIGENCE",
    "VALIDATION & TRUST",
    "PLATFORM CONTROL",
  ]);

  for (const spec of EXPECTED_SPECS) {
    const meta = NAVIGATION_ICON_METADATA[spec.id];
    assert.ok(meta, `Missing navigation metadata for ${spec.id}`);
    assert.equal(meta.title, spec.title);
    assert.equal(meta.href, spec.href);
    assert.equal(meta.groupTitle, spec.groupTitle);
    assert.equal(meta.iconName, spec.iconName);
    assert.equal(meta.componentName, spec.componentName);
    assert.equal(meta.color, spec.color);
    assert.ok(
      meta.tintOpacity >= 0.08 && meta.tintOpacity <= 0.12,
      `Tint opacity for ${spec.id} must be within 8–12% (got ${meta.tintOpacity})`
    );

    const routeFile = path.join(FRONTEND_SRC, "app", spec.id, "page.tsx");
    assert.ok(fs.existsSync(routeFile), `Expected Next.js route file at ${routeFile}`);
  }
});

test("Navigation icon resolvers handle slugs, routes, root '/', query strings, and unknown fallbacks", () => {
  assert.equal(resolveNavigationPageId("/"), "agent-mission-control");
  assert.equal(ROUTE_TO_PAGE_ID["/"], "agent-mission-control");
  assert.equal(resolveNavigationPageId("/telemetry-hub"), "telemetry-hub");
  assert.equal(resolveNavigationPageId("/ai-triage-workbench?search=ssh"), "ai-triage-workbench");
  assert.equal(resolveNavigationPageId("admin-guide"), "admin-guide");
  assert.equal(resolveNavigationPageId("non-existent-route"), null);

  const meta = getNavigationIconMetadata("/verdict-intelligence");
  assert.ok(meta);
  assert.equal(meta.color, "#2DD4BF");

  const vars = getSemanticIconCssVars(meta);
  assert.equal(vars["--nav-icon-color"], "#2DD4BF");
  assert.match(vars["--nav-icon-bg"], /^rgba\(45, 212, 191, 0\.1\)$/);

  const fallbackVars = getSemanticIconCssVars(null);
  assert.equal(fallbackVars["--nav-icon-color"], "#CBD5E1");
});

test("All 14 semantic icon colors meet WCAG AA non-text contrast (>= 3.0:1) on Obsidian dark sidebar", () => {
  const obsidianSidebarBg = "#121015";
  const classicSidebarBg = "#020617";

  for (const spec of EXPECTED_SPECS) {
    const obsidianContrast = contrastRatio(spec.color, obsidianSidebarBg);
    const classicContrast = contrastRatio(spec.color, classicSidebarBg);
    assert.ok(
      obsidianContrast >= 4.5,
      `${spec.id} (${spec.color}) Obsidian contrast too low: ${obsidianContrast.toFixed(2)}`
    );
    assert.ok(
      classicContrast >= 4.5,
      `${spec.id} (${spec.color}) Classic contrast too low: ${classicContrast.toFixed(2)}`
    );
  }
});

test("NavigationIcon component centralizes all 14 Lucide icons with 18px expanded and 20px collapsed sizing", () => {
  const navIconSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/navigation/NavigationIcon.tsx"),
    "utf-8"
  );

  for (const spec of EXPECTED_SPECS) {
    assert.match(
      navIconSrc,
      new RegExp(`"${spec.id}":\\s*${spec.componentName}\\b`),
      `NavigationIcon.tsx must bind "${spec.id}" to ${spec.componentName}`
    );
  }

  assert.match(navIconSrc, /expanded:\s*\{[\s\S]*?iconPx:\s*18/);
  assert.match(navIconSrc, /collapsed:\s*\{[\s\S]*?iconPx:\s*20/);
  assert.match(navIconSrc, /aria-hidden="true"/);
  assert.match(navIconSrc, /nav-icon-badge/);
});

test("Main Sidebar uses centralized NavigationIcon without duplicated icon mappings and preserves structure/accessibility", () => {
  const sidebarSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/layout/Sidebar.tsx"),
    "utf-8"
  );

  assert.match(sidebarSrc, /import \{ NavigationIcon \} from "@\/components\/navigation\/NavigationIcon"/);
  assert.match(sidebarSrc, /<NavigationIcon[\s\S]*?size=\{collapsed \? "collapsed" : "expanded"\}/);
  assert.doesNotMatch(sidebarSrc, /LayoutDashboard|AlertTriangle|UploadCloud|MessageSquareCode/);

  // Preserves all 4 categories and all 14 routes/titles
  for (const group of NAVIGATION_GROUP_ORDER) {
    assert.ok(sidebarSrc.includes(group), `Sidebar missing group ${group}`);
  }
  for (const spec of EXPECTED_SPECS) {
    assert.ok(sidebarSrc.includes(`"${spec.href}"`), `Sidebar missing route ${spec.href}`);
    assert.ok(sidebarSrc.includes(`"${spec.title}"`), `Sidebar missing title ${spec.title}`);
  }

  // Preserves expanded/collapsed widths, tooltips, ARIA attributes, and reduced-motion support
  assert.match(sidebarSrc, /collapsed \? "w-14" : "w-60"/);
  assert.match(sidebarSrc, /title=\{collapsed \? item\.title : undefined\}/);
  assert.match(sidebarSrc, /aria-current=\{active \? "page" : undefined\}/);
  assert.match(sidebarSrc, /aria-expanded=\{!collapsed\}/);
  assert.match(sidebarSrc, /motion-reduce:transition-none/);
  assert.match(sidebarSrc, /data-testid="sidebar-inference-widget"/);
});

test("Admin Guide removes duplicated ICON_MAP and reuses centralized NavigationIcon across page references", () => {
  const readerSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/admin-guide/AdminGuideInteractiveReader.tsx"),
    "utf-8"
  );
  const glossarySrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/admin-guide/GlossaryTroubleshootingSection.tsx"),
    "utf-8"
  );
  const tourSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/admin-guide/GuidedTourSection.tsx"),
    "utf-8"
  );
  const guidePageSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "app/admin-guide/page.tsx"),
    "utf-8"
  );

  assert.doesNotMatch(readerSrc, /const ICON_MAP/);
  assert.match(readerSrc, /import \{ NavigationIcon \} from "@\/components\/navigation\/NavigationIcon"/);
  assert.match(readerSrc, /<NavigationIcon pageId=\{page\.slug\} size="compact" active=\{isSelected\}/);
  assert.match(readerSrc, /<NavigationIcon pageId=\{currentPage\.slug\} size="expanded" active \/>/);
  assert.match(readerSrc, /<NavigationIcon pageId=\{rel\.route\} size="xs" withContainer=\{false\} \/>/);
  assert.match(readerSrc, /overflow-x-hidden/);
  assert.match(readerSrc, /aria-current=/);

  assert.match(glossarySrc, /<NavigationIcon pageId=\{page\.href\} size="compact" \/>/);
  assert.match(tourSrc, /<NavigationIcon pageId=\{lnk\.href\} size="xs" withContainer=\{false\} \/>/);
  assert.match(guidePageSrc, /<NavigationIcon pageId=\{p\.href\} size="xs" withContainer=\{false\} \/>/);
});

test("Global CSS preserves Obsidian & Classic themes, active indicator, semantic icon badge styling, focus rings, and reduced motion", () => {
  const cssSrc = fs.readFileSync(path.join(FRONTEND_SRC, "app/globals.css"), "utf-8");

  assert.match(cssSrc, /html:not\(\[data-theme="classic"\]\)/);
  assert.match(cssSrc, /html\[data-theme="classic"\]/);
  assert.match(cssSrc, /\.theme-nav-active::before/);
  assert.match(cssSrc, /\.nav-icon-badge\s*\{/);
  assert.match(cssSrc, /\.nav-icon-badge-active\s*\{/);
  assert.match(cssSrc, /html\[data-theme="classic"\]\s*:focus-visible/);
  assert.match(cssSrc, /@media \(prefers-reduced-motion: reduce\)[\s\S]*?\.nav-icon-badge/);
});
