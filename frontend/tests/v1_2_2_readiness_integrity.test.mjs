import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_SRC = path.resolve(__dirname, "../src");

test("V1.2.2 Scenario 18: AgentIntelligenceStudioOverview renders decoupled 4-part lifecycle strip", () => {
  const overviewFile = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/compact/AgentIntelligenceStudioOverview.tsx"),
    "utf8"
  );

  // 1. Decoupled lifecycle strip container with testid
  assert.ok(
    overviewFile.includes('data-testid="ais-decoupled-lifecycle-strip"'),
    "Overview must render data-testid='ais-decoupled-lifecycle-strip'"
  );

  // 2. SIEM deployment status
  assert.ok(
    overviewFile.includes("SIEM Rule:") || overviewFile.includes("SIEM:"),
    "Must render explicit SIEM rule deployment status"
  );

  // 3. Candidate Policy status
  assert.ok(
    overviewFile.includes("Policy v") || overviewFile.includes("Selected Policy:"),
    "Must render explicit Policy version and status"
  );

  // 4. AI Execution status
  assert.ok(
    overviewFile.includes("AI Execution:"),
    "Must render explicit AI Execution status"
  );
  assert.ok(
    overviewFile.includes("aiVerdictExecutionStatus"),
    "Must bind aiVerdictExecutionStatus"
  );

  // 5. Current Readiness status
  assert.ok(
    overviewFile.includes("Current Readiness:"),
    "Must render explicit Current Readiness status"
  );
  assert.ok(
    overviewFile.includes("currentReadinessBadge.label"),
    "Must display authoritative readiness badge label"
  );
});

test("V1.2.2 Scenario 19 & 20: AppContext and AI Triage Workbench default Blind Review to ON and support unmasking", () => {
  const contextFile = fs.readFileSync(
    path.join(FRONTEND_SRC, "context/AppContext.tsx"),
    "utf8"
  );

  // 1. AppContext defaults blindReviewMode to true
  assert.ok(
    contextFile.includes("useState<boolean>(true)"),
    "AppContext must initialize blindReviewMode to true by default"
  );
  assert.ok(
    contextFile.includes('localStorage.getItem("ai_verdict_blind_review")'),
    "AppContext must check localStorage for stored blind review preference"
  );
  assert.ok(
    contextFile.includes('localStorage.setItem("ai_verdict_blind_review", "true")'),
    "AppContext must persist default true when unset"
  );

  const workbenchFile = fs.readFileSync(
    path.join(FRONTEND_SRC, "app/ai-triage-workbench/page.tsx"),
    "utf8"
  );

  // 2. Workbench renders [Hidden - Blind Review] badge when masked
  assert.ok(
    workbenchFile.includes("[Hidden - Blind Review]"),
    "Workbench table must display [Hidden - Blind Review] badge"
  );
  assert.ok(
    workbenchFile.includes("EyeOff"),
    "Workbench table must render EyeOff icon for masked verdict"
  );
});

test("V1.2.2 Scenario 21: Read-Only Viewer lockout enforced across Studio Overview actions", () => {
  const overviewFile = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/compact/AgentIntelligenceStudioOverview.tsx"),
    "utf8"
  );

  // 1. Synthesize Draft disabled for isViewer
  assert.ok(
    overviewFile.includes("disabled={actionLoading || isViewer}"),
    "Synthesize Draft must be disabled for Read-Only Viewers"
  );

  // 2. Quality validation disabled for isViewer
  assert.ok(
    overviewFile.includes("disabled={loadingQuality || isViewer}"),
    "Quality validation must be disabled for Read-Only Viewers"
  );

  // 3. Simulation disabled for isViewer
  assert.ok(
    overviewFile.includes("disabled={loadingSimulation || isViewer}"),
    "Simulation must be disabled for Read-Only Viewers"
  );

  // 4. Approval button disabled for isViewer
  assert.ok(
    overviewFile.includes("disabled={actionLoading || !effectiveApprovalEligible || isViewer}"),
    "Approve button must be disabled for Read-Only Viewers"
  );

  // 5. Stage 6 action button disabled for isViewer
  assert.ok(
    overviewFile.includes("disabled={stage.stage_id === \"production_approval\" ? (!effectiveApprovalEligible || isViewer) : false}"),
    "Stage 6 checklist action must be disabled for Read-Only Viewers"
  );
});

test("V1.2.2 Scenario 22: Readiness and checklist consistency guarantees", () => {
  const overviewFile = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/compact/AgentIntelligenceStudioOverview.tsx"),
    "utf8"
  );

  // 1. Authoritative binding: ai_execution_status from backend
  assert.ok(
    overviewFile.includes("readinessData?.ai_execution_status"),
    "Must read ai_execution_status from backend readiness response"
  );

  // 2. Authoritative binding: approval_eligible governs productionReadinessStatus
  assert.ok(
    overviewFile.includes("readinessData?.approval_eligible"),
    "productionReadinessStatus must be governed by backend approval_eligible"
  );

  // 3. View Requirements navigation
  assert.ok(
    overviewFile.includes('document.getElementById("guided-readiness-checklist")'),
    "View Requirements must scroll to guided-readiness-checklist"
  );
});
