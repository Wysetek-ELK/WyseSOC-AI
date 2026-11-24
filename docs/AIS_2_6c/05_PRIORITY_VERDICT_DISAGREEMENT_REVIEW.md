# AIS 2.6c — Workstream 5: Priority Verdict Disagreement Review
**Document ID:** `05_PRIORITY_VERDICT_DISAGREEMENT_REVIEW.md`  
**Phase:** AIS 2.6c — Core LLM Intelligence Isolation, Prompt Bias Diagnosis & Human Ground Truth  
**Target Incidents:** `132474210`, `132596403`, `132599145`, `132438483`, `132591888`  
**Artifact Generated:** `docs/AIS_2_6c/PRIORITY_DISAGREEMENT_REGISTER.json`  

---

## 1. Executive Summary

Five incidents in the development cohort exhibit material contradictions between historical operational labels, Phase AIS 2.6a predictions, Phase AIS 2.6b validator decisions, and LLM reasoning. Each incident has been prepared as an isolated, high-priority blind review packet.

---

## 2. Detailed Priority Incident Review

### 2.1 Incident `132474210` — Remote Administration Support Tool
- **Detection Rule:** `PH_RULE_CS_SUSPICIOUS_ACTIVITY`
- **Observed Entity:** `UltraViewer_Service.exe` on `api.us-2.crowdstrike.com`
- **Historical Operational Label:** `False Positive`
- **Historical Provenance Note:** *"legitimate activity, nothing suspicious observed."* (Human analyst shift resolution)
- **AIS 2.6a Verdict:** `TRUE_POSITIVE`
- **AIS 2.6b Verdict:** `TRUE_POSITIVE` (Model proposed TP; accepted by validator)
- **Disagreement Analysis:**
  The historical SOC analyst verified legitimate remote support and closed the incident as FP. In contrast, the AI evaluated the incident under Policy Version 3, which defined execution without an enterprise change ticket as unauthorized True Positive. The validator accepted the TP proposal because `UltraViewer_Service.exe` is a recognized dual-use utility.
  *Evidentiary Limitation:* FortiSIEM events cannot prove or disprove internal maintenance pre-approval. Neither the AI nor the historical label can be declared objectively correct without corporate IT ticketing records.

---

### 2.2 Incident `132596403` — JavaScript Application Asset
- **Detection Rule:** `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`
- **Observed Entity:** `review.es.system.js` from `172.25.6.101` to `35.244.35.245`
- **Historical Operational Label:** `True Positive`
- **Historical Provenance Note:** *"Mail has been sent already"* (Operational shift note)
- **AIS 2.6a Verdict:** `FALSE_POSITIVE`
- **AIS 2.6b Verdict:** `REQUIRES_ATTENTION` (Model proposed TP; demoted by validator: `TP_CRITERIA_UNSATISFIED`)
- **Disagreement Analysis:**
  The historical label of "True Positive" was recorded simply because an analyst sent an operational notification email. The file is a standard JavaScript file. In 2.6a, the AI called it FP. In 2.6b, the model proposed TP due to policy trigger bias, but the validator intercepted it and correctly demoted to `REQUIRES_ATTENTION` due to lack of threat intelligence or sandbox malware evidence.

---

### 2.3 Incident `132599145` — jQuery UI Extension Library
- **Detection Rule:** `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`
- **Observed Entity:** `jquery.knob.js` from `172.25.14.157` to `35.244.35.245`
- **Historical Operational Label:** `True Positive`
- **Historical Provenance Note:** *"Case has been raised for the similar incidents."* (Ticketing tracking note)
- **AIS 2.6a Verdict:** `FALSE_POSITIVE`
- **AIS 2.6b Verdict:** `REQUIRES_ATTENTION` (Model proposed TP; demoted by validator: `TP_CRITERIA_UNSATISFIED`)
- **Disagreement Analysis:**
  `jquery.knob.js` is a standard, open-source jQuery dial/knob plugin. The historical TP label was an administrative tracking placeholder indicating that a ticketing case existed for similar alerts. The validator in 2.6b correctly prevented this benign UI library from being classified as a decisive threat True Positive.

---

### 2.4 Incident `132438483` — Unsupported Authorization Claim
- **Detection Rule:** `PH_RULE_CS_SUSPICIOUS_ACTIVITY`
- **Observed Entity:** `UltraViewer_Service.exe`
- **Historical Operational Label:** `False Positive`
- **Historical Provenance Note:** *"kill process is true"* (Automated ML clearing script)
- **AIS 2.6a Verdict:** `TRUE_POSITIVE`
- **AIS 2.6b Verdict:** `TRUE_POSITIVE` (Model proposed TP; accepted by validator)
- **Disagreement Analysis:**
  The model justified its TP proposal with an unsupported assertion: *"The file path and command line indicate unauthorized use"*. In fact, the file path was standard (`C:\Program Files (x86)\UltraViewer\UltraViewer_Service.exe`). The historical label was automatically set to False Positive by an automated script simply because Falcon killed the process.

---

### 2.5 Incident `132591888` — Executable Download (`update.exe`)
- **Detection Rule:** `PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE`
- **Observed Entity:** `update.exe` from `172.25.6.208` to `35.244.35.245`
- **Historical Operational Label:** `False Positive`
- **Historical Provenance Note:** *"file observed is not suspicious"* (Automated ML clearing script)
- **AIS 2.6a Verdict:** `FALSE_POSITIVE`
- **AIS 2.6b Verdict:** `REQUIRES_ATTENTION` (Model proposed TP; demoted by validator)
- **Disagreement Analysis:**
  Unlike the other 9 Prisma SASE incidents which involve JavaScript files, `132591888` represents a Windows PE binary (`update.exe`). The historical script assumed it was benign. In 2.6a, the AI called it FP. In 2.6b, the model proposed TP, which the validator intercepted to `REQUIRES_ATTENTION` because binary downloads without sandbox detonation or hash reputation cannot be definitively adjudicated as benign or malicious.

---

## 3. Disagreement Matrix Summary

| Incident ID | Rule | Target Entity | Historical Label | Provenance Origin | AIS 2.6a | AIS 2.6b | Primary Review Focus |
|---|---|---|---|---|---|---|---|
| **132474210** | CS | `UltraViewer_Service.exe` | `FP` | Human Analyst | `TP` | `TP` | IT Change Authorization Verification |
| **132596403** | Prisma | `review.es.system.js` | `TP` | Shift Note ("Mail sent") | `FP` | `RA` | Web Script vs Malicious Code |
| **132599145** | Prisma | `jquery.knob.js` | `TP` | Ticket Tracking Note | `FP` | `RA` | Open Source Library Triage Standard |
| **132438483** | CS | `UltraViewer_Service.exe` | `FP` | Automated ML Script | `TP` | `TP` | Grounding of "Unauthorized" Assertions |
| **132591888** | Prisma | `update.exe` | `FP` | Automated ML Script | `FP` | `RA` | Executable Download Sandboxing |

---

## 4. Deliverable Reference

- Priority Disagreement Register: [PRIORITY_DISAGREEMENT_REGISTER.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/PRIORITY_DISAGREEMENT_REGISTER.json)
