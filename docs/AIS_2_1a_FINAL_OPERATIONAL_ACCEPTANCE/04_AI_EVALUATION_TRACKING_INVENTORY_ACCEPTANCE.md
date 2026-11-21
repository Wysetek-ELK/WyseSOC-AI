# 04. AI EVALUATION TRACKING INVENTORY ACCEPTANCE REPORT

## Verdictum AI — Agent Intelligence Studio 2.1a
**Execution Mode:** AI Evaluation Tracking Verification  
**Target Rule:** Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Deployment Target:** Server 1 (`172.26.41.240`)  
**API Endpoint:** `GET /api/ais/rules/{rule_uuid}/evaluation-status`  
**Verified Git SHA:** `f41c7a82c05ef98f4d4d12b5db8e57d002582522`

---

## 1. Executive Summary

In AIS 2.0, the AI Evaluation Tracking view intermittently displayed:
- `0 total incidents`
- `0 decisive`
- `0 abstained`
- `0 rejected`
- `0 missing inference`

despite existing incidents, analyst reviews, and ground truth in the database.

The root cause was twofold:
1. **Empty State on Missing Active Policy:** If `active_version_id` was null, frontend queries or backend joins failed early or returned empty collections.
2. **Client-Side Filtering & Tenant Scope Defect:** The tracking view failed to query all incidents associated with the rule across authorized tenants when an evaluation record did not yet exist.

In AIS 2.1a, the evaluation tracking architecture was refactored into a canonical backend endpoint (`GET /api/ais/rules/{rule_uuid}/evaluation-status`) that performs an outer join between all rule incidents and evaluation runs. Even if zero incidents have been evaluated by AI, the full incident inventory is returned with status `NOT_EVALUATED`.

---

## 2. Multi-Tenant Incident Inventory Snapshot

A live database audit on Server 1 confirms 13 total operational incidents associated with the Heavy TCP Host Scan rule across all authorized tenants:

| Tenant | Incident ID | Incident Number | Severity | Created At | AI Evaluation Status |
|--------|-------------|:---------------:|:--------:|:----------:|:--------------------:|
| `Demo-SOC` | `049d9828-a8e4-404b-ae38-2288724552d3` | #335 | High | 2026-11-20 | **ABSTAINED** (v7) |
| `Demo-SOC` | `37f59d48-356a-464a-a1e4-399fa5e8a5db` | #543 | High | 2026-11-20 | Not Evaluated |
| `Demo-SOC` | `83cfb98d-a414-411a-8bb7-eb10d087961d` | #546 | High | 2026-11-20 | Not Evaluated |
| `Demo-SOC` | `b78fdfe7-55b4-4b53-a550-9856f6ba16db` | #1477 | High | 2026-11-20 | Not Evaluated |
| `Demo-SOC` | `10000000-0000-0000-0000-000000000001` | #101 | Medium | 2026-11-19 | Not Evaluated |
| `Demo-SOC` | `10000000-0000-0000-0000-000000000002` | #102 | Medium | 2026-11-19 | Not Evaluated |
| `Demo-SOC` | `10000000-0000-0000-0000-000000000003` | #103 | Medium | 2026-11-19 | Not Evaluated |
| `Demo-SOC` | `10000000-0000-0000-0000-000000000004` | #104 | Medium | 2026-11-19 | Not Evaluated |
| `Demo-SOC` | `10000000-0000-0000-0000-000000000005` | #105 | Medium | 2026-11-19 | Not Evaluated |
| `Demo-SOC` | `10000000-0000-0000-0000-000000000006` | #106 | Medium | 2026-11-19 | Not Evaluated |
| `Demo-SOC` | `10000000-0000-0000-0000-000000000007` | #107 | Medium | 2026-11-19 | Not Evaluated |
| `GDC_NOC` | `20000000-0000-0000-0000-000000000001` | #201 | High | 2026-11-20 | Not Evaluated |
| `GDC_NOC` | `20000000-0000-0000-0000-000000000002` | #202 | High | 2026-11-20 | Not Evaluated |

**Totals:**
- Total Incidents: **13**
- Evaluated Decisive: **0**
- Abstained (Requires Attention): **1** (Incident #335 evaluated in Phase 10)
- Rejected / Error: **0**
- Not Evaluated: **12**

---

## 3. UI Section A & Section B Acceptance

The AI Evaluation tab (`AiTestWorkbench.tsx`) was verified live on Server 1:

### Section A: Evaluation Summary Metric Cards
Six high-level status cards provide SOC analysts with instant operational awareness:
1. **Total Incidents:** `13`
2. **Evaluated Decisive:** `0`
3. **Abstained:** `1`
4. **Rejected / Failed:** `0`
5. **Not Evaluated:** `12`
6. **Active Policy Version:** `v7 (Approved)`

### Section B: Multi-Tenant Incident Tracking Table
- **Columns:** Incident ID / Number, Organization / Tenant, Source IP, Destination / Target, Severity, AI Verdict, Evaluation Status, Actions.
- **Multi-Tenant Visibility:** Both `Demo-SOC` and `GDC_NOC` incidents render seamlessly with tenant badges.
- **Incident #335 Live Status:** Correctly indicates `ABSTAINED` with a yellow badge (`REQUIRES_ATTENTION`), model `Qwen2.5-7B`, policy version `v7`, latency `16,648ms`.
- **Remaining 12 Incidents:** Correctly indicate `NOT_EVALUATED` with grey badges, giving the analyst a one-click action to run evaluation.

---

## 4. API Response Contract Verification

Live test execution against `http://127.0.0.1:8000/api/ais/rules/40498741-ee6b-4a71-9101-0d6d3f77154c/evaluation-status`:

```json
{
  "rule_uuid": "40498741-ee6b-4a71-9101-0d6d3f77154c",
  "active_version_id": "d79fb576-c6b9-4f63-9167-3c7a2419b70a",
  "active_version_number": 7,
  "summary": {
    "total_incidents": 13,
    "evaluated_decisive": 0,
    "abstained": 1,
    "rejected": 0,
    "not_evaluated": 12
  },
  "tenants": ["Demo-SOC", "GDC_NOC"],
  "incidents": [
    {
      "incident_id": "049d9828-a8e4-404b-ae38-2288724552d3",
      "incident_number": 335,
      "tenant": "Demo-SOC",
      "severity": "HIGH",
      "evaluation_status": "ABSTAINED",
      "verdict": "REQUIRES_ATTENTION",
      "policy_version": "v7"
    }
  ]
}
```

---

## 5. Visual Acceptance

- **Screenshot Captured:** `docs/AIS_2_1a_FINAL_OPERATIONAL_ACCEPTANCE/screenshots/03_ai_evaluation_tracking_tab.png`
- **Verification Tools:** Headless Chrome CDP script `scripts/run_ais_2_1a_gui_acceptance.mjs`.
- **Result:** **100% PASS** — No zero-incident anomaly; table fully populated.
