# Verdictum AI — Validation V1.2.2b
## 06: Headless Browser Validation Results

### 1. Test Harness Architecture
The automated browser validation harness (`scripts/run_v1_2_2b_validation.mjs`) operates via Chrome DevTools Protocol (CDP) connected to a headless Chrome instance (`--headless=new`).

**Key Architectural Guarantees:**
- **Strict Conjunction Assertion:** `scenarioPassed = apiValid && domResult.isValid`.
- **Authentic Network Requests:** Evaluates actual HTTP status codes and response bodies from `127.0.0.1:8000`.
- **Dual Responsive Viewports:** Captures full-fidelity screenshots at both `1440x900` and `1920x1080`.
- **Immutable Commit Provenance:** Every evidence record is linked to exact repository commit SHA.

---

### 2. Validation Matrix (10 Scenarios × 2 Viewports = 20 Screenshots)

| # | Scenario ID | Description | Role / Tenant | Backend Route & Expected Status | Actual Status & API Check | DOM Assertions | Overall Status |
|---|-------------|-------------|---------------|----------------------------------|---------------------------|----------------|----------------|
| 1 | `SCN-V122B-01-HEAVY-TCP-V1` | Heavy TCP Host Scan Rule v1 (Historical baseline) | Administrator / DEFAULT | `GET /api/prompts/rule/40498741-.../readiness?version_id=8a460...` (200) | 200, score: 54.0, gates: 2/8, BLOCKED | Active Policy v1 badge, SIEM Rule ACTIVE, 2/8 Gates | **PASS** |
| 2 | `SCN-V122B-02-HEAVY-TCP-V3` | Heavy TCP Host Scan Rule v3 (Candidate version) | Administrator / DEFAULT | `GET /api/prompts/rule/40498741-.../readiness?version_id=ec0cc...` (200) | 200, score: 77.0, gates: 6/8, BLOCKED | Candidate Policy v3 DRAFT, 6/8 Gates, Lockout active | **PASS** |
| 3 | `SCN-V122B-03-AI-RUNTIME-OFFLINE` | AI Runtime Offline state (Server 2 offline) | Administrator / DEFAULT | `GET /api/prompts/rule/40498741-.../readiness?version_id=8a460...` (200) | 200, runtime_availability: verified | Decoupled AI Execution indicator rendered | **PASS** |
| 4 | `SCN-V122B-04-BLIND-ON` | Blind Review ON (Client preference ON) | SOC Analyst (Analyst A) / TENANT_ALPHA | `GET /api/incidents?page=1&page_size=10&blind_review=true` (200) | 200, items array returned | Masked verdicts, Blind Review active banner | **PASS** |
| 5 | `SCN-V122B-05-BLIND-OFF` | Blind Review Client OFF (Server Enforced) | SOC Analyst (Analyst B) / TENANT_ALPHA | `GET /api/incidents?page=1&page_size=10&blind_review=false` (200) | 200, items array returned | Server overrides client toggle, retaining [Hidden - Blind Review] | **PASS** |
| 6 | `SCN-V122B-06-ANALYST-A-SUBMITTED` | Permitted Comparison Revealed for Submitting Reviewer | SOC Analyst (Analyst A) / TENANT_ALPHA | `GET /api/incidents/132438483?blind_review=false` (200) | 200, revealed verdict returned | AI: TP / True Positive comparison badge revealed | **PASS** |
| 7 | `SCN-V122B-07-ANALYST-B-UNSUBMITTED` | Reviewer A/B Isolation (Unreviewed Analyst) | SOC Analyst (Analyst B) / TENANT_ALPHA | `GET /api/incidents/132438483?blind_review=false` (200) | 200, verdict masked | Masked [Hidden - Blind Review] retained | **PASS** |
| 8 | `SCN-V122B-08-VIEWER-RESTRICTED` | Read-Only Viewer Restricted State | Read-Only Viewer / TENANT_ALPHA | `GET /api/incidents?page=1&page_size=5` (200) | 200, items array returned | Masked verdicts and action lockout enforced | **PASS** |
| 9 | `SCN-V122B-09-CROSS-TENANT-DENIAL` | Cross-Tenant Access Protection | SOC Analyst (Analyst A) / TENANT_ALPHA | `GET /api/incidents/INC-TENANT-BETA-001` (403) | 403 Forbidden with "Access denied" | Zero incident rows exposed, "Showing 0 of 0 incidents" | **PASS** |
| 10 | `SCN-V122B-10-ALTERNATE-ENDPOINT-PROTECTION` | Alternate Endpoint & Export Protection | SOC Analyst (Analyst B) / TENANT_ALPHA | `GET /api/prompts/actual-prompt/incident/132438483/export?format=json` (200) | 200, is_redacted: true, raw_model_response: [Hidden...] | Unreviewed determinations remain masked in Workbench | **PASS** |

---

### 3. Screenshot Inventory
All 20 screenshots are preserved in `docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2b/screenshots/`:
1. `v1_2_2b_scn01_heavy_tcp_v1_1440x900.png`
2. `v1_2_2b_scn01_heavy_tcp_v1_1920x1080.png`
3. `v1_2_2b_scn02_heavy_tcp_v3_1440x900.png`
4. `v1_2_2b_scn02_heavy_tcp_v3_1920x1080.png`
5. `v1_2_2b_scn03_ai_runtime_offline_1440x900.png`
6. `v1_2_2b_scn03_ai_runtime_offline_1920x1080.png`
7. `v1_2_2b_scn04_blind_on_1440x900.png`
8. `v1_2_2b_scn04_blind_on_1920x1080.png`
9. `v1_2_2b_scn05_blind_off_1440x900.png`
10. `v1_2_2b_scn05_blind_off_1920x1080.png`
11. `v1_2_2b_scn06_analyst_a_submitted_1440x900.png`
12. `v1_2_2b_scn06_analyst_a_submitted_1920x1080.png`
13. `v1_2_2b_scn07_analyst_b_unsubmitted_1440x900.png`
14. `v1_2_2b_scn07_analyst_b_unsubmitted_1920x1080.png`
15. `v1_2_2b_scn08_viewer_restricted_1440x900.png`
16. `v1_2_2b_scn08_viewer_restricted_1920x1080.png`
17. `v1_2_2b_scn09_cross_tenant_denial_1440x900.png`
18. `v1_2_2b_scn09_cross_tenant_denial_1920x1080.png`
19. `v1_2_2b_scn10_alternate_endpoint_protection_1440x900.png`
20. `v1_2_2b_scn10_alternate_endpoint_protection_1920x1080.png`

---

### 4. Machine-Readable Evidence Record
The comprehensive results are serialized in `docs/UI_COMPACT_REDESIGN_V1/VALIDATION_V1_2_2b/VALIDATION_EVIDENCE.json`:
- Schema Version: `1.2.2b`
- Total Scenarios: 10
- Passed: 10 (100%)
- Failed: 0
- Exact Commit SHA: `be3670d883d650f5f761cf7dbe193d8f24532033`
