# 23 — Security, RBAC & Benchmark Isolation

- **Benchmark Isolation:** Admin-only RBAC enforced on `/api/ground-truth/ais27/*`, double-blind masking preserved, RAG/learning pollution blocked, prompt-injection delimiter escaping preserved.
- **UPLA Security Scan (`upla-20261126-035712-a04d56` / `upla-20261126-040528-b67309`):** Clean post-deploy check reported `security: PASS` with zero secrets in changed scope.
- **Identified Transport Blocker (`G10`):** Server 1 -> Server 2 currently uses HTTP on port `8000` (`http://<private>:8000/v1`); acceptable only over private VPC/VPN/encrypted tunnel and flagged as `BLOCKED` for unencrypted public internet paths.
