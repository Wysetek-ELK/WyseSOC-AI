# AIS 2.6e — Incident-Level Error Attribution & Root-Cause Taxonomy

**Document Identifier:** `17_INCIDENT_LEVEL_ERROR_ATTRIBUTION.md`  
**Phase:** AIS 2.6e  
**Status:** COMPLETE / SPECIFICATION  
**Subject:** Attribution Taxonomy for Model Verdict Errors  
**Related Manifests:** [ROOT_CAUSE_ATTRIBUTION_MATRIX.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/ROOT_CAUSE_ATTRIBUTION_MATRIX.json)

---

## 1. Executive Summary & Attribution Taxonomy

When an AI verdict disagrees with certified human ground truth or fails deterministic validation, attributing the error to the correct subsystem is essential to prevent counter-productive prompt engineering.

Errors must be attributed using a standardized 5-tier taxonomy:

```
+-------------------------------------------------------------------------------+
|                       VERDICT ERROR ROOT-CAUSE TAXONOMY                       |
+-------------------------------------------------------------------------------+
| 1. LLM_HALLUCINATION         | Model cites file, IP, or parent process absent  |
|                              | from the canonical raw log payload.           |
+------------------------------+------------------------------------------------+
| 2. LLM_REASONING_ERROR       | Model cites real entities but draws invalid    |
|                              | security deduction (e.g. calls UltraViewer RAT)|
+------------------------------+------------------------------------------------+
| 3. POLICY_AMBIGUITY          | Approved policy lacked clear exclusion rules   |
|                              | or contained contradictory directives.         |
+------------------------------+------------------------------------------------+
| 4. CONTEXT_COMPACTION_LOSS   | Critical corroborating log was trimmed during  |
|                              | token budget compression.                      |
+------------------------------+------------------------------------------------+
| 5. GROUND_TRUTH_DISAGREEMENT | Ambiguous evidence caused certified human      |
|                              | analysts themselves to diverge.                |
+-------------------------------------------------------------------------------+
```

---

## 2. Hallucination Detection Protocol

To detect `LLM_HALLUCINATION`:
1. Extract all entities cited in the model's `reasoning` and `cited_evidence` JSON fields.
2. Cross-reference each entity against the incident's `Canonical Evidence JSON`.
3. If an entity (e.g. IP, file path, command-line parameter) does not exist in the raw evidence, flag as `CONFIRMED_HALLUCINATION`.
4. Trigger Mode C validator escalation.

---

## 3. Current Phase Status

In Phase AIS 2.6e Stage A, zero live GPU calls have been dispatched; therefore, the `ROOT_CAUSE_ATTRIBUTION_MATRIX.json` contains zero empirical errors. The taxonomy stands ready for Stage B execution.
