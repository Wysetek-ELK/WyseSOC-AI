# VERDICTUM AI — VALIDATION V1.2.1
## 08. BROWSER E2E RESULTS & SCREENSHOT SUITE MANIFEST

**Document Version:** 1.0.0  
**Test Suite:** `scripts/run_v1_2_1_validation.mjs`  
**Execution Environment:** Headless Google Chrome (CDP Port 9222)  
**Total Screenshots:** 20 (5 Scenarios × 4 Viewports)  
**Status:** 100% PASS (Zero DOM failures, Zero truncation)  

---

### 1. Viewport Matrix Tested
- **1024 × 768:** Compact desktop / SOC wall display baseline.
- **1280 × 800:** Standard analyst workstation / laptop.
- **1440 × 900:** Widescreen workstation.
- **1920 × 1080:** Full HD high-density SOC multi-monitor setup.

---

### 2. Complete Screenshot Inventory & File Table

| Scenario ID | Page Key | Viewport | File Path | File Size | DOM Assertion Status | Key Visual Finding |
|---|---|---|---|---|---|---|
| `SCN-HEAVY-TCP-V1-APPROVED` | `studio_rule_detail_heavy_tcp_v1` | 1024x768 | `screenshots/studio_rule_detail_heavy_tcp_v1_1024x768.png` | 374,899 B | **PASS** | Revalidation Required badge rendered; 0/30 reviews shown |
| `SCN-HEAVY-TCP-V1-APPROVED` | `studio_rule_detail_heavy_tcp_v1` | 1280x800 | `screenshots/studio_rule_detail_heavy_tcp_v1_1280x800.png` | 518,029 B | **PASS** | Hero card clean; zero horizontal overflow |
| `SCN-HEAVY-TCP-V1-APPROVED` | `studio_rule_detail_heavy_tcp_v1` | 1440x900 | `screenshots/studio_rule_detail_heavy_tcp_v1_1440x900.png` | 628,232 B | **PASS** | 3 primary tabs aligned; 6 checklist stages visible |
| `SCN-HEAVY-TCP-V1-APPROVED` | `studio_rule_detail_heavy_tcp_v1` | 1920x1080 | `screenshots/studio_rule_detail_heavy_tcp_v1_1920x1080.png` | 939,334 B | **PASS** | Full HD layout crisp; zero layout shift |
| `SCN-HEAVY-TCP-V3-CANDIDATE` | `studio_rule_detail_heavy_tcp_v3` | 1024x768 | `screenshots/studio_rule_detail_heavy_tcp_v3_1024x768.png` | 365,519 B | **PASS** | "Approval Blocked" button disabled; "View Requirements" present |
| `SCN-HEAVY-TCP-V3-CANDIDATE` | `studio_rule_detail_heavy_tcp_v3` | 1280x800 | `screenshots/studio_rule_detail_heavy_tcp_v3_1280x800.png` | 513,784 B | **PASS** | Candidate version 3 draft correctly bound |
| `SCN-HEAVY-TCP-V3-CANDIDATE` | `studio_rule_detail_heavy_tcp_v3` | 1440x900 | `screenshots/studio_rule_detail_heavy_tcp_v3_1440x900.png` | 630,501 B | **PASS** | Stage 6 action button displays disabled "Approval Blocked" |
| `SCN-HEAVY-TCP-V3-CANDIDATE` | `studio_rule_detail_heavy_tcp_v3` | 1920x1080 | `screenshots/studio_rule_detail_heavy_tcp_v3_1920x1080.png` | 948,020 B | **PASS** | Checklist explains incomplete gates & review requirements |
| `SCN-VIEWER-LOCKOUT` | `studio_rule_detail_viewer_lockout` | 1024x768 | `screenshots/studio_rule_detail_viewer_lockout_1024x768.png` | 374,830 B | **PASS** | Viewer cannot mutate; "Synthesize Draft" disabled |
| `SCN-VIEWER-LOCKOUT` | `studio_rule_detail_viewer_lockout` | 1280x800 | `screenshots/studio_rule_detail_viewer_lockout_1280x800.png` | 517,750 B | **PASS** | Descriptive RBAC tooltip visible on hover |
| `SCN-VIEWER-LOCKOUT` | `studio_rule_detail_viewer_lockout` | 1440x900 | `screenshots/studio_rule_detail_viewer_lockout_1440x900.png` | 627,678 B | **PASS** | Action toolbar buttons hard-disabled for Viewer |
| `SCN-VIEWER-LOCKOUT` | `studio_rule_detail_viewer_lockout` | 1920x1080 | `screenshots/studio_rule_detail_viewer_lockout_1920x1080.png` | 938,474 B | **PASS** | Full HD layout adheres strictly to read-only constraints |
| `SCN-BLIND-REVIEW-ACTIVE` | `workbench_blind_review_active` | 1024x768 | `screenshots/workbench_blind_review_active_1024x768.png` | 326,150 B | **PASS** | [Hidden - Blind Review] rendered in table verdict column |
| `SCN-BLIND-REVIEW-ACTIVE` | `workbench_blind_review_active` | 1280x800 | `screenshots/workbench_blind_review_active_1280x800.png` | 371,175 B | **PASS** | Sticky action columns aligned; zero table overflow |
| `SCN-BLIND-REVIEW-ACTIVE` | `workbench_blind_review_active` | 1440x900 | `screenshots/workbench_blind_review_active_1440x900.png` | 419,912 B | **PASS** | Double-blind protocol active; zero ground-truth leak |
| `SCN-BLIND-REVIEW-ACTIVE` | `workbench_blind_review_active` | 1920x1080 | `screenshots/workbench_blind_review_active_1920x1080.png` | 524,759 B | **PASS** | Incident triage table fits comfortably within viewport |
| `SCN-CATALOG-INTEGRITY` | `catalog_readiness_integrity` | 1024x768 | `screenshots/catalog_readiness_integrity_1024x768.png` | 271,796 B | **PASS** | 20 canonical rules rendered; zero false ready badges |
| `SCN-CATALOG-INTEGRITY` | `catalog_readiness_integrity` | 1280x800 | `screenshots/catalog_readiness_integrity_1280x800.png` | 322,180 B | **PASS** | Quality scores, versions, and readiness indicators clean |
| `SCN-CATALOG-INTEGRITY` | `catalog_readiness_integrity` | 1440x900 | `screenshots/catalog_readiness_integrity_1440x900.png` | 380,536 B | **PASS** | Compact density spacing; search and filters active |
| `SCN-CATALOG-INTEGRITY` | `catalog_readiness_integrity` | 1920x1080 | `screenshots/catalog_readiness_integrity_1920x1080.png` | 504,827 B | **PASS** | Full HD view of rule catalog with complete readiness status |

---

### 3. Assertion Validation Results
All 5 automated browser test scenarios passed in `scripts/run_v1_2_1_validation.mjs`:
- `passedScenarios: 5 / 5 (100%)`
- `totalScreenshots: 20`
- `status: "PASS"`
