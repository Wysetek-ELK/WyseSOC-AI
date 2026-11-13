# Verdictum AI — Interactive Admin & Operations Guide

Welcome to the **Verdictum AI — Agentic SOC Intelligence** Admin Guide. This manual is designed for SOC analysts, incident responders, detection engineers, and security administrators to understand the operational purpose, practical workflows, and prerequisites for every capability in the platform.

---

## 1. Guide Structure & Sitemap

The application is structured around four primary operational domains covering 14 core pages, plus an end-to-end incident lifecycle workflow:

```
Verdictum AI Platform
├── 1. SOC OPERATIONS
│   ├── Agent Mission Control (/agent-mission-control)
│   ├── AI Triage Workbench (/ai-triage-workbench)
│   ├── Telemetry Hub (/telemetry-hub)
│   ├── Human Review Queue (/human-review-queue)
│   └── SOC AI Chatbot (/soc-chatbot)
│
├── 2. AGENT INTELLIGENCE
│   ├── Agent Intelligence Studio (/agent-intelligence-studio)
│   ├── Detection Intelligence (/detection-intelligence)
│   └── Agent Memory (/agent-memory)
│
├── 3. VALIDATION & TRUST
│   ├── Agent Simulation Lab (/agent-simulation-lab)
│   └── Verdict Intelligence (/verdict-intelligence)
│
├── 4. PLATFORM CONTROL
│   ├── Inference Control (/inference-control)
│   ├── Agent Configuration (/agent-configuration)
│   ├── Governance & Access (/governance-access)
│   └── Verdictum AI Admin Guide (/admin-guide)
│
└── 5. HOW VERDICTUM AI WORKS (End-to-End Workflow)
    └── FortiSIEM Ingestion → Normalization → Detection Evaluation → Local LLM Reasoning →
        Claim Validation → Human Review → Rule Learning & Governance
```

---

## 2. Domain Documentation Links

- [SOC Operations Guide](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md): Operational monitoring, triage workbench, telemetry ingestion, human review queue, and AI copilot chatbot.
- [Agent Intelligence Guide](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md): Detection engineering studio, rule catalogs, and institutional memory repository.
- [Validation & Trust Guide](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/VALIDATION_AND_TRUST.md): Historical simulation replay lab, statistical trust scores, and Wilson score confidence gating.
- [Platform Control Guide](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/PLATFORM_CONTROL.md): Hardware monitoring, integration configuration, RBAC user management, and audit trails.
- [How Verdictum AI Works](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/END_TO_END_WORKFLOW.md): Step-by-step trace of how an incident flows from FortiSIEM through AI triage, claim validation, analyst verification, and rule learning.

---

## 3. Operational Guarantees

1. **Deterministic Claim Validation:** AI predictions are never trusted blindly. An independent validator verifies all factual claims against raw source telemetry.
2. **Double-Blind Analyst Review:** Analysts evaluate incidents without seeing AI predictions to eliminate confirmation bias and create verified ground truth.
3. **Fail-Closed Safety:** Automated incident closures are strictly disabled by default (`ENABLE_AUTO_CLOSURE = False`). A rule must satisfy all 12 safety barriers and reach explicit production approval before automation is permitted.
4. **Offline Resilience:** If the local GPU LLM server is offline, the system safely continues operations in advisory mode, routing all incidents to the human analyst queue without data loss.
