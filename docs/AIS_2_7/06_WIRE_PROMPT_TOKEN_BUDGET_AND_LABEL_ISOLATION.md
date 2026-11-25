# 06 — Wire Prompt Construction, Token Budget & Label Isolation

**Phase:** AIS 2.7 (Workstream 6)

---

## 1. Offline Token Budget Results (`ModelTokenizerService`, 8,192 Context)

All 20 incidents were constructed offline from Server 1's actual PostgreSQL payloads and Server 1's actual approved policies (`b6d9df2f` v3 and `ed7ff3c7` v1) using `PolicyCompilerService`, `TokenBudgetService(max_context_tokens=8192, max_completion_tokens=768, target_input_budget=6400)`, and `OpenAICompatibleProvider` wire serialization:

- **Mode A Input Tokens:** Min `2,690`, Max `5,411`, Min Headroom to `7,424` = `2,013` tokens. **0 / 20 overflows.**
- **Mode B Input Tokens:** Min `4,163`, Max `6,357`, Min Headroom to `7,424` = `1,067` tokens. **0 / 20 overflows.**
- **Compaction Behavior:** For multi-event incidents (`13` of `20` incidents with `2`–`34` raw events), `TokenBudgetService` pruned secondary raw events down to `events[0]` preview while retaining canonical evidence aggregates (`56/93` to `95/174` canonical records). Mode A and Mode B receive **byte-identical** budgeted factual payloads (`mode_a_mode_b_payload_parity: IDENTICAL`).

---

## 2. Label & Learning Isolation Verification

- **Pytest Integrity Suite:** `16 passed in 4.81s` (`test_ais_2_6c_three_mode_and_bias_isolation.py`, `test_ais_2_6d_empirical_integrity.py`, `test_ais_2_6f_certification_and_blind_review.py`).
- **Wire Prompt Marker Scan:** `0 / 20` GT-2 labels, `0 / 20` historical FortiSIEM resolutions/closure notes, `0 / 20` previous AI verdicts, and `0 / 20` RAG precedents injected across all 40 wire prompts. (Mode B Section 10 contains the static untrusted-data security instruction naming `<VERIFIED_HISTORICAL_PRECEDENTS>` with zero precedent content.)

Artifacts: [WIRE_PROMPT_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/WIRE_PROMPT_MANIFEST.json), [OFFLINE_TOKEN_ACCOUNTING_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/OFFLINE_TOKEN_ACCOUNTING_RESULTS.json), [LABEL_LEAKAGE_TEST_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/LABEL_LEAKAGE_TEST_RESULTS.json), [EVIDENCE_COMPACTION_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_7/EVIDENCE_COMPACTION_MANIFEST.json).
