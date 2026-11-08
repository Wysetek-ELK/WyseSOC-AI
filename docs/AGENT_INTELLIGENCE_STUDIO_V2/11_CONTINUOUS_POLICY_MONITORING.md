# 11. CONTINUOUS POLICY MONITORING & DRIFT DETECTION

## Overview

In enterprise security environments, detection rules are not static. Detection engineers frequently update SIEM rule conditions (e.g. tightening thresholds from 5 GB to 1 GB), telemetry feeds change schemas, and SOC analysts log corrections during manual triage.

The `PolicyLifecycleMonitor` (`backend/app/services/policy_lifecycle_monitor.py`) provides active, non-intrusive monitoring to detect drift between active investigation policies and the real-world environment.

---

## The Three Forms of Policy Drift

```text
+-------------------------------------------------------------------------+
|                    THE THREE FORMS OF POLICY DRIFT                      |
|                                                                         |
|  1. SIEM RULE DEFINITION DRIFT                                          |
|     - Occurs when the SIEM rule hash changes in FortiSIEM/Splunk.       |
|     - Example: Byte threshold updated from 2.0 GB to 500 MB.            |
|     - Action: Active policy remains active; drift event flagged;        |
|       SOC Lead notified to generate a new draft version.                |
|                                                                         |
|  2. TELEMETRY & SCHEMA DRIFT                                            |
|     - Occurs when expected evidence fields disappear from telemetry.    |
|     - Example: Log source stops sending 'network.bytes_sent'.           |
|     - Action: Flag contract feasibility warning; prevent silent         |
|       abstentions during live triage.                                   |
|                                                                         |
|  3. VERIFIED ANALYST FEEDBACK DRIFT                                     |
|     - Occurs when verified human analysts consistently overturn AI      |
|       verdicts (e.g. 5+ consecutive overturns on a specific rule).     |
|     - Action: Flag policy tuning recommendation; generate updated       |
|       draft incorporating verified analyst rationale.                   |
+-------------------------------------------------------------------------+
```

---

## Non-Destructive Monitoring Principles

> [!CAUTION]
> The platform **NEVER** silently alters or overwrites an active production policy upon detecting rule drift.

If a detection rule changes:
1. The currently approved policy version **remains active** to ensure continuity of operations.
2. A `PolicyDriftEvent` record is inserted into the database:
   ```python
   PolicyDriftEvent(
       rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
       drift_type="SIEM_RULE_MODIFIED",
       previous_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
       current_hash="8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4",
       detected_changes={"threshold": "Updated from 2147483648 to 1073741824"},
       is_acknowledged=False
   )
   ```
3. A visual amber warning badge appears on the rule in the Studio UI: **"Drift Detected"**.
4. The SOC Lead can review the drift event, click **"Acknowledge Drift"**, and trigger an intelligent draft regeneration to create a v2 candidate.

---

## Integration with Verified Analyst Feedback

In compliance with Phase 1 safety requirements, live incident ground truth is strictly isolated from inference. However, when tier-2 human analysts complete post-incident reviews, their verified conclusions are logged to the `VerifiedLearningHistory` table.

`PolicyLifecycleMonitor.check_analyst_feedback_drift()` analyzes these verified historical cases:
- If verified human outcomes deviate from model predictions by $\ge 15\%$ over the trailing 30-day window, a `VERIFIED_FEEDBACK_DIVERGENCE` drift event is registered.
- The system flags the policy for review, presenting the analyst rationale to the SOC Lead during next draft generation.
