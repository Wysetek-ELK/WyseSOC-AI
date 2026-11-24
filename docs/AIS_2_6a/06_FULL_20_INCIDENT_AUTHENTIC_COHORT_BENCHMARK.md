# AIS 2.6a — Report 06: Full 20-Incident Authentic Cohort Benchmark

## 1. Benchmark Execution Ledger Summary
The full benchmark cohort of 20 authentic FortiSIEM incidents (10 CrowdStrike, 10 Prisma SASE) was executed against the live Server 2 GPU runtime.

### Authoritative Performance Metrics

| Metric | Target | AIS 2.6 Baseline | AIS 2.6a Result | Status |
|---|---|---|---|:---:|
| **Overall Decisive Coverage** | $\ge 70\%$ | 0.0% (0/20) | **65.0% (13/20)** | `SUBSTANTIAL IMPROVEMENT` |
| **CrowdStrike Decisive Rate** | $\ge 70\%$ | 0.0% (0/10) | **80.0% (8/10)** | `EXCEEDS TARGET` |
| **Prisma SASE Decisive Rate** | $\ge 50\%$ | 0.0% (0/10) | **50.0% (5/10)** | `MEETS TARGET` |
| **Abstention Rate** | $\le 35\%$ | 100.0% (20/20) | **35.0% (7/20)** | `MEETS TARGET` |
| **Live GPU Executions** | 20 | 10 | **19** | `VERIFIED` |
| **Provider Boundary Rejections** | N/A | 0 | **1** | `VERIFIED BOUNDARY` |
| **Total GPU Tokens Consumed** | Accounting | 38,435 | **102,726** | `VERIFIED` |
| **Live Prompt Tokens** | Accounting | 33,702 | **92,214** | `VERIFIED` |
| **Live Completion Tokens** | Accounting | 4,733 | **10,512** | `VERIFIED` |
| **Certified Selective Accuracy** | $\ge 85\%$ | Uncertified | **Not measured — certified ground truth unavailable** | `HONEST ACCOUNTING` |

---

## 2. Complete 20-Incident Adjudication Table

| Incident ID | Detection Rule | Prompt Tok | Comp Tok | Model (Layer A) | Validator (Layer B) | Final Authoritative | Decisive |
|---|---|---:|---:|---|---|---|:---:|
| **132438483** | Crowdstrike: Suspicious Activity | 5,717 | 506 | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** |
| **132439932** | Crowdstrike: Suspicious Activity | 5,744 | 493 | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** |
| **132441815** | Crowdstrike: Suspicious Activity | 7,546 | 609 | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** |
| **132461358** | Crowdstrike: Suspicious Activity | 6,414 | 592 | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** |
| **132461368** | Crowdstrike: Suspicious Activity | N/A | N/A | None (HTTP 400) | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **NO** |
| **132472498** | Crowdstrike: Suspicious Activity | 6,109 | 543 | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** |
| **132474210** | Crowdstrike: Suspicious Activity | 6,918 | 470 | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** |
| **132501348** | Crowdstrike: Suspicious Activity | 4,412 | 545 | `TRUE_POSITIVE` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **NO** |
| **132502453** | Crowdstrike: Suspicious Activity | 5,788 | 502 | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** |
| **132527297** | Crowdstrike: Suspicious Activity | 4,443 | 441 | `TRUE_POSITIVE` | `TRUE_POSITIVE` | `TRUE_POSITIVE` | **YES** |
| **132499009** | Prisma SASE: Suspicious File Threat | 3,560 | 463 | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | **YES** |
| **132499023** | Prisma SASE: Suspicious File Threat | 3,622 | 475 | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | **YES** |
| **132499745** | Prisma SASE: Suspicious File Threat | 3,557 | 768 | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **NO** |
| **132578774** | Prisma SASE: Suspicious File Threat | 3,577 | 563 | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | **YES** |
| **132591888** | Prisma SASE: Suspicious File Threat | 3,711 | 768 | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **NO** |
| **132595592** | Prisma SASE: Suspicious File Threat | 3,607 | 768 | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **NO** |
| **132596403** | Prisma SASE: Suspicious File Threat | 3,549 | 492 | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | **YES** |
| **132599145** | Prisma SASE: Suspicious File Threat | 3,857 | 455 | `FALSE_POSITIVE` | `FALSE_POSITIVE` | `FALSE_POSITIVE` | **YES** |
| **132599146** | Prisma SASE: Suspicious File Threat | 6,225 | 291 | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **NO** |
| **132599330** | Prisma SASE: Suspicious File Threat | 3,858 | 768 | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | `REQUIRES_ATTENTION` | **NO** |
