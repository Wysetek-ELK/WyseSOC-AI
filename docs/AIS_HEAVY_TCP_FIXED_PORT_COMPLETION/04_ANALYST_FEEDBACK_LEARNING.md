# 04 — Independent Analyst Verdict & Verified Feedback Learning

**Target Rule:** `Heavy TCP Host Scan On Fixed Port` (`PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT` / `40498741-ee6b-4a71-9101-0d6d3f77154c`)
**Verified Live State on Server 1:** `69` pending double-blind reviews | `0` verified analyst ground-truth reviews | `ai_verdict_exposed: false`

---

## 1. End-to-End Human-in-the-Loop Architecture

| Workflow Step | Implementation Component | Verified Status |
| :--- | :--- | :--- |
| **Step A — AI Inference Persistence** | `verdict_pipeline.py` persists `verdict`, `proposed_verdict`, `confidence`, `trust_score`, `reason`, `supporting_evidence`, `missing_evidence`, `recommended_action`, `policy_version_id`, `prompt_capture_id`, and `prompt_sha256` on `Incident.ai_verdict`. | **Verified Live on Server 1** (`#176011`, `#167157`, `#175129`, `#176122`) |
| **Step B — Double-Blind Analyst Queue** | `AnalystReviewService.get_pending_reviews` (`GET /api/reviews/pending?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c`) strips `ai_verdict` before returning pending incidents, resolves canonical UUID/event_type aliases, enforces tenant scoping, and drains submitted items per reviewer. | **Verified Live on Server 1** (`pending_total: 69`, `ai_verdict_exposed: false` even after real LLM inference populated `ai_verdict`) + automated pytest (`test_03`) |
| **Step C — Post-Submission Reveal & Comparison** | `AnalystReviewService.submit_analyst_review` classifies each submission against AI output into `AGREEMENT_TP`, `AGREEMENT_FP`, `AI_FALSE_ALARM`, `CRITICAL_MISSED_TP`, or `ABSTAINED_RESOLVED`/`INSUFFICIENT_EVIDENCE` (excluded from verified accuracy denominator). | **Verified via automated pytest** (`test_03`, `test_rule_learning_platform.py`) |
| **Step D — Dispute Detection, L2 Adjudication & Exactly-Once Counting** | Conflicting verdicts by a second analyst automatically mark the incident `DISPUTED` without double-counting `total_analyst_reviews`. L2 adjudication (`adjudicate_review`) resolves disputes with immutable audit history and recalculates confusion matrix atomically. | **Verified via automated pytest** (`test_03` — confirmed `total_analyst_reviews == 1` across 2 conflicting reviewers, then `CRITICAL_MISSED_TP == 1` after L2 adjudication) |
| **Step E — Verified Learning Pool & RAG Leakage Prevention** | `VerifiedSemanticRetrievalService.retrieve_verified_precedents` retrieves only verified, same-rule, same-tenant precedents and strictly excludes self-incident, future timestamps, and `LOCKED_TEST` evaluation-partition records. | **Verified via automated pytest** (`test_08` — confirmed `candidates_rejected_future_leakage >= 1` and zero `LOCKED_TEST` records returned) |
| **Step F — Controlled Prompt Improvement Drafts** | `RuleLearningService.propose_prompt_improvement_draft` analyzes recurring error patterns and creates a **DRAFT** candidate policy version (`PromptVersionCreate`) without ever modifying the active approved production prompt or fine-tuning the LLM. | **Repaired & Verified via automated pytest** (`test_06`) |

---

## 2. Live Server 1 Double-Blind Integrity Proof

Immediately after real Server 2 GPU inference populated `Incident.ai_verdict` on `#176011`, `#167157`, `#175129`, and `#176122`:
- `GET /api/reviews/pending?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c&limit=10` returned `total: 69`.
- Programmatic inspection of every returned queue item verified `"ai_verdict"` key presence = **`False`**.
- **Zero synthetic analyst reviews** were injected into Server 1 PostgreSQL, preserving 100% ground-truth integrity (`total_analyst_reviews: 0`).

---

## 3. Tenant Isolation & Immutable Audit Guarantees

- Cross-tenant submission attempts (e.g., `OTHER_CORP` analyst attempting to review a `GDC_NOC` incident) raise `ValueError("Access denied")` (`test_03`).
- Every analyst review, correction, dispute flag, and L2 adjudication is stored immutably in `analyst_verdict_reviews`, with state changes tracked in `rule_learning_state_history`.
- **Policy Invariant:** Submitting analyst reviews NEVER auto-approves prompt revisions; candidate drafts must pass G1–G8 quality gates, offline replay on independent holdout samples, and explicit Administrator approval.
