# 09. SINGLE LOCAL LLM EVALUATION ACCEPTANCE REPORT

## Verdictum AI — Agent Intelligence Studio 2.1a
**Execution Mode:** Controlled Single Live Local LLM Inference Verification  
**Target Rule:** Heavy TCP Host Scan On Fixed Port (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Target Incident:** Incident #335 (`049d9828-a8e4-404b-ae38-2288724552d3`)  
**Deployment Target:** Server 1 (`172.26.41.240`)  
**Inference Host:** Server 2 (`http://13.204.214.64:8000/v1`)  
**Active Policy Baseline:** Version v7 (`d79fb576-c6b9-4f63-9167-3c7a2419b70a`)  
**Verified Git SHA:** `f41c7a82c05ef98f4d4d12b5db8e57d002582522`

---

## 1. Executive Summary

As mandated by AIS 2.1a operational constraints:
- **No unapproved batch inference execution.**
- **No synthetic evaluation generation.**
- **Explicit human authorization required prior to live model evaluation.**
- **Verification of one real Local LLM evaluation on Server 2 pinned strictly to approved policy v7.**

Upon receiving explicit user authorization, a single controlled live inference test was executed against Server 2 (`Qwen/Qwen2.5-7B-Instruct-AWQ`) evaluating Incident `#335`. The evaluation completed successfully in 16.648s, passed the quality validator with `VALIDATED` status, returned an abstention verdict (`REQUIRES_ATTENTION`), and seamlessly updated the live AI Evaluation Tracking table.

---

## 2. Explicit Human Authorization

Interactive confirmation was presented and approved via `ask_question`:

- **Prompt:** `"Authorize Single Live Local LLM Evaluation Test on Server 2 for Incident #335?"`
- **Options Presented:**
  - `(Recommended) YES — Authorize single live Local LLM inference test on Server 2 with pinned v7 policy`
  - `NO — Skip live model inference test and keep evaluation records unchanged`
- **User Decision:** `YES — Authorize single live Local LLM inference test on Server 2 with pinned v7 policy`
- **Recorded Timestamp:** `2026-11-21T04:28:40Z`

---

## 3. Live Inference Execution Telemetry

Execution script `execute_single_inference_test.py` invoked the live AI evaluation service on Server 1, dispatching to Server 2 vLLM runtime:

```json
{
  "incident_id": "049d9828-a8e4-404b-ae38-2288724552d3",
  "incident_number": 335,
  "rule_uuid": "40498741-ee6b-4a71-9101-0d6d3f77154c",
  "rule_name": "Heavy TCP Host Scan On Fixed Port",
  "prompt_version_id": "d79fb576-c6b9-4f63-9167-3c7a2419b70a",
  "prompt_version_number": 7,
  "model_name": "Qwen/Qwen2.5-7B-Instruct-AWQ",
  "inference_host": "http://13.204.214.64:8000/v1",
  "telemetry": {
    "latency_ms": 16648,
    "prompt_tokens": 1845,
    "completion_tokens": 412,
    "total_tokens": 2257
  },
  "result": {
    "verdict": "REQUIRES_ATTENTION",
    "confidence": 0.65,
    "validation_status": "VALIDATED",
    "reasoning_summary": "The model identified TCP SYN traffic targeting port 80 across multiple destination hosts (172.26.31.0/24) originating from 172.26.29.65. While characteristic of fixed port network reconnaissance, ambiguity regarding whether the source is an authorized scanner requires analyst review."
  }
}
```

---

## 4. Quality Validator Gate Verification

The inference output was processed through the post-inference Quality Validator:
- **XML Structure Verification:** All mandatory tags (`<summary>`, `<evidence_analysis>`, `<risk_assessment>`, `<verdict>`, `<confidence>`) parsed successfully.
- **Confidence Calibration:** Confidence score of 0.65 falls within the abstention bracket ($0.50 \le c < 0.75$), correctly triggering the `REQUIRES_ATTENTION` verdict.
- **Validator Status:** Recorded as `VALIDATED`.
- **Database Persistence:** Saved to `ai_evaluation_records` table linked to incident `#335` and policy version `v7`.

---

## 5. Live UI Reflection in AI Evaluation Tab

Immediately following the test, the live tracking table was refreshed and verified via Headless Chrome CDP:
- **Card Summary:**
  - Total Incidents: `13`
  - Not Evaluated: `12`
  - Abstained: `1`
  - Decisive: `0`
- **Table Row for Incident #335:**
  - Status Badge: `ABSTAINED` (Yellow)
  - AI Verdict: `REQUIRES_ATTENTION`
  - Policy Version: `v7`
  - Execution Time: `16.6s`
  - Model: `Qwen2.5-7B`
- **Screenshot Evidence:** `docs/AIS_2_1a_FINAL_OPERATIONAL_ACCEPTANCE/screenshots/03_ai_evaluation_tracking_tab.png`

---

## 6. Sign-off

The single Local LLM evaluation test on Server 2 is **100% verified, authorized, and accepted**.
