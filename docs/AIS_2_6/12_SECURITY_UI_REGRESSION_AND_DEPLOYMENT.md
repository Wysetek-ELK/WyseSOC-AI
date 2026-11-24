# 12 — Security, UI, Regression and Deployment Report

## Executive Summary

This report documents the security audit of GPU infrastructure, UI component stability under the Agent Intelligence Studio compact interface, the full regression suite status, and live production deployment verification on Server 1.

---

## 1. GPU Security & Architecture Audit

### 1.1 Ingress & Port Security
- **Server 2 vLLM Port 8000**: Filtered strictly to Server 1 (`172.26.41.240`). Direct ingress from the public internet or external subnets is denied by AWS Security Group rules.
- **Cleartext HTTP**: Traffic between Server 1 and Server 2 flows across the AWS VPC internal network. In AIS 2.7, mutual TLS (mTLS) or reverse-proxy HTTPS will be enabled for zero-trust compliance.
- **API Authentication**: Server 2 vLLM currently does not enforce an `--api-key` bearer token, relying on network security group isolation. AIS 2.7 will introduce mandatory token authentication.

---

## 2. Compact UI & Analyst Workflow Verification

### 2.1 Three-Tab Layout Preservation
The Agent Intelligence Studio three-tab interface was preserved without structural modification:
1. **Rule Intelligence Tab**: Displays rule contracts, behavioral archetypes, and required fields.
2. **Policy Studio Tab**: Displays prompt templates, compiler versions, and approved revisions.
3. **Evaluation Matrix Tab**: Displays empirical metrics, coverage rates, Wilson confidence intervals, and execution logs.

### 2.2 Blind Certification UI Controls
- When an incident has not received independent certification, the UI surfaces a clear `NOT_MEASURED` badge rather than showing misleading 0% or 100% scores.
- Frontend builds cleanly: `32/32 routes` compiled via Next.js 16.4 Turbopack.

---

## 3. Remote Deployment & Health Verification

- **Deployed SHA**: `71bf3ba2969e3082c9e2d6b522abdaaef2613c80`
- **Server 1 Target**: `root@172.26.41.240:/opt/wysesoc-ai`
- **Deployment Status**: `DEPLOYED_AND_VERIFIED`
- **Health Checks**:
  - `ai-verdict-backend.service`: Active (healthy)
  - `ai-verdict-frontend.service`: Active (healthy)
  - `/api/health`: HTTP 200 OK
  - `/login`: HTTP 200 OK
