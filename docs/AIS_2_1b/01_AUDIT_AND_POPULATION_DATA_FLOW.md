# AIS 2.1b — 01: Audit & Population Data Flow

## 1. System Context & Baseline Identification

- **Application:** Verdictum AI 2.1
- **Developer:** Wysetek Systems Technologists Pvt. Ltd.
- **Rule Name:** Heavy TCP Host Scan On Fixed Port
- **Canonical UUID:** `40498741-ee6b-4a71-9101-0d6d3f77154c`
- **Active Approved Policy Version:** `v7` (`pv-eval-contract-v7` / `d79fb576-c6b9-4f63-9167-3c7a2419b70a`)
- **Candidate Policy Version:** `v8` DRAFT (`20d4f788-85a5-437d-afbe-fe7fd80abca1`) — Strictly Preserved & Unmodified
- **Infrastructure Target:** Server 1 (`172.26.41.240` — FastAPI / Next.js / PostgreSQL), Server 2 (`AWS GPU` — vLLM AWQ)

---

## 2. End-to-End Data Flow Architecture

```mermaid
flowchart TD
    DB[(PostgreSQL Database)] --> |Incidents Table| Agg[AisEvaluationService Aggregator]
    DB --> |ActualLLMPromptCapture| Agg
    DB --> |VerdictTrustAssessmentRecord| Agg
    DB --> |AnalystVerdictReview| Agg
    DB --> |RuleLearningProfile| Agg

    Agg --> |Compute Summary & Invariant Partition| Snap[Canonical Evaluation Snapshot Contract]
    Snap --> |snapshot_id, snapshot_at, accuracy_numerator, accuracy_denominator| API[/api/v1/ais/evaluation-tracking/overview]
    API --> |AisEvaluationStatusResponse| FE[Frontend React Studio]

    FE --> Section1[Section 1: Compact Rule Toolbar]
    FE --> Section2[Section 2: Recommended Next Action]
    FE --> Section3[Section 3: Primary 3-Tab Bar]
    FE --> Section4[Section 4: Slim Model & Policy Strip]
    FE --> Section5[Section 5: Prioritized Summary Cards]
    FE --> Section6[Section 6: Dominant Incident Evaluation Table]
```

---

## 3. Scope Demarcation: Current Inventory vs. Historical Cohort

| Dimension | Scope A: Current Operational Inventory | Scope B: Cumulative Historical Ground Truth |
| :--- | :--- | :--- |
| **Data Source** | Live operational `incidents` table matched to rule tokens | `rule_learning_profiles` + `analyst_verdict_reviews` |
| **Filtering** | Active customer tenant (`DEFAULT`) + Canonical Rule Tokens | Rule lifetime learning profile + retrospective benchmarks |
| **Total Count** | 15 Incidents | 47 Analyst Reviews |
| **Verified TP** | 0 TP | 0 TP |
| **Verified FP** | 15 FP (in current incident scope) | 47 FP (cumulative analyst ground truth) |
| **Abstentions** | 15 Abstained under v7 | 30 Analyst-resolved abstentions |
| **Initial Benchmarks** | 0 Missing inference | 15 Initial benchmarks without stored AI runs |
| **Evaluation Invariant** | Total = Decisive + Abstained + Rejected + Failed + Not Evaluated | Total = Verified TP + Verified FP |
| **Accuracy Eligibility** | **NOT MEASURABLE** (0 eligible decisive comparisons) | **NOT MEASURABLE** (0 eligible decisive comparisons) |

---

## 4. Audit Findings on Pre-Existing Redundancy & Fragmentation

1. **Header Duplication:** The interface previously rendered `CompactPageHeader` followed immediately by a second "Authoritative Decoupled Rule Status Strip" which repeated the rule name, SIEM status, and version pills across 110px of vertical space.
2. **Action Banner Bloat:** The Next Recommended Action banner consumed ~80px of vertical height with multi-line padding, forcing primary content downwards.
3. **Primary Tabs Subtitles:** Primary tabs contained long explanatory subtitles (e.g., `(Analyst Review & Learning)`, `(Advanced Configuration)`), inflating tab header height.
4. **Summary Card Overcrowding:** The Test AI workbench presented 6 full-sized metric cards in equal proportion, giving 0-count secondary failure states (`Rejected`, `Failed/Timeout`) identical visual weight to primary operational indicators (`Current Incidents`, `Decisive`, `Abstained`, `Not Evaluated`).
5. **Table Occlusion:** On standard desktop viewports (1440x900 and 1280x800), the incident evaluation table was pushed below 680px, requiring immediate manual scrolling to inspect incident rows.
