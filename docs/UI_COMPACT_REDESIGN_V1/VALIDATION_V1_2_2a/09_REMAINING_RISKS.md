# VERDICTUM AI — VALIDATION V1.2.2a
## 09. Remaining Risks & Pre-Deployment Boundaries

### 1. Architectural Boundaries & Pre-Deployment Observations

While the application software, UI compact layouts, security isolation, and readiness calculations are fully verified, several operational boundaries remain relevant prior to production deployment to Verdictum AI Server 1:

#### 1. Server 2 Runtime LLM Availability
- **Observation**: During validation testing, local vLLM / Ollama inference on Server 2 was intentionally offline or unseeded with high-capacity model weights.
- **Safeguard Verification**: The system handled this cleanly. Rather than failing silently, presenting mock inferences, or falsely indicating an active engine, the platform clearly marked `AI Execution: Offline` with appropriate pulsing indicators and explanatory tooltips.
- **Action for Server 1/2 Deployment**: Verify that the Server 2 GPU service (`http://${SERVER_2_INFERENCE_HOST}:8000/v1` or configured inference endpoint) is healthy and that `is_local_llm_available()` returns `True` before enabling continuous live polling.

#### 2. FortiSIEM Continuous Scheduler Configuration
- **Observation**: Real FortiSIEM synchronization operates via `FortiSIEMContinuousScheduler`. In developer workstations, sample datasets and fixtures are used.
- **Safeguard**: The scheduler supervisor starts safely with continuous error handling and backoff if FortiSIEM credentials are not populated.
- **Action**: Ensure FortiSIEM API keys, organization IDs, and polling frequencies are securely injected via environment variables on Server 1.

#### 3. Database Migration Prerequisites
- **Observation**: Database models require the `analyst_verdict_reviews` table with compound index on `(incident_id, reviewer_id)`.
- **Safeguard**: Automated startup migration hooks backfill necessary columns and check schema versions.
- **Action**: Run standard Alembic migration check on Server 1 before application process restart.

---

### 2. Risk Mitigation Summary Matrix

| Risk / Boundary | Severity | Mitigation Implemented | Production Deployment Safeguard |
| :--- | :--- | :--- | :--- |
| Blind Review bypass | High | Server-enforced role gating on all incident & timeline endpoints | Double-blind test personas verified in automated regression |
| Multi-analyst review collisions | Medium | Compound filter on `(incident_id, reviewer_id)` in `AnalystVerdictReview` | Verified independent review records for Analyst A and Analyst B |
| Deceptive "Enabled" status when model is dead | High | Authoritative derivation checks live LLM health before displaying `Enabled` | Verified `Offline` status badge with red pulsing dot |
| Premature candidate approval | High | G1–G8 gate enforcement with disabled approve buttons | UI disables button and displays explicit blocking checklist |
