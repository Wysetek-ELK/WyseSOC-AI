# 10 — Rule Policy Contamination & Candidate Corrections

## AIS 2.7 Root Cause Findings

1. **Prisma SASE Production Policy (`ed7ff3c7` v1 on Server 1):** Mixed incompatible `Web Policy Violations with Same Source & Destination` instructions, `DO NOT use REQUIRES_ATTENTION`, and EDR process-execution criteria (`command line`, `PPID lineage`).
2. **Prisma Evidence Contract (`EC-PRISMA-SASE-V1`):** Required `process.file_name` (absent from Prisma SASE HTTP/proxy logs) instead of `file.name`.
3. **CrowdStrike Fallbacks:** Referenced `"valid digital signature"` even though FortiSIEM CrowdStrike logs omit signature attributes.

## AIS 2.8 Corrections

- Updated `_create_rule_contract("PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE")` in `empirical_benchmark_harness.py` to `EC-PRISMA-SASE-V2` requiring `file.name`, `network.source_ip`, `network.destination_ip`, `http.url`.
- Created isolated, non-promoted experimental candidate policies in `backend/app/services/ais28_policy_candidates.py` (`AIS28-CS-CANDIDATE-V1` and `AIS28-PRISMA-CANDIDATE-V1`, `status="EXPERIMENTAL_CANDIDATE"`). Approved DB production policies remain untouched.
