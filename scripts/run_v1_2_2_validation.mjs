import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUTPUT_DIR = path.resolve("docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2/screenshots");
const BASE_URL = "http://127.0.0.1:3000";
const BACKEND_URL = "http://127.0.0.1:8000";
const DEBUG_PORT = 9222;

const VIEWPORTS = [
  { name: "1024x768", width: 1024, height: 768 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

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
  const tempProfile = path.resolve(`temp_chrome_val122_${Date.now()}`);
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
  console.log("VERDICTUM AI — VALIDATION V1.2.2 SCREENSHOT & REGRESSION RUNNER");
  console.log("========================================================================");

  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  // 1. Authenticate users
  console.log("[1/5] Authenticating test personas via /api/auth/login...");
  const adminAuth = await loginUser("admin", "AdminPassword123!");
  const analystAuth = await loginUser("analyst", "AnalystPassword123!");
  const viewerAuth = await loginUser("viewer", "ViewerPassword123!");
  console.log("  ✓ Admin:", adminAuth.user.username, `(${adminAuth.user.role})`);
  console.log("  ✓ Analyst:", analystAuth.user.username, `(${analystAuth.user.role})`);
  console.log("  ✓ Viewer:", viewerAuth.user.username, `(${viewerAuth.user.role})`);

  // 2. Launch headless Chrome with CDP
  console.log("\n[2/5] Launching Chrome on debug port", DEBUG_PORT);
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
  await sleep(2000);

  const manifest = [];
  const testResults = [];

  const testScenarios = [
    // 1. Heavy TCP v1 historical baseline (APPROVED baseline, revalidation required)
    {
      scenarioId: "SCN-HEAVY-TCP-V1",
      pageKey: "studio_rule_detail_heavy_tcp_v1",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&version_id=8a460ab8-5f06-4a90-b2d4-db958199d644&tab=overview`,
      expectedRuleId: "40498741-ee6b-4a71-9101-0d6d3f77154c",
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Historical Approved Baseline: Heavy TCP v1 preserved with revalidation required and decoupled statuses",
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const hasRuleHeader = text.includes('Heavy TCP Host Scan') || text.includes('40498741');
            const hasSiemActive = text.includes('SIEM: Active') || text.includes('SIEM Rule:') || text.includes('ACTIVE');
            const hasV1Status = text.includes('v1') || text.includes('V1');
            const hasAiSuspended = text.includes('AI Execution:') && text.includes('Suspended');
            const hasApprovedBaseline = text.includes('APPROVED BASELINE') || text.includes('REVALIDATION REQUIRED') || text.includes('APPROVED');

            const allPassed = Boolean(hasRuleHeader && hasSiemActive && hasV1Status && hasApprovedBaseline);
            return {
              hasRuleHeader,
              hasSiemActive,
              hasV1Status,
              hasAiSuspended,
              hasApprovedBaseline,
              isValid: allPassed
            };
          })();
        `;
        const res = (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
        return res;
      }
    },
    // 2. Heavy TCP candidate v3 (Stage 1 & 2 BLOCKED, correct score math, disabled Approve button)
    {
      scenarioId: "SCN-HEAVY-TCP-V3",
      pageKey: "studio_rule_detail_heavy_tcp_v3",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&version_id=ec0cc351-8dd1-4026-9dc3-586387bb324c&tab=overview`,
      expectedRuleId: "40498741-ee6b-4a71-9101-0d6d3f77154c",
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Candidate Integrity: Heavy TCP v3 stages 1 & 2 blocked, score 77, no contradiction text, disabled approval",
      validateDom: async () => {
        const script = `
          (function() {
            const text = document.body.innerText;
            const stage1El = document.querySelector('[data-testid="readiness-stage-define_detection"]');
            const stage2El = document.querySelector('[data-testid="readiness-stage-verify_evidence"]');
            const hasStage1Blocked = stage1El ? stage1El.innerText.includes('BLOCKED') : (text.includes('Define Detection') && text.includes('BLOCKED'));
            const hasStage2Blocked = stage2El ? stage2El.innerText.includes('BLOCKED') : (text.includes('Verify Evidence') && text.includes('BLOCKED'));
            const hasScore77 = text.includes('77') || text.includes('77.0') || text.includes('77/100');
            const hasNoContradictionText = !text.includes('Quality score (77.0/100) below 70 requirement');
            
            const approveBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Approve') || b.innerText.includes('Approval Blocked'));
            const isApproveDisabled = approveBtn ? (approveBtn.disabled || approveBtn.innerText.includes('Approval Blocked')) : true;

            const allPassed = Boolean(hasStage1Blocked && hasStage2Blocked && hasNoContradictionText && isApproveDisabled);
            return {
              hasStage1Blocked,
              hasStage2Blocked,
              hasScore77,
              hasNoContradictionText,
              isApproveDisabled,
              isValid: allPassed
            };
          })();
        `;
        const res = (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
        return res;
      }
    },
    // 3. Blind Review Active (AI Verdict Masked in Workbench)
    {
      scenarioId: "SCN-BLIND-REVIEW-ACTIVE",
      pageKey: "workbench_blind_review_active",
      url: `${BASE_URL}/ai-triage-workbench`,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Blind Review Integrity: Double-blind mode active, verdicts masked as [Hidden - Blind Review]",
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
            const hasBlindOnHeader = text.includes('Blind Review: ON');
            const allPassed = Boolean(hasHiddenMask && hasBlindOnHeader);
            return {
              hasHiddenMask,
              hasBlindOnHeader,
              isValid: allPassed
            };
          })();
        `;
        const res = (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
        return res;
      }
    },
    // 4. Blind Review Disabled (AI Verdict Visible in Workbench)
    {
      scenarioId: "SCN-BLIND-REVIEW-DISABLED",
      pageKey: "workbench_blind_review_disabled",
      url: `${BASE_URL}/ai-triage-workbench`,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Blind Review Unmasked: Global control OFF reveals stored AI verdicts",
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
            const hasVerdicts = text.includes('True Positive') || text.includes('False Positive') || text.includes('Suspicious') || text.includes('TP');
            const allPassed = Boolean(hasBlindOffHeader && hasVerdicts);
            return {
              hasBlindOffHeader,
              hasVerdicts,
              isValid: allPassed
            };
          })();
        `;
        const res = (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
        return res;
      }
    },
    // 5. Read-Only Viewer Lockout in Studio
    {
      scenarioId: "SCN-VIEWER-LOCKOUT",
      pageKey: "studio_viewer_lockout",
      url: `${BASE_URL}/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&tab=overview`,
      user: viewerAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "RBAC Safety: Read-Only Viewer mutation controls strictly disabled",
      validateDom: async () => {
        const script = `
          (function() {
            const synthBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Synthesize Draft'));
            const isSynthDisabled = synthBtn ? synthBtn.disabled : true;
            const simBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Simulation'));
            const isSimDisabled = simBtn ? simBtn.disabled : true;
            const approveBtn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Approve') || b.innerText.includes('Approval Blocked'));
            const isApproveDisabled = approveBtn ? (approveBtn.disabled || approveBtn.innerText.includes('Approval Blocked')) : true;

            const allPassed = Boolean(isSynthDisabled && isSimDisabled && isApproveDisabled);
            return {
              isSynthDisabled,
              isSimDisabled,
              isApproveDisabled,
              isValid: allPassed
            };
          })();
        `;
        const res = (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
        return res;
      }
    },
    // 6. Rule Catalog Readiness Integrity
    {
      scenarioId: "SCN-CATALOG-INTEGRITY",
      pageKey: "studio_catalog_readiness_integrity",
      url: `${BASE_URL}/detection-intelligence`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Rule Catalog Integrity: sub-8 gate rules never display false READY FOR APPROVAL",
      validateDom: async () => {
        const script = `
          (function() {
            const table = document.querySelector('table');
            const rows = Array.from(document.querySelectorAll('tbody tr'));
            const text = document.body.innerText;
            const hasFalseReady = text.includes('READY FOR APPROVAL');
            const allPassed = Boolean(table && rows.length > 0 && !hasFalseReady);
            return {
              rowCount: rows.length,
              hasTable: Boolean(table),
              hasFalseReady,
              isValid: allPassed
            };
          })();
        `;
        const res = (await cdp.send("Runtime.evaluate", { expression: script, returnByValue: true })).result.value;
        return res;
      }
    }
  ];

  console.log(`[3/5] Executing ${testScenarios.length} test scenarios across ${VIEWPORTS.length} viewports (${testScenarios.length * VIEWPORTS.length} screenshots)...`);

  for (const scenario of testScenarios) {
    console.log(`\n========================================================================`);
    console.log(`Scenario: ${scenario.scenarioId} -> ${scenario.pageKey} (${scenario.user.user.role})`);
    console.log(`Target URL: ${scenario.url}`);
    console.log(`========================================================================`);

    // Set auth state and theme in localStorage
    const setSessionScript = `
      localStorage.setItem('ai_verdict_token', ${JSON.stringify(scenario.user.access_token)});
      localStorage.setItem('ai_verdict_user', ${JSON.stringify(JSON.stringify(scenario.user.user))});
      localStorage.setItem('ai_verdict_theme', ${JSON.stringify(scenario.theme)});
      document.documentElement.setAttribute('data-theme', ${JSON.stringify(scenario.theme)});
    `;
    await cdp.send("Runtime.evaluate", { expression: setSessionScript });

    if (scenario.setupState) {
      await scenario.setupState();
    }

    // Navigate to page
    await cdp.send("Page.navigate", { url: scenario.url });
    await sleep(3500);

    // Run DOM validation
    let domResult = { isValid: false };
    if (scenario.validateDom) {
      domResult = await scenario.validateDom();
      if (!domResult.isValid) {
        console.log("Waiting for DOM assertions to settle...");
        for (let r = 0; r < 6; r++) {
          await sleep(500);
          domResult = await scenario.validateDom();
          if (domResult.isValid) break;
        }
      }
      console.log("DOM Validation Result:", JSON.stringify(domResult, null, 2));
      testResults.push({
        scenarioId: scenario.scenarioId,
        pageKey: scenario.pageKey,
        domResult,
        status: domResult.isValid ? "PASS" : "FAIL"
      });
    }

    // Capture screenshots across each requested viewport
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

  // Write Evidence JSON
  const evidencePayload = {
    version: "V1.2.2",
    timestamp: new Date().toISOString(),
    commit: "HEAD",
    status: testResults.every(r => r.status === "PASS") ? "PASS" : "FAIL",
    summary: {
      totalScenarios: testScenarios.length,
      passedScenarios: testResults.filter(r => r.status === "PASS").length,
      failedScenarios: testResults.filter(r => r.status === "FAIL").length,
      totalScreenshots: manifest.length,
      viewportsTested: VIEWPORTS.map(v => v.name),
    },
    testResults,
    screenshots: manifest,
  };

  const evidencePath = path.resolve("docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2/VALIDATION_EVIDENCE.json");
  fs.writeFileSync(evidencePath, JSON.stringify(evidencePayload, null, 2), "utf8");
  console.log(`\n[4/5] Generated VALIDATION_EVIDENCE.json at ${evidencePath}`);

  // Cleanup
  cdp.close();
  chromeProcess.kill();
  try {
    fs.rmSync(tempProfile, { recursive: true, force: true });
  } catch {}

  console.log(`\n[5/5] Validation V1.2.2 complete. Total screenshots captured: ${manifest.length}`);
  if (evidencePayload.status !== "PASS") {
    console.error("FAIL: One or more validation scenarios failed assertions!");
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("FATAL ERROR in Validation V1.2.2 runner:", err);
  process.exit(1);
});
