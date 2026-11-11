import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import {
  buildQualityGatesExportFile,
  buildQualityGatesExportPayload,
  escapeCsvCell,
  formatQualityGatesCsv,
  formatQualityGatesMarkdown,
  getQualityGatesExportFilename,
  normalizeGateList,
} from "../src/lib/qualityExport.ts";

function makeSampleAssessment(overrides = {}) {
  return {
    assessment_id: "qa-1234",
    rule_identifier: "PH_RULE_TCP_SCAN",
    policy_version_number: 2,
    prompt_version_id: "pv-2",
    archetype: "NETWORK_SCAN",
    validator_version: "v2.0.0",
    quality_score: 81,
    structural_quality_score: 95.3,
    empirical_validation_score: 0,
    empirical_validation_status: "INSUFFICIENT_DATA",
    score_breakdown: {
      detection_semantics: 16,
      evidence_contract: 20,
      tp_fp_criteria: 20,
      abstention_escalation: 15,
      internal_consistency: 10,
      historical_simulation: 0,
    },
    gate_results: {
      G8_SIMULATION_REGRESSION: {
        gate_id: "G8",
        gate_name: "Simulation & Regression Validation",
        status: "WARNING",
        score: 0,
        max_score: 15,
        details: "Simulation status: INSUFFICIENT_DATA",
        blocking_findings: [],
        warnings: ["G8_INSUFFICIENT_DATA: Insufficient verified historical cases (1 < 5)."],
      },
      G1_RULE_INTEGRITY: {
        gate_id: "G1",
        gate_name: "Rule Definition Integrity",
        status: "WARNING",
        score: 16,
        max_score: 20,
        details: "Rule definition provenance: VENDOR_RULE_FILE. Status: VERIFIED.",
        blocking_findings: [],
        warnings: ["Incident runtime counter observed in rule conditions."],
      },
      G2_ARCHETYPE_RELEVANCE: {
        gate_id: "G2",
        gate_name: "Detection Archetype Relevance",
        status: "PASSED",
        score: 20,
        max_score: 20,
        details: "Archetype: Network Scan & Host Reconnaissance.",
        blocking_findings: [],
        warnings: [],
      },
      G3_EVIDENCE_FEASIBILITY: {
        gate_id: "G3",
        gate_name: "Evidence Contract Feasibility",
        status: "PASSED",
        score: 20,
        max_score: 20,
        details: "Contract EC-98836c40: 11 fields defined.",
        blocking_findings: [],
        warnings: [],
      },
      G4_TP_CRITERIA_VALIDITY: {
        gate_id: "G4",
        gate_name: "TP Criteria Validity",
        status: "PASSED",
        score: 10,
        max_score: 10,
        details: "Evaluated objective specificity of True Positive criteria.",
        blocking_findings: [],
        warnings: [],
      },
      G5_FP_CRITERIA_VALIDITY: {
        gate_id: "G5",
        gate_name: "FP Criteria & Benign Assumptions",
        status: "PASSED",
        score: 10,
        max_score: 10,
        details: "Evaluated False Positive criteria for unsafe benign assumptions.",
        blocking_findings: [],
        warnings: [],
      },
      G6_ABSTENTION_ESCALATION: {
        gate_id: "G6",
        gate_name: "Abstention & Escalation Safety",
        status: "PASSED",
        score: 15,
        max_score: 15,
        details: "Verified presence of explicit abstention triggers and critical escalation paths.",
        blocking_findings: [],
        warnings: [],
      },
      G7_POLICY_CONSISTENCY: {
        gate_id: "G7",
        gate_name: "Internal Policy & Contract Consistency",
        status: "PASSED",
        score: 10,
        max_score: 10,
        details: "Evaluated internal consistency between 9 policy sections and Evidence Contract.",
        blocking_findings: [],
        warnings: [],
      },
    },
    blocking_issues: [],
    warnings: ["Empirical corpus below threshold"],
    missing_evidence_mappings: [],
    recommendations: ["Collect at least 5 independently verified historical incidents before empirical approval."],
    simulation_status: "INSUFFICIENT_DATA",
    approval_eligible: true,
    structural_approval_eligible: true,
    empirical_validation_eligible: false,
    autonomous_operation_eligible: false,
    policy_digest: "sha256:policy123",
    contract_digest: "sha256:contract123",
    rule_digest: "sha256:rule123",
    archetype_version: "v2.0.0",
    evaluated_at: "2026-11-11T11:25:00Z",
    ...overrides,
  };
}

test("normalizeGateList sorts G1 through G8 in canonical order", () => {
  const assessment = makeSampleAssessment();
  const gates = normalizeGateList(assessment);
  assert.deepEqual(
    gates.map((g) => g.gate_id),
    ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"]
  );
});

test("buildQualityGatesExportPayload includes full G1-G8 assessment, eligibility tiers, and digests", () => {
  const assessment = makeSampleAssessment();
  const payload = buildQualityGatesExportPayload(assessment, {
    ruleName: "Heavy TCP Host Scan",
    severity: "MEDIUM",
    eventType: "PH_RULE_TCP_SCAN",
    versionNumber: 2,
    versionStatus: "APPROVED",
    exportedAt: "2026-11-11T11:30:33Z",
  });

  assert.equal(payload.schema_version, "1.0");
  assert.equal(payload.report_type, "quality_gates_g1_g8_assessment");
  assert.equal(payload.rule.name, "Heavy TCP Host Scan");
  assert.equal(payload.rule.severity, "MEDIUM");
  assert.equal(payload.policy_version.version_number, 2);
  assert.equal(payload.policy_version.status, "APPROVED");
  assert.equal(payload.assessment.overall_quality_score, 81);
  assert.equal(payload.assessment.structural_quality_score, 95.3);
  assert.equal(payload.assessment.gates_passed, 6);
  assert.equal(payload.assessment.gates_total, 8);
  assert.equal(payload.assessment.eligibility.structural_approval_eligible, true);
  assert.equal(payload.assessment.eligibility.empirical_validation_eligible, false);
  assert.equal(payload.assessment.eligibility.autonomous_operation_eligible, false);
  assert.equal(payload.assessment.digests.policy_digest, "sha256:policy123");
});

test("formatQualityGatesMarkdown renders readable summary, all 8 gates, recommendations, and digests", () => {
  const assessment = makeSampleAssessment({
    blocking_issues: ["G1_MISSING_THRESHOLD: Authoritative threshold missing"],
  });
  const md = formatQualityGatesMarkdown(assessment, {
    ruleName: "Heavy TCP Host Scan",
    versionNumber: 2,
    versionStatus: "APPROVED",
    exportedAt: "2026-11-11T11:30:33Z",
  });

  assert.match(md, /# Policy Quality Assessment \(G1–G8\) — Heavy TCP Host Scan/);
  assert.match(md, /\| Overall Quality Score \| \*\*81 \/ 100\*\* \|/);
  assert.match(md, /### G1: Rule Definition Integrity — WARNING \(16\/20 pts\)/);
  assert.match(md, /### G8: Simulation & Regression Validation — WARNING \(0\/15 pts\)/);
  assert.match(md, /## Blocking Issues/);
  assert.match(md, /G1_MISSING_THRESHOLD/);
  assert.match(md, /## Remediation Recommendations/);
  assert.match(md, /sha256:contract123/);
});

test("escapeCsvCell neutralizes spreadsheet formula injection (CWE-1236) and escapes quotes", () => {
  assert.equal(escapeCsvCell("=CMD('calc')"), "'=CMD('calc')");
  assert.equal(escapeCsvCell("=SUM(A1,A2)"), `"'=SUM(A1,A2)"`);
  assert.equal(escapeCsvCell("+1+1"), "'+1+1");
  assert.equal(escapeCsvCell("-10"), "'-10");
  assert.equal(escapeCsvCell("@SUM(A1:A2)"), "'@SUM(A1:A2)");
  assert.equal(escapeCsvCell(`hello, "world"`), `"hello, ""world"""`);
  assert.equal(escapeCsvCell(81), "81");
  assert.equal(escapeCsvCell(false), "false");
});

test("formatQualityGatesCsv produces header and 8 gate rows in order", () => {
  const assessment = makeSampleAssessment();
  const csv = formatQualityGatesCsv(assessment, {
    ruleName: "Heavy TCP Host Scan",
    severity: "MEDIUM",
    versionNumber: 2,
    versionStatus: "APPROVED",
  });
  const lines = csv.split("\n");
  assert.equal(lines.length, 9);
  assert.ok(lines[0].startsWith("rule_id,rule_name,severity,"));
  assert.match(lines[1], /,G1,Rule Definition Integrity,WARNING,16,20,/);
  assert.match(lines[8], /,G8,Simulation & Regression Validation,WARNING,0,15,/);
});

test("getQualityGatesExportFilename sanitizes rule name and builds deterministic extension", () => {
  const assessment = makeSampleAssessment();
  const context = {
    ruleName: "Heavy TCP Host Scan (MEDIUM)!",
    versionNumber: 2,
    exportedAt: "2026-11-11T11:30:33Z",
  };

  assert.equal(
    getQualityGatesExportFilename(assessment, "json", context),
    "quality_gates_g1_g8_heavy_tcp_host_scan_medium_v2_20261111_113033.json"
  );
  assert.equal(
    getQualityGatesExportFilename(assessment, "markdown", context),
    "quality_gates_g1_g8_heavy_tcp_host_scan_medium_v2_20261111_113033.md"
  );
  assert.equal(
    getQualityGatesExportFilename(assessment, "csv", context),
    "quality_gates_g1_g8_heavy_tcp_host_scan_medium_v2_20261111_113033.csv"
  );

  const built = buildQualityGatesExportFile(assessment, "json", context);
  assert.equal(built.mimeType, "application/json;charset=utf-8");
  assert.equal(JSON.parse(built.content).assessment.overall_quality_score, 81);
});

test("Agent Intelligence Studio page exposes Download Output control in Quality Gates tab", () => {
  const studioPath = path.resolve("src/app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(studioPath, "utf-8");
  assert.match(content, /Policy Quality Assessment \(8 Mandatory Gates\)/);
  assert.match(content, /Download Output/);
  assert.match(content, /handleExportQualityGates\("json"\)/);
  assert.match(content, /handleExportQualityGates\("markdown"\)/);
  assert.match(content, /handleExportQualityGates\("csv"\)/);
  assert.match(content, /Revalidate/);
});
