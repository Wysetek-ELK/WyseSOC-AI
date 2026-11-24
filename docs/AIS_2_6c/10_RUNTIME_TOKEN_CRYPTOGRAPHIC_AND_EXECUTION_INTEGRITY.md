# AIS 2.6c — Workstream 11: Runtime Token, Cryptographic & Execution Integrity
**Document ID:** `10_RUNTIME_TOKEN_CRYPTOGRAPHIC_AND_EXECUTION_INTEGRITY.md`  
**Phase:** AIS 2.6c — Core LLM Intelligence Isolation, Prompt Bias Diagnosis & Human Ground Truth  
**Target Components:** TokenBudgetService, Cryptographic Hashing, Execution Identity  
**Artifacts Generated:**  
- `docs/AIS_2_6c/RUNTIME_CAPABILITY_MANIFEST.json`  
- `docs/AIS_2_6c/HASH_VERIFICATION_RESULTS.json`  
- `docs/AIS_2_6c/EXECUTION_BUILD_FINGERPRINT.json`  
- `docs/AIS_2_6c/REQUEST_RESPONSE_MANIFEST.json`  

---

## 1. Runtime Token Budgeting & Admission Invariants

The evaluation harness strictly enforces runtime context limits before wire transmission to Server 2:

$$\text{exact\_wire\_prompt\_tokens} + \text{requested\_max\_completion\_tokens} \le \text{runtime\_context\_limit}$$

### Parameter Budget Enforced:
- **Verified Runtime Context Limit:** `8,192` tokens
- **Requested Completion Reservation:** `768` tokens
- **Theoretical Prompt Allowance:** `7,424` tokens
- **Conservative Target Input Budget:** `6,400` tokens
- **Admission Outcome:** If estimated prompt tokens exceed 6,400 tokens, compaction is applied; if exceeded after compaction, the incident is abstained preflight (`CONTEXT_WINDOW_EXCEEDED`) with 0 GPU waste.

---

## 2. Multi-Layer Cryptographic Hashing Architecture

Each benchmark execution record captures distinct cryptographic SHA-256 hashes:

| Byte Scope | Hash Identifier | Description |
|---|---|---|
| **Raw Evidence** | `raw_evidence_hash` | SHA-256 of raw incident syslog JSON from FortiSIEM |
| **Rule Definition** | `rule_definition_hash` | SHA-256 of FortiSIEM rule trigger logic & severity |
| **System Prompt** | `system_prompt_hash` | SHA-256 of system prompt string sent on the wire |
| **User Content** | `user_content_hash` | SHA-256 of delimiter-wrapped `<UNTRUSTED_INCIDENT_DATA>` |
| **Full Wire Prompt** | `wire_prompt_hash` | SHA-256 of system prompt + user content combined |
| **HTTP Body** | `actual_http_body_hash` | SHA-256 of canonical HTTP POST request payload |
| **Provider Response** | `raw_provider_response_hash` | SHA-256 of raw string emitted by vLLM engine |
| **Parsed Verdict** | `parsed_response_hash` | SHA-256 of normalized model JSON structure |
| **Final Verdict** | `final_verdict_hash` | SHA-256 of incident ID + final authoritative verdict |

---

## 3. Dynamic Execution Identity & Commit Integrity

The stale Git SHA bug in AIS 2.6b was resolved by implementing multi-source fallback in `EmpiricalBenchmarkHarness.get_active_git_sha()`:
1. Direct `.git/HEAD` reference resolution (eliminates subprocess timeout and path dependency).
2. Subprocess `git rev-parse HEAD`.
3. Environment variables `DEPLOYED_GIT_SHA` and `CURRENT_GIT_SHA`.
4. Refusal to silently return hardcoded ancient commits.

---

## 4. Deliverable References

- Runtime Capability Manifest: [RUNTIME_CAPABILITY_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/RUNTIME_CAPABILITY_MANIFEST.json)
- Hash Verification Results: [HASH_VERIFICATION_RESULTS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/HASH_VERIFICATION_RESULTS.json)
- Execution Build Fingerprint: [EXECUTION_BUILD_FINGERPRINT.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/EXECUTION_BUILD_FINGERPRINT.json)
- Request-Response Manifest: [REQUEST_RESPONSE_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/REQUEST_RESPONSE_MANIFEST.json)
