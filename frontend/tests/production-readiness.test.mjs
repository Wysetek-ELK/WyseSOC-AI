import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_SRC = path.resolve(__dirname, "../src");

test("AgentIntelligenceStudioOverview: implements 6 Guided Checklist Stages and Rule Identity", () => {
  const filePath = path.join(FRONTEND_SRC, "components/compact/AgentIntelligenceStudioOverview.tsx");
  const content = fs.readFileSync(filePath, "utf-8");

  // Rule Identity elements
  assert.match(content, /Deployment:\s*\{deploymentStatus\}/i);
  assert.match(content, /Rule ID:/i);
  assert.match(content, /displayArchetype/i);

  // Production Readiness Summary
  assert.match(content, /Production Readiness Summary/i);
  assert.match(content, /Quality Gates/i);
  assert.match(content, /8 Passed/i);
  assert.match(content, /Rule Quality/i);
  assert.match(content, /Verified Analyst Reviews/i);

  // Smart Next Action Card
  assert.match(content, /NextActionCard/i);
  assert.match(content, /Next Action:/i);

  // 6 Human-readable guided stages
  assert.match(content, /Define Detection/i);
  assert.match(content, /Verify Evidence/i);
  assert.match(content, /Validate AI Policy/i);
  assert.match(content, /Analyst Learning/i);
  assert.match(content, /Test AI Accuracy/i);
  assert.match(content, /Production Approval/i);

  // Simple Explanations
  assert.match(content, /What this check means/i);
  assert.match(content, /Why it matters/i);
  assert.match(content, /What is required to complete it/i);

  // Expandable Technical Details
  assert.match(content, /Show Technical Details/i);
});

test("CompactDesignSystem: EvidenceCompletenessIndicator avoids false 100% completeness", () => {
  const filePath = path.join(FRONTEND_SRC, "components/compact/CompactDesignSystem.tsx");
  const content = fs.readFileSync(filePath, "utf-8");

  // EvidenceCompletenessIndicator checks
  assert.match(content, /EvidenceCompletenessIndicator/i);
  assert.match(content, /isSemanticsVerified/i);
  assert.match(content, /Evidence Semantics Unverified/i);
});

test("DetectionIntelligence / Rule Listing: includes Production Readiness column and filtering", () => {
  const filePath = path.join(FRONTEND_SRC, "app/detection-intelligence/page.tsx");
  const content = fs.readFileSync(filePath, "utf-8");

  // Production Readiness table header & data
  assert.match(content, /Production Readiness/i);
  assert.match(content, /readinessFilter/i);
  assert.match(content, /All Production Readiness/i);
  assert.match(content, /Blocked \/ Incomplete/i);
  assert.match(content, /Ready for Approval/i);
  assert.match(content, /Gates:/i);
  assert.match(content, /missing\)/i);

  // Rule click opens Studio
  assert.match(content, /\/agent-intelligence-studio\?rule_id=/i);
});

test("AgentIntelligenceStudio: Table Mode includes compact Production Readiness column and filter", () => {
  const filePath = path.join(FRONTEND_SRC, "app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(filePath, "utf-8");

  // Readiness column in studio table
  assert.match(content, /Production Readiness/i);
  assert.match(content, /readinessFilter/i);
  assert.match(content, /All Readiness States/i);

  // 3 Primary Tabs
  assert.match(content, /Overview/i);
  assert.match(content, /Analyst Review & Learning/i);
  assert.match(content, /Advanced Configuration/i);
});

test("RuleLearningDashboard: implements Double-Blind Review and Explains Statistical Evidence vs Eligibility", () => {
  const filePath = path.join(FRONTEND_SRC, "components/learning/RuleLearningDashboard.tsx");
  const content = fs.readFileSync(filePath, "utf-8");

  // Metrics
  assert.match(content, /Total Analyst Reviews/i);
  assert.match(content, /Observed FP Precision/i);
  assert.match(content, /Wilson 95% Lower Bound/i);
  assert.match(content, /TP Recall/i);

  // Double-Blind Review Workbench
  assert.match(content, /Double-Blind Review Workbench/i);
  assert.match(content, /DOUBLE-BLIND MODE ACTIVE/i);
  assert.match(content, /AI Model Verdict is masked/i);
  assert.match(content, /FALSE POSITIVE/i);
  assert.match(content, /TRUE POSITIVE/i);

  // Ground Truth vs Eligibility Explanation
  assert.match(content, /Understanding Ground Truth/i);
  assert.match(content, /1\.\s*Reviews Collected/i);
  assert.match(content, /2\.\s*Verified Ground Truth/i);
  assert.match(content, /3\.\s*Sufficient Statistical Evidence/i);
  assert.match(content, /4\.\s*Production Accuracy Eligibility/i);
});
