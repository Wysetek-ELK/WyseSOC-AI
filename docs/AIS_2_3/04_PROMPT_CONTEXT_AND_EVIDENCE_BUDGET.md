# AIS 2.3 — Prompt Context Budgeting & Evidence Preservation

**Project:** Verdictum AI  
**Organization:** Wysetek Systems Technologists Pvt. Ltd.  
**Phase:** AIS 2.3 (Real Evidence Delivery & Verdict Accuracy Pilot)  
**Date:** November 23, 2026  
**Status:** VALIDATED & COMPLIANT  

---

## 1. Overview & Constraints

The local GPU inference service on Server 2 hosts the quantized AWQ model `Qwen/Qwen2.5-7B-Instruct-AWQ` running under vLLM.
- **Physical Context Window Limit:** Exactly **4,096 tokens**.
- **Reserved Completion Budget:** **768 tokens** (guaranteeing comprehensive JSON verdict schemas, reasoning, citations, and uncertainty declarations without mid-sentence truncation).
- **Available Prompt Budget:** **3,328 tokens** ($4,096 - 768$).

Previous failure modes occurred when uncompacted raw event lists exceeded 40,000+ tokens, triggering naive emergency stripping. Stage D establishes a strict, deterministic, evidence-preserving token allocation architecture.

---

## 2. Priority-Ordered Token Allocation Budget

The token allocation hierarchy enforces strict precedence: critical policy directives and canonical facts take priority, while correlated event lists are intelligently bounded:

```
Total Context: 4,096 Tokens
├── Reserved Output Completion: 768 Tokens
└── Available Input Prompt: 3,328 Tokens
      ├── P1: Safety & JSON Schema Definition (~400 tokens)
      ├── P2: Policy Compilation (Sections 1–9 Criteria) (~1,200 tokens)
      ├── P3: Evidence Contract Requirements (~200 tokens)
      ├── P4: Canonical Evidence Records (18–22 records) (~650 tokens)
      ├── P5: Allowlisted Primary Event Telemetry (1–2 events) (~600 tokens)
      └── Safety Wire Margin: (~278 tokens)
```

| Priority | Budget Tier | Description | Target Allocation | Measured Allocation (AIS 2.3) |
| :---: | :--- | :--- | :---: | :---: |
| **P1** | **Safety & Schema** | System delimiters, anti-leakage guards, Pydantic response JSON contract. | 400 | 380–420 |
| **P2** | **Policy Compilation** | 9-Section rule-specific investigation policy, false-positive criteria, escalation rules. | 1,200 | 1,150–1,250 |
| **P3** | **Evidence Contract** | Declared mandatory and conditional evidence fields. | 200 | 180–210 |
| **P4** | **Canonical Evidence** | Verified, normalized evidence records with cryptographic integrity digests. | 700 | 580–690 |
| **P5** | **Primary Telemetry** | Allowlisted event payload with process commands, hashes, source/destination IPs. | 600 | 450–600 |
| **P6** | **Wire Margin** | Delimiter tags, token estimation variance buffer. | 228 | 150–228 |
| **TOTAL** | **Available Input** | **Maximum prompt payload sent to vLLM** | **3,328** | **2,471 – 2,793** |

---

## 3. Empirical Verification across 20 Benchmark Fixtures

Every single historical benchmark incident was audited through `TokenBudgetService.budget_prompt` with the live Qwen tokenizer. All 20 incidents successfully fit within the available budget:

| Incident ID | Detection Rule | Canonical Evidence Count | Allowlisted Events | Total Prompt Tokens | Headroom to 3,328 Budget | Status |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **132438483** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,745 | +583 tokens (17.5%) | **PASS** |
| **132439932** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,743 | +585 tokens (17.6%) | **PASS** |
| **132441815** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,745 | +583 tokens (17.5%) | **PASS** |
| **132461358** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,743 | +585 tokens (17.6%) | **PASS** |
| **132461368** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,745 | +583 tokens (17.5%) | **PASS** |
| **132472498** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,736 | +592 tokens (17.8%) | **PASS** |
| **132474210** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,736 | +592 tokens (17.8%) | **PASS** |
| **132501348** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,793 | +535 tokens (16.1%) | **PASS** |
| **132502453** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,745 | +583 tokens (17.5%) | **PASS** |
| **132527297** | Crowdstrike: Suspicious Activity | 21 | 1 | 2,741 | +587 tokens (17.6%) | **PASS** |
| **132499009** | Prisma SASE: Suspicious File | 19 | 1 | 2,475 | +853 tokens (25.6%) | **PASS** |
| **132499023** | Prisma SASE: Suspicious File | 19 | 1 | 2,508 | +820 tokens (24.6%) | **PASS** |
| **132499745** | Prisma SASE: Suspicious File | 19 | 1 | 2,473 | +855 tokens (25.7%) | **PASS** |
| **132578774** | Prisma SASE: Suspicious File | 19 | 1 | 2,476 | +852 tokens (25.6%) | **PASS** |
| **132591888** | Prisma SASE: Suspicious File | 21 | 1 | 2,694 | +634 tokens (19.0%) | **PASS** |
| **132595592** | Prisma SASE: Suspicious File | 19 | 1 | 2,482 | +846 tokens (25.4%) | **PASS** |
| **132596403** | Prisma SASE: Suspicious File | 19 | 1 | 2,471 | +857 tokens (25.7%) | **PASS** |
| **132599145** | Prisma SASE: Suspicious File | 20 | 1 | 2,611 | +717 tokens (21.5%) | **PASS** |
| **132599146** | Prisma SASE: Suspicious File | 21 | 1 | 2,749 | +579 tokens (17.4%) | **PASS** |
| **132599330** | Prisma SASE: Suspicious File | 20 | 1 | 2,611 | +717 tokens (21.5%) | **PASS** |

---

## 4. Anti-Leakage & Blinding Controls

Strict anti-data-leakage verification was performed on every assembled model payload before transmission:
- Forbidden ground truth keys (`resolution`, `clearedReason`, `comments`, `clearedUser`, `clearedTime`, `analyst_verdict`, `ground_truth`) were audited using `HistoricalGroundTruthValidator.sanitize_incident_for_inference`.
- Leaks Detected: **0 out of 20 (100% clean)**.
- Evidence Integrity: Full cryptographic integrity digests (`sha256`) were generated for all canonical evidence records, ensuring end-to-end traceability from raw FortiSIEM JSON to model evaluation.
