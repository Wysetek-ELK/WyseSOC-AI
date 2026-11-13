# Agent Intelligence — Admin & User Guide

This guide covers the three core pages dedicated to detection rule management, prompt engineering, quality gate validation, and institutional memory retention in Verdictum AI.

---

## 1. Agent Intelligence Studio (`/agent-intelligence-studio`)

### 1. What is this page?
Agent Intelligence Studio is a comprehensive engineering IDE for detection rules and AI prompts. It features 7 integrated tabs: Prompt Editor, Detection Intelligence, Evidence Contracts, Quality Gates, Simulation Lab, Drift & Monitoring, and Rule Learning & Governance.

### 2. Why do we need it?
It bridges the gap between detection engineering and AI governance, ensuring that every AI prompt is grounded, schema-validated, statistically evaluated, and qualified before production automation.

### 3. Practical Use Case
A detection engineer selects `PH_RULE_CS_SUSPICIOUS_ACTIVITY`, drafts version 3 of its prompt template, runs structural quality gates (G1–G8), benchmarks historical accuracy in the Simulation Lab, and monitors Wilson score confidence intervals.

### 4. How to Use
1. Open **Agent Intelligence Studio** and select a rule from the catalog.
2. **Tab 1 (Editor):** Draft 9-section prompt templates with standard variables.
3. **Tab 2 & 3 (Intelligence & Contract):** Review required fields and canonical schema mappings.
4. **Tab 4 (Quality Gates):** Execute automated syntax, schema, and completeness tests.
5. **Tab 5 (Simulation):** Replay historical incidents to measure empirical accuracy.
6. **Tab 6 (Drift):** Monitor telemetry and verdict drift.
7. **Tab 7 (Rule Learning & Governance):** Inspect Wilson score lower bounds, review confusion matrices, and manage production promotion.

### 5. Prerequisites
- Administrator or Senior Detection Engineer role.
- Configured detection rules in Detection Intelligence.

### 6. Expected Result
Validated, production-ready AI prompt versions bound to specific detection rules.

### 7. Related Pages
- [Detection Intelligence](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#2-detection-intelligence-detection-intelligence) (`/detection-intelligence`)
- [Agent Simulation Lab](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/VALIDATION_AND_TRUST.md#1-agent-simulation-lab-agent-simulation-lab) (`/agent-simulation-lab`)
- [Verdict Intelligence](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/VALIDATION_AND_TRUST.md#2-verdict-intelligence-verdict-intelligence) (`/verdict-intelligence`)
- [Agent Memory](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#3-agent-memory-agent-memory) (`/agent-memory`)

---

## 2. Detection Intelligence (`/detection-intelligence`)

### 1. What is this page?
Detection Intelligence is the central catalog and registry for all security detection rules synchronized from FortiSIEM and custom correlation rules.

### 2. Why do we need it?
It provides visibility into which rules are active, their severity, event types, telemetry signatures, and whether they have associated AI prompt versions.

### 3. Practical Use Case
A SOC manager reviews the catalog to verify that all high-priority brute-force and ransomware detection rules have active AI prompt versions assigned.

### 4. How to Use
1. Open **Detection Intelligence** from the sidebar.
2. Review aggregate statistics (Total Rules, Active, Rules with Prompts).
3. Filter rules by Severity, Active Status, or search by name.
4. Click **Sync from FortiSIEM** to refresh rule definitions from the SIEM.
5. Click any rule to view its conditions, field mappings, and linked prompt templates.

### 5. Prerequisites
- Read access for analysts; Administrator role to trigger SIEM rule sync.

### 6. Expected Result
Complete synchronization of detection rules and clarity on AI coverage.

### 7. Related Pages
- [Agent Intelligence Studio](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#1-agent-intelligence-studio-agent-intelligence-studio) (`/agent-intelligence-studio`)
- [AI Triage Workbench](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#2-ai-triage-workbench-ai-triage-workbench) (`/ai-triage-workbench`)
- [Telemetry Hub](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#3-telemetry-hub-telemetry-hub) (`/telemetry-hub`)

---

## 3. Agent Memory (`/agent-memory`)

### 1. What is this page?
Agent Memory is an institutional knowledge base that stores verified human analyst determinations, resolution precedents, and rationale to guide future AI reasoning.

### 2. Why do we need it?
It prevents repetitive investigations of known false positives and ensures the AI learns from past senior analyst decisions.

### 3. Practical Use Case
An analyst investigating a new scheduled task uses the "Find Similar Cases" tool to discover three identical incidents resolved as False Positives last month by another analyst with approved change orders.

### 4. How to Use
1. Open **Agent Memory** from the sidebar.
2. Filter precedents by rule, verdict (`TRUE_POSITIVE`, `FALSE_POSITIVE`), or keyword.
3. Use the **Similar Cases Search** tool: Enter an IP, command line, or incident ID to find historical matches.
4. Click on any record to inspect the original incident context and analyst explanation.
5. Administrators can click **Seed Initial Memory** to ingest baseline historical precedents.

### 5. Prerequisites
- Human analyst reviews completed in Human Review Queue or AI Triage Workbench.

### 6. Expected Result
Instant discovery of past investigation precedents and continuous knowledge retention.

### 7. Related Pages
- [Human Review Queue](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#4-human-review-queue-human-review-queue) (`/human-review-queue`)
- [AI Triage Workbench](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#2-ai-triage-workbench-ai-triage-workbench) (`/ai-triage-workbench`)
- [Agent Intelligence Studio](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#1-agent-intelligence-studio-agent-intelligence-studio) (`/agent-intelligence-studio`)
