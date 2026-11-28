import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_SRC = path.resolve(__dirname, "../src");

test("AIS 3.1: GroundTruthCertificationPanel replaces hardcoded 20-cohort strings with dynamic cohort telemetry", () => {
  const panelPath = path.join(FRONTEND_SRC, "components/review/GroundTruthCertificationPanel.tsx");
  const content = fs.readFileSync(panelPath, "utf-8");

  assert.ok(!content.includes("All 20 Cohort"), "Must not hardcode 'All 20 Cohort'");
  assert.ok(!content.includes("Priority 5 Pilot"), "Must not hardcode 'Priority 5 Pilot'");
  assert.ok(!content.includes("Remaining 15"), "Must not hardcode 'Remaining 15'");
  assert.ok(!content.includes("before AIS 2.7 live GPU inference"), "Must remove stale AIS 2.7 copy");

  assert.ok(content.includes("AIS_3_0_INDEPENDENT_HOLDOUT_100"), "Should support/default AIS 3.0 holdout cohort");
  assert.ok(content.includes("My Human Reviews"), "Should display My Human Reviews counter");
  assert.ok(content.includes("2nd Reviews"), "Should display Independent Second Reviews counter");
  assert.ok(content.includes("Benchmark Eligible"), "Should display Benchmark Eligible counter");
  assert.ok(content.includes("Bench Executed"), "Should display Benchmark Executed counter");
  assert.ok(content.includes("Bench Completed"), "Should display Benchmark Completed counter");
  assert.ok(content.includes("Quarantined"), "Should display Quarantined counter");
  assert.ok(content.includes("CONFIRMED_EXPOSURE"), "Should render structured exposure states");
  assert.ok(content.includes("HISTORICAL_LABEL_EXISTS_BUT_MASKED"), "Should distinguish masked historical labels");
});

test("AIS 3.1: Human Review Queue tab label removes outdated AIS 2.6e tag", () => {
  const queuePath = path.join(FRONTEND_SRC, "app/human-review-queue/page.tsx");
  const content = fs.readFileSync(queuePath, "utf-8");
  assert.ok(!content.includes("Ground Truth Certification (AIS 2.6e)"), "Must not hardcode AIS 2.6e tab label");
  assert.ok(content.includes("Ground Truth Certification"), "Must keep Ground Truth Certification tab");
});

test("AIS 3.1: AccuracyLearningSummary separates Raw LLM vs Validated App and Provisional GT-2 vs Certified GT-3", () => {
  const sumPath = path.join(FRONTEND_SRC, "components/compact/AccuracyLearningSummary.tsx");
  const content = fs.readFileSync(sumPath, "utf-8");

  assert.ok(!content.includes("Awaiting Authorized GPU Run"), "Must remove stale AIS 2.8 awaiting placeholder");
  assert.ok(content.includes("AIS 3.1 Holdout — Raw LLM"), "Must separate Raw LLM accuracy row");
  assert.ok(content.includes("AIS 3.1 Holdout — Validated App"), "Must separate Validated Application accuracy row");
  assert.ok(content.includes("Provisional GT-2"), "Must label GT-2 results as provisional");
  assert.ok(content.includes("Certified GT-3"), "Must distinguish GT-3 certified results");
  assert.ok(content.includes("getLatestAis31Summary"), "Must fetch dynamic AIS 3.1 summary");
});
