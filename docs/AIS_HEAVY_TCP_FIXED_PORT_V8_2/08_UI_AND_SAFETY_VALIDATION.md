# 08 — UI & Safety Validation Report

**Components:** Frontend Workbench (`frontend/src/lib/api.ts`), AIS Studio Maturity Strip, Emergency Automation Safeguards  
**Status:** Deployed, Built (`npm run build` PASS), and Operational on Server 1  

---

## 1. AIS Studio Maturity Strip & Governance Badging

In the Agent Intelligence Studio 2.0 interface, the policy maturity strip for `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` displays the following verified states:

| UI Badge / Strip Field | Rendered Value | Visual State / Color | Underlying Truth Source |
| :--- | :--- | :---: | :--- |
| **Active Version** | `v7 (APPROVED)` | Green Badge | `d79fb576-c6b9-4f63-9167-3c7a2419b70a` |
| **Candidate Version** | `v8 (DRAFT)` | Amber Badge | `20d4f788-85a5-437d-afbe-fe7fd80abca1` |
| **Quality Score** | `85.0 / 100` | Blue / Complete | Preflight & Static Gates G1–G7 Passed |
| **Empirical Accuracy** | `NOT MEASURABLE` | Neutral / Grey Alert | `0` verified human ground-truth reviews |
| **Production Automation** | `BLOCKED` | Red Shield / Disabled | `is_enabled: false` (Governance Locked) |
| **Sibling Rule Status** | `Heavy TCP Host Scan: v2 APPROVED` | Green Badge | Isolated, untouched, active |

---

## 2. AI Triage Workbench V8.2 Visual Fields

The API client schema (`frontend/src/lib/api.ts`) was expanded to surface the V8.2 integrity fields directly to SOC analysts:

1. **Normalized Confidence Badge:**
   - Displays canonical percentage: `e.g. 95.0%`.
   - Tooltip indicates scale declaration: `Scale: PERCENT_0_100`.
   - Rejection indicator: If `AMBIGUOUS_SCALE_REJECTED`, displays warning badge *"Uncalibrated Scale Rejected"*.

2. **Reasoning Integrity & Contradiction Alert:**
   - When `reasoning_integrity_status == "REASONING_CONTRADICTION"`, the workbench displays a prominent warning callout:
     > *"⚠️ Overruled by Reasoning Integrity Engine: Model narrative asserts unanswered probes / denied flows contradicting observed telemetry (100 bidirectional sessions, 0 denied)."*
   - Displays individual contradiction bullets directly beneath the model's reason narrative.

3. **Trust Score Gauge:**
   - Down-calibrated to `3/10` (Red / Low Trust) upon detection of contradiction, overriding the model's raw high confidence.
   - Highlights that analyst intervention is mandatory.

---

## 3. Frontend Build & Service Health Verification

On Server 1 (`172.26.41.240`):
- **Next.js Production Build:**
  ```bash
  cd /opt/wysesoc-ai/frontend && npm run build
  ```
  Result: Clean compilation with 0 TypeScript or linting errors.
- **Service Verification:**
  ```bash
  systemctl is-active --quiet ai-verdict-frontend.service
  curl -fsSI http://127.0.0.1:3000/login
  ```
  Result: `HTTP/1.1 200 OK` (Service is healthy and serving production assets).
