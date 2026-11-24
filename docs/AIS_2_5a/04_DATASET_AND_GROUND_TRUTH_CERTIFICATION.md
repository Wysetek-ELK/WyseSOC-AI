# 04 — Dataset and Ground-Truth Certification Audit

## 1. Authentic Telemetry Provenance

All 20 benchmark incidents were loaded from `fixtures/Incident json.zip` (FortiSIEM export):
- Unique Files: 20
- Unique SHA-256 Hashes: 20
- Distinct Event Timestamps: 20
- Exact Byte-for-Byte Duplicates: **0**

---

## 2. Telemetry Clustering vs. Deduplication

The clustering algorithm in `EmpiricalBenchmarkHarness` was audited and corrected. Previously, records sharing rule name, host name, and event count were dropped as duplicate records.

The corrected clustering distinguishes:
1. **Exact Duplicate Records (0 incidents)**: Identical payload hashes and event identities.
2. **Related Security Event Clusters (7 incidents across 3 clusters)**:
   - *Cluster 1*: UltraViewer Remote Tool rollout across different endpoints (`132438483`, `132439932`, `132441815`, `132461358`, `132461368`).
   - *Cluster 2*: Recurring CrowdStrike signature on host `TSI-IT-002-95` (`132501348`, `132527297`).
   - *Cluster 3*: Web asset bundle download from internal host `indonis` (`132599145`, `132599146`, `132599330`).
3. **Independent Security Incidents (13 incidents)**: Distinct applications, hosts, destinations, or event types.

---

## 3. Ground Truth Verification & Forensic Provenance

An audit of the raw SIEM export revealed:
- `clearedUser`: `""` (Empty string for all 20 incidents)
- Historical Resolution Notes: Free-text comments ("kill process", "Mail sent", "Case raised", "Closed as False Positive")
- Independent Certified Reviewer: **None**

### Verdict Re-Classification:
- `132474210`: Historically resolved as True Positive. Telemetry shows dual-use process terminated by local script. Classified as `PROVISIONAL_UNVERIFIED`.
- `132499009`: Historically closed as False Positive (SurveySensum JavaScript widget download). Classified as `PROVISIONAL_UNVERIFIED`.
- All remaining 18 incidents: Classified as `PROVISIONAL_UNVERIFIED`.

In accordance with strict empirical standards, natural historical SIEM records lack independent cryptographic certification; their labels must not be treated as ground-truth gold standards.
