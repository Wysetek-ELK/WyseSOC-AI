# Phase 9 — Verdict Assurance & Human Authority Governance

---

## 1. Human Review Queue Assurance Surface

`backend/app/services/investigation_service.py` (`build_ai_assurance()`) and `frontend/src/app/human-review-queue/page.tsx` extend the existing Investigation drawer with **AI Verdict Assurance & Provenance** (`AIAssuranceSummary`), exposing:

- Incident & rule metadata (`rule_id`, `rule_name`, `policy_version_number`, `policy_digest`)
- Execution & runtime provenance (`pilot_mode`, `model_identifier`, `is_simulated` badge `SIMULATED` vs `LIVE`, `evaluated_at`)
- Dual verdict state (`proposed_verdict` vs `validated_verdict`, `validation_status`, `abstention_reason`)
- Evidence breakdown (`supporting_evidence`, `contradictory_evidence`, `missing_evidence`)
- Trustworthiness & calibration status (normalized `trust_score` capped `<= 6/10` if uncalibrated, preserved `historical_trust_score` when capped, `calibration_status`)
- Historical evaluation support (`historical_sample_count`, `historical_validation_status`)
- Human & supervisor governance (`analyst_feedback_action`, `supervisor_verified` flag)

The investigation table (`InvestigationListItem`) also surfaces `ai_validated_verdict`, `ai_trust_score`, and `pilot_mode` badges cleanly without altering historical SIEM ground truth isolation (`HistoricalGroundTruth`).

---

## 2. Non-Destructive Overrides & Supervisor Gate

1. **Separated Decision Storage**: Analysts submit `action_type` (`ACCEPTED`, `OVERRIDDEN`, `DISPUTED`, or `REQUESTED_EVIDENCE`) alongside their authoritative verdict via `POST /api/investigations/{id}/verdict` or `POST /api/pilot/evaluations/{id}/feedback`.
2. **Immutability of AI Output**: Analyst submission NEVER overwrites `proposed_verdict`, `validated_verdict`, `validation_status`, `trust_score`, or `evidence_snapshot_hash` on `PilotEvaluationRecord`.
3. **Self-Verification Prohibition**:
   - Feedback submission resets `supervisor_verified = False`.
   - `POST /api/pilot/evaluations/{id}/supervisor-verify` requires `Administrator` role (`require_admin`) AND explicitly rejects `supervisor_username == rec.analyst_user` with HTTP `400` (`SELF_VERIFICATION_PROHIBITED`).
   - Verified status only approves promotion after independent human review, preventing self-confirming AI/analyst learning loops.
4. **Role Protection**: UI verdict submission controls are disabled for `Read-Only Viewer` with explicit visual lock feedback, backed by API `require_analyst` enforcement.

