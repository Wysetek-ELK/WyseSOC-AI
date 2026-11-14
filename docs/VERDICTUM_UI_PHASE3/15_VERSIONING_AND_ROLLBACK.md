# VERDICTUM AI — PHASE 3
# 15. Versioning, Feature Toggles & Safe Rollback Guide

**Document Version:** 3.0.0  
**Phase:** Phase 3 — Unified Compact UI/UX Modernization  
**Safety Baseline Commit:** `33aa27d`  
**Feature Branch:** `feature/phase3-compact-ui`  

---

## 1. Overview & Architecture

To satisfy strict enterprise change-management requirements, Phase 3 implements a **Zero-Downtime Safe Rollback Architecture**. 

The migration features two complementary layers of rollback safety:
1. **Client-Side Runtime Feature Flag (`VERDICTUM_COMPACT_UI_ENABLED`):** Allows any individual SOC analyst or administrator to switch between the new Compact Experience and the legacy 7-tab interface on demand with zero code changes or deployment delays.
2. **Git Version Control Safeguards:** The baseline commit `33aa27d` remains pristine on branch `feature/phase3-compact-ui`, enabling atomic Git rollbacks if required.

---

## 2. Runtime Rollback via Feature Toggle

The client-side toggle is implemented in `frontend/src/app/agent-intelligence-studio/page.tsx`:

```typescript
const [compactUi, setCompactUi] = useState(true);

useEffect(() => {
  if (typeof window !== "undefined") {
    const saved = localStorage.getItem("VERDICTUM_COMPACT_UI_ENABLED");
    if (saved === "false") {
      setCompactUi(false);
    }
  }
}, []);
```

### How to Toggle Views:
1. **In the UI:** Click the `"Legacy 7-Tab View"` button in the header toolbar to immediately return to the legacy layout. To return to the modernized view, click `"Compact View"`.
2. **Via Browser Developer Console:**
   ```javascript
   // Switch back to legacy layout instantly
   localStorage.setItem("VERDICTUM_COMPACT_UI_ENABLED", "false");
   location.reload();

   // Switch to modern compact layout
   localStorage.setItem("VERDICTUM_COMPACT_UI_ENABLED", "true");
   location.reload();
   ```

---

## 3. Git Emergency Rollback Protocol

If an unexpected production defect requires reverting the entire codebase:

### Step 1: Verify Current Clean State
```powershell
git status
```

### Step 2: Atomic Rollback to Baseline Commit
```powershell
# Reset working directory and commit tree to the verified baseline
git checkout 33aa27d
```

### Step 3: Rebuild Frontend
```powershell
npm --prefix frontend run build
```

---

## 4. Policy Version History & Safe Rollbacks

In addition to frontend layout rollback, the platform provides full operational policy rollback:
- In `CompactVersionSelector`, analysts can select any historical policy version (e.g. `v1 (APPROVED)` or `v2 (ARCHIVED)`).
- Clicking the `"Rollback to This"` button invokes `api.rollbackRulePromptVersion(ruleId, versionId)`.
- The system atomically reactivates the previous approved policy baseline, recreates the Evidence Contract, and updates the cryptographic audit log.
