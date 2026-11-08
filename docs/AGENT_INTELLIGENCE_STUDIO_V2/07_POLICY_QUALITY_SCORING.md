# 07. POLICY QUALITY SCORING FORMULA

## Overview

The Policy Quality Score is a quantitative **inspection index** normalized to a 0–100 scale. It provides SOC engineering leads with an objective measure of policy clarity, completeness, and evidence alignment.

> [!IMPORTANT]
> The Policy Quality Score is strictly an **inspection index** measuring policy drafting standards. It is **NOT** a claim of 100% verdict accuracy during live incident triage. live incident accuracy depends on real-time telemetry availability, adversary tradecraft, and sensor fidelity.

---

## Mathematical Formulation

The overall Policy Quality Score $S_{\text{quality}}$ is computed as a weighted sum of the 8 individual gate evaluation scores $g_i \in [0.0, 1.0]$, modified by penalty deductions $P$ and capped by the Hard-Gate Override:

$$S_{\text{base}} = \sum_{i=1}^{8} w_i \cdot g_i \cdot 100$$

Where the gate weights $w_i$ are defined as:

| Gate | Name | Weight ($w_i$) | Percentage |
| :--- | :--- | :--- | :--- |
| **G1** | Structural Integrity & Completeness | $0.20$ | 20% |
| **G2** | Archetype Relevance & Non-Contradiction | $0.20$ | 20% |
| **G3** | Evidence Contract Feasibility | $0.15$ | 15% |
| **G4** | True Positive Specificity | $0.15$ | 15% |
| **G5** | False Positive Validity | $0.10$ | 10% |
| **G6** | Abstention & Escalation Boundary | $0.10$ | 10% |
| **G7** | Internal Consistency | $0.05$ | 5% |
| **G8** | Historical Simulation & Regression Check | $0.05$ | 5% |
| **Total** | | $\mathbf{1.00}$ | $\mathbf{100\%}$ |

---

## Penalty Deductions ($P$)

Deductions are applied for non-blocking policy flaws and warning conditions:
1. **Unresolved Telemetry Key Warning:** $-5$ points per unverified key in policy text.
2. **Missing Optional Context Guidance:** $-5$ points if secondary correlation is unspecified.
3. **Simulation Sample Warning:** $-5$ points if historical backtest has $< 5$ samples (marked as `INSUFFICIENT_DATA`).
4. **Vague Indicator Keywords:** $-2$ points for generic phrases (e.g. "look for anything weird", "check behavior").

$$\text{Score}_{\text{preliminary}} = \max\left(0, \min\left(100, S_{\text{base}} - \sum P\right)\right)$$

---

## The Hard-Gate Override Function

A policy draft cannot pass quality validation if either of the hard gates fails, regardless of the preliminary score:

$$S_{\text{final}} = \begin{cases} \min(45.0, \text{Score}_{\text{preliminary}}) & \text{if } g_1 < 1.0 \lor g_2 < 1.0 \\ \text{Score}_{\text{preliminary}} & \text{otherwise} \end{cases}$$

$$\text{approval\_eligible} = \begin{cases} \text{False} & \text{if } g_1 < 1.0 \lor g_2 < 1.0 \lor S_{\text{final}} < 70.0 \\ \text{True} & \text{if } g_1 = 1.0 \land g_2 = 1.0 \land S_{\text{final}} \ge 70.0 \end{cases}$$

---

## Score Tiering & UI Representation

In the Agent Intelligence Studio frontend, quality scores are color-coded and badged:

- **90–100 (Exceptional):** Emerald Badge. Zero blocking findings, comprehensive evidence mapping, green simulation backtest.
- **75–89 (Compliant):** Blue Badge. Eligible for approval; minor non-blocking recommendations.
- **50–74 (Warning / Incomplete):** Amber Badge. Ineligible for approval until recommendations are resolved.
- **0–49 (Failed / Hard Gate Failure):** Red Badge. Blocker present (e.g. G1 missing SIEM definition or G2 archetype contradiction). Approval strictly disabled.
