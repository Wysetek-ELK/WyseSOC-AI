# 09 — Check 5 / Tier B/C Adjudication Fidelity Report

## 1. Tier B/C Verification Logic
Check 5 enforces that affirmative True Positive verdicts must satisfy strict rule-specific criteria:
- CrowdStrike: Corroborated unauthorized remote access tools (`UltraViewer`) or administrative utilities outside change tickets.
- Prisma SASE: Malicious file verdict requires verified threat intelligence, malware hash match, or sandbox execution analysis.

## 2. Adjudication Results
- CrowdStrike: 8/10 incidents validated as TRUE_POSITIVE.
- Prisma SASE: 10/10 incidents rejected/abstained as `INSUFFICIENT_EVIDENCE` / `TP_CRITERIA_UNSATISFIED` because files were benign static JavaScript assets (`review.es.system.js`, `jquery.knob.js`).
- Unsafe False Positives Emitted: 0 (0.0%).

