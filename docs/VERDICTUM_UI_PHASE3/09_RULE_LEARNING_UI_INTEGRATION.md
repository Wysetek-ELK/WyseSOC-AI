# VERDICTUM AI — PHASE 3
# 09. Rule Learning & Ground Truth Integration Specification

**Document Version:** 3.0.0  
**Phase:** Phase 3 — Unified Compact UI/UX Modernization  
**Component Implementation:** `frontend/src/components/learning/RuleLearningDashboard.tsx`  
**Parent Page Integration:** `frontend/src/app/agent-intelligence-studio/page.tsx` (Tab 2)  

---

## 1. Overview & Objectives

Rule Learning is the continuous statistical engine that evaluates how accurately synthesized detection policies classify threats against verified human ground truth. It acts as the mathematical gateway for the G8 Quality Gate and governs automated production promotion.

In Phase 3, Rule Learning is fully integrated into **Tab 2 (Analyst Review & Learning)** of Agent Intelligence Studio 2.0, providing a bi-directional data loop between human review and policy governance.

---

## 2. Real-Time State Synchronization (`onProfileUpdate`)

Previously, submitting reviews in the learning tab did not immediately notify the parent studio, requiring manual page refreshes to update quality scores and operational status badges.

Phase 3 introduces the `onProfileUpdate` callback interface:
```typescript
export interface RuleLearningDashboardProps {
  ruleId: string;
  ruleName?: string;
  onProfileUpdate?: (profile: any) => void;
}
```
Whenever an analyst submits a review, resolves a dispute, or triggers a lifecycle stage recalculation:
1. `RuleLearningDashboard` updates its local confusion matrix and progress metrics.
2. It invokes `onProfileUpdate(profile)` to emit the updated learning profile back to `AgentIntelligenceStudioPage`.
3. The parent studio immediately updates:
   - The Top Hero Reviews count.
   - Empirical Accuracy card.
   - Operational Status Badge (`LEARNING_IN_PROGRESS` -> `READY_FOR_VALIDATION` -> `PRODUCTION_APPROVAL_PENDING`).
   - Active diagnostic blockers in Tab 1.

---

## 3. Ground Truth Sample-Size Progress & Gating

Statistical reliability requires sufficient sample sizes before autonomous actions are authorized:
- **Pilot Automation Threshold (30 Verified Samples):**
  - Requires $\ge 30$ verified analyst evaluations.
  - Requires empirical accuracy $\ge 85\%$.
  - Progress bar visually tracks reviews: `[======    ] 18 / 30 Reviews`.
- **Production Autonomous Promotion (100 Verified Samples):**
  - Requires $\ge 100$ verified analyst evaluations.
  - Requires empirical accuracy $\ge 95\%$.
  - Zero unresolved false-positive closures.

If verified review count is 0:
- Accuracy displays `N/A (Requires verified analyst reviews)`.
- The confusion matrix clearly indicates that the model is in supervised baseline learning mode.

---

## 4. Production Eligibility Checklist (`ProductionEligibilityChecklist`)

Positioned within the learning dashboard, this checklist provides full transparency regarding promotion blockers:
- Displays only criteria currently unfulfilled (preventing visual clutter).
- Clear checkmark (`✓`) for met criteria and warning circle (`⚠`) for pending items.
- Highlights exact sample deficits (e.g. *"Needs 12 more verified analyst reviews"*).
