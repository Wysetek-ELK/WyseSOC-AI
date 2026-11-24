# AIS 2.6a — Report 07: Evaluation Layer Separation Analysis

## 1. Architectural Three-Layer Model
To prevent self-referential bias and evidence leakage, the evaluation architecture enforces strict decoupling across three distinct layers:

```
[Layer A: Raw Model Inference]
       │  (Generates proposed verdict, raw confidence, and reasoning)
       ▼
[Layer B: Evidence & Preflight Validator]
       │  (Enforces rule criteria, evidence grounding, ticket authenticity)
       ▼
[Layer C: Certified Ground Truth Certification]
          (Requires independent multi-analyst consensus ground truth)
```

---

## 2. Empirical Performance by Layer

| Layer | Function | Decisive Count | Decisive Rate | Abstentions |
|---|---|---:|---:|---:|
| **Layer A** | Raw Model Proposals | 14 / 20 | 70.0% | 6 / 20 (30.0%) |
| **Layer B** | Evidence & Rule Validation | 13 / 20 | 65.0% | 7 / 20 (35.0%) |
| **Layer C** | Certified Ground Truth | 0 / 20 | 0.0% | 20 / 20 (100.0%) |

---

## 3. Layer Separation Case Studies
1. **Layer A -> Layer B Interception (Incident 132501348):**
   - Layer A proposed `TRUE_POSITIVE` with 85% confidence, citing potential Falcon COM object tampering.
   - Layer B evaluated the telemetry and determined that only 2 sparse events existed without definitive process command line or execution proof.
   - Layer B downgraded the proposal to `REQUIRES_ATTENTION` (`TP_CRITERIA_UNSATISFIED`).
2. **Layer B -> Layer C Distinction:**
   - 13 verdicts achieved Layer B validation (8 TP, 5 FP).
   - Zero verdicts achieved Layer C certification because zero incidents possess multi-analyst consensus certification.
   - The UI and metrics report this honestly rather than falsely claiming 100% certified accuracy.
