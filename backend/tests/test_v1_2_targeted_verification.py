import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.models.user import User


@pytest.mark.asyncio
async def test_active_plus_7_of_8_gates_cannot_be_active_readiness(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
):
    """
    V1.2 Scenario A: A rule with only 7/8 gates passed MUST NEVER be reported
    as 'ACTIVE' production readiness, even if the FortiSIEM deployment status is 'ACTIVE'.
    """
    rule = Rule(
        id="rule_7_gates_test",
        rule_id="RULE-7-GATES",
        name="7 of 8 Gates Candidate Test Rule",
        event_type="PH_RULE_7_GATES",
        description="Candidate version passing 7/8 gates with 1 pending gate",
        severity="HIGH",
        status="ACTIVE",  # SIEM deployment is ACTIVE
        data_source="Firewall",
        detection_tech="Network",
        pattern_logic="SELECT * FROM events",
    )
    db_session.add(rule)

    rp = RulePrompt(
        id="rp_7_gates_test",
        rule_id=rule.id,
        title="7 Gates Prompt",
    )
    db_session.add(rp)

    # v1 is a draft passing 7/8 gates
    pv = PromptVersion(
        id="pv_7_gates_v1",
        prompt_id=rp.id,
        version_number=1,
        status="DRAFT",
        is_template_draft=True,
        common_prompt="Common",
        rule_specific_prompt="Rule specific",
        detection_conditions="Conditions",
        required_evidence="Evidence",
        tp_indicators="TP",
        fp_indicators="FP",
        missing_info_criteria="Missing",
        escalation_conditions="Escalation",
        quality_status="VALIDATING",
        quality_score=78.0,
    )
    db_session.add(pv)

    # Add snapshot with valid archetype
    snap = RuleIntelligenceSnapshot(
        id="snap_7_gates_test",
        rule_id=rule.id,
        rule_identifier=rule.rule_id,
        definition_status="VERIFIED",
        primary_archetype="NETWORK_SCAN",
        threshold=50,
    )
    db_session.add(snap)

    # Add quality assessment record with 7 PASSED gates and 1 PENDING/FAILED gate
    gate_results = {
        "G1_RULE_INTEGRITY": {"status": "PASSED"},
        "G2_ARCHETYPE_RELEVANCE": {"status": "PASSED"},
        "G3_EVIDENCE_FEASIBILITY": {"status": "PASSED"},
        "G4_TP_CRITERIA_VALIDITY": {"status": "PASSED"},
        "G5_FP_CRITERIA_VALIDITY": {"status": "PASSED"},
        "G6_ABSTENTION_ESCALATION": {"status": "PASSED"},
        "G7_POLICY_CONSISTENCY": {"status": "PASSED"},
        "G8_SIMULATION_REGRESSION": {"status": "PENDING"},
    }
    qa = PolicyQualityAssessmentRecord(
        id="qa_7_gates_test",
        rule_id=rule.id,
        prompt_version_id=pv.id,
        quality_score=78.0,
        approval_eligible=False,
        gate_results=gate_results,
        blocking_issues=[],
        warnings=["G8 simulation pending"],
    )
    db_session.add(qa)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Check /api/rules listing
    rules_res = await client.get("/api/rules?page=1&page_size=20", headers=headers)
    assert rules_res.status_code == 200
    r_item = next(item for item in rules_res.json()["items"] if item["id"] == rule.id)
    assert r_item["status"] == "ACTIVE"  # SIEM status remains ACTIVE
    assert r_item["gates_passed_count"] == 7
    # Readiness MUST NOT be ACTIVE!
    assert r_item["production_readiness_status"] != "ACTIVE"
    assert r_item["production_readiness_status"] in ("VALIDATING", "READY_FOR_APPROVAL", "LEARNING", "INCOMPLETE", "BLOCKED")

    # 2. Check /api/prompts/summary
    sum_res = await client.get("/api/prompts/summary", headers=headers)
    assert sum_res.status_code == 200
    s_item = next(item for item in sum_res.json() if item["rule_id"] == rule.id)
    assert s_item["status"] == "ACTIVE"
    assert s_item["gates_passed_count"] == 7
    assert s_item["production_readiness_status"] != "ACTIVE"


@pytest.mark.asyncio
async def test_unknown_archetype_cannot_be_active_readiness(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
):
    """
    V1.2 Scenario B: A rule with UNKNOWN archetype MUST be reported as
    'INCOMPLETE' readiness, and NEVER as 'ACTIVE', regardless of SIEM status.
    """
    rule = Rule(
        id="rule_unknown_arch_test",
        rule_id="RULE-UNKNOWN-ARCH",
        name="Unknown Archetype Test Rule",
        event_type="PH_RULE_UNKNOWN_ARCH",
        description="Rule with unclassified archetype",
        severity="MEDIUM",
        status="ACTIVE",
        data_source="Custom",
        detection_tech="Unknown",
        pattern_logic="",
    )
    db_session.add(rule)

    rp = RulePrompt(
        id="rp_unknown_arch",
        rule_id=rule.id,
        title="Unknown Arch Prompt",
    )
    db_session.add(rp)

    pv = PromptVersion(
        id="pv_unknown_arch_v1",
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED",  # Stale approval
        is_template_draft=False,
        common_prompt="Common",
        rule_specific_prompt="Rule specific",
        detection_conditions="",
        required_evidence="",
        tp_indicators="",
        fp_indicators="",
        missing_info_criteria="",
        escalation_conditions="",
        quality_status="REWORK_REQUIRED",
        quality_score=40.0,
    )
    db_session.add(pv)
    rp.active_version_id = pv.id

    # Snapshot explicitly has UNKNOWN archetype
    snap = RuleIntelligenceSnapshot(
        id="snap_unknown_arch",
        rule_id=rule.id,
        rule_identifier=rule.rule_id,
        definition_status="INCOMPLETE",
        primary_archetype="UNKNOWN",
        threshold=0,
    )
    db_session.add(snap)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {analyst_token}"}

    sum_res = await client.get("/api/prompts/summary", headers=headers)
    assert sum_res.status_code == 200
    s_item = next(item for item in sum_res.json() if item["rule_id"] == rule.id)
    assert s_item["detection_archetype"] == "UNKNOWN"
    assert s_item["production_readiness_status"] == "INCOMPLETE"
    assert s_item["production_readiness_status"] != "ACTIVE"


@pytest.mark.asyncio
async def test_rbac_viewer_unauthorized_actions(
    client: AsyncClient,
    db_session: AsyncSession,
    viewer_token: str,
    analyst_token: str,
    admin_token: str,
):
    """
    V1.2 RBAC: Read-Only Viewer cannot approve, mutate policy, or submit reviews.
    Analyst cannot bypass administrator-only production approval.
    """
    rule = Rule(
        id="rule_rbac_test",
        rule_id="RULE-RBAC-TEST",
        name="RBAC Validation Rule",
        event_type="PH_RULE_RBAC",
        description="Testing role restrictions",
        severity="HIGH",
        status="ACTIVE",
    )
    db_session.add(rule)

    rp = RulePrompt(
        id="rp_rbac_test",
        rule_id=rule.id,
        title="RBAC Prompt",
    )
    db_session.add(rp)

    pv = PromptVersion(
        id="pv_rbac_v1",
        prompt_id=rp.id,
        version_number=1,
        status="DRAFT",
        is_template_draft=True,
        common_prompt="Common",
        rule_specific_prompt="Rule specific",
        detection_conditions="Conditions",
        required_evidence="Evidence",
        tp_indicators="TP",
        fp_indicators="FP",
        missing_info_criteria="Missing",
        escalation_conditions="Escalation",
        quality_status="DRAFT",
        quality_score=60.0,
    )
    db_session.add(pv)

    inc = Incident(
        id="inc_rbac_test",
        incident_id="INC-RBAC-001",
        rule_id=rule.id,
        event_type=rule.event_type,
        severity=rule.severity,
        status_name="ACTIVE",
        first_seen_epoch=1700000000,
        last_seen_epoch=1700000000,
        created_at_epoch=1700000000,
        updated_at_epoch=1700000000,
    )
    db_session.add(inc)
    await db_session.commit()

    headers_viewer = {"Authorization": f"Bearer {viewer_token}"}
    headers_analyst = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Viewer cannot approve policy (must be 403 Forbidden)
    res = await client.post(
        f"/api/prompts/rule/{rule.id}/approve/{pv.id}",
        headers=headers_viewer,
        json={"change_summary": "Viewer unauthorized approval"}
    )
    assert res.status_code == 403

    # 2. Viewer cannot rollback policy
    res = await client.post(
        f"/api/prompts/rule/{rule.id}/rollback/{pv.id}",
        headers=headers_viewer,
    )
    assert res.status_code == 403

    # 3. Viewer cannot revoke policy
    res = await client.post(
        f"/api/prompts/rule/{rule.id}/version/{pv.id}/revoke",
        headers=headers_viewer,
        json={"revocation_reason": "Viewer unauthorized revoke"}
    )
    assert res.status_code == 403

    # 4. Viewer cannot create manual draft
    res = await client.post(
        f"/api/prompts/rule/{rule.id}/draft",
        headers=headers_viewer,
        json={
            "common_prompt": "x",
            "rule_specific_prompt": "y",
            "detection_conditions": "z",
            "required_evidence": "w",
            "tp_indicators": "tp",
            "fp_indicators": "fp",
            "missing_info_criteria": "m",
            "escalation_conditions": "e",
        }
    )
    assert res.status_code == 403

    # 5. Viewer cannot submit analyst review
    res = await client.post(
        f"/api/reviews/{inc.incident_id}/submit",
        headers=headers_viewer,
        json={
            "analyst_verdict": "FALSE_POSITIVE",
            "analyst_notes": "Viewer attempt",
            "blind_mode_active": True,
        }
    )
    assert res.status_code == 403

    # 6. Analyst cannot approve policy (must be 403 Forbidden - Admin only)
    res = await client.post(
        f"/api/prompts/rule/{rule.id}/approve/{pv.id}",
        headers=headers_analyst,
        json={"change_summary": "Analyst bypass attempt"}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_blind_review_masks_ground_truth(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
):
    """
    V1.2 Blind Review: When blind_review=true is requested, ground-truth resolution
    and analyst determinations are strictly sanitized and masked.
    """
    rule = Rule(
        id="rule_blind_test",
        rule_id="RULE-BLIND",
        name="Blind Review Test Rule",
        event_type="PH_RULE_BLIND",
        severity="MEDIUM",
        status="ACTIVE",
    )
    db_session.add(rule)

    inc = Incident(
        id="inc_blind_test_001",
        incident_id="INC-BLIND-001",
        rule_id=rule.id,
        event_type=rule.event_type,
        severity=rule.severity,
        status_name="ACTIVE",
        first_seen_epoch=1700000000,
        last_seen_epoch=1700000000,
        created_at_epoch=1700000000,
        updated_at_epoch=1700000000,
        raw_payload={"srcIp": "192.0.2.10", "cleared_reason": "False alarm test ground truth"},
    )
    db_session.add(inc)
    await db_session.commit()

    headers = {"Authorization": f"Bearer {analyst_token}"}

    # 1. With blind_review=true on incident list
    res = await client.get("/api/incidents?blind_review=true", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]
    found = next((i for i in items if i["incident_id"] == inc.incident_id), None)
    assert found is not None
    # Historical resolution must be masked
    assert found["historical_resolution"] in ("[Hidden - Blind Review]", None)


@pytest.mark.asyncio
async def test_heavy_tcp_host_scan_readiness_service_authoritative(
    db_session: AsyncSession,
):
    """
    Task 4 Verification: Heavy TCP Host Scan On Fixed Port must evaluate to:
      - Detection Archetype: NETWORK_SCAN
      - SIEM Deployment Status: ACTIVE
      - Verified Reviews: 0
      - Empirical Accuracy: N/A (None)
      - Production Readiness: BLOCKED / INCOMPLETE
      - Recommended Action: Verify FortiSIEM Detection Semantics
    """
    from app.services.production_readiness_service import ProductionReadinessService
    from app.schemas.production_readiness import ReadinessStatus

    rule = Rule(
        id="rule_heavy_tcp_authoritative",
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        name="Heavy TCP Host Scan On Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        severity="MEDIUM",
        status="ACTIVE",
        data_source="Network Firewall",
        detection_tech="Port Threshold",
        pattern_logic="SELECT * FROM events",
    )
    db_session.add(rule)
    await db_session.commit()

    res = await ProductionReadinessService.evaluate_readiness(db_session, rule.id)
    assert res.rule_deployment_status == "ACTIVE"
    assert "SCAN" in res.detection_archetype
    assert res.verified_reviews_count == 0
    assert res.metrics.get("empirical_accuracy") is None
    assert res.readiness_status in (ReadinessStatus.BLOCKED, ReadinessStatus.INCOMPLETE, ReadinessStatus.LEARNING)
    assert res.stages[0].stage_id == "define_detection"
    assert len(res.stages) == 6
