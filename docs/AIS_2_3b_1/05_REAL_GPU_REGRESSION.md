# AIS 2.3b.1 — Real GPU Regression Results & Empirical Accounting

**Project:** Verdictum AI  
**Subsystem:** Agent Intelligence Studio (AIS)  
**Phase:** AIS 2.3b.1 (Wire Token Reservation & Semantic Verdict Grounding Integrity)  
**Date:** November 23, 2026  
**Status:** COMPLETED & EMPIRICALLY RECORDED  

---

## 1. Executive Summary

Phase AIS 2.3b.1 executed a comprehensive regression re-evaluation across all 5 historical FortiSIEM benchmark incidents (2 CrowdStrike and 3 Prisma SASE) to verify the corrected wire token budgeting, semantic claim grounding, and empirical accounting.

### Key Results:
1. **100% Wire Budget Compliance:** All dispatched live requests registered **3,013 wire prompt tokens**, strictly complying with the $\le 3,328$ prompt ceiling with 315 tokens of headroom.
2. **Strict 768 Completion Headroom:** Available completion headroom before reaching the 4,096 context ceiling was **1,083 tokens** ($4,096 - 3,013$), fully preserving the requested 768 tokens without silent provider clamping.
3. **Zero Output Truncation:** All dispatched responses completed normally (`finish_reason = "stop"`).
4. **Semantic Grounding Enforced on Incident `132527297`:**
   - Model proposed `TRUE_POSITIVE` based on *"The executing binary is not signed"*.
   - Validator marked Claim 1 as `UNSUPPORTED_PREDICATE` because `process.name = UltraViewer_Service.exe` does not prove signature status.
   - Decisive proposal was fail-closed **REJECTED** and overruled to `REQUIRES_ATTENTION`.
5. **Safe Preflight Abstentions (Prisma SASE):** All 3 Prisma SASE incidents safely abstained at preflight (`CONTEXT_WINDOW_EXCEEDED`) with **0 ms of wasted GPU compute**.
6. **Clean Empirical Accounting:** Preflight abstentions record `raw_proposed_verdict: None`, preventing safe fallbacks from being misrepresented as model decisions.

---

## 2. Side-by-Side Comparison: AIS 2.3a vs AIS 2.3b vs AIS 2.3b.1

| Incident ID | Vendor / Rule | AIS 2.3a Prompt | AIS 2.3a Finish | AIS 2.3b Prompt | AIS 2.3b Finish | AIS 2.3b.1 Wire Tokens | AIS 2.3b.1 Headroom | AIS 2.3b.1 Finish | AIS 2.3b.1 Proposed | AIS 2.3b.1 Effective Verdict | AIS 2.3b.1 Validation Status |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `132438483` | CrowdStrike | 3,757 | `length` (Truncated) | 3,370 | `stop` | **3,013** | **1,083** | `stop` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `VALIDATED` |
| `132527297` | CrowdStrike | 3,758 | `length` (Truncated) | 3,371 | `stop` | **3,013** | **1,083** | `stop` | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `REJECTED` |
| `132499009` | Prisma SASE | 3,576 | `length` (Truncated) | 6,204 | `None` (Preflight) | >6,000 | N/A | `None` (Preflight) | `None` | `REQUIRES_ATTENTION` | `CONTEXT_WINDOW_EXCEEDED` |
| `132499023` | Prisma SASE | 3,607 | `length` (Truncated) | 6,299 | `None` (Preflight) | >6,000 | N/A | `None` (Preflight) | `None` | `REQUIRES_ATTENTION` | `CONTEXT_WINDOW_EXCEEDED` |
| `132499745` | Prisma SASE | 3,583 | `length` (Truncated) | 6,176 | `None` (Preflight) | >6,000 | N/A | `None` (Preflight) | `None` | `REQUIRES_ATTENTION` | `CONTEXT_WINDOW_EXCEEDED` |

---

## 3. Dispatched Incidents Deep Dive

### 3.1 Incident `132438483` (CrowdStrike: Suspicious Activity)
- **Database UUID:** `f382827c-1068-409d-9e4d-6baf4e2e3b86`
- **Execution Mode:** Dispatched live GPU evaluation
- **Actual Wire Prompt Tokens:** 3,013 (<= 3,328 cap)
- **Completion Reserve Available:** 1,083 tokens (>= 768 tokens)
- **Requested Max Tokens:** 768
- **Finish Reason:** `stop` (no truncation)
- **Proposed Verdict:** `REQUIRES_ATTENTION` (Confidence: 50.0%)
- **Effective Verdict:** `REQUIRES_ATTENTION`
- **Validation Status:** `VALIDATED`
- **Grounded Supporting Claims:**
  - `process.command_line = "\"C:\\Program Files (x86)\\UltraViewer\\UltraViewer_Service.exe\""` (`GROUNDED`)
  - `process.parent_name = "services.exe"` (`GROUNDED`)
- **Reasoning Verification:** Model noted missing `process.parent_command_line`. Check 4e identified that `file.hash_sha256` was in fact `PRESENT_VALID` in canonical telemetry.

### 3.2 Incident `132527297` (CrowdStrike: Suspicious Activity)
- **Database UUID:** `028c79e6-7397-4c49-a0ed-15b9997fdd7a`
- **Execution Mode:** Dispatched live GPU evaluation
- **Actual Wire Prompt Tokens:** 3,013 (<= 3,328 cap)
- **Completion Reserve Available:** 1,083 tokens (>= 768 tokens)
- **Requested Max Tokens:** 768
- **Finish Reason:** `stop` (no truncation)
- **Proposed Verdict:** `TRUE_POSITIVE` (Confidence: 85.0%)
- **Effective Verdict:** `REQUIRES_ATTENTION` (Overruled by Validator)
- **Validation Status:** `REJECTED`
- **Validation Reason Codes:** `["UNSUPPORTED_PREDICATE", "UNSUPPORTED_CLAIM", "TP_CRITERIA_UNSATISFIED"]`
- **Claim Grounding Analysis:**
  - Claim 1 (*"The executing binary is not signed"* citing `process.name`): `is_grounded = False`, `grounding_status = "UNSUPPORTED_PREDICATE"`.
  - Claim 2 (*"Process was blocked by the Crowdstrike agent"* citing `security.action`): `is_grounded = True`, `grounding_status = "GROUNDED"`.
- **Verdict Integrity Principle:** A security control block does not prove that an application is malicious; without valid signature verification or confirmed threat intelligence, the decisive TP proposal cannot be certified and must be routed to human review.

---

## 4. Empirical Evaluation Metrics & Accounting

```json
{
  "total_incidents_evaluated": 5,
  "real_gpu_dispatched_count": 2,
  "successful_complete_responses_count": 2,
  "preflight_abstained_count": 3,
  "model_proposed_tp_count": 1,
  "model_proposed_fp_count": 0,
  "model_proposed_attention_count": 1,
  "model_no_inference_count": 3,
  "validator_decisive_accepted_count": 0,
  "validator_overruled_to_attention_count": 1,
  "selective_accuracy": "NOT_MEASURABLE (0 decisive accepted verdicts)",
  "decision_coverage": 0.0,
  "safe_disposition_rate": 1.0,
  "fabrication_detected": false
}
```

### Accounting Notes:
- **Zero Preflight Pollution:** The 3 Prisma SASE incidents are counted strictly under `preflight_abstained_count` and `model_no_inference_count`. They do not inflate `model_proposed_attention_count`.
- **No False 100% Accuracy:** Selective accuracy is reported as `NOT_MEASURABLE` because the single proposed TP was rejected due to an unsupported predicate. The platform refuses to claim 100% accuracy on ungrounded claims.
- **Fail-Closed Safety:** 100% of incidents (5/5) resulted in safe outcomes (`REQUIRES_ATTENTION`). Zero ungrounded auto-closures occurred.
