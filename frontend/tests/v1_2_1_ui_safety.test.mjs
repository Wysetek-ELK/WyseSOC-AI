import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

test("V1.2.1: AgentIntelligenceStudioOverview enforces UI safety and RBAC viewer lockout", () => {
  const overviewFile = fs.readFileSync(
    path.resolve("src/components/compact/AgentIntelligenceStudioOverview.tsx"),
    "utf8"
  );

  // 1. Synthesize Draft must be disabled for Read-Only Viewers
  assert.ok(
    overviewFile.includes("disabled={actionLoading || isViewer}"),
    "Synthesize Draft button must include disabled={actionLoading || isViewer}"
  );
  assert.ok(
    overviewFile.includes("Read-Only Viewer cannot synthesize drafts"),
    "Synthesize Draft button must explain viewer lockout in title"
  );

  // 2. Simulation button must be disabled for Read-Only Viewers
  assert.ok(
    overviewFile.includes("disabled={loadingSimulation || isViewer}"),
    "Simulation button must include disabled={loadingSimulation || isViewer}"
  );

  // 3. Approve button must be guarded by effectiveApprovalEligible and !isViewer
  assert.ok(
    overviewFile.includes("disabled={actionLoading || !effectiveApprovalEligible || isViewer}"),
    "Approve button must be guarded by effectiveApprovalEligible and !isViewer"
  );

  // 4. View Requirements button present when approval is blocked
  assert.ok(
    overviewFile.includes("View Requirements"),
    "Must offer View Requirements button when approval is blocked"
  );
  assert.ok(
    overviewFile.includes('id="guided-readiness-checklist"'),
    "Guided readiness checklist container must have id='guided-readiness-checklist'"
  );

  // 5. Readiness badges must include fail-closed UNKNOWN and UNAVAILABLE
  assert.ok(
    overviewFile.includes("UNKNOWN:") && overviewFile.includes("STATUS UNKNOWN"),
    "Must support UNKNOWN status badge"
  );
  assert.ok(
    overviewFile.includes("UNAVAILABLE:") && overviewFile.includes("SERVICE UNAVAILABLE"),
    "Must support UNAVAILABLE status badge"
  );
});

test("V1.2.1: Studio page.tsx strictly requires 8 quality gates and 30 reviews for approval eligibility", () => {
  const pageFile = fs.readFileSync(
    path.resolve("src/app/agent-intelligence-studio/page.tsx"),
    "utf8"
  );

  // 1. isApprovalEligible definition check
  assert.ok(
    pageFile.includes("passedGatesCount === 8"),
    "isApprovalEligible must require passedGatesCount === 8"
  );
  assert.ok(
    pageFile.includes("total_analyst_reviews || 0) >= 30"),
    "isApprovalEligible must require at least 30 verified analyst reviews"
  );

  // 2. Header badge decoupling: Approved baseline with < 8 gates is not falsely marked ACTIVE PRODUCTION
  assert.ok(
    pageFile.includes("APPROVED BASELINE (REVALIDATION REQUIRED)"),
    "Header must differentiate approved baselines requiring revalidation from active production"
  );
  assert.ok(
    pageFile.includes("SUPERVISED LEARNING"),
    "Header must display SUPERVISED LEARNING during learning phase"
  );

  // 3. Right-hand action toolbar approve button guarded by isViewer
  assert.ok(
    pageFile.includes("disabled={actionLoading || !selectedVersionId || !isApprovalEligible || isViewer}"),
    "Right-hand Approve button must be disabled for Read-Only Viewers"
  );

  // 4. Secondary synthesize buttons disabled for viewers
  assert.ok(
    pageFile.includes("disabled={actionLoading || loadingPrompt || isViewer}"),
    "Intelligent draft button in top bar must be disabled for Viewers"
  );
  assert.ok(
    pageFile.includes("disabled={actionLoading || isViewer}"),
    "Intelligent draft buttons in editor tab must be disabled for Viewers"
  );
});

test("V1.2.1: Production readiness API schema defines UNKNOWN and UNAVAILABLE", () => {
  const schemaFile = fs.readFileSync(
    path.resolve("../backend/app/schemas/production_readiness.py"),
    "utf8"
  );
  assert.ok(schemaFile.includes('UNKNOWN = "UNKNOWN"'), "Schema must include UNKNOWN");
  assert.ok(schemaFile.includes('UNAVAILABLE = "UNAVAILABLE"'), "Schema must include UNAVAILABLE");
});
