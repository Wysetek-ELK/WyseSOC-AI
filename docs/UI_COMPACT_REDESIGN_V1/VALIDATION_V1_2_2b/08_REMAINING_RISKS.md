# Verdictum AI — Validation V1.2.2b
## 08: Remaining Operational Risks and Mitigation Roadmap

### 1. Risk Analysis Matrix

| # | Risk Area | Severity | Description | Current Safe State | Production Mitigation Roadmap |
|---|-----------|----------|-------------|--------------------|-------------------------------|
| 1 | **Server 2 GPU LLM Offline** | Medium | Local GPU LLM on Verdictum AI Server 2 is offline during local test runs. | UI accurately displays `AI Execution: Offline` (red pulsing indicator). Zero synthetic fabrication or simulated hallucinations. | Upon remote deployment to Server 1, configure upstream HTTPS connectivity to Server 2 vLLM/Ollama host with automated health checks. |
| 2 | **Dynamic Telemetry Rule Discovery Name Overlaps** | Low | New incident event types create automated rule records which appear in dropdown selection filters. | Multi-tenant isolation at incident level prevents cross-tenant alert row exposure. Search results strictly return 0 items. | Enforce customer tenant tagging on automatically synchronized rule profiles during FortiSIEM background polling. |
| 3 | **Database Migration for Existing Users** | Low | Production databases on Server 1 must receive the `customer` column on `users` table without downtime. | Self-healing startup migration in `backend/app/main.py` executes `ALTER TABLE users ADD COLUMN customer VARCHAR(128)` automatically. | Run dry-run migration script on Server 1 staging replica prior to live deployment. |
| 4 | **Analyst Blind Review Cache Invalidation** | Low | Client browsers could potentially retain cached incident detail in HTTP cache headers. | Cache-Control headers on incident and review endpoints are set to `no-store, no-cache, must-revalidate`. | Maintain existing no-cache headers on all reverse proxies (Nginx/Caddy). |

---

### 2. Safeguards Enforced by RepoDeploy Governor
- **Zero Direct Pushes:** All git operations are hard-gated by the RepoDeploy Governor PreToolUse hook.
- **Zero Real IP Leakage:** Real server IPs are completely redacted; environment references use documentation placeholders or `${SERVER_1_HOST}`.
- **Two-Stage Approval Gating:** Gate 1 (GitHub update) requires explicit user authorization. Gate 2 (Remote deployment) is strictly withheld until explicit subsequent mandate.
