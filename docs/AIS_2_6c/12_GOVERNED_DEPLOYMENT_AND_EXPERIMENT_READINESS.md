# AIS 2.6c — Workstream 12: Governed Deployment and Experiment Readiness Report

**Phase:** AIS 2.6c  
**Report ID:** `AIS-2.6c-REP-12`  
**Execution Timestamp:** 2026-11-24T15:12:00Z  
**Active Execution Git SHA:** `d854a5ef7471b74dab408473963a4511eab4dc66`  
**UPLA Project:** `SOC-AI-Agent` (`proj-98348ed9ed5e2ba1`)  
**Operating Mode:** `FULL_WORKFLOW`  

---

## 1. Governance Context and Deployment Architecture

In compliance with the Universal Project Lifecycle Agent (UPLA) contract:
- Project Mode: `FULL_WORKFLOW`
- Gate 1: Human Approval Gate 1 (GitHub Synchronization)
- Gate 2: Human Approval Gate 2 (Remote Server Deployment)

No external mutations, GitHub pushes, or remote deployments may be executed without separate, explicit YES/NO approvals from the user.

### Infrastructure Targets:
1. **Server 1 — Verdictum AI Application Server:**
   - Host: `172.26.41.240`
   - User: `root`
   - Deploy Directory: `/opt/wysesoc-ai`
   - SSH Key: `C:\Users\amits\.ssh\upla_server1_ed25519`
   - Verified Git SHA to deploy: `d854a5ef7471b74dab408473963a4511eab4dc66`
2. **Server 2 — AWS GPU Server:**
   - Host: `13.204.214.64`
   - Port: `8000/v1`
   - Model: `Qwen/Qwen2.5-7B-Instruct-AWQ`
   - Connectivity Status: **OFFLINE** (connection timeout)
   - Operational Rule: Zero automated modifications to AWS instance state.

---

## 2. Preflight Deployment Verification

Prior to presenting Gate 1 and Gate 2 approval prompts, the following preflight checks were completed:

| Check Category | Verification Procedure | Result | Status |
|---|---|---|---|
| Working Copy Hygiene | `git status --porcelain` | Clean / untracked test scripts segregated | **PASS** |
| Secret Exclusion | Scan for credentials, tokens, SSH keys | 0 secrets in commit diffs | **PASS** |
| Unit Test Regression | 126 backend tests + 16 frontend suites | 100% passing | **PASS** |
| Frontend Production Build | `npm run build` with Turbopack | 32 static pages generated in 1.1s | **PASS** |
| Benchmark Harness Parity | SHA-256 hash match against manifest | Matched | **PASS** |
| Git SHA Traceability | Traversal via `.git/HEAD` | HEAD: `d854a5ef7471b74dab408473963a4511eab4dc66` | **PASS** |

---

## 3. Human Approval Gate Readiness

The system stands ready to execute Gate 1 and Gate 2 prompts:
1. **Gate 1 Prompt:** `"Governance and security checks completed. Would you like to update the GitHub repository?"` (`YES` | `NO`).
2. **Gate 2 Prompt:** `"GitHub synchronization completed. Would you like to implement these changes on the remote server?"` (`YES` | `NO`).

Until the user issues explicit authorization, local verification remains authoritative and non-destructive.

---

## 4. Machine-Readable Identity

- Deployment manifest stored at: [DEPLOYMENT_IDENTITY_MANIFEST.json](file:///c:/Users/amits/OneDrive/Documents/SOC-AI-Agent/docs/AIS_2_6c/DEPLOYMENT_IDENTITY_MANIFEST.json)
