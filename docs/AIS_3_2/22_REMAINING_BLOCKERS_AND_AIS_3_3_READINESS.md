# AIS 3.2 — 22: Remaining Blockers & AIS 3.3 Readiness

## Remaining Blockers Before Closing AIS 3.2 Empirical Gates
1. **Server 1 Admin Authentication / Browser `DevToolsActivePort`:** Authenticate to `http://172.26.41.240`, trigger `POST /api/ais32/cohorts/development/ensure`, run real GPU technical pilot + paired Mode A vs Mode B runs on `AIS_3_2_DEVELOPMENT`, and capture authenticated GUI screenshots.
2. **Contract & Semantic Mapping Sign-Off:** Review and approve `PROVISIONAL` rule contracts and `DEFAULT_SEMANTIC_MAPPINGS`.
3. **Organizational Context Population:** Populate tenant-approved scanners, maintenance windows, and asset inventory entries in `ais32_organizational_contexts`.
4. **Pre-existing Debt:** 2 legacy pytest mismatches (`test_database_migrations.py` `'008_soc_pilot'`, `test_phase1_security_controls.py` `POLICY_NOT_APPROVED`) and pre-existing frontend ESLint errors.

## AIS 3.3 Fresh Holdout Isolation Plan (`ISOLATION_PLAN_PREPARED_NOT_EVALUATED`)
- **Recommended Minimum Sample Size:** **N >= 240** untouched incidents including **>= 60 TPs** across all 11 archetypes with dual independent blind human review (**GT-3**).
- **Rationale:** N=100 at ~18% TP prevalence yields only 18 TPs (95% Wilson CI width >20% on recall). To bound TP recall >=95% and overall accuracy >=90% within +/-4.0% with dual-reviewer GT-3 certification, >= 240 untouched incidents (including >= 60 TPs across all 11 archetypes) is required.
- **Guardrails:** Exclude `AIS_2_6E_FROZEN_20`, `AIS_3_0_INDEPENDENT_HOLDOUT_100`, `AIS_3_2_DEVELOPMENT`, and `LearningRecord`-exposed IDs/hashes; freeze policy & validator versions prior to AIS 3.3 execution. Do NOT proceed to AIS 4.0 until AIS 3.3 independent acceptance passes.
