# VERDICTUM AI — VALIDATION V1.2.2a
## 04. Heavy TCP Historical v1 vs. Current Readiness Reconciliation

### 1. The Apparent Paradox

In the Validation V1.2.2 review, an apparent discrepancy was noted regarding the **Heavy TCP Host Scan** rule:
- `studio_heavy_tcp_v1_historical` screenshot clearly showed:
  - Header: `Policy v1: APPROVED`
  - Current Readiness: `BLOCKED / INCOMPLETE`
  - Quality Score: `54.0`
  - Quality Gates Passed: `2 / 8`
  - AI Execution: `Suspended`
- However, section 3 of the V1.2.2 report stated:
  `Readiness: APPROVED BASELINE`

This created ambiguity: was the screenshot failing to reflect the approved status, or was the report narrative conflating historical approval with current readiness?

---

### 2. Reconciliation & Root Cause

The investigation revealed that **the screenshot was 100% accurate, and the report narrative was in error**.

#### 2.1 The Two Distinct Realities:
1. **Policy Version Status (`version_status = "APPROVED"`)**:
   - In the database, version `v1` (ID `8a460ab8-5f06-4a90-b2d4-db958199d644`) is indeed the **historically approved baseline** that was promoted in an earlier release before AIS 2.0 gates were established.
   - It is marked as `status = "APPROVED"` and `RulePrompt.active_version_id = '8a460ab8-5f06-4a90-b2d4-db958199d644'`.
2. **Current AIS 2.0 Production Readiness (`readiness_status = "BLOCKED"`)**:
   - When modern AIS 2.0 evaluation is executed against `v1`, it evaluates all 8 rigorous quality gates (G1 through G8), evidence contracts, and telemetry ground truth.
   - Under this audit, `v1` only passes **2 out of 8 quality gates** (G1 and G7 pass; G2, G3, G4, G5, G6, and G8 fail) and scores only **54.0 / 100** (below the 70.0 threshold).
   - Therefore, its **Current Readiness is `BLOCKED`** pending re-validation or promotion of a compliant candidate version.

#### 2.2 Reconciled Matrix

| Dimension | Value | Meaning |
| :--- | :--- | :--- |
| **SIEM Rule Status** | `ACTIVE` | Detection rule is live in FortiSIEM cluster |
| **Policy v1 Version Status** | `APPROVED` | Historically signed off as production baseline |
| **AI Execution Status** | `Suspended` | Administrative suspension active (`ai_execution_suspended = True`) |
| **Current AIS 2.0 Readiness** | `BLOCKED / INCOMPLETE` | Fails modern G1–G8 standards (score 54.0, 2/8 gates) |
| **Active Candidate Version** | `v3` | Score 77.0, 6/8 gates; blocked on FortiSIEM semantics verification |

---

### 3. Concrete Source Code Proof

In `backend/app/services/production_readiness_service.py` (lines 80–120):
```python
# Active version status reflects the historical DB status:
active_version_status = active_version.status if active_version else "NONE"  # -> "APPROVED"

# But readiness_status is strictly recomputed from live gate verification:
if not gates_all_passed or quality_score < 70.0 or verified_count < required_reviews:
    readiness_status = ReadinessStatus.BLOCKED
```

And in `frontend/src/components/compact/AgentIntelligenceStudioOverview.tsx`:
```tsx
{/* Historical Baseline Card */}
<div>Policy v1: <span className="text-emerald-400 font-semibold">APPROVED</span></div>

{/* Current Evaluation Card */}
<div>Current Readiness: <span className="text-rose-400 font-semibold">Blocked / Incomplete</span> (54.0/100)</div>
```

Both cards are rendered side-by-side with complete visual clarity.

---

### 4. Conclusion

There is zero inconsistency in the software. Historical approval records are faithfully preserved, while modern safety governance prevents unverified execution without passing active quality gates. The V1.2.2a evidence and documentation now completely reconcile this distinction.
