# AIS 2.6d — Deliverable 03: Operator Manual Ground Truth Review Guide

**Target Audience:** Project Owner, Lead SOC Analyst, Security Detection Engineers  
**Application:** Verdictum AI (Agent Intelligence Studio)  
**Phase:** AIS 2.6d Operational Checkpoint A  
**Status:** READY FOR OPERATOR REVIEW  

---

## 1. Purpose of Human Ground Truth Review

To establish whether Verdictum AI's local LLM (`Qwen/Qwen2.5-7B-Instruct-AWQ`) possesses genuine security intelligence, we must compare its real, live predictions against **authentic human ground truth**.

Previous evaluations in AIS 2.6b and 2.6c were limited because:
1. Historical FortiSIEM resolution labels often reflected automated script closures or brief shift handovers rather than rigorous forensic adjudication.
2. AI evaluations were conducted in offline simulation mode without live model inference.

The project owner and SOC analysts are now requested to complete blind reviews of the **frozen 20-incident development cohort**, beginning with the **top 5 priority disagreement cases**.

> [!IMPORTANT]
> **Zero Guesswork Required:** If the available incident evidence does not contain sufficient telemetry to prove an attack or legitimate authorization, select **`Inconclusive`**. Never manufacture a forced True Positive or False Positive.

---

## 2. Access & Navigation Instructions

### 2.1 Application Access
- **Application URL:**  
  `http://<SERVER_1_IP>:3000/agent-intelligence-studio`  
  *(If connecting locally: `http://localhost:3000/agent-intelligence-studio`)*
- **Legacy Route Auto-Redirect:**  
  Navigating to `/agent-studio/ground-truth` automatically redirects to `/agent-intelligence-studio`.
- **Operator Credentials:**  
  Log in using an authorized SOC Analyst or Administrator account:
  - Username: `analyst` *(or your assigned SOC account)*
  - Default initial login if unauthenticated: navigate to `/login`.

### 2.2 Navigating to the Review Queue
1. Log into Verdictum AI.
2. From the main sidebar or top navigation, select **Agent Intelligence Studio**.
3. By default, the studio opens on the **Double-Blind Incident Review Queue** (or click the **"Review Incidents"** tab).
4. You will see:
   - **Queue Header:** Displays `Pending: 20`, `Reviewed: 0`, and the badge `Double-Blind Active (AI Determination Masked)`.
   - **Left Panel:** Scrollable list of pending security incidents.
   - **Right Panel:** Normalized Evidence Artifacts, Raw Telemetry Logs, and the Analyst Independent Determination form.

---

## 3. Step-by-Step Review Procedure

For each incident in the queue:

### Step 1: Select Incident from Left Panel
Click on an incident in the left queue list (e.g., `#132474210`). The right-hand workspace will load the incident details.

### Step 2: Inspect Normalized Evidence & Telemetry
In the right workspace, examine:
- **Incident Summary:** Rule name, trigger timestamp, severity, and customer scope.
- **Normalized Evidence Artifacts:** Process path, command line, source IP, destination port, and file hash.
- **Raw Event Telemetry:** Expand the `Raw Telemetry Logs` accordion to view original FortiSIEM JSON events.
- **Rule Definition:** Review why the detection rule fired.

> [!NOTE]
> All AI verdicts, confidence scores, and historical closure comments have been strictly masked on the server to prevent confirmation bias.

### Step 3: Record Your Independent Determination
Under **"Analyst Independent Determination"**, select one of three choices:
1. **True Positive (TP) — Confirmed Malicious:**
   - Select if evidence confirms unauthorized attacker activity, malicious tools, or genuine policy violations.
2. **False Positive (FP) — Benign Noise:**
   - Select if evidence confirms authorized administrative activity, approved software deployment, or standard benign web assets.
3. **Inconclusive — Insufficient Evidence:**
   - Select if evidence lacks necessary forensic artifacts (e.g. unknown executable binary without sandbox detonation, or ambiguous remote tool without IT authorization context).

### Step 4: Add Investigative Rationale & Evidence References
- **Investigation Notes / Rationale:** Enter a concise summary of your finding (e.g., *"UltraViewer executing on Domain Controller with no ITSM change ticket observed. High risk of unauthorized remote access."* or *"Standard CDN JavaScript library downloaded during routine browser session; benign web asset."*).
- **Evidence Citations:** Cite key evidence tags or fields (e.g., `EV-132474210-src_ip`, `update.exe`, `DestinationPort:443`).

### Step 5: Submit Determination
- Click **"Submit Review"**.
- Your review is immediately committed to the persistent database as a **Level 2 Independent Human Review**.
- Upon submission, the stored AI verdict comparison is revealed to you for feedback.
- Click **"Next Incident"** to proceed to the next case.

---

## 4. Priority Incidents for Immediate Review (Top 5 Batch)

Please complete the following **five priority incidents** first:

| Priority | Incident ID | Detection Rule | Target Asset / Entity | Key Question for Reviewer |
|---|---|---|---|---|
| **#1** | **`132474210`** | Crowdstrike: Suspicious Activity | Domain Controller `PC-TSI-DC` / `UltraViewer_Service.exe` | Is UltraViewer authorized on a Domain Controller, or is it an unauthorized dual-use remote access tool? |
| **#2** | **`132596403`** | Prisma SASE: Suspicious File Threat | IP `172.25.6.101` / `review.es.system.js` | Is this a standard benign web JavaScript asset, or does it contain malicious script behavior? |
| **#3** | **`132599145`** | Prisma SASE: Suspicious File Threat | IP `172.25.14.157` / `jquery.knob.js` | Is this open-source jQuery library download benign noise or an attack vector? |
| **#4** | **`132438483`** | Crowdstrike: Suspicious Activity | Workstation `DESKTOP-E0G2R49` / `UltraViewer_Service.exe` | Is UltraViewer legitimate user software on a client workstation or unauthorized shadow IT? |
| **#5** | **`132591888`** | Prisma SASE: Suspicious File Threat | IP `172.25.6.208` / `update.exe` | Can a Windows PE executable (`update.exe`) be confirmed benign/malicious without sandbox detonation, or is it Inconclusive? |

---

## 5. Remaining Incidents of the Frozen 20 Cohort

Following the top 5, please review the remaining 15 cases in the queue:
- **CrowdStrike Cases:** `132439932`, `132441815`, `132461358`, `132461368`, `132472498`, `132501348`, `132502453`, `132527297`.
- **Prisma SASE Cases:** `132499009`, `132499023`, `132499745`, `132578774`, `132595592`, `132599146`, `132599330`.

---

## 6. Checkpoint Notice: Governance Invariant

> [!IMPORTANT]
> **Operator Checkpoint A is currently ACTIVE:**
> - Under strict UPLA and AIS 2.6d governance invariants, **empirical accuracy metrics cannot be calculated or certified until human ground truth reviews are completed and submitted**.
> - Workstream status is currently recorded as:  
>   `overall_status = "BLOCKED_PENDING_HUMAN_GROUND_TRUTH"`
> - As soon as reviews are submitted through the application, the benchmark harness will evaluate the live LLM outputs against your certified human determinations.

*Live queue and tracking registers:*  
- [GROUND_TRUTH_REVIEW_QUEUE.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/GROUND_TRUTH_REVIEW_QUEUE.json)  
- [HUMAN_REVIEW_PROGRESS.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6d/HUMAN_REVIEW_PROGRESS.json)
