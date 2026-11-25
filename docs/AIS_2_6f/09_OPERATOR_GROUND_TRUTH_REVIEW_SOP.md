# 09 — Operator Ground Truth Review SOP

1. Sign in at `http://172.26.41.240/login` and navigate to **Human Review Queue** (`/human-review-queue`).
2. Select tab **Ground Truth Certification (AIS 2.6e)**.
3. Filter by **Priority 5 Pilot** first and click **Certify** on each incident (`132474210`, `132596403`, `132599145`, `132438483`, `132591888`).
4. Review the **Triggered FortiSIEM Rule Definition**, search **Original Raw Security Logs**, check **Normalized Canonical Evidence**, attach any verified change/host context if needed, classify `TRUE_POSITIVE` / `FALSE_POSITIVE` / `INCONCLUSIVE`, cite evidence IDs, check all 3 attestations, and click **Submit & Lock Independent Review**.
5. Have a **second distinct reviewer** sign in and complete blind certification for each item.
6. If `CONFLICT_PENDING_ADJUDICATION` occurs, an uninvolved Senior Analyst / Administrator issues binding adjudication.
