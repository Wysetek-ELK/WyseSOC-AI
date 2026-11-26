# 04 — Authentication & Secure Transport Verification

- **Server 1 Admin Authentication**: Benchmark endpoints enforce `require_admin` RBAC; unauthenticated probes to `/run`, `/runtime-verify`, `/tokenize-verify`, `/smoke-test`, `/api/llm/config`, and `/api/system/servers/live` all failed closed with **HTTP 401**.
- **Server 1 -> Server 2 Transport Probes**:
  - Private VPC probe `172.29.164.10:8000`: Timed out from Server 1.
  - TLS `:443`: Timed out; TLS `:8000`: `SSL: WRONG_VERSION_NUMBER`.
  - Active UAT Endpoint: `http://13.204.214.64:8000/v1` (plaintext HTTP; explicitly authorized by operator for UAT execution).
- **Production Security Gate (`G10`)**: Remains **BLOCKED** for production deployment until private VPC security-group routing or TLS encryption protects customer event payloads in transit.
