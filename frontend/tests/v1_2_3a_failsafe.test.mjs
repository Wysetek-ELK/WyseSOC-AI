import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test("V1.2.3a Fail-Safe: page.tsx defines explicit ruleError and versionError states with race protection", () => {
  const pagePath = path.resolve(__dirname, "../src/app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  // Rule Error state and Version Error state
  assert.ok(content.includes("const [ruleError, setRuleError] = useState"), "ruleError state must be defined");
  assert.ok(content.includes("const [versionError, setVersionError] = useState"), "versionError state must be defined");
  assert.ok(content.includes("const promptRequestIdRef = useRef"), "promptRequestIdRef must guard against race conditions");

  // Fail-Safe Render Blocks
  assert.ok(content.includes('data-testid="ais-rule-not-found"'), "Must render ais-rule-not-found block on 404 rule");
  assert.ok(content.includes('data-testid="ais-version-unavailable"'), "Must render ais-version-unavailable block on 404 version");
  assert.ok(content.includes("Rule Not Found"), "Must render Rule Not Found title");
  assert.ok(content.includes("Version Unavailable"), "Must render Version Unavailable title");

  // No silent fallback to v1 on invalid requested version
  assert.ok(
    content.includes("The requested prompt policy version"),
    "Must explain that requested prompt version does not exist"
  );
  assert.ok(
    content.includes("Version Isolation Guarantee"),
    "Must state version isolation guarantee"
  );
});

test("V1.2.3a Fail-Safe: AgentIntelligenceStudioOverview handles readiness failure and clears stale data", () => {
  const compPath = path.resolve(__dirname, "../src/components/compact/AgentIntelligenceStudioOverview.tsx");
  const content = fs.readFileSync(compPath, "utf-8");

  // Readiness error state
  assert.ok(content.includes("const [readinessError, setReadinessError] = useState"), "readinessError state must exist");
  assert.ok(content.includes('READINESS_UNAVAILABLE'), "readinessBadgeMap must define READINESS_UNAVAILABLE");
  assert.ok(content.includes('READINESS UNAVAILABLE'), "READINESS UNAVAILABLE badge label must be present");
  assert.ok(content.includes('data-testid="ais-readiness-unavailable-card"'), "Must render readiness unavailable warning card");

  // Stale data cleared immediately on selection change
  assert.ok(
    content.includes("setReadinessData(null)"),
    "Must clear readinessData when selection changes"
  );

  // Approval strictly disabled on error
  assert.ok(
    content.includes("!readinessError && readinessData"),
    "Approval eligibility must require !readinessError"
  );

  // SIEM status never inferred from AI approval
  assert.ok(
    !content.includes('selectedVersion?.status === "APPROVED" ? "ACTIVE" : "NOT_DEPLOYED"'),
    "Must NEVER infer SIEM rule deployment status from AI policy approval!"
  );
});

test("V1.2.3a SIEM Status Source: CompactPageHeader displays decoupled SIEM and Policy badges", () => {
  const cdsPath = path.resolve(__dirname, "../src/components/compact/CompactDesignSystem.tsx");
  const cdsContent = fs.readFileSync(cdsPath, "utf-8");

  assert.ok(cdsContent.includes('siemStatus?:'), "CompactPageHeaderProps must accept siemStatus");
  assert.ok(cdsContent.includes('data-testid="header-siem-rule-status"'), "Must render header-siem-rule-status");
  assert.ok(cdsContent.includes('data-testid="header-policy-lifecycle-status"'), "Must render header-policy-lifecycle-status");

  const diagPath = path.resolve(__dirname, "../src/lib/diagnostics.ts");
  const diagContent = fs.readFileSync(diagPath, "utf-8");

  assert.ok(diagContent.includes("export function deriveSiemRuleStatus"), "Must export deriveSiemRuleStatus");
  assert.ok(diagContent.includes("SIEM Rule Active"), "deriveSiemRuleStatus must return SIEM Rule Active on ACTIVE");
  assert.ok(diagContent.includes("SIEM Rule Inactive"), "deriveSiemRuleStatus must return SIEM Rule Inactive on INACTIVE");
});

test("V1.2.3a UI Error-State Invariants: Header badge suppression, stale data clearing, race-guards & fallback dropdown", () => {
  const pagePath = path.resolve(__dirname, "../src/app/agent-intelligence-studio/page.tsx");
  const content = fs.readFileSync(pagePath, "utf-8");

  // 1. Race condition guards across all fetchers
  assert.ok(content.includes("fetchIntelligence = async"), "fetchIntelligence defined");
  assert.ok(content.includes("fetchDriftEvents = async"), "fetchDriftEvents defined");
  assert.ok(content.includes("fetchQualityPreview = async"), "fetchQualityPreview defined");
  assert.ok(content.includes("fetchLearningProfile = async"), "fetchLearningProfile defined");

  // All fetchers check promptRequestIdRef
  const fetchIntelMatch = content.match(/fetchIntelligence[\s\S]*?reqId !== promptRequestIdRef\.current/);
  assert.ok(fetchIntelMatch, "fetchIntelligence must guard against race condition using promptRequestIdRef");

  const fetchQualityMatch = content.match(/fetchQualityPreview[\s\S]*?reqId !== promptRequestIdRef\.current/);
  assert.ok(fetchQualityMatch, "fetchQualityPreview must guard against race condition using promptRequestIdRef");

  const fetchDriftMatch = content.match(/fetchDriftEvents[\s\S]*?reqId !== promptRequestIdRef\.current/);
  assert.ok(fetchDriftMatch, "fetchDriftEvents must guard against race condition using promptRequestIdRef");

  const fetchLearningMatch = content.match(/fetchLearningProfile[\s\S]*?reqId !== promptRequestIdRef\.current/);
  assert.ok(fetchLearningMatch, "fetchLearningProfile must guard against race condition using promptRequestIdRef");

  // 2. Stale data cleared immediately on rule / version error
  assert.ok(content.includes("setIntelligenceData(null)"), "Must clear intelligenceData on error");
  assert.ok(content.includes("setLearningProfile(null)"), "Must clear learningProfile on error");
  assert.ok(content.includes("setQualityAssessment(null)"), "Must clear qualityAssessment on error");
  assert.ok(content.includes("setDriftEvents([])"), "Must clear driftEvents on error");
  assert.ok(content.includes("setSimulationResult(null)"), "Must clear simulationResult on error");

  // 3. Header badge suppression on error (no false 'Ready for Learning')
  assert.ok(
    content.includes("ruleError ? undefined : deriveSiemRuleStatus(selectedRule?.status)"),
    "Must suppress siemStatus in header when ruleError is active"
  );
  assert.ok(
    content.includes("title={ruleError ? \"Rule Not Found\" : (selectedRule?.name || selectedRuleId)}"),
    "Must render 'Rule Not Found' in title on ruleError"
  );
  assert.ok(
    /lifecycleStatus=\{[\s\S]*?ruleError[\s\S]*?\? undefined[\s\S]*?: versionError/.test(content),
    "Must suppress lifecycle readiness badges when ruleError is active"
  );

  // 4. Dropdown fallback for invalid rule_id
  assert.ok(
    content.includes("-- Rule Not Found ("),
    "Dropdown must render '-- Rule Not Found ({selectedRuleId}) --' disabled option when rule_id is not in catalog"
  );
});
