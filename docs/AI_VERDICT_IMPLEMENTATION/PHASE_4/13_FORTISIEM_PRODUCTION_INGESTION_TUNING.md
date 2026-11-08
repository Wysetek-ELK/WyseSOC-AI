# Report 13: Fortinet FortiSIEM Production Ingestion Tuning

## 1. Ingestion Modalities in Enterprise SOC

In production enterprise deployments, Fortinet FortiSIEM streams security alerts into AI Verdict through two primary mechanisms:
1. **Push Mechanism (FortiSIEM Notification Webhooks / JSON Dispatch):**
   FortiSIEM incident notification scripts emit HTTP POST requests containing raw incident payloads to `/api/fortisiem/webhook` or `/api/incidents/ingest`.
2. **Pull Mechanism (Scheduled REST Polling):**
   `FortiSIEMContinuousSyncService` polls FortiSIEM's REST API at configurable intervals (`settings.FORTISIEM_POLL_INTERVAL_SECONDS`, default: 180s) to retrieve unresolved incidents.

---

## 2. Ingestion Pipeline & De-duplication

To handle bursts of alerts during major security events, the ingestion pipeline incorporates:
- **Zip-Bomb & Ingestion Guards:** Protects file uploads with `UPLOAD_MAX_FILE_SIZE` (50MB), uncompressed size limits (250MB), and compression ratio limits (max 50:1).
- **Incident Deduplication:** Checks uniqueness on `incident_id` using database indexing (`Incident.incident_id.unique()`). Duplicate webhooks are acknowledged idempotently without creating duplicate rows or repeated LLM evaluations.
- **Durable Queue Handoff:** Incoming incidents are committed to PostgreSQL and dispatched to Celery's `live_triage` queue, returning an immediate HTTP 202/200 acknowledgement to FortiSIEM within 100ms.

---

## 3. Telemetry Field Normalization for FortiSIEM Records

FortiSIEM events vary substantially depending on log collector types (Syslog, Windows Event Logs, NetFlow, AWS CloudTrail). The `EvidenceNormalizationService` extracts canonical fields:

| Canonical Key | Primary FortiSIEM Source Attributes | Fallback Source Attributes |
| :--- | :--- | :--- |
| `source_ip` | `srcIpAddr`, `src_ip`, `src` | `reporting_ip`, `devIpAddr` |
| `dest_ip` | `destIpAddr`, `dst_ip`, `dst` | `collectorIp` |
| `source_user` | `user`, `srcUser`, `actor` | `account`, `logonUser` |
| `process_name` | `procName`, `process`, `app` | `fileName`, `serviceName` |
| `event_action` | `action`, `eventAction`, `status` | `raw_payload.event_type` |

---

## 4. Operational Configuration Tuning

In `/opt/ai-verdict/backend/.env`:
```ini
FORTISIEM_HOST="https://fortisiem.internal.corp:443"
FORTISIEM_USERNAME="svc_aiverdict_read"
FORTISIEM_PASSWORD="CryptographicallyStrongPassword123!"
FORTISIEM_VERIFY_SSL="true"
FORTISIEM_TIMEOUT="25.0"
FORTISIEM_AUTO_POLL_ENABLED="true"
FORTISIEM_POLL_INTERVAL_SECONDS="120"
FORTISIEM_AUTO_AI_VERDICT="true"
FORTISIEM_MOCK_FALLBACK="false"
```

### Safety Note:
In production, `FORTISIEM_MOCK_FALLBACK` is strictly enforced to `false`. If the FortiSIEM appliance is unreachable, the sync service logs an alert and retries during the next interval rather than fabricating synthetic security events.

