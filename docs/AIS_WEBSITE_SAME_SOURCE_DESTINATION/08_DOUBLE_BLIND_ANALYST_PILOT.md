# 08 — Double-Blind SOC Analyst Pilot & Review Queue Protocol
**Target Rule:** `Website access policy violation: Same Source and Destination`  
**Rule UUID:** `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`  
**Workbench URL:** `/learning/rules/7bd13e89-0828-48e6-8cf5-f3cbf12d438c?tab=workbench`  
**Review Queue API:** `GET /api/reviews/pending?rule_id=7bd13e89-0828-48e6-8cf5-f3cbf12d438c`  
**Review Submission API:** `POST /api/reviews/{incident_id}/submit`  

---

## 1. Double-Blind Review Design & Non-Bias Invariant

To establish empirical ground truth without anchoring bias or circular self-validation, Verdictum AI implements a strict **Double-Blind Review Queue**:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   DOUBLE-BLIND WORKBENCH ARCHITECTURE                  │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Telemetry Ingestion  │ FortiGate UTM logs ingested and normalized   │
│ 2. Background AI Eval   │ Local LLM evaluates incident in background   │
│ 3. Strict UI Masking    │ Analyst queue serves incident with:          │
│                         │   • is_blind_mode: true                      │
│                         │   • ai_verdict: null (MASKED)                │
│                         │   • confidence: null (MASKED)                │
│                         │   • reason: null (MASKED)                    │
│ 4. Human Determination  │ Analyst reviews raw telemetry independently  │
│ 5. Submission & Reveal  │ Upon submission, AI verdict is revealed;     │
│                         │ agreement/disagreement is recorded in audit  │
│ 6. Ground-Truth Lock    │ Verified human verdict updates rule ground   │
│                         │ truth and feeds statistical calibration      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. API Endpoints & Verification

The review queue was tested directly against Server 1 (`172.26.41.240`):

1. **Queue Retrieval (`GET /api/reviews/pending?rule_id=7bd13e89-0828-48e6-8cf5-f3cbf12d438c&limit=15`):**
   - HTTP Status: `200 OK`
   - Total Pending Incidents: `220`
   - Active Mode: `blind_mode_active: true`
   - Payload Verification: `analyst_verdict: null`, `is_blind_mode: true`. AI verdict fields are completely omitted from the payload.
2. **Review Submission (`POST /api/reviews/{incident_id}/submit`):**
   - Payload:
     ```json
     {
       "analyst_verdict": "TRUE_POSITIVE",
       "analyst_notes": "Repeated attempts to access restricted gambling category; blocked by UTM profile.",
       "blind_mode_active": true,
       "evidence_references": ["EV-4142-PAYLOAD_DETAIL-webcategory"]
     }
     ```
   - Behavior: Validates determination, evaluates agreement against stored AI verdict, updates verified ground truth, and recalibrates confusion matrix.
3. **Dispute Adjudication (`POST /api/reviews/{review_id}/adjudicate`):**
   - Restricted to `Administrator`, `SOC_Manager`, or `Senior_Analyst`. Resolves disputes where Tier-1 analyst and AI verdict conflict.

---

## 3. Recommended Pilot Cohort (Initial 15 Incidents)

The following 15 incidents are designated as the initial human pilot cohort for SOC Tier-1 analysts:

| Queue # | Incident ID | DB UUID | Reporting Device | Client Source IP | Raw Events | Stratum |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | **#4142** | `bb793252...` | `HOST-172.26.31.254` | `172.26.29.74` | 1 | Rich UTM (LinkedIn) |
| **2** | **#4178** | `9db5da52...` | `HOST-172.26.31.254` | `172.26.29.72` | 2 | Rich UTM |
| **3** | **#4171** | `e73efb3c...` | `HOST-172.26.31.254` | `172.26.29.72` | 1 | Rich UTM |
| **4** | **#4170** | `ca30f736...` | `HOST-172.26.31.254` | `172.26.29.72` | 1 | Rich UTM |
| **5** | **#4176** | `a4300ced...` | `HOST-45.64.199.219` | `172.25.26.59` | 1 | Rich UTM (Overruled FP) |
| **6** | **#4177** | `e50f611f...` | `HOST-45.64.199.219` | `172.25.26.59` | 1 | Rich UTM |
| **7** | **#4172** | `e943933c...` | `HOST-45.64.199.219` | `172.25.26.59` | 1 | Rich UTM |
| **8** | **#4168** | `9d5e8f8f...` | `HOST-172.27.31.254` | `172.27.29.71` | 2 | Rich UTM |
| **9** | **#4158** | `d0f0ff4d...` | `HOST-172.27.31.254` | `172.27.29.53` | 1 | Rich UTM |
| **10** | **#4159** | `068e7366...` | `HOST-172.27.31.254` | `172.27.29.53` | 1 | Rich UTM |
| **11** | **#4148** | `5f751008...` | `HOST-45.64.199.219` | `172.25.24.219` | 0 | Header-Only |
| **12** | **#4145** | `00457a4e...` | `HOST-45.64.199.219` | `172.25.24.219` | 0 | Header-Only |
| **13** | **#3954** | `2efa3936...` | `HOST-45.64.199.219` | `172.25.24.219` | 2 | Rich UTM (Advertising) |
| **14** | **#4179** | Next in Queue | `HOST-172.26.31.254` | Subnet LAN | $\ge 1$ | Rich UTM |
| **15** | **#4180** | Next in Queue | `HOST-45.64.199.219` | Subnet DMZ | $\ge 1$ | Rich UTM |

---

## 4. Analyst Pilot Operational Runbook

SOC Analysts participating in the pilot must follow these instructions:

1. **Access the Workbench:** Open a browser and navigate to:
   `http://172.26.41.240/learning/rules/7bd13e89-0828-48e6-8cf5-f3cbf12d438c?tab=workbench`
2. **Review Telemetry:**
   - Inspect the source client IP, reporting device, destination domain, FortiGuard web category, and firewall action.
   - Note whether the connection was dropped or blocked by policy.
   - Check if an approved business exemption exists in the corporate ticketing system.
3. **Submit Determination:**
   - Select `TRUE_POSITIVE`, `FALSE_POSITIVE`, or `REQUIRES_ATTENTION`.
   - Provide brief rationale in the notes field.
   - Click **Submit Review**.
4. **Inspect Post-Submission Reveal:**
   - The UI reveals the background Local LLM verdict and confidence.
   - In case of disagreement, the review is automatically flagged for Senior Analyst adjudication.
