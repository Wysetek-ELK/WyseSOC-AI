# 23 — Manual Analyst Review & Certification Guide

## Step-by-Step Operator Procedure
1. Sign in at `http://172.26.41.240/login` using a reviewer/administrator account with human-review permission.
2. Ensure **Blind Review: ON** is active in the top bar (enforced automatically in certification mode).
3. In the left navigation under **SOC OPERATIONS**, open **Human Review Queue** (`/human-review-queue`).
4. Click the **Ground Truth Certification (AIS 2.6e)** tab.
5. Select the target cohort from the cohort dropdown:
   - `AIS_2_6E_FROZEN_20 (20)` to complete second-reviewer GT-3 certification (currently `0/20 GT-3`, `20/20 GT-2 Single`).
   - `AIS_3_0_INDEPENDENT_HOLDOUT_100 (100)` to perform blinded dual-reviewer GT-3 certification of the fresh holdout (currently `0/100 GT-3`, `100/100 GT0_UNREVIEWED`).
6. Click **Inspect** / **Certify** on an unassigned/unreviewed incident. Do **not** view historical AI verdicts prior to submitting your independent verdict.
7. Review original FortiSIEM incident details, raw event logs, and the complete triggered rule definition (`PH_RULE_*`).
8. Select **TRUE_POSITIVE**, **FALSE_POSITIVE**, or **INCONCLUSIVE**, enter concise factual evidence citations (event IDs, fields, exact observed values), and submit + lock your review.
9. Monitor the header metrics (**GT-2 Single**, **GT-3 Certified**, **Conflicts**, **My Locked**) and adjudicate any reviewer conflicts via the conflict workflow before AIS 3.0 execution.
