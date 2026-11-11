# Agent Intelligence Studio 2.2 — Canonical Rule Identification, G1 & Evidence Contract Validation

---

## 1. Exact Rule Identification & Workbench Reconciliation (`AIS-F07`)

### Problem Fixed
Free-text search in AI Triage Workbench matched substrings across distinct SIEM rules (e.g., `"Heavy TCP Host Scan"` combined both `PH_RULE_HEAVY_TCP_HOST_SCAN` and `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT`), rows only displayed `rule_name` and `event_type` (hiding canonical UUID `Rule.id` and logical `Rule.rule_id`), and `IncidentService.list_incidents` filtered `rule_id` without AIS's sibling-isolation rules — causing Workbench counts to diverge from AIS simulation counts.

### Implemented Solution
- **API & Schema Alignment ([schemas/incident.py](../../backend/app/schemas/incident.py), [api/incidents.py](../../backend/app/api/incidents.py)):**
  - `IncidentListItemResponse` and `IncidentDetailResponse` now expose `rule_uuid`, `logical_rule_id`, `rule_name`, and `event_type`.
  - `GET /api/incidents` supports an explicit `exact_rule_id` parameter (keeping `rule_id` as an alias for backward compatibility).
  - `IncidentListResponse` computes cohort-wide rule distribution (`distinct_rule_count`, `combines_multiple_rules`, `matched_rules`, `exact_rule_id`, `exact_logical_rule_id`, `exact_rule_name`) across the full filtered cohort.
- **1:1 Backend Filtering Parity ([incident_service.py](../../backend/app/services/incident_service.py)):**
  - `IncidentService.list_incidents_with_rule_summary` calls AIS's exact canonical resolvers: `resolve_canonical_rule`, `build_rule_incident_context`, `build_rule_incident_sql_filter`, and row-level `verify_incident_matches_rule`.
  - Verified in `test_ais_2_2_remediation.py::test_3`:
    - Free-text `search="Heavy TCP Host Scan"` across `PH_RULE_HEAVY_TCP_HOST_SCAN` (2 rows) + `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` (4 rows) returns `total=6`, `combines_multiple_rules=True`, `distinct_rule_count=2`, and itemized rule counts `2` and `4`.
    - Passing `exact_rule_id=<PH_RULE_HEAVY_TCP_HOST_SCAN UUID>` returns `total=2`, `combines_multiple_rules=False`, matching `PolicySimulationService` `metrics["funnel"]["retrieved"] == 2` **1-for-1**.
- **Workbench UI ([ai-triage-workbench/page.tsx](../../frontend/src/app/ai-triage-workbench/page.tsx)):**
  - Dedicated **Exact Rule Filter** dropdown independent of free-text search.
  - Table `Rule / Event Type` cell shows `rule_name`, `logical_rule_id`, shortened `rule_uuid` (full UUID on hover), and `event_type`.
  - Multi-rule warning banner (`combines_multiple_rules === true`) displays exact matched rule pills with counts and one-click rule isolation.

---

## 2. G1 Integrity, Runtime Counters & FortiSIEM Evidence Normalization

### Fixes Verified
1. **Runtime Incident Counters Rejected as Rule Thresholds:**
   - [`FortiSIEMService._parse_json_rule`](../../backend/app/services/fortisiem_service.py) no longer falls back to runtime `incidentDetail` / `incidentDetailJson` as `pattern_logic`; when authoritative `pattern`/`patternLogic`/`expression` is absent, `pattern_logic` stays `""`, raw metrics go only to `metadata["source_incident_metrics"]`, and `metadata["definition_status"] = "INCOMPLETE"`.
   - [`FortiSIEMService.import_authoritative_rule_definition`](../../backend/app/services/fortisiem_service.py) checks whether parsed correlation conditions are actually present before assigning `definition_status = "VERIFIED"` (empty or runtime-counter-only definitions stay `INCOMPLETE`), and refreshes persisted `RuleIntelligenceSnapshot`.
   - [`RuleIntelligenceAnalyzer.analyze_rule`](../../backend/app/services/rule_intelligence_analyzer.py) rejects non-JSON runtime counter patterns (`incidentCount=...`, `incidentDetail=...`) and `_extract_threshold_from_conditions` skips runtime counter fields (`incidentcount`, `incidentdetail`, `incidentid`, `eventcount`, `totalcount`), guaranteeing unverified rules never gain invented thresholds or `VERIFIED` status.
2. **Timestamp & FortiSIEM Field Fixture Normalization:**
   - [`EvidenceNormalizationService.normalize_incident_evidence`](../../backend/app/services/evidence_normalization_service.py) resolves top-level `event.timestamp` from `first_seen_epoch or created_at_epoch or last_seen_epoch` (converting both 10-digit seconds `< 1e11` and 13-digit milliseconds `>= 1e11`), eliminating false `PREFLIGHT_GUARD` abstentions on FortiSIEM incidents carrying `first_seen_epoch` without `created_at_epoch`.
   - Confirmed via `test_ais_2_2_remediation.py::test_4` and `test_6` with representative FortiSIEM fixtures (`Pattern Conditions:`, `COUNT(Matched Events) >= 50`, `"Destination Port": 445`, `"Source IP"`, nested `rawEvents` `"dstPort"`): maps cleanly to `network.destination_port`, `network.source_ip`, `security.event_type`, `event.timestamp`, and `NETWORK_SCAN` `RuleEvidenceContract`.
3. **RuleIntelligenceSnapshot Parity:**
   - `GET /api/prompts/rule/{rule_id}/intelligence` (`_analyze_with_snapshot`), `AgentPolicyEngine.approve_version`, `_compute_policy_quality_readonly`, `PolicySimulationService`, and `verdict_pipeline` all consume [`get_rule_semantics_and_contract`](../../backend/app/services/policy_governance.py).

---

## 3. Remotely Unverified Production Validation (`NOT VERIFIED`)

- Live FortiSIEM Supervisor XML/REST responses and production `PH_RULE_HEAVY_TCP_HOST_SCAN` correlation definitions in Server 1 PostgreSQL remain **`NOT VERIFIED`** locally and must be inspected during the subsequent remote integration validation phase.
