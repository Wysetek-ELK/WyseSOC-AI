# AIS 2.6e — Three-Mode Experimental Control Specification

**Document Identifier:** `07_THREE_MODE_EXPERIMENTAL_CONTROL.md`  
**Phase:** AIS 2.6e  
**Status:** COMPLETE / FROZEN  
**Target Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ`  
**Related Artifacts:** [THREE_MODE_EXECUTION_PROTOCOL.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/THREE_MODE_EXECUTION_PROTOCOL.json), [POLICY_IDENTITY_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/POLICY_IDENTITY_MANIFEST.json), [PROMPT_PARITY_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/PROMPT_PARITY_RESULTS.json)

---

## 1. Executive Summary & Experimental Purpose

The fundamental scientific objective of Phase AIS 2.6e is to measure the actual, empirical intelligence and correctness of the local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`) when evaluating real FortiSIEM security incidents. To isolate intrinsic LLM reasoning from policy guidance and external deterministic validation, the evaluation architecture enforces strict three-mode experimental control.

```
                      +---------------------------------------+
                      |       Raw Incident & Evidence         |
                      |   (Canonical Compact Evidence JSON)   |
                      +-------------------+-------------------+
                                          |
          +-------------------------------+-------------------------------+
          |                               |                               |
          v                               v                               v
+-------------------+           +-------------------+           +-------------------+
|      MODE A       |           |      MODE B       |           |      MODE C       |
|  Neutral Baseline |           |  Approved Policy  |           |   Deterministic   |
|   (Zero Policy)   |           |  (Domain Guidance)|           |     Validator     |
+---------+---------+           +---------+---------+           +---------+---------+
          |                               |                               |
          v                               v                               v
[ LLM Core Reasoning ]          [ LLM Policy Guidance ]         [ Python Logic Rule ]
  TP / FP / Inconclusive          TP / FP / Inconclusive          Review / Escalate
          |                               |                               |
          +-------------------------------+-------------------------------+
                                          |
                                          v
                      +---------------------------------------+
                      |      Certified Human Ground Truth     |
                      |   (Double-Blind Certified Reviews)    |
                      +---------------------------------------+
```

---

## 2. Experimental Mode Definitions

### 2.1 Mode A: Neutral Baseline (Unassisted Core LLM Reasoning)
* **Goal:** Establish the intrinsic security reasoning baseline of `Qwen/Qwen2.5-7B-Instruct-AWQ` without any domain-specific policy hints, rule directives, or triage heuristics.
* **Prompt Template:** `NEUTRAL_SOC_BASELINE_V1`
* **Prompt Template LF Hash:** `eed5c3beb4cc9d108762a43da5085b516d16958377d5c7fa2abcb602f1c7e056`
* **Prompt Template CRLF Hash:** `459915e17e42d2caf9e040d127de4713ec41057d8c9edcd689a66b79ed448f6f`
* **Input Elements:** 
  1. System instruction defining neutral SOC triage analyst persona.
  2. Incident metadata (incident ID, rule name, severity, trigger timestamp).
  3. FortiSIEM rule triggering logic/condition.
  4. Deterministically compacted canonical evidence logs (process execution, network connections, file operations).
* **Excluded Elements:** Policy instructions, triage directives, analyst notes, historical resolution, ground truth labels.

### 2.2 Mode B: Approved Policy Guidance (Domain-Assisted Reasoning)
* **Goal:** Quantify the exact delta in verdict accuracy, confidence calibration, and coverage when the LLM is supplied with verified, human-approved SOC triage policy guidelines.
* **Policy Identity:**
  * **Policy ID:** `bd751fac-9bfb-4994-b150-8850bb94dd6c`
  * **Rule Name:** `Crowdstrike-Falcon-Host-Block-Detected` (and Prisma SASE equivalent)
  * **Policy Version:** `1` (Approved & Frozen)
  * **Policy Hash:** `d48a04b1257d0793b8c66e2c3e163d274094a9ea7538be14081ae212643a61f3`
  * **Compiler Version:** `v3.0.0`
* **Input Elements:** Identical evidence payload as Mode A PLUS compiled domain policy guidelines (specifying verified execution paths, administrative software exclusions, and IOC validation criteria).

### 2.3 Mode C: Independent Deterministic Validation
* **Goal:** Determine whether a deterministic Python validation engine can independently detect false verdicts or policy breaches without LLM hallucination.
* **Engine Type:** Deterministic rule engine (`backend/app/services/verdict_validator.py`).
* **GPU Utilization:** **0 GPU inference calls** (pure local CPU deterministic evaluation).
* **Behavior:** Evaluates LLM output from Mode A and Mode B against structural constraints, factual presence of cited entities in raw logs, and mandatory policy rules.

---

## 3. Strict Experimental Control Parameters

To ensure 100% mathematical reproducibility and prevent non-deterministic sampling variance:

| Parameter | Frozen Value | Scientific Rationale |
| :--- | :--- | :--- |
| **Model** | `Qwen/Qwen2.5-7B-Instruct-AWQ` | Authoritative hosted local model on Server 2 |
| **Inference Server** | vLLM (OpenAI-compatible `/v1/chat/completions`) | High-throughput AWQ quantized inference engine |
| **Temperature** | `0.0` | Eliminates random token sampling; forces greedy decoding |
| **Top-P** | `1.0` | Disabled when temperature is 0.0 |
| **Seed** | `42` | Deterministic pseudo-random seed anchor |
| **Max Completion Tokens**| `768` | Fixed completion budget for verdict JSON reasoning |
| **Input Token Budget** | `7,424` | 8,192 total context window minus 768 completion budget |
| **Compaction Strategy** | Deterministic canonical compaction | Proved in WS2: Max observed prompt = 6,680 tokens (0 overflows) |

---

## 4. Prompt Parity & Invariance Verification

A core flaw identified in historical benchmarks was mid-experiment prompt modification. In AIS 2.6e:
1. **Parity Check:** The Mode A neutral prompt template was verified byte-for-byte against the AIS 2.6c baseline.
2. **Hash Lineage:** 
   - Execution Normalized (LF): `eed5c3beb4cc9d108762a43da5085b516d16958377d5c7fa2abcb602f1c7e056` (100% Match)
   - Stored File (CRLF): `459915e17e42d2caf9e040d127de4713ec41057d8c9edcd689a66b79ed448f6f` (100% Match)
3. **Immutability Contract:** Prompts are frozen. No prompt text, system directive, or schema specification may be altered during pilot or cohort execution.

---

## 5. Safeguards Against Information Contamination

To uphold Non-Negotiable Requirements 3, 4, 5, 14, and 16:
1. **Zero Ground Truth In Prompts:** Neither Mode A nor Mode B prompts contain any historical analyst comments, resolution codes, or human ground truth labels.
2. **Zero Prior Verdict Leakage:** Mode B does not receive Mode A outputs; Mode A does not receive Mode B outputs.
3. **Validator Isolation:** Mode C operates strictly post-hoc on generated outputs; it does not steer, intercept, or rewrite inference-time token generation.
4. **Denominators:** Any metric where observations are zero must evaluate strictly to `null` or `NOT_DEMONSTRATED`.
