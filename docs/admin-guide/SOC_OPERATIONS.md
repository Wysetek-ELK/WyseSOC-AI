# SOC Operations — Admin & User Guide

This guide covers the five primary operational pages used daily by Security Operations Center (SOC) analysts, shift leads, and incident responders in Verdictum AI.

---

## 1. Agent Mission Control (`/agent-mission-control`)

### 1. What is this page?
Agent Mission Control is the executive and operational dashboard for Verdictum AI. It provides real-time visibility into overall security posture, automated triage throughput, and live cluster health across Verdictum Core (Server 1 / Platform API, logical hostname `verdictum-core-01`) and Verdictum Cortex (Server 2 / vLLM AI Engine, logical hostname `verdictum-cortex-01`).

### 2. Why do we need it?
SOC managers and lead analysts need a single pane of glass to monitor incident inflow, automation status, and system capacity without digging through multiple queues or running manual database queries.

### 3. Practical Use Case
During a morning shift handover, the SOC Lead reviews the 24-hour True Positive vs. False Positive ratio and checks Verdictum Cortex cluster health before assigning escalations to Tier 1 analysts.

### 4. How to Use
1. Open **Agent Mission Control** from the top of the sidebar.
2. Review the top KPI cards: Ingested Incidents, AI Triage Coverage, and TP/FP breakdown.
3. Inspect the Server Infrastructure Monitor for Verdictum Core (API/DB) and Verdictum Cortex (LLM) health status.
4. Check the Recent Triage Activity stream for high-severity alerts.
5. If new incidents are pending reconciliation, click **Reconcile Pending** to trigger background processing.

### 5. Prerequisites
- Active user account (Administrator, SOC Analyst, or Read-Only Viewer).
- Telemetry data ingested via Telemetry Hub or FortiSIEM sync.
- Operational with or without an active LLM (displays offline advisory status gracefully).

### 6. Expected Result
Instant situational awareness of SOC throughput, AI triage performance, and cluster availability.

### 7. Related Pages
- [AI Triage Workbench](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#2-ai-triage-workbench-ai-triage-workbench) (`/ai-triage-workbench`)
- [Telemetry Hub](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#3-telemetry-hub-telemetry-hub) (`/telemetry-hub`)
- [Human Review Queue](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#4-human-review-queue-human-review-queue) (`/human-review-queue`)
- [Inference Control](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/PLATFORM_CONTROL.md#1-inference-control-inference-control) (`/inference-control`)

---

## 2. AI Triage Workbench (`/ai-triage-workbench`)

### 1. What is this page?
The AI Triage Workbench is the central investigation workspace where analysts inspect security alerts, review AI-generated verdicts, and examine underlying raw evidence.

### 2. Why do we need it?
It automates the repetitive and time-consuming task of initial evidence gathering, allowing analysts to quickly validate whether an alert is a benign false alarm or an active attack.

### 3. Practical Use Case
An analyst investigates Incident #176061 (SSH Tunneling alert), reviews the AI's proposed False Positive verdict, verifies the destination IP in the raw evidence table, and confirms authorized backup activity.

### 4. How to Use
1. Navigate to **AI Triage Workbench** from the sidebar.
2. Filter incidents by Detection Rule, Severity, or search by IP/hostname.
3. Toggle **Blind Review Mode** if conducting unbiased independent evaluation.
4. Click on an incident row to view its details, or click **Run AI Analysis** for un-triaged events.
5. Inspect the AI Verdict modal: Confidence score, reasoning summary, and grounded evidence table.

### 5. Prerequisites
- SOC Analyst or Administrator role.
- Ingested incidents in the database.
- Local LLM connectivity for live triage, or mock fallback mode when offline.

### 6. Expected Result
Rapid determination of incident veracity supported by grounded, hallucination-free evidence.

### 7. Related Pages
- [Agent Mission Control](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#1-agent-mission-control-agent-mission-control) (`/agent-mission-control`)
- [Human Review Queue](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#4-human-review-queue-human-review-queue) (`/human-review-queue`)
- [Telemetry Hub](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#3-telemetry-hub-telemetry-hub) (`/telemetry-hub`)
- [Detection Intelligence](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#2-detection-intelligence-detection-intelligence) (`/detection-intelligence`)

---

## 3. Telemetry Hub (`/telemetry-hub`)

### 1. What is this page?
Telemetry Hub is the data ingestion and synchronization center responsible for connecting to FortiSIEM, importing offline telemetry archives, and orchestrating continuous background polling.

### 2. Why do we need it?
It ensures that the AI analysis engine always has fresh security events from firewalls, endpoints, and servers without manual file transfers.

### 3. Practical Use Case
A SOC engineer configures the 5-minute automated FortiSIEM sync poller and manually pulls Incident #176061 to test immediate triage throughput.

### 4. How to Use
1. Navigate to **Telemetry Hub** from the sidebar.
2. **To pull a single incident:** Enter the FortiSIEM Incident ID and click **Pull & Ingest Incident**.
3. **To run a batch sync:** Set batch size and click **Pull Latest Incidents Batch**.
4. **To toggle continuous polling:** Click **Start Background Poller** (monitors next sync countdown).
5. **For offline testing:** Drag and drop a JSON/CSV telemetry file into the upload dropzone.

### 5. Prerequisites
- Administrator or SOC Analyst permissions.
- Configured FortiSIEM API credentials in Agent Configuration (or local mock fallback mode enabled).

### 6. Expected Result
Telemetry records ingested, normalized into canonical fields, and added to the triage queue.

### 7. Related Pages
- [AI Triage Workbench](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#2-ai-triage-workbench-ai-triage-workbench) (`/ai-triage-workbench`)
- [Agent Mission Control](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#1-agent-mission-control-agent-mission-control) (`/agent-mission-control`)
- [Agent Configuration](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/PLATFORM_CONTROL.md#2-agent-configuration-agent-configuration) (`/agent-configuration`)

---

## 4. Human Review Queue (`/human-review-queue`)

### 1. What is this page?
The Human Review Queue is a collaborative human-in-the-loop escalation workbench where complex, disputed, or high-risk security incidents are thoroughly investigated, assigned, and resolved by SOC analysts.

### 2. Why do we need it?
It prevents unchecked automated actions, provides a structured workspace for analyst questions and notes, and records verified ground truth for AI model learning.

### 3. Practical Use Case
An L1 analyst encounters an ambiguous PowerShell execution alert, marks it as "Awaiting Evidence", asks a question to the system owner, and records an approved change order as evidence.

### 4. How to Use
1. Open **Human Review Queue** from the sidebar.
2. Filter by investigation status (`ASSIGNED`, `IN_PROGRESS`, `PENDING_REVIEW`, `DISPUTED`).
3. Click an incident to open the **Investigation Drawer**.
4. Add investigation notes, post questions, or attach additional telemetry files.
5. Select the final determination (`ACCEPTED`, `OVERRIDDEN`, `DISPUTED`) and toggle **Mark as Independently Verified**.
6. Click **Submit Final Determination**.

### 5. Prerequisites
- SOC Analyst or Administrator role.
- Assigned or unreviewed incidents in the database.

### 6. Expected Result
Investigation updated, ticket resolution recorded, and verified ground-truth precedent stored in Agent Memory.

### 7. Related Pages
- [AI Triage Workbench](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#2-ai-triage-workbench-ai-triage-workbench) (`/ai-triage-workbench`)
- [Agent Memory](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#3-agent-memory-agent-memory) (`/agent-memory`)
- [Agent Intelligence Studio](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#1-agent-intelligence-studio-agent-intelligence-studio) (`/agent-intelligence-studio`)

---

## 5. Verdictum Sentinel (`/soc-chatbot`)

### 1. What is this page?
Verdictum Sentinel is an **AI SOC Investigation Copilot** powered directly by **Verdictum Cortex** that allows analysts to query security concepts, deobfuscate malicious scripts, map incidents to MITRE ATT&CK techniques, interpret threat intelligence, and draft containment playbooks using natural language.

### 2. Why do we need it?
It accelerates tactical investigation by providing on-demand guidance, threat intelligence summaries, and script analysis directly within the analyst's workflow without leaving the platform.

### 3. Practical Use Case
An analyst pastes an obfuscated Base64 PowerShell one-liner from an alert, and Sentinel deobfuscates the script, extracts the malicious C2 domain, and recommends containment steps.

### 4. How to Use
1. Navigate to **Verdictum Sentinel** from the sidebar.
2. *(Optional)* Select an active incident from the dropdown to attach its telemetry context.
3. Click a Quick Prompt (e.g., "MITRE ATT&CK Mapping" or "Deobfuscate PowerShell") or type a custom query.
4. Click **Send** and inspect the streamed response with latency and token analytics.
5. If Verdictum Cortex LLM is offline, review the offline fallback banner.

### 5. Prerequisites
- Active Verdictum Cortex Qwen LLM cluster for live inference (graceful advisory message when offline).
- User authenticated with SOC Analyst or Administrator role.

### 6. Expected Result
Instant expert analysis, decoded payloads, and structured containment checklists.

### 7. Related Pages
- [AI Triage Workbench](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#2-ai-triage-workbench-ai-triage-workbench) (`/ai-triage-workbench`)
- [Inference Control](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/PLATFORM_CONTROL.md#1-inference-control-inference-control) (`/inference-control`)
- [Agent Mission Control](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#1-agent-mission-control-agent-mission-control) (`/agent-mission-control`)
