# 08. SECURITY, RBAC, AND DOUBLE-BLIND REVIEW ENFORCEMENT

## Verdictum AI — Agent Intelligence Studio 2.1
**Powered by WYSETEK Systems**

---

## 1. Executive Summary

In autonomous and AI-assisted Security Operations Center (SOC) environments, model evaluation integrity relies entirely on uncontaminated ground truth. If human analysts can observe model predictions before rendering their determinations, cognitive confirmation bias severely skews evaluation accuracy. Furthermore, enterprise multi-tenancy and administrative controls require strict Role-Based Access Control (RBAC) and data isolation.

This document specifies the security controls, RBAC matrices, and double-blind isolation mechanisms implemented in **Agent Intelligence Studio 2.1**.

---

## 2. Double-Blind Review Isolation Architecture

### 2.1 Core Invariant
**No SOC analyst may view model inference verdicts, confidence scores, reasoning chains, or LLM explanations for any incident before submitting their independent, authoritative ground-truth determination.**

```
┌────────────────────────────────────────────────────────────────────────┐
│                        INCIDENT REVIEW PIPELINE                        │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                                     ▼
                   ┌───────────────────────────────────┐
                   │    Has Current Analyst Submitted  │
                   │     Ground Truth Determination?   │
                   └─────────────────┬─────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │                                 │
                 NO │                                 │ YES
                    ▼                                 ▼
      ┌───────────────────────────┐     ┌───────────────────────────┐
      │   DOUBLE-BLIND ISOLATION  │     │      BLINDING LIFTED      │
      │ • AI Verdicts: HIDDEN     │     │ • AI Verdict: REVEALED    │
      │ • Confidence: MASKED      │     │ • Confidence: REVEALED    │
      │ • Reasoning Chain: MASKED │     │ • Reasoning: REVEALED     │
      │ • Prompt Capture: LOCKED  │     │ • Comparison: DISPLAYED   │
      └───────────────────────────┘     └───────────────────────────┘
```

### 2.2 Technical Enforcement
1. **API Level Masking:**
   - In `AisEvaluationService`, unreviewed incidents return `effective_verdict: null` and `is_masked: true` when queried by non-administrative users.
   - Verified via unit test `test_13_double_blind_protection_unreviewed_incident_masks_verdicts`.
2. **Frontend Shielding:**
   - In `ReviewIncidentsWorkbench.tsx`, the `AnalystDeterminationForm` renders in an isolated pane. AI inference outputs are not mounted in the DOM until the `analyst_verdict_reviews` record is committed to PostgreSQL.
3. **Audit Provenance:**
   - The timestamp of analyst review submission (`reviewed_at`) is cryptographically compared against LLM execution timestamps (`created_at`) to mathematically verify that the human review preceded the unblinding event.

---

## 3. Role-Based Access Control (RBAC) Matrix

| Studio Capability | Read-Only Viewer | SOC Analyst | SOC Lead / Administrator | Enforcement Mechanism |
| :--- | :---: | :---: | :---: | :--- |
| **View Incidents & Evidence** | Allowed | Allowed | Allowed | Frontend UI / API GET |
| **Submit Ground Truth Review** | DENIED | Allowed | Allowed | `POST /api/reviews` (403 for Viewer) |
| **Execute Single AI Test** | DENIED | Allowed | Allowed | `POST /api/ai/test` (403 for Viewer) |
| **Inspect Actual LLM Prompt** | DENIED | Allowed (Reviewed only) | Allowed (All) | Double-Blind Masking Service |
| **Trigger Batch Inference** | DENIED | DENIED | Allowed | `POST /api/ais/evaluation/batch` (Admin only) |
| **Author Policy Prompts** | DENIED | DENIED | Allowed | `PUT /api/prompts/rule/{id}` (Admin only) |
| **Synthesize Intelligent Draft** | DENIED | DENIED | Allowed | `POST /api/prompts/synthesize` (Admin only) |
| **Validate Quality Gates (G1–G8)**| Allowed (Preview) | Allowed (Preview)| Allowed (Persist) | `POST /api/quality/validate` |
| **Approve Policy for Production** | DENIED | DENIED | Allowed | `POST /api/prompts/approve` (Admin only) |
| **Activate Approved Policy** | DENIED | DENIED | Allowed | `POST /api/prompts/.../activate-approved` |
| **Revert / Rollback Policy** | DENIED | DENIED | Allowed | `POST /api/prompts/rollback` (Admin only) |
| **Access Settings Workbench** | Allowed (Read) | Allowed (Read) | Allowed (Full) | Route & Module Guards |

---

## 4. Multi-Tenant Scoping & Data Isolation

### 4.1 Tenancy Architecture
FortiSIEM environments ingest telemetry from multiple customer organizations (e.g., `GDC_NOC`, `Demo-SOC`, `Enterprise-Prod`).
- Standard tenant users are cryptographically scoped to their assigned customer tenant ID.
- Global SOC Administrators have cross-tenant governance authority.
- The evaluation service (`AisEvaluationService`) checks `current_user.is_admin_user`. If admin, multi-tenant FortiSIEM records across all customer organizations are aggregated for rule-level evaluation without dropping tenant-specific records.

### 4.2 Cross-Tenant Contamination Defense
- Incident queries enforce parameterized SQLAlchemy filters: `Incident.customer == target_customer` for tenant users.
- Tenant isolation verified via unit test `test_16_tenant_isolation_enforced`.

---

## 5. Prompt Injection Defense & Evidence Isolation

1. **Schema Bounding:**
   - Raw FortiSIEM log fields are sanitized and strictly validated against `CanonicalEvidenceRecord`.
   - Untrusted payload strings (e.g., HTTP headers, URI parameters, command lines) cannot break JSON structuring.
2. **Context Escaping:**
   - Model prompt templates strictly enclose untrusted incident data in fenced `<incident_evidence>` XML blocks.
   - Policy instructions are compiled before runtime; runtime incident evidence cannot alter policy instructions or system directives.
