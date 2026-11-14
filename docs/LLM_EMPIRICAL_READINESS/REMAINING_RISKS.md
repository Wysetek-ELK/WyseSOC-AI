# Verdictum AI — Empirical Verdict Readiness: Remaining Risks & Risk Taxonomy

## 1. Risk Taxonomy Classification

All components, security invariants, and validation controls are classified according to the four-tier verification taxonomy:

- **`IMPLEMENTED`**: Component architecture and safety code are fully built in the backend.
- **`OFFLINE VERIFIED`**: Validated by automated unit and regression test suites passing 100% in local test environments.
- **`PENDING GPU VALIDATION`**: Offline code complete; awaiting live inference execution against Server 2 GPU (`Qwen/Qwen2.5-7B-Instruct-AWQ`).
- **`EMPIRICALLY VERIFIED`**: Evaluated on live LLM inference against human-verified historical incident cohorts with statistical significance ($N \ge 30$).

---

## 2. Master Verification Matrix

| Component / Capability | Status | Verified Safeguards | Remaining Risk / Pending Action |
|---|---|---|---|
| **Signed Binary Non-Sufficiency** | `OFFLINE VERIFIED` | Binaries in System32 or validly signed alone cannot grant False Positive authorization. | None offline; prevents signed LOLBin bypasses. |
| **Maintenance Start/End Window Bounds** | `OFFLINE VERIFIED` | Telemetry timestamps strictly validated against maintenance start/end time. | Relies on accurate SIEM timestamp parsing. |
| **Absent Authorization Status Gating** | `OFFLINE VERIFIED` | Absent status attributes assigned state `UNKNOWN` and rejected fail-closed. | None offline; eliminates silent ticket approvals. |
| **Authoritative Evidence Provenance** | `OFFLINE VERIFIED` | Untrusted source systems (`rawsyslog`, `userpayload`) blocked from satisfying ITSM approvals. | None offline; blocks telemetry injection. |
| **Autonomous Incident Closure Hard Gating** | `OFFLINE VERIFIED` | Closure strictly restricted to decisive validated False Positives with certification. | None; zero unverified or abstained incidents can close. |
| **Anti-Data-Leakage Blinding Pipeline** | `OFFLINE VERIFIED` | Recursive stripping of 12 resolution/analyst leakage keys. Zero leakage detected in 20 incidents. | Requires maintenance if SIEM adds new resolution field names. |
| **Empirical Benchmark Evaluation Harness** | `OFFLINE VERIFIED` | Production-equivalent evaluation pipeline, Wilson score intervals, and confusion matrix calculation. | `PENDING GPU VALIDATION`: Ready for live execution on Server 2. |
| **Live Local LLM Accuracy Benchmark** | `PENDING GPU VALIDATION` | Harness supports `--mode live` with OpenAI-compatible endpoint. | Must execute against Server 2 once booted. |
| **Real Production Accuracy Certification** | `PENDING GPU VALIDATION` | Empirical metrics, calibration bins, and Wilson intervals operational. | Requires live GPU run to achieve `EMPIRICALLY VERIFIED`. |
| **Cohort Sample Size Expansion ($N \ge 100$)** | `IMPLEMENTED` | Dataset loader supports zip archives and SQLite database ingestion. | Current verified cohort has $N = 6$ ($N < 30$ statistical power limit). |

---

## 3. Detailed Remaining Risks & Mitigation Strategies

### Risk 1: Small Verified Ground Truth Cohort Size ($N < 30$)
- **Severity**: Moderate (Statistical Limitation, Not Security Vulnerability)
- **Status**: `OFFLINE VERIFIED` / `PENDING GPU VALIDATION`
- **Description**: Of the 20 historical FortiSIEM incidents in `fixtures/Incident json.zip`, only 6 have human-adjudicated ground truth labels (4 `VERIFIED_TP`, 2 `VERIFIED_FP`). The remaining 14 incidents were resolved by legacy automated ML ("Resolution set by Machine Learning") or contained containment-only EDR notes ("kill process is true") without human adjudication. Under our strict fail-closed safety rules, automated closures are rightly classified as `UNVERIFIED` and excluded from the accuracy denominator.
- **Impact**: At $N = 6$, Wilson 95% confidence intervals are wide ($[0.00\%, 48.99\%]$ for unsafe FP rate).
- **Mitigation**:
  - The benchmark harness automatically detects $N < 30$ and activates `statistical_power_warning = True` to prevent mistaking sample limitations for model failure.
  - Roadmap Phase 2 includes ingesting $N \ge 100$ historical incidents directly from production FortiSIEM archives.

### Risk 2: Live Local LLM Performance & Latency on Server 2
- **Severity**: Low to Moderate (Operational)
- **Status**: `PENDING GPU VALIDATION`
- **Description**: In offline mode, the harness evaluates deterministic baseline proposals. Real live model execution against `Qwen/Qwen2.5-7B-Instruct-AWQ` on Server 2 may exhibit prompt-length latency variations or subtle JSON formatting anomalies.
- **Mitigation**:
  - `TokenBudgetService` actively compacts evidence within the 16k context window.
  - Schema recovery and fallback mechanisms safely convert malformed LLM outputs into `REQUIRES_ATTENTION`.
  - Step-by-step checklist provided in `GPU_EXECUTION_CHECKLIST.md`.

### Risk 3: Dependency on SIEM Telemetry Field Quality
- **Severity**: Low (Robustly Mitigated)
- **Status**: `OFFLINE VERIFIED`
- **Description**: If a SIEM incident lacks critical fields (e.g., missing process name or destination IP), the preflight validator flags `EVIDENCE_MISSING` and forces `REQUIRES_ATTENTION`.
- **Mitigation**:
  - Preflight validation prevents inference on incomplete telemetry.
  - Re-evaluation queues allow re-triaging when supplementary telemetry is synchronized.

---

## 4. Path to "EMPIRICALLY VERIFIED" Status

To transition the local LLM from `PENDING GPU VALIDATION` to `EMPIRICALLY VERIFIED`:
1. Boot Server 2 GPU instance and verify vLLM health via `curl http://<SERVER_2_IP>:8000/health`.
2. Follow `docs/LLM_EMPIRICAL_READINESS/GPU_EXECUTION_CHECKLIST.md`.
3. Execute `python backend/app/scripts/run_empirical_benchmark.py --mode live --endpoint http://<SERVER_2_IP>:8000/v1`.
4. Verify that:
   - $N_{\text{unsafe FP}} = 0$.
   - JSON Schema Compliance $\ge 98\%$.
   - True Positive Recall $\ge 85\%$.
   - False Positive Precision $\ge 85\%$.
5. Save the generated `LIVE_GPU_BENCHMARK_<run_id>.md` report as the permanent empirical proof of performance.

