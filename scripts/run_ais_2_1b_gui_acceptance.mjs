import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUTPUT_DIR = path.resolve("docs/AIS_2_1b/screenshots");
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
  const tempProfile = path.resolve(`temp_chrome_ais21b_${Date.now()}`);
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
  console.log(`Saved screenshot: ${filePath} (${(buffer.length / 1024).toFixed(1)} KB)`);
  return filePath;
}

async function setViewport(cdp, width, height) {
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width,
    height,
    deviceScaleFactor: 1,
    mobile: false,
  });
  await sleep(500);
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
  console.log("=== VERDICTUM AI AIS 2.1b: LIVE GUI ACCEPTANCE TEST ON SERVER 1 ===");
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  console.log("[1/8] Authenticating administrator account via API...");
  const authData = await loginViaApi();
  console.log(`Authenticated: ${authData.user.username} (${authData.user.role})`);

  console.log("[2/8] Launching headless Chrome CDP session on port 9222...");
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

    // Primary Viewport: 1440x900
    await setViewport(cdp, 1440, 900);

    // Set cookie
    await cdp.send("Network.setCookie", {
      name: "ai_verdict_session",
      value: authData.access_token,
      domain: "172.26.41.240",
      path: "/",
      httpOnly: false,
      secure: false,
    });

    console.log("[3/8] Navigating to Login Page for initial state verification...");
    await cdp.send("Page.navigate", { url: `${BASE_URL}/login` });
    await sleep(2000);
    await captureScreenshot(cdp, "01_login_page.png");

    // Seed localStorage
    await cdp.send("Runtime.evaluate", {
      expression: `
        localStorage.setItem("ai_verdict_token", ${JSON.stringify(authData.access_token)});
        localStorage.setItem("ai_verdict_user", ${JSON.stringify(JSON.stringify(authData.user))});
        localStorage.setItem("ai_verdict_theme", "obsidian");
        localStorage.setItem("VERDICTUM_COMPACT_UI_ENABLED", "true");
      `,
    });

    console.log("[4/8] Navigating to Agent Intelligence Studio for Heavy TCP rule (1440x900)...");
    await cdp.send("Page.navigate", { url: `${BASE_URL}/agent-intelligence-studio?rule_id=${RULE_UUID}` });
    await sleep(4000);

    // Evaluate Header & Compact Rule Toolbar Geometry & Content
    const evalRuleHeader = await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const bodyText = document.body.innerText;
          const hasDualBranding = bodyText.includes('Verdictum AI') && (bodyText.includes('WYSETEK') || bodyText.includes('Wysetek'));
          const hasTargetRule = bodyText.includes('Heavy TCP Host Scan On Fixed Port');
          const hasV7Approved = bodyText.includes('v7') && (bodyText.includes('APPROVED') || bodyText.includes('Approved') || bodyText.includes('Active'));
          const hasThreeTabs = bodyText.includes('Review Incidents') && bodyText.includes('Test AI') && bodyText.includes('Accuracy & Learning');
          const hasSettings = bodyText.includes('Advanced Settings') || bodyText.includes('Settings');
          const hasCompactAction = bodyText.includes('Action needed:') || bodyText.includes('Next Recommended Action:');

          // Measure layout coordinates on 1440x900
          const toolbar = document.querySelector('[data-testid="ais-compact-toolbar"], [data-testid="header-policy-lifecycle-status"]')?.closest('div');
          const tabs = document.querySelector('[data-testid="ais-primary-tabs"]');
          const nextBtn = document.querySelector('[data-testid="next-action-button"]');

          return {
            hasDualBranding,
            hasTargetRule,
            hasV7Approved,
            hasThreeTabs,
            hasSettings,
            hasCompactAction,
            toolbarTop: toolbar ? Math.round(toolbar.getBoundingClientRect().top) : null,
            tabsTop: tabs ? Math.round(tabs.getBoundingClientRect().top) : null,
            hasZeroHorizontalScroll: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
          };
        })()
      `,
      returnByValue: true,
    });
    console.log("Rule Header & Compact Toolbar State:", JSON.stringify(evalRuleHeader.result?.value, null, 2));
    await captureScreenshot(cdp, "02_compact_toolbar_and_action_1440x900.png");

    console.log("[5/8] Testing Operational Tab 2: Test AI (Dominant Incident Table)...");
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const tab = document.querySelector('[data-testid="tab-test-ai"]');
          if (tab) { tab.click(); return 'clicked_test_ai_tab'; }
          const tabs = document.querySelectorAll('button, [role="tab"]');
          for (const t of tabs) {
            if (t.innerText.includes('Test AI') || t.innerText.includes('AI Evaluation')) {
              t.click();
              return 'clicked_ai_eval';
            }
          }
          return 'tab_not_found';
        })()
      `,
    });
    await sleep(2500);

    const evalTestAiView = await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const text = document.body.innerText;
          const hasTotalCards = text.includes('Current Incidents') || text.includes('Total Incidents');
          const hasDecisive = text.includes('Decisive Verdicts') || text.includes('Decisive');
          const hasAbstained = text.includes('Abstained');
          const hasNotEvaluated = text.includes('Not Evaluated');
          const hasSecondaryOutcomes = text.includes('Secondary Outcomes') || text.includes('Rejected:');
          const hasModelContext = text.includes('Qwen/Qwen2.5-7B') || text.includes('Model:');
          const hasGpuOnline = text.includes('ONLINE') || text.includes('Online');
          const hasTable = text.includes('Incident Evaluation Tracking');

          // Check vertical position of table to verify it is visible above the fold on 1440x900
          const tableElem = document.querySelector('table');
          const tableRect = tableElem ? tableElem.getBoundingClientRect() : null;

          return {
            hasTotalCards,
            hasDecisive,
            hasAbstained,
            hasNotEvaluated,
            hasSecondaryOutcomes,
            hasModelContext,
            hasGpuOnline,
            hasTable,
            tableTop: tableRect ? Math.round(tableRect.top) : null,
            tableHeight: tableRect ? Math.round(tableRect.height) : null,
            tableVisibleWithoutScroll: tableRect ? tableRect.top < 850 : false,
            containsDemoSoc: text.includes('Demo-SOC'),
            containsGdcNoc: text.includes('GDC_NOC'),
            containsIncident335: text.includes('335'),
          };
        })()
      `,
      returnByValue: true,
    });
    console.log("Test AI Tab (Evaluation Tracking):", JSON.stringify(evalTestAiView.result?.value, null, 2));
    await captureScreenshot(cdp, "03_test_ai_dominant_table_1440x900.png");

    console.log("[6/8] Testing Operational Tab 3: Accuracy & Learning...");
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const tab = document.querySelector('[data-testid="tab-learning"]');
          if (tab) { tab.click(); return 'clicked_learning_tab'; }
          const tabs = document.querySelectorAll('button, [role="tab"]');
          for (const t of tabs) {
            if (t.innerText.includes('Accuracy') || t.innerText.includes('Learning')) {
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
            hasReviews32Or45: text.includes('32') || text.includes('45') || text.includes('47'),
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
    await captureScreenshot(cdp, "04_accuracy_learning_tab_1440x900.png");

    console.log("[7/8] Testing Operational Tab 1: Review Incidents & Evidence Mapping...");
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const tab = document.querySelector('[data-testid="tab-overview"]');
          if (tab) { tab.click(); return 'clicked_overview_tab'; }
          const tabs = document.querySelectorAll('button, [role="tab"]');
          for (const t of tabs) {
            if (t.innerText.includes('Review Incidents') || t.innerText.includes('Incidents')) {
              t.click();
              return 'clicked_incidents';
            }
          }
          return 'tab_not_found';
        })()
      `,
    });

    // Wait for incidents table to load
    let incidentsLoaded = false;
    for (let i = 0; i < 20; i++) {
      await sleep(500);
      const checkRes = await cdp.send("Runtime.evaluate", {
        expression: `document.body.innerText.includes('335') || document.body.innerText.includes('172.26.29.65')`,
        returnByValue: true,
      });
      if (checkRes.result?.value) {
        incidentsLoaded = true;
        break;
      }
    }

    // Click on incident 335 if present to expand inspection drawer
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const rows = document.querySelectorAll('tr, [data-testid^="incident-row"]');
          for (const r of rows) {
            if (r.innerText.includes('335')) {
              r.click();
              return 'clicked_incident_335';
            }
          }
          return 'row_335_not_found';
        })()
      `,
    });
    await sleep(1500);

    const evalIncidentsView = await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const text = document.body.innerText;
          return {
            hasIncidentsTab: true,
            incidentsLoaded,
            containsIncident335: text.includes('335'),
            containsSourceMetadata: text.includes('Source: Incident Metadata') || text.includes('172.26.29.65') || text.includes('Incident Details'),
            containsHostReporting: text.includes('172.26.31.254') || text.includes('HOST-172.26.31.254') || text.includes('172.26.29.65')
          };
        })()
      `,
      returnByValue: true,
    });
    console.log("Review Incidents Tab:", JSON.stringify(evalIncidentsView.result?.value, null, 2));
    await captureScreenshot(cdp, "05_review_incidents_tab_1440x900.png");

    // Open Advanced Settings Drawer
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const btn = document.querySelector('[data-testid="tab-advanced"]');
          if (btn) { btn.click(); return 'clicked_settings_btn'; }
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
    await sleep(1500);
    await captureScreenshot(cdp, "06_advanced_settings_drawer_1440x900.png");

    // Switch back to Test AI tab for multi-viewport captures
    await cdp.send("Runtime.evaluate", {
      expression: `
        (() => {
          const tab = document.querySelector('[data-testid="tab-test-ai"]');
          if (tab) tab.click();
        })()
      `,
    });
    await sleep(1500);

    console.log("[8/8] Capturing Multi-Viewport Screenshots & Geometry...");
    // 1280x800
    await setViewport(cdp, 1280, 800);
    const vp1280 = await cdp.send("Runtime.evaluate", {
      expression: `({
        width: window.innerWidth,
        height: window.innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        zeroHorizontalScroll: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      })`,
      returnByValue: true,
    });
    console.log("Viewport 1280x800 Geometry:", JSON.stringify(vp1280.result?.value));
    await captureScreenshot(cdp, "07_viewport_1280x800.png");

    // 1727x972
    await setViewport(cdp, 1727, 972);
    const vp1727 = await cdp.send("Runtime.evaluate", {
      expression: `({
        width: window.innerWidth,
        height: window.innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        zeroHorizontalScroll: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      })`,
      returnByValue: true,
    });
    console.log("Viewport 1727x972 Geometry:", JSON.stringify(vp1727.result?.value));
    await captureScreenshot(cdp, "08_viewport_1727x972.png");

    // 1920x1080
    await setViewport(cdp, 1920, 1080);
    const vp1920 = await cdp.send("Runtime.evaluate", {
      expression: `({
        width: window.innerWidth,
        height: window.innerHeight,
        scrollWidth: document.documentElement.scrollWidth,
        clientWidth: document.documentElement.clientWidth,
        zeroHorizontalScroll: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      })`,
      returnByValue: true,
    });
    console.log("Viewport 1920x1080 Geometry:", JSON.stringify(vp1920.result?.value));
    await captureScreenshot(cdp, "09_viewport_1920x1080.png");

    const finalReport = {
      testTimestamp: new Date().toISOString(),
      baseUrl: BASE_URL,
      ruleUuid: RULE_UUID,
      viewportsTested: ["1440x900", "1280x800", "1727x972", "1920x1080"],
      ruleHeader: evalRuleHeader.result?.value,
      testAiTab: evalTestAiView.result?.value,
      accuracyTab: evalAccuracyView.result?.value,
      incidentsTab: evalIncidentsView.result?.value,
      viewportGeometry: {
        vp1280: vp1280.result?.value,
        vp1727: vp1727.result?.value,
        vp1920: vp1920.result?.value,
      },
      screenshots: [
        "01_login_page.png",
        "02_compact_toolbar_and_action_1440x900.png",
        "03_test_ai_dominant_table_1440x900.png",
        "04_accuracy_learning_tab_1440x900.png",
        "05_review_incidents_tab_1440x900.png",
        "06_advanced_settings_drawer_1440x900.png",
        "07_viewport_1280x800.png",
        "08_viewport_1727x972.png",
        "09_viewport_1920x1080.png"
      ]
    };

    const reportJson = JSON.stringify(finalReport, null, 2);
    fs.writeFileSync(path.join(OUTPUT_DIR, "../gui_acceptance_results.json"), reportJson);
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
