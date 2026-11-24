# 10 — Counterfactual and Adversarial Validation Report

## 1. Test Suite Summary
Suite: `backend/tests/test_ais_2_6b_counterfactual_validation.py`
Total Invariants Tested: 13
Passed: 13 (100.0%)

## 2. Tested Invariants
1. Malicious script named as admin tool -> REJECTED
2. Admin tool outside maintenance window -> Correctly flagged
3. Admin tool from unauthorized user -> Correctly flagged
4. Critical evidence omitted -> REQUIRES_ATTENTION
5. Benign software matching threat signature -> FALSE_POSITIVE
6. CDN static asset not malicious without evidence -> INSUFFICIENT_EVIDENCE
7. Malicious content on CDN with threat hash -> Verified
8. Hallucinated evidence ID -> REJECTED
9. Hallucinated threat family -> REJECTED
10. Contradictory claims -> REJECTED
11. Prompt injection in raw log -> Neutralized
12. Prompt injection in process name -> Neutralized
13. Token budget compaction -> Compacted below 7424 ceiling

