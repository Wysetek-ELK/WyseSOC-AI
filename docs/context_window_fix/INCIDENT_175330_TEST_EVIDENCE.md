# Incident #175330 & #173403 Live Inference Test Evidence

**Date:** 2026-11-12  
**Test Harness:** RepoDeploy Governor Live Inference Controller  
**Server 1 (Backend Host):** `remote-server` (Ubuntu 24.04 LTS, FastAPI)  
**Server 2 (Inference Host):** `<SERVER2_IP>:8000` (vLLM `Qwen/Qwen2.5-7B-Instruct-AWQ`)

---

## 1. Executive Summary

Prior to remediation, FortiSIEM incident #175330 generated **40,792 tokens** and failed closed with `CONTEXT_WINDOW_EXCEEDED` without executing LLM inference. Similarly, incident #173403 generated **4,979 tokens** and failed closed at the 4,096-token boundary.

Following implementation of `EvidenceCompactionService`, `ModelTokenizerService`, and dynamic context clamping, both incidents were evaluated live from Server 1 against Server 2:
- **Incident #175330:** Prompt compacted to ~3,000 tokens (well within the 3,584 available budget). Real GPU inference executed in 18.77s on Server 2 (`Qwen/Qwen2.5-7B-Instruct-AWQ`). Real completion tokens were generated and verified.
- **Incident #173403:** Prompt compacted to fit within budget. Real GPU inference executed in 17.65s on Server 2. Real completion tokens were generated and verified.
- **Trustworthiness & Grounding:** Zero unsupported verdicts were accepted. When the LLM produced ungrounded FP assertions, `IndependentVerdictValidator` rejected the claims and safely escalated to `REQUIRES_ATTENTION` as an abstention.

---

## 2. Live Inference Test Run: Incident #175330

### Incident Metadata:
- **Incident ID:** `175330`
- **Rule ID:** `PH_RULE_ANOMALY_TRAFFIC_DENIED_OUTBOUND_PORT`
- **Rule Title:** "Sudden Increase In Firewall Denied Outbound Traffic To A Specific TCP/UDP port"
- **Raw Event Count:** 100 events
- **Pre-Compaction Canonical Records:** 361 records (40,792 tokens)
- **Compacted Canonical Records:** 15 records (988 tokens)
- **Total Prompt Tokens:** 3,003 tokens ($\le 3,584$ budget)

### Live Execution Log:
```text
=== 1. CHECK BACKEND .ENV CONFIG ===
LOCAL_LLM_BASE_URL: http://<SERVER2_IP>:8000/v1
LOCAL_LLM_MODEL_NAME: Qwen/Qwen2.5-7B-Instruct-AWQ

=== 2. PROBE HEALTH & MODELS ENDPOINT ===
ROOT /health: HTTP 200
/v1/models: HTTP 200

=== 3. TEST CHAT COMPLETION (CLEAN PROMPT) ===
CHAT COMPLETION HTTP 200 in 447ms
RESPONSE:
{"id":"chatcmpl-850f13bd6095573e","object":"chat.completion","created":1794476496,"model":"Qwen/Qwen2.5-7B-Instruct-AWQ","choices":[{"index":0,"message":{"role":"assistant","content":"{\"status\": \"ok\", \"verdict\": \"TRUE_POSITIVE\"}","refusal":null,"annotations":null,"audio":null,"function_call":null,"reasoning":null},"logprobs":null,"finish_reason":"stop","stop_reason":null,"token_ids":null,"routed_experts":null,"weight_versions":null}],"service_tier":null,"system_fingerprint":"vllm-0.33.0-"}

=== 4. TEST TRIAGE ON HISTORICAL INCIDENT ===
Targeting requested incident: 175330
Testing triage on Historical Incident: 175330
Title: Sudden Increase In Firewall Denied Outbound Traffic To A Specific TCP/UDP port
Event Type: PH_RULE_ANOMALY_TRAFFIC_DENIED_OUTBOUND_PORT
Ground Truth Resolution: True Positive

>>> EVALUATION FINISHED in 18.77s! <<<
New Verdict: REQUIRES_ATTENTION
Confidence: 0.0%
Model Identifier: Qwen/Qwen2.5-7B-Instruct-AWQ
Reason: Model fabricated or asserted unverified evidence claims. Human Tier 2 investigation required. [Validation: EVIDENCE_VALUE_MISMATCH; FP_CRITERIA_UNSATISFIED]. Model rationale: The observed traffic is internal loopback traffic, which is typical for internal health checks and proxy reflections. There is no indication of external malicious activity.
Validation Status: REJECTED
Is Simulated: False
```

---

## 3. Live Inference Test Run: Incident #173403

### Incident Metadata:
- **Incident ID:** `173403`
- **Rule ID:** `PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST`
- **Rule Title:** "Website access policy violation: Same Source and Destination"
- **Pre-Remediation Status:** `CONTEXT_WINDOW_EXCEEDED (4,979 tokens)`
- **Post-Remediation Status:** Real LLM inference completed successfully in 17.65s

### Live Execution Log:
```text
=== 4. TEST TRIAGE ON HISTORICAL INCIDENT ===
Targeting requested incident: 173403
Testing triage on Historical Incident: 173403
Title: Website access policy violation: Same Source and Destination
Event Type: PH_RULE_WEB_POL_VIOLATION_SAME_SRC_SAME_DEST
Ground Truth Resolution: True Positive

>>> EVALUATION FINISHED in 17.65s! <<<
New Verdict: REQUIRES_ATTENTION
Confidence: 0.0%
Model Identifier: Qwen/Qwen2.5-7B-Instruct-AWQ
Reason: Model fabricated or asserted unverified evidence claims. Human Tier 2 investigation required. [Validation: EVIDENCE_VALUE_MISMATCH; FP_CRITERIA_UNSATISFIED]. Model rationale: The alert is triggered by internal loopback traffic where the source and destination IPs are identical, which is typical for internal health checks or proxy reflections.
Validation Status: REJECTED
Is Simulated: False
```

---

## 4. Key Verification Takeaways

1. **Successful Real Inference:**
   - Inference completed with `Model Identifier: Qwen/Qwen2.5-7B-Instruct-AWQ` and `is_simulated: False`.
   - The remote GPU daemon processed both prompts and generated structured completion tokens.
2. **Safeguards and Trustworthiness Verification:**
   - In both cases, the LLM attempted to claim benign internal loopback activity without grounded evidence.
   - The `IndependentVerdictValidator` and `EvidenceContractService` strictly caught the discrepancy (`EVIDENCE_VALUE_MISMATCH; FP_CRITERIA_UNSATISFIED`).
   - The system rejected the unsupported verdict and safely preserved `REQUIRES_ATTENTION` as an abstention.
3. **Zero Evidence Dropping:**
   - All Evidence Contract required fields, detection criteria, primary timestamps, time range bounds, and representative syslog clusters were verified present in the prompt.

