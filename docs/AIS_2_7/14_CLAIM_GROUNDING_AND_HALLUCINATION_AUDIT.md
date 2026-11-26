# AIS 2.7 — Workstream 14: Claim-Level Grounding & Hallucination Audit

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [CLAIM_LEVEL_GROUNDING_RESULTS.json](CLAIM_LEVEL_GROUNDING_RESULTS.json), [HALLUCINATION_REGISTER.json](HALLUCINATION_REGISTER.json)

## 1. Quantitative Grounding Audit

| Metric | Mode A (Neutral) | Mode B (Policy-Assisted) |
|---|---|---|
| Total `supporting_claims` emitted | `59` | `45` |
| Mechanically ID/field/value matched claims | `56/59` | `32/45` |
| Strictly semantically faithful claims | `34/59` | `24/45` |
| Mode B incidents validator-flagged `has_hallucinations=True` | N/A | `10/20` |
| Mode B incidents validator-flagged contradictions | N/A | `7/20` |
| Mode B incidents 100% free of mechanical or semantic hallucinations | N/A | **`0/20`** |

## 2. Verified Live Hallucination & Contradiction Typology (`91` Events Logged)

Observed examples reproduced verbatim from `inference_evidence/`:

1. **False Missing-Field Hallucination (`7/9` CrowdStrike UltraViewer TPs in Mode B):** Claimed `process.command_line is missing` despite `"C:\\Program Files (x86)\\UltraViewer\\UltraViewer_Service.exe"` being present in `canonical_evidence` (`132474210`, `132438483`, `132441815`, `132461358`, `132461368`, `132472498`, `132502453`).
2. **Path Mischaracterization (`132439932` Mode B):** Asserted `UltraViewer_Service.exe` executed from `"a writable temporary path"` while citing `\Device\HarddiskVolume3\Program Files (x86)\UltraViewer\UltraViewer_Service.exe`.
3. **Fabricated Signature Telemetry (`132527297`, `132461358`, `132461368`, `132502453` Mode B):** Asserted `"Binary not signed"` citing `process.name` (`UltraViewer_Service.exe`) or `file.digital_signature: "N/A"` when zero signature telemetry exists.
4. **Catastrophic RFC-1918 vs Public IP Hallucinations (Prisma SASE Mode B):**
   - `132596403`: Called public CloudFront destination IP `13.35.36.32` `"internal"`.
   - `132599330`: Called public AWS IP `3.109.76.166` `"a trusted internal IP address"`.
   - `132499023`: Claimed RFC-1918 internal IP `172.25.14.67` `"is not internal"`.
   - `132591888`: Called RFC-1918 client IP `172.25.6.208` `"likely a remote server"`.
5. **Invented Absence-of-Process Claims on Network Logs (`132499009`, `132578774`, `132599330`, `132596403` Mode B):** Fabricated `"No suspicious process execution detected"` citing empty `process.file_name` or mismatched `file.name`.
6. **Unsupported Benignity Rationalization (`20/20` Mode A & `9/10` Prisma Mode B):** Violated prompt ban on assuming filenames (`UltraViewer_Service.exe`, `jquery.knob.js`, `select2.min.js`) or CDN IPs establish benign authorization.
