import type {
  PolicyQualityAssessmentResponse,
  QualityGateResult,
} from "./api";

export type QualityExportFormat = "json" | "markdown" | "csv";

export interface QualityExportContext {
  ruleName?: string;
  ruleIdentifier?: string;
  severity?: string;
  eventType?: string;
  versionNumber?: number;
  versionStatus?: string;
  exportedAt?: string;
}

export interface BuiltQualityExportFile {
  content: string;
  mimeType: string;
  filename: string;
}

const FORMAT_METADATA: Record<
  QualityExportFormat,
  { ext: string; mimeType: string; label: string }
> = {
  json: {
    ext: "json",
    mimeType: "application/json;charset=utf-8",
    label: "JSON",
  },
  markdown: {
    ext: "md",
    mimeType: "text/markdown;charset=utf-8",
    label: "Markdown",
  },
  csv: {
    ext: "csv",
    mimeType: "text/csv;charset=utf-8",
    label: "CSV",
  },
};

function getGateOrderNumber(gateId: string): number {
  const match = gateId.match(/\d+/);
  return match ? Number.parseInt(match[0], 10) : Number.MAX_SAFE_INTEGER;
}

/**
 * Returns the 8 quality gates in canonical G1–G8 order.
 */
export function normalizeGateList(
  assessment: PolicyQualityAssessmentResponse
): QualityGateResult[] {
  const rawGates = assessment.gate_results
    ? Object.values(assessment.gate_results)
    : assessment.gates || [];

  return [...rawGates].sort((a, b) => {
    const orderDiff = getGateOrderNumber(a.gate_id) - getGateOrderNumber(b.gate_id);
    return orderDiff !== 0 ? orderDiff : a.gate_id.localeCompare(b.gate_id);
  });
}

function getBlockingIssues(assessment: PolicyQualityAssessmentResponse): string[] {
  return assessment.blocking_issues ?? assessment.blocking_findings ?? [];
}

function resolveEmpiricalStatus(assessment: PolicyQualityAssessmentResponse): string {
  return (
    assessment.empirical_validation_status ||
    assessment.simulation_status ||
    "NOT_EVALUATED"
  );
}

function resolveExportTimestamp(exportedAt?: string): string {
  return exportedAt || new Date().toISOString();
}

function formatCompactUtcTimestamp(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  const safeDate = Number.isNaN(date.getTime()) ? new Date() : date;
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${safeDate.getUTCFullYear()}` +
    `${pad(safeDate.getUTCMonth() + 1)}` +
    `${pad(safeDate.getUTCDate())}_` +
    `${pad(safeDate.getUTCHours())}` +
    `${pad(safeDate.getUTCMinutes())}` +
    `${pad(safeDate.getUTCSeconds())}`
  );
}

function sanitizeFilenameSlug(raw: string): string {
  const cleaned = raw
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 48);
  return cleaned || "policy_rule";
}

/**
 * Builds the deterministic filename for a G1–G8 Quality Gates export.
 */
export function getQualityGatesExportFilename(
  assessment: PolicyQualityAssessmentResponse,
  format: QualityExportFormat,
  context: QualityExportContext = {}
): string {
  const baseLabel =
    context.ruleName ||
    context.ruleIdentifier ||
    assessment.rule_identifier ||
    "policy_rule";
  const slug = sanitizeFilenameSlug(baseLabel);
  const versionNum = context.versionNumber ?? assessment.policy_version_number;
  const versionSegment =
    versionNum !== undefined && versionNum !== null ? `_v${versionNum}` : "";
  const timestamp = formatCompactUtcTimestamp(
    resolveExportTimestamp(context.exportedAt)
  );
  const { ext } = FORMAT_METADATA[format];
  return `quality_gates_g1_g8_${slug}${versionSegment}_${timestamp}.${ext}`;
}

/**
 * Builds the structured JSON export payload for Quality Gates G1–G8 output.
 */
export function buildQualityGatesExportPayload(
  assessment: PolicyQualityAssessmentResponse,
  context: QualityExportContext = {}
) {
  const exportedAt = resolveExportTimestamp(context.exportedAt);
  const gates = normalizeGateList(assessment);
  const blockingIssues = getBlockingIssues(assessment);
  const passedCount = gates.filter((g) => g.status === "PASSED").length;
  const empiricalStatus = resolveEmpiricalStatus(assessment);
  const structuralEligible =
    assessment.structural_approval_eligible ??
    (Boolean(assessment.approval_eligible) && blockingIssues.length === 0);
  const empiricalEligible =
    assessment.empirical_validation_eligible ??
    empiricalStatus === "EVALUATED_PASSED";

  return {
    schema_version: "1.0",
    report_type: "quality_gates_g1_g8_assessment",
    title: "Agent Intelligence Studio 2.0 — Policy Quality Gates (G1–G8) Output",
    exported_at: exportedAt,
    rule: {
      id: assessment.rule_identifier || context.ruleIdentifier || "",
      name: context.ruleName || assessment.rule_identifier || "",
      severity: context.severity || null,
      event_type: context.eventType || null,
      archetype: assessment.archetype,
      archetype_version: assessment.archetype_version,
    },
    policy_version: {
      prompt_version_id: assessment.prompt_version_id || null,
      version_number: context.versionNumber ?? assessment.policy_version_number,
      status: context.versionStatus || null,
    },
    assessment: {
      assessment_id: assessment.assessment_id,
      validator_version: assessment.validator_version,
      evaluated_at: assessment.evaluated_at,
      validation_status: assessment.validation_status || null,
      overall_quality_score: assessment.quality_score,
      structural_quality_score: assessment.structural_quality_score ?? null,
      empirical_validation_score: assessment.empirical_validation_score ?? null,
      empirical_validation_status: empiricalStatus,
      simulation_status: assessment.simulation_status,
      gates_passed: passedCount,
      gates_total: gates.length,
      eligibility: {
        approval_eligible: assessment.approval_eligible,
        structural_approval_eligible: structuralEligible,
        empirical_validation_eligible: empiricalEligible,
        autonomous_operation_eligible:
          assessment.autonomous_operation_eligible ?? false,
        hard_gate_failure:
          assessment.hard_gate_failure ?? blockingIssues.length > 0,
      },
      score_breakdown: assessment.score_breakdown || {},
      gates,
      blocking_issues: blockingIssues,
      warnings: assessment.warnings || [],
      missing_evidence_mappings: assessment.missing_evidence_mappings || [],
      recommendations: assessment.recommendations || [],
      digests: {
        policy_digest: assessment.policy_digest,
        contract_digest: assessment.contract_digest,
        rule_digest: assessment.rule_digest,
      },
    },
  };
}

/**
 * Formats a human-readable Markdown report for Quality Gates G1–G8 output.
 */
export function formatQualityGatesMarkdown(
  assessment: PolicyQualityAssessmentResponse,
  context: QualityExportContext = {}
): string {
  const payload = buildQualityGatesExportPayload(assessment, context);
  const { rule, policy_version: pv, assessment: summary } = payload;
  const gates = summary.gates;

  const lines: string[] = [
    `# Policy Quality Assessment (G1–G8) — ${rule.name || rule.id}`,
    "",
    `- **Rule ID:** \`${rule.id || "N/A"}\``,
    ...(rule.severity ? [`- **Severity:** ${rule.severity}`] : []),
    ...(rule.event_type ? [`- **Event Type:** \`${rule.event_type}\``] : []),
    `- **Detection Archetype:** \`${rule.archetype}\` (${rule.archetype_version})`,
    `- **Policy Version:** v${pv.version_number}${pv.status ? ` (${pv.status})` : ""}`,
    `- **Assessment ID:** \`${summary.assessment_id}\``,
    `- **Validator Version:** \`${summary.validator_version}\``,
    `- **Evaluated At:** ${summary.evaluated_at}`,
    `- **Exported At:** ${payload.exported_at}`,
    "",
    "## Executive Summary",
    "",
    "| Metric | Value |",
    "| --- | --- |",
    `| Overall Quality Score | **${summary.overall_quality_score} / 100** |`,
    `| Structural Quality (G1–G7) | ${summary.structural_quality_score !== null ? `${summary.structural_quality_score} / 100` : "N/A"} |`,
    `| Empirical Validation (G8) | ${summary.empirical_validation_status} |`,
    `| Gates Passed | ${summary.gates_passed} / ${summary.gates_total} |`,
    `| Blocking Issues | ${summary.blocking_issues.length} |`,
    `| Structural Approval | ${summary.eligibility.structural_approval_eligible ? "ELIGIBLE (G1–G7)" : "BLOCKED"} |`,
    `| Empirical G8 Eligibility | ${summary.eligibility.empirical_validation_eligible ? "VERIFIED" : `NOT CERTIFIED (${summary.empirical_validation_status})`} |`,
    `| Autonomous Operations | ${summary.eligibility.autonomous_operation_eligible ? "ELIGIBLE" : "REQUIRES G8 PASS"} |`,
    "",
    "## Mandatory Quality Gates (G1–G8)",
    "",
  ];

  for (const gate of gates) {
    lines.push(
      `### ${gate.gate_id}: ${gate.gate_name} — ${gate.status} (${gate.score}/${gate.max_score} pts)`
    );
    lines.push("");
    if (gate.details) {
      lines.push(gate.details);
      lines.push("");
    }
    if (gate.blocking_findings && gate.blocking_findings.length > 0) {
      lines.push("**Blocking Findings:**");
      for (const finding of gate.blocking_findings) {
        lines.push(`- ${finding}`);
      }
      lines.push("");
    }
    if (gate.warnings && gate.warnings.length > 0) {
      lines.push("**Warnings:**");
      for (const warning of gate.warnings) {
        lines.push(`- ${warning}`);
      }
      lines.push("");
    }
  }

  if (summary.blocking_issues.length > 0) {
    lines.push("## Blocking Issues");
    lines.push("");
    for (const issue of summary.blocking_issues) {
      lines.push(`- ${issue}`);
    }
    lines.push("");
  }

  if (summary.warnings.length > 0) {
    lines.push("## Advisory Warnings");
    lines.push("");
    for (const warning of summary.warnings) {
      lines.push(`- ${warning}`);
    }
    lines.push("");
  }

  if (summary.missing_evidence_mappings.length > 0) {
    lines.push("## Missing Evidence Mappings");
    lines.push("");
    for (const mapping of summary.missing_evidence_mappings) {
      lines.push(`- \`${mapping}\``);
    }
    lines.push("");
  }

  if (summary.recommendations.length > 0) {
    lines.push("## Remediation Recommendations");
    lines.push("");
    for (const rec of summary.recommendations) {
      lines.push(`- ${rec}`);
    }
    lines.push("");
  }

  const breakdownEntries = Object.entries(summary.score_breakdown);
  if (breakdownEntries.length > 0) {
    lines.push("## Score Breakdown");
    lines.push("");
    lines.push("| Dimension | Score |");
    lines.push("| --- | --- |");
    for (const [dimension, score] of breakdownEntries) {
      lines.push(`| ${dimension} | ${score} |`);
    }
    lines.push("");
  }

  lines.push("## Cryptographic Digests");
  lines.push("");
  lines.push(`- **Policy Digest:** \`${summary.digests.policy_digest}\``);
  lines.push(`- **Contract Digest:** \`${summary.digests.contract_digest}\``);
  lines.push(`- **Rule Digest:** \`${summary.digests.rule_digest}\``);
  lines.push("");

  return lines.join("\n");
}

/**
 * Escapes a CSV cell and neutralizes spreadsheet formula injection (CWE-1236).
 */
export function escapeCsvCell(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  let text = String(value);
  // Prefix leading formula characters so spreadsheet clients cannot execute cell content
  if (/^[=+\-@\t\r]/.test(text)) {
    text = `'${text}`;
  }
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

/**
 * Formats a tabular CSV report containing one row per Quality Gate (G1–G8).
 */
export function formatQualityGatesCsv(
  assessment: PolicyQualityAssessmentResponse,
  context: QualityExportContext = {}
): string {
  const payload = buildQualityGatesExportPayload(assessment, context);
  const { rule, policy_version: pv, assessment: summary } = payload;

  const headers = [
    "rule_id",
    "rule_name",
    "severity",
    "event_type",
    "policy_version_number",
    "policy_version_status",
    "archetype",
    "assessment_id",
    "evaluated_at",
    "overall_quality_score",
    "structural_quality_score",
    "empirical_validation_status",
    "structural_approval_eligible",
    "empirical_validation_eligible",
    "autonomous_operation_eligible",
    "gate_id",
    "gate_name",
    "gate_status",
    "gate_score",
    "gate_max_score",
    "gate_details",
    "gate_blocking_findings",
    "gate_warnings",
    "assessment_blocking_issues",
    "recommendations",
  ];

  const commonPrefix = [
    rule.id,
    rule.name,
    rule.severity ?? "",
    rule.event_type ?? "",
    pv.version_number,
    pv.status ?? "",
    rule.archetype,
    summary.assessment_id,
    summary.evaluated_at,
    summary.overall_quality_score,
    summary.structural_quality_score ?? "",
    summary.empirical_validation_status,
    summary.eligibility.structural_approval_eligible,
    summary.eligibility.empirical_validation_eligible,
    summary.eligibility.autonomous_operation_eligible,
  ];

  const commonSuffix = [
    summary.blocking_issues.join(" | "),
    summary.recommendations.join(" | "),
  ];

  const gateRows: QualityGateResult[] =
    summary.gates.length > 0
      ? summary.gates
      : [
          {
            gate_id: "NONE",
            gate_name: "No gates evaluated",
            status: "WARNING",
            score: 0,
            max_score: 0,
            details: "",
            blocking_findings: [],
            warnings: [],
          },
        ];

  const rows = [
    headers.map(escapeCsvCell).join(","),
    ...gateRows.map((gate) =>
      [
        ...commonPrefix,
        gate.gate_id,
        gate.gate_name,
        gate.status,
        gate.score,
        gate.max_score,
        gate.details,
        (gate.blocking_findings || []).join(" | "),
        (gate.warnings || []).join(" | "),
        ...commonSuffix,
      ]
        .map(escapeCsvCell)
        .join(",")
    ),
  ];

  return rows.join("\n");
}

/**
 * Generates the serialized content, MIME type, and filename for a Quality Gates export.
 */
export function buildQualityGatesExportFile(
  assessment: PolicyQualityAssessmentResponse,
  format: QualityExportFormat,
  context: QualityExportContext = {}
): BuiltQualityExportFile {
  const filename = getQualityGatesExportFilename(assessment, format, context);
  const { mimeType } = FORMAT_METADATA[format];

  let content: string;
  if (format === "json") {
    content = JSON.stringify(
      buildQualityGatesExportPayload(assessment, context),
      null,
      2
    );
  } else if (format === "markdown") {
    content = formatQualityGatesMarkdown(assessment, context);
  } else {
    content = formatQualityGatesCsv(assessment, context);
  }

  return { content, mimeType, filename };
}

/**
 * Triggers a browser file download from an in-memory Blob.
 */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(url), 1000);
}

export function getQualityExportFormatLabel(format: QualityExportFormat): string {
  return FORMAT_METADATA[format].label;
}

