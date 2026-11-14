# Verdictum AI Branding & Server Naming Implementation Report

**Document Version:** 1.0.0  
**Date:** November 14, 2026  
**Status:** Completed & Validated  
**Scope:** Full-stack branding and naming alignment across Frontend, Backend, Configuration, and Documentation  

---

## 1. Executive Summary

This report documents the implementation of the approved branding and naming convention across the entire Verdictum AI platform. The objective was to establish unified, production-grade identity standards across all user interfaces, status telemetry, API metadata, and architectural documentation without impacting underlying business logic, database schemas, inference pipelines, security guardrails, or physical infrastructure.

### Approved Naming Architecture

| Component | Legacy / Previous Name | Approved Production Name | Logical Hostname | Primary Function |
|---|---|---|---|---|
| **Platform** | Verdictum AI | **Verdictum AI** | N/A | Unified autonomous SOC decision platform |
| **Server 1** | Server 1 / Application Server | **Verdictum Core** | `verdictum-core-01` | Platform orchestration, ingestion, DB, deterministic triage |
| **Server 2** | Server 2 / LLM Server | **Verdictum Cortex** | `verdictum-cortex-01` | Dedicated local AI & GPU inference engine (Qwen 2.5 7B) |
| **SOC AI Chatbot** | SOC AI Chatbot | **Verdictum Sentinel** | N/A | Conversational SOC copilot interface |
| **Chatbot Persona** | SOC AI Copilot | **Sentinel — AI SOC Investigation Copilot** | N/A | Context-aware investigation and threat intelligence copilot |

---

## 2. Frontend Implementation

All frontend modifications preserve existing responsive layouts, Tailwind CSS tokens, iconography, and navigation routes.

### 2.1 Sidebar Navigation
- **File:** `frontend/src/components/layout/Sidebar.tsx`
- **Updates:**
  - Renamed primary navigation link from `SOC AI Chatbot` to `Verdictum Sentinel`.
  - Updated navigation tooltip and badge (`COPILOT`).
  - Preserved internal URL routing to `/soc-chatbot` to prevent breaking bookmarks and deep-links.

### 2.2 Verdictum Sentinel Copilot Interface
- **File:** `frontend/src/app/soc-chatbot/page.tsx`
- **Updates:**
  - **Heading & Persona:** Set to `Verdictum Sentinel` with role descriptor `AI SOC Investigation Copilot`.
  - **Description:** Updated to *"Context-aware autonomous investigation copilot powered by Verdictum Cortex..."*
  - **Header Badges:** Added permanent `Powered by Verdictum Cortex` pill badge alongside live telemetry status:
    - Connected state: `Cortex Online` (emerald pulse)
    - Disconnected / degraded state: `Cortex Offline` (amber alert)
    - Probing state: `Probing Cortex...`
  - **Empty State Display:** Renamed card header to `Ask Sentinel — AI SOC Investigation Copilot`.
  - **Chat Messages & Streamers:** Updated assistant identity to `Verdictum Sentinel · Cortex`.
  - **Thinking Indicator:** Updated to `Sentinel is investigating evidence...`.
  - **Input Placeholder:** Set to `Ask Sentinel to investigate incidents, analyze threats, or explain detection rules...`.
  - **Settings Drawer:** Labeled endpoint settings as `Active Endpoint (Verdictum Cortex)`.

### 2.3 Server Infrastructure Monitor
- **File:** `frontend/src/components/system/ServerInfrastructureMonitor.tsx`
- **Updates:**
  - Server 1 Node Card: Renamed to `Verdictum Core (Platform Engine)` with logical badge `verdictum-core-01`.
  - Server 2 Node Card: Renamed to `Verdictum Cortex (AI Inference Engine)` with logical badge `verdictum-cortex-01`.
  - Gradient legends, CPU/RAM/VRAM utilization cards, and topology graphs updated with approved branding.

### 2.4 Agent Configuration & Topology
- **File:** `frontend/src/app/agent-configuration/page.tsx`
- **Updates:**
  - Panel header renamed to `Verdictum Cortex Inference Engine Integration`.
  - Topology nodes labeled as `Verdictum Core · verdictum-core-01` and `Verdictum Cortex · verdictum-cortex-01`.
  - Connection test status messages updated to `Verdictum Cortex Connection Successful`.
  - Outbound IP label updated to `Verdictum Core Outbound Public IP`.

### 2.5 Inference Control & Simulation Lab
- **Files:** `frontend/src/app/inference-control/page.tsx`, `frontend/src/app/agent-simulation-lab/page.tsx`
- **Updates:**
  - Cluster degraded badge updated to `DEGRADED (CORTEX OFFLINE)`.
  - Comments and breadcrumbs updated to reference `Verdictum Core`.
  - Simulation provider options updated to `Verdictum Cortex LLM`.

### 2.6 Telemetry Hub & Token Bifurcation
- **Files:** `frontend/src/app/telemetry-hub/page.tsx`, `frontend/src/components/telemetry/HistoricalTelemetryTimeline.tsx`, `frontend/src/components/telemetry/TokenBifurcationWidget.tsx`
- **Updates:**
  - Timeline storage indicators updated to `Verdictum Core Storage` / `Verdictum Core Persistent DB`.
  - Token bifurcation widgets updated: `Verdictum Core Ledger`, `Verdictum Cortex (vLLM Engine)`, and `Active Verdictum Cortex Providers`.

### 2.7 AI Triage Workbench & Pilot Controls
- **Files:** `frontend/src/app/ai-triage-workbench/page.tsx`, `frontend/src/app/ai-triage-workbench/[id]/page.tsx`, `frontend/src/components/pilot/PilotControlAndDashboard.tsx`
- **Updates:**
  - Provenance badges: `• LIVE_PROVIDER (Verdictum Cortex) • Cortex Online`.
  - Pilot execution controls: `Cortex: ONLINE/OFFLINE`, with offline disclaimer: *"Live batches strictly reject simulated fallbacks when Verdictum Cortex is offline."*

### 2.8 Administrative Guide & Architectural Walkthroughs
- **Files:**
  - `frontend/src/data/admin-guide/pagesGuideData.ts`
  - `frontend/src/data/admin-guide/architectureFlowData.ts`
  - `frontend/src/data/admin-guide/requirementsData.ts`
  - `frontend/src/data/admin-guide/decisionFlowData.ts`
  - `frontend/src/data/admin-guide/glossaryAndTroubleshootingData.ts`
  - `frontend/src/data/admin-guide/incidentExampleData.ts`
  - `frontend/src/components/admin-guide/AdminGuideInteractiveReader.tsx`
  - `frontend/src/components/admin-guide/GuidedTourSection.tsx`
  - `frontend/src/components/admin-guide/RequirementsSection.tsx`
- **Updates:**
  - Page definitions updated to `Verdictum Sentinel` and `Verdictum Cortex`.
  - Architecture stages across all 17 workflow steps mapped to `Verdictum Core` and `Verdictum Cortex`.
  - Troubleshooting FAQs updated: *"What happens when Verdictum Cortex is offline?"*

---

## 3. Backend & API Implementation

Backend modifications maintain 100% backward compatibility for API consumers, database schemas, and external integrations.

### 3.1 Chat API & Sentinel System Prompt
- **Files:** `backend/app/schemas/chat.py`, `backend/app/api/chat.py`
- **Updates:**
  - Added `logical_hostname: str = "verdictum-cortex-01"` and `server_name: str = "Verdictum Cortex"` to `ChatStatusResponse`.
  - System Prompt identity updated:
    ```text
    You are Verdictum Sentinel, an AI SOC Investigation Copilot embedded within the Verdictum AI platform.
    Your mission is to assist SOC analysts in investigating security incidents, interpreting FortiSIEM telemetry,
    analyzing detection rules, and formulating containment strategies.
    ```
  - Preserved dual-compatibility status messages: `"Connected to Verdictum Cortex (Server 2)"` and `"Cannot reach Server 2 (Verdictum Cortex)"`.
  - Token telemetry logs set role identifier to `"Verdictum Sentinel"`.

### 3.2 System Monitor Service
- **File:** `backend/app/services/system_monitor_service.py`
- **Updates:**
  - Server 1 sample payload updated: `server_name = "Verdictum Core (Platform & SIEM Engine)"`, `logical_hostname = "verdictum-core-01"`.
  - Server 2 sample payload updated: `server_name = "Verdictum Cortex (AI & GPU Inference Engine)"`, `logical_hostname = "verdictum-cortex-01"`.

### 3.3 LLM Configuration Service & Schemas
- **Files:** `backend/app/schemas/llm_config.py`, `backend/app/services/llm_config_service.py`
- **Updates:**
  - Added `logical_hostname: str = "verdictum-cortex-01"`, `core_logical_hostname: str = "verdictum-core-01"`, and `core_outbound_ip: Optional[str] = None` to `LLMConfigResponse`.
  - Connection test responses return informative strings referencing `Verdictum Cortex (Server 2)`.

### 3.4 Health Checks & Prometheus Metrics
- **File:** `backend/app/api/health.py`
- **Updates:**
  - Health check docstrings updated to reference `Verdictum Core` and `Verdictum Cortex`.
  - Health response payload enriched with `logical_hostname` and `server_name` attributes for both `system` and `local_llm` components.
  - Prometheus metrics HELP strings updated to reference `Verdictum Cortex inference engine`.

### 3.5 FortiSIEM, Incidents, & Telemetry Timeline
- **Files:** `backend/app/api/fortisiem.py`, `backend/app/api/incidents.py`, `backend/app/services/telemetry_timeline_service.py`
- **Updates:**
  - Offline 503 detail messages updated to `Verdictum Cortex (Server 2) is currently offline`.
  - Telemetry timeline responses include `logical_hostname: "verdictum-core-01"` and `server_name: "Verdictum Core"` while retaining `storage_node: "Server 1 Persistent Storage"` for legacy assertions.

---

## 4. Documentation & Administrative Guides

- `docs/admin-guide/README.md`: Added Section 3 ("Component Architecture & Server Naming") defining `Verdictum Core`, `Verdictum Cortex`, and `Verdictum Sentinel`.
- `docs/admin-guide/SOC_OPERATIONS.md`: Updated Section 5 to `## 5. Verdictum Sentinel (/soc-chatbot)`.
- `docs/admin-guide/PLATFORM_CONTROL.md`: Updated Inference Control and Agent Configuration documentation.
- `docs/admin-guide/END_TO_END_WORKFLOW.md`: Updated Mermaid sequence diagram and lane annotations.
- `ARCHITECTURE.md` & `README.md`: Updated primary architecture specifications to reflect the approved two-server topology.

---

## 5. Backward Compatibility & Architectural Safeguards

1. **API Contracts:** No existing endpoints were moved or deprecated. All `/soc-chatbot`, `/chat/message`, `/chat/status`, and `/llm/config` routes remain unchanged.
2. **Database Identifiers:** Database columns, primary keys, audit logs, and historical records remain unaltered.
3. **Infrastructure Configuration:** Physical hostnames, DNS entries, IP settings, environment variable keys (`LOCAL_LLM_HOST`, `LOCAL_LLM_PORT`, `FORTISIEM_HOST`), systemd unit files, and SSH keys were not modified.
4. **Dual-Compatibility Strings:** Where legacy test harnesses or external monitors rely on substrings (e.g. `Server 2`), strings were composed with both approved names and legacy qualifiers (e.g., `"Verdictum Cortex (Server 2)"`).
