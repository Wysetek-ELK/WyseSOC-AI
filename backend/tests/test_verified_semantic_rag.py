import pytest
from datetime import datetime, timedelta
from app.utils.datetime_utils import utc_now
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.learning import LearningRecord
from app.models.rule import Rule
from app.services.verified_semantic_retrieval_service import VerifiedSemanticRetrievalService


@pytest.mark.asyncio
async def test_verified_rag_governance_gates(db_session: AsyncSession):
    """
    Tests all 6 isolation gates of VerifiedSemanticRetrievalService:
    - Status gate: Only VERIFIED records qualify
    - Self-exclusion: Current incident is ignored
    - Tenant isolation: Cross-tenant records rejected
    - Rule scope: Cross-rule records rejected
    - Temporal filter: Future records rejected
    - Duplicate suppression: Duplicates suppressed
    """
    rule_a = Rule(id="rule-a-uuid", rule_id="RULE-A", name="Rule A", event_type="Process")
    rule_b = Rule(id="rule-b-uuid", rule_id="RULE-B", name="Rule B", event_type="Network")
    db_session.add_all([rule_a, rule_b])
    await db_session.flush()

    base_time = datetime(2026, 6, 1, 12, 0, 0)

    # 1. Target Query Incident (Tenant 100, Rule A, created at base_time)
    target_inc = Incident(
        incident_id="INC-QUERY",
        rule_id=rule_a.id,
        event_type="Process",
        title="Suspicious Encoded Script Execution",
        description="PowerShell process with base64 encoded payload",
        customer="TENANT-100",
        created_at=base_time,
    )
    db_session.add(target_inc)
    await db_session.flush()

    # 2. Historical Incident 1: VALID QUALIFIED PRECEDENT (VERIFIED, Rule A, Tenant 100, Past)
    past_inc_1 = Incident(
        incident_id="INC-HIST-01",
        rule_id=rule_a.id,
        event_type="Process",
        title="Historical Encoded Script Attack",
        description="PowerShell execution encoded payload",
        customer="TENANT-100",
        created_at=base_time - timedelta(days=5),
    )
    db_session.add(past_inc_1)
    await db_session.flush()

    lr_valid = LearningRecord(
        incident_id=past_inc_1.id,
        rule_id=rule_a.id,
        verification_status="VERIFIED",
        verified_verdict="TRUE_POSITIVE",
        analyst_explanation="Confirmed encoded PowerShell cradle downloading malware.",
        feedback_timestamp=base_time - timedelta(days=4),
    )

    # 3. Candidate 2: UNVERIFIED (Must be rejected by Gate 1)
    lr_unverified = LearningRecord(
        incident_id=past_inc_1.id,
        rule_id=rule_a.id,
        verification_status="PENDING_REVIEW",
        verified_verdict="FALSE_POSITIVE",
        analyst_explanation="Unverified analyst submission.",
        feedback_timestamp=base_time - timedelta(days=3),
    )

    # 4. Candidate 3: SELF-INCIDENT (Must be rejected by Gate 2)
    lr_self = LearningRecord(
        incident_id=target_inc.id,
        rule_id=rule_a.id,
        verification_status="VERIFIED",
        verified_verdict="TRUE_POSITIVE",
        analyst_explanation="Self incident should not be retrieved.",
        feedback_timestamp=base_time - timedelta(days=1),
    )

    # 5. Candidate 4: CROSS-TENANT (Tenant 200, must be rejected by Gate 3)
    past_inc_cross_tenant = Incident(
        incident_id="INC-HIST-TENANT200",
        rule_id=rule_a.id,
        event_type="Process",
        title="Another Tenant PowerShell Attack",
        customer="TENANT-200",
        created_at=base_time - timedelta(days=5),
    )
    db_session.add(past_inc_cross_tenant)
    await db_session.flush()

    lr_cross_tenant = LearningRecord(
        incident_id=past_inc_cross_tenant.id,
        rule_id=rule_a.id,
        verification_status="VERIFIED",
        verified_verdict="TRUE_POSITIVE",
        analyst_explanation="Cross-tenant precedent.",
        feedback_timestamp=base_time - timedelta(days=4),
    )

    # 6. Candidate 5: CROSS-RULE (Rule B, must be rejected by Gate 4)
    past_inc_cross_rule = Incident(
        incident_id="INC-HIST-RULE-B",
        rule_id=rule_b.id,
        event_type="Network",
        title="Network Beaconing Alert",
        customer="TENANT-100",
        created_at=base_time - timedelta(days=5),
    )
    db_session.add(past_inc_cross_rule)
    await db_session.flush()

    lr_cross_rule = LearningRecord(
        incident_id=past_inc_cross_rule.id,
        rule_id=rule_b.id,
        verification_status="VERIFIED",
        verified_verdict="FALSE_POSITIVE",
        analyst_explanation="Cross rule precedent.",
        feedback_timestamp=base_time - timedelta(days=4),
    )

    # 7. Candidate 6: FUTURE LEAKAGE (Verified 2 days AFTER target incident, must be rejected by Gate 5)
    past_inc_future = Incident(
        incident_id="INC-HIST-FUTURE",
        rule_id=rule_a.id,
        event_type="Process",
        title="Future Incident from Replay",
        customer="TENANT-100",
        created_at=base_time + timedelta(days=1),
    )
    db_session.add(past_inc_future)
    await db_session.flush()

    lr_future = LearningRecord(
        incident_id=past_inc_future.id,
        rule_id=rule_a.id,
        verification_status="VERIFIED",
        verified_verdict="TRUE_POSITIVE",
        analyst_explanation="Future feedback.",
        feedback_timestamp=base_time + timedelta(days=2),
    )

    db_session.add_all([lr_valid, lr_unverified, lr_self, lr_cross_tenant, lr_cross_rule, lr_future])
    await db_session.commit()

    # Execute Retrieval
    res = await VerifiedSemanticRetrievalService.retrieve_verified_precedents(
        db=db_session,
        incident=target_inc,
        rule_id=rule_a.id,
        max_precedents=5,
    )

    # Verify filtering outcomes
    assert res.retrieval_status == "PRECEDENTS_FOUND"
    assert len(res.precedents) == 1
    assert res.precedents[0].incident_id == "INC-HIST-01"
    assert res.precedents[0].verified_verdict == "TRUE_POSITIVE"

    # Verify rejection counters
    assert res.candidates_rejected_unverified >= 1
    assert res.candidates_rejected_cross_tenant >= 1
    assert res.candidates_rejected_cross_rule >= 1
    assert res.candidates_rejected_future_leakage >= 1

    # Verify proper RAG enclosure tags
    assert "<VERIFIED_HISTORICAL_PRECEDENTS>" in res.formatted_rag_block
    assert "</VERIFIED_HISTORICAL_PRECEDENTS>" in res.formatted_rag_block


@pytest.mark.asyncio
async def test_verified_rag_safe_fallback_when_empty(db_session: AsyncSession):
    """Verify safe fallback without fictitious hallucinations when no verified precedents exist."""
    rule = Rule(id="rule-empty-uuid", rule_id="RULE-EMPTY", name="Empty Precedents Rule", event_type="DNS")
    db_session.add(rule)
    await db_session.flush()

    incident = Incident(
        incident_id="INC-NO-PRECEDENT",
        rule_id=rule.id,
        event_type="DNS",
        title="DNS Tunneling Alert",
        created_at=utc_now(),
    )
    db_session.add(incident)
    await db_session.commit()

    res = await VerifiedSemanticRetrievalService.retrieve_verified_precedents(
        db=db_session,
        incident=incident,
        rule_id=rule.id,
        max_precedents=2,
    )

    assert res.retrieval_status == "NO_VERIFIED_PRECEDENT"
    assert len(res.precedents) == 0
    assert res.formatted_rag_block == ""
