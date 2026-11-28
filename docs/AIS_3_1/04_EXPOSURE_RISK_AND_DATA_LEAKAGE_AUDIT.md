# AIS 3.1 — Workstream 4: Exposure Risk (`100/100`) & Data Leakage Audit

**Cohort:** `AIS_3_0_INDEPENDENT_HOLDOUT_100`  
**Machine-Readable Evidence:** `docs/AIS_3_1/EXPOSURE_RISK_MANIFEST.json`

---

## 1. Root Cause of the UI's `Exposure Risk: 100` Counter

Direct inspection of `GroundTruthCertificationService.ensure_ais_3_0_holdout_cohort` (`backend/app/services/ground_truth_certification_service.py`) and live PostgreSQL records on Server 1 proves why all 100 items displayed `Exposure Risk`:

```python
exposure_flag = bool(inc.ground_truth is not None or inc.ai_verdict is not None)
```

In PostgreSQL, **85 of 100** incidents had a `HistoricalGroundTruth` ORM row whose `resolution` field was **empty string `""`** (`exists=False`, `is_ml_generated=False`), while **15** had non-empty historical SIEM resolution metadata (`14` `True Positive`, `1` `False Positive`), and **61** had an operational `ai_verdict` object (`REQUIRES_ATTENTION`). Because the legacy boolean checked `inc.ground_truth is not None` instead of actual exposure or leakage channels, it over-flagged all 100 incidents as exposed regardless of masking or RAG/Learning isolation.

---

## 2. Multi-Channel Leakage & Exposure Venn Audit

| Leakage / Exposure Vector Checked | Audited Population | Confirmed Count | Evidence & Verification Method |
|---|---|---:|---|
| **`LearningRecord` / RAG Store** | Platform total `88` records (`83` verified across 3 AIS 2.x rule UUIDs) | **0 / 100** | Queried all `LearningRecord` rows on Server 1 via `/api/learning/records` |
| **`ActualLLMPromptCapture`** | Operational / simulation prompt captures | **0 / 100** | Checked per-incident prompt capture counts on Server 1 |
| **`AIS_2_6E_FROZEN_20` Overlap** | Development / regression cohort | **0 / 100** | Cross-cohort incident ID intersection |
| **Operational `ai_verdict` Exists** | Prior auto-triage attempts (`2026-11-19` to `2026-11-25`) | **61 / 100** | `41` `Qwen/Qwen2.5-7B-Instruct-AWQ`, `17` `POLICY_GUARD`, `2` `PREFLIGHT_GUARD`, `1` `TOKEN_BUDGET_GUARD` — **all 61** resolved to `REQUIRES_ATTENTION` (no decisive leaked label) and masked during human review |
| **Non-Empty Historical SIEM Resolution** | Legacy FortiSIEM resolution string | **15 / 100** | `14` `True Positive`, `1` `False Positive` — masked under `BLIND_ENFORCED`; interestingly, human reviewer classified 12 of those 14 historical TPs as `FALSE_POSITIVE`, 1 as `INCONCLUSIVE`, 1 as `TRUE_POSITIVE`, proving reviewer independence |
| **Blind-Review Enforcement** | Queue, Detail, Investigation, Timeline APIs | **100 / 100 Enforced** | Server-side masking stripped both historical resolution and operational `ai_verdict` before reviewer submission; all 3 blind attestations `True` |

### Exact Exposure Venn Breakdown `(hist_resolution, op_ai_verdict, in_learning, in_prompt_capture)`
- `(False, False, False, False)`: **25 incidents** -> `VERIFIED_NO_DETECTED_EXPOSURE`
- `(False, True, False, False)`: **60 incidents** -> `HISTORICAL_LABEL_EXISTS_BUT_MASKED` (operational `REQUIRES_ATTENTION` masked)
- `(True, False, False, False)`: **14 incidents** -> `HISTORICAL_LABEL_EXISTS_BUT_MASKED` (SIEM resolution masked)
- `(True, True, False, False)`: **1 incident** (`fid=14`) -> `HISTORICAL_LABEL_EXISTS_BUT_MASKED` (both masked)

---

## 3. AIS 3.1 Exposure Classification & Remediation

| AIS 3.1 Classification Enum | Count | Benchmark Disposition |
|---|---:|---|
| `VERIFIED_NO_DETECTED_EXPOSURE` | **25** | Clean & Eligible (`PROVISIONAL_SINGLE_REVIEW_BENCHMARK`) |
| `HISTORICAL_LABEL_EXISTS_BUT_MASKED` | **75** | Eligible (`PROVISIONAL_SINGLE_REVIEW_BENCHMARK`; historical/op metadata strictly masked & absent from LLM prompt/RAG/Memory) |
| `CONFIRMED_EXPOSURE` | **0** | Quarantined if present (`0` confirmed) |
| `EXPOSURE_UNCERTAIN` | **0** | Flagged if telemetry unavailable (`0` uncertain) |

Both subsets (`25` completely untouched and `75` masked-historical) are tracked separately in post-run evaluation metrics so accuracy on the `25`-incident clean core can be verified alongside the full `100`-incident cohort.
