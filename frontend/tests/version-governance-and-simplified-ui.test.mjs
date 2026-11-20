import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_SRC = path.resolve(__dirname, "../src");

test("Phase 2: Simplified UI 3 Primary Tabs and Workbenches", () => {
  const pagePath = path.join(FRONTEND_SRC, "app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  // Verify Primary 3 Tabs
  assert.ok(content.includes('data-testid="tab-overview"'), "Tab 1: Review Incidents button must exist");
  assert.ok(content.includes('Review Incidents'), "Tab 1 label must be Review Incidents");
  assert.ok(content.includes('data-testid="tab-test-ai"'), "Tab 2: Test AI button must exist");
  assert.ok(content.includes('Test AI'), "Tab 2 label must be Test AI");
  assert.ok(content.includes('data-testid="tab-learning"'), "Tab 3: Accuracy & Learning button must exist");
  assert.ok(content.includes('Accuracy & Learning'), "Tab 3 label must be Accuracy & Learning");
  assert.ok(content.includes('data-testid="tab-advanced"'), "Tab 4: Advanced Settings button must exist");
  assert.ok(content.includes('Advanced Settings'), "Tab 4 label must be Advanced Settings");

  // Verify Tab 1: ReviewIncidentsWorkbench integration
  assert.ok(content.includes("<ReviewIncidentsWorkbench"), "Must render ReviewIncidentsWorkbench in Tab 1");
  const reviewFile = fs.readFileSync(path.join(FRONTEND_SRC, "components/compact/ReviewIncidentsWorkbench.tsx"), "utf-8");
  assert.ok(reviewFile.includes("Double-Blind"), "ReviewIncidentsWorkbench must indicate Double-Blind review status");
  assert.ok(reviewFile.includes("TRUE_POSITIVE"), "Must provide TRUE_POSITIVE verdict option");
  assert.ok(reviewFile.includes("FALSE_POSITIVE"), "Must provide FALSE_POSITIVE verdict option");
  assert.ok(reviewFile.includes("INSUFFICIENT_EVIDENCE"), "Must provide INSUFFICIENT_EVIDENCE verdict option");
  assert.ok(reviewFile.includes("Submit Review"), "Must have Submit Review action");
  assert.ok(reviewFile.includes("Next Incident"), "Must have Next Incident action");

  // Verify Tab 2: AiTestWorkbench integration
  assert.ok(content.includes("<AiTestWorkbench"), "Must render AiTestWorkbench in Tab 2");
  const testFile = fs.readFileSync(path.join(FRONTEND_SRC, "components/compact/AiTestWorkbench.tsx"), "utf-8");
  assert.ok(testFile.includes("Qwen/Qwen2.5-7B-Instruct-AWQ"), "Must display active Local AWQ model");
  assert.ok(testFile.includes("Run Real AI Test"), "Must provide Run Real AI Test action");
  assert.ok(testFile.includes("Effective Verdict"), "Must display Effective Verdict");
  assert.ok(testFile.includes("Evidence Grounding"), "Must display Evidence Grounding percentage");
  assert.ok(testFile.includes("Token Usage"), "Must display token usage and telemetry");

  // Verify Tab 3: AccuracyLearningSummary integration
  assert.ok(content.includes("<AccuracyLearningSummary"), "Must render AccuracyLearningSummary in Tab 3");
  const accuracyFile = fs.readFileSync(path.join(FRONTEND_SRC, "components/compact/AccuracyLearningSummary.tsx"), "utf-8");
  assert.ok(accuracyFile.includes("Accuracy: NOT MEASURABLE"), "Must state Accuracy: NOT MEASURABLE when unverified");
  assert.ok(accuracyFile.includes("Begin Independent Analyst Reviews"), "Must recommend starting reviews when unverified");
  assert.ok(accuracyFile.includes("TP Recall"), "Must display TP Recall metric");
  assert.ok(accuracyFile.includes("FP Precision"), "Must display FP Precision metric");
  assert.ok(accuracyFile.includes("Confusion Matrix"), "Must provide Confusion Matrix when ground truth exists");
});

test("Phase 3: Simplified Rule Header, Decoupled Statuses, and Authoritative Next Recommended Action", () => {
  const pagePath = path.join(FRONTEND_SRC, "app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  // Rule Header decoupled statuses
  assert.ok(content.includes("SIEM Active"), "Header must include SIEM Active badge");
  assert.ok(content.includes("No Active Version") || content.includes("Approved"), "Header must show active approved version");
  assert.ok(content.includes("Draft"), "Header must show candidate draft version");
  assert.ok(content.includes("Supervised Learning") || content.includes("Learning"), "Header must show learning stage");

  // Next Recommended Action Banner
  assert.ok(content.includes("Next Recommended Action:"), "Must render Next Recommended Action banner");
  assert.ok(content.includes("Create Draft Policy"), "Must support 'Create Draft Policy' action");
  assert.ok(content.includes("Validate Draft Policy"), "Must support 'Validate Draft Policy' action");
  assert.ok(content.includes("Inspect Validation Issues"), "Must support 'Inspect Validation Issues' action");
  assert.ok(content.includes("Start Analyst Review"), "Must support 'Start Analyst Review' action");
  assert.ok(content.includes("Evaluate Accuracy"), "Must support 'Evaluate Accuracy' action");
  assert.ok(content.includes("Request Administrator Approval"), "Must support 'Request Administrator Approval' action");
  assert.ok(content.includes("Run AI Simulation / Verification"), "Must support 'Run AI Simulation / Verification' action");
});

test("Phase 4: Advanced Settings 9 Modular Sections", () => {
  const pagePath = path.join(FRONTEND_SRC, "app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  assert.ok(content.includes("1. Investigation Policy"), "Module 1: Investigation Policy must exist");
  assert.ok(content.includes("2. Quality Gates"), "Module 2: Quality Gates must exist");
  assert.ok(content.includes("3. Evidence Contract"), "Module 3: Evidence Contract must exist");
  assert.ok(content.includes("4. Rule XML & Logic"), "Module 4: Rule XML & Logic must exist");
  assert.ok(content.includes("5. Prompt Inspector"), "Module 5: Prompt Inspector must exist");
  assert.ok(content.includes("6. Model Diagnostics"), "Module 6: Model Diagnostics must exist");
  assert.ok(content.includes("7. Simulation History"), "Module 7: Simulation History must exist");
  assert.ok(content.includes("8. Production Governance"), "Module 8: Production Governance must exist");
  assert.ok(content.includes("9. Manage Versions"), "Module 9: Manage Versions must exist");
});

test("Phase 5: Manage Version History Governance & Safe Deletion Invariants", () => {
  const compPath = path.join(FRONTEND_SRC, "components/compact/ManageVersionHistory.tsx");
  const content = fs.readFileSync(compPath, "utf-8");

  // Invariants: Active & Approved version protection
  assert.ok(content.includes("Protected from deletion"), "Protected versions must be marked protected");
  assert.ok(content.includes("Permanent Deletion Strictly Prohibited"), "Must explain active deletion prohibition");
  assert.ok(content.includes("Active policy cannot be archived"), "Must prohibit archival of active policy");

  // Invariants: Deletion preview and typed confirmation
  assert.ok(content.includes("Deletion Impact Preview"), "Must present deletion impact preview modal");
  assert.ok(content.includes("DELETE v"), "Must require typed confirmation DELETE v{N} for individual deletion");
  assert.ok(content.includes("PERMANENTLY DELETE"), "Must require typed confirmation PERMANENTLY DELETE for bulk cleanup");

  // Invariants: Safe API client bindings
  const apiPath = path.join(FRONTEND_SRC, "lib/api.ts");
  const apiContent = fs.readFileSync(apiPath, "utf-8");
  assert.ok(apiContent.includes("getRuleVersionHistory"), "Must export getRuleVersionHistory");
  assert.ok(apiContent.includes("getVersionDeletionPreview"), "Must export getVersionDeletionPreview");
  assert.ok(apiContent.includes("deletePromptVersion"), "Must export deletePromptVersion");
  assert.ok(apiContent.includes("archivePromptVersion"), "Must export archivePromptVersion");
  assert.ok(apiContent.includes("restorePromptVersion"), "Must export restorePromptVersion");
  assert.ok(apiContent.includes("bulkDeletePromptVersions"), "Must export bulkDeletePromptVersions");

  // Invariants: RBAC viewer lockout
  assert.ok(content.includes("isViewer"), "Must enforce viewer check");
  assert.ok(content.includes("Viewer Lockout") || content.includes("Read-Only Viewer"), "Must explain viewer restrictions");

  // Invariants: Compact table layout headers
  assert.ok(content.includes(">Version</th>"), "Must display Version column header");
  assert.ok(content.includes(">Status</th>"), "Must display Status column header");
  assert.ok(content.includes(">Created</th>"), "Must display Created column header");
  assert.ok(content.includes(">Usage</th>"), "Must display Usage column header");
  assert.ok(content.includes(">Actions</th>"), "Must display Actions column header");

  // Invariants: Specific deletion protection tooltips
  assert.ok(content.includes("Deletion unavailable — historical approved policy"), "Must display historical approved tooltip");
  assert.ok(content.includes("Deletion unavailable — active policy version"), "Must display active policy tooltip");
  assert.ok(content.includes("Deletion unavailable — referenced by inference history"), "Must display inference history reference tooltip");
});
