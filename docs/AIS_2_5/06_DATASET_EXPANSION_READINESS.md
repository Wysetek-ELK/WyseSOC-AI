# AIS 2.5 — Stage 5b: Certified Ground-Truth Dataset Expansion Readiness Plan

**Document ID:** `docs/AIS_2_5/06_DATASET_EXPANSION_READINESS.md`  
**Phase:** AIS 2.5 (Certified Evidence, Controlled 8K Inference & Real LLM Accuracy Benchmark)  
**Author:** Principal SOC AI Architect, LLM/MLOps Engineer, Detection Engineer, Independent Empirical Evaluation Auditor  
**Date:** November 24, 2026  
**Status:** ARCHITECTED & OPERATIONALIZED  
**Target Evaluation Cohort:** $\ge 30\text{ Certified True Positives}$ and $\ge 30\text{ Certified False Positives}$ ($N \ge 60$)  

---

## 1. Executive Summary & Purpose

The multi-rule live benchmark (Stage 4) confirmed an empirical truth of the current historical archive: with only **2 Certified False Positives** and **0 Certified True Positives**, mathematical accuracy, precision, and recall have undefined denominators ($0/0$).

To move Verdictum AI to **statistically qualified empirical accuracy**, this readiness plan establishes the infrastructure, governance, double-blind adjudication workflows, and deduplication controls necessary to assemble a certified evaluation dataset of **at least 30 certified TP and 30 certified FP cases**.

```
+---------------------------------------------------------------------------------------------------+
|                                  DATASET EXPANSION PIPELINE                                       |
+---------------------------------------------------------------------------------------------------+
|  [ SOURCE INGESTION ]        [ INDEPENDENT BLIND REVIEW ]            [ GOVERNANCE & FREEZING ]    |
|                                                                                                   |
|  Real Multi-Tenant SIEM  --> Analyst 1 (Primary)    ---\                                          |
|  Incident Telemetry                                      \---> Inter-Rater Agreement              |
|                             Analyst 2 (Peer Review) ---/       (Cohen's Kappa >= 0.85)            |
|                                                                          |                        |
|  Controlled Red Team     --> Explicit "SIMULATION"   -----> Disagreement Escalation              |
|  Adversary Emulations        Segregation                        (Lead Security Architect)         |
|                                                                          |                        |
|                                                                          v                        |
|                                                               Frozen Evaluation Partition         |
|                                                               (30 Certified TP / 30 Certified FP) |
+---------------------------------------------------------------------------------------------------+
```

---

## 2. Ingestion & Candidate Identification Architecture

### 2.1 Candidate Data Stream A: Natural Multi-Tenant SIEM Telemetry
Acquires candidate historical investigations from enterprise FortiSIEM production instances spanning 90 days across multiple client organizations:
- **Tenant 1 (Tosoh):** Endpoint EDR, CrowdStrike, SentinelOne, Active Directory logs.
- **Tenant 2 (Forbes Marshall):** Palo Alto Prisma SASE, Cloud NGFW, Web Security proxies.
- **Tenant 3 (WSTPL):** Infrastructure firewalls, VPN gateways, server auth telemetry.

**Eligibility Filtering:**
- Incident must contain full raw security events (`rawEvents.length >= 1`).
- Must contain specific triggered FortiSIEM rule definitions and thresholds.
- Must possess closed investigation tickets with human analyst investigation text.

### 2.2 Candidate Data Stream B: Controlled Adversary Simulations (Red Team)
Because naturally occurring True Positive intrusions are rare ($<0.1\%$ in production), authentic adversary simulations are incorporated:
- **Frameworks:** MITRE ATT&CK Caldera, Atomic Red Team, Mandiant attack emulation.
- **Strict Partitioning Rule:** Every simulation record is permanently stamped:
  ```json
  {
    "telemetry_origin": "CONTROLLED_ADVERSARY_SIMULATION",
    "is_simulation": true,
    "emulation_plan_id": "MITRE-ATT&CK-T1059.001-POWERSHELL"
  }
  ```
- **Contamination Guard:** Simulated records are evaluated in a dedicated `SIMULATION_EVALUATION` partition and are **never** commingled with natural production telemetry when reporting operational SOC False Positive Rates.

---

## 3. Double-Blind Human Certification Workflow

Historical labels alone do not establish ground truth. A formal human certification workflow is implemented via Agent Intelligence Studio (`/api/analyst-review/adjudicate`):

```
                                  Candidate Incident
                                          |
                    +---------------------+---------------------+
                    |                                           |
            Analyst Reviewer 1                          Analyst Reviewer 2
          (Independent Assessment)                    (Independent Assessment)
                    |                                           |
                    +---------------------+---------------------+
                                          |
                                 Do Reviews Match?
                                          |
                        +-----------------+-----------------+
                        |                                   |
                       YES                                 NO
                        |                                   |
                        v                                   v
             [ CERTIFIED GROUND TRUTH ]           [ TIER 3 ESCALATION ]
             - Verified True Positive             Lead Detection Engineer
             - Verified False Positive            Final Adjudication Binding
```

### 3.1 Certification Rubric

#### A. True Positive Certification Rubric
The adjudicator must verify and cite at least one affirmative malicious indicator:
1. **Command Line & Process Telemetry:** Execution of malicious commands (e.g., encoded PowerShell, suspicious process hollowing, LSASS dumping).
2. **Adversary Infrastructure:** Outbound connection to known malicious C2 domain/IP corroborated by threat intelligence (VirusTotal, AlienVault OTX, Talos).
3. **Persistence / Privilege Escalation:** Unauthorized scheduled tasks, registry Run keys, service installations, or token impersonation.
4. **Data Exfiltration:** High-volume encrypted outbound transfer over non-standard protocols.

#### B. False Positive Certification Rubric
The adjudicator must verify and cite affirmative benign context:
1. **Enterprise Authorization:** Documented IT change ticket, corporate maintenance schedule, or administrative ticket ID.
2. **Sanctioned Software:** Binary matches official enterprise software vendor signature (hash verified against NSRL / Vendor CDN).
3. **Internal Security Tooling:** Activity attributed to authorized vulnerability scanning (Nessus, Qualys) during approved maintenance windows.

### 3.2 Inter-Rater Reliability & Freezing Standard
To ensure dataset rigor, inter-rater agreement is mathematically verified using **Cohen's Kappa ($\kappa$)**:

$$\kappa = \frac{p_o - p_e}{1 - p_e}$$

- **Threshold Requirement:** $\kappa \ge \mathbf{0.85}$ across the dual-reviewer cohort.
- Any incident with reviewer disagreement is reviewed by the Lead Security Detection Engineer. If consensus cannot be reached with high confidence, the incident is retained as `UNVERIFIED` and excluded from the certified evaluation set.

---

## 4. Anti-Contamination & Deduplication Safeguards

### 4.1 Cluster Deduplication & Batch Closure Suppression
Multi-alert storms from the same host or network event can falsely multiply sample sizes.
- **Deterministic Cluster Hashing:**
  $$K_{\text{cluster}} = \text{SHA256}(\text{rule\_id} \mid \text{target\_entity} \mid \text{telemetry\_signature})$$
- **Suppression Invariant:** Within any cluster, exactly **one** primary incident is admitted to the certified evaluation set. All subsequent identical alerts are tagged `is_duplicate = true` and reserved for stability testing only.

### 4.2 Data Blinding & Anti-Leakage Contract
Before any candidate record is exported to the evaluation partition:
1. `HistoricalGroundTruthValidator.sanitize_incident_for_inference` executes.
2. Fields `resolution`, `clearedReason`, `clearedTime`, `clearedUser`, `cmsClearUser`, `comments`, `ticket_id`, and `analyst_verdict` are deeply stripped.
3. Automated test `test_ground_truth_isolation.py` verifies zero leakage keys prior to benchmark dispatch.

---

## 5. Dataset Architecture & Target Partitions

The target 60-incident dataset is partitioned to prevent overfitting:

```
+------------------------------------------------------------------------------------+
|                   CERTIFIED EVALUATION DATASET (N = 60)                            |
+------------------------------------------------------------------------------------+
|                                                                                    |
|  [ CALIBRATION & DEVELOPMENT SET (N = 20) ]                                        |
|  - 10 Certified True Positives                                                     |
|  - 10 Certified False Positives                                                    |
|  Purpose: Policy tuning, prompt threshold optimization, contract refinements.      |
|                                                                                    |
|  [ HELD-OUT INDEPENDENT TEST SET (N = 40) ]                                        |
|  - 20 Certified True Positives                                                     |
|  - 20 Certified False Positives                                                    |
|  Purpose: Unbiased empirical accuracy qualification, confidence interval reporting.|
|  Rule: Strictly quarantined; ZERO prompt iteration allowed against this set.      |
+------------------------------------------------------------------------------------+
```

---

## 6. Readiness Checklist & Roadmap

| Milestone | Activity | Owner | Target Date | Readiness Status |
|---|---|---|:---:|:---:|
| **M1: Ingestion** | Extract 100 candidate raw JSON incidents from multi-tenant SIEM archives | Security Detection Engineer | Week 1 | **IN PROGRESS** |
| **M2: Double-Blind Review** | Execute dual-analyst review across all 100 candidate files | Tier 2 SOC Analysts | Week 2 | **READY (UI Active)** |
| **M3: Adjudication** | Resolve disagreements and calculate Cohen's Kappa ($\kappa \ge 0.85$) | Lead Security Architect | Week 2 | **DESIGNED** |
| **M4: Cluster Freezing** | Deduplicate clusters and freeze 30 TP / 30 FP partitioned dataset | Independent Auditor | Week 3 | **GOVERNED** |
| **M5: Benchmark Execution** | Run full 60-incident live benchmark against Server 2 vLLM runtime | LLM/MLOps Engineer | Week 3 | **READY (8K Active)** |

**Stage 5 Deliverables Status:** Both `05_GROUND_TRUTH_CERTIFICATION_AUDIT.md` and `06_DATASET_EXPANSION_READINESS.md` are complete and accepted.
