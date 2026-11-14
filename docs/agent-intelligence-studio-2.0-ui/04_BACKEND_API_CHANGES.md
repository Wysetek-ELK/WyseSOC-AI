# 04 - Backend API Changes

## 1. Overview of API Modifications

To support the simplified 3-Tab Studio, the compact readiness column in rule catalogs, and authoritative evidence-based readiness evaluation, the following backend APIs were implemented and enhanced.

---

## 2. New Endpoints

### 2.1 `GET /api/prompts/rule/{rule_id}/readiness`

Returns the authoritative, structured production readiness evaluation for a detection rule and specific candidate version.

- **Authentication:** Bearer JWT token (`User` required: L1 Viewer, Analyst, or Admin).
- **Parameters:**
  - `rule_id` (path, string): Canonical UUID or string identifier of the rule.
  - `version_id` (query, optional): Specific `PromptVersion` UUID. If omitted, defaults to candidate draft, otherwise active version.
  - `customer` (query, optional): Multi-tenant partition key (default `"DEFAULT"`).

- **Response Body (`ProductionReadinessResponse`):**
```json
{
  "rule_id": "rule_heavy_tcp_test_001",
  "rule_name": "Heavy TCP Host Scan On Fixed Port",
  "rule_identifier": "RULE-HEAVY-TCP-SCAN",
  "severity": "HIGH",
  "detection_archetype": "NETWORK_SCAN",
  "detection_description": "Network Scan detection: monitors multiple connection attempts...",
  "version_id": "v-uuid-1234",
  "version_number": 2,
  "version_status": "DRAFT",
  "rule_deployment_status": "ACTIVE",
  "deployment_status": "ACTIVE",
  "active_version_number": 1,
  "active_version_status": "APPROVED",
  "readiness_status": "BLOCKED",
  "readiness_label": "BLOCKED / INCOMPLETE",
  "readiness_progress": 33,
  "quality_score": 48.0,
  "quality_gates_passed": 1,
  "total_quality_gates": 8,
  "verified_reviews_count": 0,
  "required_reviews_count": 30,
  "production_reviews_target": 100,
  "approval_eligible": false,
  "last_evaluated_at": "2026-11-14T12:00:00Z",
  "stages": [
    {
      "stage_id": "define_detection",
      "stage_name": "1. Define Detection",
      "stage_number": 1,
      "status": "BLOCKED",
      "simple_explanation": "Verifies the FortiSIEM correlation conditions...",
      "missing_requirement": "Detection rule lacks authoritative correlation thresholds.",
      "next_action": "Verify and define correlation threshold in FortiSIEM rule semantics.",
      "action_button": {
        "label": "Inspect Semantics",
        "action": "open_tab",
        "target_tab": "advanced",
        "target_section": "intelligence"
      },
      "technical_details": {
        "definition_status": "INCOMPLETE",
        "primary_archetype": "NETWORK_SCAN"
      }
    }
  ],
  "recommended_action": {
    "title": "Verify FortiSIEM Detection Semantics",
    "description": "Rule definition lacks authoritative correlation thresholds.",
    "label": "Inspect Semantics",
    "target_tab": "advanced",
    "target_section": "intelligence",
    "action_type": "NAVIGATE",
    "status": "warning"
  },
  "gate_results": { ... },
  "blocking_requirements": ["G1_RULE_DEFINITION_INCOMPLETE"],
  "warnings": [],
  "supporting_evidence_references": ["srcIp", "destIp", "destPort", "count"],
  "metrics": {
    "empirical_accuracy": null,
    "fp_precision": null,
    "wilson_lower_bound": null,
    "tp_recall": null,
    "verified_tp_count": 0,
    "verified_fp_count": 0,
    "total_analyst_reviews": 0,
    "unacknowledged_drift_events": 0
  }
}
```

---

## 3. Modified Endpoints

### 3.1 `GET /api/prompts/summary`

Enhanced to compute and return production readiness metadata for every monitored rule in bulk.

- **Changes:**
  - Added dynamic fallback: If no `RuleIntelligenceSnapshot` exists for a rule, it invokes `RuleIntelligenceAnalyzer.analyze_rule` and `DetectionArchetypeRegistry.classify_rule` rather than falsely defaulting to `"UNKNOWN"`.
  - Added new response fields to `RulePromptSummaryItem`:
    - `production_readiness_status`: String (`INCOMPLETE`, `BLOCKED`, `LEARNING`, `VALIDATING`, `READY_FOR_APPROVAL`, `APPROVED`, `ACTIVE`).
    - `gates_passed_count`: Integer count of passed gates (0–8).
    - `missing_requirements_count`: Count of active blocking issues.
    - `recommended_action_title`: Human-readable title of prioritized next action.
  - Ensured `revalidation_required` evaluates strictly to boolean (`bool(...)`), eliminating validation errors on unversioned rules.

### 3.2 `GET /api/rules`

Enhanced to support compact readiness indicators and server-side filtering on rule directories.

- **Changes:**
  - Added query parameter `readiness`: Optional string (`ALL`, `BLOCKED`, `LEARNING`, `VALIDATING`, `READY_FOR_APPROVAL`, `APPROVED`, `ACTIVE`).
  - Filters rules server-side according to computed readiness status.
  - Added new response fields to `RuleResponse`:
    - `production_readiness_status`: String.
    - `gates_passed_count`: Integer.
    - `missing_requirements_count`: Integer.

---

## 4. Pydantic Schemas Added & Extended

Located in `backend/app/schemas/production_readiness.py`:

```python
class ReadinessStatus(str, Enum):
    INCOMPLETE = "INCOMPLETE"
    BLOCKED = "BLOCKED"
    LEARNING = "LEARNING"
    VALIDATING = "VALIDATING"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"

class StageStatus(str, Enum):
    COMPLETED = "COMPLETED"
    NEEDS_ACTION = "NEEDS_ACTION"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"

class ActionButton(BaseModel):
    label: str
    action: str
    target_tab: Optional[str] = "overview"
    target_section: Optional[str] = None

class ReadinessStageItem(BaseModel):
    stage_id: str
    stage_name: str
    stage_number: int
    status: StageStatus
    simple_explanation: str
    missing_requirement: Optional[str] = None
    next_action: str
    action_button: ActionButton
    technical_details: Dict[str, Any] = Field(default_factory=dict)

class SmartNextAction(BaseModel):
    title: str
    description: str
    label: str
    target_tab: str = "overview"
    target_section: Optional[str] = None
    action_type: str = "NAVIGATE"
    status: str = "primary"
```

---

## 5. Backward Compatibility & RBAC Verification

1. **Client Compatibility:**
   - Pre-existing consumers of `/api/rules` and `/api/prompts/summary` continue to parse all existing fields without breaking changes.
   - Both `rule_deployment_status` and `deployment_status` are present in `ProductionReadinessResponse` to accommodate all client conventions.
2. **RBAC Guardrails:**
   - Reading readiness status requires authenticated user (`get_current_active_user`).
   - Editing policies and submitting reviews requires `require_analyst`.
   - Approving candidate versions requires `require_admin`.
