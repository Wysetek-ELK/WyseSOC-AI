# 07 — Cryptographic Integrity and Hash Authenticity Report

## 1. 11 Discrete Cryptographic Hashes
Every execution record in `LIVE_EXECUTION_LEDGER.jsonl` tracks 11 discrete SHA-256 hashes:
1. `raw_evidence_hash`
2. `rule_definition_hash`
3. `policy_content_hash`
4. `system_prompt_hash`
5. `user_content_hash`
6. `wire_prompt_hash`
7. `actual_http_body_hash`
8. `raw_provider_response_hash`
9. `parsed_response_hash`
10. `final_verdict_hash`
11. `canonical_request_payload_hash`

All 20 incidents possess completely unique and distinct `wire_prompt_hash` values.

