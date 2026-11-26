# 07 — Deterministic Evidence Intelligence Engine

Implemented `EvidenceIntelligenceEngine.enrich_incident_evidence()` in `backend/app/services/evidence_intelligence_service.py` with strictly factual, non-verdict-biased security context:

1. **`network_classification`:** Uses Python stdlib `ipaddress` to classify source, destination, endpoint, and NAT IPs (`RFC1918_PRIVATE`, `LOOPBACK`, `CGNAT_100_64`, `LINK_LOCAL`, `DOCUMENTATION_TEST_NET`, `PUBLIC_ROUTABLE`), identifies port services (`443 HTTPS`, `22 SSH`, `3389 RDP`, `445 SMB`, etc.), and sets `nat_or_proxy_translation_present`.
2. **`endpoint_process_classification`:** Classifies binary paths into explicit zones (`PROGRAM_FILES`, `WINDOWS_SYSTEM_DIR`, `WRITABLE_TEMP_DIR`, `USER_PROFILE_OR_DOWNLOADS`, `PROGRAMDATA`, `UNIX_SYSTEM_BIN`), separates `execution_evidence_present` vs `download_only_evidence_present`, and explicitly sets `digital_signature_status = "NOT_REPORTED_IN_TELEMETRY"` when absent.
3. **`file_and_web_context`:** Extracts normalized MD5/SHA1/SHA256 digests, URL, web category, application name, and extension class (`EXECUTABLE_OR_SCRIPT`, `WEB_STATIC_OR_ASSET`, `ARCHIVE`, `DOCUMENT`).
4. **`telemetry_field_presence`:** Lists populated vs genuinely absent forensic fields so models do not claim observed telemetry is missing.
