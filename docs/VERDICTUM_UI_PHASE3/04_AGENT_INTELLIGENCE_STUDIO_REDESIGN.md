# VERDICTUM AI — PHASE 3
# 04. Agent Intelligence Studio 2.0 Redesign Specification

**Document Version:** 3.0.0  
**Phase:** Phase 3 — Unified Compact UI/UX Modernization  
**Page Implementation:** `frontend/src/app/agent-intelligence-studio/page.tsx`  
**Overview Component:** `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`  

---

## 1. Architectural Transformation

Agent Intelligence Studio 2.0 serves as the policy synthesis and governance nexus for all FortiSIEM detection rules. The Phase 3 redesign transitions AIS from a congested 7-tab layout into a clean, operational 3-Primary Tab architecture:

```
[Tab 1: Overview] (Default)  |  [Tab 2: Analyst Review & Learning]  |  [Tab 3: Advanced Configuration]
```

A prominent **Rollout Toggle** (`VERDICTUM_COMPACT_UI_ENABLED`) allows operators to switch between the new Compact Experience and the Legacy 7-Tab View, with state persisted in `localStorage`.

---

## 2. Tab 1 — Overview (Default Landing View)

The Overview tab is rendered immediately upon opening any detection rule, providing instant operational clarity answering:
1. What is the current rule state?
2. What is working?
3. What is failing?
4. What is the next immediate action?

### 2.1 Hero Metrics Summary
- **Rule Quality Card:** Displays validated score (e.g. `92/100`) and passed gates tally (`8/8 passed`).
- **AI Accuracy Card:** Displays verified accuracy (e.g. `96.7%` or `N/A (Requires verified analyst reviews)`). Never shows a misleading 0% when zero reviews exist.
- **Analyst Reviews Card:** Displays count of completed reviews against the 30-review pilot requirement.
- **Automation Status Card:** Displays enforcement state (`DISABLED`, `PILOT`, `APPROVED`, `ACTIVE`) with operational status dot.

### 2.2 Top Next Action Directive
A high-contrast card prominently instructing the analyst on their next required task:
- If rule definition is missing: *"Review and import FortiSIEM correlation threshold definitions."*
- If reviews are needed: *"Conduct independent double-blind reviews on pending incidents in Analyst Review tab."*
- If validation passed: *"Review simulation replay results and proceed to Production Approval."*

### 2.3 Consolidated Diagnostic Issues ("What Needs Attention?")
Replaces scattered error alerts with a single prioritized container. Deduplicates identical root causes across multiple backend services and maps technical error codes to plain-language operational summaries:
- **Title:** Plain-language issue description.
- **Cause:** Specific technical condition triggering the failure.
- **Missing Elements:** Exact telemetry fields or test samples required.
- **Impact:** Operational consequence (e.g. *"Production approval is blocked"*).
- **Corrective Action:** 1-click button deep-linking directly to the remediation tab.

### 2.4 Quick-Glance System Health Grid
Provides instant visual status for:
- **Quality Gates G1–G8:** Compact badges indicating status for each individual gate.
- **Evidence Contract Completeness:** Percentage of required SIEM fields currently mapped.
- **Ground Truth Sample Size:** Visual progress toward 30-sample pilot and 100-sample production gates.

### 2.5 Quick Action Bar
Unified action buttons:
- `Synthesize Intelligent Draft`: Triggers LLM draft generation.
- `Validate Quality`: Executes deterministic G1–G8 quality gates.
- `Run Simulation`: Launches offline replay simulation.
- `Approve Policy`: Opens production gating sign-off modal (disabled if G1–G8 or criteria fail).
- `Rollback`: Safely reverts to any previous policy version.

---

## 3. Tab 2 — Analyst Review & Learning

Tab 2 consolidates the rule learning workflow:
- **Empirical Accuracy Tracking:** Visual progress bar toward pilot (30 samples) and production (100 samples) thresholds.
- **Confusion Matrix:** True Positive, True Negative, False Positive, False Negative, and Abstained tallies.
- **Disputed Incidents Table:** Incidents where analyst determinations disagreed with SIEM historical closure.
- **Production Eligibility Checklist:** Transparent checklist detailing exact unfulfilled criteria blocking autonomous closure.

---

## 4. Tab 3 — Advanced Configuration

Tab 3 organizes the deep technical tooling into a segmented sub-navigation bar:
1. **Policy Editor:** 9 structured policy sections with code highlighting and markdown editing.
2. **Quality Gates:** In-depth diagnostics and evidence requirements for Gates G1 through G8.
3. **SIEM Semantics:** Detection objective, primary archetype, and MITRE ATT&CK mappings.
4. **Evidence Contract:** Mandatory core fields, optional fields, and missing requirement alerts.
5. **Simulation Lab:** Historical incident replay benchmarking.
6. **Drift & Monitoring:** Semantic drift tracking and policy revision history.
