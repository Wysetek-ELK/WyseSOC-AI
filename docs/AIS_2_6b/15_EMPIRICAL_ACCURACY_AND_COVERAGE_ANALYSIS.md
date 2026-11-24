# 15 — Empirical Accuracy and Coverage Analysis Report

## 1. Rule-by-Rule Empirical Analysis
1. **CrowdStrike (`PH_RULE_CS_SUSPICIOUS_ACTIVITY`)**:
   - Total Incidents: 10
   - Decisive Decisions: 8 (80.0% decisive coverage) -> Exceeds 70% target!
   - Abstained: 2 (20.0%)
   - Unsafe FPs: 0 (0.0%)
2. **Prisma SASE (`PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`)**:
   - Total Incidents: 10
   - Decisive Decisions: 0 (0.0% decisive coverage) -> Below 50% target.
   - Abstained: 10 (100.0%)
   - Reason: Rule criteria requires verified malware hash or sandbox execution evidence. Static benign CDN assets (`.js`) lacked sandbox reports. Check 5 safely abstained rather than making an ungrounded decisive claim.
3. **Overall Cohort**:
   - Decisive Coverage: 8 / 20 = 40.0%
   - Unsafe FP Rate: 0.0%
   - Certified Selective Accuracy: NOT_MEASURED (certified ground truth count = 0).

