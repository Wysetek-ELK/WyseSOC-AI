# 06 — Manual L1 Analyst Test Guide: Actual LLM Prompt Inspector

**Platform:** Verdictum AI — Agent Intelligence Studio 2.0  
**Feature:** View Actual LLM Prompt  
**Target Audience:** L1 SOC Analysts, Incident Responders, SOC Leads  
**Date:** November 14, 2026  

---

## 1. Purpose of This Feature

When Verdictum AI generates an AI verdict (e.g. `TRUE_POSITIVE`, `FALSE_POSITIVE`, or `REQUIRES_ATTENTION`), L1 analysts often need to understand:
- *Why did the Local LLM reach this verdict?*
- *What investigation instructions was it given?*
- *What incident evidence and historical precedents did it see?*
- *Did it follow the approved SOC policy or an unapproved draft?*

The **View Actual LLM Prompt** button in **Agent Intelligence Studio 2.0** allows you to see the **exact request payload** that Verdictum AI (Server 1) sent over the network to the Local LLM (Server 2) for that specific incident.

---

## 2. Step-by-Step Walkthrough

### Step 1: Open Agent Intelligence Studio 2.0
1. Sign in to Verdictum AI as an Analyst or Administrator.
2. Navigate to **Agent Intelligence Studio** from the left navigation menu (`/agent-intelligence-studio`).

### Step 2: Access the Prompt Inspector
You can open the inspector from two locations:
- **Header Action Bar:** Click the emerald button labeled **"View Actual LLM Prompt"** with the terminal icon at the top of the Studio.
- **Simulation / Verdict Results Table:** When running a simulation or reviewing past cases, click the small terminal icon `[>_]` in the incident row.

### Step 3: Enter or Verify the Incident ID
- If you clicked from an incident row, the inspector opens automatically with that incident's prompt.
- If you opened from the top button, enter an Incident ID (e.g. `INC-SCAN-TEST-001` or your FortiSIEM incident ID) in the search box in the modal header and click **Inspect**.

---

## 3. Reading the Inspector Header & Banners

### 3.1 Status Banner
Always look at the colored banner at the top of the modal:

| Banner | Color | Meaning |
|---|---|---|
| **Captured Runtime Prompt** | Green | Verified outbound request recorded when Verdictum AI contacted the LLM. |
| **Historical Capture Unavailable** | Amber | This verdict was evaluated before the prompt capture feature was deployed. The payload was not recorded. |
| **Preview Only** | Sky Blue | A live generated preview based on current policy rules. **Not proof** of what was sent in the past. |

### 3.2 Prompt Integrity Badge
Located in the upper right of the L1 summary card:
- **Prompt Integrity: Verified (Green Shield):** The recorded request payload matches its cryptographic SHA-256 hash, used an approved policy version, and strictly quarantined untrusted telemetry.
- **Prompt Integrity: Mismatch Detected (Red Alert):** The saved payload appears tampered or diverged from its recorded hash. Notify your SOC Lead.
- **Prompt Integrity: Unverified (Gray Shield):** The prompt is a preview or represents an unapproved policy.

---

## 4. Reading the L1 Summary Card

Directly beneath the banner, the L1 Summary explains the core facts:
> **"This is the investigation instruction and incident evidence that Verdictum AI sent to the Local LLM to generate this verdict."**

Review the 5 highlighted metrics:
1. **Policy Version:** Confirms which version of the rule prompt was active (e.g., `Version 2 (APPROVED)`).
2. **Mandatory Evidence:** Shows whether required fields (Source IP, Target Port, Event Count, Threshold) were present in the incident telemetry.
3. **RAG Precedents:** Shows how many historical similar cases were included as few-shot examples (e.g., `None (Zero RAG)` or `1 Included`).
4. **Verdict Returned:** The verdict issued by the Local LLM (`TRUE_POSITIVE`, `FALSE_POSITIVE`, etc.).
5. **Policy Approval Match:** Confirms whether the prompt matches the SOC Lead's approved baseline.

---

## 5. Navigating the 6 Inspector Tabs

| Tab | What It Shows | What L1 Analysts Should Check |
|---|---|---|
| **1. Execution Summary** | Incident ID, rule name, model, execution time, latency ms, policy source, dispatch status. | Confirm the model used (e.g. `Qwen 2.5 7B Instruct`) and that dispatch status is `COMPLETED`. |
| **2. System Prompt** | The exact compiled system prompt sent to the LLM. | Read Sections 1-9 to verify the investigation directive, detection conditions (e.g. `Threshold: 50.0 distinct hosts`), and true/false positive indicators. |
| **3. Incident Payload** | The exact user message with normalized FortiSIEM telemetry. | Look between `<UNTRUSTED_INCIDENT_DATA>` and `</UNTRUSTED_INCIDENT_DATA>` to see the exact IPs, ports, and event counts the LLM evaluated. |
| **4. Historical Precedents** | Historical RAG cases injected into inference. | Verify whether previous analyst verdicts influenced the LLM. If empty, the LLM relied purely on rule logic. |
| **5. Output Contract** | Mandatory JSON schema enforced on the LLM. | Confirms the LLM was forced to return structured fields: `verdict`, `confidence`, `reason`, `supporting_evidence`. |
| **6. Technical Details** | Token usage, generation settings (temperature, max_tokens), SHA-256 hash. | Check prompt and completion tokens. Verify that `request_sha256` is recorded. |

---

## 6. Copying and Exporting

- **Copy Prompt:** Click the **"Copy Prompt"** button at the top right of the tabs to copy the complete system prompt to your clipboard.
- **Export JSON / Markdown:** Click **JSON** or **Markdown** to download a permanent evidence dossier for an audit, incident report, or post-incident review.
- **Role Redaction:** If you are a SOC Analyst, internal IP addresses and secrets will be automatically masked as `[REDACTED_IP]` or `[REDACTED_SECRET]` to protect company confidentiality. Administrators can view unredacted data.
