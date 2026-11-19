import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  BRANDING,
  COMPANY_NAME,
  SHORT_COMPANY_NAME,
  COPYRIGHT_NOTICE,
} from "../src/config/branding.ts";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FRONTEND_SRC = path.resolve(__dirname, "../src");

test("Centralized Branding Configuration defines required company and product constants", () => {
  assert.equal(
    BRANDING.company.fullName,
    "Wysetek Systems Technologists Pvt. Ltd.",
    "Company full name must be 'Wysetek Systems Technologists Pvt. Ltd.'"
  );
  assert.equal(
    BRANDING.company.shortName,
    "WYSETEK",
    "Company short name must be 'WYSETEK'"
  );
  assert.equal(
    BRANDING.company.developedByLabel,
    "Developed & Operated by",
    "Developed & Operated by label must match requirement"
  );
  assert.equal(
    BRANDING.company.sidebarAttribution,
    "by WYSETEK",
    "Sidebar attribution must be 'by WYSETEK'"
  );
  assert.equal(
    BRANDING.company.copyrightYear,
    2026,
    "Copyright year must be 2026"
  );
  assert.equal(
    BRANDING.company.copyrightNotice,
    "© 2026 Wysetek Systems Technologists Pvt. Ltd.",
    "Copyright notice must be '© 2026 Wysetek Systems Technologists Pvt. Ltd.'"
  );

  // Convenience exports
  assert.equal(COMPANY_NAME, "Wysetek Systems Technologists Pvt. Ltd.");
  assert.equal(SHORT_COMPANY_NAME, "WYSETEK");
  assert.equal(COPYRIGHT_NOTICE, "© 2026 Wysetek Systems Technologists Pvt. Ltd.");

  // Product titles and mottos
  assert.equal(BRANDING.product.name, "Verdictum AI");
  assert.equal(BRANDING.product.title, "VERDICTUM AI");
  assert.equal(BRANDING.product.platformSubtitle, "Agentic SOC Intelligence Platform");
  assert.equal(BRANDING.product.agenticSubtitle, "Agentic SOC Intelligence");
  assert.equal(BRANDING.product.securityMotto, "Evidence-Driven Security Intelligence");
});

test("Login Page incorporates centralized company branding below Evidence-Driven Security Intelligence", () => {
  const loginSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "app/login/page.tsx"),
    "utf-8"
  );

  // Must import centralized branding
  assert.match(
    loginSrc,
    /import\s*\{\s*BRANDING\s*\}\s*from\s*["']@\/config\/branding["']/,
    "Login page must import centralized BRANDING configuration"
  );

  // Preserves existing Verdictum AI logo, product title, and styling
  assert.match(loginSrc, /<BrandLogo[\s\S]*?size=\{92\}[\s\S]*?priority/);
  assert.match(loginSrc, /BRANDING\.product\.title/);
  assert.match(loginSrc, /BRANDING\.product\.platformSubtitle/);
  assert.match(loginSrc, /BRANDING\.product\.securityMotto/);

  // Directly below security motto, displays "Developed & Operated by" and company name
  const mottoPos = loginSrc.indexOf("BRANDING.product.securityMotto");
  const developedByPos = loginSrc.indexOf("BRANDING.company.developedByLabel");
  const companyNamePos = loginSrc.indexOf("BRANDING.company.fullName");

  assert.ok(
    mottoPos > 0 && developedByPos > mottoPos && companyNamePos > developedByPos,
    "Branding must appear directly below Evidence-Driven Security Intelligence in order: motto -> developedBy -> fullName"
  );

  // Typography and responsive classes
  assert.match(
    loginSrc,
    /text-\[9px\]\s+uppercase\s+tracking-widest\s+text-slate-500\s+font-mono\s+font-medium/,
    "Developed by label must use elegant, compact uppercase mono typography"
  );
  assert.match(
    loginSrc,
    /text-\[11px\]\s+sm:text-xs\s+font-semibold\s+tracking-wide\s+text-amber-300\/90\s+font-sans\s+mt-0\.5\s+text-center\s+leading-snug\s+px-1\s+break-words/,
    "Company name must use gold/amber accent, break-words, and responsive font sizing"
  );

  // Preserves authentication form, credentials fields, and JWT/RBAC notices
  assert.match(loginSrc, /handleSubmit/);
  assert.match(loginSrc, /Username or Analyst ID/);
  assert.match(loginSrc, /Password/);
  assert.match(loginSrc, /Sign In to Platform/);
  assert.match(loginSrc, /Authorized SOC Personnel Only • JWT/);
});

test("Sidebar Header displays 'by WYSETEK' in subtle gold text beneath Agentic SOC Intelligence", () => {
  const sidebarSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/layout/Sidebar.tsx"),
    "utf-8"
  );

  // Must import centralized branding
  assert.match(
    sidebarSrc,
    /import\s*\{[\s\S]*?BRANDING[\s\S]*?\}\s*from\s*["']@\/config\/branding["']/,
    "Sidebar must import centralized BRANDING configuration"
  );

  // Inside the expanded brand header div, order must be: name -> subtitle -> attribution ('by WYSETEK')
  assert.match(
    sidebarSrc,
    /BRANDING\.product\.name[\s\S]*?BRANDING\.product\.agenticSubtitle[\s\S]*?data-testid="sidebar-company-tagline"[\s\S]*?BRANDING\.company\.sidebarAttribution/,
    "Sidebar header must order: product name -> agentic subtitle -> attribution ('by WYSETEK')"
  );

  // Gold accent typography for "by WYSETEK"
  assert.match(
    sidebarSrc,
    /text-\[8px\]\s+text-amber-300\/85\s+font-mono\s+tracking-wider\s+uppercase\s+leading-tight\s+mt-0\.5\s+font-medium/,
    "Sidebar attribution must use subtle gold font-mono text"
  );

  // Header link title attribute includes full branding
  assert.match(
    sidebarSrc,
    /title=\{`\$\{BRANDING\.product\.name\}\s+\$\{BRANDING\.company\.sidebarAttribution\}\s+—\s+\$\{BRANDING\.product\.agenticSubtitle\}`\}/,
    "Header link title must combine product name, attribution, and subtitle"
  );
});

test("Sidebar Footer contains full company copyright notice in both expanded and collapsed layouts", () => {
  const sidebarSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/layout/Sidebar.tsx"),
    "utf-8"
  );

  // Full copyright notice in expanded state
  assert.match(
    sidebarSrc,
    /data-testid="sidebar-company-footer"/,
    "Sidebar footer must contain company footer element"
  );
  assert.match(
    sidebarSrc,
    /BRANDING\.company\.copyrightNotice/,
    "Sidebar footer must reference centralized copyrightNotice"
  );

  // Preserves inference widget intact with data-testid in both states
  assert.match(
    sidebarSrc,
    /data-testid="sidebar-inference-widget"/,
    "Inference widget must retain data-testid"
  );
  assert.match(
    sidebarSrc,
    /data-testid="sidebar-arch-label"/,
    "Inference widget architecture label must remain intact"
  );

  // Collapsed state support: copyright indicator with full tooltip and aria-label
  assert.match(
    sidebarSrc,
    /aria-label=\{BRANDING\.company\.copyrightNotice\}/,
    "Collapsed footer must expose accessible aria-label with full copyright notice"
  );
  assert.match(
    sidebarSrc,
    /title=\{BRANDING\.company\.copyrightNotice\}/,
    "Collapsed footer must expose title attribute with full copyright notice"
  );
});

test("Branding remains visible across all authenticated pages through persistent Shell layout", () => {
  const shellSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "components/layout/Shell.tsx"),
    "utf-8"
  );

  // Verifies Shell renders Sidebar for all authenticated (non-login) pages
  assert.match(shellSrc, /isLoginPage\s*=\s*pathname\s*===\s*["']\/login["']/);
  assert.match(shellSrc, /<Sidebar\s*\/>/);
  assert.match(shellSrc, /<Header\s*\/>/);
  assert.match(shellSrc, /<main className="flex-1 overflow-y-auto theme-main-canvas/);
});

test("Root metadata incorporates centralized branding", () => {
  const layoutSrc = fs.readFileSync(
    path.join(FRONTEND_SRC, "app/layout.tsx"),
    "utf-8"
  );

  assert.match(
    layoutSrc,
    /import\s*\{\s*BRANDING\s*\}\s*from\s*["']@\/config\/branding["']/,
    "Root layout must import centralized BRANDING configuration"
  );
  assert.match(layoutSrc, /\$\{BRANDING\.product\.name\}\s*—\s*\$\{BRANDING\.product\.platformSubtitle\}/);
  assert.match(layoutSrc, /\$\{BRANDING\.company\.fullName\}/);
});
