# 08. AUTHORIZED UPLA DEPLOYMENT ON SERVER 1 REPORT

## Verdictum AI — Agent Intelligence Studio 2.1a
**Execution Mode:** Authorized Multi-Server Remote Deployment via UPLA  
**Target Server:** Server 1 (`172.26.41.240`, Rocky Linux 10.1, `/opt/wysesoc-ai`)  
**Execution ID:** `upla-20261121-041339-6a8835`  
**Verified Git Commit SHA:** `f41c7a82c05ef98f4d4d12b5db8e57d002582522`  
**UPLA Profile:** `release`

---

## 1. Executive Summary

Deployment of AIS 2.1a was executed in strict adherence to the Universal Project Lifecycle Agent (UPLA) governance framework, requiring:
- Post-development governance and security validation.
- Zero unapproved mutations.
- **Human Approval Gate 1 (GitHub Synchronization):** Explicit authorization prior to pushing code.
- **Human Approval Gate 2 (Remote Deployment):** Explicit authorization prior to server mutation.
- Exact commit SHA verification on remote deployment source.
- Multi-server service verification and firewall configuration.

Both human approval gates were explicitly granted by the user, and the deployment completed with status **`DEPLOYED_AND_VERIFIED`**.

---

## 2. Gate 1 — GitHub Synchronization Approval

### Human Approval Interaction
- **Prompt:** `"Governance and security checks completed. Would you like to update the GitHub repository?"`
- **Target:** `https://github.com/Wysetek-ELK/WyseSOC-AI.git@feature/phase3-compact-ui`
- **User Decision:** `YES — Update GitHub Repository`
- **Recorded Approval Command:**
  ```powershell
  & ~/.gemini/config/plugins/upla/scripts/upla.ps1 record-approval `
      -ExecutionId "upla-20261121-041339-6a8835" `
      -Gate "GITHUB" `
      -Target "https://github.com/Wysetek-ELK/WyseSOC-AI.git@feature/phase3-compact-ui" `
      -Fingerprint "080c92da09a96ea5b10ecae251781b0a8867a57a522339d6756894c2e684070a" `
      -Decision "YES"
  ```
- **Git Push Verification:**
  - Branch: `feature/phase3-compact-ui`
  - Local HEAD SHA: `f41c7a82c05ef98f4d4d12b5db8e57d002582522`
  - Remote Origin SHA: `f41c7a82c05ef98f4d4d12b5db8e57d002582522`
  - Status: **SYNCHRONIZED AND VERIFIED**

---

## 3. Gate 2 — Remote Deployment Approval

### Human Approval Interaction
- **Prompt:** `"GitHub synchronization completed. Would you like to implement these changes on the remote server?"`
- **Target:** `server-1@f41c7a82c05ef98f4d4d12b5db8e57d002582522`
- **User Decision:** `YES — Implement on Remote Server 1`
- **Recorded Approval Command:**
  ```powershell
  & ~/.gemini/config/plugins/upla/scripts/upla.ps1 record-approval `
      -ExecutionId "upla-20261121-041339-6a8835" `
      -Gate "DEPLOYMENT" `
      -Target "server-1@f41c7a82c05ef98f4d4d12b5db8e57d002582522" `
      -Fingerprint "f41c7a82c05ef98f4d4d12b5db8e57d002582522" `
      -Decision "YES"
  ```

---

## 4. Remote Deployment Execution Log

Deployment executed to Server 1 (`172.26.41.240`):
1. **Target Directory:** `/opt/wysesoc-ai`
2. **Git Synchronization:**
   ```bash
   git fetch origin feature/phase3-compact-ui
   git checkout feature/phase3-compact-ui
   git reset --hard f41c7a82c05ef98f4d4d12b5db8e57d002582522
   ```
   Verified `git rev-parse HEAD` = `f41c7a82c05ef98f4d4d12b5db8e57d002582522`.
3. **Frontend Build:**
   ```bash
   npm --prefix frontend run build
   ```
   Turbopack completed compilation with 32/32 static routes.
4. **Service Restart & Health Checks:**
   ```bash
   sudo systemctl restart ai-verdict-backend
   sudo systemctl restart ai-verdict-frontend
   ```
   - `ai-verdict-backend.service`: Active (running), PID 36566, listening on port 8000.
   - `ai-verdict-frontend.service`: Active (running), PID 36579, listening on port 3000.
5. **Firewalld Port Configuration:**
   Rocky Linux firewall initially blocked external access to port 3000.
   ```bash
   firewall-cmd --add-port=3000/tcp --permanent
   firewall-cmd --reload
   ```
   External HTTP reachability confirmed on `http://172.26.41.240:3000`.

---

## 5. Deployment Record Summary

```json
{
  "execution_id": "upla-20261121-041339-6a8835",
  "status": "DEPLOYED_AND_VERIFIED",
  "deployed_commit_sha": "f41c7a82c05ef98f4d4d12b5db8e57d002582522",
  "server": "server-1 (172.26.41.240)",
  "services": [
    {"name": "ai-verdict-backend", "status": "active", "port": 8000},
    {"name": "ai-verdict-frontend", "status": "active", "port": 3000}
  ],
  "gates_passed": ["GATE_1_GITHUB", "GATE_2_REMOTE_DEPLOYMENT"],
  "completed_at": "2026-11-21T04:20:00Z"
}
```
