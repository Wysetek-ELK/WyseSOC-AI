# AIS 2.6e — Workstream 4: Operator Manual Review Guide

**Phase:** AIS 2.6e  
**Target URL:** `http://172.26.41.240:3000/agent-intelligence-studio` (Server 1) or `http://localhost:3000/agent-intelligence-studio` (Local)  
**Document Identity:** `docs/AIS_2_6e/06_OPERATOR_MANUAL_REVIEW_GUIDE.md`  
**Referenced Manifest:** [GROUND_TRUTH_REVIEW_QUEUE.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6e/GROUND_TRUTH_REVIEW_QUEUE.json)

---

## 1. Quick-Start Instructions for SOC Reviewers

To unlock empirical accuracy measurement, authorized SOC analysts must submit double-blind reviews for at least the **5 priority incidents** (and ideally all 20 incidents):

1. **Navigate to the Review Workbench:**
   Open your browser to:
   `http://172.26.41.240:3000/agent-intelligence-studio`
2. **Select an Incident from the Queue:**
   Use the search bar or queue list to select one of the 5 priority incidents:
   - Priority 1: `132474210`
   - Priority 2: `132596403`
   - Priority 3: `132599145`
   - Priority 4: `132438483`
   - Priority 5: `132591888`
3. **Examine the Blinded Evidence Packet:**
   - Review the triggered FortiSIEM rule definition and severity.
   - Inspect the normalized telemetry events, process paths, and command lines.
   - Inspect raw firewall / EDR logs in the collapsible telemetry panel.
4. **Select Your Verdict:**
   - **`TRUE_POSITIVE`**: If the activity represents unauthorized, malicious, or policy-violating activity matching the detection objective.
   - **`FALSE_POSITIVE`**: If the activity represents legitimate, authorized, or benign operational software (e.g. approved remote support, standard CDN web scripts).
   - **`INCONCLUSIVE`**: If the available logs lack essential forensic data (e.g. missing parent command line, unresolvable destination domain) to make a definitive determination.
5. **Provide Evidence-Grounded Reasoning:**
   - For `TRUE_POSITIVE` or `FALSE_POSITIVE`, enter 1–3 sentences citing observed telemetry fields (e.g. "UltraViewer executed from Program Files under services.exe with DNS connection to update.ultraviewer.net").
   - Click **Submit Analyst Review**.

Once submitted, the record is cryptographically bound into `analyst_verdict_reviews` as Level 2 Ground Truth.
