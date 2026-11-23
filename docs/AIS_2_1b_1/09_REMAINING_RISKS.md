# AIS 2.1b.1 — Remaining Risks & Operational Limitations

**Project**: Verdictum AI — Agent Intelligence Studio (AIS)  
**Date**: November 23, 2026  

---

## 1. Technical & Operational Limitations

While AIS 2.1b.1 successfully achieves snapshot consistency, cross-tab population synchronization, and GUI acceptance, the engineering and SOC QA teams identify the following operational realities that must be managed:

### Risk 1: Single-Class Ground Truth Distribution (Zero Live True Positives)
- **Current Observation**: The live environment contains 65 cumulative historical reviews and 33 operational reviews, all verified as **False Positives** (0 TP / 65 FP).
- **Cause**: The rule detects heavy TCP host scanning on fixed ports. In this customer enterprise network, all recorded scan occurrences originate from scheduled internal vulnerability scanners (e.g., Nessus, Qualys) and network health monitors.
- **Impact**: Without real adversarial port scans generating True Positive verdicts, empirical sensitivity (Recall) and balanced F1-score cannot be measured from live traffic alone.
- **Mitigation for AIS 2.2**: Controlled red-team simulation or sandbox synthetic traffic injection will be required to validate TP detection capabilities without contaminating production ground truth.

### Risk 2: 100% Abstention Rate Under Policy v7
- **Current Observation**: Policy v7 produced 0 decisive predictions across 33 evaluated incidents (100% abstention).
- **Cause**: Policy v7 includes conservative confidence thresholds to prevent speculative False Positives on complex network alerts.
- **Impact**: While abstention safely prevents hallucinated verdicts, decision coverage is currently 0%.
- **Mitigation for AIS 2.2**: Draft Policy v8 features calibrated prompt guidelines designed to increase decision coverage on known vulnerability scanner signatures while maintaining strict abstention on ambiguous patterns.

### Risk 3: Client Cache Staleness During Extended Idle Sessions
- **Current Observation**: React Query is configured to cache evaluation tracking snapshots for 30 seconds (`staleTime: 30000`).
- **Cause**: If an analyst leaves the browser tab open for hours while hundreds of new alerts ingest in the background, the UI will reflect the snapshot captured at the last user interaction or tab switch.
- **Mitigation**: The UI provides an explicit "Refresh" button and revalidates queries whenever the analyst changes tabs, alters scope selectors, or submits a review.

### Risk 4: Long-Running Large-Scale Batch Evaluations
- **Current Observation**: Evaluating hundreds of incidents against the local AWQ model on Server 2 requires approximately 1.2 to 2.5 seconds per incident.
- **Cause**: GPU inference queuing and context token length.
- **Mitigation**: AIS 2.1b/2.1b.1 handles evaluations asynchronously in background worker queues, displaying "In-Flight" and "Queued" statuses without blocking the user interface.
