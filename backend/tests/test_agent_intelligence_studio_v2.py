import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.schemas.evidence_contract import RuleEvidenceContract
from app.schemas.rule_intelligence import (
    SemanticsDefinitionStatus,
    SourceProvenance,
    ArchetypeId,
)
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.policy_generation_service import PolicyGenerationService
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.policy_simulation_service import PolicySimulationService
from app.services.policy_lifecycle_monitor import PolicyLifecycleMonitor
from app.services.bulk_quality_audit_service import BulkQualityAuditService
from app.services.prompt_studio_service import AgentPolicyEngine


@pytest.mark.asyncio
async def test_req01_rule_intelligence_authoritative_vs_observed():
    """
    REQ-01: Rule Intelligence Analyzer must distinguish authoritative SIEM definitions
    from observed incident telemetry. An observed sentBytes64 must NOT be treated as a threshold.
    """
    rule_auth = Rule(
        id="AUTH_RULE_001",
        rule_id="AUTH_RULE_001",
        name="High Volume Outbound Transfer",
        event_type="NETWORK_TRAFFIC",
        data_source="FortiSIEM",
    )
    authoritative_def = {
        "rule_id": "AUTH_RULE_001",
        "rule_name": "High Volume Outbound Transfer",
        "threshold": 1073741824,  # 1GB
        "threshold_unit": "bytes",
        "aggregation_window": "15m",
        "grouping_keys": ["src_ip"],
        "primary_behavior": "network_exfiltration",
    }
    semantics_a = RuleIntelligenceAnalyzer.analyze_rule(
        rule=rule_auth,
        authoritative_siem_definition=authoritative_def,
    )
    assert semantics_a.definition_status == SemanticsDefinitionStatus.VERIFIED
    assert semantics_a.source_provenance == SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION
    assert semantics_a.threshold == 1073741824
    assert semantics_a.threshold_unit == "bytes"
    assert semantics_a.aggregation_window == "15m"
    assert semantics_a.review_required is False

    # Case B: Only observed incident pattern metadata exists (e.g. sentBytes64: 2130499380)
    rule_obs = Rule(
        id="PH_RULE_LARGE_OUTBOUND_XFER",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        name="Large Outbound Transfer",
        event_type="Exfiltration",
        data_source="MSSP-Primary",
        pattern_logic='{"sentBytes64": 2130499380}',
        parsed_metadata={"source": "AUTO_SYNCED_FROM_INCIDENT"},
    )
    semantics_b = RuleIntelligenceAnalyzer.analyze_rule(
        rule=rule_obs,
        observed_incident_sample={"sentBytes64": 2130499380},
    )
    # Must NOT assume sentBytes64 is the detection threshold
    assert semantics_b.threshold is None
    assert semantics_b.definition_status == SemanticsDefinitionStatus.INCOMPLETE
    assert semantics_b.review_required is True
    assert "sentBytes64" in semantics_b.observed_fields
    assert any("threshold" in r.lower() for r in semantics_b.missing_requirements)


@pytest.mark.asyncio
async def test_req02_detection_archetype_classification_and_contradictions():
    """
    REQ-02: Detection Archetype Engine classifies rules into 12 versioned archetypes
    and detects contradictions.
    """
    rule_xfer = Rule(
        id="PH_RULE_LARGE_OUTBOUND_XFER",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        name="Large Outbound Transfer",
        event_type="Exfiltration",
        data_source="MSSP-Primary",
    )
    semantics_xfer = RuleIntelligenceAnalyzer.analyze_rule(rule=rule_xfer)
    classification_xfer = DetectionArchetypeRegistry.classify_rule(semantics_xfer, rule_xfer)
    assert classification_xfer.primary_archetype == ArchetypeId.NETWORK_EXFILTRATION
    assert classification_xfer.confidence_score >= 0.70

    # Test 2: Malware Execution maps to MALWARE_EXECUTION
    rule_malware = Rule(
        id="RULE_MALWARE_01",
        rule_id="RULE_MALWARE_01",
        name="Cobalt Strike Malware Process Execution",
        event_type="Process_Creation",
        pattern_logic="powershell.exe -enc",
    )
    semantics_malware = RuleIntelligenceAnalyzer.analyze_rule(rule=rule_malware)
    classification_malware = DetectionArchetypeRegistry.classify_rule(semantics_malware, rule_malware)
    assert classification_malware.primary_archetype == ArchetypeId.MALWARE_EXECUTION

    # Test 3: Contradiction detection rules on archetype
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(ArchetypeId.NETWORK_EXFILTRATION)
    assert len(archetype_def.contradiction_rules) >= 3
    rule_ids = [r["rule_id"] for r in archetype_def.contradiction_rules]
    assert "INBOUND_LABELED_AS_EXFILTRATION" in rule_ids

    # Test 4: Unknown rule classification fails safely to UNKNOWN
    rule_unknown = Rule(
        id="RULE_UNK_99",
        rule_id="RULE_UNK_99",
        name="Custom Vendor Obscure Event 99",
        event_type="VND_CUSTOM",
    )
    semantics_unknown = RuleIntelligenceAnalyzer.analyze_rule(rule=rule_unknown)
    classification_unk = DetectionArchetypeRegistry.classify_rule(semantics_unknown, rule_unknown)
    assert classification_unk.primary_archetype == ArchetypeId.UNKNOWN


@pytest.mark.asyncio
async def test_req03_evidence_requirement_mapper():
    """
    REQ-03: Evidence Requirement Mapper generates Core, Conditional, Optional,
    and Unsupported telemetry fields.
    """
    rule_exfil = Rule(
        id="PH_RULE_LARGE_OUTBOUND_XFER",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        name="Large Outbound Transfer",
        event_type="Exfiltration",
        data_source="MSSP-Primary",
    )
    semantics_exfil = RuleIntelligenceAnalyzer.analyze_rule(rule=rule_exfil)
    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(ArchetypeId.NETWORK_EXFILTRATION)

    contract = EvidenceRequirementMapper.map_evidence_contract(
        rule=rule_exfil,
        semantics=semantics_exfil,
        archetype_def=archetype_def,
    )
    field_names = [f.field for f in contract.required_evidence]
    assert any("source_ip" in f for f in field_names)
    assert any("destination_ip" in f for f in field_names)
    assert any("bytes" in f for f in field_names)

    # Network Exfiltration must mark file_hash as unsupported in archetype
    assert any("hash" in uf or "file_hash" in uf for uf in archetype_def.unsupported_fields)


@pytest.mark.asyncio
async def test_req04_policy_generation_and_soc_baseline_v2():
    """
    REQ-04: Policy Generation Service synthesizes 9 structured sections.
    It does not invent missing thresholds, and contains no hardcoded confidence intervals.
    """
    rule_exfil = Rule(
        id="PH_RULE_LARGE_OUTBOUND_XFER",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        name="Large Outbound Transfer",
        event_type="Exfiltration",
        data_source="MSSP-Primary",
    )
    draft_dict = PolicyGenerationService.generate_nine_section_draft(rule=rule_exfil)

    # Check 9 sections populated
    assert draft_dict["common_prompt"] != ""
    assert draft_dict["rule_specific_prompt"] != ""
    assert draft_dict["detection_conditions"] != ""
    assert draft_dict["required_evidence"] != ""
    assert draft_dict["tp_indicators"] != ""
    assert draft_dict["fp_indicators"] != ""
    assert draft_dict["missing_info_criteria"] != ""
    assert draft_dict["escalation_conditions"] != ""
    assert len(draft_dict["analyst_questions"]) >= 3

    # Check safety: No hardcoded confidence intervals (e.g. "85-95%")
    assert "85-95%" not in draft_dict["common_prompt"]
    assert "85-95%" not in draft_dict["rule_specific_prompt"]

    # Check that missing threshold is explicitly flagged in detection conditions
    assert "UNSPECIFIED" in draft_dict["detection_conditions"] or "INCOMPLETE" in draft_dict["detection_conditions"]


@pytest.mark.asyncio
async def test_req05_policy_quality_validator_8_gates():
    """
    REQ-05: Policy Quality Validator evaluates 8 gates.
    Hard gate failures override score; irrelevant policy is flagged.
    """
    rule_incomplete = Rule(
        id="PH_RULE_LARGE_OUTBOUND_XFER",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        name="Large Outbound Transfer",
        event_type="Exfiltration",
        data_source="MSSP-Primary",
        pattern_logic='{"sentBytes64": 2130499380}',
        parsed_metadata={"source": "AUTO_SYNCED_FROM_INCIDENT"},
    )
    semantics = RuleIntelligenceAnalyzer.analyze_rule(rule=rule_incomplete)

    # Irrelevant policy: Network Exfiltration containing Malware process/hash requirements
    irrelevant_ver = PromptVersion(
        id=f"pv_{uuid.uuid4().hex[:8]}",
        prompt_id=f"rp_{uuid.uuid4().hex[:8]}",
        version_number=1,
        status="DRAFT",
        common_prompt="Standard SOC baseline protocol.",
        rule_specific_prompt="Verify file hash on VirusTotal, check parent process command line, inspect DLL injection.",
        detection_conditions="sentBytes64 > 2130499380",
        required_evidence="file_hash, process_command_line, parent_process",
        tp_indicators="Known malware hash match",
        fp_indicators="Legitimate admin powershell script",
        missing_info_criteria="Missing file hash",
        escalation_conditions="Active malware beaconing",
        analyst_questions=["What is the malware hash?"],
        change_summary="Irrelevant malware draft",
    )

    assessment = PolicyQualityValidator.validate_policy_quality(
        rule=rule_incomplete,
        prompt_version=irrelevant_ver,
        semantics=semantics,
    )

    # Gate 1: Integrity must fail due to incomplete SIEM definition
    assert assessment.gate_results["G1_RULE_INTEGRITY"].status.value == "FAILED"

    # Gate 2: Relevance must fail due to process/malware mismatch for network exfiltration
    assert assessment.gate_results["G2_ARCHETYPE_RELEVANCE"].status.value == "FAILED"

    # Approval MUST be blocked regardless of score
    assert assessment.approval_eligible is False
    assert len(assessment.blocking_issues) >= 2

    # Cryptographic digests must be present
    assert len(assessment.policy_digest) == 64
    assert len(assessment.rule_digest) == 64


@pytest.mark.asyncio
async def test_req06_policy_quality_scoring_index():
    """
    REQ-06: Policy Quality Scoring Index produces a 0-100 inspection index,
    not a verdict accuracy claim.
    """
    rule_dns = Rule(
        id="RULE_DNS_01",
        rule_id="RULE_DNS_01",
        name="DNS Tunneling Activity",
        event_type="DNS_QUERY",
    )
    auth_def = {
        "rule_id": "RULE_DNS_01",
        "threshold": 50,
        "threshold_unit": "queries/min",
        "aggregation_window": "5m",
        "grouping_keys": ["src_ip", "query_domain"],
        "primary_behavior": "dns_tunneling",
    }
    semantics = RuleIntelligenceAnalyzer.analyze_rule(rule=rule_dns, authoritative_siem_definition=auth_def)
    draft_dict = PolicyGenerationService.generate_nine_section_draft(
        rule=rule_dns,
        authoritative_siem_definition=auth_def,
    )
    valid_cols = {c.name for c in PromptVersion.__table__.columns}
    pv_kwargs = {k: v for k, v in draft_dict.items() if k in valid_cols}
    pv = PromptVersion(
        id=f"pv_{uuid.uuid4().hex[:8]}",
        prompt_id=f"rp_{uuid.uuid4().hex[:8]}",
        version_number=1,
        **pv_kwargs,
    )

    assessment = PolicyQualityValidator.validate_policy_quality(
        rule=rule_dns,
        prompt_version=pv,
        semantics=semantics,
    )

    # Quality score is bounded 0 to 100
    assert 0.0 <= assessment.quality_score <= 100.0
    assert "detection_semantics" in assessment.score_breakdown
    assert "evidence_contract" in assessment.score_breakdown
    assert "tp_fp_criteria" in assessment.score_breakdown


@pytest.mark.asyncio
async def test_req07_historical_simulation_and_insufficient_data(db_session: AsyncSession):
    """
    REQ-07: Historical Simulation Lab tests regression against historical incidents.
    If sample count < 5, reports INSUFFICIENT_DATA honestly.
    """
    sim_service = PolicySimulationService(db_session)

    dummy_pv = PromptVersion(
        id="dummy_pv",
        prompt_id="dummy_rp",
        version_number=1,
        status="DRAFT",
        rule_specific_prompt="Test directive",
    )

    # Evaluate for a rule with zero historical incidents
    result = await sim_service.evaluate_candidate_policy(
        rule_id="NON_EXISTENT_OR_NEW_RULE",
        candidate_version=dummy_pv,
    )
    assert result["simulation_status"] == "INSUFFICIENT_DATA"
    assert result["sample_count"] < 5
    assert result["critical_regressions"] == 0


@pytest.mark.asyncio
async def test_req08_approval_governance_and_contract_activation(db_session: AsyncSession):
    """
    REQ-08: SOC Lead approval requires a green quality validation.
    Hard gate failures block approval. Approved policy activates Evidence Contract atomically.
    """
    engine = AgentPolicyEngine(db_session)

    # Create a test rule without authoritative threshold
    rule = Rule(
        id=f"RULE_TEST_{uuid.uuid4().hex[:6]}",
        rule_id=f"RULE_TEST_{uuid.uuid4().hex[:6]}",
        name="Test Incomplete Rule",
        event_type="Exfiltration",
        severity="MEDIUM",
        status="ACTIVE",
        pattern_logic='{"sentBytes64": 2130499380}',
        parsed_metadata={"source": "AUTO_SYNCED_FROM_INCIDENT"},
    )
    db_session.add(rule)
    await db_session.commit()

    # Generate initial draft via engine
    rule_prompt = await engine.get_or_create_rule_prompt(rule.id)
    ver_res = await db_session.execute(select(PromptVersion).where(PromptVersion.prompt_id == rule_prompt.id))
    versions = ver_res.scalars().all()
    assert len(versions) >= 1
    draft_v1 = versions[0]

    # Attempt to approve draft_v1 when definition is INCOMPLETE
    # Should raise ValueError because G1 fails
    with pytest.raises(ValueError) as excinfo:
        await engine.approve_version(
            rule_id=rule.id,
            version_id=draft_v1.id,
            user_id="soc_lead_admin",
            change_summary="Premature approval attempt",
        )
    assert "blocked" in str(excinfo.value).lower() or "gate" in str(excinfo.value).lower() or "integrity" in str(excinfo.value).lower()


@pytest.mark.asyncio
async def test_req09_bulk_policy_quality_audit(db_session: AsyncSession):
    """
    REQ-09: Bulk Policy Quality Audit evaluates detection rules in chunks of 100
    in strict read-only mode without altering approved policies.
    """
    # Seed 15 test rules
    for i in range(15):
        rid = f"BULK_RULE_{i}_{uuid.uuid4().hex[:4]}"
        r = Rule(
            id=rid,
            rule_id=rid,
            name=f"Bulk Rule {i}",
            event_type="Network",
            severity="MEDIUM",
            status="ACTIVE",
        )
        db_session.add(r)
    await db_session.commit()

    audit_service = BulkQualityAuditService(db_session)
    job = await audit_service.execute_bulk_audit(user_id="test_admin")

    assert job.processed_rules >= 15
    assert job.status == "COMPLETED"
    assert job.id is not None
    assert job.passed_count >= 0


@pytest.mark.asyncio
async def test_req10_continuous_policy_monitoring_and_drift(db_session: AsyncSession):
    """
    REQ-10: Policy Lifecycle Monitor detects SIEM rule drift and captures
    verified analyst feedback without silently modifying active policies.
    """
    monitor = PolicyLifecycleMonitor(db_session)

    rid = f"RULE_DRIFT_{uuid.uuid4().hex[:6]}"
    rule = Rule(
        id=rid,
        rule_id=rid,
        name="Drift Test Rule",
        event_type="Authentication",
        severity="HIGH",
        status="ACTIVE",
    )
    db_session.add(rule)
    await db_session.commit()

    # 1. Detect SIEM rule change
    drift_events = await monitor.detect_and_handle_rule_drift(
        rule=rule,
        updated_rule_dict={"pattern_logic": "sentBytes > 100"},
    )
    assert len(drift_events) > 0
    assert drift_events[0].trigger_type == "SIEM_RULE_DEFINITION_CHANGED"
    assert drift_events[0].revalidation_required is True

    # 2. Capture verified analyst feedback
    feedback_event = await monitor.ingest_verified_analyst_feedback(
        rule_id=rule.id,
        incident_id="INC-12345",
        adjudicated_verdict="FALSE_POSITIVE",
        model_verdict="TRUE_POSITIVE",
        analyst_notes="Authorized monthly maintenance backup script",
    )
    assert feedback_event is not None
    assert feedback_event.trigger_type == "ANALYST_FEEDBACK_VERIFIED"

    # 3. Acknowledge drift
    count = await monitor.acknowledge_drift(rule.id)
    assert count >= 2


@pytest.mark.asyncio
async def test_reference_case_large_outbound_transfer_full_lifecycle(
    client: AsyncClient,
    db_session: AsyncSession,
    admin_token: str,
):
    """
    CRITICAL MANDATORY REFERENCE CASE: PH_RULE_LARGE_OUTBOUND_XFER
    Rule Identifier: PH_RULE_LARGE_OUTBOUND_XFER
    Rule Name: Large Outbound Transfer
    Category: Exfiltration
    Data Source: MSSP-Primary
    Severity: MEDIUM
    Observed Metadata: {"sentBytes64": 2130499380}

    Verification Criteria:
    1. Classified as NETWORK_EXFILTRATION.
    2. Does NOT assume 2130499380 is a configured threshold.
    3. Missing authoritative definition marks definition_status = INCOMPLETE.
    4. Quality validator G1 fails (integrity blocker) and blocks approval.
    5. Quality validator G2 rejects malware-focused instructions.
    6. When authoritative definition is supplied, G1 passes.
    """
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Ingest/create the reference rule with observed sentBytes64 pattern
    rule = Rule(
        id="PH_RULE_LARGE_OUTBOUND_XFER",
        rule_id="PH_RULE_LARGE_OUTBOUND_XFER",
        name="Large Outbound Transfer",
        event_type="Exfiltration",
        severity="MEDIUM",
        status="ACTIVE",
        data_source="MSSP-Primary",
        pattern_logic='{"sentBytes64": 2130499380}',
        parsed_metadata={"source": "AUTO_SYNCED_FROM_INCIDENT"},
    )
    db_session.add(rule)
    await db_session.commit()

    # 2. Analyze Rule Intelligence via API
    analyze_res = await client.post(
        f"/api/prompts/rule/{rule.id}/analyze",
        headers=headers,
        json={"authoritative_siem_definition": None},
    )
    assert analyze_res.status_code == 200
    intel_data = analyze_res.json()
    assert intel_data["semantics"]["definition_status"] == "INCOMPLETE"
    assert intel_data["semantics"]["threshold"] is None
    assert intel_data["classification"]["primary_archetype"] == "NETWORK_EXFILTRATION"

    # 3. Generate Intelligent Draft via API
    draft_res = await client.post(
        f"/api/prompts/rule/{rule.id}/generate-intelligent-draft",
        headers=headers,
        json={"authoritative_siem_definition": None},
    )
    assert draft_res.status_code == 200
    draft = draft_res.json()
    assert draft["is_template_draft"] is True
    assert draft["status"] == "DRAFT"

    # 4. Validate Quality — must fail G1 due to incomplete definition
    val_res = await client.post(
        f"/api/prompts/rule/{rule.id}/validate-quality?version_id={draft['id']}",
        headers=headers,
    )
    assert val_res.status_code == 200
    q_data = val_res.json()
    assert q_data["approval_eligible"] is False
    assert len(q_data["blocking_issues"]) > 0
    assert q_data["gate_results"]["G1_RULE_INTEGRITY"]["status"] == "FAILED"

    # 5. Attempt Approval via API — must be rejected (400)
    appr_res = await client.post(
        f"/api/prompts/rule/{rule.id}/approve/{draft['id']}",
        headers=headers,
        json={"change_summary": "Attempting approval without authoritative definition"},
    )
    assert appr_res.status_code == 400

    # 6. Now provide authoritative SIEM rule definition and re-generate
    auth_def = {
        "rule_id": "PH_RULE_LARGE_OUTBOUND_XFER",
        "rule_name": "Large Outbound Transfer",
        "threshold": 1000000000,  # 1GB authoritative threshold
        "threshold_unit": "bytes",
        "aggregation_window": "30m",
        "grouping_keys": ["src_ip", "dest_ip"],
        "primary_behavior": "network_exfiltration",
    }
    draft_v2_res = await client.post(
        f"/api/prompts/rule/{rule.id}/generate-intelligent-draft",
        headers=headers,
        json={"authoritative_siem_definition": auth_def},
    )
    assert draft_v2_res.status_code == 200
    draft_v2 = draft_v2_res.json()

    # Validate Quality of v2 — G1 should pass
    val_v2_res = await client.post(
        f"/api/prompts/rule/{rule.id}/validate-quality?version_id={draft_v2['id']}",
        headers=headers,
    )
    assert val_v2_res.status_code == 200
    q_v2 = val_v2_res.json()
    assert q_v2["gate_results"]["G1_RULE_INTEGRITY"]["status"] == "PASSED"
    assert q_v2["approval_eligible"] is True

    # 7. Approve v2 — must succeed and activate
    appr_v2_res = await client.post(
        f"/api/prompts/rule/{rule.id}/approve/{draft_v2['id']}",
        headers=headers,
        json={"change_summary": "Approved by SOC Lead with verified authoritative definition"},
    )
    assert appr_v2_res.status_code == 200
    approved_ver = appr_v2_res.json()
    assert approved_ver["status"] == "APPROVED"
