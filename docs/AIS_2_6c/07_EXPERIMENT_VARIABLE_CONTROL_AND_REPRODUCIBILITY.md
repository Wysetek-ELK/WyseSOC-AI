# AIS 2.6c — Workstream 8: Experimental Variable Control & Reproducibility
**Document ID:** `07_EXPERIMENT_VARIABLE_CONTROL_AND_REPRODUCIBILITY.md`  
**Phase:** AIS 2.6c — Core LLM Intelligence Isolation, Prompt Bias Diagnosis & Human Ground Truth  
**Target Environment:** AWS GPU Server 2 (vLLM / Qwen2.5-7B-Instruct-AWQ)  
**Artifact Generated:** `docs/AIS_2_6c/EXPERIMENT_CONFIGURATION_MANIFEST.json`  

---

## 1. Experimental Control Principles

Scientific attribution requires holding all environmental and runtime variables constant between Mode A and Mode B so that any observed difference in verdict distribution is attributable solely to prompt framing.

### Controlled Parameters:
1. **Model Identity:** `Qwen/Qwen2.5-7B-Instruct-AWQ`
2. **Inference Engine:** vLLM v0.6+ on Server 2 (`http://13.204.214.64:8000/v1`)
3. **Hardware Platform:** AWS GPU instance (NVIDIA A10G 24GB VRAM)
4. **Sampling Temperature:** `0.0` (greedy decoding for deterministic classification)
5. **Top-P Sampling:** `1.0`
6. **Random Seed:** Fixed to `42`
7. **Runtime Context Limit:** `8,192` tokens
8. **Completion Reservation:** `768` tokens
9. **Target Input Budget:** `6,400` tokens
10. **Evidence Serialization:** Identical canonical JSON normalization across all modes.

---

## 2. Prevention of Dataset Contamination & Overfitting

The 20 incidents tested in Phase AIS 2.6c constitute an authentic **development diagnostic cohort**.
- **Rule 19 & Rule 24 Contract:** The prompt must never be tuned iteratively against these 20 incidents and the resulting score reported as "generalized model accuracy".
- **AIS 2.7 Holdout Isolation:** All incidents, rules, and variations slated for the future AIS 2.7 benchmark (100–300 unseen incidents) are strictly isolated and not accessed during Phase AIS 2.6c development.
- **Prompt Immutability:** No prompt alterations are permitted mid-cohort. Any revision generates a new versioned experiment with full provenance logging.

---

## 3. Deliverable Reference

- Experiment Configuration Manifest: [EXPERIMENT_CONFIGURATION_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/EXPERIMENT_CONFIGURATION_MANIFEST.json)
