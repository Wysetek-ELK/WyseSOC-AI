# 07 — Gate G8 Accuracy & Production Governance Assessment

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`, UUID `40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Active Policy:** v7 (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`, `APPROVED`, Active in Live Triage)  
**Candidate Policy:** DRAFT v8 (`20d4f788-85a5-437d-afbe-fe7fd80abca1`, `DRAFT`, Quality Score: `85.0/85.0`)  
**Production Automation State:** **`BLOCKED & DISABLED`** (`is_enabled: false`)  
**FortiSIEM Live Action State:** **`0 Automated Closures Executed`**  

---

## 1. Governance Quality Gates Audit (G1–G8)

AIS 2.0 enforces an 8-stage gate framework for policy evaluation and promotion:

| Gate | Verification Check | Score / Status | Evaluator | State |
| :--- | :--- | :---: | :--- | :---: |
| **G1** | Schema Validation & Untrusted Boundary Enclosure | `10.0 / 10.0` | `PolicyQualityValidator` | **PASS** |
| **G2** | Evidence Contract Completeness & Archetype Alignment | `15.0 / 15.0` | `EvidenceContractService` | **PASS** |
| **G3** | Adversarial Prompt Injection Defense & Sanitization | `15.0 / 15.0` | `PromptSafetyEngine` | **PASS** |
| **G4** | Grounding Directives & Hallucination Suppression | `15.0 / 15.0` | `ModelClaimExtractor` | **PASS** |
| **G5** | Deterministic Reasoning Contradiction Guards | `10.0 / 10.0` | `ReasoningIntegrityEngine` | **PASS** |
| **G6** | Confidence Normalization & Explicit Scale Metadata | `10.0 / 10.0` | `ConfidenceNormalizer` | **PASS** |
| **G7** | Token Budget & Compaction Compliance (<4096 / <768) | `10.0 / 10.0` | `TokenBudgetService` | **PASS** |
| **Subtotal** | **Preflight & Static Gates (G1–G7)** | **`85.0 / 85.0`** | **Automated Gate Evaluator** | **`PASS (100%)`** |
| **G8** | **Empirical Ground-Truth Accuracy & Wilson CI Validation** | **`PENDING`** | **`EmpiricalBenchmarkHarness`** | **`INSUFFICIENT_DATA`** |

---

## 2. Empirical Accuracy Status: Strictly `NOT MEASURABLE`

> [!CAUTION]
> **Zero Human Ground-Truth Reviews Exist in the Database.**
> In strict compliance with UPLA governance, scientific integrity, and anti-hallucination policies, empirical accuracy is officially designated as **`NOT MEASURABLE`**.

Under no circumstances will synthetic test runs, exploratory model replays, or self-evaluated LLM inferences be reported as ground-truth accuracy. In benchmark run `2074b011-9fe8-46fb-9937-ff5ead18fc61`:
- `total_scanned`: `6`
- `rule_matched`: `6`
- `analyst_labeled`: `0`
- `verified_ground_truth_cases`: `0`
- `empirical_accuracy`: `null` (`NOT_CALCULABLE`)
- `validation_state`: `INSUFFICIENT_DATA`

---

## 3. Production Automation Policy & Safety Invariants

Production automation for `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` is strictly **DISABLED**:

```json
{
  "rule_id": "40498741-ee6b-4a71-9101-0d6d3f77154c",
  "is_enabled": false,
  "min_trust_score": 7,
  "min_evidence_score": 80.0,
  "require_contract_verified": true,
  "max_daily_closures": 50,
  "current_daily_closures": 0,
  "kill_switch_active": false
}
```

### Safety Protections in Live Operation:
1. **v7 Remains Active:** The currently deployed live triage engine executes approved policy v7. Candidate v8 is retained strictly in `DRAFT` status and cannot execute on live incidents without explicit analyst promotion.
2. **Validator Overrule:** In the V8.2 benchmark, all 4 decisive `TRUE_POSITIVE` model proposals were overruled to `REQUIRES_ATTENTION` and their trust scores were capped at `3/10` (far below the `7/10` automation threshold).
3. **Emergency Disarm:** The global emergency disable endpoint (`POST /api/rule-learning/automation/emergency-disable-all`) remains active and verified.
