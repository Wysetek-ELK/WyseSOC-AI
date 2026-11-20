# Verdictum AI — SOC Analyst Review Quick Start
**A Nontechnical Operational Guide for Independent Incident Review**
**Target Rule:** Website Access Policy Violation (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`)  
**URL:** [http://172.26.41.240:3000/agent-intelligence-studio](http://172.26.41.240:3000/agent-intelligence-studio)  

---

## Welcome to Double-Blind Ground Truth Review

As a SOC Analyst, your independent expertise is required to evaluate real FortiSIEM security alerts. To ensure statistical integrity, the AI's predictions are completely hidden (masked) until you record your own verdict. This prevents confirmation bias and builds trustworthy ground truth for model calibration.

Follow this simple, 10-step guide:

---

### Step 1 — Log In and Open Agent Intelligence Studio
1. Open your browser and navigate to:  
   **`http://172.26.41.240:3000/agent-intelligence-studio`**
2. Log in using your SOC Analyst credentials (`username` and `password`).

---

### Step 2 — Select the Website Access Policy Rule
1. In the rule selector at the top-left, choose:  
   **`Website access policy violation: Same Source and Destination`**  
   *(UUID: `7bd13e89-0828-48e6-8cf5-f3cbf12d438c`)*
2. Confirm the active tab is **Review Incidents** (Tab 1).
3. Verify that the badge **`Double-Blind Active (AI Determination Masked)`** is displayed.

---

### Step 3 — Select an Incident from the Queue
1. In the left panel (**Incident Review Queue**), click an incident to review.
2. We recommend starting with the verified initial cohort:  
   **`#4142`**, **`#4178`**, **`#4171`**, **`#4170`**, **`#4176`**, **`#4177`**, **`#4172`**, **`#4168`**, **`#4158`**, **`#4159`**, **`#4148`**, **`#4145`**, **`#3954`**, **`#4179`**, **`#4180`**.
3. The right panel will immediately load the incident's security details.

---

### Step 4 — Inspect Normalized Evidence & Raw Logs
1. Examine the **Normalized Evidence Artifacts** table:
   - Client Source IP (e.g. `172.26.29.74`).
   - Destination Domain / Host (e.g. `linkedin.com`, `adservice.google.com`).
   - Web Category (e.g. `Social.Networking`, `Advertising`, `Gambling`).
   - Firewall Action (e.g. `PASSED`, `BLOCKED`, `DROPPED`).
2. Read the **Original Raw Logs** box beneath the table to confirm the exact FortiGate UTM log payload.

---

### Step 5 — Determine Your Verdict
Select one of the three radio buttons under **Analyst Independent Determination**:

- **True Positive (TP) — Confirmed Malicious / Actionable Violation:**  
  *Choose this if the user made deliberate or repeated attempts to reach prohibited sites (e.g. gambling, malware, adult, proxy evasion) that represent an actionable corporate policy violation.*
- **False Positive (FP) — Benign Noise / Business Exception:**  
  *Choose this if the connection was benign (e.g. static CDN assets, business SaaS portals, legitimate software updates, authorized exemptions).*
- **Insufficient Evidence — Missing Critical Telemetry:**  
  *Choose this if the alert is header-only with no raw logs, or if key fields (domain, user, category) are missing and prevent an honest decision.*

---

### Step 6 — Enter Investigation Notes & Evidence Citations
1. In **Investigation Notes / Rationale**, type a brief 1–2 sentence explanation of your reasoning (e.g., *"Legitimate access to corporate LinkedIn portal; benign browsing"*).
2. In **Evidence Citations**, list the key evidence IDs observed (e.g., `EV-01, DestinationDomain:linkedin.com`).

---

### Step 7 — Submit Your Review
1. Click the cyan **Submit Review** button.
2. The system securely saves your determination into PostgreSQL.

---

### Step 8 — Inspect the Revealed AI Comparison
Immediately after submission, the system unmasks the Local LLM determination:
- Look at the cyan card: **Post-Submission AI Determination Comparison**.
- Compare **Your Determination** side-by-side with the **AI Model Determination**.
- Check the comparison outcome tag:
  - `AGREEMENT_TP`: Both you and the AI confirmed a True Positive!
  - `AGREEMENT_FP`: Both you and the AI confirmed a False Positive!
  - `AI_FALSE_ALARM`: You found it benign, but AI thought it was malicious.
  - `CRITICAL_MISSED_TP`: You found a confirmed violation, but AI marked it false positive.

---

### Step 9 — Optional: Inspect Full LLM Prompt Capture
If you wish to see the exact prompt delivered to Server 2, click the **Inspect LLM Prompt Capture** button in the post-submission card to view token counts and full model completion text.

---

### Step 10 — Move to the Next Incident
1. Click the **Continue to Next Incident** button.
2. The queue automatically advances to the next unreviewed alert.
3. Repeat the process to help build our 30-case pilot ground-truth dataset!

---

### Escalation & Support
If you encounter an incident with conflicting evidence or an unusual corporate exception, record `INSUFFICIENT_EVIDENCE` or leave a note requesting Senior Analyst adjudication. Automated incident closures and auto-ticketing remain disabled.
