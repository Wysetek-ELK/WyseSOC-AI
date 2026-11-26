# AIS 2.9 Executive Summary

- **Engineering Completion**: `AIS_2_9_ENGINEERING_COMPLETE`
- **Frozen Regression**: `FROZEN_REGRESSION_TARGETS_MET`
- **Independent Certification Readiness**: `READY_FOR_INDEPENDENT_HUMAN_REVIEW`
- **Production Readiness**: `NOT_YET_PRODUCTION_CERTIFIED`
- **Server 1 Deployment**: `2dc8d15a4517626bcae375e5754f4431693053f3` (`DEPLOYED_AND_VERIFIED`)
- **Server 2 Model**: `Qwen/Qwen3-14B-AWQ` (`server_2_running=true`, `server_2_restart_performed=false`)
- **GPU Budget**: `33 / 50` attempted (`33` succeeded, `0` failed)

## Accuracy Comparison (Frozen 20-Incident Cohort)

| Metric | AIS 2.8 | AIS 2.9 Actual | Target | Status |
|---|---:|---:|---:|---|
| Validated exact agreement | 80.0% (16/20) | 95.0% (19/20) | 90–95% | MET |
| Validated TP recall | 66.67% (6/9) | 100.0% (9/9) | >= 90% | MET |
| FP identification recall | 0.0% (0/1) | 0.0% (0/1) | Evidence-dependent | EXPECTED_SAFETY_ABSTENTION |
| Binary correctness | 60.0% (6/10) | 90.0% (9/10) | 80–90% | MET |
| Decision coverage | 60.0% (6/10) | 90.0% (9/10) | 80–90% | MET |
| Context overflows | 1 | 0 | 0 | MET |
