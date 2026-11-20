import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_SRC = path.resolve(__dirname, "../src");
const BACKEND_SRC = path.resolve(__dirname, "../../backend/app");

test("Phase 2 & 3: ReviewIncidentsWorkbench strictly enforces true Double-Blind masking pre-submission", () => {
  const workbenchPath = path.join(FRONTEND_SRC, "components/compact/ReviewIncidentsWorkbench.tsx");
  const content = fs.readFileSync(workbenchPath, "utf-8");

  // 1. Mandatory double-blind status indicator
  assert.ok(content.includes("Double-Blind Active (AI Determination Masked)"), "Must display active double-blind badge");

  // 2. Pre-submission choices must be strictly TRUE_POSITIVE, FALSE_POSITIVE, INSUFFICIENT_EVIDENCE
  assert.ok(content.includes('"TRUE_POSITIVE"'), "Must provide TRUE_POSITIVE choice");
  assert.ok(content.includes('"FALSE_POSITIVE"'), "Must provide FALSE_POSITIVE choice");
  assert.ok(content.includes('"INSUFFICIENT_EVIDENCE"'), "Must provide INSUFFICIENT_EVIDENCE choice");

  // 3. Must NOT present derived outcomes as pre-submission analyst options
  assert.ok(!content.includes('value="AGREE_TP"'), "Must not present AGREE_TP as selectable verdict");
  assert.ok(!content.includes('value="AGREE_FP"'), "Must not present AGREE_FP as selectable verdict");
  assert.ok(!content.includes('value="MISSED_TP"'), "Must not present MISSED_TP as selectable verdict");
  assert.ok(!content.includes('value="FALSE_ALARM"'), "Must not present FALSE_ALARM as selectable verdict");

  // 4. Pre-submission header must not have Inspect Payload leakage button
  assert.ok(!content.includes('Inspect Payload\n                  </button>'), "Must not contain pre-submission Inspect Payload button");

  // 5. Post-submission reveal must handle empty AI evaluation with explicit fallback
  assert.ok(content.includes('AI Evaluation Not Available'), "Must display 'AI Evaluation Not Available' when AI evaluation is missing");

  // 6. Post-submission prompt inspection must be available safely
  assert.ok(content.includes('Inspect LLM Prompt Capture'), "Must offer safe prompt inspection only post-submission");
});

test("Phase 2 & 3: Backend API and service enforce strict verdict validation and server-side masking", () => {
  const apiPath = path.join(BACKEND_SRC, "api/rule_learning.py");
  const apiContent = fs.readFileSync(apiPath, "utf-8");

  // Rejection of derived outcomes in SubmitReviewRequest
  assert.ok(apiContent.includes("is a derived post-comparison outcome and cannot be submitted"), "API schema must reject derived outcomes");
  assert.ok(apiContent.includes("TRUE_POSITIVE"), "Must allow TRUE_POSITIVE");
  assert.ok(apiContent.includes("FALSE_POSITIVE"), "Must allow FALSE_POSITIVE");
  assert.ok(apiContent.includes("INSUFFICIENT_EVIDENCE"), "Must allow INSUFFICIENT_EVIDENCE");

  // AnalystReviewService strict validation
  const servicePath = path.join(BACKEND_SRC, "services/analyst_review_service.py");
  const serviceContent = fs.readFileSync(servicePath, "utf-8");
  assert.ok(serviceContent.includes("getattr(inc, \"events\", None) or []"), "Must reliably read events relationship");
  assert.ok(serviceContent.includes("norm_verdict not in (\"TRUE_POSITIVE\", \"FALSE_POSITIVE\", \"INSUFFICIENT_EVIDENCE\")"), "Service must strictly validate analyst verdict");

  // IncidentService case-insensitive role check
  const incServicePath = path.join(BACKEND_SRC, "services/incident_service.py");
  const incContent = fs.readFileSync(incServicePath, "utf-8");
  assert.ok(incContent.includes("norm_role in (\"soc analyst\", \"analyst\", \"security analyst\", \"senior analyst\", \"soc_analyst\", \"senior_analyst\")"), "Must support analyst role variants");
});

test("Phase 8: AIS Page wires ReviewIncidentsWorkbench with safe post-submission prompt inspection", () => {
  const pagePath = path.join(FRONTEND_SRC, "app/agent-intelligence-studio/page.tsx");
  const pageContent = fs.readFileSync(pagePath, "utf-8");

  assert.ok(pageContent.includes("<ReviewIncidentsWorkbench"), "Page must embed ReviewIncidentsWorkbench");
  assert.ok(pageContent.includes("onOpenActualPrompt="), "Page must wire onOpenActualPrompt for post-submission inspection");
});
