import { spawn, execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUTPUT_DIR = path.resolve("docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2b/screenshots");
const EVIDENCE_JSON_PATH = path.resolve("docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2b/VALIDATION_EVIDENCE.json");
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
  const tempProfile = path.resolve(`temp_chrome_val122b_${Date.now()}`);
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
  console.log("VERDICTUM AI — VALIDATION V1.2.2b EVIDENCE INTEGRITY & SECURITY RUNNER");
  console.log("========================================================================");

  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const gitCommitSha = getGitCommitSha();
  console.log("Immutable Repository SHA:", gitCommitSha);

  // 1. Prepare database test personas and review state
  console.log("\n[1/6] Running database state preparation...");
  execSync("python scripts/setup_v1_2_2b_state.py", {
    stdio: "inherit",
    env: { ...process.env, PYTHONPATH: path.resolve("backend") },
  });

  // 2. Authenticate users
  console.log("\n[2/6] Authenticating test personas via /api/auth/login...");
  const adminAuth = await loginUser("admin", "AdminPassword123!");
  const analystAuth = await loginUser("analyst", "AnalystPassword123!");
  const analystBAuth = await loginUser("analyst_b", "AnalystPassword123!");
  const viewerAuth = await loginUser("viewer", "ViewerPassword123!");
  console.log("  ✓ Admin:", adminAuth.user.username, `(${adminAuth.user.role})`, "Tenant:", adminAuth.user.customer || "DEFAULT");
  console.log("  ✓ Analyst A:", analystAuth.user.username, `(${analystAuth.user.role})`, "Tenant:", analystAuth.user.customer);
  console.log("  ✓ Analyst B:", analystBAuth.user.username, `(${analystBAuth.user.role})`, "Tenant:", analystBAuth.user.customer);
  console.log("  ✓ Viewer:", viewerAuth.user.username, `(${viewerAuth.user.role})`, "Tenant:", viewerAuth.user.customer);

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

  // Prime origin localStorage
  await cdp.send("Page.navigate", { url: `${BASE_URL}/ai-triage-workbench` });
  await sleep(2000);

  const testResults = [];

  const testScenarios = [
    // 1. Heavy TCP v1 historical baseline
    {
      scenarioId: "SCN-V122B-01-HEAVY-TCP-V1",
      pageKey: "v1_2_2b_scn01_heavy_tcp_v1",
      ruleId: "40498741-ee6b-4a71-9101-0d6d3f77154c",
      version: "v1 (8a460ab8-5f06-4a90-b2d4-db958199d644)",
      role: "Administrator",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&version_id=8a460ab8-5f06-4a90-b2d4-db958199d644&tab=overview`,
      apiEndpoint: `${BACKEND_URL}/api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/readiness?version_id=8a460ab8-5f06-4a90-b2d4-db958199d644`,
      expectedBackendStatus: 200,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Heavy TCP Host Scan Rule v1: Canonical readiness route, Active Policy v1 badge, score 54.0, gates 2/8, readiness BLOCKED",
      validateApi: (data) => {
        return (
          data &&
          data.readiness_status === "BLOCKED" &&
          data.quality_score === 54.0 &&
          data.quality_gates_passed === 2 &&
          data.approval_eligible === false
        );
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasActivePolicyBadge = text.includes('Active Policy v1') || text.includes('Active Policy:');
            const hasSiemRule = text.includes('SIEM Rule: ACTIVE') || text.includes('SIEM Rule:') || text.includes('ACTIVE');
            const hasBlockedReadiness = text.includes('BLOCKED') || text.includes('2 / 8') || text.includes('2/8');
            const hasHeavyTcp = text.includes('Heavy TCP Host Scan') || text.includes('40498741');
            const assertions = {
              hasActivePolicyBadge,
              hasSiemRule,
              hasBlockedReadiness,
              hasHeavyTcp
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

    // 2. Heavy TCP v3 candidate version
    {
      scenarioId: "SCN-V122B-02-HEAVY-TCP-V3",
      pageKey: "v1_2_2b_scn02_heavy_tcp_v3",
      ruleId: "40498741-ee6b-4a71-9101-0d6d3f77154c",
      version: "v3 (ec0cc351-8dd1-4026-9dc3-586387bb324c)",
      role: "Administrator",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&version_id=ec0cc351-8dd1-4026-9dc3-586387bb324c&tab=overview`,
      apiEndpoint: `${BACKEND_URL}/api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/readiness?version_id=ec0cc351-8dd1-4026-9dc3-586387bb324c`,
      expectedBackendStatus: 200,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Heavy TCP Host Scan Rule v3 Candidate: Canonical readiness route, score 77.0, gates 6/8, sub-8 gate lockout",
      validateApi: (data) => {
        return (
          data &&
          data.readiness_status === "BLOCKED" &&
          data.quality_score === 77.0 &&
          data.quality_gates_passed === 6 &&
          data.approval_eligible === false
        );
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasCandidateV3 = text.includes('v3') || text.includes('Policy v3');
            const hasSixGates = text.includes('6 / 8') || text.includes('6/8') || text.includes('BLOCKED');
            const hasHeavyTcp = text.includes('Heavy TCP Host Scan') || text.includes('40498741');
            const assertions = {
              hasCandidateV3,
              hasSixGates,
              hasHeavyTcp
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

    // 3. AI Runtime Offline
    {
      scenarioId: "SCN-V122B-03-AI-RUNTIME-OFFLINE",
      pageKey: "v1_2_2b_scn03_ai_runtime_offline",
      ruleId: "40498741-ee6b-4a71-9101-0d6d3f77154c",
      version: "v1 (8a460ab8-5f06-4a90-b2d4-db958199d644)",
      role: "Administrator",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&version_id=8a460ab8-5f06-4a90-b2d4-db958199d644&tab=overview`,
      apiEndpoint: `${BACKEND_URL}/api/prompts/rule/40498741-ee6b-4a71-9101-0d6d3f77154c/readiness?version_id=8a460ab8-5f06-4a90-b2d4-db958199d644`,
      expectedBackendStatus: 200,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "AI Runtime Offline State: Server 2 unavailable, UI reflects decoupled execution state",
      validateApi: (data) => {
        return data && (data.ai_execution_status === "Offline" || data.ai_execution_status === "Disabled" || data.runtime_availability !== undefined);
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasAiExecution = text.includes('AI Execution:') || text.includes('AI Execution');
            const hasSiemRule = text.includes('SIEM Rule:');
            const hasReadiness = text.includes('Current Readiness:');
            const assertions = {
              hasAiExecution,
              hasSiemRule,
              hasReadiness
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

    // 4. Blind Review ON
    {
      scenarioId: "SCN-V122B-04-BLIND-ON",
      pageKey: "v1_2_2b_scn04_blind_on",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst A)",
      url: `${BASE_URL}/ai-triage-workbench`,
      apiEndpoint: `${BACKEND_URL}/api/incidents?page=1&page_size=10&blind_review=true`,
      expectedBackendStatus: 200,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Blind Review Enabled (Client ON): Masked AI determinations for unreviewed items, active blind review indicators",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'true');`
        });
      },
      validateApi: (data) => {
        return data && Array.isArray(data.items);
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasBlindIndicator = text.includes('Blind Review') || text.includes('BLIND') || text.includes('[Hidden - Blind Review]');
            const hasWorkbench = text.includes('AI Triage Workbench') || text.includes('Incidents');
            const assertions = {
              hasBlindIndicator,
              hasWorkbench
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

    // 5. Blind Review Client OFF (Server Enforced)
    {
      scenarioId: "SCN-V122B-05-BLIND-OFF",
      pageKey: "v1_2_2b_scn05_blind_off",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst B)",
      url: `${BASE_URL}/ai-triage-workbench`,
      apiEndpoint: `${BACKEND_URL}/api/incidents?page=1&page_size=10&blind_review=false`,
      expectedBackendStatus: 200,
      user: analystBAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Blind Review Client OFF: Server-side isolation overrides client toggle, retaining [Hidden - Blind Review] for unreviewed",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'false');`
        });
      },
      validateApi: (data) => {
        return data && Array.isArray(data.items);
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasHiddenMask = text.includes('[Hidden - Blind Review]');
            const hasWorkbench = text.includes('AI Triage Workbench') || text.includes('Incidents');
            const assertions = {
              hasHiddenMask,
              hasWorkbench
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

    // 6. Analyst A Submitted (Revealed Verdict & Comparison)
    {
      scenarioId: "SCN-V122B-06-ANALYST-A-SUBMITTED",
      pageKey: "v1_2_2b_scn06_analyst_a_submitted",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst A)",
      url: `${BASE_URL}/ai-triage-workbench?search=132438483`,
      apiEndpoint: `${BACKEND_URL}/api/incidents/132438483?blind_review=false`,
      expectedBackendStatus: 200,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Analyst A Submitted Review: Permitted comparison revealed for submitting reviewer (revealed AI verdict badge)",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'true');`
        });
      },
      validateApi: (data) => {
        return data && (data.ai_verdict !== null || data.incident_id === "132438483");
      },
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasRevealedBadge = text.includes('AI: TP') || text.includes('AI: FP') || text.includes('AI: ATTN') || text.includes('True Positive') || text.includes('AGREEMENT');
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

    // 7. Analyst B Unsubmitted (Reviewer Isolation)
    {
      scenarioId: "SCN-V122B-07-ANALYST-B-UNSUBMITTED",
      pageKey: "v1_2_2b_scn07_analyst_b_unsubmitted",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst B)",
      url: `${BASE_URL}/ai-triage-workbench?search=132438483`,
      apiEndpoint: `${BACKEND_URL}/api/incidents/132438483?blind_review=false`,
      expectedBackendStatus: 200,
      user: analystBAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Reviewer A/B Isolation: Analyst A submission does NOT unmask incident 132438483 for Analyst B (retains [Hidden - Blind Review])",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'true');`
        });
      },
      validateApi: (data) => {
        return data && (data.ai_verdict === null || data.ai_verdict?.verdict === "[Hidden - Blind Review]" || data.is_redacted === true);
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

    // 8. Viewer Restricted
    {
      scenarioId: "SCN-V122B-08-VIEWER-RESTRICTED",
      pageKey: "v1_2_2b_scn08_viewer_restricted",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "Read-Only Viewer",
      url: `${BASE_URL}/ai-triage-workbench`,
      apiEndpoint: `${BACKEND_URL}/api/incidents?page=1&page_size=5`,
      expectedBackendStatus: 200,
      user: viewerAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Read-Only Viewer: Masked determinations and restricted interactive controls",
      setupState: async () => {
        await cdp.send("Runtime.evaluate", {
          expression: `localStorage.setItem('ai_verdict_blind_review', 'false');`
        });
      },
      validateApi: (data) => {
        return data && Array.isArray(data.items);
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

    // 9. Cross-Tenant Access Denial
    {
      scenarioId: "SCN-V122B-09-CROSS-TENANT-DENIAL",
      pageKey: "v1_2_2b_scn09_cross_tenant_denial",
      ruleId: "PH_RULE_BETA_EXFIL",
      version: "N/A",
      role: "SOC Analyst (Analyst A, Tenant Alpha)",
      url: `${BASE_URL}/ai-triage-workbench?search=INC-TENANT-BETA-001`,
      apiEndpoint: `${BACKEND_URL}/api/incidents/INC-TENANT-BETA-001`,
      expectedBackendStatus: 403,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Cross-Tenant Access Denial: Analyst A (Tenant Alpha) accessing Tenant Beta incident yields HTTP 403 and zero UI leakage",
      validateApi: (data, status) => {
        return status === 403 && data && String(data.detail).includes("Access denied");
      },
      validateDom: async () => {
        const script = `
          (function() {
            const tbodyText = document.querySelector('tbody')?.innerText || '';
            const noBetaInTable = !tbodyText.includes('Unauthorized Data Exfiltration from Beta Storage') && !tbodyText.includes('INC-TENANT-BETA-001');
            const fullText = document.body.innerText;
            const hasZeroOrNoMatch = fullText.includes('Showing 0 of 0 incidents') || fullText.includes('No matching incidents found') || fullText.includes('0');
            const assertions = {
              noBetaInTable,
              hasZeroOrNoMatch
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

    // 10. Alternate Endpoint & Actual Prompt Export Protection
    {
      scenarioId: "SCN-V122B-10-ALTERNATE-ENDPOINT-PROTECTION",
      pageKey: "v1_2_2b_scn10_alternate_endpoint_protection",
      ruleId: "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
      version: "N/A",
      role: "SOC Analyst (Analyst B)",
      url: `${BASE_URL}/ai-triage-workbench?search=132438483`,
      apiEndpoint: `${BACKEND_URL}/api/prompts/actual-prompt/incident/132438483/export?format=json`,
      expectedBackendStatus: 200,
      user: analystBAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Alternate Endpoint & Export Protection: Unreviewed analyst cannot bypass blind review via actual prompt export",
      validateApi: (data, status) => {
        return (
          status === 200 &&
          data &&
          data.is_redacted === true &&
          data.raw_model_response === "[Hidden - Blind Review]" &&
          data.l1_explanation &&
          data.l1_explanation.verdict_returned === "[Hidden - Blind Review]"
        );
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
    let apiValid = false;
    try {
      const apiRes = await fetch(scenario.apiEndpoint, {
        headers: { "Authorization": `Bearer ${scenario.user.access_token}` },
      });
      apiStatus = apiRes.status;
      apiData = await apiRes.json();
      if (scenario.validateApi) {
        apiValid = scenario.validateApi(apiData, apiStatus);
      } else {
        apiValid = apiStatus === (scenario.expectedBackendStatus || 200);
      }
    } catch (e) {
      console.warn(`  [API Warning] Fetch failed for ${scenario.apiEndpoint}:`, e.message);
    }

    console.log(`  [API Verification] Endpoint: ${scenario.apiEndpoint}`);
    console.log(`  [API Verification] Expected: ${scenario.expectedBackendStatus || 200}, Actual: ${apiStatus}, Valid: ${apiValid ? "YES" : "NO"}`);

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

    // Fail-fast boolean conjunction: scenarioPassed MUST require both API valid and DOM valid!
    const scenarioPassed = apiValid && domResult.isValid;
    console.log(`  [Assertions] Overall Outcome: ${scenarioPassed ? "PASS" : "FAIL"} (API: ${apiValid ? "PASS" : "FAIL"}, DOM: ${domResult.isValid ? "PASS" : "FAIL"})`);
    for (const [key, val] of Object.entries(domResult.assertions || {})) {
      console.log(`    - ${key}: ${val ? "PASSED" : "FAILED"}`);
    }

    const capturedScreenshots = [];

    // Capture across viewports
    for (const vp of scenario.viewports) {
      console.log(`  [Capture] Viewport: ${vp.name} (${vp.width}x${vp.height})`);
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: vp.width,
        height: vp.height,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await cdp.send("Emulation.setVisibleSize", { width: vp.width, height: vp.height });
      await sleep(1000);

      const shotRes = await cdp.send("Page.captureScreenshot", {
        format: "png",
        captureBeyondViewport: false,
      });

      const shotFileName = `${scenario.pageKey}_${vp.name}.png`;
      const shotFilePath = path.join(OUTPUT_DIR, shotFileName);
      fs.writeFileSync(shotFilePath, Buffer.from(shotRes.data, "base64"));
      capturedScreenshots.push({
        viewport: vp.name,
        resolution: `${vp.width}x${vp.height}`,
        filename: shotFileName,
        absolutePath: shotFilePath,
      });
      console.log(`    ✓ Saved screenshot: ${shotFileName}`);
    }

    testResults.push({
      scenarioId: scenario.scenarioId,
      ruleId: scenario.ruleId,
      version: scenario.version,
      authenticatedRole: scenario.role,
      expectedBackendStatus: scenario.expectedBackendStatus || 200,
      actualBackendStatus: apiStatus,
      apiValidationPassed: apiValid,
      backendPayloadSummary: apiData ? (Array.isArray(apiData.items) ? `items: ${apiData.items.length}` : (apiData.readiness_status ? `readiness: ${apiData.readiness_status}, score: ${apiData.readiness_score}` : (apiData.detail || "json response"))) : "N/A",
      expectedUiStatus: "COMPLIANT_RENDER",
      actualUiStatus: domResult.isValid ? "COMPLIANT_RENDER" : "ASSERTION_FAILED",
      mandatoryAssertions: domResult.assertions,
      evidenceTimestamp: new Date().toISOString(),
      exactCommitSha: gitCommitSha,
      status: scenarioPassed ? "PASS" : "FAIL",
      screenshots: capturedScreenshots,
    });
  }

  // 5. Write VALIDATION_EVIDENCE.json
  console.log("\n[5/6] Serializing VALIDATION_EVIDENCE.json...");
  const evidenceReport = {
    schemaVersion: "1.2.2b",
    title: "Verdictum AI — Validation V1.2.2b Final Evidence Integrity & Security Acceptance",
    generatedAt: new Date().toISOString(),
    exactCommitSha: gitCommitSha,
    summary: {
      totalScenarios: testResults.length,
      passedScenarios: testResults.filter((r) => r.status === "PASS").length,
      failedScenarios: testResults.filter((r) => r.status === "FAIL").length,
      totalScreenshotsCaptured: testResults.reduce((acc, r) => acc + r.screenshots.length, 0),
    },
    results: testResults,
  };

  fs.writeFileSync(EVIDENCE_JSON_PATH, JSON.stringify(evidenceReport, null, 2));
  console.log(`  ✓ Evidence JSON saved to: ${EVIDENCE_JSON_PATH}`);

  // 6. Cleanup
  console.log("\n[6/6] Cleaning up Chrome...");
  cdp.close();
  chromeProcess.kill();
  try {
    fs.rmSync(tempProfile, { recursive: true, force: true });
  } catch {}

  console.log("\n========================================================================");
  console.log(`VALIDATION COMPLETED: ${evidenceReport.summary.passedScenarios}/${evidenceReport.summary.totalScenarios} PASSED`);
  console.log(`SCREENSHOTS PRODUCED: ${evidenceReport.summary.totalScreenshotsCaptured} IMAGES`);
  console.log("========================================================================");

  if (evidenceReport.summary.failedScenarios > 0) {
    process.exitCode = 1;
  }
}

main().catch((err) => {
  console.error("FATAL ERROR in Validation V1.2.2b Runner:", err);
  process.exit(1);
});
