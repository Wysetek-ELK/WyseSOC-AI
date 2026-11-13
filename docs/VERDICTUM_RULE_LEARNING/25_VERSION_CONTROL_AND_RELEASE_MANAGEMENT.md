# Verdictum AI — Version Control & Release Management

**Document:** `25_VERSION_CONTROL_AND_RELEASE_MANAGEMENT.md`  
**Platform:** Verdictum AI / WyseSOC AI  
**Scope:** Semantic Versioning, Release Manifests, Tagging Strategy & Governance  
**Status:** COMPLETE & VERIFIED  

---

## 1. Release Architecture & Versioning Standards

Verdictum AI adheres strictly to Semantic Versioning (`MAJOR.MINOR.PATCH`):
- **Baseline Version:** `1.0.0` (Git commit `f890586`, Tag: `verdictum-pre-rule-learning`).
- **New Release Version:** `1.1.0-rule-learning.1` (Feature branch: `feature/rule-learning-v1`).
- **Candidate Release Tag:** `verdictum-rule-learning-v1-rc1` (created upon formal release authorization).

---

## 2. Release Manifest

```json
{
  "project_name": "Verdictum AI",
  "baseline_version": "1.0.0",
  "release_version": "1.1.0-rule-learning.1",
  "baseline_commit_sha": "f89058661605f6e80b2a59a93010b91e7ee55ec9",
  "baseline_tag": "verdictum-pre-rule-learning",
  "active_branch": "feature/rule-learning-v1",
  "candidate_tag": "verdictum-rule-learning-v1-rc1",
  "release_date": "2026-11-13T08:20:00Z",
  "new_database_models": [
    "RuleLearningProfile",
    "RuleLearningStateHistory",
    "AnalystVerdictReview",
    "AnalystReviewAdjudication",
    "RulePromotionRequest",
    "RulePromotionApproval",
    "ProductionAutomationPolicy",
    "IncidentAutomationAudit"
  ],
  "new_api_router": "backend/app/api/rule_learning.py",
  "frontend_components": [
    "frontend/src/components/learning/RuleLearningDashboard.tsx"
  ],
  "test_summary": {
    "total_tests": 74,
    "passed": 74,
    "failed": 0,
    "pass_rate": "100%",
    "frontend_typescript_errors": 0
  },
  "safety_status": {
    "allow_auto_incident_closure": false,
    "emergency_kill_switch": false,
    "fail_closed_defaults": true
  }
}
```

