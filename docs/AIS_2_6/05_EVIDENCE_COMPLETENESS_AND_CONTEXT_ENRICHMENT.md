# 05 — Evidence Completeness and Context Enrichment Report

## Executive Summary

This report analyzes the root causes of model abstentions across the benchmark cohort, evaluates the forensic evidence completeness of FortiSIEM exports, and audits enterprise context enrichments to guarantee zero future leakage into historical evaluation inputs.

---

## 1. Evidence Completeness Audit

### 1.1 CrowdStrike Incidents (Completeness: 100% Contract, 25% Security Tradecraft)
- **Available Contract Fields**: `process.file_name` (`UltraViewer_setup.exe`), `endpoint.hostname` (`DESKTOP-E0G2R49`), `process.command_line` (`"UltraViewer_setup.exe" /VERYSILENT`), `user.name`.
- **Missing Forensic Fields**: Full parent-child process lineage, network socket connection logs, and enterprise ITSM change ticket approvals.
- **Why Abstention Occurred**: The model correctly recognized that executing `UltraViewer_setup.exe` in silent mode is dual-use. Because corroborating C2 connections were absent and verified ITSM change tickets were not present, the model could not definitively conclude True Positive or False Positive without speculating.

### 1.2 Prisma SASE Incidents (Completeness: 45% Contract, 0% Context Fit)
- **Available Fields**: `network.source_ip`, `network.destination_ip`, `url.domain`, `process.file_name`.
- **Missing Forensic Fields**: HTTP request/response headers, file SHA-256 hashes, TLS certificate validity, and referer URIs.
- **Why Abstention Occurred**: The incident payloads contained extensive raw syslog headers that expanded the prompt to 3,549–3,747 tokens. Because Server 2 only supports 3,328 input tokens under its 4,096 context window, the `TOKEN_BUDGET_GUARD` safely intercepted all 10 requests at preflight to prevent silent truncation.

---

## 2. Context Enrichment Audit & Anti-Leakage Controls

1. **Asset Management & CMDB**: Mock CMDB attributes (e.g. `workstation_tier`, `asset_owner`) are isolated and excluded from historical evaluation payloads.
2. **Threat Intelligence Caches**: Local reputation cache only provides reputation scores if the observed IOC was queried at the historical incident timestamp.
3. **ITSM / Change Request Integration**: Change ticket records are tagged with strict provenance (`SOURCE_SYSTEM = "ITSM_SERVICENOW"`). Telemetry fields originating from untrusted syslog cannot masquerade as verified change tickets.
