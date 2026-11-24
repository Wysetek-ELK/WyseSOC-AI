# AIS 2.6a — Report 09: Accuracy and Learning UI Verification

## 1. Compact UI Architecture
The Agent Intelligence Studio UI retains its clean, ergonomic 3-tab layout:
1. **Rule Performance & Learning**
2. **Evaluation Workbench**
3. **Audit & Evidence Ledger**

---

## 2. Verified UI Runtime Updates
- The Model Context Strip displays:
  - Context Window: **8,192 tokens (Verified)**
  - Prompt Ceiling: **7,424 tokens**
  - Reserved Output: **768 tokens**
  - Active Model: `Qwen/Qwen2.5-7B-Instruct-AWQ`
- The Metrics Panel displays:
  - Decisive Coverage: **65.0%**
  - CrowdStrike Decisive: **80.0%**
  - Prisma SASE Decisive: **50.0%**
  - Certified Selective Accuracy: `"Not measured — certified ground truth unavailable"`
- TypeScript typecheck and Next.js production build: **Passed with exit code 0**.
