# Platform Control — Admin & User Guide

This guide covers the four platform control and administrative configuration pages in Verdictum AI.

---

## 1. Inference Control (`/inference-control`)

### 1. What is this page?
Inference Control is a real-time hardware health, resource utilization, and token economics monitoring console for the AI inference cluster.

### 2. Why do we need it?
It provides operational visibility into GPU VRAM, KV cache usage, CPU/memory loads, token budgets, and historical latency to ensure high availability and prevent performance bottlenecks.

### 3. Practical Use Case
A platform administrator checks the Verdictum Cortex GPU status after a high-volume incident burst, observing that VRAM is at 62%, KV cache is healthy, and average response latency is 1,240 ms.

### 4. How to Use
1. Navigate to **Inference Control** from the sidebar.
2. Inspect **Verdictum Core** (Backend API & Platform Engine, `verdictum-core-01`) CPU, RAM, and Disk metrics.
3. Inspect **Verdictum Cortex** (vLLM / Qwen GPU Inference Engine, `verdictum-cortex-01`) status, model name, and KV cache utilization.
4. Review the **Token Bifurcation** widget: Breakdown of tokens across Incident Triage, Batch Triage, Simulation Replay, and Policy Testing.
5. Check cluster status alerts if Verdictum Cortex is offline or unreachable.

### 5. Prerequisites
- System monitoring service active; Verdictum Core & Verdictum Cortex telemetry accessible.

### 6. Expected Result
Full situational awareness of AI cluster health, token costs, and processing latency.

### 7. Related Pages
- [Agent Mission Control](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#1-agent-mission-control-agent-mission-control) (`/agent-mission-control`)
- [Agent Configuration](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/PLATFORM_CONTROL.md#2-agent-configuration-agent-configuration) (`/agent-configuration`)
- [Verdictum Sentinel](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#5-verdictum-sentinel-soc-chatbot) (`/soc-chatbot`)

---

## 2. Agent Configuration (`/agent-configuration`)

### 1. What is this page?
Agent Configuration is the master integration settings and environmental preferences panel for FortiSIEM and the Verdictum Cortex LLM server.

### 2. Why do we need it?
It centralizes API endpoints, authentication credentials, network timeouts, context window budgets, and operational flags in one secure interface.

### 3. Practical Use Case
An administrator updates the FortiSIEM hostname, tests the connection successfully with green feedback, adjusts the LLM context window budget to 16,384 tokens, and enables Double-Blind Review Mode.

### 4. How to Use
1. Open **Agent Configuration** from the sidebar.
2. **FortiSIEM Section:** Enter Host URL, Username, Password, and timeout; click **Test Connection**; click **Save Configuration**.
3. **Local LLM Section:** Configure Verdictum Cortex Host, Port, Model Name (`Qwen/Qwen2.5-7B-Instruct-AWQ`), and context budget; click **Test LLM Connection**.
4. **Preferences Section:** Toggle **Blind Review Mode** (hides AI verdicts across analysts) and switch themes.

### 5. Prerequisites
- Administrator role required to save or test credentials.

### 6. Expected Result
Securely persisted system settings and verified connectivity to external security infrastructure.

### 7. Related Pages
- [Inference Control](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/PLATFORM_CONTROL.md#1-inference-control-inference-control) (`/inference-control`)
- [Telemetry Hub](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#3-telemetry-hub-telemetry-hub) (`/telemetry-hub`)
- [Governance & Access](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/PLATFORM_CONTROL.md#3-governance--access-governance-access) (`/governance-access`)

---

## 3. Governance & Access (`/governance-access`)

### 1. What is this page?
Governance & Access is the user management, role-based access control (RBAC), and immutable security audit log center.

### 2. Why do we need it?
It enforces the principle of least privilege, ensures multi-tenant isolation, and provides tamper-proof historical accountability for all administrative and triage actions.

### 3. Practical Use Case
A Security Director creates a new user account for a junior analyst with the "SOC Analyst" role and reviews audit logs to verify who engaged the emergency automation kill-switch last night.

### 4. How to Use
1. Navigate to **Governance & Access** from the sidebar.
2. **Tab 1 (User Management):** Fill out the "Create New User" form (Username, Email, Full Name, Password, Role) and click **Create User**.
3. View the table of active users and toggle user status as needed.
4. **Tab 2 (Audit Trail):** Inspect timestamped records of user logins, rule transitions, prompt approvals, and system configurations.

### 5. Prerequisites
- Administrator role for user creation and modification; read-only access for analysts.

### 6. Expected Result
Strict access control compliance and verifiable audit history.

### 7. Related Pages
- [Agent Configuration](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/PLATFORM_CONTROL.md#2-agent-configuration-agent-configuration) (`/agent-configuration`)
- [Agent Intelligence Studio](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#1-agent-intelligence-studio-agent-intelligence-studio) (`/agent-intelligence-studio`)

---

## 4. Verdictum AI Admin Guide (`/admin-guide`)

### 1. What is this page?
The Verdictum AI Admin Guide is an interactive user documentation and operational reference manual integrated directly into the application interface.

### 2. Why do we need it?
It empowers analysts, engineers, and administrators to understand system workflows, prerequisites, and use cases without leaving the platform or consulting external documents.

### 3. Practical Use Case
A newly hired L1 analyst uses the Admin Guide to understand how the 7-stage verification pipeline works, reviews the step-by-step instructions for the Double-Blind Review Workbench, and clicks a direct link to the Human Review Queue.

### 4. How to Use
1. Open **Verdictum AI Admin Guide** from the bottom of the sidebar.
2. Use the left-side Table of Contents to navigate through the 4 core groups (SOC Operations, Agent Intelligence, Validation & Trust, Platform Control) or the "How Verdictum AI Works" end-to-end workflow guide.
3. Use the search bar to locate specific terms, pages, or use cases.
4. Click direct links to jump immediately to the corresponding application page.
5. Use **Previous** and **Next** buttons at the bottom of each page for guided reading.

### 5. Prerequisites
- Accessible to all authenticated users (SOC Analysts, Administrators, Read-Only Viewers).

### 6. Expected Result
Instant comprehension of application capabilities, operational procedures, and safety rules.

### 7. Related Pages
- [Agent Mission Control](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#1-agent-mission-control-agent-mission-control) (`/agent-mission-control`)
- [AI Triage Workbench](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#2-ai-triage-workbench-ai-triage-workbench) (`/ai-triage-workbench`)
- [Agent Intelligence Studio](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#1-agent-intelligence-studio-agent-intelligence-studio) (`/agent-intelligence-studio`)
