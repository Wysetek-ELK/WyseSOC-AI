# Report 04 — Target Rule Audit: Heavy TCP Host Scan On Fixed Port

## 1. Target Rule Identity

| Attribute | Authoritative Value |
| :--- | :--- |
| **Rule Name** | Heavy TCP Host Scan On Fixed Port |
| **Rule ID (UUID)** | `40498741-ee6b-4a71-9101-0d6d3f77154c` |
| **SIEM Rule Event Type** | `PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` |
| **Severity** | MEDIUM |
| **Detection Archetype** | `NETWORK_SCAN` |
| **Underlying SIEM Logic** | `COUNT(DISTINCT destIpAddr) >= 50` on fixed destination port within 180 seconds |

---

## 2. Policy Version Breakdown & Defect Analysis

### Version 1: APPROVED (Defective Baseline)
- **Status:** `APPROVED` (Active Baseline in original deployment)
- **Quality Status:** `REVIEW_REQUIRED` (Flagged for Revocation)
- **Content Defect:** Contained generic endpoint malware, binary execution, and process ancestry directives:
  - *"Inspect process.name, parent process, cmdline arguments, and powershell script execution."*
  - *"Check sha256 file hash on VirusTotal and inspect process ancestry."*
- **Root Cause:** A generic malware template was incorrectly approved for a network sweep rule.
- **Safety Action:** Flagged for administrative revocation via `POST /api/prompts/rule/{id}/version/{id}/revoke`. AI verdict execution is suspended (`ai_execution_suspended = True`).

### Version 2: ARCHIVED (Intermediate Iteration)
- **Status:** `ARCHIVED`
- **Quality Status:** `REWORK_REQUIRED`
- **Content Defect:** Contained flawed loopback assumptions and unverified port-sweep criteria.
- **Status:** Retained for audit; cannot be activated without re-validation.

### Version 3: DRAFT (Corrected Prototype)
- **Status:** `DRAFT` (Work-in-progress, unapproved)
- **Quality Status:** `GENERATED_DRAFT`
- **Content Correction:** Models the true `NETWORK_SCAN` attack semantics:
  - Models horizontal sweep threshold: `COUNT(DISTINCT destIpAddr) >= 50`.
  - Distinguishes internal authorized scanners (e.g. Qualys, Tenable, Rapid7) from unauthorized reconnaissance.
  - Requires destination host IP spread, fixed port telemetry, and CIDR scope analysis.
- **Governance Safeguard:** Remains in `DRAFT`. In accordance with prompt requirements, V3 is **never automatically approved or silently substituted**. It requires formal administrative review and quality gate sign-off.

---

## 3. Real-Time Eligibility State

Evaluating `PolicyEligibilityService.evaluate_eligibility` on rule `40498741-ee6b-4a71-9101-0d6d3f77154c`:
- **Is Eligible:** `False`
- **Governance Status:** `RULE_SUSPENDED`
- **Reason Code:** `RULE_AI_EXECUTION_SUSPENDED`
- **Explanation:** *"AI verdict execution is suspended for rule 'Heavy TCP Host Scan On Fixed Port' (Reason: Semantic mismatch detected: Approved V1 contains endpoint malware instructions instead of NETWORK_SCAN criteria. Revocation required.)."*
- **SIEM Telemetry Ingestion:** Functions normally and uninterrupted. Syslog and SIEM event polling are not impacted.

---
*Report Completed on 2026-11-15.*
