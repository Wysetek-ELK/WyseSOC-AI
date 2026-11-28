import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

test("AIS 3.2 API Client: exports ais32Api methods cleanly", () => {
  const apiContent = fs.readFileSync(path.resolve("src/lib/api.ts"), "utf-8");
  for (const method of [
    "getOverview",
    "getArchetypes",
    "getSemantics",
    "listContracts",
    "getContractDetail",
    "saveContract",
    "getOrgContextTypes",
    "listOrgContext",
    "createOrgContext",
    "decideOrgContext",
    "evaluateRun",
    "getAis33Readiness",
  ]) {
    assert.ok(apiContent.includes(method), `ais32Api missing method ${method}`);
  }
});

test("AIS 3.2 Intelligence Panel: Overview, Rule Intelligence drawer, Org Context, and Mode A vs Mode B metrics", () => {
  const panelContent = fs.readFileSync(path.resolve("src/components/compact/Ais32IntelligencePanel.tsx"), "utf-8");
  assert.match(panelContent, /AIS 3\.2 Universal Rule Intelligence Overview/);
  assert.match(panelContent, /Dynamic Rule Contract Inspector/);
  assert.match(panelContent, /Verified Organizational Context Registry/);
  assert.match(panelContent, /Internal IP != authorized; absent context = UNKNOWN/);
  assert.match(panelContent, /Mode A .* Neutral Baseline/);
  assert.match(panelContent, /Mode B .* Universal Rule-Aware Engine/);
  assert.match(panelContent, /Validated App/);
  assert.match(panelContent, /Effective Op/);
  assert.match(panelContent, /AIS 3\.3 Fresh Holdout Target/);
});

test("Agent Intelligence Studio: integrates AIS 3.2 without duplicate View Actual LLM Prompt button labels", () => {
  const studioContent = fs.readFileSync(path.resolve("src/app/agent-intelligence-studio/page.tsx"), "utf-8");
  assert.match(studioContent, /<Ais32IntelligencePanel[\s\S]*variant="overview"/);
  assert.match(studioContent, /<Ais32IntelligencePanel[\s\S]*variant="accuracy"/);

  // Ensure button label "View Actual LLM Prompt" appears at most once outside comments/attributes
  const matches = studioContent.match(/>\s*View Actual LLM Prompt\s*</g) || [];
  const rawLabelLines = studioContent
    .split(/\r?\n/)
    .filter((l) => l.includes("View Actual LLM Prompt") && !l.includes("title=") && !l.includes("{/*"));
  assert.ok(rawLabelLines.length <= 1 && matches.length <= 1, `Duplicate 'View Actual LLM Prompt' buttons found: ${rawLabelLines.length}`);
});

test("Incident Detail Workbench: discloses uncalibrated score & avoids duplicate prompt buttons", () => {
  const incContent = fs.readFileSync(path.resolve("src/app/ai-triage-workbench/[id]/page.tsx"), "utf-8");
  assert.match(incContent, /\(Uncalibrated\)/);
  assert.match(incContent, /CALIBRATION|NOT_CALIBRATED/i);
  const btnMatches = incContent.match(/<span>View Actual LLM Prompt<\/span>/g) || [];
  assert.equal(btnMatches.length, 1, "Incident detail page must render exactly one View Actual LLM Prompt button");
});
