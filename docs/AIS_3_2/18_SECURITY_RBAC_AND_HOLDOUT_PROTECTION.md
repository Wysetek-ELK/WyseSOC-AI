# AIS 3.2 — 18: Security, RBAC & Holdout Protection

- Unauthenticated `/api/ais32/*` access blocked (`401` verified live on `http://172.26.41.240/api/ais32/overview` and in HTTP test client).
- Analyst role blocked (`403`) from Admin contract edits, org-context approvals, dev cohort creation, and benchmark execution; cross-tenant org-context reads/writes blocked (`403`).
- UPLA `release` security scan: `0` new secret or static security findings, `npm-audit` `PASS` (`pip-audit` `NOT VERIFIED`).
