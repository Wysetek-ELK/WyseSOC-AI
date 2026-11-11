# AIS 2.0 Rule Identity & Canonical Mapping Audit

**Target Canonical Rule:** `PH_RULE_HEAVY_TCP_HOST_SCAN` (`9839fa49-40ac-4676-abcc-4c5581ae9e09`)  
**Distinct Sibling Rule Observed:** `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` (`37a7542f-c029-4676-9aba-4de51c9e90c6` in local dev SQLite)

---

## 1. Identifier Model & Canonical Separation

Every SIEM rule carries three primary identifiers across `rules` and `incidents`:
- `Rule.id`: Internal `String(36)` UUID primary key (e.g., `9839fa49-40ac-4676-abcc-4c5581ae9e09`).
- `Rule.rule_id`: Unique FortiSIEM logical rule identifier (e.g., `PH_RULE_HEAVY_TCP_HOST_SCAN`).
- `Rule.event_type`: SIEM event type string (e.g., `PH_RULE_HEAVY_TCP_HOST_SCAN`, though may differ from `rule_id` as seen in local dev DB `PH_RULE_DEBUG_FUNNEL` with `event_type="ProcessExecution"`).
- `Incident.rule_id`: Nullable FK to `rules.id`.
- `Incident.event_type`: Raw alert `eventType` ingested from FortiSIEM.

### Mandatory Rule Isolation
`PH_RULE_HEAVY_TCP_HOST_SCAN` and `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` are **separate canonical rules** with distinct detection conditions:
- `PH_RULE_HEAVY_TCP_HOST_SCAN`: Heavy TCP host scanning (broad/variable-port or host-sweep semantics).
- `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` *(confirmed in `backend/ai_verdict.db`)*: `Expression: COUNT(DISTINCT destIpAddr) >= 50 AND destPort IS NOT NULL`, `Window: 300s`, `GroupBy: srcIpAddr,destPort`.

These rules **must not** be merged merely because their human-readable names share `"Heavy TCP Host Scan"`.

---

## 2. Confirmed Mapping Inconsistencies & Lookup Defects

**Finding IDs:** `AIS-F07` & `AIS-F08` | **Severity:** MEDIUM | **Confidence:** **CONFIRMED (Code-level)**

### A. Cross-Endpoint Mapping Mismatch Matrix

| Component & Source Location | Lookup Predicate Used | Defect / Divergence |
| :--- | :--- | :--- |
| **`IncidentService.list_incidents`** (`incident_service.py:94-111`) | `rule_id` param: `or_(Incident.rule_id == rule_id, Incident.event_type == rule_id)`. `search`: `ILIKE` across `incident_id`, `title`, `description`, `source_ip`, `reporting_device`, `event_type`. | Workbench free-text search `"Heavy TCP Host Scan"` aggregates incidents across multiple distinct TCP scan rules (`33` hits). |
| **`PolicySimulationService.run_dry_run_intelligence_evaluation`** (`policy_simulation_service.py:213-216, 295`) | Resolves `Rule` via `or_(Rule.id == rule_id, Rule.rule_id == rule_id)` -> `rule_ids = {rule_id, matched_rule.id, matched_rule.rule_id}`, then queries `Incident.rule_id.in_(rule_ids)`. | **No `Incident.event_type` fallback!** Incidents where `Incident.rule_id IS NULL` (not yet auto-mapped) or mismatched FK UUID are invisible to AIS G8. |
| **`rules.list_rules`** (`rules.py:30-38`) vs **`rules.get_rule_detail`** (`rules.py:211-214`) | `list_rules`: `outerjoin` on `Rule.id == Incident.rule_id`. `get_rule_detail`: `or_(Incident.rule_id == rule.id, Incident.event_type == rule.event_type)`. | Incident counts displayed in Rules table can diverge from Rule Detail page whenever `Incident.rule_id` is `NULL` or stale. |
| **`AgentPolicyEngine`** (`prompt_studio_service.py`) | `get_or_create_rule_prompt` (`:44`) checks `or_(Rule.id == rule_id, Rule.rule_id == rule_id)`. However `generate_template_draft` (`:99`), `create_draft_version` (`:189`), `approve_version` (`:256`), and `rollback_version` (`:402`) query `Rule.id == rule_id` ONLY! | Calling `AgentPolicyEngine` methods directly with logical `rule_id` (`"PH_RULE_HEAVY_TCP_HOST_SCAN"`) fails `Rule` lookup (`RuleMaturityService.get_or_create_evaluation` at `maturity_service.py:28` has the same `Rule.id == rule_id` constraint). |
| **`HistoricalEligibilityService`** (`historical_eligibility_service.py:70-83, 185`) | Builds maps for `Rule.id`, `Rule.rule_id`, and `Rule.event_type`, accurately coalescing rule buckets. | Correctly links `event_type`-matched incidents even without FK linkage, unlike `PolicySimulationService`. |
| **`VerdictTriageAgent`** (`ai_verdict_service.py:211-237`) | Auto-maps `Incident.rule_id` using `or_(Rule.event_type == incident.event_type, Rule.rule_id == incident.event_type)` only when triaging an incident, then backfills siblings. | Creates a temporal inconsistency: historical rules never triaged live may retain unlinked (`rule_id=NULL`) incidents omitted from G8 simulation. |

### B. Typo in `DetectionArchetypeRegistry` (`detection_archetype_registry.py:691`)
Line 691 checks `"PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT" in combo` (missing `_ON_`), whereas the canonical FortiSIEM name in DB is `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT`.  
- **Current Impact:** Low, because line 692 (`"HOST_SCAN" in combo`) and line 693 (`"HOST SCAN" in combo`) still classify both `PH_RULE_HEAVY_TCP_HOST_SCAN` and `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` as `ArchetypeId.NETWORK_SCAN` (`confidence=0.95`). Should still be corrected for exact match hygiene.

### C. Parser & SIEM Discovery Gaps
1. **`DetectionContextEngine.parse_rule_text` (`rule_parser.py:46, 64, 112-115`):** Recognizes `"pattern conditions"` in `headers_known` (`L46`) and captures it into `sections["pattern conditions"]`, yet `L112-115` only checks `"pattern_logic"` and `"pattern"` when assigning `data["pattern_logic"]`, silently dropping `"Pattern Conditions"` blocks.
2. **`FortiSIEMService.sync_all_rules_from_siem` (`fortisiem_service.py:130-239`):** Discovers rules strictly from unique `eventType` values present in the last 500 incidents (`AUTO_SYNCED_FROM_INCIDENT`), setting `pattern_logic=""` and `definition_status="INCOMPLETE"`, rather than querying FortiSIEM's rule catalogue.

---

## 3. Local Dev Database Verification vs. Unverified Live Production Counts

### Observed Local Dev DB (`backend/ai_verdict.db`, Read-Only)
- Total rules = **4**:
  - `271b0831-f6f5-4d86-9e0b-d53aee948cf0`: `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (`10` incidents)
  - `b2f1f1e4-117b-4b0e-87ca-65869898630b`: `Prisma_SASE_Suspicious_File_Threat_Detection_` (`10` incidents)
  - `37a7542f-c029-4676-9aba-4de51c9e90c6`: `PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT` (`VERIFIED` XML import, **`0` incidents**)
  - `07bef27c-84ca-4a78-9a04-e61b65cb9277`: `PH_RULE_DEBUG_FUNNEL` (`event_type="ProcessExecution"`, `6` incidents)
- `PH_RULE_HEAVY_TCP_HOST_SCAN` (`9839fa49-40ac-4676-abcc-4c5581ae9e09`) does **not** exist in the local SQLite database.

### Remote Live Production Status (`UNVERIFIED`)
Whether the 33 AI Triage Workbench hits represent 2 `PH_RULE_HEAVY_TCP_HOST_SCAN` + 31 `_ON_FIXED_PORT`, or include additional `PH_RULE_HEAVY_TCP_HOST_SCAN` incidents with `rule_id IS NULL` or an unmerged duplicate `Rule` row, cannot be verified locally and requires running these read-only queries against live PostgreSQL:

```sql
-- Exact canonical rule breakdown across all TCP/Scan rules and orphan event_type rows
SELECT r.id AS rule_uuid,
       r.rule_id AS canonical_rule_id,
       r.name,
       r.event_type,
       COUNT(DISTINCT CASE WHEN i.rule_id = r.id THEN i.id END) AS fk_matched_count,
       COUNT(DISTINCT CASE WHEN i.event_type = r.event_type AND (i.rule_id IS NULL OR i.rule_id <> r.id) THEN i.id END) AS event_type_unlinked_count
FROM rules r
LEFT JOIN incidents i
  ON i.rule_id = r.id OR i.event_type = r.event_type
WHERE r.rule_id ILIKE '%SCAN%' OR r.name ILIKE '%Scan%' OR r.event_type ILIKE '%SCAN%'
GROUP BY r.id, r.rule_id, r.name, r.event_type
ORDER BY fk_matched_count DESC;

-- Detect any orphaned event_types with no matching Rule row or duplicate Rule rows
SELECT i.event_type, i.rule_id, COUNT(*) AS cnt
FROM incidents i
LEFT JOIN rules r ON r.id = i.rule_id
WHERE (i.event_type ILIKE '%TCP%SCAN%' OR i.title ILIKE '%Heavy TCP Host Scan%')
GROUP BY i.event_type, i.rule_id
ORDER BY cnt DESC;
```

