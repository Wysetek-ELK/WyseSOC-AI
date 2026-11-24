# 03 — Dataset Provenance and Certification Status

## 1. Historical Dataset Inventory
- Ingested Cohort: 20 historical FortiSIEM incidents from `fixtures/Incident json.zip`.
- Rule Coverage:
  - `PH_RULE_CS_SUSPICIOUS_ACTIVITY` (10 incidents)
  - `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE` (10 incidents)
- Ground Truth Certification Status:
  - **Certified Ground Truth Count: 0**
  - **Uncertified Operational Incidents: 20**
  - Operational shift logs represent unverified 1-analyst operational notes ('Mail sent', 'Escalated to L2').
  - Certified Ground Truth requires consensus from 3 independent human experts (Senior SOC Analyst, Detection Engineer, FortiSIEM Specialist).
  - Selective Accuracy is classified as **NOT_MEASURED** pending human panel certification.

