import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const OUTPUT_DIR = path.resolve("docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_1/screenshots");
const BASE_URL = "http://127.0.0.1:3000";
const DEBUG_PORT = 9222;

const VIEWPORTS = [
  { name: "1024x768", width: 1024, height: 768 },
  { name: "1280x800", width: 1280, height: 800 },
  { name: "1366x768", width: 1366, height: 768 },
  { name: "1440x900", width: 1440, height: 900 },
  { name: "1920x1080", width: 1920, height: 1080 },
];

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Simple CDP Client over WebSocket
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
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!res.ok) throw new Error(`Login failed for ${username}: ${res.status}`);
  return res.json();
}

async function launchChrome() {
  const tempProfile = path.resolve(`temp_chrome_val_${Date.now()}`);
  const chromeProcess = spawn(CHROME_PATH, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    `--remote-debugging-port=${DEBUG_PORT}`,
    `--user-data-dir=${tempProfile}`,
    "about:blank",
  ], { stdio: "ignore" });

  // Wait for debug port to be ready
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
  console.log("=== VERDICTUM AI POPULATED & AUTHENTICATED VALIDATION 1.1 ===");
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  console.log("[1/5] Authenticating test accounts...");
  const adminAuth = await loginUser("admin", "AdminPassword123!");
  const analystAuth = await loginUser("analyst", "AnalystPassword123!");
  const viewerAuth = await loginUser("viewer", "ViewerPassword123!");
  console.log(`- Administrator: ${adminAuth.user.username} (${adminAuth.user.role})`);
  console.log(`- SOC Analyst:   ${analystAuth.user.username} (${analystAuth.user.role})`);
  console.log(`- Viewer:        ${viewerAuth.user.username} (${viewerAuth.user.role})`);

  console.log("[2/5] Launching headless Chrome with remote debugging on port 9222...");
  const { chromeProcess, tempProfile } = await launchChrome();

  const pagesRes = await fetch(`http://127.0.0.1:${DEBUG_PORT}/json/list`);
  const pagesList = await pagesRes.json();
  const targetTab = pagesList[0];
  const cdp = new CdpSession(targetTab.webSocketDebuggerUrl);
  await cdp.connect();
  console.log("Connected to Chrome DevTools Protocol session.");

  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("DOM.enable");

  // Initial navigation to origin to allow setting localStorage
  await cdp.send("Page.navigate", { url: `${BASE_URL}/login` });
  await sleep(1000);

  const manifest = [];
  const testResults = [];

  // Scenarios to capture and validate
  const testScenarios = [
    // 1. Telemetry Hub (Admin, 5 viewports, Obsidian)
    {
      pageKey: "telemetry_hub",
      url: `${BASE_URL}/telemetry-hub`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Telemetry Hub with 4 compact KPIs, active poller, and populated ingestion history",
    },
    // 2. AI Triage Workbench (Admin, 5 viewports, Obsidian)
    {
      pageKey: "ai_triage_workbench",
      url: `${BASE_URL}/ai-triage-workbench`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "AI Triage Workbench with 125+ populated incidents, CompactRuleScopeBar, and sticky actions",
    },
    // 3. Agent Intelligence Studio - Directory (Admin, 5 viewports, Obsidian)
    {
      pageKey: "agent_intelligence_studio_catalog",
      url: `${BASE_URL}/agent-intelligence-studio`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "AIS Rule Directory with 36+ monitored rules, quality scores, readiness tags, and sticky actions",
    },
    // 4. Agent Intelligence Studio - Rule Detail (Approved Policy: RULE-NET-001)
    {
      pageKey: "studio_rule_detail_approved",
      url: `${BASE_URL}/agent-intelligence-studio`, // Will switch to rule via UI or state
      user: adminAuth,
      theme: "obsidian",
      viewports: [
        { name: "1024x768", width: 1024, height: 768 },
        { name: "1280x800", width: 1280, height: 800 },
        { name: "1440x900", width: 1440, height: 900 },
        { name: "1920x1080", width: 1920, height: 1080 },
      ],
      description: "AIS Rule Detail for approved high-volume scan rule with wrapped title and 12-col grid",
      ruleSelect: "RULE-NET-001",
    },
    // 5. Agent Intelligence Studio - Rule Detail (Blocked Draft Policy: RULE-EDR-003)
    {
      pageKey: "studio_rule_detail_blocked",
      url: `${BASE_URL}/agent-intelligence-studio`,
      user: adminAuth,
      theme: "obsidian",
      viewports: [{ name: "1440x900", width: 1440, height: 900 }, { name: "1920x1080", width: 1920, height: 1080 }],
      description: "AIS Rule Detail for G1-blocked rule showing explicit failure banner and disabled approval",
      ruleSelect: "RULE-EDR-003",
    },
    // 6. Agent Intelligence Studio - Suspended Policy (RULE-WAF-004)
    {
      pageKey: "studio_rule_detail_suspended",
      url: `${BASE_URL}/agent-intelligence-studio`,
      user: adminAuth,
      theme: "obsidian",
      viewports: [{ name: "1920x1080", width: 1920, height: 1080 }],
      description: "AIS Rule Detail with explicit suspension warning and reason banner",
      ruleSelect: "RULE-WAF-004",
    },
    // 7. Human Review Queue (Analyst, 5 viewports, Obsidian)
    {
      pageKey: "human_review_queue",
      url: `${BASE_URL}/human-review-queue`,
      user: analystAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Human Review Queue for SOC Analyst with pending adjudication incidents",
    },
    // 8. Detection Intelligence (5 viewports, Obsidian)
    {
      pageKey: "detection_intelligence",
      url: `${BASE_URL}/detection-intelligence`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Detection Intelligence rules catalog with 36+ rules and production readiness filters",
    },
    // 9. Mission Control (Admin, 5 viewports, Obsidian)
    {
      pageKey: "mission_control",
      url: `${BASE_URL}/agent-mission-control`,
      user: adminAuth,
      theme: "obsidian",
      viewports: VIEWPORTS,
      description: "Mission Control populated with live metrics, agent workload, and recent activity",
    },
    // 10. Classic Theme Validation (AI Triage & Studio in Classic Theme)
    {
      pageKey: "ai_triage_workbench_classic",
      url: `${BASE_URL}/ai-triage-workbench`,
      user: adminAuth,
      theme: "classic",
      viewports: [{ name: "1440x900", width: 1440, height: 900 }, { name: "1920x1080", width: 1920, height: 1080 }],
      description: "AI Triage Workbench rendered in Classic Theme (neutral slate/zinc)",
    },
    {
      pageKey: "agent_intelligence_studio_classic",
      url: `${BASE_URL}/agent-intelligence-studio`,
      user: adminAuth,
      theme: "classic",
      viewports: [{ name: "1440x900", width: 1440, height: 900 }, { name: "1920x1080", width: 1920, height: 1080 }],
      description: "Agent Intelligence Studio rendered in Classic Theme",
    },
    // 11. Read-Only Viewer Experience (Viewer role)
    {
      pageKey: "studio_viewer_role",
      url: `${BASE_URL}/agent-intelligence-studio`,
      user: viewerAuth,
      theme: "obsidian",
      viewports: [{ name: "1440x900", width: 1440, height: 900 }],
      description: "Read-Only Viewer view showing disabled approval and write actions",
    },
  ];

  console.log(`[3/5] Executing ${testScenarios.length} test scenarios across viewports...`);

  let currentAuthUser = null;
  let currentTheme = null;

  for (const scenario of testScenarios) {
    console.log(`\n--- Scenario: ${scenario.pageKey} (${scenario.theme}, ${scenario.user.user.role}) ---`);

    // Set auth state and theme in localStorage if changed
    const setSessionScript = `
      localStorage.setItem('ai_verdict_token', ${JSON.stringify(scenario.user.access_token)});
      localStorage.setItem('ai_verdict_user', ${JSON.stringify(JSON.stringify(scenario.user.user))});
      localStorage.setItem('ai_verdict_theme', ${JSON.stringify(scenario.theme)});
      document.documentElement.setAttribute('data-theme', ${JSON.stringify(scenario.theme)});
    `;
    await cdp.send("Runtime.evaluate", { expression: setSessionScript });
    currentAuthUser = scenario.user.user.username;
    currentTheme = scenario.theme;

    // Navigate to page
    await cdp.send("Page.navigate", { url: scenario.url });
    await sleep(1500);

    // If scenario specifies a rule to select in Studio:
    if (scenario.ruleSelect) {
      const selectRuleScript = `
        (function() {
          // Find option matching ruleSelect
          const select = document.querySelector('select');
          if (select) {
            const opt = Array.from(select.options).find(o => o.text.includes('${scenario.ruleSelect}'));
            if (opt) {
              select.value = opt.value;
              select.dispatchEvent(new Event('change', { bubbles: true }));
            }
          }
        })();
      `;
      await cdp.send("Runtime.evaluate", { expression: selectRuleScript });
      await sleep(1000);
    }

    for (const vp of scenario.viewports) {
      const filename = `${scenario.pageKey}_${vp.name}.png`;
      const filePath = path.join(OUTPUT_DIR, filename);

      // Set viewport device metrics
      await cdp.send("Emulation.setDeviceMetricsOverride", {
        width: vp.width,
        height: vp.height,
        deviceScaleFactor: 1,
        mobile: false,
      });
      await sleep(400);

      // Run DOM geometry checks
      const domCheckScript = `
        (function() {
          const doc = document.documentElement;
          const body = document.body;
          const scrollWidth = Math.max(doc.scrollWidth, body.scrollWidth);
          const hasHorizontalOverflow = scrollWidth > window.innerWidth + 2;

          // Check sticky action columns
          const stickyCells = Array.from(document.querySelectorAll('.vcds-sticky-action-col, th.sticky, td.sticky'));
          const stickyCount = stickyCells.length;

          // Check for any text clipping / ellipsis
          const clippedTitles = Array.from(document.querySelectorAll('h1, h2, h3, .font-bold'))
            .filter(el => el.scrollWidth > el.clientWidth && el.clientWidth > 0 && window.getComputedStyle(el).textOverflow === 'ellipsis')
            .map(el => el.textContent.trim().slice(0, 40));

          // Check visible buttons
          const buttons = Array.from(document.querySelectorAll('button:not([disabled])')).map(b => b.textContent.trim());

          return {
            hasHorizontalOverflow,
            scrollWidth,
            innerWidth: window.innerWidth,
            stickyCount,
            clippedTitlesCount: clippedTitles.length,
            clippedTitlesSample: clippedTitles.slice(0, 3),
            hasStickyActions: stickyCount > 0,
            url: window.location.href,
            pageTitle: document.title,
          };
        })();
      `;

      const evalRes = await cdp.send("Runtime.evaluate", {
        expression: domCheckScript,
        returnByValue: true,
      });

      const domMetrics = evalRes.result.value || {};

      // Capture screenshot
      const shot = await cdp.send("Page.captureScreenshot", { format: "png" });
      fs.writeFileSync(filePath, Buffer.from(shot.data, "base64"));
      const stat = fs.statSync(filePath);

      console.log(`  ✓ ${filename} (${stat.size} bytes) | Overflow: ${domMetrics.hasHorizontalOverflow} | Sticky: ${domMetrics.stickyCount} cells`);

      manifest.push({
        scenario: scenario.pageKey,
        filename,
        filepath: filePath,
        viewport: vp.name,
        width: vp.width,
        height: vp.height,
        theme: scenario.theme,
        userRole: scenario.user.user.role,
        bytes: stat.size,
        horizontalOverflow: domMetrics.hasHorizontalOverflow,
        scrollWidth: domMetrics.scrollWidth,
        stickyCellsCount: domMetrics.stickyCount,
        description: scenario.description,
      });
    }
  }

  console.log(`\n[4/5] Writing validation manifest...`);
  const manifestPath = path.join(OUTPUT_DIR, "validation_manifest.json");
  fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2));
  console.log(`Wrote ${manifest.length} screenshot records to ${manifestPath}`);

  console.log("[5/5] Cleaning up Chrome session...");
  cdp.close();
  chromeProcess.kill();
  try {
    fs.rmSync(tempProfile, { recursive: true, force: true });
  } catch {}

  console.log("\n=== AUTHENTICATED POPULATED VALIDATION COMPLETE ===");
  console.log(`Total Artifacts Captured: ${manifest.length} populated screenshots`);
}

main().catch((err) => {
  console.error("FATAL ERROR in validation runner:", err);
  process.exit(1);
});
