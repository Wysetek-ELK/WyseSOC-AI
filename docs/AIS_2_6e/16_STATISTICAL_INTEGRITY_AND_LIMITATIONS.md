# AIS 2.6e — Statistical Integrity, Sample Limitations & Cohort Correlation

**Document Identifier:** `16_STATISTICAL_INTEGRITY_AND_LIMITATIONS.md`  
**Phase:** AIS 2.6e  
**Status:** COMPLETE / AUDITED  
**Subject:** Statistical Power & Sample Limitations of the 20-Incident Frozen Cohort  
**Related Manifests:** [STATISTICAL_LIMITATIONS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/STATISTICAL_LIMITATIONS.json), [COHORT_DUPLICATION_AUDIT.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/COHORT_DUPLICATION_AUDIT.json)

---

## 1. Executive Summary

A critical engineering responsibility is to clearly articulate what a benchmark **can** and **cannot** prove. Even when live GPU inference and human ground truth reviews are completed, the statistical design of the 20-incident frozen cohort imposes fundamental mathematical boundaries.

---

## 2. Statistical Sample Size & Confidence Intervals ($n = 20$)

With a cohort size of $n = 20$ incidents, statistical uncertainty is substantial. Using the Wilson score interval with continuity correction at a 95% confidence level ($\alpha = 0.05$):

| Observed Successes ($k / 20$) | Point Accuracy | 95% Wilson Confidence Interval | Practical Interpretation |
| :---: | :---: | :---: | :--- |
| **20 / 20** | 100.0% | **[83.9%, 100.0%]** | True population accuracy could be as low as 84%. |
| **18 / 20** | 90.0% | **[69.9%, 97.2%]** | Confidence interval spans nearly 28 percentage points. |
| **16 / 20** | 80.0% | **[58.4%, 91.9%]** | Statistically indistinguishable from a coin flip at the lower bound. |
| **14 / 20** | 70.0% | **[48.1%, 85.5%]** | Lower bound crosses the 50% random chance threshold. |

### Scientific Implication:
A 20-incident benchmark cannot prove that an LLM has "95% accuracy". It can only serve as a **qualitative triage smoke test** to detect catastrophic failure modes (e.g., pervasive hallucination, total model collapse, syntax corruption).

---

## 3. Correlated Cohort Clustering (Violation of i.i.d. Assumption)

Standard statistical inference assumes that sample observations are *independent and identically distributed* ($i.i.d.$). In the frozen 20-incident cohort, this assumption is violated:

```
[ 20 Frozen Cohort Incidents ]
  |
  +--- CrowdStrike Falcon Rule (10 Incidents)
  |      |
  |      +---> 9 Incidents: "UltraViewer_Service.exe" (Identical hash, path, and IOC update.ultraviewer.net)
  |      +---> 1 Incident:  "MEGAsync.exe"
  |
  +--- Prisma SASE Rule (10 Incidents)
         |
         +---> 3 Incidents: Originate from the identical source host (172.25.14.157)
         +---> 7 Incidents: Distinct web scripts / executables
```

### Analytical Finding:
- **45% of the entire cohort** (9 out of 20) represents the exact same executable (`UltraViewer_Service.exe`) evaluated on different workstations.
- If the model correctly identifies `UltraViewer` as an administrative tool in Mode B, it will score 9 correct answers in a cluster. This creates an **artificial clustering boost** that does not reflect generalizable SOC capability.
- Any reported accuracy metric must report both **Macro Accuracy** (weighted equally across distinct binaries) and **Micro Accuracy** (raw incident count).
