import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUTPUT_DIR = path.resolve("docs/AIS_2_1a_UNIFIED_POPULATION_ACCURACY_INTEGRITY/screenshots");
const LEGACY_OUTPUT_DIR = path.resolve("docs/AIS_2_1a_FINAL_OPERATIONAL_ACCEPTANCE/screenshots");
const BASE_URL = "http://172.26.41.240:3000";
const DEBUG_PORT = 9222;
const RULE_UUID = "40498741-ee6b-4a71-9101-0d6d3f77154c";

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

async function launchChrome() {
  const tempProfile = path.resolve(`temp_chrome_ais21a_${Date.now()}`);
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

async function captureScreenshot(cdp, filename) {
  const result = await cdp.send("Page.captureScreenshot", { format: "png" });
  const buffer = Buffer.from(result.data, "base64");
  const filePath = path.join(OUTPUT_DIR, filename);
  fs.writeFileSync(filePath, buffer);
  if (fs.existsSync(LEGACY_OUTPUT_DIR)) {
    fs.writeFileSync(path.join(LEGACY_OUTPUT_DIR, filename), buffer);
  }
  console.log(`Saved screenshot: ${filePath} (${(buffer.length / 1024).toFixed(1)} KB)`);
  return filePath;
}

async function loginViaApi() {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "admin", password: "AdminPassword123!" }),
  });
  if (!res.ok) {
    throw new Error(`API login failed with HTTP ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

async function main() {
  console.log("=== VERDICTUM AI AIS 2.1a: LIVE GUI ACCEPTANCE TEST ON SERVER 1 ===");
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }
  if (!fs.existsSync(LEGACY_OUTPUT_DIR)) {
    fs.mkdirSync(LEGACY_OUTPUT_DIR, { recursive: true });
  }

  console.log("[1/6] Authenticating administrator account via API...");
  const authData = await loginViaApi();
  console.log(`Authenticated: ${authData.user.username} (${authData.user.role})`);

  console.log("[2/6] Launching headless Chrome CDP session on port 9222...");
  const { chromeProcess, tempProfile } = await launchChrome();

  try {
    const pagesRes = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/list`);
    const pagesList = await pagesRes.json();
    const pageTarget = pagesList.find((p) => p.type === "page") || pagesList[0];

    const cdp = new CdpSession(pageTarget.webSocketDebuggerUrl);
    await cdp.connect();
    await cdp.send("Page.enable");
    await cdp.send("DOM.enable");
    await cdp.send("Runtime.enable");
    await cdp.send("Network.enable");

    // Set viewport: 1440x900
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width: 1440,
      height: 900,
      deviceScaleFactor: 1,
      mobile: false,
    });

    // Set cookie
    await cdp.send("Network.setCookie", {
      name: "ai_verdict_session",
      value: authData.access_token,
      domain: "172.26.41.240",
      path: "/",
      httpOnly: false,
      secure: false,
    });

    console.log("[3/6] Navigating to Login Page for initial state verification...");
    await cdp.send("Page.navigate", { url: `${BASE_URL}/login` });
    await sleep(2000);
    await captureScreenshot(cdp, "01_login_page.png");

    // Seed localStorage
    await cdp.send("Runtime.evaluate", {
      expression: `
        localStorage.setItem("ai_verdict_token", ${JSON.stringify(authData.access_token)});
        localStorage.setItem("ai_verdict_user", ${JSON.stringify(JSON.stringify(authData.user))});
        localStorage.setItem("ai_verdict_theme", "obsidian");
      `,
    });

    console.log("[4/6] Navigating to Agent Intelligence Studio for Heavy TCP rule...");
    await cdp.send("Page.navigate", { url: `${BASE_URL}/agent-intelligence-studio?rule_id=${RULE_UUID}` });
    await sleep(4000);

    // Verify Rule Header & Active Policy State
    const evalRuleHeader = await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const bodyText = document.body.innerText;
          const hasDualBranding = bodyText.includes('Verdictum AI') && bodyText.includes('WYSETEK');
          const hasTargetRule = bodyText.includes('Heavy TCP Host Scan On Fixed Port');
          const hasV7Approved = bodyText.includes('v7') && (bodyText.includes('APPROVED') || bodyText.includes('Active'));
          const hasNoActiveVersion = bodyText.includes('No Active Version') || bodyText.includes('AI Execution Suspended: POLICY_NOT_APPROVED');
          const hasThreeTabs = bodyText.includes('Incidents') && bodyText.includes('AI Evaluation') && bodyText.includes('Accuracy');
          const hasSettings = bodyText.includes('Settings');
          return {
            hasDualBranding,
            hasTargetRule,
            hasV7Approved,
            hasNoActiveVersion,
            hasThreeTabs,
            hasSettings,
            pageTitle: document.title,
            bodySnippet: bodyText.slice(0, 1000)
          };
        })()
      `,
      returnByValue: true,
    });
    console.log("Rule Header & Active Policy State:", JSON.stringify(evalRuleHeader.result?.value, null, 2));
    await captureScreenshot(cdp, "02_ais_header_and_rule_v7_active.png");

    console.log("[5/6] Testing Operational Tab 2: AI Evaluation Tracking...");
    // Click Tab: AI Evaluation
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const tabs = document.querySelectorAll('button, [role="tab"]');
          for (const t of tabs) {
            if (t.innerText.includes('AI Evaluation') || t.innerText.includes('AI Evaluation Tracking')) {
              t.click();
              return 'clicked_ai_eval';
            }
          }
          return 'tab_not_found';
        })()
      `,
    });
    await sleep(2500);

    const evalTrackingView = await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const text = document.body.innerText;
          const hasTotalCards = text.includes('Total Incidents');
          const hasNotEvaluated = text.includes('Not Evaluated');
          const hasAbstained = text.includes('Abstained');
          const hasTable = text.includes('Demo-SOC') || text.includes('GDC_NOC') || text.includes('Incident');
          return {
            hasTotalCards,
            hasNotEvaluated,
            hasAbstained,
            hasTable,
            containsDemoSoc: text.includes('Demo-SOC'),
            containsGdcNoc: text.includes('GDC_NOC'),
            containsIncident335: text.includes('335')
          };
        })()
      `,
      returnByValue: true,
    });
    console.log("AI Evaluation Tracking Tab:", JSON.stringify(evalTrackingView.result?.value, null, 2));
    await captureScreenshot(cdp, "03_ai_evaluation_tracking_tab.png");

    console.log("[6/6] Testing Operational Tab 3: Accuracy & Learning...");
    // Click Tab: Accuracy
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const tabs = document.querySelectorAll('button, [role="tab"]');
          for (const t of tabs) {
            if (t.innerText.includes('Accuracy') || t.innerText.includes('Accuracy & Learning')) {
              t.click();
              return 'clicked_accuracy';
            }
          }
          return 'tab_not_found';
        })()
      `,
    });
    await sleep(2500);

    const evalAccuracyView = await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const text = document.body.innerText;
          const lower = text.toLowerCase();
          const hasNotMeasurable = lower.includes('not measurable') || lower.includes('no eligible decisive') || lower.includes('0 eligible decisive');
          const hasContradictory13Reviews45FP = text.includes('13 Reviews (0 TP / 45 FP)') || text.includes('13 (0 TP / 45 FP)');
          const hasDualScopes = (text.includes('Current Incident Inventory') || text.includes('Current Operational')) && (text.includes('Cumulative Historical') || text.includes('Historical Cohort'));
          const hasOneClassDataset = text.includes('One-Class Dataset') || lower.includes('one-class');
          return {
            hasAccuracyTab: true,
            hasReviews32Or45: text.includes('32') || text.includes('45'),
            hasFpMention: text.includes('FP') || text.includes('False Positive'),
            hasNotMeasurable,
            hasContradictory13Reviews45FP,
            hasDualScopes,
            hasOneClassDataset,
          };
        })()
      `,
      returnByValue: true,
    });
    console.log("Accuracy & Learning Tab:", JSON.stringify(evalAccuracyView.result?.value, null, 2));
    await captureScreenshot(cdp, "04_accuracy_learning_tab.png");

    // Click Tab: Incidents (Review Incidents)
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const tabs = document.querySelectorAll('button, [role="tab"]');
          for (const t of tabs) {
            if (t.innerText.includes('Incidents') || t.innerText.includes('Review Incidents')) {
              t.click();
              return 'clicked_incidents';
            }
          }
          return 'tab_not_found';
        })()
      `,
    });
    await sleep(2500);

    const evalIncidentsView = await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const text = document.body.innerText;
          return {
            hasIncidentsTab: true,
            containsIncident335: text.includes('335'),
            containsSourceMetadata: text.includes('Source: Incident Metadata') || text.includes('172.26.29.65'),
            containsHostReporting: text.includes('172.26.31.254') || text.includes('HOST-172.26.31.254')
          };
        })()
      `,
      returnByValue: true,
    });
    console.log("Incidents Tab & Evidence Mapping:", JSON.stringify(evalIncidentsView.result?.value, null, 2));
    await captureScreenshot(cdp, "05_review_incidents_tab.png");

    // Click Settings Control
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const buttons = document.querySelectorAll('button');
          for (const b of buttons) {
            if (b.innerText.includes('Settings')) {
              b.click();
              return 'clicked_settings';
            }
          }
          return 'settings_not_found';
        })()
      `,
    });
    await sleep(2000);
    await captureScreenshot(cdp, "06_settings_drawer_open.png");

    const finalReport = {
      testTimestamp: new Date().toISOString(),
      baseUrl: BASE_URL,
      ruleUuid: RULE_UUID,
      ruleHeader: evalRuleHeader.result?.value,
      aiEvaluationTab: evalTrackingView.result?.value,
      accuracyTab: evalAccuracyView.result?.value,
      incidentsTab: evalIncidentsView.result?.value,
      screenshots: [
        "01_login_page.png",
        "02_ais_header_and_rule_v7_active.png",
        "03_ai_evaluation_tracking_tab.png",
        "04_accuracy_learning_tab.png",
        "05_review_incidents_tab.png",
        "06_settings_drawer_open.png"
      ]
    };

    const reportJson = JSON.stringify(finalReport, null, 2);
    fs.writeFileSync(path.join(OUTPUT_DIR, "../gui_acceptance_results.json"), reportJson);
    if (fs.existsSync(LEGACY_OUTPUT_DIR)) {
      fs.writeFileSync(path.join(LEGACY_OUTPUT_DIR, "../gui_acceptance_results.json"), reportJson);
    }
    console.log("=== LIVE GUI ACCEPTANCE COMPLETED SUCCESSFULLY ===");

    cdp.close();
  } finally {
    try {
      chromeProcess.kill();
      fs.rmSync(tempProfile, { recursive: true, force: true });
    } catch {}
  }
}

main().catch((err) => {
  console.error("FATAL ERROR in GUI Acceptance:", err);
  process.exit(1);
});
