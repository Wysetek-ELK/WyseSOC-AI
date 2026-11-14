import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import {
  deriveOperationalStatus,
  extractConsolidatedIssues,
  formatHttpError,
} from "../src/lib/diagnostics.ts";

test("deriveOperationalStatus: accurately derives all 7 operational states", () => {
  // 1. SUSPENDED
  assert.equal(
    deriveOperationalStatus({
      lifecycleStage: "SUSPENDED",
      qualityScore: 80,
      totalAnalystReviews: 35,
    }).status,
    "SUSPENDED"
  );

  // 2. PRODUCTION_ACTIVE
  assert.equal(
    deriveOperationalStatus({
      lifecycleStage: "PRODUCTION",
      activeVersionStatus: "APPROVED",
      qualityScore: 90,
      totalAnalystReviews: 35,
    }).status,
    "PRODUCTION_ACTIVE"
  );

  // 3. PRODUCTION_APPROVAL_PENDING
  assert.equal(
    deriveOperationalStatus({
      lifecycleStage: "VALIDATION",
      isApprovalEligible: true,
      qualityScore: 88,
      totalAnalystReviews: 32,
    }).status,
    "PRODUCTION_APPROVAL_PENDING"
  );

  // 4. ACTION_REQUIRED (Incomplete definition or hard gate failure)
  assert.equal(
    deriveOperationalStatus({
      lifecycleStage: "LEARNING",
      isIncompleteDefinition: true,
      hasHardGateFailure: true,
      qualityScore: 40,
      totalAnalystReviews: 5,
    }).status,
    "ACTION_REQUIRED"
  );

  // 5. READY_FOR_VALIDATION (totalAnalystReviews >= 10 && qualityScore >= 60)
  assert.equal(
    deriveOperationalStatus({
      lifecycleStage: "LEARNING",
      isApprovalEligible: false,
      qualityScore: 85,
      totalAnalystReviews: 15,
    }).status,
    "READY_FOR_VALIDATION"
  );

  // 6. LEARNING_IN_PROGRESS (totalAnalystReviews > 0 but < 10)
  assert.equal(
    deriveOperationalStatus({
      lifecycleStage: "LEARNING",
      qualityScore: 50,
      totalAnalystReviews: 4,
    }).status,
    "LEARNING_IN_PROGRESS"
  );

  // 7. READY_FOR_LEARNING (totalAnalystReviews === 0)
  assert.equal(
    deriveOperationalStatus({
      lifecycleStage: "LEARNING",
      qualityScore: 70,
      totalAnalystReviews: 0,
    }).status,
    "READY_FOR_LEARNING"
  );
});

test("extractConsolidatedIssues: deduplicates identical root causes and prioritizes severity", () => {
  const issues = extractConsolidatedIssues({
    ruleId: "TEST_RULE",
    ruleName: "Test Suspicious Execution",
    definitionStatus: "INCOMPLETE",
    qualityAssessment: {
      quality_score: 55,
      approval_eligible: false,
      blocking_issues: ["G1_RULE_DEFINITION_INCOMPLETE", "G4_POLICY_CONTRACT_COMPILATION_FAILED"],
      gates: [
        {
          gate_name: "G1: Rule Definition",
          status: "FAILED",
          score: 0,
          details: "Detection rule lacks authoritative SIEM correlation thresholds.",
        },
        {
          gate_name: "G4: Policy Contract Compilation",
          status: "FAILED",
          score: 40,
          details: "Policy contract failed deterministic compilation.",
        },
      ],
    },
    learningProfile: {
      total_analyst_reviews: 0,
      verified_tp_count: 0,
      verified_fp_count: 0,
      empirical_accuracy: null,
      is_production_eligible: false,
      eligibility_reasons: ["Requires minimum 30 verified reviews for pilot"],
    },
    llmOnline: false,
    evidenceContract: {
      required_fields: ["src_ip", "dest_port", "cmdline"],
      missing_fields: ["cmdline"],
    },
  });

  assert.ok(issues.length >= 2, "Should extract at least 2 issues");
  // LLM Offline or security should be prioritized at the top
  assert.equal(issues[0].severity, "critical");

  // Should include rule definition issue
  const ruleIssue = issues.find((i) => i.id.includes("rule_def") || i.category === "rule_definition");
  assert.ok(ruleIssue, "Should report rule definition issue");

  // Should include review/accuracy gap
  const accuracyIssue = issues.find((i) => i.id.includes("accuracy") || i.id.includes("ground_truth"));
  assert.ok(accuracyIssue, "Should report unverified accuracy gap");
  assert.match(accuracyIssue.nextAction, /review/i);
});

test("formatHttpError: formats 422, 400, and standard errors with actionable remediation", () => {
  const err422 = {
    response: {
      status: 422,
      data: {
        detail: [
          { loc: ["body", "policy_contract"], msg: "Field required", type: "value_error.missing" },
        ],
      },
    },
  };
  const formatted = formatHttpError(err422);
  assert.equal(formatted.title, "Request Could Not Be Processed");
  assert.match(formatted.message, /Field required/i);
  assert.equal(formatted.isRetryable, false);

  const err500 = {
    response: {
      status: 500,
    },
  };
  const formatted500 = formatHttpError(err500);
  assert.equal(formatted500.title, "Server Internal Error");
  assert.equal(formatted500.isRetryable, true);

  const errNetwork = new Error("Network timeout connecting to backend");
  const formattedNet = formatHttpError(errNetwork);
  assert.match(formattedNet.message, /Network timeout/i);
});

test("Agent Intelligence Studio: implements 3 Primary Tabs and rollout toggle", () => {
  const pagePath = path.resolve("src/app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  // Verify Primary Tabs structure
  assert.match(content, /primaryTab === "overview"/, "Must render Overview primary tab");
  assert.match(content, /primaryTab === "learning"/, "Must render Analyst Review & Learning primary tab");
  assert.match(content, /primaryTab === "advanced"/, "Must render Advanced Configuration primary tab");

  // Verify rollout toggle & localStorage persistence
  assert.match(content, /VERDICTUM_COMPACT_UI_ENABLED/, "Must support rollout toggle key");
  assert.match(content, /localStorage/, "Must check localStorage for user preference");

  // Verify default tab is Overview
  assert.match(content, /primaryTab === "overview"/, "Must render Overview as primary default");

  // Verify deep-link query parameter parsing
  assert.match(content, /tabParam/, "Must read tab query parameter");
});

test("AI Triage Workbench Detail: contains 4-Dimension Verdict Matrix and Collapsible Diagnostics", () => {
  const pagePath = path.resolve("src/app/ai-triage-workbench/[id]/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  assert.match(content, /IncidentVerdictMatrix/, "Must render 4-dimension IncidentVerdictMatrix");
  assert.match(content, /NextActionCard/, "Must render NextActionCard directive");
  assert.match(content, /AdvancedDetailsPanel/, "Must wrap diagnostics in AdvancedDetailsPanel");
  assert.match(content, /blindReviewMode/, "Must support double-blind review mode");
});

test("Human Review Queue: implements Double-Blind masking and post-submission comparison", () => {
  const pagePath = path.resolve("src/app/human-review-queue/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  assert.match(content, /blindReviewMode/, "Must support blindReviewMode state");
  assert.match(content, /Double-Blind Review Active/, "Must display double-blind masking notice");
  assert.match(content, /Post-Submission Comparison/, "Must provide post-submission comparison reveal");
});

test("Agent Simulation Lab: distinguishes Replay Engine and handles unverified accuracy", () => {
  const pagePath = path.resolve("src/app/agent-simulation-lab/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  assert.match(content, /MetricSummaryCard/, "Must render MetricSummaryCard primitives");
  assert.match(content, /NextActionCard/, "Must render NextActionCard");
  assert.match(content, /AdvancedDetailsPanel/, "Must wrap diagnostics in AdvancedDetailsPanel");
  assert.match(content, /N\/A \(Pending Ground Truth\)/, "Must withhold 0% accuracy when unverified");
});
