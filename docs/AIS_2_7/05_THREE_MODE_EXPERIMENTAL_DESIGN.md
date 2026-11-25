# 05 — Controlled Three-Mode Experimental Design

**Phase:** AIS 2.7 (Workstream 5)

---

## 1. Three-Mode Architecture

1. **Mode A — Neutral LLM Baseline (20 GPU calls):** Uses `EmpiricalBenchmarkHarness.NEUTRAL_SOC_BASELINE_V1` + strict JSON output schema, identical budgeted incident payload and `rule_spec`, zero rule-specific intelligence policy, zero RAG (`rag_block=""`), zero GT/historical labels.
2. **Mode B — Approved Policy-Assisted LLM (20 GPU calls):** Uses identical budgeted incident payload and `rule_spec`, compiled with Server 1's actual approved policies:
   - CrowdStrike (`0974a66e-ede2-4a6a-821b-6283a99c8aa4`): **`b6d9df2f-aad8-4208-89de-3e94e64e1b49` (v3, `APPROVED`)**
   - Prisma SASE (`14481ebd-4e8c-421e-8579-b6ee7995b746`): **`ed7ff3c7-ff30-49cb-a0f8-fa10eba79ece` (v1, `APPROVED`)**
3. **Mode C — Deterministic Validator (0 GPU calls):** Consumes raw Mode B response + canonical evidence + `RuleEvidenceContract` through `ModelClaimExtractor`, `IndependentVerdictValidator v2.0.0`, and `VerdictTrustworthinessEngine`.

---

## 2. Pre-Execution Policy Contamination & Bias Audit

- **CrowdStrike v3 (`b6d9df2f...`):** Clean generic `MALWARE_EXECUTION` policy; no benchmark incident IDs or label leakage.
- **Prisma SASE v1 (`ed7ff3c7...`):** Contains **no benchmark incident IDs or label leakage**, **but exhibits a severe template mismatch**: its `common_prompt` discusses `SAME_SRC_SAME_DEST` and EDR PowerShell/LOLBins and instructs *"DO NOT use REQUIRES_ATTENTION for routine internal web policy"*, while its `rule_specific_prompt` requires parent process lineage and command lines that do not exist in Prisma SASE firewall logs. Per Requirement 11, this approved policy is **NOT modified** during baseline execution; its impact on Mode B vs Mode A is directly measured in Workstreams 15–16.

---

## 3. Frozen Controls

- Model: `Qwen/Qwen2.5-7B-Instruct-AWQ` via `http://13.204.214.64:8000/v1` (verified `max_model_len=8192`).
- Context ceiling: `8192` tokens; completion reserve: `768` tokens; target input budget: `6400` tokens (hard ceiling `7424`).
- `temperature=0.1`, `allow_mock_fallback=False`, `rag_block=""`, `seed=None` (reproducibility limitation documented).

Artifacts: [EXPERIMENT_CONFIGURATION_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/EXPERIMENT_CONFIGURATION_MANIFEST.json), [APPROVED_POLICY_IDENTITY.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/APPROVED_POLICY_IDENTITY.json), [PROMPT_PARITY_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/PROMPT_PARITY_MANIFEST.json).
