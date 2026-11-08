# Operating Limitations, Boundaries & Next Steps (AIS 2.1)

## 1. Operating Boundaries and Safety Invariants

Agent Intelligence Studio 2.1 is explicitly engineered as a **dry-run intelligence evaluation and validation platform**. It operates under strict containment invariants:

1. **Zero Automated SIEM Ticket Closures**:
   The validation engine operates in observation mode over historical logs and staged test cohorts. It does not issue FortiSIEM API updates to close, resolve, or reclassify live tickets.
2. **Zero Automated Containment / Host Isolation**:
   No EDR isolation commands, firewall blocklist pushes, or account lockouts are initiated by this layer.
3. **Strict Zero Direct Push & RepoDeploy Governor Enforcement**:
   All software changes remain on local development branches until formal, two-stage approval gating is executed.
4. **Zero Production Rule Alteration**:
   The validation engine does not rewrite active production SIEM rules or silently modify approved G1–G8 policies in the production registry.

---

## 2. Technical Limitations and Known Trade-Offs

### 1. Statistical Precision in Low-Volume Scenarios
While Wilson score intervals provide mathematically sound confidence bounds for small sample sizes, rules triggered infrequently (e.g., $N < 15$) produce wide confidence intervals (e.g., $90\%$ accuracy with interval $[0.55, 0.98]$). SOC leadership must not interpret point accuracy on small cohorts as proof of production readiness.

### 2. Regex-Based Entity Extraction vs. Unstructured Telemetry
The current `VerdictClaimValidator` employs strict regular expressions for IPv4, IPv6, common domain structures, ports, and hexadecimal hashes. For complex, nested proprietary event payloads where entity names do not adhere to standard conventions, custom extractor patterns must be registered per log source.

### 3. Asynchronous Execution Overhead During Bulk Replay
Simulating hundreds of historical incidents sequentially through local LLMs can introduce processing latency. For large-scale historical replays ($> 500$ incidents), batch evaluations must be dispatched to background Celery worker pools.

---

## 3. Recommended Next Steps & Production Pilot Roadmap

### Phase 1: Shadow-Mode Historical Telemetry Ingestion (Weeks 1–2)
- Replay 30 days of historical SIEM incidents for the top 50 high-volume rules.
- Accumulate ground truth records and establish calibrated baselines ($N \ge 30$).
- Validate that the demotion rate on ambiguous alerts aligns with human Tier-2 escalation rates.

### Phase 2: Analyst Feedback Integration & Active Learning (Weeks 3–4)
- Expose the Verdict Intelligence Dashboard (Dashboards A through E) to senior SOC analysts.
- Capture analyst feedback on demoted cases to refine Evidence Contracts and archetype requirements.
- Tune selective classification thresholds ($\theta$) per detection archetype.

### Phase 3: Pilot Auto-Triage on Calibrated Rules (Weeks 5–6)
- Enable automated pre-triage recommendations only for rules with:
  - $N \ge 50$ verified historical incidents.
  - Balanced Accuracy $\ge 92\%$.
  - ECE $\le 0.08$.
  - Required Trust Score $\ge 9/10$.
- All other alerts remain gated under mandatory human analyst review.
