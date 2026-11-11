# Phase 8.2 — Stage I FortiSIEM Integration Validation

**Evidence Source:** `docs/phase8.2/evidence/fortisiem/stage_i_fortisiem_probe.json`  
**Live Status:** `BLOCKED` (`FSI-01-C3` = `NOT_TESTED`)

## Connectivity & Configuration Audit

- **Configured Host (`FORTISIEM_HOST`):** `https://<CONFIGURED_FORTISIEM_HOST>`
- **Live TCP Socket Probe (`443`):** `reachable: false`, error `gaierror` (internal hostname unresolvable from local staging workstation).
- **Relevant Configuration Flags (`backend/.env`):**
  - `FORTISIEM_VERIFY_SSL`: `"false"` (acceptable only for isolated local mock testing; remediation required for staging/production supervisor integration to set `true` with trusted CA cert).
  - `FORTISIEM_MOCK_FALLBACK`: `"true"` (must be `false` in staging/production live integration runs).
  - `FORTISIEM_AUTO_POLL_ENABLED`: `"false"`
- **Unit & Parser Verification:** FortiSIEM incident/event ingestion models, attribute sanitization (`model_payload_allowlist.py`), and historical ground-truth separation passed inside the offline backend test suite, while live authenticated FortiSIEM REST polling (`FSI-01-C3`) remains blocked until network connectivity to a staging supervisor is available.
