# AIS 2.6a — Report 08: Ground Truth and Historical Label Audit

## 1. Audit Methodology
Every historical label in `fixtures/Incident json.zip` was audited against its original FortiSIEM incident payload and analyst resolution string.

---

## 2. Key Audit Findings
1. **Operational vs. Certified Labels:**
   - The historical resolutions in the SIEM represent single-analyst operational shift notes (e.g. "kill process is true", "legitimate activity, noth...", "case closed").
   - They were created under time pressure without formal adjudicative rigor or multi-analyst review.
   - None of the 20 incidents meet the standard for **Certified Ground Truth**.
2. **Resolution Conflict in Incident 132474210:**
   - Operational note said "legitimate activity", but raw event logs proved the execution of `UltraViewer_Service.exe` (unauthorized remote administration software).
   - The LLM and Layer B validator correctly identified this as an unapproved remote tool execution (Policy Violation True Positive).
   - This illustrates why uncertified operational notes must not be blindly equated with truth.
3. **Certified Selective Accuracy Status:**
   - Standard: $\ge 85\%$ selective accuracy on certified incidents.
   - Actual: Certified incidents = 0.
   - Reported as: **Not measured — certified ground truth unavailable**.
