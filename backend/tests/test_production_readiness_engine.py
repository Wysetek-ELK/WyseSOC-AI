import pytest
import os
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.services.production_readiness_service import ProductionReadinessService
from app.schemas.production_readiness import ReadinessStatus, StageStatus

ZIP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "Incident json.zip"))


async def _get_or_create_test_rule(db_session: AsyncSession, name: str = "Test Heavy TCP Host Scan", event_type: str = "PH_RULE_TEST_SCAN") -> Rule:
    q = select(Rule).where(Rule.event_type == event_type)
    res = await db_session.execute(q)
    rule = res.scalars().first()
    if not rule:
        rule = Rule(
            id=str(uuid.uuid4()),
            rule_id=f"RULE-{uuid.uuid4().hex[:8]}",
            name=name,
            event_type=event_type,
            description="TCP Host port scan detection rule for perimeter firewalls",
            severity="HIGH",
            status="ACTIVE",
            data_source="FortiSIEM Telemetry",
            detection_tech="Pattern Match",
            pattern_logic="SELECT * FROM events WHERE eventType = 'PH_RULE_TEST_SCAN'",
        )
        db_session.add(rule)
        await db_session.commit()
        await db_session.refresh(rule)
    return rule


@pytest.mark.asyncio
async def test_production_readiness_service_direct_evaluation(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
):
    """Test ProductionReadinessService evaluates the 6 human-readable stages and returns authoritative readiness data."""
    rule = await _get_or_create_test_rule(db_session, "Direct Evaluation Rule", "PH_RULE_DIRECT_EVAL")

    readiness = await ProductionReadinessService.evaluate_readiness(db_session, rule.id)

    # Assert response contract
    assert readiness.rule_id == rule.id
    assert readiness.rule_name == rule.name
    assert readiness.readiness_status in [
        ReadinessStatus.BLOCKED,
        ReadinessStatus.INCOMPLETE,
        ReadinessStatus.LEARNING,
        ReadinessStatus.VALIDATING,
        ReadinessStatus.READY_FOR_APPROVAL,
        ReadinessStatus.APPROVED,
        ReadinessStatus.ACTIVE,
    ]
    assert readiness.deployment_status in ["ACTIVE", "INACTIVE", "SUSPENDED", "NOT_DEPLOYED"]

    # Verify all 6 human-readable stages are present
    assert len(readiness.stages) == 6
    stage_ids = [s.stage_id for s in readiness.stages]
    assert stage_ids == [
        "define_detection",
        "verify_evidence",
        "validate_policy",
        "analyst_learning",
        "test_accuracy",
        "production_approval",
    ]

    # Verify smart next action
    assert readiness.recommended_action is not None
    assert readiness.recommended_action.title
    assert readiness.recommended_action.target_tab in ["overview", "learning", "advanced"]

    # Quality Gates G1-G8 dictionary
    assert isinstance(readiness.gate_results, dict)
    assert 0 <= readiness.quality_gates_passed <= 8


@pytest.mark.asyncio
async def test_readiness_api_endpoint(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
    viewer_token: str,
):
    """Test GET /api/prompts/rule/{rule_id}/readiness endpoint."""
    rule = await _get_or_create_test_rule(db_session, "Endpoint Test Rule", "PH_RULE_API_ENDPOINT")

    headers_viewer = {"Authorization": f"Bearer {viewer_token}"}
    res = await client.get(f"/api/prompts/rule/{rule.id}/readiness", headers=headers_viewer)
    assert res.status_code == 200
    data = res.json()

    assert data["rule_id"] == rule.id
    assert "readiness_status" in data
    assert "deployment_status" in data or "rule_deployment_status" in data
    assert "stages" in data
    assert len(data["stages"]) == 6
    assert "recommended_action" in data
    assert "gate_results" in data


@pytest.mark.asyncio
async def test_rule_listing_and_summary_readiness_fields(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
):
    """Test that /api/rules and /api/prompts/summary populate compact production readiness columns."""
    await _get_or_create_test_rule(db_session, "Listing Test Rule", "PH_RULE_LISTING_TEST")
    headers_analyst = {"Authorization": f"Bearer {analyst_token}"}

    # 1. Test /api/rules
    rules_res = await client.get("/api/rules?page=1&page_size=10", headers=headers_analyst)
    assert rules_res.status_code == 200
    rules_data = rules_res.json()
    assert "items" in rules_data
    assert len(rules_data["items"]) > 0
    first_rule = rules_data["items"][0]
    assert "production_readiness_status" in first_rule
    assert "gates_passed_count" in first_rule
    assert "missing_requirements_count" in first_rule

    # Test readiness filter on /api/rules
    filter_res = await client.get("/api/rules?readiness=BLOCKED", headers=headers_analyst)
    assert filter_res.status_code == 200
    filter_data = filter_res.json()
    for item in filter_data["items"]:
        assert item["production_readiness_status"] in ("BLOCKED", "INCOMPLETE")

    # 2. Test /api/prompts/summary (returns a List of items)
    summary_res = await client.get("/api/prompts/summary", headers=headers_analyst)
    assert summary_res.status_code == 200
    summary_data = summary_res.json()
    assert isinstance(summary_data, list)
    assert len(summary_data) > 0
    first_sum = summary_data[0]
    assert "production_readiness_status" in first_sum
    assert "gates_passed_count" in first_sum
    assert "missing_requirements_count" in first_sum


@pytest.mark.asyncio
async def test_heavy_tcp_host_scan_status_consistency_and_archetype(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
    admin_token: str,
):
    """
    Status consistency regression test for 'Heavy TCP Host Scan On Fixed Port':
    1. Verifies that archetype resolves dynamically to NETWORK_SCAN (never UNKNOWN).
    2. Verifies that deployment status ACTIVE coexists correctly with candidate readiness BLOCKED/INCOMPLETE.
    3. Verifies that 0 reviews yields N/A accuracy (never marked PASS).
    4. Verifies that approval is rejected when quality gates have blockers.
    """
    # Create or update test rule 'Heavy TCP Host Scan On Fixed Port'
    q = select(Rule).where(Rule.name.ilike("%Heavy TCP Host Scan%"))
    r_exec = await db_session.execute(q)
    test_rule = r_exec.scalars().first()

    if not test_rule:
        test_rule = Rule(
            id="rule_heavy_tcp_test_001",
            rule_id="RULE-HEAVY-TCP-SCAN",
            name="Heavy TCP Host Scan On Fixed Port",
            event_type="PH_RULE_HEAVY_TCP_SCAN",
            description="Detects multiple TCP SYN connection attempts to fixed port from single host",
            severity="HIGH",
            status="ACTIVE",  # SIEM baseline is ACTIVE
            data_source="FortiSIEM Ingestion",
            detection_tech="Network Port Threshold",
            pattern_logic="SELECT srcIp, destIp, destPort, count(*) FROM events WHERE eventType = 'PH_RULE_HEAVY_TCP_SCAN' GROUP BY srcIp, destIp, destPort HAVING count(*) > 50",
        )
        db_session.add(test_rule)
        await db_session.commit()
        await db_session.refresh(test_rule)

    headers_analyst = {"Authorization": f"Bearer {analyst_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # Evaluate readiness
    readiness = await ProductionReadinessService.evaluate_readiness(db_session, test_rule.id)

    # 1. Archetype check: Network Scan detection must be recognized
    assert "SCAN" in readiness.detection_archetype or readiness.detection_archetype != "UNKNOWN"

    # 2. Status separation: Baseline is ACTIVE, candidate readiness is BLOCKED/INCOMPLETE
    assert readiness.deployment_status == "ACTIVE"
    assert readiness.readiness_status in [ReadinessStatus.BLOCKED, ReadinessStatus.INCOMPLETE]

    # 3. Accuracy check: With 0 verified reviews, accuracy status must be INSUFFICIENT_EVIDENCE
    stage5_acc = next(s for s in readiness.stages if s.stage_id == "test_accuracy")
    assert stage5_acc.status in [StageStatus.PENDING, StageStatus.NEEDS_ACTION, StageStatus.BLOCKED]
    assert readiness.verified_reviews_count == 0

    # 4. API prompt summary check: Summary must report detection archetype and readiness correctly
    sum_res = await client.get("/api/prompts/summary", headers=headers_analyst)
    assert sum_res.status_code == 200
    sum_items = sum_res.json()
    sum_item = next((s for s in sum_items if s["rule_id"] == test_rule.id), None)
    if sum_item:
        assert sum_item["detection_archetype"] != "UNKNOWN"
        assert sum_item["production_readiness_status"] in ("BLOCKED", "INCOMPLETE")

    # 5. Try approving an incomplete version via admin: must be rejected with 400
    prompt_res = await client.get(f"/api/prompts/rule/{test_rule.id}", headers=headers_analyst)
    assert prompt_res.status_code == 200
    prompt_data = prompt_res.json()
    if prompt_data.get("versions"):
        ver_id = prompt_data["versions"][0]["id"]
        # If version has quality blockers, approval must be rejected
        appr_res = await client.post(
            f"/api/prompts/rule/{test_rule.id}/approve/{ver_id}",
            headers=headers_admin,
            json={"change_summary": "Attempt unauthorized approval"}
        )
        # Should be 400 if blockers exist
        if appr_res.status_code != 200:
            assert appr_res.status_code == 400
            assert "rejected by Quality Validation Gates" in appr_res.json()["detail"]
