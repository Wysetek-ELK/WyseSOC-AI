"""
Comprehensive End-to-End Integration Test Suite for Verdictum AI AIS 2.0
Target Rule: Heavy TCP Host Scan On Fixed Port
  - Event Type: PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT
  - Canonical UUID: 40498741-ee6b-4a71-9101-0d6d3f77154c

Tests software behavior using isolated in-memory SQLite + synthetic fixtures and mocked
FortiSIEM write-back. Synthetic fixtures NEVER contribute to real empirical accuracy.
"""

import uuid
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from sqlalchemy import select
from httpx import AsyncClient, ASGITransport

from app.database import Base, get_db
from app.main import app
from app.api.deps import get_current_active_user
from app.models.user import User
from app.models.rule import Rule
from app.models.incident import Incident, IncidentEvent
from app.models.prompt import RulePrompt, PromptVersion
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.rule_learning import RuleLearningProfile
from app.models.production_governance import ProductionAutomationPolicy
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.policy_generation_service import PolicyGenerationService
from app.services.rule_learning_service import RuleLearningService
from app.services.analyst_review_service import AnalystReviewService
from app.services.promotion_service import PromotionService
from app.services.automation_governor import AutomationGovernor


TARGET_RULE_UUID = "40498741-ee6b-4a71-9101-0d6d3f77154c"
TARGET_EVENT_TYPE = "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT"
TARGET_RULE_NAME = "Heavy TCP Host Scan On Fixed Port"

SIBLING_RULE_UUID = "9839fa49-40ac-4676-abcc-4c5581ae9e09"
SIBLING_EVENT_TYPE = "PH_RULE_HEAVY_TCP_HOST_SCAN"

ANALYST_A = User(id="u-ana-a", username="analyst_a", email="a@soc.local", role="SOC Analyst", customer="GDC_NOC", is_active=True)
ANALYST_B = User(id="u-ana-b", username="analyst_b", email="b@soc.local", role="SOC Analyst", customer="GDC_NOC", is_active=True)
ADMIN_USER = User(id="u-admin", username="soc_admin", email="admin@soc.local", role="Administrator", customer="GDC_NOC", is_active=True)
TENANT_OTHER = User(id="u-other", username="tenant_other", email="other@soc.local", role="SOC Analyst", customer="OTHER_CORP", is_active=True)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _seed_target_rule(db: AsyncSession) -> Rule:
    rule = Rule(
        id=TARGET_RULE_UUID,
        rule_id=TARGET_EVENT_TYPE,
        name=TARGET_RULE_NAME,
        event_type=TARGET_EVENT_TYPE,
        description="Detects a single source IP scanning many distinct destination hosts on a single fixed TCP port.",
        severity="HIGH",
        status="ACTIVE",
        data_source="FortiSIEM",
        detection_tech="Network Reconnaissance",
        pattern_logic='{"groupBy":"srcIpAddr,destIpPort","distinctCount":"destIpAddr >= 100","window":"10m"}',
    )
    sibling = Rule(
        id=SIBLING_RULE_UUID,
        rule_id=SIBLING_EVENT_TYPE,
        name="Heavy TCP Host Scan",
        event_type=SIBLING_EVENT_TYPE,
        description="Multi-port TCP host scan sibling rule.",
        severity="HIGH",
        status="ACTIVE",
    )
    db.add(rule)
    db.add(sibling)
    await db.commit()
    return rule


async def _seed_approved_prompt_with_g1_g8(db: AsyncSession, rule: Rule) -> PromptVersion:
    rp = RulePrompt(
        id=str(uuid.uuid4()),
        rule_id=rule.id,
        title=f"Investigation Prompt - {rule.name}",
        ai_execution_suspended=False,
    )
    db.add(rp)
    await db.flush()

    draft_fields = PolicyGenerationService.generate_nine_section_draft(rule=rule)
    pv = PromptVersion(
        id=str(uuid.uuid4()),
        prompt_id=rp.id,
        version_number=1,
        status="APPROVED",
        quality_status="APPROVED",
        quality_score=96.0,
        common_prompt=draft_fields["common_prompt"],
        rule_specific_prompt=draft_fields["rule_specific_prompt"],
        detection_conditions=draft_fields["detection_conditions"],
        required_evidence=draft_fields["required_evidence"],
        tp_indicators=draft_fields["tp_indicators"],
        fp_indicators=draft_fields["fp_indicators"],
        missing_info_criteria=draft_fields["missing_info_criteria"],
        escalation_conditions=draft_fields["escalation_conditions"],
        analyst_questions=draft_fields["analyst_questions"],
        change_summary="Approved test policy for E2E verification",
    )
    db.add(pv)
    await db.flush()
    rp.active_version_id = pv.id
    db.add(rp)

    gate_results = {
        f"G{i}_GATE": {"gate_id": f"G{i}", "status": "PASSED", "score": 10.0, "max_score": 10.0}
        for i in range(1, 9)
    }
    qa = PolicyQualityAssessmentRecord(
        id=f"PQA-TEST-{uuid.uuid4().hex[:8]}",
        rule_id=rule.id,
        prompt_version_id=pv.id,
        version_number=1,
        archetype="NETWORK_SCAN",
        quality_score=96.0,
        gate_results=gate_results,
        blocking_issues=[],
        warnings=[],
        approval_eligible=True,
        simulation_status="EVALUATED_PASSED",
    )
    db.add(qa)
    await db.commit()
    return pv


@pytest.mark.asyncio
async def test_01_evidence_normalization_header_and_raw_events(db_session: AsyncSession):
    """Phase 2: Verify destIpPort extraction on header-only AND scan aggregation on rich FortiGate raw events."""
    await _seed_target_rule(db_session)

    # A. Header-only incident (matching real Server 1 incident 176122 shape)
    inc_header = Incident(
        id=str(uuid.uuid4()),
        incident_id="176122",
        rule_id=TARGET_RULE_UUID,
        event_type=TARGET_EVENT_TYPE,
        title=TARGET_RULE_NAME,
        severity="MEDIUM",
        customer="GDC_NOC",
        source_ip="",
        raw_payload={
            "incidentSrc": "srcIpAddr:172.25.24.153, srcGeoCountry:, ",
            "incidentTarget": "destIpPort:443, ",
            "incidentDetail": '{"incidentCount":102}',
            "clearedReason": "SECRET_GT_LEAK_MUST_BE_STRIPPED",
        },
    )
    res_hdr = EvidenceNormalizationService.normalize_incident_evidence(inc_header, events=[])
    fields_hdr = {r.source_field: r.observed_value for r in res_hdr.records}
    assert fields_hdr["network.source_ip"] == "172.25.24.153"
    assert fields_hdr["network.destination_port"] == "443"
    assert fields_hdr["scan.connection_count"] == "102"
    assert fields_hdr["scan.raw_events_count"] == "0"
    assert all("SECRET_GT_LEAK" not in r.observed_value for r in res_hdr.records)

    # B. Rich raw-event incident (matching real Server 1 FortiGate-120G forward logs)
    evts = [
        IncidentEvent(
            id=str(uuid.uuid4()),
            incident_id=inc_header.id,
            event_id=f"evt-{i}",
            event_receive_time=1794476056000 + (i * 1000),
            event_type="FortiGate-traffic-end-forward-client-rst",
            raw_log=(
                f'<189>devname="FortiGate-120G" srcip=172.25.24.154 dstip=8.8.4.{i + 1} '
                f'dstport=443 proto=6 action="client-rst" policyname="Cybersecurity" '
                f'service="Browsing" sentbyte=2210 rcvdbyte=4461'
            ),
            attributes={"Source IP": "172.25.24.154", "Destination TCP/UDP Port": 443, "Firewall Action": "client-rst"},
        )
        for i in range(5)
    ]
    res_rich = EvidenceNormalizationService.normalize_incident_evidence(inc_header, events=evts)
    fields_rich = {r.source_field: r.observed_value for r in res_rich.records}
    assert fields_rich["scan.raw_events_count"] == "5"
    assert fields_rich["scan.unique_destination_hosts"] == "5"
    assert "external=5" in fields_rich["scan.destination_scope"]
    assert "client-rst=5" in fields_rich["scan.firewall_action_summary"]
    assert "bidirectional_sessions=5" in fields_rich["scan.tcp_behavior_summary"]
    assert "policy=Cybersecurity" in fields_rich["scan.policy_and_service"]
    assert float(fields_rich["scan.window_seconds"]) >= 4.0


@pytest.mark.asyncio
async def test_02_rule_specific_policy_generation_no_unsafe_assumptions(db_session: AsyncSession):
    """Phase 2: Verify target rule generates dedicated NETWORK_SCAN policy without RFC-1918 FP assumptions."""
    rule = await _seed_target_rule(db_session)
    draft = PolicyGenerationService.generate_nine_section_draft(rule=rule)
    assert draft["primary_archetype"] == "NETWORK_SCAN"
    assert draft["status"] == "DRAFT"
    assert "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT" in draft["rule_specific_prompt"]
    assert "NEVER classify as FALSE_POSITIVE merely because" in draft["rule_specific_prompt"]
    assert "authorized vulnerability scanner" in draft["fp_indicators"].lower()
    assert "scan.raw_events_count == 0" in draft["missing_info_criteria"]


@pytest.mark.asyncio
async def test_03_double_blind_review_dispute_adjudication_and_exact_once(db_session: AsyncSession):
    """Phase 4: Verify blind queue drains, UUID alias resolution, inter-analyst dispute, and L2 adjudication."""
    rule = await _seed_target_rule(db_session)
    inc = Incident(
        id=str(uuid.uuid4()),
        incident_id="900001",
        rule_id=rule.id,
        event_type=TARGET_EVENT_TYPE,
        title=TARGET_RULE_NAME,
        severity="HIGH",
        customer="GDC_NOC",
        ai_verdict={"verdict": "FALSE_POSITIVE", "confidence": 82.0, "reason": "Test AI FP"},
    )
    db_session.add(inc)
    await db_session.commit()

    # Pending queue finds incident by UUID and hides AI verdict
    total, items = await AnalystReviewService.get_pending_reviews(
        db_session, customer="GDC_NOC", rule_id=TARGET_RULE_UUID, reviewer_id=ANALYST_A.username
    )
    assert total == 1
    assert items[0]["incident_id"] == "900001"
    assert "ai_verdict" not in items[0]

    # Analyst A submits FP -> AGREEMENT_FP
    r1 = await AnalystReviewService.submit_analyst_review(
        db=db_session,
        incident_id="900001",
        reviewer_id=ANALYST_A.username,
        analyst_verdict="FALSE_POSITIVE",
        analyst_notes="Verified CDN browsing",
        evidence_references=["EV-900001-1"],
        customer="GDC_NOC",
    )
    await db_session.commit()
    assert r1["comparison_outcome"] == "AGREEMENT_FP"

    # Queue for Analyst A now drains to 0
    total_after, _ = await AnalystReviewService.get_pending_reviews(
        db_session, customer="GDC_NOC", rule_id=TARGET_RULE_UUID, reviewer_id=ANALYST_A.username
    )
    assert total_after == 0

    # Analyst B submits conflicting TP -> flagged DISPUTED, profile NOT double-counted!
    r2 = await AnalystReviewService.submit_analyst_review(
        db=db_session,
        incident_id="900001",
        reviewer_id=ANALYST_B.username,
        analyst_verdict="TRUE_POSITIVE",
        analyst_notes="Unauthorized internal port sweep",
        customer="GDC_NOC",
    )
    await db_session.commit()
    assert r2["is_disputed"] is True
    assert r2["ground_truth_status"] == "DISPUTED"

    prof = await RuleLearningService.get_profile(db_session, TARGET_RULE_UUID, "GDC_NOC")
    assert prof.total_analyst_reviews == 1  # Exact-once per incident!

    # Cross-tenant review attempt is rejected
    with pytest.raises(ValueError, match="Access denied"):
        await AnalystReviewService.submit_analyst_review(
            db=db_session,
            incident_id="900001",
            reviewer_id=TENANT_OTHER.username,
            analyst_verdict="FALSE_POSITIVE",
            customer="OTHER_CORP",
        )

    # L2 Adjudication resolves dispute to TRUE_POSITIVE -> updates profile to CRITICAL_MISSED_TP
    adj = await AnalystReviewService.adjudicate_review(
        db=db_session,
        review_id=r1["review_id"],
        adjudicator_id=ADMIN_USER.username,
        final_verdict="TRUE_POSITIVE",
        rationale="L2 confirmed unauthorized scan",
    )
    await db_session.commit()
    assert adj["final_verdict"] == "TRUE_POSITIVE"
    assert adj["comparison_outcome"] == "CRITICAL_MISSED_TP"

    prof_after = await RuleLearningService.get_profile(db_session, TARGET_RULE_UUID, "GDC_NOC")
    assert prof_after.verified_tp_count == 1
    assert prof_after.verified_fp_count == 0
    assert prof_after.error_distribution.get("critical_missed_tp") == 1


@pytest.mark.asyncio
async def test_04_empirical_95_99_zero_missed_tp_and_separation_of_duties(db_session: AsyncSession):
    """Phases 5 & 6: Enforce 95% accuracy, 99% FP precision, 100 samples, 0 missed TP, G1-G8, and SoD."""
    rule = await _seed_target_rule(db_session)
    await _seed_approved_prompt_with_g1_g8(db_session, rule)

    profile = await RuleLearningService.get_or_create_profile(db_session, TARGET_RULE_UUID, "GDC_NOC")
    assert profile.primary_archetype == "NETWORK_SCAN"

    # Case 1: Insufficient samples (41 < 100) -> BLOCKED
    profile.total_analyst_reviews = 41
    profile.verified_tp_count = 15
    profile.verified_fp_count = 26
    profile.ai_correct_count = 41
    profile.ai_incorrect_count = 0
    profile.error_distribution = {"agreement_tp": 15, "agreement_fp": 26, "critical_missed_tp": 0, "ai_false_alarm": 0}
    RuleLearningService._recalculate_profile_metrics(profile)
    elig_small, reasons_small, _ = await RuleLearningService.evaluate_full_production_readiness(db_session, profile)
    assert elig_small is False
    assert any("100" in r for r in reasons_small)

    # Case 2: 150 samples with 1 missed TP -> BLOCKED even though accuracy > 99%!
    profile.total_analyst_reviews = 150
    profile.verified_tp_count = 50
    profile.verified_fp_count = 100
    profile.ai_correct_count = 149
    profile.ai_incorrect_count = 1
    profile.error_distribution = {"agreement_tp": 49, "agreement_fp": 100, "critical_missed_tp": 1, "ai_false_alarm": 0}
    RuleLearningService._recalculate_profile_metrics(profile)
    elig_miss, reasons_miss, _ = await RuleLearningService.evaluate_full_production_readiness(db_session, profile)
    assert elig_miss is False
    assert any("Critical Missed True Positives" in r for r in reasons_miss)

    # Case 3: 150 samples, 100% FP precision (100/100 -> Wilson LB >= 96.3%), >= 95% acc, 0 missed TP, G1-G8 PASS -> ELIGIBLE
    profile.lifecycle_stage = RuleLearningService.STAGE_SUPERVISED_PILOT
    profile.total_analyst_reviews = 150
    profile.verified_tp_count = 50
    profile.verified_fp_count = 100
    profile.ai_correct_count = 148
    profile.ai_incorrect_count = 2
    profile.error_distribution = {"agreement_tp": 50, "agreement_fp": 98, "critical_missed_tp": 0, "ai_false_alarm": 2}
    RuleLearningService._recalculate_profile_metrics(profile)
    db_session.add(profile)
    await db_session.commit()

    elig_ok, reasons_ok, meta_ok = await RuleLearningService.evaluate_full_production_readiness(db_session, profile)
    assert elig_ok is True, f"Unexpected blockers: {reasons_ok}"
    assert meta_ok["g1_g8_passed"] is True

    # Submit formal promotion request by analyst_a
    req = await PromotionService.create_promotion_request(
        db=db_session,
        profile_id=profile.id,
        target_stage=RuleLearningService.STAGE_CONTROLLED_PRODUCTION,
        requester_id=ANALYST_A.username,
        justification="Empirical gates and G1-G8 passed",
    )
    await db_session.commit()

    # Separation of duties: requester CANNOT self-approve!
    with pytest.raises(ValueError, match="Separation of duties"):
        await PromotionService.decide_promotion_request(
            db=db_session,
            request_id=req.id,
            approver_id=ANALYST_A.username,
            action="APPROVED",
            decision_notes="Self-approval attempt",
        )

    # Distinct Administrator approves -> transitions to CONTROLLED_PRODUCTION, automation STILL disabled until explicit enable!
    dec = await PromotionService.decide_promotion_request(
        db=db_session,
        request_id=req.id,
        approver_id=ADMIN_USER.username,
        action="APPROVED",
        decision_notes="Verified all evidence and approved controlled production",
    )
    await db_session.commit()
    assert dec["status"] == "APPROVED"
    assert dec["automation_auto_enabled"] is False

    # Sibling rule remains strictly in LEARNING and unaffected!
    sib_prof = await RuleLearningService.get_or_create_profile(db_session, SIBLING_RULE_UUID, "GDC_NOC")
    assert sib_prof.lifecycle_stage == RuleLearningService.STAGE_LEARNING


@pytest.mark.asyncio
async def test_05_controlled_fortisiem_automation_all_branches_and_emergency_suspension(db_session: AsyncSession):
    """Phase 7: Verify TP escalation, INSUFFICIENT routing, FP dry-run & mocked write-back, idempotency, and missed-TP kill."""
    rule = await _seed_target_rule(db_session)
    pv = await _seed_approved_prompt_with_g1_g8(db_session, rule)

    profile = await RuleLearningService.get_or_create_profile(db_session, TARGET_RULE_UUID, "GDC_NOC")
    profile.lifecycle_stage = RuleLearningService.STAGE_CONTROLLED_PRODUCTION
    profile.total_analyst_reviews = 150
    profile.verified_tp_count = 50
    profile.verified_fp_count = 100
    profile.ai_correct_count = 150
    profile.ai_incorrect_count = 0
    profile.error_distribution = {"agreement_tp": 50, "agreement_fp": 100, "critical_missed_tp": 0, "ai_false_alarm": 0}
    RuleLearningService._recalculate_profile_metrics(profile)
    db_session.add(profile)
    await db_session.commit()

    # Seed 3 incidents: TP, INSUFFICIENT_EVIDENCE, FALSE_POSITIVE
    inc_tp = Incident(
        id=str(uuid.uuid4()), incident_id="700001", rule_id=rule.id, event_type=TARGET_EVENT_TYPE,
        title=TARGET_RULE_NAME, customer="GDC_NOC", source_ip="172.25.24.200",
        ai_verdict={"verdict": "TRUE_POSITIVE", "trust_score": 9, "confidence": 94.0, "reason": "Unauthorized SMB/445 sweep", "prompt_version_id": pv.id, "prompt_version_number": 1, "model_identifier": "Qwen/Qwen2.5-7B-Instruct-AWQ"},
    )
    inc_ins = Incident(
        id=str(uuid.uuid4()), incident_id="700002", rule_id=rule.id, event_type=TARGET_EVENT_TYPE,
        title=TARGET_RULE_NAME, customer="GDC_NOC",
        ai_verdict={"verdict": "REQUIRES_ATTENTION", "trust_score": 3, "confidence": 40.0, "reason": "0 raw logs", "missing_evidence": ["raw firewall logs"]},
    )
    inc_fp = Incident(
        id=str(uuid.uuid4()), incident_id="700003", rule_id=rule.id, event_type=TARGET_EVENT_TYPE,
        title=TARGET_RULE_NAME, customer="GDC_NOC",
        ai_verdict={"verdict": "FALSE_POSITIVE", "trust_score": 9, "confidence": 96.0, "reason": "Authorized Nessus scan CHG-101", "supporting_evidence": ["EV-1"], "prompt_version_id": pv.id, "prompt_version_number": 1, "model_identifier": "Qwen/Qwen2.5-7B-Instruct-AWQ"},
    )
    db_session.add_all([inc_tp, inc_ins, inc_fp])
    await db_session.commit()

    # 1. AI TRUE_POSITIVE -> NEVER auto-closes
    tp_res = await AutomationGovernor.execute_governed_incident_decision(db_session, "700001", "GDC_NOC", dry_run=True)
    assert tp_res["incident_closed"] is False
    assert tp_res["action_taken"] == "ROUTE_TO_ANALYST_TP"

    # 2. AI INSUFFICIENT_EVIDENCE -> NEVER auto-closes
    ins_res = await AutomationGovernor.execute_governed_incident_decision(db_session, "700002", "GDC_NOC", dry_run=True)
    assert ins_res["incident_closed"] is False
    assert ins_res["execution_status"] == "ROUTED_INSUFFICIENT_EVIDENCE"
    assert len(ins_res["execution_status"]) <= 32

    # 3. AI FALSE_POSITIVE while policy is still disabled -> BLOCKED_SAFETY_BARRIER
    fp_blocked = await AutomationGovernor.execute_governed_incident_decision(db_session, "700003", "GDC_NOC", dry_run=True)
    assert fp_blocked["incident_closed"] is False
    assert fp_blocked["execution_status"] == "BLOCKED_SAFETY_BARRIER"

    # 4. Explicitly enable automation policy via Admin -> dry-run now succeeds (DRY_RUN_WOULD_CLOSE, zero live writes)
    await PromotionService.update_automation_policy(
        db=db_session, rule_id=TARGET_RULE_UUID, customer="GDC_NOC",
        admin_user_id=ADMIN_USER.username, is_enabled=True, reason="Controlled staging test",
    )
    await db_session.commit()

    fp_dry = await AutomationGovernor.execute_governed_incident_decision(db_session, "700003", "GDC_NOC", dry_run=True)
    assert fp_dry["incident_closed"] is False
    assert fp_dry["execution_status"] == "DRY_RUN_WOULD_CLOSE"
    assert all(fp_dry["barriers"].values())

    # 5. Mocked FortiSIEM live write-back -> CLOSED_AND_VERIFIED, and duplicate attempt blocked by barrier 12!
    class MockFortiSIEM:
        async def close_incident_in_fortisiem(self, **kwargs):
            return {
                "ok": True,
                "dry_run": False,
                "execution_status": "CLOSED_AND_VERIFIED",
                "siem_status_code": 200,
                "siem_transaction_id": "MOCK-FSM-001",
                "remote_verified": True,
                "message": "Mocked FortiSIEM closure verified",
            }

    fp_live = await AutomationGovernor.execute_governed_incident_decision(
        db_session, "700003", "GDC_NOC", dry_run=False, siem_service=MockFortiSIEM()
    )
    await db_session.commit()
    assert fp_live["incident_closed"] is True
    assert fp_live["execution_status"] == "CLOSED_AND_VERIFIED"

    # Duplicate closure attempt blocked idempotently by barrier_12
    fp_dup = await AutomationGovernor.execute_governed_incident_decision(
        db_session, "700003", "GDC_NOC", dry_run=False, siem_service=MockFortiSIEM()
    )
    assert fp_dup["incident_closed"] is False
    assert fp_dup["barriers"]["barrier_12_idempotent_not_closed"] is False

    # 6. Verified Critical Missed TP immediately suspends profile + disables policy + suspends RulePrompt!
    inc_miss = Incident(
        id=str(uuid.uuid4()), incident_id="700004", rule_id=rule.id, event_type=TARGET_EVENT_TYPE,
        title=TARGET_RULE_NAME, customer="GDC_NOC",
        ai_verdict={"verdict": "FALSE_POSITIVE", "trust_score": 9, "confidence": 92.0, "reason": "Wrong FP"},
    )
    db_session.add(inc_miss)
    await db_session.commit()

    await AnalystReviewService.submit_analyst_review(
        db=db_session, incident_id="700004", reviewer_id=ANALYST_A.username,
        analyst_verdict="TRUE_POSITIVE", analyst_notes="Confirmed unauthorized reconnaissance!", customer="GDC_NOC",
    )
    await db_session.commit()

    prof_susp = await RuleLearningService.get_profile(db_session, TARGET_RULE_UUID, "GDC_NOC")
    pol_susp = (await db_session.execute(
        select(ProductionAutomationPolicy).where(ProductionAutomationPolicy.profile_id == prof_susp.id)
    )).scalar_one()
    rp_susp = (await db_session.execute(select(RulePrompt).where(RulePrompt.rule_id == rule.id))).scalar_one()

    assert prof_susp.lifecycle_stage == RuleLearningService.STAGE_SUSPENDED
    assert pol_susp.is_enabled is False
    assert pol_susp.emergency_disable is True
    assert rp_susp.ai_execution_suspended is True


@pytest.mark.asyncio
async def test_06_prompt_improvement_draft_never_mutates_approved_prompt(db_session: AsyncSession):
    """Phase 4: Feedback-driven candidate draft creation leaves active APPROVED prompt untouched."""
    rule = await _seed_target_rule(db_session)
    approved_v = await _seed_approved_prompt_with_g1_g8(db_session, rule)

    res = await RuleLearningService.propose_prompt_improvement_draft(
        db=db_session, rule_id=TARGET_RULE_UUID, customer="GDC_NOC", user_id=ADMIN_USER.id
    )
    await db_session.commit()
    assert res["status"] == "DRAFT_CREATED"
    assert res["draft_status"] == "DRAFT"
    assert res["active_production_prompt_modified"] is False

    rp = (await db_session.execute(select(RulePrompt).where(RulePrompt.rule_id == rule.id))).scalar_one()
    assert rp.active_version_id == approved_v.id


@pytest.mark.asyncio
async def test_07_llm_response_validation_insufficient_evidence_and_rejections():
    """Phase 3: Verify INSUFFICIENT_EVIDENCE acceptance and strict rejection of bad refs/confidence/JSON."""
    import json
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.services.model_provider.openai_compatible import OpenAICompatibleProvider

    provider = OpenAICompatibleProvider(base_url="http://127.0.0.1:8000/v1", model_name="Qwen/Qwen2.5-7B-Instruct-AWQ")
    ok, vstat, err = provider.validate_verdict_schema({
        "verdict": "INSUFFICIENT_EVIDENCE",
        "confidence": 40.0,
        "reason": "Missing raw firewall logs (0 events).",
    })
    assert ok is True and vstat == "VALID" and err is None

    def _mock_http_response(content_str: str):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "choices": [{"message": {"content": content_str}}],
            "usage": {"prompt_tokens": 120, "completion_tokens": 45, "total_tokens": 165},
        }
        return resp

    inc_payload = {"incident_id": "176122"}
    rule_spec = {"id": TARGET_RULE_UUID, "rule_id": TARGET_EVENT_TYPE, "name": TARGET_RULE_NAME}

    # 1. Valid INSUFFICIENT_EVIDENCE normalized safely to REQUIRES_ATTENTION
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_http_response(json.dumps({
        "incident_id": "176122",
        "rule_id": TARGET_EVENT_TYPE,
        "verdict": "INSUFFICIENT_EVIDENCE",
        "confidence": 35.0,
        "reason": "Header-only incident with zero raw logs.",
        "missing_evidence": ["raw firewall logs"],
        "recommended_action": "Collect FortiGate traffic logs before deciding.",
    })))):
        res = await provider.analyze_incident(inc_payload, rule_spec, "TEST PROMPT", 1)
        assert res.validation_status == "VALID"
        assert res.verdict == "REQUIRES_ATTENTION"
        assert "FortiGate" in (res.recommended_action or "")

    # 2. Mismatched incident_id -> rejected with INVALID_INCIDENT_REF + post_capture FAILED
    post_cb = AsyncMock()
    pre_cb = AsyncMock(return_value=MagicMock(id="cap-1", request_sha256="abc123"))
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_http_response(json.dumps({
        "incident_id": "999999",
        "rule_id": TARGET_EVENT_TYPE,
        "verdict": "FALSE_POSITIVE",
        "confidence": 95.0,
        "reason": "Wrong incident reference",
    })))):
        res_bad_inc = await provider.analyze_incident(
            inc_payload, rule_spec, "TEST PROMPT", 1,
            capture_callback=pre_cb, post_capture_callback=post_cb,
        )
        assert res_bad_inc.validation_status == "INVALID_INCIDENT_REF"
        assert res_bad_inc.verdict == "REQUIRES_ATTENTION"
        assert post_cb.await_count == 1
        assert post_cb.call_args.kwargs["status"] == "FAILED"

    # 3. Mismatched rule_id (e.g. sibling multi-port rule) -> rejected with INVALID_RULE_REF
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_http_response(json.dumps({
        "incident_id": "176122",
        "rule_id": SIBLING_EVENT_TYPE,
        "verdict": "FALSE_POSITIVE",
        "confidence": 90.0,
        "reason": "Confused with sibling rule",
    })))):
        res_bad_rule = await provider.analyze_incident(inc_payload, rule_spec, "TEST PROMPT", 1)
        assert res_bad_rule.validation_status == "INVALID_RULE_REF"
        assert res_bad_rule.verdict == "REQUIRES_ATTENTION"

    # 4. Out-of-range confidence (> 100) -> rejected with INVALID_CONFIDENCE
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_mock_http_response(json.dumps({
        "incident_id": "176122",
        "rule_id": TARGET_EVENT_TYPE,
        "verdict": "FALSE_POSITIVE",
        "confidence": 150.0,
        "reason": "Invalid confidence",
    })))):
        res_bad_conf = await provider.analyze_incident(inc_payload, rule_spec, "TEST PROMPT", 1)
        assert res_bad_conf.validation_status == "INVALID_CONFIDENCE"
        assert res_bad_conf.verdict == "REQUIRES_ATTENTION"


@pytest.mark.asyncio
async def test_08_contradictory_evidence_block_and_rag_partition_isolation(db_session: AsyncSession):
    """Phases 4, 5 & 7: Contradictory evidence blocks FP closure; LOCKED_TEST never leaks into RAG."""
    from app.models.learning import LearningRecord
    from app.services.verified_semantic_retrieval_service import VerifiedSemanticRetrievalService
    from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator

    rule = await _seed_target_rule(db_session)
    pv = await _seed_approved_prompt_with_g1_g8(db_session, rule)

    # Contradictory evidence must block barrier 5 even when rule is in CONTROLLED_PRODUCTION & enabled
    profile = await RuleLearningService.get_or_create_profile(db_session, TARGET_RULE_UUID, "GDC_NOC")
    profile.lifecycle_stage = RuleLearningService.STAGE_CONTROLLED_PRODUCTION
    profile.total_analyst_reviews = 150
    profile.verified_tp_count = 50
    profile.verified_fp_count = 100
    profile.ai_correct_count = 150
    profile.ai_incorrect_count = 0
    profile.error_distribution = {"agreement_tp": 50, "agreement_fp": 100, "critical_missed_tp": 0, "ai_false_alarm": 0}
    RuleLearningService._recalculate_profile_metrics(profile)
    db_session.add(profile)
    await db_session.commit()

    await PromotionService.update_automation_policy(
        db=db_session, rule_id=TARGET_RULE_UUID, customer="GDC_NOC",
        admin_user_id=ADMIN_USER.username, is_enabled=True, reason="Enable for barrier 5 test",
    )
    inc_contra = Incident(
        id=str(uuid.uuid4()), incident_id="700099", rule_id=rule.id, event_type=TARGET_EVENT_TYPE,
        title=TARGET_RULE_NAME, customer="GDC_NOC",
        ai_verdict={
            "verdict": "FALSE_POSITIVE", "trust_score": 9, "confidence": 91.0,
            "reason": "Mixed outbound browsing and internal denied sweeps",
            "contradictory_evidence": ["25 denied flows to internal port 445 conflict with browsing claim"],
            "policy_version_id": pv.id, "policy_version_number": 1,
        },
    )
    db_session.add(inc_contra)
    await db_session.commit()

    contra_res = await AutomationGovernor.execute_governed_incident_decision(db_session, "700099", "GDC_NOC", dry_run=True)
    assert contra_res["incident_closed"] is False
    assert contra_res["barriers"]["barrier_05_zero_contradictions"] is False

    # Verify LOCKED_TEST partition isolation in VerifiedSemanticRetrievalService
    locked_id = next(
        f"INC-LOCK-{i}"
        for i in range(1, 500)
        if str(getattr(HistoricalGroundTruthValidator.assign_partition(f"INC-LOCK-{i}"), "value", "")).upper() == "LOCKED_TEST"
    )
    inc_locked = Incident(
        id=str(uuid.uuid4()), incident_id=locked_id, rule_id=rule.id, event_type=TARGET_EVENT_TYPE,
        title=TARGET_RULE_NAME, customer="GDC_NOC",
    )
    db_session.add(inc_locked)
    await db_session.flush()
    lr_locked = LearningRecord(
        rule_id=rule.id, incident_id=inc_locked.id, verified_verdict="FALSE_POSITIVE",
        analyst_explanation="Heavy TCP Host Scan On Fixed Port authorized scanner",
        verification_status="VERIFIED",
    )
    db_session.add(lr_locked)
    await db_session.commit()

    rag = await VerifiedSemanticRetrievalService.retrieve_verified_precedents(
        db=db_session, incident=inc_contra, rule_id=rule.id, max_precedents=5
    )
    assert all(p.incident_id != locked_id for p in rag.precedents)
    assert rag.candidates_rejected_future_leakage >= 1
