# Remote GUI & API Acceptance Verification Plan

**Target Host**: Server 1 (`172.26.41.240`)  
**Components Under Verification**:
- FastAPI Backend (`ai-verdict-backend.service`)
- Next.js Frontend (`ai-verdict-frontend.service`)
- PostgreSQL Database (`rule_learning_profiles`, `analyst_verdict_reviews`)
**Rule**: `Heavy TCP Host Scan On Fixed Port` (`40498741-ee6b-4a71-9101-0d6d3f77154c`)  
**Date**: November 20, 2026  

---

## 1. Remote API Verification Procedure

Following authorized UPLA deployment to Server 1:

### Test Step 1: Query Rule Learning Profile Before Manual Evaluation
- **Endpoint**: `GET http://172.26.41.240/api/learning/rules/40498741-ee6b-4a71-9101-0d6d3f77154c`
- **Expected Status**: 200 OK
- **Expected Data**:
  - `total_analyst_reviews`: 31
  - `verified_fp_count`: 31
  - `verified_tp_count`: 0
  - `empirical_accuracy`: `null` (N/A)
  - `eligible_evaluations`: 0

### Test Step 2: Trigger Explicit Accuracy Evaluation Endpoint
- **Endpoint**: `POST http://172.26.41.240/api/learning/rules/40498741-ee6b-4a71-9101-0d6d3f77154c/evaluate-accuracy`
- **Headers**: `Authorization: Bearer <token>`, `Content-Type: application/json`
- **Expected Status**: 200 OK
- **Expected Payload**:
  - `success`: `true`
  - `decisive_evaluations`: 0
  - `total_analyst_reviews`: 31
  - `verified_fp_count`: 31
  - `verified_tp_count`: 0
  - `empirical_accuracy`: `null`
  - `class_balance`: `{ "verified_tp": 0, "required_pilot_tp": 10, "is_balanced": false, "tp_deficit": 10 }`
  - `breakdown`: `{ "analyst_resolved_abstention": 16, "analyst_only_initial_benchmark": 15, "agreement_tp": 0, "agreement_fp": 0 }`
  - `message`: Explicitly states 0 decisive AI predictions found across 31 verified reviews (16 abstentions, 15 initial benchmarks).

---

## 2. Browser GUI Acceptance Procedure

### Test Step 3: Header & Next Recommended Action Verification
- **URL**: `http://172.26.41.240/agent-intelligence-studio?rule_id=40498741-ee6b-4a71-9101-0d6d3f77154c`
- **Verification**:
  - Top banner displays: **"Collect True Positive Ground Truth"** with badge **"Class Balance Needed"**.
  - Description states: *"31 reviews collected (0 TP / 31 FP). At least 10 independently confirmed True Positive cases required for pilot calibration baseline. Currently 0 decisive AI predictions."*
  - Button text: **"Review Incidents Queue"**. Clicking smoothly scrolls into the review workbench.

### Test Step 4: Accuracy & Learning Tab Verification
- **Tab**: Click *Accuracy & Learning (Analyst Review & Learning)*.
- **Verification**:
  - Tab badge displays `31` reviews.
  - Top Diagnostic Alert appears with title: **"Empirical Accuracy: NOT MEASURABLE (0 Decisive AI Predictions)"** and badge **"DECISIVE PREDICTIONS NEEDED"**.
  - Detailed narrative explains that 16 reviews resolved AI abstentions and 15 were initial benchmarks without AI inference.
  - Amber alert box displays **Pilot Class Balance Deficit**: *"0/10 True Positives confirmed. At least 10 TP cases and 10 FP cases are required for Supervised Pilot calibration baseline."*
  - Prominent **"Evaluate Accuracy"** button is present. Clicking triggers calculation, shows a spinner, and displays feedback.
  - **Verified Confusion Matrix**: Table displays 0 in all 4 decisive cells, accompanied by the explanation box: *"Why is the confusion matrix currently zero? All 31 verified reviews in the database are currently non-decisive paired samples..."*
  - Card 2 (Empirical Accuracy) displays `N/A` with subtitle *"Awaiting decisive predictions"* and an inline **"Re-evaluate"** action.
