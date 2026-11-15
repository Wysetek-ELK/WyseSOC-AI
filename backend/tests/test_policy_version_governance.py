import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident
from app.services.prompt_studio_service import PromptStudioService
from app.services.policy_eligibility_service import PolicyEligibilityService
from app.services.verdict_pipeline import run_shared_verdict_pipeline


@pytest.mark.asyncio
async def test_revocation_lifecycle_and_audit(db_session: AsyncSession):
    """
    Validates Task 2:
    - Administrator revokes an approved version with mandatory justification.
    - Status transitions to REVOKED.
    - Audit fields (revoked_by, revoked_at, revocation_reason, previous_status) are stored.
    - Active AI execution is suspended for the rule.
    - Empty reason is rejected.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_REVOKE_TEST",
        name="Test Revocation Rule",
        event_type="PH_RULE_TEST",
        severity="HIGH",
        description="Rule to test policy version revocation lifecycle",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    prompt = RulePrompt(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        title=rule.name,
    )
    db_session.add(prompt)
    await db_session.flush()

    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="APPROVED",
        rule_specific_prompt="Original investigation prompt",
        detection_conditions="Standard conditions",
        required_evidence="ip, port",
        tp_indicators="Confirmed attack",
        fp_indicators="Benign testing",
        missing_info_criteria="Missing logs",
        escalation_conditions="Critical severity",
        analyst_questions=["Is it verified?"],
        change_summary="Initial approved baseline",
        created_by_user_id="lead-analyst",
        approved_by_user_id="soc-admin",
        approved_at=datetime.now(timezone.utc),
    )
    db_session.add(v1)
    prompt.active_version_id = v1.id
    await db_session.commit()

    service = PromptStudioService(db_session)

    # 1. Reject empty revocation reason
    with pytest.raises(ValueError, match="substantive revocation reason"):
        await service.revoke_version(
            rule_id=rule.id,
            version_id=v1.id,
            user_id="admin-01",
            revocation_reason="",
        )

    # 2. Successfully revoke with reason
    revocation_reason = "Contains defective criteria that misclassifies internal testing as true attack"
    revoked_v1 = await service.revoke_version(
        rule_id=rule.id,
        version_id=v1.id,
        user_id="admin-01",
        revocation_reason=revocation_reason,
    )
    await db_session.refresh(revoked_v1)

    assert revoked_v1.status == "REVOKED"
    assert revoked_v1.revoked_by_user_id == "admin-01"
    assert revoked_v1.revocation_reason == revocation_reason
    assert revoked_v1.previous_status == "APPROVED"
    assert revoked_v1.revoked_at is not None

    # Check parent prompt state: active execution must be suspended
    refreshed_prompt = (await db_session.execute(select(RulePrompt).where(RulePrompt.id == prompt.id))).scalar_one()
    assert refreshed_prompt.ai_execution_suspended is True
    assert "revoked" in (refreshed_prompt.suspension_reason or "").lower()


@pytest.mark.asyncio
async def test_rollback_rejection_on_revoked_and_draft(db_session: AsyncSession):
    """
    Validates that:
    - Attempting rollback to a REVOKED version is strictly blocked.
    - Attempting rollback to an unapproved DRAFT version is strictly blocked.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_ROLLBACK_BLOCK_TEST",
        name="Test Rollback Governance",
        event_type="PH_RULE_RB_TEST",
        severity="MEDIUM",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    prompt = RulePrompt(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        title=rule.name,
    )
    db_session.add(prompt)
    await db_session.flush()

    v1_revoked = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="REVOKED",
        rule_specific_prompt="Defective instructions",
        change_summary="Revoked version",
        revocation_reason="Flawed logic",
    )
    v2_draft = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=2,
        status="DRAFT",
        rule_specific_prompt="Draft replacement",
        change_summary="Unapproved draft",
    )
    db_session.add_all([v1_revoked, v2_draft])
    await db_session.commit()

    service = PromptStudioService(db_session)

    # Rollback to REVOKED must raise ValueError
    with pytest.raises(ValueError, match="Cannot rollback to Version 1: Policy is REVOKED"):
        await service.rollback_version(rule_id=rule.id, target_version_id=v1_revoked.id)

    # Rollback to DRAFT must raise ValueError
    with pytest.raises(ValueError, match="Only approved policy versions can be restored"):
        await service.rollback_version(rule_id=rule.id, target_version_id=v2_draft.id)


@pytest.mark.asyncio
async def test_semantic_mismatch_detection(db_session: AsyncSession):
    """
    Validates that PolicyEligibilityService detects semantic mismatch when
    endpoint malware instructions are applied to a NETWORK_SCAN rule.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        name="Heavy TCP Host Scan On Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        severity="HIGH",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    # Mismatched policy: mentions process name, powershell, file hash instead of network sweeps
    mismatched_prompt = (
        "Inspect process.name, parent process, cmdline arguments, and powershell script execution. "
        "Check sha256 file hash on VirusTotal and inspect process ancestry."
    )
    has_mismatch, reason = PolicyEligibilityService.detect_semantic_mismatch(rule, mismatched_prompt)
    assert has_mismatch is True
    assert "malware" in reason.lower()
    assert "NETWORK_SCAN" in reason

    # Correct policy: mentions destination hosts, TCP ports, scanner IPs, sweep thresholds
    correct_prompt = (
        "Analyze distinct destination IP addresses (destIpAddr >= 50) on fixed destination port (destPort). "
        "Correlate scanner source IP address (srcIpAddr) across CIDR blocks and verify whether authorized vulnerability scanner."
    )
    has_mismatch2, reason2 = PolicyEligibilityService.detect_semantic_mismatch(rule, correct_prompt)
    assert has_mismatch2 is False
    assert reason2 is None


@pytest.mark.asyncio
async def test_policy_eligibility_service_evaluation(db_session: AsyncSession):
    """
    Tests authoritative PolicyEligibilityService.evaluate_eligibility across
    different lifecycle states.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_ELIGIBILITY_TEST",
        name="Heavy TCP Host Scan On Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        severity="HIGH",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    prompt = RulePrompt(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        title=rule.name,
        ai_execution_suspended=False,
    )
    db_session.add(prompt)
    await db_session.flush()

    # 1. Revoked active version
    v_revoked = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="REVOKED",
        rule_specific_prompt="Network scan prompt",
        revocation_reason="Old version",
    )
    db_session.add(v_revoked)
    prompt.active_version_id = v_revoked.id
    await db_session.commit()

    elig_revoked = await PolicyEligibilityService.evaluate_eligibility(
        db=db_session,
        rule=rule,
        candidate_version=v_revoked,
        active_approved_version=v_revoked,
        is_simulation=False,
    )
    assert elig_revoked.is_eligible is False
    assert elig_revoked.status == "POLICY_REVOKED"

    # 2. Suspended rule
    prompt.ai_execution_suspended = True
    prompt.suspension_reason = "Manual SOC Admin suspension"
    await db_session.commit()

    elig_suspended = await PolicyEligibilityService.evaluate_eligibility(
        db=db_session,
        rule=rule,
        candidate_version=None,
        active_approved_version=v_revoked,
        is_simulation=False,
    )
    assert elig_suspended.is_eligible is False
    assert elig_suspended.status == "RULE_SUSPENDED"

    # 3. Draft candidate cannot be approved for runtime dispatch
    v_draft = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=3,
        status="DRAFT",
        rule_specific_prompt="destIpAddr >= 50 port scan instructions",
    )
    db_session.add(v_draft)
    prompt.ai_execution_suspended = False
    await db_session.commit()

    elig_draft = await PolicyEligibilityService.evaluate_eligibility(
        db=db_session,
        rule=rule,
        candidate_version=v_draft,
        active_approved_version=None,
        is_simulation=False,
    )
    assert elig_draft.is_eligible is False
    assert elig_draft.status == "DRAFT_NOT_APPROVED"

    # In simulation mode, draft CAN be evaluated safely
    elig_draft_sim = await PolicyEligibilityService.evaluate_eligibility(
        db=db_session,
        rule=rule,
        candidate_version=v_draft,
        active_approved_version=None,
        is_simulation=True,
    )
    assert elig_draft_sim.is_eligible is True


@pytest.mark.asyncio
async def test_verdict_pipeline_intercepts_suspended_rule(db_session: AsyncSession):
    """
    Validates that run_shared_verdict_pipeline intercepts executions for rules
    with suspended execution or revoked policy, returning a safe abstention
    without throwing an unhandled error or affecting SIEM ingestion.
    """
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id="PH_RULE_PIPELINE_GUARD_TEST",
        name="Heavy TCP Host Scan On Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        severity="MEDIUM",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.flush()

    prompt = RulePrompt(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        title=rule.name,
        ai_execution_suspended=True,
        suspension_reason="Policy under review for semantic defects",
    )
    db_session.add(prompt)
    await db_session.flush()

    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="REVOKED",
        rule_specific_prompt="Bad prompt",
        revocation_reason="Defective prompt",
    )
    db_session.add(v1)
    prompt.active_version_id = v1.id
    await db_session.commit()

    incident = Incident(
        id=str(uuid.uuid4()),
        incident_id=f"INC-{uuid.uuid4().hex[:6]}",
        title="TCP Scan Detected",
        rule_id=rule.id,
        severity="MEDIUM",
        event_type=rule.event_type,
        source_ip="mock-src-host",
        description="TCP Scan Detected",
    )
    db_session.add(incident)
    await db_session.commit()

    # Execute verdict pipeline in production mode (is_simulation=False)
    # The pipeline should safely intercept and return REQUIRES_ATTENTION with 0 confidence
    verdict_result = await run_shared_verdict_pipeline(
        db=db_session,
        incident=incident,
        rule=rule,
        prompt_version=v1,
        active_approved_version=v1,
        is_simulation=False,
    )

    assert verdict_result is not None
    assert verdict_result.is_abstained is True
    assert verdict_result.effective_verdict == "REQUIRES_ATTENTION"
    assert "AI verdict execution is suspended" in verdict_result.verdict_data["reason"]
    assert "RULE_AI_EXECUTION_SUSPENDED" in verdict_result.verdict_data["reason"] or "POLICY_REVOKED" in verdict_result.verdict_data["reason"]
