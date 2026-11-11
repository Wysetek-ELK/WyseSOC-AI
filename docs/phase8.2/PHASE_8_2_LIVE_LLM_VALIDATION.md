# Phase 8.2 — Stage E Live Server 2 LLM & Controlled HTTP Wire Validation

**Evidence Sources:**
- `docs/phase8.2/evidence/llm/stage_e_live_llm_probe.json`
- `backend/tests/test_phase8_2_validation.py` (`test_p8_2_def_006_health_redaction_trust_parity_and_recovery`, `test_stage_e_controlled_wire_scenarios`)

## 1. Live Server 2 Endpoint Status (`BLOCKED`)

- Configured endpoint (`LOCAL_LLM_BASE_URL`): `http://192.0.2.50:8000/v1` (RFC-5737 documentation/placeholder subnet; model `Qwen/Qwen2.5-7B-Instruct-AWQ`).
- Live TCP socket probe: `reachable: false`, error `TimeoutError`.
- Live inference criterion `LLM-01-C2` and live GPU telemetry `MON-02-C2` remain **`NOT_TESTED`** / **`BLOCKED`**. No simulated or loopback HTTP test is counted as real Server 2 hardware proof.

## 2. Runtime Fixes Applied to `VerdictTriageAgent` & `EvidenceNormalizationService`

1. **Dynamic Endpoint Probe Cache Invalidation (`VerdictTriageAgent.is_local_llm_available`):** Tracked `_last_probed_base_url` alongside `_last_probe_time` so switching `LOCAL_LLM_BASE_URL` cleanly forces an immediate re-probe instead of returning a stale 8-second cached `False`.
2. **Canonical `event.timestamp` Emission (`EvidenceNormalizationService`):** Added top-level `created_at_epoch`, per-event `event_receive_time`, and `FIELD_MAPPINGS` keys (`timestamp`, `eventtime`, `event_time`, `event_receive_time`, `eventreceivetime`, `event receive time`) so normalized incidents populate canonical `event.timestamp` records required by archetype contracts (`P8.2-DEF-007`).

## 3. Controlled HTTP Wire Matrix (`OpenAICompatibleProvider` -> `VerdictTriageAgent` -> `IndependentVerdictValidator`)

All scenarios executed against real `ThreadingHTTPServer` HTTP endpoints with `LOCAL_LLM_ALLOW_MOCK_FALLBACK=False`:

| Scenario | Model Proposal | Authoritative Outcome | Validation Status / Codes | Trust Score |
| :--- | :--- | :--- | :--- | :--- |
| 1. Outbound Unreachable Fail-Closed | None (TCP refused) | `LocalLLMUnavailableError` raised | Fail-closed (no silent mock fallback) | N/A |
| 2. Recovery After Server Reconnect | `TRUE_POSITIVE` (grounded) | `TRUE_POSITIVE` (`ACCEPTED_DECISIVE_VERDICT`) | `VALIDATED`, `is_simulated=False` | Uncalibrated cap |
| 3. Malicious TP (`INC-P82-WIRE-TP`) | `TRUE_POSITIVE` (grounded) | `TRUE_POSITIVE` (`ACCEPTED_DECISIVE_VERDICT`) | `VALIDATED` | `6/10` (uncalibrated cap) |
| 4. Authorized FP (`INC-P82-WIRE-FP`) | `FALSE_POSITIVE` (`CHG-4410`) | `FALSE_POSITIVE` (`ACCEPTED_DECISIVE_VERDICT`) | `VALIDATED` | `<= 6/10` |
| 5. UltraViewer Containment Contradiction | `FALSE_POSITIVE` + contradiction | `REQUIRES_ATTENTION` | `REJECTED` (`trust_score <= 3`) | `<= 3/10` |
| 6. Missing Critical Telemetry | Partial incident | `REQUIRES_ATTENTION` | `INSUFFICIENT_EVIDENCE` | Capped |
| 7. Unsupported / Fabricated Claim (`EV-NONEXISTENT-99`) | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `REJECTED` (`EVIDENCE_REFERENCE_NOT_FOUND`) | `<= 3/10` |
| 8. Blanket RFC-1918 Negative Assumption FP | `FALSE_POSITIVE` (RFC-1918 only) | `REQUIRES_ATTENTION` | Rejected (`FP_CRITERIA_UNSATISFIED`) | Capped |
| 9. Malformed JSON Output (`<<<MALFORMED_NOT_JSON>>>`) | Unparseable | `REQUIRES_ATTENTION` (`SAFE_ABSTENTION_AFTER_INVALID_OUTPUT`) | `INVALID_MODEL_OUTPUT` | `<= 2/10` |
| 10. Dual-Worker Concurrent Contention | `TRUE_POSITIVE` (2 async workers) | `ACCEPTED_DECISIVE_VERDICT`, `dual_post_calls == 1`, `1` trust row | Idempotent lock handoff | Same `replay_signature` |

