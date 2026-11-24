# AIS 2.6e — Complete Live Three-Mode Benchmark Protocol

**Document Identifier:** `14_COMPLETE_LIVE_THREE_MODE_BENCHMARK.md`  
**Phase:** AIS 2.6e  
**Status:** SPECIFICATION / FROZEN  
**Target Population:** Full 20 Frozen Cohort Incidents  
**Related Manifests:** [THREE_MODE_EXECUTION_PROTOCOL.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/THREE_MODE_EXECUTION_PROTOCOL.json), [BENCHMARK_EXECUTION_PLAN.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/BENCHMARK_EXECUTION_PLAN.json)

---

## 1. Executive Summary & Full Benchmark Protocol

Following successful pilot completion, the full Three-Mode benchmark evaluates the entire frozen 20-incident cohort. The benchmark systematically compares:
- **Mode A (Neutral Core LLM):** 20 live requests.
- **Mode B (Approved Policy LLM):** 20 live requests.
- **Mode C (Deterministic Validator):** 20 local evaluations (0 GPU calls).

Total cohort GPU calls: **40 live requests** (10 completed in pilot + 30 completed in cohort phase) + 1 smoke test = **41 total baseline calls**.

---

## 2. Experimental Mode Comparison Matrix

```
+---------------------------------------------------------------------------------------+
| Incident (1..20)                                                                      |
+---------------------------------------------------------------------------------------+
        |                                       |                               |
        v                                       v                               v
[ Mode A: Neutral ]                    [ Mode B: Policy ]              [ Mode C: Validator ]
  Prompt: NEUTRAL_SOC_BASELINE_V1        Prompt: Approved Policy V1      Evaluates A & B output
  Temp: 0.0, Seed: 42                    Temp: 0.0, Seed: 42             Deterministic Python
  Telemetry -> MODE_A_LIVE_LEDGER        Telemetry -> MODE_B_LIVE_LEDGER Telemetry -> MODE_C_LEDGER
        |                                       |                               |
        +---------------------------------------+-------------------------------+
                                                |
                                                v
                              [ Certified Human Ground Truth ]
                                                |
                                                v
                               [ Comparative Accuracy Analysis ]
```

---

## 3. Telemetry and Ledger Verification Invariants

Every live execution record must satisfy:
1. `request_id`: Non-empty UUID from vLLM.
2. `prompt_tokens`: Integer between 2,000 and 7,424.
3. `completion_tokens`: Integer between 50 and 768.
4. `latency_ms`: Float $\ge 500.0$ ms.
5. `is_live_measurement`: Strictly `true`.
6. `provider_name`: Strictly `LIVE_VLLM_OPENAI_COMPATIBLE`.

Any record missing these attributes or carrying `OFFLINE_SIMULATION` is rejected by the integrity scanner.
