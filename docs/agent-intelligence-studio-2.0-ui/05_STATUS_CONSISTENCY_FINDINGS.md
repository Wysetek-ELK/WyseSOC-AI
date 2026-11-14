# 05 - Status Consistency Findings

## 1. Regression Scenario: "Heavy TCP Host Scan On Fixed Port"

The detection rule **"Heavy TCP Host Scan On Fixed Port"** was audited as the primary regression and validation scenario to investigate and resolve coexisting inconsistencies reported in the UI:

- **Observed Inconsistencies:**
  1. *Production Active and readiness failures coexisted simultaneously.*
  2. *One view displayed archetype `NETWORK_SCAN` while another displayed `UNKNOWN`.*
  3. *Evidence field completeness showed 100% despite missing semantic correlation conditions.*
  4. *Rule quality score was 48/100, Quality Gates was 1/8 Passed, Analyst Reviews was 0, and LLM was offline.*

---

## 2. Root Cause Analysis

### Finding 1: Production Active vs Readiness Coexistence

- **Root Cause:** In the SIEM database, the rule row had `status = "ACTIVE"`, signifying that FortiSIEM was actively ingesting network scan alerts for this signature. However, the candidate policy version in Prompt Studio (v2) was an unverified draft with an incomplete definition (`quality_score = 48`, Gate G1 failed).
- **Pre-Existing Bug:** The UI displayed `Rule.status` ("ACTIVE") as the global rule status header, which operators interpreted as "AI automation is active and approved".
- **Resolution:**
  - Architecturally separated **SIEM Deployment Status** (`Rule.status`: `ACTIVE`, `INACTIVE`) from **AI Production Readiness** (`readiness_status`: `BLOCKED`, `INCOMPLETE`, `LEARNING`, etc.).
  - The UI now clearly displays: `Deployment: ACTIVE` (SIEM) alongside `Production Readiness: BLOCKED / INCOMPLETE` (AI).
  - Existing active SIEM rules are never suspended simply because their AI candidate policy is blocked.

### Finding 2: `NETWORK_SCAN` vs `UNKNOWN` Archetype Mismatch

- **Root Cause:** In `/api/prompts/summary`, the backend populated `detection_archetype` strictly by looking up `rule_intelligence_snapshots` table records:
  ```python
  # Old logic:
  snap = snaps_by_rule_id.get(r.id)
  archetype = snap.primary_archetype if snap else "UNKNOWN"
  ```
  If a rule had never been opened in the studio or snapshot job had not run, `snap` was `None`, resulting in `"UNKNOWN"`. Meanwhile, opening the studio ran dynamic classification (`DetectionArchetypeRegistry.classify_rule`), which correctly identified the pattern as `"NETWORK_SCAN"`.
- **Resolution:**
  - Updated `/api/prompts/summary` to fall back dynamically to `RuleIntelligenceAnalyzer.analyze_rule(r)` and `DetectionArchetypeRegistry.classify_rule(semantics, r)` whenever a snapshot is absent.
  - Archetype now uniformly reports `NETWORK_SCAN` across summary views, rule tables, and studio detail pages.

### Finding 3: False 100% Evidence Field Completeness

- **Root Cause:** In `frontend/src/components/compact/CompactDesignSystem.tsx`, the `EvidenceCompletenessIndicator` evaluated completeness as:
  ```typescript
  // Old logic:
  const ratio = requiredCount > 0 ? Math.round((availableCount / requiredCount) * 100) : 100;
  ```
  Because the incident payload happened to contain 5 standard telemetry fields (`srcIp`, `destIp`, `destPort`, `count`, `eventTime`), `availableCount = 5` and `requiredCount = 5`, yielding 100%.
  However, the underlying rule semantics lacked correlation threshold specifications, and Gate G3 failed because the semantic feasibility condition was unmet.
- **Resolution:**
  - Enhanced `EvidenceCompletenessIndicator` to accept `isSemanticsVerified`.
  - If semantics are unverified or mandatory contract conditions are unfulfilled, completeness is capped at 50% and explicitly labeled with an amber banner:
    `"Evidence Semantics Unverified (Raw telemetry fields present but unvalidated)"`.

### Finding 4: Insufficient Reviews & Offline LLM Handling

- **Root Cause:** Prior to this implementation, some views rendered accuracy as `0%` or left it blank when 0 analyst reviews existed, and fallback simulated runs were occasionally conflated with live model inference.
- **Resolution:**
  - When verified analyst reviews < 30, empirical accuracy strictly returns `N/A`.
  - When LLM is offline, live inference tests are blocked, and simulation replays explicitly record execution provenance (`is_simulated = True`, `provider_type = "SIMULATED"`). Simulated replays cannot satisfy production gate G8.

---

## 3. Verification & Regression Guarantee

The regression scenario is codified and verified in `backend/tests/test_production_readiness_engine.py`:
- `test_heavy_tcp_host_scan_status_consistency_and_archetype`:
  - Asserts archetype is `NETWORK_SCAN` (never `UNKNOWN`).
  - Asserts deployment status is `ACTIVE` while readiness is `BLOCKED`/`INCOMPLETE`.
  - Asserts 0 reviews yields `N/A` accuracy (never marked PASS).
  - Asserts admin approval is rejected (`400 Bad Request`) when quality blockers are present.
