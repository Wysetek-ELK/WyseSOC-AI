import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

test("V1.2: Agent Intelligence Studio renders 3 primary tabs and 6 readiness stages", () => {
  const overviewFile = fs.readFileSync(
    path.resolve("src/components/compact/AgentIntelligenceStudioOverview.tsx"),
    "utf8"
  );

  // 1. Six guided stages
  const requiredStages = [
    "define_detection",
    "verify_evidence",
    "validate_policy",
    "analyst_learning",
    "test_accuracy",
    "production_approval",
  ];
  for (const stage of requiredStages) {
    assert.ok(
      overviewFile.includes(stage),
      `Overview component must define stage '${stage}'`
    );
  }

  // 2. Candidate vs Active decoupled governance
  assert.ok(overviewFile.includes("selectedPolicyLabel"), "Must define selectedPolicyLabel");
  assert.ok(overviewFile.includes("activePolicyLabel"), "Must define activePolicyLabel");
  assert.ok(overviewFile.includes("aiVerdictExecutionStatus"), "Must define aiVerdictExecutionStatus");
  assert.ok(overviewFile.includes("productionReadinessStatus"), "Must define productionReadinessStatus");

  // 3. Navigation between tabs
  assert.ok(overviewFile.includes("onNavigateTab"), "Must support onNavigateTab callback");
});

test("V1.2: Rule Detail navigation via URL parameters rule_id and tab", () => {
  const pageFile = fs.readFileSync(
    path.resolve("src/app/agent-intelligence-studio/page.tsx"),
    "utf8"
  );

  // Checks URL query parameters initialization
  assert.ok(pageFile.includes("rule_id") && pageFile.includes("ruleId"), "Must support rule_id and ruleId query params");
  assert.ok(pageFile.includes("setViewMode(\"studio\")"), "Must set viewMode to studio when ruleId is present");
  assert.ok(pageFile.includes("primaryTab"), "Must manage primaryTab state");
  assert.ok(pageFile.includes("handleOpenStudioForRule"), "Must provide handleOpenStudioForRule handler");
});

test("V1.2: AI Triage Workbench toolbar has no redundant Blind Review button but preserves global toggle", () => {
  const workbenchFile = fs.readFileSync(
    path.resolve("src/app/ai-triage-workbench/page.tsx"),
    "utf8"
  );
  const headerFile = fs.readFileSync(
    path.resolve("src/components/layout/Header.tsx"),
    "utf8"
  );

  // Workbench toolbar should NOT contain the duplicate toggle button
  assert.ok(
    !workbenchFile.includes("toggleBlindReviewMode"),
    "Workbench toolbar must not duplicate toggleBlindReviewMode button"
  );

  // Global Header MUST contain the canonical toggle
  assert.ok(
    headerFile.includes("setBlindReviewMode") && headerFile.includes("Blind Review Mode Toggle"),
    "Global Header must contain the authoritative setBlindReviewMode control"
  );
  assert.ok(
    !workbenchFile.includes("Blind Review: ON") && !workbenchFile.includes("Blind Review: OFF"),
    "Workbench toolbar must not duplicate Blind Review toggle button"
  );

  // Workbench MUST maintain the active warning banner when blind review is active
  assert.ok(
    workbenchFile.includes("Blind Review Active") || workbenchFile.includes("Ground-truth labels masked"),
    "Workbench must render the ground-truth masking banner when active"
  );
});

test("V1.2: Sticky table action columns and zero-overflow layout rules preserved", () => {
  const studioFile = fs.readFileSync(
    path.resolve("src/app/agent-intelligence-studio/page.tsx"),
    "utf8"
  );
  const workbenchFile = fs.readFileSync(
    path.resolve("src/app/ai-triage-workbench/page.tsx"),
    "utf8"
  );
  const globalsCss = fs.readFileSync(
    path.resolve("src/app/globals.css"),
    "utf8"
  );

  assert.ok(studioFile.includes("sticky right-0"), "AIS table must have sticky right action column");
  assert.ok(workbenchFile.includes("sticky right-0"), "Workbench table must have sticky right action column");
  assert.ok(globalsCss.includes("vcds-sticky-action-col"), "Globals CSS must define vcds-sticky-action-col token");
});
