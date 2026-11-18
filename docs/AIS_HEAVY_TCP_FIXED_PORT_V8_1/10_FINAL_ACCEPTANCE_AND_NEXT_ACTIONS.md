# 10 — Final V8.1 Acceptance Verdict & Prioritized Next Actions

## Final Acceptance Verdict

> **`V8.1 ENGINEERING COMPLETE — ANALYST GROUND TRUTH PENDING — PRODUCTION BLOCKED`**

- **Active Policy Recommendation:** **Keep Approved v7 (`d79fb576`) active and retain Candidate v8 (`20d4f788`) as `DRAFT`.** Do **not** approve v8 or enable production automation until real human analyst ground truth is collected, the observed 7B factual inversion is mitigated, and G8 passes on `LOCKED_TEST`.

---

## 1. Strict Evidence Separation Matrix

| Verification Layer | Status | Exact Verified Evidence |
| :--- | :---: | :--- |
| **1. Code Implemented** | **COMPLETE** | 4096/768 token budget, lossless Step 0 wire deduplication, Section 10/11 compaction, `scan.sample_context`, prioritized 14-field scan compaction, first-class `TRUNCATED_OUTPUT` rejection, and `test_11` implemented across 8 backend files. |
| **2. Automated Unit / Integration Tests** | **23/24 LIVE (`8120d882b`) + 1 FIX PENDING SERVER 1 RE-RUN** | `test_01`–`test_10`, `test_rule_learning_platform.py`, and `test_api_422_remediation.py` all PASS on Server 1 (`8120d882b`); synthetic `test_11` `+ 140` → `+ 95` margin fix committed in working tree and awaiting Server 1 pull to confirm `24/24`. |
| **3. Real Local GPU LLM Tested (Server 2)** | **COMPLETE (`run_id = a95cd268`)** | 6 real incidents run on live `Qwen/Qwen2.5-7B-Instruct-AWQ`: **`0/6` truncations** (down from `5/6`), **`14/14` fields preserved on `5/5` rich incidents**, `-821` prompt tokens, `6/6` SHA-256 `hash_match = True`, safe abstention on `#176122` & `#167157`, live validator rejection of `#164575` (`EVIDENCE_VALUE_MISMATCH`), AND honest identification of 7B factual inversion (`bidirectional_sessions=100` described as `"predominantly unanswered probes"`). |
| **4. Human-Verified Analyst Ground Truth** | **PENDING (`0 / 69` reviewed)** | `69` pending incidents (`32` rich-log Priority A/B + `37` header-only Tier 2) live in Double-Blind Workbench (`blind_mode_active = true`); `0` synthetic labels fabricated. |
| **5. Production Autonomy Readiness** | **BLOCKED (`7/8` gates)** | `lifecycle_stage = LEARNING`, `is_production_eligible = false`, `automation_policy.is_enabled = false`, `accuracy_status = NOT_MEASURABLE`, `0/100` evaluations, `0/25` TP, `0/50` FP, `0` live FortiSIEM closures. |

---

## 2. Prioritized Next Actions

1. **Pull Final V8.1 Commit on Server 1 & Confirm `24/24` Pytest Pass (Engineering — 2 minutes):**
   - Pull the final synced commit containing the `+ 95` safety margin in [token_budget_service.py](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/backend/app/services/token_budget_service.py) and re-run `pytest tests/test_ais_heavy_tcp_e2e.py tests/test_rule_learning_platform.py tests/test_api_422_remediation.py -q` on Server 1 to verify `24 passed, 0 failed`.
2. **Execute Priority A & Priority B Human Analyst Double-Blind Pilot (SOC Team — Immediate):**
   - Label the **4 Priority A mixed-scope `Demo-SOC` incidents** (`#167157`, `#160595`, `#158997`, `#158332`) first, followed by the **28 Priority B pure-external rich-log incidents** (`16 GDC_NOC` + `12 Demo-SOC`) via the Double-Blind Review Workbench (`06_ANALYST_LEARNING_PILOT.md`).
   - Reaching the first `>= 5` verified labels immediately unlocks certifying G8 simulation and verified RAG precedents (`TRAINING` split).
3. **Implement V8.2 Deterministic Prose-vs-Telemetry Contradiction Guardrail & Confidence Normalization (Engineering — Next Sprint):**
   - **Why:** In V8.1 real GPU testing, `Qwen/Qwen2.5-7B-Instruct-AWQ` copied `bidirectional_sessions=100, unanswered_probes=0` into `asserted_value` while still writing `"predominantly unanswered probes"` in `claim_text`/`reason` (on `#176011`, `#175129`, `#173449`) and returned `confidence` on a `0–1` scale (`0.9`/`0.95`) instead of `0–100`.
   - **Action:** Add a deterministic contradiction check inside `IndependentVerdictValidator` that flags/rejects claims whose prose asserts `"unanswered"` / `"denied"` / `"no bidirectional"` when observed `scan.tcp_behavior_summary` shows `bidirectional_sessions >= 80%` and `unanswered_probes <= 5%` (and vice versa), plus normalize/validate `0–1` vs `0–100` confidence explicitly.
4. **Optional Maintenance-Approved Server 2 Context Expansion (`--max-model-len 8192`) (Infra — Optional):**
   - After an administrator verifies free VRAM via `nvidia-smi` on Server 2 (`verdictum-cortex-01`), increasing vLLM `--max-model-len` from `4096` → `8192` (~`9.3 GB` total VRAM at 4 concurrent slots) would provide ample headroom for multi-precedent RAG injection once human reviews populate the verified precedent store. **Do not apply without explicit maintenance approval.**
5. **Certifying G8 Holdout Evaluation & Governed Promotion (SOC Lead + Admin — Post-100 Reviews):**
   - Once `>= 100` verified evaluations (`>= 25` TP, `>= 50` FP) exist, run certifying real-LLM G8 evaluation on `LOCKED_TEST`, verify all 10 readiness gates (`accuracy >= 95%`, `FP precision >= 99%`, `Wilson LCB >= 96%`, `TP recall >= 95%`, `0` critical missed TPs, `G1–G8 = 8/8`), and obtain explicit Admin approval before activating any candidate policy or controlled `FALSE_POSITIVE` automation.
