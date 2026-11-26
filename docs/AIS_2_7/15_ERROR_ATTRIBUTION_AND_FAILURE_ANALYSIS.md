# AIS 2.7 — Workstream 15: 100% Error Attribution & Root Cause Analysis

**Phase:** AIS 2.7 | **Generated (UTC):** 2026-11-25T06:31:38.558775+00:00  
**Artifacts:** [ERROR_ATTRIBUTION_MATRIX.json](ERROR_ATTRIBUTION_MATRIX.json), [MODEL_REASONING_FAILURE_REGISTER.json](MODEL_REASONING_FAILURE_REGISTER.json)

## 1. Primary Root-Cause Counts (Every Incorrect Incident Accounted For)

### Mode A (`19/20` Errors)
- `RC-02_MODEL_BIAS_FALSE_POSITIVE_COLLAPSE`: **`19/19`** (predicted `FALSE_POSITIVE` at 85% conf across all 9 CrowdStrike TPs and all 10 Prisma SASE `INCONCLUSIVE` alerts).

### Mode B (`18/20` Errors)
- `RC-04_POLICY_TEMPLATE_DOMAIN_MISMATCH_PRISMA`: **`10/18`** (`9` Prisma `FALSE_POSITIVE` + `1` Prisma `TRUE_POSITIVE` on `132499745`, combined with Server 1's mismatched EDR-style Prisma policy forbidding abstention and model's IP/benignity hallucinations).
- `RC-06_CONTRADICTORY_MISSING_EVIDENCE_CLAIM`: **`7/18`** (`7/9` CrowdStrike UltraViewer TPs where model falsely claimed `process.command_line` was missing).
- `RC-07_HUMAN_ONLY_HASH_REPUTATION_DEPENDENCY`: **`1/18`** (`132501348` `MEGAsync.exe`: CrowdStrike description alleged Falcon sensor COM tampering and GT-2 analyst relied on external clean hash reputation absent from LLM input).

### Mode C (`11/20` Strict 3-Class Disagreements vs GT-2)
- `RC-10_UPSTREAM_MODE_B_ABSTENTION_PRESERVED_BY_VALIDATOR`: **`7/11`** (correctly did NOT fabricate TP when Mode B abstained; flagged missing-field contradictions).
- `RC-12_VALIDATOR_MISSED_NARRATIVE_IP_OR_BENIGNITY_HALLUCINATION`: **`2/11`** (`132599145`, `132499023`: Mode B citations matched strings superficially while narrative assumed benignity or misread RFC1918 IP).
- `RC-11_VALIDATOR_SAFE_ESCALATION_PREVENTING_FP_AS_TP`: **`1/11`** (`132501348`: Mode C prevented Mode B's false TP misclassification by escalating to `REQUIRES_ATTENTION`).
- `RC-09_VALIDATOR_SAFETY_REJECTION_OF_HALLUCINATED_SIGNATURE_CLAIM`: **`1/11`** (`132527297`: Mode C rightly rejected Mode B's lucky `TRUE_POSITIVE` because claim fabricated `"Binary not signed"` citing `process.name`).
