# 06 — Validator Corrections and Regression Verification

## 1. Targeted Validator Corrections

Two structural validator defects were identified and resolved in `backend/app/services/`:

1. **Network Baseline Grounded Authorization Support (`independent_verdict_validator.py`)**:
   Previously, `has_grounded_authorization` only accepted endpoint management processes (`ccmexec.exe`, `gpscript.exe`) or change tickets (`CHG-xxx`). It rejected all network baseline authorizations.
   - *Fix*: Added verification for approved enterprise domains, CDN allowlists, and clean threat intelligence reputation records (`policy.approved_domain`, `domain.allowlist`, `clean reputation`).

2. **Claim Extractor Predicate False Positives (`model_claim_extractor.py`)**:
   - Clean reputation statements (e.g. "VirusTotal reports clean reputation") were falsely triggering `UNSUPPORTED_PREDICATE: MALWARE_VERIFIED`.
   - Claims mentioning approved CDN domains (e.g. `cdn.enterprise-approved.com`) were falsely triggering unverified administrative authorization predicates.
   - *Fix*: Added negation guards for clean/benign terms and restricted administrative authorization predicates to explicit authorization assertions.

---

## 2. Controlled Regression Test Suite

Created dedicated regression suite `backend/tests/test_ais_2_5a_validator_regression.py` containing 7 comprehensive unit tests:

| Test Case | Scenario | Expected Outcome | Result |
|---|---|---|---|
| `test_valid_true_positive_accepted` | Genuinely supported TP (malicious C2, encoded powershell, temp path) | `VALIDATED`, Accepted | **PASS** |
| `test_valid_endpoint_false_positive_accepted` | Legitimate endpoint admin binary (`ccmexec.exe` + `CHG-10294`) | `VALIDATED`, Accepted | **PASS** |
| `test_valid_network_baseline_false_positive_accepted` | Legitimate network download from approved domain with clean hash | `VALIDATED`, Accepted | **PASS** |
| `test_unsupported_true_positive_rejected` | Unsupported TP (dual-use tool without malicious tradecraft) | `REJECTED`, Escalated | **PASS** |
| `test_unsupported_false_positive_rejected` | Unsupported FP (unauthorized script claimed as maintenance) | `REJECTED`, Escalated | **PASS** |
| `test_deduplication_distinguishes_distinct_incidents` | Multiple incidents sharing rule ID but differing in detail/time | `is_duplicate=False` | **PASS** |
| `test_wilson_score_interval_exact_computation` | Exact Wilson score calculation for $N=2, k=0$ and $N=20, k=0$ | [0.0%, 65.76%], [0.0%, 16.84%] | **PASS** |

### Execution Command:
```powershell
backend\venv\Scripts\pytest backend/tests/test_ais_2_5a_validator_regression.py -q
# Output: 7 passed in 0.98s
```
Full backend test suite: **36/36 tests PASSED**.
