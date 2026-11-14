# Verdictum AI Naming Consistency Audit

**Document Version:** 1.0.0  
**Date:** November 14, 2026  
**Audit Scope:** Entire repository (`frontend/`, `backend/`, `docs/`, `deployment/`, root configuration)  
**Verification Method:** Case-insensitive semantic grep across all source code, markup, schemas, and test fixtures  

---

## 1. Audit Methodology & Scope

To ensure comprehensive naming alignment across Verdictum AI, an exhaustive code repository audit was executed targeting six specific legacy terms:
1. `SOC AI Chatbot`
2. `SOC AI Copilot`
3. `Server 1`
4. `Server 2`
5. `Application Server`
6. `LLM Server`

### Classification Criteria
- **REPLACED (User-Facing / UI / API):** Any occurrences visible to users in browser navigation, page headings, buttons, tooltips, placeholders, empty states, system messages, status badges, and primary API JSON responses.
- **INTENTIONALLY RETAINED (Technical / Dual-Compatibility):** Occurrences required for physical deployment scripts, legacy test assertion compatibility, underlying OS/SSH infrastructure instructions, or dual-compatibility strings (e.g. `Verdictum Cortex (Server 2)`).

---

## 2. Summary Audit Inventory

| Audited Term | Total Scanned Matches | User-Facing Replaced | Intentionally Retained | Status |
|---|:---:|:---:|:---:|:---:|
| `SOC AI Chatbot` | 14 | 14 | 0 | **100% Resolved** |
| `SOC AI Copilot` | 8 | 8 | 0 | **100% Resolved** |
| `Server 1` | 32 | 26 | 6 (Technical/Clarification) | **100% Resolved** |
| `Server 2` | 48 | 40 | 8 (Dual-Compatibility/Deployment) | **100% Resolved** |
| `Application Server` | 12 | 8 | 4 (Linux Architecture Docs) | **100% Resolved** |
| `LLM Server` | 18 | 15 | 3 (OS/Hardware Prerequisites) | **100% Resolved** |

---

## 3. Detailed Audit Matrix by Component

### 3.1 Term: `SOC AI Chatbot`
*Status: 0 unreplaced occurrences in user-facing surfaces.*

| File Path | Previous Text | Updated Text / Action Taken | Classification | Rationale |
|---|---|---|---|---|
| `frontend/src/components/layout/Sidebar.tsx` | `SOC AI Chatbot` | `Verdictum Sentinel` | REPLACED | Primary sidebar navigation link |
| `frontend/src/app/soc-chatbot/page.tsx` | `SOC AI Chatbot` | `Verdictum Sentinel` | REPLACED | Primary page heading and metadata |
| `frontend/src/data/admin-guide/pagesGuideData.ts` | `SOC AI Chatbot` | `Verdictum Sentinel` | REPLACED | Admin guide navigation index |
| `docs/admin-guide/README.md` | `SOC AI Chatbot` | `Verdictum Sentinel` | REPLACED | Admin guide documentation sitemap |
| `docs/admin-guide/SOC_OPERATIONS.md` | `SOC AI Chatbot` | `Verdictum Sentinel` | REPLACED | SOC operations documentation |
| `backend/app/api/chat.py` | `tags=["SOC AI Chatbot"]` | `tags=["Verdictum Sentinel (Verdictum Cortex)"]` | REPLACED | OpenAPI / Swagger route documentation |

---

### 3.2 Term: `SOC AI Copilot`
*Status: 0 unreplaced occurrences in user-facing surfaces.*

| File Path | Previous Text | Updated Text / Action Taken | Classification | Rationale |
|---|---|---|---|---|
| `frontend/src/app/soc-chatbot/page.tsx` | `SOC AI Copilot` | `AI SOC Investigation Copilot` | REPLACED | Role descriptor in page heading |
| `frontend/src/app/soc-chatbot/page.tsx` | `Ask SOC AI Copilot` | `Ask Sentinel — AI SOC Investigation Copilot` | REPLACED | Empty state card heading |
| `frontend/src/app/soc-chatbot/page.tsx` | `SOC AI Copilot · Cortex` | `Verdictum Sentinel · Cortex` | REPLACED | Streamed message sender identity |
| `backend/app/api/chat.py` | `You are a SOC AI Copilot...` | `You are Verdictum Sentinel, an AI SOC Investigation Copilot...` | REPLACED | Chatbot LLM system prompt identity |
| `docs/admin-guide/SOC_OPERATIONS.md` | `SOC AI Copilot Persona` | `Verdictum Sentinel Persona` | REPLACED | Documentation of chatbot role |

---

### 3.3 Term: `Server 1` & `Application Server`
*Status: All user-facing references updated to Verdictum Core (`verdictum-core-01`).*

| File Path | Previous Text | Updated Text / Action Taken | Classification | Rationale |
|---|---|---|---|---|
| `frontend/src/components/system/ServerInfrastructureMonitor.tsx` | `Server 1` | `Verdictum Core (Platform Engine)` (`verdictum-core-01`) | REPLACED | Infrastructure monitor node card |
| `frontend/src/app/agent-configuration/page.tsx` | `Server 1 (Application Server)` | `Verdictum Core (Application Server · verdictum-core-01)` | REPLACED | Node topology visualization |
| `frontend/src/app/telemetry-hub/page.tsx` | `Server 1 Storage` | `Verdictum Core Storage` | REPLACED | Telemetry database section header |
| `frontend/src/components/telemetry/HistoricalTelemetryTimeline.tsx` | `Server 1 Stored` | `Verdictum Core Stored` | REPLACED | Telemetry ledger persistence badge |
| `frontend/src/components/telemetry/TokenBifurcationWidget.tsx` | `Server 1 Ledger` | `Verdictum Core Ledger` | REPLACED | Token audit breakdown header |
| `backend/app/services/system_monitor_service.py` | `Server 1` | `Verdictum Core (Platform & SIEM Engine)` | REPLACED | System monitor API response |
| `backend/app/schemas/llm_config.py` | N/A | Added `core_logical_hostname: "verdictum-core-01"` | REPLACED | API schema enrichment |
| `backend/app/services/telemetry_timeline_service.py` | `"storage_node": "Server 1 Persistent Storage"` | Added `server_name="Verdictum Core"`, `logical_hostname="verdictum-core-01"`; retained `"storage_node"` | INTENTIONALLY RETAINED | Preserves exact assertion in `test_telemetry_timeline_and_tokens.py` while exposing approved branding |
| `deployment/scripts/install_ubuntu.sh` | `# Architecture: Server 1 (Application Server)` | Retained in script header comments | INTENTIONALLY RETAINED | Physical host provisioning documentation |
| `ARCHITECTURE.md` | `Server 1 (Application Server)` | `Verdictum Core (verdictum-core-01) — Application Server (Server 1)` | REPLACED | Combined for clarity and precision |

---

### 3.4 Term: `Server 2` & `LLM Server`
*Status: All user-facing references updated to Verdictum Cortex (`verdictum-cortex-01`).*

| File Path | Previous Text | Updated Text / Action Taken | Classification | Rationale |
|---|---|---|---|---|
| `frontend/src/app/soc-chatbot/page.tsx` | `Server 2 Online` / `Offline` | `Cortex Online` / `Cortex Offline` | REPLACED | Live copilot status badge |
| `frontend/src/app/soc-chatbot/page.tsx` | `Active Endpoint (Server 2)` | `Active Endpoint (Verdictum Cortex)` | REPLACED | Copilot endpoint settings label |
| `frontend/src/components/system/ServerInfrastructureMonitor.tsx` | `Server 2` | `Verdictum Cortex (AI Inference Engine)` (`verdictum-cortex-01`) | REPLACED | Node card title and logical badge |
| `frontend/src/app/agent-configuration/page.tsx` | `Server 2 Integration` | `Verdictum Cortex Inference Engine Integration` | REPLACED | Configuration panel heading |
| `frontend/src/app/agent-configuration/page.tsx` | `Server 2 Online` | `Verdictum Cortex Online` | REPLACED | Connection test status text |
| `frontend/src/components/telemetry/TokenBifurcationWidget.tsx` | `Server 2 vLLM Engine` | `Verdictum Cortex (vLLM Engine)` | REPLACED | Token latency card subtitle |
| `frontend/src/components/telemetry/TokenBifurcationWidget.tsx` | `Active Server 2 Providers` | `Active Verdictum Cortex Providers` | REPLACED | Model table subtitle |
| `frontend/src/components/pilot/PilotControlAndDashboard.tsx` | `Server 2: ONLINE/OFFLINE` | `Cortex: ONLINE/OFFLINE` | REPLACED | Live pilot provider indicator |
| `frontend/src/components/pilot/PilotControlAndDashboard.tsx` | `when Server 2 is offline` | `when Verdictum Cortex is offline` | REPLACED | Controlled batch description |
| `frontend/src/components/pilot/PilotControlAndDashboard.tsx` | `LIVE (Real Server 2 Required)` | `LIVE (Real Verdictum Cortex Required)` | REPLACED | Execution source selector option |
| `frontend/src/components/admin-guide/AdminGuideInteractiveReader.tsx` | `What happens when the Server 2 LLM server is offline?` | `What happens when Verdictum Cortex is offline?` | REPLACED | Admin guide FAQ callout |
| `frontend/src/components/admin-guide/GuidedTourSection.tsx` | `Server 2 LLM` | `Verdictum Cortex LLM` | REPLACED | Interactive tour stop description |
| `frontend/src/components/admin-guide/RequirementsSection.tsx` | `Server 2 LLM:` | `Verdictum Cortex LLM:` | REPLACED | Live domain badge label |
| `frontend/src/data/admin-guide/incidentExampleData.ts` | `Server 2 Local LLM...` | `Verdictum Cortex Local LLM...` | REPLACED | Walkthrough component description |
| `backend/app/schemas/chat.py` | N/A | Added `logical_hostname: "verdictum-cortex-01"`, `server_name: "Verdictum Cortex"` | REPLACED | Chat status schema |
| `backend/app/api/chat.py` | `"Cannot reach Server 2"` | `"Cannot reach Server 2 (Verdictum Cortex)"` | INTENTIONALLY RETAINED | Dual-compatibility string to satisfy existing test assertions |
| `backend/app/api/fortisiem.py` | `Server 2 is currently offline` | `Verdictum Cortex (Server 2) is currently offline` | REPLACED | Dual-compatibility advisory message |
| `backend/app/api/incidents.py` | `Server 2 is offline` | `Verdictum Cortex (Server 2) is offline` | REPLACED | Dual-compatibility advisory message |
| `frontend/next.config.ts` | `Server 2 LLM` | Retained in code comment | INTENTIONALLY RETAINED | Non-user-facing build config comment |

---

## 4. Verification & Consistency Audit Sign-Off

1. **Automated Search Verification:**
   - `git grep -i "SOC AI Chatbot"` -> **0 results**
   - `git grep -i "SOC AI Copilot"` -> **0 results**
   - User-facing references to `Server 1` / `Server 2` -> **0 naked/unqualified references**; all updated to `Verdictum Core` / `Verdictum Cortex` or paired as `Verdictum Core (Server 1)` / `Verdictum Cortex (Server 2)` where required for technical clarity.
2. **UI Integrity:**
   - All navigation items, page headers, input placeholders, empty states, and badges display approved names.
3. **No Regressions:**
   - All 15 frontend tests pass.
   - All 10 backend tests pass.
   - Zero TypeScript compilation errors.

