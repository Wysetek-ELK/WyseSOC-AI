# AIS 2.7 — Workstream 23: Remaining Blockers, Corrective Actions & Next Operator Steps

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [REMAINING_BLOCKERS.json](REMAINING_BLOCKERS.json), [RECOMMENDED_CORRECTIVE_ACTIONS.json](RECOMMENDED_CORRECTIVE_ACTIONS.json), [NEXT_OPERATOR_ACTIONS.json](NEXT_OPERATOR_ACTIONS.json)

## 1. Remaining Blockers

- **BLK-01 (CRITICAL):** **Deployed LLM Intelligence Failure** — Qwen/Qwen2.5-7B-Instruct-AWQ scored 5.0% (Mode A) / 10.0% (Mode B) 3-class accuracy and hallucinated facts across both CrowdStrike and Prisma SASE.
- **BLK-02 (HIGH):** **GT-3 Certification Not Yet Complete** — Current cohort has 20/20 locked GT-2 single-reviewer labels (0 GT-3 dual-certified), with historical exposure risk on all 20 items.
- **BLK-03 (HIGH):** **Prisma SASE Policy Template Mismatch (ed7ff3c7 v1)** — Server 1 approved Prisma SASE policy references EDR/loopback criteria and instructs against REQUIRES_ATTENTION, contributing to 0/10 Prisma abstentions in Mode B.
- **BLK-04 (MEDIUM):** **External Hash & IP Enrichment Missing** — Human analyst had external hash reputation (MEGAsync clean on 132501348) unavailable to LLM prompts.
- **BLK-05 (LOW):** **EC2 Hardware / Billing Telemetry Unverified via Server 1 HTTP** — gpu_telemetry_verified=false on Server 1 /api/health; GPU model/VRAM (historically AWS EC2 g5.xlarge A10G) could not be directly polled from Server 1 HTTP telemetry.

## 2. Prioritized Corrective Actions

- **P0 [MODEL_REPLACEMENT]:** Evaluate replacing Qwen/Qwen2.5-7B-Instruct-AWQ with a stronger unquantized/larger model (e.g. 14B/32B Instruct FP16/BF16 on adequate GPU VRAM) using the identical AIS 2.7 3-mode harness.
- **P0 [POLICY_REMEDIATION]:** Replace Prisma SASE Approved Policy ed7ff3c7 v1 (currently using an EDR/internal-loopback template) with a proxy/file-transfer policy permitting REQUIRES_ATTENTION when hash/URL/download confirmation is absent.
- **P1 [ENRICHMENT_PIPELINE]:** Add deterministic VirusTotal/hash reputation and RFC1918/CDN/ASN IP-classification enrichment into canonical_evidence before LLM inference (resolving 132501348 MEGAsync hash dependency and stopping IP hallucination).
- **P1 [VALIDATOR_HARDENING]:** Extend Deterministic Validator to catch prose semantic contradictions inside claim_text/reason (e.g., calling Program Files 'writable temporary path', calling public IPs 'internal', calling RFC1918 'not internal').
- **P1 [GROUND_TRUTH_GT3]:** Have independent Reviewer #2 complete GT-3 dual-reviewer certification on Server 1 and remediate minor GT-2 metadata inconsistencies (e.g. 132474210 authorization_context).
- **P2 [INFRASTRUCTURE_TIMEOUT]:** Raise Server 1 nginx proxy_read_timeout for benchmark/batch endpoints (currently 120s caused single HTTP 504 on 132499009 when Mode A+B ran combined) or standardize per-mode execution.

## 3. Immediate Next Operator Actions

1. MANUALLY SHUT DOWN OR STOP GPU SERVER 2 (http://13.204.214.64:8000/v1) if no further inference testing is planned immediately, to avoid ongoing EC2 GPU charges (left running per explicit Checkpoint A authorization).
2. Review AIS 2.7 final findings in docs/AIS_2_7/24_FINAL_ACCEPTANCE_AND_EXECUTIVE_SUMMARY.md (and EMPIRICAL_METRICS.json) before deciding candidate replacement model for GPU Server 2.
3. Assign independent Reviewer #2 in Server 1 Ground Truth Certification UI to upgrade frozen 20 cohort items from GT-2 to GT-3.
4. Fix Prisma SASE Approved Policy (ed7ff3c7) on Server 1 before any replacement-model benchmark re-run.
