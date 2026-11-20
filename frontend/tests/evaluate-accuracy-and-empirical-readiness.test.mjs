import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_SRC = path.resolve(__dirname, "../src");
const BACKEND_SRC = path.resolve(__dirname, "../../backend/app");

test("Evaluate Accuracy & Empirical Readiness: API client implements evaluateRuleAccuracy", () => {
  const apiPath = path.join(FRONTEND_SRC, "lib/api.ts");
  const content = fs.readFileSync(apiPath, "utf-8");

  assert.ok(
    content.includes("evaluateRuleAccuracy(ruleId: string"),
    "api.ts must define evaluateRuleAccuracy method"
  );
  assert.ok(
    content.includes("/learning/rules/${encodeURIComponent(ruleId)}/evaluate-accuracy"),
    "evaluateRuleAccuracy must hit POST /api/learning/rules/{rule_id}/evaluate-accuracy"
  );
  assert.ok(
    content.includes('"Content-Type": "application/json"'),
    "evaluateRuleAccuracy must send application/json header"
  );
});

test("Evaluate Accuracy & Empirical Readiness: AccuracyLearningSummary provides evaluation action, diagnostic alert, and zero-matrix explanation", () => {
  const summaryPath = path.join(FRONTEND_SRC, "components/compact/AccuracyLearningSummary.tsx");
  const content = fs.readFileSync(summaryPath, "utf-8");

  // 1. Evaluate accuracy button must exist
  assert.ok(
    content.includes("handleEvaluateAccuracy"),
    "Must implement handleEvaluateAccuracy click handler"
  );
  assert.ok(
    content.includes("api.evaluateRuleAccuracy"),
    "handleEvaluateAccuracy must call api.evaluateRuleAccuracy"
  );
  assert.ok(
    content.includes("Evaluate Accuracy"),
    "Must display 'Evaluate Accuracy' button in UI"
  );

  // 2. Clear explanation when accuracy is N/A despite existing ground truth reviews
  assert.ok(
    content.includes("Empirical Accuracy: NOT MEASURABLE (0 Decisive AI Predictions)"),
    "Must display diagnostic banner explaining why accuracy is N/A when 0 decisive predictions exist"
  );
  assert.ok(
    content.includes("DECISIVE PREDICTIONS NEEDED"),
    "Must badge the state as requiring decisive predictions"
  );

  // 3. Class balance notice
  assert.ok(
    content.includes("Pilot Class Balance Deficit:"),
    "Must inform user of pilot class balance requirements (>= 10 TP, >= 10 FP)"
  );

  // 4. Confusion matrix zero-value diagnostic explanation
  assert.ok(
    content.includes("Why is the confusion matrix currently zero?"),
    "Must provide plain-English explanation for why confusion matrix is zero"
  );
  assert.ok(
    content.includes("analyst_resolved_abstention"),
    "Must identify analyst-resolved abstentions in confusion matrix diagnostics"
  );
  assert.ok(
    content.includes("analyst_only_initial_benchmark"),
    "Must identify analyst-only initial benchmarks in confusion matrix diagnostics"
  );
});

test("Evaluate Accuracy & Empirical Readiness: AIS Page wires evaluate handler and corrects next recommended action", () => {
  const pagePath = path.join(FRONTEND_SRC, "app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  // 1. handleEvaluateAccuracy implementation
  assert.ok(
    content.includes("handleEvaluateAccuracy"),
    "page.tsx must implement handleEvaluateAccuracy"
  );
  assert.ok(
    content.includes("api.evaluateRuleAccuracy(selectedRuleId"),
    "handleEvaluateAccuracy must call api.evaluateRuleAccuracy with selectedRuleId"
  );

  // 2. Next Recommended Action must handle Class Balance Deficit (0 TP / 31 FP)
  assert.ok(
    content.includes("Collect True Positive Ground Truth"),
    "nextRecommendedAction must identify when True Positive ground truth is missing"
  );
  assert.ok(
    content.includes("Class Balance Needed"),
    "nextRecommendedAction must badge incomplete class balance"
  );

  // 3. Next Recommended Action action must execute evaluation rather than passive tab switch
  assert.ok(
    content.includes("action: handleEvaluateAccuracy"),
    "nextRecommendedAction action must invoke handleEvaluateAccuracy for Evaluate Accuracy"
  );

  // 4. fetchLearningProfile race condition protection
  assert.ok(
    !content.includes("if (reqId !== promptRequestIdRef.current) return;\n      setLearningProfile(data);"),
    "fetchLearningProfile must not be cancelled by promptRequestIdRef race condition"
  );

  // 5. ReviewIncidentsWorkbench receives learningProfile prop
  assert.ok(
    content.includes("learningProfile={learningProfile}"),
    "ReviewIncidentsWorkbench must receive learningProfile prop from page state"
  );
});

test("Evaluate Accuracy & Empirical Readiness: Backend API and service enforce mathematical evaluation without fabrication", () => {
  const apiPath = path.join(BACKEND_SRC, "api/rule_learning.py");
  const apiContent = fs.readFileSync(apiPath, "utf-8");

  assert.ok(
    apiContent.includes('@router.post("/learning/rules/{rule_id}/evaluate-accuracy"'),
    "API must expose POST /learning/rules/{rule_id}/evaluate-accuracy"
  );
  assert.ok(
    apiContent.includes("RuleLearningService.evaluate_rule_accuracy("),
    "Endpoint must delegate to RuleLearningService.evaluate_rule_accuracy"
  );

  const servicePath = path.join(BACKEND_SRC, "services/rule_learning_service.py");
  const serviceContent = fs.readFileSync(servicePath, "utf-8");

  assert.ok(
    serviceContent.includes("async def evaluate_rule_accuracy("),
    "RuleLearningService must define evaluate_rule_accuracy classmethod"
  );
  assert.ok(
    serviceContent.includes("total_decisive = agreement_tp + agreement_fp + ai_false_alarm + critical_missed_tp"),
    "Must strictly compute decisive automated evaluations"
  );
  assert.ok(
    serviceContent.includes("empirical_accuracy = None"),
    "Must return empirical_accuracy = None when decisive evaluations == 0"
  );
  assert.ok(
    serviceContent.includes("is_pilot_balanced = verified_tp >= pilot_tp_required and verified_fp >= pilot_fp_required"),
    "Must check pilot class balance (>= 10 TP and >= 10 FP)"
  );
});
