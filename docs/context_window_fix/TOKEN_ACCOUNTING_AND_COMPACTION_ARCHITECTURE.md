# Token Accounting and Compaction Architecture

**Date:** 2026-11-12  
**Component:** Evidence Compaction, Deduplication & Token Accounting Engine  
**Module Paths:**
- `backend/app/services/tokenizer_service.py` (`ModelTokenizerService`)
- `backend/app/services/evidence_compaction_service.py` (`EvidenceCompactionService`)
- `backend/app/services/token_budget_service.py` (`TokenBudgetService`)

---

## 1. Architectural Overview

Verdictum AI operates across a dual-tier distributed pipeline: Server 1 (FastAPI backend running triage, normalization, and policy compilation) and Server 2 (vLLM inference host serving Qwen2.5-7B-Instruct-AWQ).

To resolve `CONTEXT_WINDOW_EXCEEDED` without silently truncating evidence or fabricating unsupported verdicts, the token management engine incorporates:
1. **Model-Compatible Token Accounting:** Accurate token estimation reflecting BPE subword tokenization, JSON punctuation overhead, Base64 strings, and hex hashes.
2. **Evidence-Aware Compaction & Deduplication:** Multi-stage reduction of redundant telemetry while preserving 100% forensic fidelity and occurrence counts.
3. **Mandatory Contract Anchors Invariant:** Essential detection criteria and required fields are guaranteed inclusion across all evaluations.
4. **Deterministic Chunking:** Multi-window evaluation for genuinely oversized unique evidence that exceeds single-prompt budgets.
5. **Fail-Closed Safe Abstention:** Preserves `REQUIRES_ATTENTION` as an abstention (never an inferred verdict) when telemetry cannot be safely processed.

---

## 2. Priority Hierarchy and Token Accounting

Prompts are assembled and budgeted according to a strict priority hierarchy:

| Priority | Section | Mutability | Trimming Strategy |
| :--- | :--- | :--- | :--- |
| **P1** | System Safety Instructions & Output Schema | Immutable | Never trimmed; guaranteed inclusion. |
| **P2** | Enterprise Approved Policy Directives | Immutable | Never trimmed; verified approved policy text. |
| **P3** | Mandatory Evidence Contract Requirements | Immutable | Never trimmed; required fields must be present. |
| **P4** | Critical Incident Telemetry & Canonical Evidence | Compaction-Protected | Compacted, deduplicated, and relevance-sorted. |
| **P5** | Correlated Secondary Events | Trimmable | Trimmed from oldest secondary backwards; preserves `events[0]`. |
| **P6** | Optional Enrichment (Threat Intel, GeoIP) | Trimmable | Trimmed after RAG. |
| **P7** | Verified Semantic Precedents (RAG) | Trimmable | Trimmed first when prompt exceeds budget. |

### ModelTokenizerService
Provides model-compatible token counting using `tiktoken` (`cl100k_base` / `o200k_base`) when installed, with a calibrated pure-Python byte-pair encoding (BPE) subword tokenizer fallback.

```python
breakdown = ModelTokenizerService.account_prompt_breakdown(
    p1_schema_text=p1_schema,
    p2_policy_text=p2_policy,
    p3_contract_dict=p3_contract,
    p4_critical_evidence=p4_evidence,
    p5_correlated_events=p5_events,
    p6_enrichment=p6_enrich,
    p7_rag_block=p7_rag,
    rule_spec=rule_spec,
    reserved_output_tokens=512,
)
```

---

## 3. Evidence Compaction Engine Pipeline

`EvidenceCompactionService` executes a 6-stage reduction pipeline:

```
Raw Canonical Evidence Records (e.g. 361 records, 40k tokens)
    │
    ├── Step 1: Timestamp Range Aggregation
    │   └── 189 duplicate timestamps -> 1 Primary Trigger + 1 event.time_range summary
    │
    ├── Step 2: Raw Syslog Template Clustering
    │   └── 100 raw logs -> 2 representative verbatim samples + cluster frequency records
    │
    ├── Step 3: Repetitive Value Deduplication
    │   └── Collapses repeated (source_field, observed_value) tuples
    │   └── Invariant: DO_NOT_COLLAPSE_FIELDS protects command lines and file hashes
    │
    ├── Step 4: Relevance Selection & Priority Sorting
    │   └── Contract Required Fields (+1000 score)
    │   └── Detection Rule Pattern Fields (+500 score)
    │   └── High-Signal Anomaly Metrics (+400 score)
    │   └── Core SOC Identifiers (+300 score)
    │
    ├── Step 5: Bounded JSON Compaction
    │   └── Serializes minimal structure with explicit occurrence_count: N
    │
    └── Step 6: Deterministic Chunking (Opt-In / Multi-Window)
        └── When unique evidence exceeds budget, partitions into windows
        └── Mandatory Contract Anchors replicated into EVERY chunk
```

---

## 4. Grounding and Claim Verification Invariant

When `EvidenceCompactionService` introduces aggregate or representative records (e.g. `event.time_range` or cluster records), it generates deterministic `CanonicalEvidenceRecord` objects and registers them with the pipeline.

In `VerdictPipeline`:
```python
# Synchronize compacted records into norm_result.records
norm_result.records = compacted_canonical_records
```
This guarantees that when the LLM cites evidence IDs in `supporting_claims`, `ModelClaimExtractor` and `IndependentVerdictValidator` resolve citations against the exact evidence set present in the prompt, eliminating phantom reference errors.
