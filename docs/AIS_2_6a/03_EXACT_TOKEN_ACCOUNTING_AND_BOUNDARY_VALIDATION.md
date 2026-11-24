# AIS 2.6a — Report 03: Exact Token Accounting and Boundary Validation

## 1. Token Accounting Invariant
Under the 8,192-token runtime:
$$\text{actual\_wire\_prompt\_tokens} + \text{reserved\_completion\_tokens} \le 8192$$
With reserved completion tokens fixed at $768$:
$$\text{wire\_prompt\_ceiling} = 8192 - 768 = 7424\text{ tokens}$$

---

## 2. Empirical Boundary Test Scenarios

| Scenario | Input Condition | Observed Behavior | Governance Verdict |
|---|---|---|---|
| **Normal Incident Prompt** | 3,500 - 4,500 tokens | Admitted, processed on GPU, completed within budget | `PASS` |
| **Prompt Exceeding 4K Context** | 5,717 tokens (Incident 132438483) | Admitted under 8K runtime; 506 completion tokens; 44.2s latency | `PASS` |
| **Prompt Near Maximum Budget** | 6,918 tokens (Incident 132474210) | Admitted; 470 completion tokens; total 7,388 <= 8192; zero truncation | `PASS` |
| **Prompt Exceeding Validated Boundary** | 8,193 tokens (Incident 132461368) | Deterministically rejected by vLLM provider HTTP 400; routed safely to manual review | `PASS` |
| **Completion Reserve Protection** | 768 max completion requested | Output stopped naturally at 450-600 tokens or capped safely at 768 tokens without context overflow | `PASS` |

---

## 3. Boundary Rejection Forensic Analysis
Incident `132461368` provided direct empirical proof of runtime boundary enforcement:
- Prompt token length reached **8,193 tokens**.
- Server 2 vLLM returned HTTP 400:
  `"This model's maximum context length is 8192 tokens. However, your prompt contains at least 8193 input tokens, which exceeds this limit even without any output tokens."`
- The application caught the provider error, prevented crashes, set `is_decisive_accepted=False`, `final_authoritative_verdict="REQUIRES_ATTENTION"`, and preserved complete evidence.
