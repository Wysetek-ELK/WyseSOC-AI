# VERDICTUM AI — VALIDATION V1.2.1
## 07. HEAVY TCP HOST SCAN REGRESSION & AUDIT TRAIL

**Document Version:** 1.0.0  
**Target Rule ID:** `40498741-ee6b-4a71-9101-0d6d3f77154c` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT`)  
**Status:** FULLY RECONCILED & VERIFIED  

---

### 1. Ground Truth Database Inspection

Direct query against `ai_verdict.db` via `AsyncSessionLocal`:

- **Rule Metadata:**
  - ID: `40498741-ee6b-4a71-9101-0d6d3f77154c`
  - Name: `Heavy TCP Host Scan On Fixed Port`
  - SIEM Deployment Status: `ACTIVE`
  - Category: `NETWORK_SCAN`
  - Rule Prompt ID: `ebc01046-a6f5-41dd-b9a1-1a2edaa1b79a`
  - Active Version ID: `8a460ab8-5f06-4a90-b2d4-db958199d644` (Version 1)

- **Version History:**
  1. **Version 1 (`8a460ab8-5f06-4a90-b2d4-db958199d644`):**
     - Version Number: `1`
     - Status: `APPROVED`
     - Quality Status: `REVIEW_REQUIRED`
     - Quality Score: `52.0`
     - Passing Gates: `2/8` (Hard gate failures on G1 definition and G4 test coverage)
     - Verified Analyst Reviews: `0`
     - Wilson Lower Bound: `None`
  2. **Version 2 (`a1e4afa2-f3b3-40cc-add7-40692c50cabc`):**
     - Version Number: `2`
     - Status: `ARCHIVED`
     - Quality Status: `REWORK_REQUIRED`
     - Quality Score: `60.0`
  3. **Version 3 (`ec0cc351-8dd1-4026-9dc3-586387bb324c`):**
     - Version Number: `3`
     - Status: `DRAFT`
     - Quality Status: `GENERATED_DRAFT`
     - Quality Score: `88.0`
     - Passing Gates: `6/8` (G1-G6 passed, G7 statistical validation unreached, G8 simulation pending)
     - Verified Analyst Reviews: `0`

---

### 2. Reconciliation of Prior Inconsistencies

#### Problem in V1.2:
In V1.2 screenshots, Version 1 displayed an `ACTIVE PRODUCTION` badge in the header, while the readiness section reported `BLOCKED` with `4/8` gates. Version 3 displayed an enabled `Approve & Activate` button despite lacking required reviews.

#### Fixed in V1.2.1:
1. **Scenario A (Version 1 - Approved Baseline):**
   - Header badge renders: `APPROVED BASELINE (REVALIDATION REQUIRED)`.
   - Clear banner explains:
     > *"This policy version was formally approved as a baseline, but automated revalidation is required because 6 of 8 quality gates or ground-truth reviews are incomplete."*
   - Active Policy is correctly distinguished from Empirical Production Readiness.
2. **Scenario B & C (Version 3 - Candidate Draft):**
   - Direct link with `version_id=ec0cc351-8dd1-4026-9dc3-586387bb324c` successfully loads Version 3.
   - Header badge renders: `SUPERVISED LEARNING (DRAFT CANDIDATE)`.
   - Top action toolbar button renders: `[Approval Blocked]` (disabled).
   - Adjacent link renders: `View Requirements`, pointing to `#guided-readiness-checklist`.
   - Stage 6 action button renders: `[Approval Blocked]` (disabled).
   - Backend API rejects any approval attempt with HTTP 400.

---

### 3. Screenshot Evidence & Viewport Verification
Screenshots captured and verified for Heavy TCP Host Scan:
- `studio_rule_detail_heavy_tcp_v1_1024x768.png` (374,899 bytes)
- `studio_rule_detail_heavy_tcp_v1_1280x800.png` (518,029 bytes)
- `studio_rule_detail_heavy_tcp_v1_1440x900.png` (628,232 bytes)
- `studio_rule_detail_heavy_tcp_v1_1920x1080.png` (939,334 bytes)
- `studio_rule_detail_heavy_tcp_v3_1024x768.png` (365,519 bytes)
- `studio_rule_detail_heavy_tcp_v3_1280x800.png` (513,784 bytes)
- `studio_rule_detail_heavy_tcp_v3_1440x900.png` (630,501 bytes)
- `studio_rule_detail_heavy_tcp_v3_1920x1080.png` (948,020 bytes)
