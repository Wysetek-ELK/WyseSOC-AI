import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_SRC = path.resolve(__dirname, "../src");

test("VCDS 1.0: Global CSS establishes compact design tokens and utilities", () => {
  const cssPath = path.join(FRONTEND_SRC, "app/globals.css");
  const content = fs.readFileSync(cssPath, "utf-8");

  assert.match(content, /\.vcds-card/, "globals.css must define .vcds-card utility");
  assert.match(content, /\.vcds-panel/, "globals.css must define .vcds-panel utility");
  assert.match(content, /\.vcds-sticky-action-col/, "globals.css must define .vcds-sticky-action-col");
  assert.match(content, /--vcds-font-sans/, "globals.css must declare font tokens");
  assert.match(content, /--vcds-space-/, "globals.css must declare 4px-grid spacing tokens");
  assert.doesNotMatch(content, /p-4 sm:p-6 lg:p-8 !important/, "No brute-force !important overrides");
});

test("VCDS 1.0: CompactPageHeader supports wrapping and non-clipped titles", () => {
  const compPath = path.join(FRONTEND_SRC, "components/compact/CompactDesignSystem.tsx");
  const content = fs.readFileSync(compPath, "utf-8");

  assert.match(content, /CompactPageHeader/, "Must export CompactPageHeader");
  assert.match(content, /break-words/, "Title must allow natural word wrapping");
  assert.match(content, /CompactRuleScopeBar/, "Must export CompactRuleScopeBar");
  assert.match(content, /data-testid="multi-rule-search-warning"/, "Must preserve multi-rule test id");
  assert.match(content, /data-testid="exact-rule-filter-banner"/, "Must preserve exact rule test id");
});

test("VCDS 1.0: Agent Intelligence Studio implements decoupled header and 12-col grid", () => {
  const aisCompPath = path.join(FRONTEND_SRC, "components/compact/AgentIntelligenceStudioOverview.tsx");
  const content = fs.readFileSync(aisCompPath, "utf-8");

  assert.match(content, /lg:col-span-8/, "Must implement 8-column primary workflow area");
  assert.match(content, /lg:col-span-4/, "Must implement 4-column context & governance sidebar");
  assert.match(content, /Synthesize Draft/, "Must preserve Synthesize Draft action");
  assert.match(content, /Validate Quality/, "Must preserve Validate Quality action");
  assert.match(content, /View Actual LLM Prompt/, "Must preserve View Actual LLM Prompt action");
  assert.match(content, /CompactVersionSelector/, "Must preserve Version Selector");
});

test("VCDS 1.0: Telemetry Hub implements 4-Card KPI row and dual-column workspace", () => {
  const thPath = path.join(FRONTEND_SRC, "app/telemetry-hub/page.tsx");
  const content = fs.readFileSync(thPath, "utf-8");

  assert.match(content, /Continuous Poller/, "Must display Continuous Poller KPI");
  assert.match(content, /Total Pulled/, "Must display Total Pulled KPI");
  assert.match(content, /AI Verdicts/, "Must display AI Verdicts KPI");
  assert.match(content, /Local LLM Engine/, "Must display Local LLM Engine KPI");
  assert.match(content, /lg:col-span-7/, "Must implement 7-col ingest worker column");
  assert.match(content, /lg:col-span-5/, "Must implement 5-col on-demand column");
  assert.match(content, /onDemandTab/, "Must support tabbed on-demand ingestion");
  assert.match(content, /historyTab/, "Must support tabbed history inspection");
});

test("VCDS 1.0: AI Triage Workbench integrates CompactRuleScopeBar and sticky action column", () => {
  const atwPath = path.join(FRONTEND_SRC, "app/ai-triage-workbench/page.tsx");
  const content = fs.readFileSync(atwPath, "utf-8");

  assert.match(content, /CompactRuleScopeBar/, "Must render CompactRuleScopeBar");
  assert.match(content, /sticky right-0/, "Must make action column sticky right");
});

test("VCDS 1.0: Action columns across operational tables are sticky right", () => {
  const aisTablePath = path.join(FRONTEND_SRC, "app/agent-intelligence-studio/page.tsx");
  const aisContent = fs.readFileSync(aisTablePath, "utf-8");
  assert.match(aisContent, /sticky right-0.*Action/, "AIS table header must be sticky right");

  const hrqPath = path.join(FRONTEND_SRC, "app/human-review-queue/page.tsx");
  const hrqContent = fs.readFileSync(hrqPath, "utf-8");
  assert.match(hrqContent, /sticky right-0.*Action/, "HRQ table header must be sticky right");

  const detPath = path.join(FRONTEND_SRC, "app/detection-intelligence/page.tsx");
  const detContent = fs.readFileSync(detPath, "utf-8");
  assert.match(detContent, /sticky right-0.*Action/, "Detection Intelligence table header must be sticky right");
});
