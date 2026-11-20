"""
PostgreSQL Policy Version Deletion Integrity Test Suite
Validates strict referential-integrity, immutability of approved policy baselines,
and protection against accidental or malicious deletion across all lifecycle transitions.
"""

import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.user import User
from app.models.audit import AuditLog
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.pilot import PilotEvaluationRecord
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord
from app.models.dry_run import DryRunConfig
from app.services.policy_version_governance_service import PolicyVersionGovernanceService


async def create_base_rule_and_prompt(db: AsyncSession, rule_id_str: str = "PH_RULE_INTEGRITY_TEST"):
    rule = Rule(
        id=str(uuid.uuid4()),
        rule_id=rule_id_str,
        name="Integrity Verification Test Rule",
        event_type="PH_RULE_TEST",
        severity="HIGH",
        status="ACTIVE",
    )
    db.add(rule)
    await db.flush()

    prompt = RulePrompt(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        title=rule.name,
    )
    db.add(prompt)
    await db.flush()
    return rule, prompt


@pytest.mark.asyncio
async def test_unreferenced_draft_deletion_succeeds(db_session: AsyncSession, admin_user: User):
    """Test 1: Unreferenced draft can be safely and permanently deleted."""
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_DRAFT_DEL_TEST")

    # Active approved baseline v1
    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Baseline active policy",
        approved_at=datetime.now(timezone.utc),
    )
    # Obsolete unreferenced draft v2
    v2 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=2,
        status="DRAFT",
        was_ever_approved=False,
        rule_specific_prompt="Obsolete draft to delete",
    )
    # Associated draft assessment
    qa = PolicyQualityAssessmentRecord(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        prompt_version_id=v2.id,
        version_number=2,
        archetype="GENERAL",
        quality_score=75.0,
        approval_eligible=False,
        simulation_status="COMPLETED",
        score_breakdown={},
        gate_results={},
        blocking_issues=[],
        warnings=[],
        missing_evidence_mappings=[],
        recommendations=[],
        policy_digest="sha256:abc",
        contract_digest="sha256:def",
        rule_digest="sha256:123",
        validator_version="2.0",
        evaluated_at=datetime.now(timezone.utc),
    )
    db_session.add_all([v1, v2, qa])
    prompt.active_version_id = v1.id
    await db_session.commit()

    # Preview check
    preview = await PolicyVersionGovernanceService.get_deletion_preview(db_session, rule.id, v2.id)
    assert preview.is_eligible is True
    assert preview.version_number == 2
    assert preview.records_affected == 2  # draft + quality assessment

    # Delete draft
    result = await PolicyVersionGovernanceService.delete_version(
        db=db_session,
        rule_identifier=rule.id,
        version_id=v2.id,
        current_user=admin_user,
        justification="Removing obsolete candidate draft",
    )
    assert result["success"] is True
    assert result["deleted_version_number"] == 2

    # Verify version and assessment are gone, while v1 remains
    v2_check = (await db_session.execute(select(PromptVersion).where(PromptVersion.id == v2.id))).scalar_one_or_none()
    assert v2_check is None
    qa_check = (await db_session.execute(select(PolicyQualityAssessmentRecord).where(PolicyQualityAssessmentRecord.id == qa.id))).scalar_one_or_none()
    assert qa_check is None
    v1_check = (await db_session.execute(select(PromptVersion).where(PromptVersion.id == v1.id))).scalar_one_or_none()
    assert v1_check is not None


@pytest.mark.asyncio
async def test_active_approved_version_deletion_rejected(db_session: AsyncSession, admin_user: User):
    """Test 2: Active approved version is strictly protected from deletion."""
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_ACTIVE_DEL_BLOCK")

    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Active policy",
        approved_at=datetime.now(timezone.utc),
    )
    db_session.add(v1)
    prompt.active_version_id = v1.id
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await PolicyVersionGovernanceService.delete_version(
            db=db_session,
            rule_identifier=rule.id,
            version_id=v1.id,
            current_user=admin_user,
        )
    assert exc_info.value.status_code == 400
    assert "permanently immutable" in exc_info.value.detail or "cannot be deleted" in exc_info.value.detail


@pytest.mark.asyncio
async def test_historical_approved_version_deletion_rejected(db_session: AsyncSession, admin_user: User):
    """Test 3: Inactive historical approved baseline is strictly protected from deletion."""
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_HIST_DEL_BLOCK")

    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Historical approved baseline v1",
        approved_at=datetime.now(timezone.utc),
    )
    v2 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=2,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Currently active baseline v2",
        approved_at=datetime.now(timezone.utc),
    )
    db_session.add_all([v1, v2])
    prompt.active_version_id = v2.id
    await db_session.commit()

    # Attempting to delete historical approved baseline v1 must be rejected
    with pytest.raises(HTTPException) as exc_info:
        await PolicyVersionGovernanceService.delete_version(
            db=db_session,
            rule_identifier=rule.id,
            version_id=v1.id,
            current_user=admin_user,
        )
    assert exc_info.value.status_code == 400
    assert "permanently immutable" in exc_info.value.detail


@pytest.mark.asyncio
async def test_archived_approved_version_deletion_rejected(db_session: AsyncSession, admin_user: User):
    """
    Test 4: Lifecycle transition APPROVED -> ARCHIVED -> DELETE is strictly rejected.
    Archived versions that were previously approved retain immutable status.
    """
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_ARCHIVED_APPROVED_BLOCK")

    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Approved baseline v1",
        approved_at=datetime.now(timezone.utc),
    )
    v2 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=2,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Active baseline v2",
        approved_at=datetime.now(timezone.utc),
    )
    db_session.add_all([v1, v2])
    prompt.active_version_id = v2.id
    await db_session.commit()

    # Archive v1
    archived_v1 = await PolicyVersionGovernanceService.archive_version(
        db=db_session,
        rule_identifier=rule.id,
        version_id=v1.id,
        current_user=admin_user,
        reason="Superceded by v2",
    )
    assert archived_v1.status == "ARCHIVED"
    assert archived_v1.was_ever_approved is True
    assert archived_v1.previous_status == "APPROVED"

    # Attempt delete on archived approved version -> MUST FAIL
    with pytest.raises(HTTPException) as exc_info:
        await PolicyVersionGovernanceService.delete_version(
            db=db_session,
            rule_identifier=rule.id,
            version_id=v1.id,
            current_user=admin_user,
        )
    assert exc_info.value.status_code == 400
    assert "permanently immutable" in exc_info.value.detail


@pytest.mark.asyncio
async def test_restored_approved_version_deletion_rejected(db_session: AsyncSession, admin_user: User):
    """
    Test 5: Lifecycle transition APPROVED -> ARCHIVED -> RESTORED -> DELETE is strictly rejected.
    Restored approved versions return to APPROVED, NEVER DRAFT, and cannot be deleted.
    """
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_RESTORED_APPROVED_BLOCK")

    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="ARCHIVED",
        was_ever_approved=True,
        previous_status="APPROVED",
        rule_specific_prompt="Archived approved baseline",
        approved_at=datetime.now(timezone.utc),
    )
    v2 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=2,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Active baseline v2",
        approved_at=datetime.now(timezone.utc),
    )
    db_session.add_all([v1, v2])
    prompt.active_version_id = v2.id
    await db_session.commit()

    # Restore v1
    restored_v1 = await PolicyVersionGovernanceService.restore_version(
        db=db_session,
        rule_identifier=rule.id,
        version_id=v1.id,
        current_user=admin_user,
    )
    # Must restore as APPROVED, never DRAFT!
    assert restored_v1.status == "APPROVED"
    assert restored_v1.was_ever_approved is True

    # Attempt delete on restored approved version -> MUST FAIL
    with pytest.raises(HTTPException) as exc_info:
        await PolicyVersionGovernanceService.delete_version(
            db=db_session,
            rule_identifier=rule.id,
            version_id=v1.id,
            current_user=admin_user,
        )
    assert exc_info.value.status_code == 400
    assert "permanently immutable" in exc_info.value.detail


@pytest.mark.asyncio
async def test_revoked_approved_version_deletion_rejected(db_session: AsyncSession, admin_user: User):
    """
    Test 6: Lifecycle transition APPROVED -> REVOKED -> DELETE is strictly rejected.
    Revoked versions maintain audit accountability and cannot be deleted.
    """
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_REVOKED_DEL_BLOCK")

    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="REVOKED",
        was_ever_approved=True,
        previous_status="APPROVED",
        revocation_reason="Flawed detection logic causing false negatives",
        approved_at=datetime.now(timezone.utc),
    )
    db_session.add(v1)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await PolicyVersionGovernanceService.delete_version(
            db=db_session,
            rule_identifier=rule.id,
            version_id=v1.id,
            current_user=admin_user,
        )
    assert exc_info.value.status_code == 400
    assert "permanently immutable" in exc_info.value.detail


@pytest.mark.asyncio
async def test_referenced_draft_deletion_rejected(db_session: AsyncSession, admin_user: User):
    """
    Test 7: Unapproved drafts referenced by execution records (captures, pilot, dry run, benchmarks)
    cannot be deleted due to referential integrity and audit provenance.
    """
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_REF_DRAFT_BLOCK")

    v_draft = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=2,
        status="DRAFT",
        was_ever_approved=False,
        rule_specific_prompt="Draft tested in simulation",
    )
    db_session.add(v_draft)
    await db_session.commit()

    # Reference 1: Outbound LLM prompt capture
    capture = ActualLLMPromptCapture(
        id=str(uuid.uuid4()),
        incident_id="INC-REF-01",
        rule_id=rule.id,
        policy_version_id=v_draft.id,
        llm_model_name="Qwen2.5-7B-AWQ",
        token_count=120,
        captured_at=datetime.now(timezone.utc),
    )
    db_session.add(capture)
    await db_session.commit()

    # Must be blocked by capture reference
    with pytest.raises(HTTPException) as exc_info:
        await PolicyVersionGovernanceService.delete_version(
            db=db_session,
            rule_identifier=rule.id,
            version_id=v_draft.id,
            current_user=admin_user,
        )
    assert exc_info.value.status_code == 400
    assert "outbound LLM inference captures" in exc_info.value.detail


@pytest.mark.asyncio
async def test_cross_rule_version_id_mismatch_rejected(db_session: AsyncSession, admin_user: User):
    """Test 8: Cross-rule version ID lookup mismatch returns HTTP 404."""
    rule_a, prompt_a = await create_base_rule_and_prompt(db_session, "PH_RULE_A")
    rule_b, prompt_b = await create_base_rule_and_prompt(db_session, "PH_RULE_B")

    v_b = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt_b.id,
        version_number=1,
        status="DRAFT",
        was_ever_approved=False,
    )
    db_session.add(v_b)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await PolicyVersionGovernanceService.delete_version(
            db=db_session,
            rule_identifier=rule_a.id,
            version_id=v_b.id,
            current_user=admin_user,
        )
    assert exc_info.value.status_code == 404
    assert f"Policy version '{v_b.id}' not found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_bulk_deletion_excludes_approved_and_referenced_versions(db_session: AsyncSession, admin_user: User):
    """
    Test 9: Bulk deletion correctly excludes approved, active, and referenced versions,
    only deleting genuine obsolete unreferenced drafts.
    """
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_BULK_DEL_TEST")

    # v1: Historical approved
    v1 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Historical approved baseline v1",
        approved_at=datetime.now(timezone.utc),
    )
    # v2: Active approved
    v2 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=2,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Active baseline v2",
        approved_at=datetime.now(timezone.utc),
    )
    # v3: Referenced draft (dry run simulation)
    v3 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=3,
        status="DRAFT",
        was_ever_approved=False,
        rule_specific_prompt="Referenced draft v3",
    )
    # v4: Eligible obsolete draft 1
    v4 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=4,
        status="DRAFT",
        was_ever_approved=False,
        rule_specific_prompt="Obsolete draft v4",
    )
    # v5: Eligible obsolete draft 2
    v5 = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=5,
        status="DRAFT",
        was_ever_approved=False,
        rule_specific_prompt="Obsolete draft v5",
    )
    db_session.add_all([v1, v2, v3, v4, v5])
    prompt.active_version_id = v2.id
    await db_session.flush()

    # Add dry run reference to v3
    dry_run = DryRunConfig(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        prompt_version_id=v3.id,
        name="Benchmark Simulation",
    )
    db_session.add(dry_run)
    await db_session.commit()

    resp = await PolicyVersionGovernanceService.bulk_delete_versions(
        db=db_session,
        rule_identifier=rule.id,
        version_ids=[v1.id, v2.id, v3.id, v4.id, v5.id],
        current_user=admin_user,
        justification="Clean up test drafts",
    )

    assert resp.selected_count == 5
    assert resp.deleted_count == 2
    assert resp.eligible_count == 2
    assert resp.protected_count == 3
    assert set(resp.deleted_version_numbers) == {4, 5}

    # Verify protected versions still exist in DB
    remaining_res = await db_session.execute(
        select(PromptVersion.version_number).where(PromptVersion.prompt_id == prompt.id)
    )
    remaining_vnums = set(remaining_res.scalars().all())
    assert remaining_vnums == {1, 2, 3}


@pytest.mark.asyncio
async def test_archive_restore_preserves_approval_status(db_session: AsyncSession, admin_user: User):
    """
    Test 10: Validates that archiving and restoring an approved version preserves
    its APPROVED status (never converted to DRAFT) and was_ever_approved=True invariant,
    while unapproved drafts restore as DRAFT.
    """
    rule, prompt = await create_base_rule_and_prompt(db_session, "PH_RULE_STATUS_PRESERVE_TEST")

    # Inactive historical approved baseline
    v1_approved = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=1,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Approved baseline v1",
        approved_at=datetime.now(timezone.utc),
    )
    # Active approved baseline
    v2_active = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=2,
        status="APPROVED",
        was_ever_approved=True,
        rule_specific_prompt="Active baseline v2",
        approved_at=datetime.now(timezone.utc),
    )
    # Unapproved draft
    v3_draft = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=prompt.id,
        version_number=3,
        status="DRAFT",
        was_ever_approved=False,
        rule_specific_prompt="Draft v3",
    )
    db_session.add_all([v1_approved, v2_active, v3_draft])
    prompt.active_version_id = v2_active.id
    await db_session.commit()

    # 1. Archive approved baseline v1
    archived_v1 = await PolicyVersionGovernanceService.archive_version(
        db=db_session,
        rule_identifier=rule.id,
        version_id=v1_approved.id,
        current_user=admin_user,
        reason="Archiving historical approved baseline",
    )
    assert archived_v1.status == "ARCHIVED"
    assert archived_v1.was_ever_approved is True
    assert archived_v1.previous_status == "APPROVED"

    # 2. Restore approved baseline v1
    restored_v1 = await PolicyVersionGovernanceService.restore_version(
        db=db_session,
        rule_identifier=rule.id,
        version_id=v1_approved.id,
        current_user=admin_user,
    )
    # Invariant: restored status MUST be APPROVED, NEVER DRAFT!
    assert restored_v1.status == "APPROVED"
    assert restored_v1.was_ever_approved is True

    # 3. Archive unapproved draft v3
    archived_v3 = await PolicyVersionGovernanceService.archive_version(
        db=db_session,
        rule_identifier=rule.id,
        version_id=v3_draft.id,
        current_user=admin_user,
        reason="Archiving temporary draft",
    )
    assert archived_v3.status == "ARCHIVED"
    assert archived_v3.was_ever_approved is False

    # 4. Restore unapproved draft v3
    restored_v3 = await PolicyVersionGovernanceService.restore_version(
        db=db_session,
        rule_identifier=rule.id,
        version_id=v3_draft.id,
        current_user=admin_user,
    )
    # Genuine unapproved draft restores to DRAFT
    assert restored_v3.status == "DRAFT"
    assert restored_v3.was_ever_approved is False
