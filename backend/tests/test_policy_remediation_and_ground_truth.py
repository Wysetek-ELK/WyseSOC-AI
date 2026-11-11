import pytest
import uuid
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.incident import Incident, HistoricalGroundTruth
from app.schemas.rule_intelligence import (
    DetectionSemantics,
    SemanticsDefinitionStatus,
    SourceProvenance,
    ArchetypeId,
)
from app.schemas.policy_quality import (
    GateStatus,
    SimulationStatus,
)
from app.schemas.verdict_intelligence import GroundTruthLabel
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.policy_simulation_service import PolicySimulationService


@pytest.mark.asyncio
async def test_gate_2_unclassified_telemetry_receives_warning_and_penalized_score():
    """
    REQ-Phase1: G2 must NOT award full marks (20.0) or PASSED to rules classified as
    'Unclassified / Inadequate Telemetry'. It must return WARNING with 10.0 points.
    """
    rule = Rule(
        id="test_unclassified_rule",
        rule_id="RULE_UNCLASSIFIED_01",
        name="Unclassified Host Telemetry",
        event_type="PH_RULE_UNCLASSIFIED_HOST_TELEMETRY",
    )
    semantics = DetectionSemantics(
        rule_identifier="RULE_UNCLASSIFIED_01",
        rule_name="Unclassified Host Telemetry",
        event_type="PH_RULE_UNCLASSIFIED_HOST_TELEMETRY",
        definition_status=SemanticsDefinitionStatus.VERIFIED,
        source_provenance=SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION,
    )

    classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
    assert archetype_def.archetype_id == ArchetypeId.UNKNOWN

    pv = PromptVersion(
        id="pv_unclass_01",
        prompt_id="rp_unclass_01",
        version_number=1,
        rule_specific_prompt="Analyze generic anomaly telemetry.",
        detection_conditions="Anomaly flagged by SIEM.",
        required_evidence="1. security.event_type\n2. event.timestamp",
        tp_indicators="Confirmed anomalous activity.",
        fp_indicators="Normal baseline operations.",
        missing_info_criteria="Missing critical fields requires analyst attention.",
        escalation_conditions="Escalate on critical assets.",
    )

    contract = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def, pv)
    assessment = PolicyQualityValidator.validate_policy_quality(
        rule=rule,
        prompt_version=pv,
        contract=contract,
        semantics=semantics,
    )

    g2_result = assessment.gate_results["G2_ARCHETYPE_RELEVANCE"]
    assert g2_result.status == GateStatus.WARNING
    assert g2_result.score == 10.0  # NOT full marks (20.0)
    assert g2_result.score < g2_result.max_score
    assert any("INADEQUATE_TELEMETRY" in w for w in assessment.warnings)
    assert assessment.score_breakdown["detection_semantics"] <= 10.0


@pytest.mark.asyncio
async def test_gate_5_blocks_hardcoded_confidence_and_blanket_benign_assumptions():
    """
    REQ-Phase1: G5 must strictly fail when policy contains hardcoded confidence ranges (80-98%)
    or blanket benign assumptions on loopback / RFC-1918 traffic.
    """
    rule = Rule(
        id="test_g5_rule",
        rule_id="RULE_G5_TEST",
        name="Port Scan Detection",
        event_type="SCAN_EVENT",
    )
    semantics = DetectionSemantics(
        rule_identifier="RULE_G5_TEST",
        rule_name="Port Scan Detection",
        event_type="SCAN_EVENT",
        definition_status=SemanticsDefinitionStatus.VERIFIED,
        source_provenance=SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION,
    )
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(ArchetypeId.UNKNOWN)

    pv_flawed = PromptVersion(
        id="pv_g5_flawed",
        prompt_id="rp_g5_flawed",
        version_number=1,
        rule_specific_prompt="Internal RFC-1918 traffic should be assumed benign.",
        fp_indicators="1. Traffic from 127.0.0.1 is benign with confidence 80-95%.\n2. Internal RFC-1918 traffic is benign.",
    )

    contract = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def, pv_flawed)
    assessment = PolicyQualityValidator.validate_policy_quality(rule, pv_flawed, contract, semantics)

    g5_result = assessment.gate_results["G5_FP_CRITERIA_VALIDITY"]
    assert g5_result.status == GateStatus.FAILED
    assert g5_result.score == 0.0
    assert assessment.approval_eligible is False
    assert any("UNSAFE_FP_ASSUMPTION" in b for b in assessment.blocking_issues)
    assert any("PRESCRIPTIVE_CONFIDENCE_RANGE" in b for b in assessment.blocking_issues)


@pytest.mark.asyncio
async def test_gate_7_flags_missing_security_event_type():
    """
    REQ-Phase1: G7 must warn when critical contract field 'security.event_type' is omitted
    from Section 4 required evidence, and pass when included.
    """
    rule = Rule(
        id="test_g7_rule",
        rule_id="RULE_G7_TEST",
        name="Host Scan",
        event_type="SCAN_EVENT",
    )
    semantics = DetectionSemantics(
        rule_identifier="RULE_G7_TEST",
        rule_name="Host Scan",
        event_type="SCAN_EVENT",
        definition_status=SemanticsDefinitionStatus.VERIFIED,
        source_provenance=SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION,
    )
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(ArchetypeId.UNKNOWN)

    # Missing security.event_type
    pv_missing = PromptVersion(
        id="pv_g7_missing",
        prompt_id="rp_g7_missing",
        version_number=1,
        required_evidence="1. Source IP address\n2. Destination port",
    )
    contract_missing = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def, pv_missing)
    assessment_missing = PolicyQualityValidator.validate_policy_quality(rule, pv_missing, contract_missing, semantics)

    g7_missing = assessment_missing.gate_results["G7_POLICY_CONSISTENCY"]
    assert g7_missing.status == GateStatus.WARNING
    assert any("security.event_type" in w for w in assessment_missing.warnings)

    # With security.event_type
    pv_present = PromptVersion(
        id="pv_g7_present",
        prompt_id="rp_g7_present",
        version_number=2,
        required_evidence="1. security.event_type (ENUM) [CRITICAL]\n2. event.timestamp\n3. network.source_ip",
    )
    contract_present = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def, pv_present)
    assessment_present = PolicyQualityValidator.validate_policy_quality(rule, pv_present, contract_present, semantics)

    g7_present = assessment_present.gate_results["G7_POLICY_CONSISTENCY"]
    assert g7_present.status == GateStatus.PASSED
    assert not any("security.event_type" in w for w in assessment_present.warnings)


@pytest.mark.asyncio
async def test_recommendations_cover_all_failed_and_warning_gates():
    """
    REQ-Phase1: Recommendations must include corrective actions for all failed and warning gates.
    """
    rule = Rule(
        id="test_recs_rule",
        rule_id="RULE_RECS_TEST",
        name="Scan Test",
        event_type="SCAN_TEST",
    )
    semantics = DetectionSemantics(
        rule_identifier="RULE_RECS_TEST",
        rule_name="Scan Test",
        event_type="SCAN_TEST",
        definition_status=SemanticsDefinitionStatus.VERIFIED,
        source_provenance=SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION,
    )
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(ArchetypeId.UNKNOWN)

    pv = PromptVersion(
        id="pv_recs_test",
        prompt_id="rp_recs_test",
        version_number=1,
        rule_specific_prompt="Internal RFC-1918 traffic is benign.",
        required_evidence="1. Source IP",  # Omits security.event_type -> G7 warning
        fp_indicators="Internal 127.0.0.1 loopback traffic is benign with confidence 85-95%.",  # G5 fail
    )
    contract = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def, pv)
    assessment = PolicyQualityValidator.validate_policy_quality(rule, pv, contract, semantics)

    # G2 has warning (INADEQUATE_TELEMETRY)
    # G5 has failure (UNSAFE_FP & CONFIDENCE_RANGE)
    # G7 has warning (missing security.event_type)
    # G8 has warning (not evaluated)
    assert len(assessment.recommendations) >= 4
    recs_text = " ".join(assessment.recommendations).lower()
    assert "telemetry" in recs_text or "archetype" in recs_text  # G2
    assert "confidence" in recs_text  # G5
    assert "rfc-1918" in recs_text or "loopback" in recs_text  # G5
    assert "event_type" in recs_text or "contract" in recs_text  # G7
    assert "historical" in recs_text or "incidents" in recs_text  # G8


@pytest.mark.asyncio
async def test_heavy_tcp_scan_before_after_remediation():
    """
    REQ-Phase1 & Phase2: End-to-end before/after validation for Heavy TCP Host Scan On Fixed Port (MEDIUM).
    Version 1 is blocked from approval; Version 2 candidate resolves all blockers with NETWORK_SCAN archetype.
    """
    rule = Rule(
        id="rule_heavy_tcp_scan",
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        name="Heavy TCP Host Scan On Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        severity="MEDIUM",
    )
    semantics = DetectionSemantics(
        rule_identifier="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        rule_name="Heavy TCP Host Scan On Fixed Port",
        event_type="PH_RULE_HEAVY_TCP_HOST_SCAN_ON_FIXED_PORT",
        event_category="Security",
        primary_behavior="network_scan",
        definition_status=SemanticsDefinitionStatus.VERIFIED,
        source_provenance=SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION,
    )

    # Classify with real registry — resolves to NETWORK_SCAN
    classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
    assert classification.primary_archetype == ArchetypeId.NETWORK_SCAN
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)

    # Version 1 (Flawed Legacy Policy)
    v1 = PromptVersion(
        id="pv_v1_flawed",
        prompt_id="rp_heavy_tcp",
        version_number=1,
        status="ARCHIVED",
        rule_specific_prompt="Traffic from RFC-1918 internal addresses or 127.0.0.1 loopback should be assumed benign.",
        required_evidence="1. Source IP address\n2. Destination port",
        fp_indicators="1. Internal RFC-1918 traffic is benign.\n2. Loopback 127.0.0.1 traffic is benign with confidence 85-95%.",
        tp_indicators="Rapid sequential connections to fixed port.",
        missing_info_criteria="Missing source IP requires abstention.",
        escalation_conditions="Escalate if domain controllers targeted.",
    )
    c1 = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def, v1)
    res_v1 = PolicyQualityValidator.validate_policy_quality(rule, v1, c1, semantics)

    assert res_v1.approval_eligible is False
    assert res_v1.gate_results["G5_FP_CRITERIA_VALIDITY"].status == GateStatus.FAILED
    assert res_v1.gate_results["G5_FP_CRITERIA_VALIDITY"].score == 0.0
    assert res_v1.gate_results["G7_POLICY_CONSISTENCY"].status == GateStatus.WARNING

    # Version 2 (Remediated Candidate Policy with NETWORK_SCAN archetype)
    v2 = PromptVersion(
        id="pv_v2_remediated",
        prompt_id="rp_heavy_tcp",
        version_number=2,
        status="DRAFT",
        rule_specific_prompt="Analyze TCP scan telemetry on fixed destination port. Evaluate connection rates, destination diversity, and authorization status against known vulnerability scanners.",
        required_evidence=(
            "1. security.event_type (ENUM) [CRITICAL] — Authoritative event type\n"
            "2. event.timestamp (DATETIME) [CRITICAL] — Event timestamp\n"
            "3. network.source_ip (IPV4) [STANDARD] — Originating scanner or host IP\n"
            "4. network.destination_port (INTEGER) [STANDARD] — Destination port\n"
            "5. detection.threshold (FLOAT) [CRITICAL] — Authoritative detection trigger threshold"
        ),
        fp_indicators="1. Authorized vulnerability scan with active change ticket.\n2. Approved health monitoring probe.\n3. Verified IT discovery service.",
        tp_indicators="1. Rapid sequential TCP connections from untrusted host.\n2. Targeted service is high-value port.",
        missing_info_criteria="Abstain and vote REQUIRES_ATTENTION if source IP is unrecorded or logs truncated.",
        escalation_conditions="Escalate immediately if scan establishes successful connections to critical assets.",
    )
    c2 = EvidenceRequirementMapper.map_evidence_contract(rule, semantics, archetype_def, v2)
    res_v2 = PolicyQualityValidator.validate_policy_quality(rule, v2, c2, semantics)

    assert res_v2.approval_eligible is True
    assert len(res_v2.blocking_issues) == 0
    assert res_v2.gate_results["G1_RULE_INTEGRITY"].status == GateStatus.PASSED
    assert res_v2.gate_results["G1_RULE_INTEGRITY"].score == 20.0
    assert res_v2.gate_results["G2_ARCHETYPE_RELEVANCE"].status == GateStatus.PASSED
    assert res_v2.gate_results["G2_ARCHETYPE_RELEVANCE"].score == 20.0
    assert res_v2.gate_results["G3_EVIDENCE_FEASIBILITY"].status == GateStatus.PASSED
    assert res_v2.gate_results["G3_EVIDENCE_FEASIBILITY"].score == 20.0
    assert res_v2.gate_results["G4_TP_CRITERIA_VALIDITY"].status == GateStatus.PASSED
    assert res_v2.gate_results["G4_TP_CRITERIA_VALIDITY"].score == 10.0
    assert res_v2.gate_results["G5_FP_CRITERIA_VALIDITY"].status == GateStatus.PASSED
    assert res_v2.gate_results["G5_FP_CRITERIA_VALIDITY"].score == 10.0
    assert res_v2.gate_results["G6_ABSTENTION_ESCALATION"].status == GateStatus.PASSED
    assert res_v2.gate_results["G6_ABSTENTION_ESCALATION"].score == 15.0
    assert res_v2.gate_results["G7_POLICY_CONSISTENCY"].status == GateStatus.PASSED
    assert res_v2.gate_results["G7_POLICY_CONSISTENCY"].score == 10.0
    assert res_v2.gate_results["G8_SIMULATION_REGRESSION"].status == GateStatus.WARNING
    assert res_v2.gate_results["G8_SIMULATION_REGRESSION"].score == 0.0

    # Structural quality 100/100, Total score 85/100 with G8 INSUFFICIENT_DATA
    assert res_v2.structural_quality_score == 100.0
    assert res_v2.quality_score == 85.0


@pytest.mark.asyncio
async def test_authoritative_rule_import_and_g1_scoring(db_session: AsyncSession):
    """
    REQ-Phase1: Incomplete or heuristic definitions receive penalized G1 scores;
    importing authoritative XML updates definition_status to VERIFIED and awards full 20.0 points.
    """
    from app.services.fortisiem_service import FortiSIEMService

    xml_content = """<rule id="PH_RULE_TEST_PORT_SCAN">
        <name>Test Port Scan Rule</name>
        <description>Detects rapid scanning against host ports.</description>
        <severity>HIGH</severity>
        <subCategory>Reconnaissance</subCategory>
        <condition>
            <window>60</window>
            <groupBy>srcIpAddr</groupBy>
            <expression>COUNT(DISTINCT destPort) &gt;= 20</expression>
        </condition>
    </rule>"""

    siem_svc = FortiSIEMService(db_session)
    res = await siem_svc.import_authoritative_rule_definition(
        rule_identifier="PH_RULE_TEST_PORT_SCAN",
        definition_text=xml_content,
        format_type="XML",
    )
    assert res["success"] is True
    assert res["definition_status"] == "VERIFIED"

    stmt = select(Rule).where(Rule.rule_id == "PH_RULE_TEST_PORT_SCAN")
    rule = (await db_session.execute(stmt)).scalars().first()
    assert rule is not None
    assert "Expression: COUNT(DISTINCT destPort) >= 20" in rule.pattern_logic
    assert rule.parsed_metadata.get("definition_status") == "VERIFIED"


@pytest.mark.asyncio
async def test_strict_rule_filtering_and_rule_mismatch_exclusion(db_session: AsyncSession):
    """
    REQ-Phase2 & Phase3: Historical simulation must strictly exclude incidents belonging
    to other rules (e.g. Crowdstrike, Prisma SASE) with RULE_MISMATCH reasons and
    never simulate them against a non-matching target rule.
    """
    # Create target rule
    target_rule = Rule(
        id="rule_target_tcp_scan_01",
        rule_id="PH_RULE_HEAVY_TCP_HOST_SCAN_TARGET",
        name="Heavy TCP Host Scan Target",
        event_type="TCP_SCAN_TARGET",
    )
    db_session.add(target_rule)

    # Create other rule (e.g. Crowdstrike endpoint alert)
    other_rule = Rule(
        id="rule_other_cs_alert_01",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        name="Crowdstrike Suspicious Activity",
        event_type="CS_ALERT",
    )
    db_session.add(other_rule)
    await db_session.flush()

    # Seed 3 Crowdstrike incidents (must NOT be evaluated as TCP scan)
    for i in range(3):
        inc_cs = Incident(
            incident_id=f"INC_CS_{i}_{uuid.uuid4().hex[:6]}",
            rule_id=other_rule.id,
            event_type="CS_ALERT",
            source_ip=f"10.0.0.{i}",
            raw_payload={"src": f"10.0.0.{i}", "alert": "Suspicious PowerShell"},
        )
        db_session.add(inc_cs)
        await db_session.flush()
        db_session.add(HistoricalGroundTruth(
            incident_id=inc_cs.id,
            resolution="True Positive",
            comments="Crowdstrike malware execution alert",
            is_ml_generated=False,
        ))

    await db_session.commit()

    sim_service = PolicySimulationService(db_session)
    run_record = await sim_service.run_dry_run_intelligence_evaluation(
        run_name="Test-Rule-Mismatch-Strict-Filter",
        rule_id=target_rule.id,
        archetype="NETWORK_SCAN",
    )

    funnel = run_record.metrics["funnel"]
    # AIS 2.1 (AIS-F01): Target rule has 0 incidents -> rule-scoped query retrieves 0 (never scans unrelated global 50)
    assert funnel["available"] == 0
    assert funnel["retrieved"] == 0
    assert funnel["total_scanned"] == 0
    assert funnel["rule_matched"] == 0
    assert funnel["evaluated"] == 0
    assert funnel["scored"] == 0
    assert funnel["eligible"] == 0
    assert run_record.validation_state == "INSUFFICIENT_DATA"


@pytest.mark.asyncio
async def test_ground_truth_adjudication_excludes_ml_and_closures_alone():
    """
    REQ-Phase2: Adjudication must mark ML-generated resolutions and closure status alone as UNVERIFIED.
    Human analyst resolutions with clear rationale are marked VERIFIED_TP or VERIFIED_FP.
    """
    # 1. ML-generated resolution
    label, rel, rat = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="False Positive",
        analyst_comments="Resolution set by Machine Learning",
        is_ml_generated=True,
    )
    assert label == GroundTruthLabel.UNVERIFIED

    # 2. ML in comments without is_ml_generated flag
    label, rel, rat = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="False Positive",
        analyst_comments="Resolution set by Machine Learning",
        is_ml_generated=False,
    )
    assert label == GroundTruthLabel.UNVERIFIED

    # 3. Closure alone without disposition
    label, rel, rat = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="Manually Cleared",
        analyst_comments="User closed the incident",
    )
    assert label == GroundTruthLabel.UNVERIFIED

    # 4. Verified human analyst True Positive
    label, rel, rat = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="True Positive",
        analyst_comments="Confirmed credential dumping via mimikatz on domain controller",
    )
    assert label == GroundTruthLabel.VERIFIED_TP
    assert rel == 1.0

    # 5. Verified human analyst False Positive
    label, rel, rat = HistoricalGroundTruthValidator.adjudicate_label(
        raw_resolution="False Positive",
        analyst_comments="Approved SCCM maintenance script running during scheduled maintenance window",
    )
    assert label == GroundTruthLabel.VERIFIED_FP
    assert rel == 1.0


@pytest.mark.asyncio
async def test_six_stage_eligibility_funnel_and_exclusions(db_session: AsyncSession):
    """
    REQ-Phase2 & REQ-Phase3: Six-stage eligibility funnel:
    total_scanned -> rule_matched -> analyst_labeled -> eligible -> excluded -> evaluated.
    """
    rule = Rule(
        id=f"rule_funnel_{uuid.uuid4().hex[:8]}",
        rule_id="RULE_FUNNEL_TEST",
        name="Funnel Test Rule",
        event_type="FUNNEL_EVENT",
    )
    db_session.add(rule)
    await db_session.flush()

    prompt = RulePrompt(rule_id=rule.id, title=f"Prompt — {rule.name}")
    db_session.add(prompt)
    await db_session.flush()

    pv = PromptVersion(
        prompt_id=prompt.id,
        version_number=1,
        status="APPROVED",
        rule_specific_prompt="Standard triage.",
        detection_conditions="Standard conditions.",
        required_evidence="1. security.event_type\n2. event.timestamp",
        tp_indicators="Confirmed threat.",
        fp_indicators="Legitimate activity.",
        missing_info_criteria="Missing critical fields.",
        escalation_conditions="Escalate P1.",
    )
    db_session.add(pv)
    await db_session.flush()

    # Seed 7 incidents:
    # 2 human TP
    # 2 human FP
    # 2 ML-generated (excluded)
    # 1 unclosed (excluded)
    for i in range(2):
        inc_tp = Incident(
            incident_id=f"INC_TP_{i}_{uuid.uuid4().hex[:6]}",
            rule_id=rule.id,
            event_type="FUNNEL_EVENT",
            source_ip=f"192.0.2.1{i}",
            raw_payload={"src": f"192.0.2.1{i}", "event_type": "FUNNEL_EVENT"},
        )
        db_session.add(inc_tp)
        await db_session.flush()
        db_session.add(HistoricalGroundTruth(
            incident_id=inc_tp.id,
            resolution="True Positive",
            comments=f"Confirmed security incident with verified malicious activity #{i}",
            cleared_user="analyst1",
            is_ml_generated=False,
        ))

    for i in range(2):
        inc_fp = Incident(
            incident_id=f"INC_FP_{i}_{uuid.uuid4().hex[:6]}",
            rule_id=rule.id,
            event_type="FUNNEL_EVENT",
            source_ip=f"192.0.2.2{i}",
            raw_payload={"src": f"192.0.2.2{i}", "event_type": "FUNNEL_EVENT"},
        )
        db_session.add(inc_fp)
        await db_session.flush()
        db_session.add(HistoricalGroundTruth(
            incident_id=inc_fp.id,
            resolution="False Positive",
            comments=f"Confirmed authorized IT administrative operation under change window #{i}",
            cleared_user="analyst2",
            is_ml_generated=False,
        ))

    for i in range(2):
        inc_ml = Incident(
            incident_id=f"INC_ML_{i}_{uuid.uuid4().hex[:6]}",
            rule_id=rule.id,
            event_type="FUNNEL_EVENT",
            source_ip=f"192.0.2.3{i}",
            raw_payload={"src": f"192.0.2.3{i}", "event_type": "FUNNEL_EVENT"},
        )
        db_session.add(inc_ml)
        await db_session.flush()
        db_session.add(HistoricalGroundTruth(
            incident_id=inc_ml.id,
            resolution="False Positive",
            comments="Resolution set by Machine Learning",
            cleared_user="",
            is_ml_generated=True,
        ))

    inc_unclosed = Incident(
        incident_id=f"INC_UNCLOSED_{uuid.uuid4().hex[:6]}",
        rule_id=rule.id,
        event_type="FUNNEL_EVENT",
        source_ip="192.0.2.40",
        raw_payload={"src": "192.0.2.40", "event_type": "FUNNEL_EVENT"},
    )
    db_session.add(inc_unclosed)
    await db_session.flush()

    await db_session.commit()

    sim_service = PolicySimulationService(db_session)
    summary = await sim_service.evaluate_candidate_policy(
        rule_id=rule.id,
        candidate_version=pv,
        baseline_version=None,
    )

    funnel = summary["funnel"]
    assert funnel["total_scanned"] == 7
    assert funnel["rule_matched"] == 7
    assert funnel["analyst_labeled"] == 6  # 6 incidents had resolution in SIEM
    assert funnel["eligible"] == 4         # Exactly 4 eligible cases (2 human TP + 2 human FP)
    assert funnel["excluded"] == 3         # 2 ML + 1 unclosed
    assert funnel["evaluated"] == 4        # AIS 2.1 (AIS-F04): Strictly excludes ineligible rows from G8 inference & scoring
    assert funnel["scored"] == 4

    reasons = funnel["exclusion_reasons"]
    assert reasons["HEURISTIC_OR_ML_LABEL"] == 2
    assert reasons["MISSING_ANALYST_LABEL"] == 1
    assert len(funnel["exclusions_detail"]) == 3
    # Check that rule_id is populated on exclusions_detail
    assert all("rule_id" in ex for ex in funnel["exclusions_detail"])

    # Verify stage_details populated for pop-up drilldown modal
    stage_details = summary.get("stage_details") or funnel.get("stage_details")
    assert stage_details is not None
    assert len(stage_details["scanned"]) == 7
    assert len(stage_details["rule_matched"]) == 7
    assert len(stage_details["analyst_labeled"]) == 6
    assert len(stage_details["eligible"]) == 4
    assert len(stage_details["excluded"]) == 3
    assert len(stage_details["evaluated"]) == 4

    # Sample sufficiency: 4 < 5 -> INSUFFICIENT_DATA
    assert summary["simulation_status"] == SimulationStatus.INSUFFICIENT_DATA.value
    assert summary["regression_status"] == "NOT_ASSESSED"
