# Phase 9 — Security & Governance Validation

**Scan Evidence:** `docs/phase9/evidence/security/phase9_security_scan.json`

---

## 1. Security Controls Verified in Code & Automated Tests

1. **SOC Pilot Hard Safety Boundaries (`backend/app/schemas/pilot.py`)**:
   - Requests attempting `allow_external_writeback=True` or `allow_auto_incident_closure=True` are rejected at schema validation (`422 Unprocessable Content`).
   - `PilotService` hardcodes both flags to `False` in DB persistence and config snapshots.
2. **Fail-Closed Live Inference Guarantee**:
   - `source_type="LIVE"` forces `allow_simulated_fallback=False` in both `PilotService.evaluate_incident_for_pilot()` and `VerdictTriageAgent._evaluate_incident_locked()`.
   - When Server 2 is unreachable, `LIVE` pilot tasks fail cleanly (`PROVIDER_UNAVAILABLE`) and trigger circuit auto-pause if configured, instead of falling back to simulated heuristics.
3. **3-Role RBAC & Self-Verification Prevention**:
   - Tested via both API pytest (`test_pilot_default_disabled_safety_blocks_and_rbac`, `test_analyst_assisted_assurance_override_and_supervisor_gate`) and Playwright (`test_phase9_ui_e2e.py`):
     - `Read-Only Viewer` receives `403` on batch triggers, feedback, and all pilot config/lifecycle mutations, with matching disabled buttons in the UI and **0 console errors**.
     - `SOC Analyst` receives `403` on `/pilot/config` (PUT), `/activate`, `/pause`, `/disable`, `/rollback`, and `/supervisor-verify`.
     - Independent supervisor verification rejects `supervisor_username == rec.analyst_user` (`400 SELF_VERIFICATION_PROHIBITED`).
4. **Tamper-Evident Audit Logging**:
   - All pilot lifecycle transitions, analyst feedback actions, and supervisor verifications emit HMAC-signed `AuditLog` entries via `AuditService.log()`.

---

## 2. Static Secret, IP, AST CWE & XSS Checks

Automated checks executed across all Phase 9 backend, frontend, deployment, and benchmark files (`docs/phase9/evidence/security/phase9_security_scan.json`):

| Check Category | Target Scope | Result |
|---|---|---|
| Hardcoded Secret Regex Scan | All 17 Phase 9 code, script & deployment files | **PASSED** (`0` matches) |
| Real RFC1918 / Private IP Scan | All Phase 9 & `deployment/` files (non-example IPs) | **PASSED** (`0` matches in Phase 9 / `deployment/` files; removed `10.x.x.4` & `10.x.x.5`). *(Note: 2 pre-existing baseline literals remain untouched outside Phase 9 scope: loopback check in `independent_verdict_validator.py:102` and UI placeholder in `agent-memory/page.tsx:235`.)* |
| Python AST Dangerous Call Audit (`eval`/`exec`/`shell=True`) | `pilot.py`, `pilot_service.py`, `historical_eligibility_service.py`, `008_soc_pilot.py`, `schemas/pilot.py` | **PASSED** (`0` dangerous calls) |
| Frontend Unsafe HTML/Eval Audit (`dangerouslySetInnerHTML`/`eval`) | `PilotControlAndDashboard.tsx`, `HistoricalEligibilityPanel.tsx` | **PASSED** (`0` occurrences) |
| Full Repo `gitleaks detect --no-git` Cross-Check | Whole workspace (`75.44 MB` scanned) | 19 warnings strictly in gitignored Next.js `.next/` build artifacts, gate ID strings (`G3_...`–`G8_...`), empty password template line, test fixture `"short-key-12345"`, and legacy Phase 1 docs; **0 Phase 9 findings**. |

