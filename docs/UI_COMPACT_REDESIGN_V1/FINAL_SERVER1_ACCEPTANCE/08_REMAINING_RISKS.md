# Verdictum AI — Final Release Closure: Remaining Risks & Operational Governance (08_REMAINING_RISKS.md)

**Generated:** 2026-11-17T09:47:00+05:30  
**Target Environment:** Verdictum AI Server 1 (`remote-server`)  
**Status:** **DOCUMENTED & CONTROLLED**

---

## 1. Risk Register & Mitigations

| Risk ID | Description | Severity | Likelihood | Built-in Mitigation & Current Operational State |
|---|---|---|---|---|
| **RSK-01** | **Server 2 Cortex GPU Offline:** The GPU inference cluster (`http://<server-2-cortex>:8000`) is currently powered off or unreachable. | Medium | High | **Mitigated:** Circuit breaker is active and `ALLOW_MOCK_FALLBACK: False`. System safely reports `AI Execution: Offline`, queues non-urgent tasks in Redis/Celery, and refuses to fabricate fake LLM responses. |
| **RSK-02** | **Candidate Policy Approval Blocking:** Candidate v3 policy for Heavy TCP Host Scan cannot be promoted to production because it has 0/30 verified analyst reviews. | Low | Guaranteed | **Intended Governance Control:** Candidate v3 correctly scores 78.0/100 and fails G1 and G8. Policy promotion is blocked by design until human SOC analysts submit 30 ground-truth reviews. Approved historical baseline v1 remains safely assigned. |
| **RSK-03** | **FortiSIEM Upstream Sync Latency:** Live synchronization with FortiSIEM cluster (`https://<fortisiem-cluster>`) requires VPN/tunnel routing. | Low | Low | **Mitigated:** Synchronized rules are cached in PostgreSQL `rules` table with full incident count snapshots (e.g. 69 incidents cached for Heavy TCP). Platform functions offline without degradation. |
| **RSK-04** | **Browser Cache Invalidation:** Analysts who previously loaded older UI builds may retain cached JavaScript chunks. | Very Low | Medium | **Mitigated:** Cache-busting headers configured on Nginx; Next.js asset hashing ensures new deployment chunks (`5a0f646`) load cleanly. |

---

## 2. Operational Recommendations

1. **Server 2 Power-On:** When GPU cluster is online, restart `ai-verdict-backend.service` to re-probe health and open slots.
2. **Supervised Learning Pilot:** Direct SOC L1/L2 analysts to review 30 incidents in AI Triage Workbench to accumulate ground-truth Controls for Heavy TCP Host Scan.
3. **Database Maintenance:** Schedule automated `VACUUM ANALYZE` weekly; WAL archiving is verified healthy.
