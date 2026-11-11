import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import {
  ARCHITECTURE_EDGES,
  ARCHITECTURE_STEPS,
  ARCHITECTURE_SWIMLANES,
} from "../src/data/admin-guide/architectureFlowData.ts";
import {
  DECISION_EDGES,
  DECISION_STEPS,
  DECISION_SWIMLANES,
} from "../src/data/admin-guide/decisionFlowData.ts";
import {
  ARCHETYPE_SPOTLIGHT,
  DETERMINISTIC_GUARDRAILS,
  EVIDENCE_SUFFICIENCY_DIMENSIONS,
  NINE_POLICY_SECTIONS,
  QUALITY_GATES_DOCS,
  STUDIO_LIFECYCLE_STAGES,
  TRUSTWORTHINESS_DIMENSIONS,
} from "../src/data/admin-guide/studioGuideData.ts";
import {
  INCIDENT_165233_METADATA,
  INCIDENT_165233_STEPS,
} from "../src/data/admin-guide/incidentExampleData.ts";
import { REQUIREMENT_DOMAINS } from "../src/data/admin-guide/requirementsData.ts";
import {
  GLOSSARY_ENTRIES,
  GUIDED_TOUR_STOPS,
  PLATFORM_PAGE_LINKS,
  TROUBLESHOOTING_SCENARIOS,
} from "../src/data/admin-guide/glossaryAndTroubleshootingData.ts";

test("Sidebar contains Platform Control -> Verdictum AI Admin Guide route", () => {
  const sidebarPath = path.resolve("src/components/layout/Sidebar.tsx");
  const sidebarContent = fs.readFileSync(sidebarPath, "utf-8");
  assert.match(sidebarContent, /PLATFORM CONTROL/);
  assert.match(sidebarContent, /Verdictum AI Admin Guide/);
  assert.match(sidebarContent, /\/admin-guide/);
});

test("End-to-End Architecture flow includes all 17 stages, two lanes, bridges, and 6-part metadata", () => {
  assert.equal(ARCHITECTURE_STEPS.length, 17);
  assert.equal(ARCHITECTURE_SWIMLANES.length, 2);

  const expectedTitles = [
    "FortiSIEM",
    "Telemetry Hub",
    "Rule Intelligence Analyzer",
    "Detection Archetype",
    "Evidence Contract",
    "Intelligent Policy Generator",
    "Quality Gates G1–G7",
    "Historical Simulation G8",
    "Human Policy Approval",
    "Approved Policy Registry",
    "Verdict Triage Agent",
    "Evidence Evaluation",
    "Local LLM Reasoning",
    "TP / FP / Requires Analyst Attention",
    "SOC Analyst Review",
    "Verified Feedback",
    "Calibration / Regression Monitoring",
  ];

  assert.deepEqual(
    ARCHITECTURE_STEPS.map((s) => s.title),
    expectedTitles
  );

  const stepIds = new Set(ARCHITECTURE_STEPS.map((s) => s.id));
  for (const edge of ARCHITECTURE_EDGES) {
    assert.ok(stepIds.has(edge.source), `Missing edge source: ${edge.source}`);
    assert.ok(stepIds.has(edge.target), `Missing edge target: ${edge.target}`);
  }

  const bridges = ARCHITECTURE_EDGES.filter((e) => e.isBridge);
  assert.ok(bridges.length >= 4, "Expected explicit cross-lane bridge connections");

  for (const step of ARCHITECTURE_STEPS) {
    assert.ok(step.componentName.length > 0, `${step.id} missing componentName`);
    assert.ok(step.inputData.length > 0, `${step.id} missing inputData`);
    assert.ok(step.processingLogic.length > 0, `${step.id} missing processingLogic`);
    assert.ok(step.outputData.length > 0, `${step.id} missing outputData`);
    assert.ok(step.requiredConfig.length > 0, `${step.id} missing requiredConfig`);
    assert.ok(step.failureOrAbstention.length > 0, `${step.id} missing failureOrAbstention`);
  }
});

test("Verdictum AI Decision Engine flow includes 9 pipeline steps and all 3 verdict outcomes", () => {
  assert.equal(DECISION_SWIMLANES.length, 2);
  assert.equal(DECISION_STEPS.length, 12);

  const outcomes = DECISION_STEPS.map((s) => s.outcomeBadge).filter(Boolean);
  assert.deepEqual(outcomes.sort(), [
    "FALSE_POSITIVE",
    "REQUIRES_ANALYST_ATTENTION",
    "TRUE_POSITIVE",
  ]);

  const stepIds = new Set(DECISION_STEPS.map((s) => s.id));
  for (const edge of DECISION_EDGES) {
    assert.ok(stepIds.has(edge.source), `Missing decision edge source: ${edge.source}`);
    assert.ok(stepIds.has(edge.target), `Missing decision edge target: ${edge.target}`);
  }

  for (const step of DECISION_STEPS) {
    assert.ok(step.componentName.length > 0);
    assert.ok(step.inputData.length > 0);
    assert.ok(step.processingLogic.length > 0);
    assert.ok(step.outputData.length > 0);
    assert.ok(step.requiredConfig.length > 0);
    assert.ok(step.failureOrAbstention.length > 0);
  }
});

test("AIS 2.0 Guide covers 8 lifecycle stages, NETWORK_SCAN, 9 policy sections, and Quality Gates G1-G8", () => {
  assert.equal(STUDIO_LIFECYCLE_STAGES.length, 8);
  assert.equal(NINE_POLICY_SECTIONS.length, 9);
  assert.equal(QUALITY_GATES_DOCS.length, 8);
  assert.deepEqual(
    QUALITY_GATES_DOCS.map((g) => g.gateId),
    ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]
  );

  for (const gate of QUALITY_GATES_DOCS) {
    assert.ok(gate.passConditions.length > 0, `${gate.gateId} missing pass conditions`);
    assert.ok(gate.warningConditions.length > 0, `${gate.gateId} missing warning conditions`);
    assert.ok(gate.blockerConditions.length > 0, `${gate.gateId} missing blocker conditions`);
    assert.ok(gate.remediationGuidance.length > 0, `${gate.gateId} missing remediation`);
  }

  assert.equal(ARCHETYPE_SPOTLIGHT.networkScan.archetypeId, "NETWORK_SCAN");
  assert.ok(ARCHETYPE_SPOTLIGHT.allArchetypes.includes("NETWORK_SCAN"));
  assert.equal(EVIDENCE_SUFFICIENCY_DIMENSIONS.length, 4);
  assert.equal(TRUSTWORTHINESS_DIMENSIONS.length, 5);
  assert.equal(DETERMINISTIC_GUARDRAILS.length, 7);
});

test("Incident 165233 illustrative walkthrough adheres strictly to non-fabrication constraints", () => {
  assert.equal(INCIDENT_165233_METADATA.incidentId, "165233");
  assert.equal(INCIDENT_165233_METADATA.ruleName, "Heavy TCP Host Scan");
  assert.equal(INCIDENT_165233_METADATA.siemResolution, "False Positive");
  assert.equal(INCIDENT_165233_METADATA.historicalAiDecision, "REQUIRES_ANALYST_ATTENTION");
  assert.equal(INCIDENT_165233_METADATA.observedTrustScore, "3/10");
  assert.equal(INCIDENT_165233_METADATA.simulationStatus, "INSUFFICIENT_DATA");

  assert.equal(INCIDENT_165233_STEPS.length, 6);
  for (const step of INCIDENT_165233_STEPS) {
    assert.ok(
      step.illustrativePlaceholders.some((p) => p.includes("ILLUSTRATIVE PLACEHOLDER")),
      `Step ${step.id} should explicitly label illustrative placeholders`
    );
  }
});

test("Admin Setup covers all 11 domains and valid platform route links", () => {
  assert.equal(REQUIREMENT_DOMAINS.length, 11);
  for (const dom of REQUIREMENT_DOMAINS) {
    assert.ok(dom.items.length >= 2, `Domain ${dom.id} should have detailed checks`);
    for (const item of dom.items) {
      assert.ok(["REQUIRED", "CONDITIONAL", "OPTIONAL"].includes(item.criticality));
      assert.ok(item.consequenceIfMissing.length > 10);
      assert.ok(item.verificationCheck.length > 5);
    }
  }

  for (const link of PLATFORM_PAGE_LINKS) {
    const cleanRoute = link.href.replace(/^\//, "");
    const pageFile = path.resolve("src/app", cleanRoute, "page.tsx");
    assert.ok(fs.existsSync(pageFile), `Expected page route file for ${link.href}: ${pageFile}`);
  }
});

test("Glossary, Guided Tour, and Troubleshooting cover required diagnostic scenarios", () => {
  assert.ok(GLOSSARY_ENTRIES.length >= 15);
  assert.ok(GUIDED_TOUR_STOPS.length >= 6);
  assert.ok(TROUBLESHOOTING_SCENARIOS.length >= 5);

  const ids = new Set(TROUBLESHOOTING_SCENARIOS.map((s) => s.id));
  assert.ok(ids.has("ts-high-quality-g8-insufficient"));
  assert.ok(ids.has("ts-fp-gets-abstain"));
  assert.ok(ids.has("ts-zero-labels-empirical"));
  assert.ok(ids.has("ts-missing-evidence-lowers-trust"));
  assert.ok(ids.has("ts-v1-vs-v2-different-results"));
});

test("WorkflowFlowDiagram fits full workspace screen with browser fullscreen animated-architecture view and collapsible Step Details", () => {
  const diagramSrc = fs.readFileSync(
    path.resolve("src/components/admin-guide/WorkflowFlowDiagram.tsx"),
    "utf-8"
  );
  const pageSrc = fs.readFileSync(
    path.resolve("src/app/admin-guide/page.tsx"),
    "utf-8"
  );
  assert.match(diagramSrc, /requestFullscreen/);
  assert.match(diagramSrc, /fullscreenchange/);
  assert.match(diagramSrc, /fixed inset-0 z-50/);
  assert.match(diagramSrc, /useState<boolean>\(false\)/);
  assert.match(diagramSrc, /Step Details/);
  assert.match(diagramSrc, /xl:col-span-12/);
  assert.match(pageSrc, /className="space-y-4 w-full"/);
});
