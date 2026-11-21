# 06 — Test Fixture Provenance and Eligibility

**Verdictum AI — AIS 2.1a Unified Population Hotfix**  
**Investigation:** Patterned Test UUID Provenance & Eligibility Rules  
**Pattern Under Review:** `10000000-0000-0000-0000-000000000001` and `20000000-0000-0000-0000-000000000001`  
**Timestamp:** 2026-11-21T11:16:50+05:30  
**Status:** AUDITED, VERIFIED & GUARDED  

---

## 1. Provenance Investigation

An extensive codebase and database audit was conducted to determine the origin of patterned UUIDs:

1. **Static Codebase Grep:**
   - Patterned UUIDs like `10000000-0000-0000-0000-000000000001` were found in unit test fixtures (`backend/tests/test_ais_evaluation_tracking.py`) and legacy mock verification documentation.
   - They were created specifically as deterministic identifiers for synthetic test harnesses to avoid collisions with randomized UUIDs during isolated test execution.

2. **Server 1 Operational Database Audit:**
   - Executed queries against live tables: `incidents`, `analyst_verdict_reviews`, `actual_llm_prompt_captures`, `verdict_trust_assessment_records`, and `rule_learning_profiles`.
   - **Result:** **Zero (0)** patterned UUIDs exist in any operational table on Server 1.
   - All 13 operational incidents are authentic FortiSIEM events (#335, #543, #546, #595, #664, #705, #729, #841, #1477, #2339, #7411, #7422, #7475) with valid SIEM event timestamps, reporting IPs (`172.26.29.65`, `172.26.31.254`), and customer tenant bindings (`Demo-SOC`, `GDC_NOC`).

---

## 2. Evidence-Backed Eligibility Policy

To guarantee that test fixtures cannot contaminate production evaluation metrics even if inadvertently introduced during testing or development, the following eligibility policy is enforced:

### Policy Rule: Exclude Patterned Synthetic Identifiers
```python
import re

PATTERNED_TEST_UUID_REGEX = re.compile(
    r"^[0-9]0000000-0000-0000-0000-[0-9a-f]{12}$",
    re.IGNORECASE
)

def is_eligible_incident(incident_id: str) -> bool:
    if not incident_id:
        return False
    # Reject patterned test fixtures
    if PATTERNED_TEST_UUID_REGEX.match(str(incident_id).strip()):
        return False
    return True
```

### Scope of Enforcement:
- **`RuleLearningService.evaluate_rule_accuracy`:** Excludes candidate reviews matching the regex from ground truth and accuracy calculations.
- **`AisEvaluationService.get_rule_evaluation_tracking_overview`:** Filters out synthetic incidents from authoritative operational tracking.
- **Physical Data Integrity:** In accordance with non-destructive hotfix guidelines, synthetic records are not physically dropped if present in test environments; rather, they are excluded at query and calculation boundaries with audit logging.
