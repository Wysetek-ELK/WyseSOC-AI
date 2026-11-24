# AIS 2.6e — Actual Model Capability Assessment & Retention Decision

**Document Identifier:** `19_ACTUAL_MODEL_CAPABILITY_AND_RETENTION_DECISION.md`  
**Phase:** AIS 2.6e  
**Status:** COMPLETE / EVALUATION  
**Evaluated Model:** `Qwen/Qwen2.5-7B-Instruct-AWQ`  
**Related Manifests:** [MODEL_CAPABILITY_DECISION.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/MODEL_CAPABILITY_DECISION.json)

---

## 1. Executive Summary & Assessment Decision

The central question of Phase AIS 2.6e is:
> *Can our locally hosted LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`) independently produce a correct and trustworthy SOC verdict when evaluated against real security incidents?*

### Formal Capability Finding:
$$\mathbf{CAPABILITY\_ASSESSMENT = UNPROVEN\_EMPIRICALLY}$$
$$\mathbf{RETENTION\_RECOMMENDATION = PROVISIONALLY\_RETAIN\_FOR\_STAGE\_B}$$

---

## 2. Evaluation of Evidence

### 2.1 What Has Been Empirically Proven:
1. **Context Window Adherence:** The model and token budgeting pipeline support up to 8,192 tokens; all 20 real incidents fit within 6,680 prompt tokens, ensuring zero context truncation.
2. **Structural Output Compliance:** Unit tests confirm the model follows JSON schemas and outputs valid triage structures without syntax collapse.
3. **Infrastructure Feasibility:** The AWQ 4-bit quantized model runs efficiently within 5.5 GB VRAM on an AWS EC2 `g5.xlarge` instance (NVIDIA A10G 24GB).

### 2.2 What Remains Unproven:
1. **Actual Security Intelligence:** True Positive / False Positive discrimination on live real-world logs.
2. **Policy Guidance Sensitivity:** Whether approved domain policy genuinely improves accuracy or merely introduces confirmation bias.
3. **Hallucination Rate:** Frequency with which the model invents processes or network traffic under production pressure.

---

## 3. Retention Justification and Next Steps

Non-Negotiable Requirement 12 prohibits premature architectural churn:
- **Do NOT discard or replace the model:** Replacing the model with an alternative (e.g., Llama-3, Mistral, or a 70B variant) without first establishing the empirical baseline of `Qwen2.5-7B-Instruct-AWQ` would introduce confounding variables.
- **Do NOT implement complex RAG or agentic loops:** The single-pass reasoning capability must be quantified first.
- **Decision:** Retain `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2. Proceed to Stage B live evaluation once the operator completes priority ground truth reviews and authorizes GPU power-on.
