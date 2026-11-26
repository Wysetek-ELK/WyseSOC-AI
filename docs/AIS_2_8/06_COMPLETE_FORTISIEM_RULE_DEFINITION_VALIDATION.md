# 06 — Complete FortiSIEM Rule Definition Validation

## Root Cause Found in AIS 2.7

- `ais27_benchmark_runner.py` L591–598 and `verdict_pipeline.py` L849–855 sent only a 6-key stub (`id`, `rule_id`, `name`, `event_type`, `severity`, `description`) in `rule_spec`, omitting `pattern_logic`, `raw_rule_text`, and `parsed_metadata`. Mode B received `detection_conditions` text while Mode A did not, causing unfair evidence asymmetry.

## Solution (`RuleDefinitionBuilder`)

- Implemented `RuleDefinitionBuilder.build_complete_rule_spec()` in `backend/app/services/evidence_intelligence_service.py`:
  - Preserves `pattern_logic`, `raw_rule_text`, `parsed_metadata`, `data_source`, `detection_tech`, `evaluation_mode`.
  - Parses individual predicate clauses, `group_by`, `window`, `threshold`, and `exclusions`.
  - Deterministically evaluates each clause against canonical/raw telemetry into `MATCHED`, `NOT_MATCHED`, `UNKNOWN`, or `NOT_EVALUABLE`.
- Wired identically into both `verdict_pipeline.py` and `ais27_benchmark_runner.py` (`captured[0][1] == captured[1][1]` verified in `test_ais_2_8_intelligence.py`).
