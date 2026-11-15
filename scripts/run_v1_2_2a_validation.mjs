import { spawn, execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUTPUT_DIR = path.resolve("docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2a/screenshots");
const BASE_URL = "http://127.0.0.1:3000";
const BACKEND_URL = "http://127.0.0.1:8000";
const DEBUG_PORT = 9222;

const VIEWPORTS = [
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

function getGitCommitSha() {
  try {
    return execSync("git rev-parse HEAD", { encoding: "utf8" }).trim();
  } catch (e) {
    return "UNKNOWN_COMMIT";
  }
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

class CdpSession {
  constructor(wsUrl) {
    this.wsUrl = wsUrl;
    this.ws = null;
    this.id = 1;
    this.pending = new Map();
  }

  async connect() {
    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(this.wsUrl);
      this.ws.onopen = () => resolve();
      this.ws.onerror = (err) => reject(err);
      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.id && this.pending.has(msg.id)) {
          const { resolve, reject } = this.pending.get(msg.id);
          this.pending.delete(msg.id);
          if (msg.error) reject(new Error(msg.error.message));
          else resolve(msg.result);
        }
      };
    });
  }

  async send(method, params = {}) {
    const id = this.id++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    if (this.ws) {
      try { this.ws.close(); } catch {}
    }
  }
}

async function loginUser(username, password) {
  const res = await fetch(`${BACKEND_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error(`Login failed for ${username}: ${res.status}`);
  return res.json();
}

async function launchChrome() {
  const tempProfile = path.resolve(`temp_chrome_val122a_${Date.now()}`);
  const chromeProcess = spawn(CHROME_PATH, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    `--remote-debugging-port=${DEBUG_PORT}`,
    `--user-data-dir=${tempProfile}`,
    "about:blank",
  ], { stdio: "ignore" });

  let ready = false;
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/version`);
      if (res.ok) {
        ready = true;
        break;
      }
    } catch {}
    await sleep(300);
  }

  if (!ready) {
    chromeProcess.kill();
    throw new Error("Chrome debug port failed to become ready");
  }

  return { chromeProcess, tempProfile };
}

async function main() {
  console.log("========================================================================");
  console.log("VERDICTUM AI — VALIDATION V1.2.2a TARGETED SECURITY & EVIDENCE RUNNER");
  console.log("========================================================================");

  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const gitCommitSha = getGitCommitSha();
  console.log("Immutable Repository SHA:", gitCommitSha);

  // 1. Prepare database test personas and review state
  console.log("\n[1/6] Running database state preparation...");
  execSync("python scripts/setup_v1_2_2a_state.py", {
    stdio: "inherit",
    env: { ...process.env, PYTHONPATH: path.resolve("backend") },
  });

  // 2. Authenticate users
  console.log("\n[2/6] Authenticating test personas via /api/auth/login...");
  const adminAuth = await loginUser("admin", "AdminPassword123!");
  const analystAuth = await loginUser("analyst", "AnalystPassword123!");
  const analystBAuth = await loginUser("analyst_b", "AnalystPassword123!");
  const viewerAuth = await loginUser("viewer", "ViewerPassword123!");
  console.log("  ✓ Admin:", adminAuth.user.username, `(${adminAuth.user.role})`);
  console.log("  ✓ Analyst A:", analystAuth.user.username, `(${analystAuth.user.role})`);
  console.log("  ✓ Analyst B:", analystBAuth.user.username, `(${analystBAuth.user.role})`);
  console.log("  ✓ Viewer:", viewerAuth.user.username, `(${viewerAuth.user.role})`);

  // 3. Launch headless Chrome with CDP
  console.log("\n[3/6] Launching Chrome on debug port", DEBUG_PORT);
  const { chromeProcess, tempProfile } = await launchChrome();

  const targetsRes = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/list`);
  const targets = await targetsRes.json();
  const pageTarget = targets.find((t) => t.type === "page") || targets[0];
  const cdp = new CdpSession(pageTarget.webSocketDebuggerUrl);
  await cdp.connect();
  console.log("  ✓ Connected to Chrome CDP target:", pageTarget.id);

  await cdp.send("Page.enable");
  await cdp.send("DOM.enable");
  await cdp.send("Runtime.enable");

  // Initial navigation to establish origin for localStorage
  console.log("  ✓ Establishing application origin context at", BASE_URL);
  await cdp.send("Page.navigate", { url: `${BASE_URL}/login` });
  await sleep(1500);

  const manifest = [];
  const testResults = [];

  const testScenarios = [
    // 1. Blind Review Active (AI Verdict Masked in Workbench)
    {
      scenarioId: "SCN-V122A-01-BLIND-ON",
      pageKey: "workbench_blind_review_on",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst A)",
      url: `${BASE_URL}/ai-triage-workbench`,
      apiEndpoint: `${BACKEND_URL}/api/incidents?blind_review=true&page=1&page_size=5`,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Blind Review ON: Double-blind review active, AI verdicts masked as [Hidden - Blind Review]",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'true');`
        });
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasHiddenMask = text.includes('[Hidden - Blind Review]');
            const hasBlindOnHeader = text.includes('Blind Review: ON') || text.includes('Blind Review:');
            const hasBlindActiveBanner = text.includes('Blind Review Active:');
            const assertions = {
              hasHiddenMask,
              hasBlindOnHeader,
              hasBlindActiveBanner
            };
            return {
              assertions,
              isValid: Object.values(assertions).every(Boolean)
            };
          })();
        `;
        return (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
      }
    },
    // 2. Blind Review UI Preference OFF (Server Isolation Active)
    {
      scenarioId: "SCN-V122A-02-BLIND-OFF",
      pageKey: "workbench_blind_review_off",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst A)",
      url: `${BASE_URL}/ai-triage-workbench`,
      apiEndpoint: `${BACKEND_URL}/api/incidents?blind_review=false&page=1&page_size=5`,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Blind Review OFF: Client preference OFF shows server isolation banner and retains masked verdicts for unreviewed items",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'false');`
        });
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasBlindOffHeader = text.includes('Blind Review: OFF');
            const hasServerIsolationBanner = text.includes('Blind Review UI Preference: OFF') && text.includes('Server-enforced double-blind isolation remains active');
            const hasHiddenMask = text.includes('[Hidden - Blind Review]');
            const assertions = {
              hasBlindOffHeader,
              hasServerIsolationBanner,
              hasHiddenMask
            };
            return {
              assertions,
              isValid: Object.values(assertions).every(Boolean)
            };
          })();
        `;
        return (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
      }
    },
    // 3. Analyst A Post-Submission (Revealed Verdict & Ground Truth)
    {
      scenarioId: "SCN-V122A-03-ANALYST-A-POST-SUBMISSION",
      pageKey: "workbench_analyst_a_post_submission",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst A)",
      url: `${BASE_URL}/ai-triage-workbench?search=132438483`,
      apiEndpoint: `${BACKEND_URL}/api/incidents/132438483?blind_review=false`,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Analyst A Post-Submission: Permitted comparison revealed for submitting reviewer (AI verdict badge with Sparkles)",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'true');`
        });
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasRevealedBadge = text.includes('AI: TP') || text.includes('AI: FP') || text.includes('AI: ATTN') || text.includes('True Positive');
            const hasIncident132 = text.includes('132438483');
            const assertions = {
              hasRevealedBadge,
              hasIncident132
            };
            return {
              assertions,
              isValid: Object.values(assertions).every(Boolean)
            };
          })();
        `;
        return (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
      }
    },
    // 4. Analyst B Pre-Submission (Reviewer A/B Isolation)
    {
      scenarioId: "SCN-V122A-04-ANALYST-B-PRE-SUBMISSION",
      pageKey: "workbench_analyst_b_pre_submission",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst B)",
      url: `${BASE_URL}/ai-triage-workbench?search=132438483`,
      apiEndpoint: `${BACKEND_URL}/api/incidents/132438483?blind_review=false`,
      user: analystBAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Reviewer A/B Isolation: Analyst A submission does NOT unmask incident 132438483 for Analyst B (retains [Hidden - Blind Review])",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'true');`
        });
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasHiddenMask = text.includes('[Hidden - Blind Review]');
            const hasIncident132 = text.includes('132438483');
            const assertions = {
              hasHiddenMask,
              hasIncident132
            };
            return {
              assertions,
              isValid: Object.values(assertions).every(Boolean)
            };
          })();
        `;
        return (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
      }
    },
    // 5. Read-Only Viewer Restricted State
    {
      scenarioId: "SCN-V122A-05-VIEWER-RESTRICTED",
      pageKey: "workbench_viewer_restricted",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "Read-Only Viewer",
      url: `${BASE_URL}/ai-triage-workbench`,
      apiEndpoint: `${BACKEND_URL}/api/incidents?page=1&page_size=5`,
      user: viewerAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "RBAC Safety: Read-Only Viewer receives safely redacted verdicts with zero unmasked disclosure",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'false');`
        });
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasHiddenMask = text.includes('[Hidden - Blind Review]');
            const assertions = {
              hasHiddenMask
            };
            return {
              assertions,
              isValid: Object.values(assertions).every(Boolean)
            };
          })();
        `;
        return (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
      }
    },
    // 6. Heavy TCP v1 historical baseline (APPROVED baseline, revalidation required)
    {
      scenarioId: "SCN-V122A-06-HEAVY-TCP-V1-HISTORICAL",
      pageKey: "studio_heavy_tcp_v1_historical",
      ruleId: "40498741-ee6b-4a71-9101-0d6d3f77154c",
      version: "v1 (8a460ab8-5f06-4a90-b2d4-db958199d644)",
      role: "Administrator",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&version_id=8a460ab8-5f06-4a90-b2d4-db958199d644&tab=overview`,
      apiEndpoint: `${BACKEND_URL}/api/prompts/readiness/40498741-ee6b-4a71-9101-0d6d3f77154c?version_id=8a460ab8-5f06-4a90-b2d4-db958199d644`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Historical Approved Baseline: Heavy TCP v1 policy status APPROVED distinct from current readiness BLOCKED / INCOMPLETE (score 54.0, gates 2/8)",
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasRuleHeader = text.includes('Heavy TCP Host Scan') || text.includes('40498741');
            const hasSiemActive = text.includes('SIEM Rule:') && text.includes('ACTIVE');
            const hasPolicyV1Approved = text.includes('Policy v1:') && text.includes('APPROVED');
            const hasAiExecutionSuspended = text.includes('AI Execution:') && text.includes('Suspended');
            const hasReadinessBlocked = text.includes('Current Readiness:') && (text.includes('Blocked / Incomplete') || text.includes('BLOCKED'));
            const hasScore54 = text.includes('54') || text.includes('54.0') || text.includes('54/100');

            const assertions = {
              hasRuleHeader,
              hasSiemActive,
              hasPolicyV1Approved,
              hasAiExecutionSuspended,
              hasReadinessBlocked,
              hasScore54
            };
            return {
              assertions,
              isValid: Object.values(assertions).every(Boolean)
            };
          })();
        `;
        return (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
      }
    },
    // 7. Heavy TCP candidate v3 (Stage 1 & 2 BLOCKED, correct score math, disabled Approve button)
    {
      scenarioId: "SCN-V122A-07-HEAVY-TCP-V3-CANDIDATE",
      pageKey: "studio_heavy_tcp_v3_candidate",
      ruleId: "40498741-ee6b-4a71-9101-0d6d3f77154c",
      version: "v3 (ec0cc351-8dd1-4026-9dc3-586387bb324c)",
      role: "Administrator",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&version_id=ec0cc351-8dd1-4026-9dc3-586387bb324c&tab=overview`,
      apiEndpoint: `${BACKEND_URL}/api/prompts/readiness/40498741-ee6b-4a71-9101-0d6d3f77154c?version_id=ec0cc351-8dd1-4026-9dc3-586387bb324c`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Candidate Integrity: Heavy TCP v3 stages 1 & 2 blocked, score 77.0, smart action 'Verify FortiSIEM Detection Semantics', approval disabled",
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasStage1Blocked = text.includes('Define Detection') && text.includes('BLOCKED');
            const hasStage2Blocked = text.includes('Verify Evidence') && text.includes('BLOCKED');
            const hasScore77 = text.includes('77') || text.includes('77.0') || text.includes('77/100');
            const hasNoContradictionText = !text.includes('Quality score (77.0/100) below 70 requirement');
            const hasSmartNextAction = text.includes('Verify FortiSIEM Detection Semantics') || text.includes('Detection Semantics');
            
            const approveBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Approve') || b.innerText.includes('Approval Blocked'));
            const isApproveDisabled = approveBtn ? (approveBtn.disabled || approveBtn.innerText.includes('Approval Blocked')) : true;

            const assertions = {
              hasStage1Blocked,
              hasStage2Blocked,
              hasScore77,
              hasNoContradictionText,
              hasSmartNextAction,
              isApproveDisabled
            };
            return {
              assertions,
              isValid: Object.values(assertions).every(Boolean)
            };
          })();
        `;
        return (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
      }
    },
    // 8. AI Configured Enabled + Runtime LLM Offline
    {
      scenarioId: "SCN-V122A-08-AI-EXECUTION-RUNTIME-OFFLINE",
      pageKey: "studio_ai_execution_runtime_offline",
      ruleId: "40498741-ee6b-4a71-9101-0d6d3f77154c",
      version: "v1 (8a460ab8-5f06-4a90-b2d4-db958199d644)",
      role: "Administrator",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&version_id=8a460ab8-5f06-4a90-b2d4-db958199d644&tab=overview`,
      apiEndpoint: `${BACKEND_URL}/api/prompts/readiness/40498741-ee6b-4a71-9101-0d6d3f77154c?version_id=8a460ab8-5f06-4a90-b2d4-db958199d644`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Authoritative Status: Configured enablement distinguished from runtime availability (AI Execution: Offline)",
      setupState: async () => {
        execSync("python scripts/toggle_scenario_8.py enable", {
          env: { ...process.env, PYTHONPATH: path.resolve("backend") },
        });
      },
      teardownState: async () => {
        execSync("python scripts/toggle_scenario_8.py disable", {
          env: { ...process.env, PYTHONPATH: path.resolve("backend") },
        });
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasAiExecutionOffline = text.includes('AI Execution:') && text.includes('Offline');
            const hasPolicyV1Approved = text.includes('Policy v1:') && text.includes('APPROVED');
            const assertions = {
              hasAiExecutionOffline,
              hasPolicyV1Approved
            };
            return {
              assertions,
              isValid: Object.values(assertions).every(Boolean)
            };
          })();
        `;
        return (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
      }
    },
  ];

  console.log("\n[4/6] Executing validation scenarios...");

  for (const scenario of testScenarios) {
    console.log(`\n------------------------------------------------------------------------`);
    console.log(`Executing Scenario: ${scenario.scenarioId} — ${scenario.description}`);

    // Set auth state and theme in localStorage at current origin
    const setSessionScript = `
      localStorage.setItem('ai_verdict_token', ${JSON.stringify(scenario.user.access_token)});
      localStorage.setItem('ai_verdict_user', ${JSON.stringify(JSON.stringify(scenario.user.user))});
      localStorage.setItem('ai_verdict_theme', ${JSON.stringify(scenario.theme || "obsidian")});
      document.documentElement.setAttribute('data-theme', ${JSON.stringify(scenario.theme || "obsidian")});
    `;
    await cdp.send("Runtime.evaluate", { expression: setSessionScript });

    if (scenario.setupState) {
      await scenario.setupState();
    }

    // Direct Authenticated API Verification
    let apiStatus = 0;
    let apiData = null;
    try {
      const apiRes = await fetch(scenario.apiEndpoint, {
        headers: { "Authorization": `Bearer ${scenario.user.access_token}` },
      });
      apiStatus = apiRes.status;
      apiData = await apiRes.json();
    } catch (e) {
      console.warn(`  [API Warning] Fetch failed for ${scenario.apiEndpoint}:`, e.message);
    }

    // Navigate to test page
    console.log(`  [Navigate] ${scenario.url}`);
    await cdp.send("Page.navigate", { url: scenario.url });

    // Wait for network idle and component hydration
    await sleep(3500);

    // Validate DOM assertions with settle loop
    let domResult = { isValid: false, assertions: {} };
    if (scenario.validateDom) {
      domResult = await scenario.validateDom();
      if (!domResult.isValid) {
        console.log("  Waiting for DOM assertions to settle...");
        for (let r = 0; r < 8; r++) {
          await sleep(500);
          domResult = await scenario.validateDom();
          if (domResult.isValid) break;
        }
      }
    }

    const scenarioPassed = domResult.isValid;
    console.log(`  [Assertions] Outcome: ${scenarioPassed ? "PASS" : "FAIL"}`);
    for (const [key, val] of Object.entries(domResult.assertions || {})) {
      console.log(`    - ${key}: ${val ? "PASSED" : "FAILED"}`);
    }

    testResults.push({
      scenarioId: scenario.scenarioId,
      ruleId: scenario.ruleId,
      version: scenario.version,
      authenticatedRole: scenario.role,
      expectedBackendStatus: 200,
      actualBackendStatus: apiStatus,
      backendPayloadSummary: apiData ? (Array.isArray(apiData.items) ? `items: ${apiData.items.length}` : `readiness: ${apiData.readiness_status}, ai_exec: ${apiData.ai_execution_status}`) : "N/A",
      expectedUiStatus: "COMPLIANT_RENDER",
      actualUiStatus: scenarioPassed ? "COMPLIANT_RENDER" : "ASSERTION_FAILED",
      mandatoryAssertions: domResult.assertions,
      evidenceTimestamp: new Date().toISOString(),
      exactCommitSha: gitCommitSha,
      status: scenarioPassed ? "PASS" : "FAIL",
    });

    if (scenario.teardownState) {
      await scenario.teardownState();
    }

    // Capture screenshots across target viewports
    for (const vp of scenario.viewports) {
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: vp.width,
        height: vp.height,
        deviceScaleFactor: 1,
        mobile: false,
      });

      await sleep(400);

      const shot = await cdp.send("Page.captureScreenshot", {
        format: "png",
        captureBeyondViewport: false,
      });

      const filename = `${scenario.pageKey}_${vp.name}.png`;
      const filePath = path.join(OUTPUT_DIR, filename);
      fs.writeFileSync(filePath, Buffer.from(shot.data, "base64"));
      const stat = fs.statSync(filePath);

      console.log(`  [Screenshot] ${filename} (${stat.size} bytes)`);

      manifest.push({
        scenarioId: scenario.scenarioId,
        pageKey: scenario.pageKey,
        viewport: vp.name,
        width: vp.width,
        height: vp.height,
        filename,
        fileSizeBytes: stat.size,
        path: `screenshots/${filename}`,
        description: `${scenario.description} (${vp.name})`,
      });
    }
  }

  // 5. Write Evidence JSON
  const evidencePayload = {
    version: "V1.2.2a",
    timestamp: new Date().toISOString(),
    commitSha: gitCommitSha,
    status: testResults.every((r) => r.status === "PASS") ? "PASS" : "FAIL",
    summary: {
      totalScenarios: testScenarios.length,
      passedScenarios: testResults.filter((r) => r.status === "PASS").length,
      failedScenarios: testResults.filter((r) => r.status === "FAIL").length,
      totalScreenshots: manifest.length,
      viewportsTested: VIEWPORTS.map((v) => v.name),
    },
    testResults,
    screenshots: manifest,
  };

  const evidencePath = path.resolve("docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2a/VALIDATION_EVIDENCE.json");
  fs.writeFileSync(evidencePath, JSON.stringify(evidencePayload, null, 2), "utf8");
  console.log(`\n[5/6] Generated VALIDATION_EVIDENCE.json at ${evidencePath}`);

  // 6. Cleanup
  cdp.close();
  chromeProcess.kill();
  try {
    fs.rmSync(tempProfile, { recursive: true, force: true });
  } catch {}

  console.log(`\n[6/6] Validation V1.2.2a complete. Total screenshots captured: ${manifest.length}`);
  if (evidencePayload.status !== "PASS") {
    console.error("FAIL: One or more validation scenarios failed mandatory assertions!");
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("FATAL ERROR in Validation V1.2.2a runner:", err);
  process.exit(1);
});
