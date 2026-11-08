# Empirical Accuracy Evaluation Engine (AIS 2.1)

## 1. Overview and Core Purpose

Standard classification benchmarks often report single-point accuracy numbers (e.g., "94% accurate") that obscure statistical uncertainty and fail to measure the cost of abstention. In high-stakes SOC environments, an AI assistant that refuses to answer when evidence is scarce is vastly superior to one that guesses blindly.

The **Empirical Accuracy Evaluator** (`backend/app/services/empirical_accuracy_evaluator.py`) calculates robust statistical performance metrics, computes **Wilson Score 95% Confidence Intervals**, and evaluates **selective classification risk-coverage trade-offs**.

---

## 2. Statistical Metrics & Confusion Matrix

The engine maps model verdicts (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ANALYST_ATTENTION`) against historical ground truth:

```
                            Adjudicated Ground Truth
                         TP            FP       ATTENTION
                   +-------------+-------------+---------+
         TP        |     TP      |     FP      |   N/A   |
Model              +-------------+-------------+---------+
Verdict  FP        |     FN      |     TN      |   N/A   |
                   +-------------+-------------+---------+
         ATTENTION | Abstain(TP) | Abstain(FP) |   N/A   |
                   +-------------+-------------+---------+
```

### Core Metrics (Evaluated on Covered Decisions):
- **Precision**: $\frac{\text{TP}}{\text{TP} + \text{FP}}$
- **Recall (Sensitivity)**: $\frac{\text{TP}}{\text{TP} + \text{FN}}$
- **Specificity**: $\frac{\text{TN}}{\text{TN} + \text{FP}}$
- **Balanced Accuracy**: $\frac{\text{Recall} + \text{Specificity}}{2}$
- **F1-Score**: $\frac{2 \times \text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$

---

## 3. Wilson Score 95% Confidence Intervals

Point estimates on small sample sizes are misleading ($3/3 = 100\%$, but the true population accuracy could be under $50\%$). The evaluator computes asymmetric **Wilson Score intervals** with continuity correction for all proportions ($z = 1.96$):

$$w = \frac{p + \frac{z^2}{2n} \pm z \sqrt{\frac{p(1-p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

Where:
- $p$ is the observed sample proportion.
- $n$ is the number of evaluated samples.
- $z = 1.95996$ for a $95\%$ confidence level.

When $n = 10$ and $p = 0.90$, the Wilson 95% interval is $[0.596, 0.982]$, making the uncertainty immediately obvious to SOC decision-makers.

---

## 4. Selective Classification & Risk-Coverage Curves

In selective classification, the system can choose between making a definitive decision or abstaining (`REQUIRES_ANALYST_ATTENTION`) based on a confidence threshold $\theta$:

$$\text{Coverage}(\theta) = \frac{\text{Decisions Made with Confidence} \ge \theta}{\text{Total Incidents}}$$
$$\text{Selective Risk}(\theta) = \frac{\text{Errors Made with Confidence} \ge \theta}{\text{Decisions Made with Confidence} \ge \theta}$$

### The Risk-Coverage Curve:
The evaluator sweeps $\theta$ from $0.0$ to $1.0$ in $0.1$ increments:
- At $\theta = 0.0$: Coverage is $100\%$, but Risk is higher as difficult or incomplete incidents are forced into a decision.
- As $\theta$ increases: Coverage decreases (higher abstention), and Selective Risk falls towards zero as only rock-solid cases are classified.

```
Selective Risk (%)
  |
30| * (Coverage = 100%, Threshold = 0.0)
20|    *
10|       * (Coverage = 80%, Threshold = 0.6)
 2|            * (Coverage = 55%, Threshold = 0.9)
 0+------------------------------------------------ Coverage (%)
  0      20      40      60      80     100
```

---

## 5. Abstention Rate Analysis

The engine distinguishes between two distinct classes of abstentions:
1. **Justified Abstentions**: Incidents where raw SIEM evidence was incomplete (`is_sufficient == False`) or contradictory. Abstaining on these cases represents a success of the guardrails, avoiding false positives or missed breaches.
2. **Under-Confident Abstentions**: Incidents with complete, high-quality evidence where the model failed to reach a confident decision. These identify opportunities for policy refinement or few-shot example enhancement.
