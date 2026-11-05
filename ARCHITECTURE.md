# AI Verdict — System Architecture Specification

## 1. Architectural Philosophy & Governance

AI Verdict is designed under a two-server enterprise topology:
- **Server 1 — Application Server**: Hosts the Next.js frontend, Python FastAPI backend, PostgreSQL relational database, and secure ingestion pipelines.
- **Server 2 — Inference Server (Future)**: Hosts the local LLM running on dedicated GPU infrastructure (AWS `g4dn.2xlarge`) served via a private OpenAI-compatible API.

During Phase 1, **Server 1 is developed exclusively**. No model runtime, external API, or GPU dependency exists. All system metrics reflect genuine database records.

---

## 2. Server 1 Component Diagram

```
+-----------------------------------------------------------------------------------+
|                                  SERVER 1                                         |
|                                                                                   |
|  +-----------------------------------------------------------------------------+  |
|  |                            Nginx Reverse Proxy                              |  |
|  |             - Port 80 (Redirect) / Port 443 (TLS 1.3 / HTTP/2)              |  |
|  |             - Security Headers / 50MB Max Payload / Gzip                     |  |
|  +-----------------------+----------------------------------+------------------+  |
|                          |                                  |                     |
|                /api/*    |                        /*        |                     |
|                          v                                  v                     |
|  +-------------------------------------+   +-----------------------------------+  |
|  |       FastAPI Application           |   |       Next.js 15+ Frontend        |  |
|  |  - Auth & RBAC (Argon2 / JWT)       |   |  - App Router / TypeScript        |  |
|  |  - Ingestion & ZipGuard Engine      |   |  - Tailwind CSS / Dark SOC Theme  |  |
|  |  - SIEM Text Rule Parser            |   |  - Blind Review Mode Controller   |  |
|  |  - Incident & Rule Services         |   |  - Operational Views (P1)         |  |
|  |  - Ground Truth Isolation Layer     |   |  - Phase 2/3 Feature Placeholders |  |
|  +------------------+------------------+   +-----------------------------------+  |
|                     |                                                             |
|                     | SQLAlchemy 2.x Async Engine                                 |
|                     v                                                             |
|  +-----------------------------------------------------------------------------+  |
|  |                          PostgreSQL 16+ Database                            |  |
|  |  - users / audit_logs                                                       |  |
|  |  - rules (SIEM rule catalog & metadata)                                     |  |
|  |  - import_jobs (Ingestion logs)                                             |  |
|  |  - incidents (Normalized telemetry & searchable fields)                     |  |
|  |  - incident_events (Raw security event telemetry)                           |  |
|  |  - historical_ground_truth (ISOLATED resolution data)                        |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 3. Ground-Truth Isolation & Model Allowlist Architecture

A primary architectural requirement is preventing historical investigation conclusions, analyst notes, or closure metadata from leaking into future LLM analysis payloads.

### Storage Isolation
- Normalized incident telemetry is stored in the `incidents` table and `incident_events` table.
- Resolution, cleared reasons, analyst comments, and closure timestamps are isolated into the `historical_ground_truth` table with a unique foreign key constraint.

### Whitelist Payload Construction (`build_model_facing_payload`)
Before any incident data can be sent to future model services, it passes through the strict allowlist filter:
```
Raw Ingested Data
       |
       v
+---------------------------------------------------------------------+
|                  Ground Truth Isolation Filter                      |
|                                                                     |
|  FORBIDDEN FIELDS (Dropped & Blocked):                              |
|  - resolution, clearedReason, comments, clearedUser, clearedTime    |
|  - resolvedAt, mttr, cmsClearUser, is_ml_generated                  |
|                                                                     |
|  ALLOWED FIELDS (Permitted for Investigation):                      |
|  - incident_id, event_type, title, description, detail, severity    |
|  - category, subcategory, source_ip, reporting_device               |
|  - reporting_ip, first_seen_epoch, last_seen_epoch, created_at_epoch|
|  - raw_events[].attributes (sanitized of closure keys)              |
+---------------------------------------------------------------------+
       |
       v
ModelFacingIncidentPayload (Strict Allowlist Schema)
```

---

## 4. Ingestion & Security Defenses

The ingestion pipeline protects against common archive and file-based vulnerabilities:

1. **Zip Slip / Path Traversal Defense (`ZipGuard`)**:
   - Rejects any archive entry containing `..`, absolute root paths, or drive specifiers.
   - Normalizes path structures before extraction.
2. **Decompression Bomb Defense**:
   - Caps individual uncompressed file size to 25 MB.
   - Caps cumulative uncompressed archive size to 250 MB.
   - Rejects compression ratios exceeding 50:1.
   - Enforces a maximum archive entry count of 2,000 files.
3. **Resilient Vendor Parsing**:
   - Stores raw incident JSON unmodified in `raw_payload` (JSONB) to preserve unknown vendor-specific fields.
   - Retains nested event attributes dynamically within `incident_events.attributes`.
   - Normalizes core SIEM fields (timestamps, severity, status, source IP, device).

---

## 5. Future Inference Server Interface (Phase 3+)

When Server 2 (AWS `g4dn.2xlarge`) is integrated in future stages, it will connect using a provider-independent contract:

```python
class ModelProvider(ABC):
    @abstractmethod
    async def get_health(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        pass

    @abstractmethod
    async def analyze_incident(self, payload: ModelFacingIncidentPayload) -> StructuredModelVerdict:
        pass
```

The future pipeline will be:
`SIEM Incident -> Normalization -> Allowlist Filter -> ModelProvider -> Structured Verdict -> Policy Validation -> Analyst Review -> Feedback Store -> Evaluation`.
