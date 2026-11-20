# Report 02 — Double-Blind Security & Masking Validation
**Verdictum AI — AIS 2.0 Server-Side Enforcement & RBAC Security**
**Date:** November 20, 2026  
**Status:** VALIDATED & ENFORCED  
**Security Boundary:** Server 1 (`172.26.41.240`) FastAPI Backend & Next.js Frontend  

---

## 1. Executive Summary

This report establishes the security boundaries, authorization controls, and server-side masking guarantees for Double-Blind Review in Verdictum AI. Client-side hiding of AI determinations is insufficient for empirical governance; masking must be non-bypassable and enforced by the server before JSON transmission.

All pre-submission API endpoints have been verified to redact model predictions, confidence scores, chain-of-thought rationale, and agreement indicators.

---

## 2. Server-Side Masking Policy (The Contract)

### 2.1 Permitted Data (Pre-Submission)
Before an independent analyst determination is successfully received and persisted, the server and UI permit only:
- **Incident Metadata:** `incident_id`, `rule_id`, `rule_uuid`, `title`, `event_type`, `severity`, `customer`, `created_at`.
- **Network Observables:** `source_ip`, `destination_port`, `reporting_device`.
- **Raw Security Logs:** Unedited FortiGate UTM event logs, HTTP request URI, FortiGuard category, firewall policy action (`PASSED`, `BLOCKED`, `DROPPED`).
- **Normalized Evidence Artifacts:** Structured key-value telemetry pairs with explicit evidence IDs (e.g., `EV-01: DestinationDomain`, `EV-02: WebCategory`).
- **Approved Business Exception Records:** Authoritative change tickets or intranet whitelist exceptions, if present in FortiSIEM.

### 2.2 Strictly Forbidden Data (Pre-Submission)
The server strictly suppresses and purges:
- ❌ Raw or effective AI verdict (`TRUE_POSITIVE`, `FALSE_POSITIVE`, `REQUIRES_ATTENTION`).
- ❌ AI confidence score and probability distributions.
- ❌ Local LLM explanation, chain-of-thought, or summary text.
- ❌ AI trust score and hallucination risk markers.
- ❌ Agreement indicators (`AGREEMENT_TP`, `AI_FALSE_ALARM`, `CRITICAL_MISSED_TP`).
- ❌ Prompt template previews or prompt capture completions for the unreviewed incident.

---

## 3. Server-Side Enforcement Architecture

### 3.1 `AnalystReviewService.get_pending_reviews`
When querying the pending review queue (`GET /api/reviews/pending`), the backend builds the response items with explicit projection:
```python
items.append({
    "incident_id": inc.incident_id,
    "db_id": inc.id,
    "rule_id": inc.rule_id or inc.event_type,
    "title": inc.title,
    "event_type": inc.event_type,
    "severity": inc.severity,
    "customer": inc.customer,
    "source_ip": src_ip,
    "destination_port": dest_port,
    "incident_detail": inc_detail,
    "reporting_device": rpt_dev,
    "raw_events_count": len(evts),
    "created_at": inc.created_at.isoformat() if inc.created_at else None,
    "investigation_status": inv.status if inv else "PENDING_REVIEW",
    "analyst_verdict": inv.analyst_verdict if inv else None,
    "is_disputed": bool(getattr(inv, "is_disputed", False)) if inv else False,
    "is_blind_mode": True,  # AI verdict, confidence, and rationale strictly excluded
})
```
No AI determination keys exist in the serialization dictionary.

### 3.2 `IncidentService.get_incident`
When fetching full incident details (`GET /api/incidents/{id}?blind_review=true`), access to `ai_verdict` is guarded by `can_see_verdict`:
```python
norm_role = (user_role or "").strip().lower()
if is_admin:
    can_see_verdict = has_analyst_review if blind_review else True
elif norm_role in ("soc analyst", "analyst", "security analyst", "senior analyst", "soc_analyst", "senior_analyst"):
    can_see_verdict = has_analyst_review
else:
    can_see_verdict = False

safe_ai_verdict = (
    VerdictTrustworthinessEngine.normalize_ai_verdict_dict(inc.ai_verdict) if can_see_verdict
    else None
)
```
For any analyst, `can_see_verdict` evaluates to `False` unless this specific analyst has already submitted a review for this incident. Passing `?blind_review=false` by an analyst is ignored.

---

## 4. Role-Based Access Control (RBAC) & Tenant Boundaries

1. **Submission Authorization:** `POST /api/reviews/{incident_id}/submit` depends on `require_analyst`.
   - `Administrator`: Allowed.
   - `SOC Analyst`: Allowed.
   - `Read-Only Viewer`: Denied with **HTTP 403 Forbidden**.
2. **Tenant Scoping:**
   - Multi-tenant customer scoping is strictly enforced. If an analyst assigned to tenant `GDC_NOC` attempts to review an incident belonging to tenant `Demo-SOC`, the service raises `ValueError("Access denied: Incident belongs to customer 'Demo-SOC'...")` resulting in **HTTP 403 Forbidden**.
3. **Dispute Adjudication:** `POST /api/reviews/{review_id}/adjudicate` is restricted to `Administrator`, `SOC_Manager`, or `Senior_Analyst`. Standard Tier-1 analysts cannot adjudicate conflicting reviews.

---

## 5. Elimination of Pre-Submission Prompt Inspection Leakage

In previous iterations, `ReviewIncidentsWorkbench.tsx` included a header button labeled "Inspect Payload" that invoked the actual prompt inspector. Although un-wired, opening that modal would have displayed the LLM prompt capture along with the model's completion verdict.

**Correction Implemented:**
- The pre-submission header button was completely removed.
- A safe post-submission button, **"Inspect LLM Prompt Capture"**, was placed exclusively inside the `{revealedResult && (...)}` container.
- An analyst can only inspect the full LLM prompt and response *after* their own determination is persisted in PostgreSQL.
