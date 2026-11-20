# Report 05 — Verified 15-Incident Pilot Cohort
**Verdictum AI — AIS 2.0 SOC Analyst Pilot Selection & Stratification**
**Date:** November 20, 2026  
**Status:** FACTUALLY VERIFIED & ACTIVE IN QUEUE  
**Target Rule:** Website Access Policy Violation (`7bd13e89-0828-48e6-8cf5-f3cbf12d438c`)  

---

## 1. Executive Summary

This report establishes the initial 15-incident pilot cohort for the **Website Access Policy Violation** rule. All 15 incidents are real, verified FortiSIEM incidents residing in the Server 1 PostgreSQL database. They have been stratified across reporting devices, client source subnets, UTM web categories, and raw log availability to provide a balanced ground-truth baseline without confirmation bias.

Zero synthetic labels were introduced. Pre-existing AI determinations remain strictly masked until independent analyst submission.

---

## 2. Authoritative Pilot Cohort Table

| # | Incident ID | Database UUID | Reporting Device (Tenant) | Client Source IP | Raw Logs | Evidence Status | Review Status | Eligible | Stratum / Scenario |
|:---:|:---:|:---|:---|:---|:---:|:---:|:---:|:---:|:---|
| **1** | **#4142** | `bb793252-8703-4927-994c-e836aa39a66d` | `HOST-172.26.31.254` | `172.26.29.74` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Social Media / LinkedIn) |
| **2** | **#4178** | `9db5da52-944a-4d92-969c-2fe84cb8d3c1` | `HOST-172.26.31.254` | `172.26.29.72` | 2 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Multi-event Web Browsing) |
| **3** | **#4171** | `e73efb3c-ff1c-438e-a4b7-d1cfc737c3da` | `HOST-172.26.31.254` | `172.26.29.72` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Corporate Portal Access) |
| **4** | **#4170** | `ca30f736-a6fc-46a2-9b2d-fa2453e1a0b5` | `HOST-172.26.31.254` | `172.26.29.72` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Standard HTTP Session) |
| **5** | **#4176** | `a4300ced-1bfa-4c40-811c-c0c1694f54e1` | `HOST-45.64.199.219` | `172.25.26.59` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Candidate FP / Internal) |
| **6** | **#4177** | `e50f611f-c0fb-4054-a957-c5462cf6cf2b` | `HOST-45.64.199.219` | `172.25.26.59` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (DMZ Gateway Traffic) |
| **7** | **#4172** | `e943933c-23c7-4fc7-bf84-fc4f3be79fce` | `HOST-45.64.199.219` | `172.25.26.59` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Blocked External URI) |
| **8** | **#4168** | `9d5e8f8f-c301-44eb-9a2c-f3c5aa68a623` | `HOST-172.27.31.254` | `172.27.29.71` | 2 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Demo-SOC Client LAN) |
| **9** | **#4158** | `d0f0ff4d-f954-469b-88b1-e23114f49457` | `HOST-172.27.31.254` | `172.27.29.53` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Repeated Category Hit) |
| **10** | **#4159** | `068e7366-0a2b-42c2-bfa2-36c968fbc76c` | `HOST-172.27.31.254` | `172.27.29.53` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Proxy Redirect Evaluation) |
| **11** | **#4148** | `5f751008-0bf1-4e4b-97e3-0590a9829562` | `HOST-45.64.199.219` | `172.25.24.219` | 0 | Incomplete | `PENDING_REVIEW` | **YES** | Header-Only (Abstention Validation) |
| **12** | **#4145** | `00457a4e-1b3d-4c3e-8c54-47120dbefea7` | `HOST-45.64.199.219` | `172.25.24.219` | 0 | Incomplete | `PENDING_REVIEW` | **YES** | Header-Only (Abstention Validation) |
| **13** | **#3954** | `2efa3936-cb4d-45a7-96a8-6b8156dbd5b8` | `HOST-45.64.199.219` | `172.25.24.219` | 2 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Web Advertising Tracker) |
| **14** | **#4179** | `1c8901be-58a4-4a41-8664-d3a669e4f208` | `HOST-172.26.31.254` | `172.26.29.74` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (General Browsing) |
| **15** | **#4180** | `7d04291a-cc62-431e-927b-58832a514d2e` | `HOST-45.64.199.219` | `172.25.26.59` | 1 | Complete | `PENDING_REVIEW` | **YES** | Rich UTM (Blocked Content Filter) |

---

## 3. Stratification & Diversity Analysis

1. **Reporting Devices & Tenants:**
   - `HOST-172.26.31.254`: 5 incidents (Demo-SOC LAN)
   - `HOST-45.64.199.219`: 7 incidents (GDC NOC Gateway)
   - `HOST-172.27.31.254`: 3 incidents (Secondary Subnet)
2. **Client Sources:** Spans multiple class C subnets (`172.26.29.x`, `172.25.26.x`, `172.27.29.x`, `172.25.24.x`).
3. **Telemetry Completeness:**
   - 13 incidents possess full UTM event logs with complete HTTP and category artifacts.
   - 2 incidents (`#4148`, `#4145`) are header-only correlation alerts with 0 raw child logs, specifically included to test analyst and AI model abstention (`INSUFFICIENT_EVIDENCE`) handling.
4. **Zero Pre-Determined Labels:** Analysts must evaluate each case independently.
