# VERDICTUM AI — VALIDATION V1.2.1
## 03. FRONTEND UI SAFETY & RBAC FIXES

**Document Version:** 1.0.0  
**Target Components:** `AgentIntelligenceStudioOverview.tsx`, `page.tsx`  
**Status:** COMPLETE & VERIFIED  

---

### 1. Overview of Frontend UI Safety Hardening

Frontend safety hardening addressed three primary failure modes:
1. **Conflated Governance Badges:** A rule whose version was approved displayed `ACTIVE PRODUCTION` even when revalidation was required due to failing gates or missing reviews.
2. **Premature & Active Approval Controls:** Approval action buttons remained clickable or gave the impression that candidate policies could be deployed despite incomplete quality gates.
3. **Read-Only Viewer Action Exposure:** Viewer sessions previously displayed active mutation buttons that triggered unexpected 403 API errors upon click.

---

### 2. Detailed Component Refactors

#### A. Decoupled Lifecycle Badges (`AgentIntelligenceStudioOverview.tsx`)
In the studio overview hero card, the four lifecycle dimensions are rendered separately:
- **SIEM Status:** Indicates FortiSIEM collector rule status (`ACTIVE` / `DISABLED`).
- **Active Policy Baseline:** Indicates currently active baseline version (e.g. `v1 (Approved Baseline)`).
- **Candidate Version:** Indicates evaluated draft (e.g. `v3 (Draft)`).
- **Readiness Status:**
  - `ACTIVE`: Rendered ONLY when 8/8 gates pass and >= 30 verified analyst reviews exist.
  - `APPROVED BASELINE (REVALIDATION REQUIRED)`: Rendered when a version is approved, but automated revalidation is incomplete.
  - `APPROVAL ELIGIBLE`: Rendered when a candidate draft meets all 8 gates and 30 reviews.
  - `SUPERVISED LEARNING`: Rendered when empirical analyst reviews are in progress.
  - `BLOCKED / INCOMPLETE`: Rendered when hard quality gates fail.

#### B. Guarded Approval Buttons with "View Requirements" Action
Both in the top toolbar and in Stage 6 of the Guided Readiness Checklist:
- If `!effectiveApprovalEligible || isViewer`:
  - Button text: `"Approval Blocked"`
  - Attribute: `disabled={true}`
  - Styling: `bg-slate-900 text-slate-500 border-slate-800 cursor-not-allowed`
  - Tooltip: `"Approval blocked — X mandatory checks incomplete"` (or viewer-specific explanation)
  - Secondary action: `"View Requirements"` link immediately adjacent, which scrolls smoothly to `#guided-readiness-checklist`.

#### C. Stage 6 Guided Readiness Item Refactor
Stage 6 ("Production Approval") in `AgentIntelligenceStudioOverview.tsx`:
```typescript
{
  stage_id: "production_approval",
  stage_name: "Production Approval",
  stage_number: 6,
  status: (selectedVersion?.status === "APPROVED" && passedGates === 8)
    ? "COMPLETED"
    : effectiveApprovalEligible
    ? "NEEDS_ACTION"
    : "BLOCKED",
  simple_explanation: "Formal governance gate: verifies that all quality criteria pass before an authorized administrator signs off on production deployment.",
  missing_requirement: !effectiveApprovalEligible && selectedVersion?.status !== "APPROVED"
    ? `Approval blocked — ${blockingReqCount} mandatory checks incomplete.`
    : null,
  next_action: effectiveApprovalEligible
    ? "All prerequisite quality criteria satisfied. Ready for administrator sign-off."
    : "Resolve blocking stages above to enable approval.",
  action_button: effectiveApprovalEligible
    ? { label: "Approve Policy", action: "request_approval", target_tab: "overview" }
    : { label: "Approval Blocked", action: "request_approval", target_tab: "overview" },
  technical_details: {},
}
```

In the stage list rendering:
```typescript
{stage.action_button && (
  <button
    type="button"
    disabled={stage.stage_id === "production_approval" ? (!effectiveApprovalEligible || isViewer) : false}
    onClick={() => handleStageAction(stage)}
    title={
      stage.stage_id === "production_approval"
        ? isViewer
          ? "Read-Only Viewer cannot approve policies (requires Administrator role)"
          : !effectiveApprovalEligible
          ? `Approval blocked — ${blockingReqCount} mandatory checks incomplete`
          : "Approve policy for production baseline"
        : undefined
    }
    className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold inline-flex items-center gap-1 transition-colors ${
      stage.stage_id === "production_approval" && (!effectiveApprovalEligible || isViewer)
        ? "bg-slate-900/60 text-slate-500 border border-slate-800 cursor-not-allowed opacity-60"
        : "bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700"
    }`}
  >
    {stage.action_button.label} <ArrowRight className="w-3 h-3 text-cyan-400" />
  </button>
)}
```

#### D. Candidate Version URL Parameter Binding (`page.tsx`)
In `fetchPrompt(ruleId)`:
```typescript
if (rp.versions && rp.versions.length > 0) {
  let targetId = rp.active_version_id || rp.versions[0].id;
  if (typeof window !== "undefined") {
    const params = new URLSearchParams(window.location.search);
    const urlVer = params.get("version_id") || params.get("versionId");
    if (urlVer && rp.versions.some((v) => v.id === urlVer)) {
      targetId = urlVer;
    }
  }
  setSelectedVersionId(targetId);
  loadVersionIntoForm(rp.versions.find((v) => v.id === targetId) || rp.versions[0]);
}
```
This ensures direct linking to specific versions (such as candidate Draft v3) correctly loads that candidate version, evaluates its specific quality assessment, and binds the appropriate UI controls.

#### E. RBAC Viewer Lockout
Across all mutating buttons (`Synthesize Draft`, `Validate Quality`, `Simulation`, `Approve`):
- Added `|| isViewer` to `disabled` attributes.
- Added descriptive viewer tooltips indicating required roles (`SOC Analyst` or `Administrator`).

---

### 3. Visual & Functional Assertions
DOM validation confirmed across headless browser sessions:
- `hasBlockedBadge: true`
- `hasViewRequirements: true`
- `approveBtnText: "Approval Blocked"`
- `isApproveDisabled: true`
- `isSynthDisabled: true` (viewer)
