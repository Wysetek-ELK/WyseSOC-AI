# Validation & Trust — Admin & User Guide

This guide covers the two specialized pages dedicated to offline historical simulation replay, statistical trust measurement, and controlled automation qualification in Verdictum AI.

---

## 1. Agent Simulation Lab (`/agent-simulation-lab`)

### 1. What is this page?
The Agent Simulation Lab is an offline testing and historical replay laboratory that evaluates detection rules and AI prompts against captured datasets before production deployment.

### 2. Why do we need it?
It allows engineers to measure accuracy, detect regressions, and identify missed threats without risking live security operations or incident closures.

### 3. Practical Use Case
Before rolling out a prompt change for firewall port scans, an engineer creates a simulation job replaying 50 historical incidents to verify 100% agreement and zero critical false negatives.

### 4. How to Use
1. Navigate to **Agent Simulation Lab** from the sidebar.
2. Review existing simulation replay jobs and their completion status.
3. Click **New Simulation Job**: Select detection rule, provider type (`SIMULATED` heuristic or `OPENAI_COMPATIBLE` LLM), and sample limit.
4. Click **Launch Simulation Run**.
5. Click on completed jobs to inspect per-incident agreement, trust scores, and latency.

### 5. Prerequisites
- SOC Analyst or Administrator role.
- Historical incident records in the database.

### 6. Expected Result
Empirical validation report showing agreement rate, confusion breakdown, and regression safety.

### 7. Related Pages
- [Agent Intelligence Studio](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#1-agent-intelligence-studio-agent-intelligence-studio) (`/agent-intelligence-studio`)
- [Verdict Intelligence](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/VALIDATION_AND_TRUST.md#2-verdict-intelligence-verdict-intelligence) (`/verdict-intelligence`)
- [Detection Intelligence](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#2-detection-intelligence-detection-intelligence) (`/detection-intelligence`)

---

## 2. Verdict Intelligence (`/verdict-intelligence`)

### 1. What is this page?
Verdict Intelligence is a quantitative trustworthiness, statistical calibration, and autonomous pilot governance dashboard.

### 2. Why do we need it?
It ensures that automated AI verdicts are backed by rigorous mathematical standards (Wilson Score 95% confidence intervals, sample size gating) and supervises controlled pilot deployments.

### 3. Practical Use Case
A SOC Director examines the Trust Score distribution across 500 incidents and verifies that Rule `PH_RULE_HEAVY_TCP_HOST_SCAN` has achieved a 97.2% Wilson lower bound before approving pilot automation.

### 4. How to Use
1. Open **Verdict Intelligence** from the sidebar.
2. **Tab 1 (Overview):** Review average Trust Scores (1–10 scale) and automation readiness.
3. **Tab 2 (Accuracy & Calibration):** Inspect empirical validation vs. simulation runs.
4. **Tab 3 (Rule-wise Trustworthiness):** Check per-rule calibration status and Wilson confidence bounds.
5. **Tab 4 (Explainability):** Enter an incident ID to calculate its 5-factor Trust Assessment score.
6. **Tab 5 (Controlled Pilot):** Configure shadow-mode pilots, supervisor verify thresholds, and emergency rollbacks.

### 5. Prerequisites
- Administrator or Senior Analyst role for pilot modifications; read access for viewers.

### 6. Expected Result
Mathematical transparency into AI reliability and safe governance of automation pilots.

### 7. Related Pages
- [Agent Intelligence Studio](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/AGENT_INTELLIGENCE.md#1-agent-intelligence-studio-agent-intelligence-studio) (`/agent-intelligence-studio`)
- [Agent Simulation Lab](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/VALIDATION_AND_TRUST.md#1-agent-simulation-lab-agent-simulation-lab) (`/agent-simulation-lab`)
- [AI Triage Workbench](file:///c:/Users/amit/OneDrive/Documents/SOC-AI-Agent/docs/admin-guide/SOC_OPERATIONS.md#2-ai-triage-workbench-ai-triage-workbench) (`/ai-triage-workbench`)
