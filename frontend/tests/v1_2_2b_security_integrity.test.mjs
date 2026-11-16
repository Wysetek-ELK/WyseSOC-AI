import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test("V1.2.2b Scenario 01: Agent Intelligence Studio renders Active Policy v{version} badge", () => {
  const studioFile = path.resolve(__dirname, "../src/app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(studioFile, "utf-8");

  // Must not have ambiguous "Production Active"
  assert.ok(!content.includes('<CheckCircle2 className="w-3 h-3" /> Production Active'), "Must replace ambiguous 'Production Active' badge");
  assert.ok(content.includes("Active Policy v{selectedVersion.version_number}"), "Must render 'Active Policy v{selectedVersion.version_number}'");
});

test("V1.2.2b Scenario 02: Detection Intelligence renders SIEM Status column and SIEM ACTIVE badge", () => {
  const detFile = path.resolve(__dirname, "../src/app/detection-intelligence/page.tsx");
  const content = fs.readFileSync(detFile, "utf-8");

  assert.ok(content.includes("SIEM Status"), "Must label column as SIEM Status instead of Baseline Status");
  assert.ok(content.includes("SIEM ACTIVE"), "Must label active rules as SIEM ACTIVE");
});

test("V1.2.2b Scenario 03: AgentIntelligenceStudioOverview decouples SIEM Rule, Policy Version, and Readiness", () => {
  const overviewFile = path.resolve(__dirname, "../src/components/compact/AgentIntelligenceStudioOverview.tsx");
  const content = fs.readFileSync(overviewFile, "utf-8");

  assert.ok(content.includes("SIEM Rule Deployment Status") || content.includes("SIEM Rule:"), "Must explicitly present SIEM Rule status");
  assert.ok(content.includes("Policy v") || content.includes("Active Policy:"), "Must explicitly present Policy Version status");
  assert.ok(content.includes("AI Execution Status") || content.includes("AI Execution:"), "Must explicitly present AI Execution status");
});
