import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const srcDir = path.resolve(__dirname, "../src");

function scanDirectory(dir, filterFn) {
  let files = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files = files.concat(scanDirectory(fullPath, filterFn));
    } else if (filterFn(fullPath)) {
      files.push(fullPath);
    }
  }
  return files;
}

test("V1.2.3 Scenario 01: Zero occurrences of ambiguous 'Production Active' string across all frontend source files", () => {
  const tsFiles = scanDirectory(srcDir, (f) => f.endsWith(".ts") || f.endsWith(".tsx"));
  const offending = [];

  for (const file of tsFiles) {
    const content = fs.readFileSync(file, "utf-8");
    if (content.includes("Production Active")) {
      offending.push(file);
    }
  }

  assert.equal(
    offending.length,
    0,
    `Found 'Production Active' in files: ${offending.join(", ")}. Must use 'SIEM Rule Active' or 'Active Policy' instead.`
  );
});

test("V1.2.3 Scenario 02: diagnostics.ts deriveOperationalStatus maps approved/controlled state to 'SIEM Rule Active'", () => {
  const diagFile = path.resolve(srcDir, "lib/diagnostics.ts");
  const content = fs.readFileSync(diagFile, "utf-8");

  assert.ok(
    content.includes('label: "SIEM Rule Active"'),
    "diagnostics.ts must specify label: 'SIEM Rule Active' for operational status"
  );
  assert.ok(
    !content.includes('label: "Production Active"'),
    "diagnostics.ts must not contain label: 'Production Active'"
  );
});

test("V1.2.3 Scenario 03: ProductionReadiness types support bidirectional readiness_score and quality_score", () => {
  const typesFile = path.resolve(srcDir, "lib/api.ts");
  const content = fs.readFileSync(typesFile, "utf-8");

  assert.ok(
    content.includes("quality_score?: number | null;"),
    "ProductionReadiness response types must declare quality_score"
  );
  assert.ok(
    content.includes("readiness_score?: number | null;"),
    "ProductionReadiness response types must declare readiness_score"
  );
});

test("V1.2.3 Scenario 04: UI decoupling guarantees SIEM deployment, policy approval, readiness, and execution", () => {
  const overviewFile = path.resolve(srcDir, "components/compact/AgentIntelligenceStudioOverview.tsx");
  const content = fs.readFileSync(overviewFile, "utf-8");

  // Verify all four orthogonal dimensions exist in the component
  assert.ok(content.includes("SIEM"), "Must display SIEM rule dimension");
  assert.ok(content.includes("Policy"), "Must display Policy version dimension");
  assert.ok(content.includes("Readiness") || content.includes("readiness_status"), "Must display Readiness dimension");
  assert.ok(content.includes("Execution") || content.includes("ai_execution_status"), "Must display Execution dimension");
});
