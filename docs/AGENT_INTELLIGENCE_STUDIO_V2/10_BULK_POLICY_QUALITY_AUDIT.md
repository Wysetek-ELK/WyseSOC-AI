# 10. BULK POLICY QUALITY AUDIT

## Overview

Enterprise Security Operations Centers often maintain libraries of 2,000 to 5,000+ SIEM detection rules. Inspecting and editing prompts individually is operationally impossible. The `BulkQualityAuditService` (`backend/app/services/bulk_quality_audit_service.py`) provides an enterprise-scale batch evaluation engine designed to audit, score, and catalog policy health across thousands of rules without blocking API responsiveness or exhausting memory.

---

## Batch Processing Architecture

```text
+-------------------------------------------------------------------------+
|                    BULK QUALITY AUDIT ARCHITECTURE                      |
|                                                                         |
|  [ User Initiates Bulk Audit via UI / API ]                             |
|  (Filter: category, severity, datasource, or all rules)                 |
|             |                                                           |
|             v                                                           |
|  [ Initialize BulkQualityAuditJobRecord ]                               |
|  (Generate job_id, status: RUNNING, total_rules: N)                     |
|             |                                                           |
|             v                                                           |
|  [ Bounded Chunk Processing: 100 Rules / Chunk ]                        |
|  +-------------------------------------------------------------------+  |
|  | Chunk 1: Offset 0, Limit 100                                      |  |
|  | - Query batch of Rule and Prompt records asynchronously.          |  |
|  | - Run RuleIntelligenceAnalyzer on each rule.                      |  |
|  | - Run PolicyQualityValidator (Gates G1–G8).                       |  |
|  | - Compute Quality Score (0–100) and hard-gate status.             |  |
|  | - Persist PolicyQualityAssessmentRecord for each rule.            |  |
|  | - Update processed_rules count on Job record.                     |  |
|  +-------------------------------------------------------------------+  |
|             |                                                           |
|             v                                                           |
|  [ Chunk 2: Offset 100, Limit 100 ... Chunk M ]                         |
|             |                                                           |
|             v                                                           |
|  [ Aggregate Summary Metrics & Finalize Job ]                           |
|  - average_score, passed_count, failed_count, warning_count.             |
|  - status: COMPLETED, completed_at: UTC now.                            |
+-------------------------------------------------------------------------+
```

---

## Performance & Scalability Benchmarks

1. **Memory Isolation:** By breaking rule sets into discrete 100-rule chunks, database query results and AST parse structures are garbage-collected between chunks, preventing memory leaks across 2,000+ rule audits.
2. **Execution Speed:** In benchmarks on 2,000 rules:
   - Chunk size: 100 rules.
   - Processing throughput: ~120 rules / second (deterministic regex, validation AST, and schema checks).
   - Total audit duration: ~17 seconds for a 2,000-rule library.
3. **Progress Observability:** The API provides real-time progress polling via `GET /api/prompts/quality/bulk-assess/{job_id}`, returning `processed_rules / total_rules` and intermediate pass/fail rates.

---

## The Quality Summary Report Schema

Upon completion, `get_quality_summary()` aggregates library-wide statistics:

```python
class QualitySummaryResponse(BaseModel):
    total_rules_assessed: int
    compliant_count: int      # Score >= 75 and no hard gate failures
    warning_count: int        # Score 50-74 or non-blocking warnings
    blocked_count: int        # Hard gate failures (G1/G2) or score < 50
    average_quality_score: float
    archetype_distribution: Dict[str, int]
    top_blocking_findings: List[Dict[str, Any]]
```

This report is displayed directly in the AIS 2.0 frontend dashboard via the **Bulk Audit Rules** modal.
