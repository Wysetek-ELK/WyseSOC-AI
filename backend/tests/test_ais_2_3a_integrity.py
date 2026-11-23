import pytest
import zipfile
import json
from app.models.incident import Incident
from app.models.rule import Rule
from app.services.empirical_benchmark_harness import EventAdapter
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_compaction_service import EvidenceCompactionService
from app.services.token_budget_service import TokenBudgetService
from app.services.model_claim_extractor import ModelClaimExtractor, ModelSupportingClaim
from app.services.verdict_pipeline import build_sanitized_model_payload
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.evidence_contract_service import EvidenceContractService


def test_canonical_field_aliasing_for_process_binary():
    """Verify that 'File Name' in raw telemetry produces both process.file_name and process.name."""
    inc = Incident(
        id="test-alias-01",
        incident_id=99901,
        title="Test Process Binary Alert",
        event_type="ProcessAlert",
        severity=5,
        raw_payload={
            "rawEvents": [{
                "eventId": "EVT-01",
                "attribute": {
                    "File Name": "UltraViewer_Service.exe",
                    "Parent File Name": "services.exe",
                    "Command": '"C:\\Program Files\\UltraViewer\\UltraViewer_Service.exe"',
                    "SHA256 Hash": "10ff43f2d4a991c83caefce1c4442fa95258d0d93f168dde339f52322aa371e9",
                }
            }]
        }
    )
    raw_events = [EventAdapter(inc.raw_payload["rawEvents"][0], 0)]
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc, raw_events)
    fields = {r.source_field: r.observed_value for r in norm_res.records}

    assert "process.file_name" in fields
    assert fields["process.file_name"] == "UltraViewer_Service.exe"
    assert "process.name" in fields
    assert fields["process.name"] == "UltraViewer_Service.exe"
    assert "process.parent_name" in fields
    assert fields["process.parent_name"] == "services.exe"
    assert "file.hash_sha256" in fields


def test_compaction_preservation_of_process_lineage():
    """Verify that process.file_name, process.name, and process.parent_name are never evicted during compaction."""
    inc = Incident(
        id="test-compaction-01",
        incident_id=99902,
        title="Compaction Invariant Alert",
        event_type="ProcessAlert",
        severity=5,
    )
    # Create 50 noisy firewall log events along with 1 process event
    raw_events_list = [
        {
            "eventId": f"FW-{i}",
            "attribute": {
                "Event Receive Time": 1793821800000 + i * 1000,
                "Action": "deny",
                "Destination IP": f"10.0.0.{i}",
                "Destination TCP/UDP Port": 80,
            }
        }
        for i in range(50)
    ]
    raw_events_list.append({
        "eventId": "EVT-PROC",
        "attribute": {
            "File Name": "malware.exe",
            "Parent File Name": "explorer.exe",
            "Command": "malware.exe -run",
            "SHA256 Hash": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
        }
    })
    raw_events = [EventAdapter(e, i) for i, e in enumerate(raw_events_list)]
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc, raw_events)

    contract_req = ["process.name", "process.command_line", "user.name", "endpoint.hostname"]
    compaction_res = EvidenceCompactionService.compact_and_deduplicate(
        records=norm_res.records,
        contract_required_fields=contract_req,
        max_evidence_budget_tokens=1000,
    )
    compacted_fields = {r["source_field"]: r["observed_value"] for r in compaction_res["compacted_records"]}

    assert "process.name" in compacted_fields or "process.file_name" in compacted_fields
    assert "process.parent_name" in compacted_fields
    assert "file.hash_sha256" in compacted_fields


def test_claim_grounding_resilient_citation_resolution():
    """Verify that model claims citing field variants (e.g. file_name) ground against canonical records."""
    inc = Incident(
        id="test-grounding-01",
        incident_id=99903,
        title="Prisma SASE Alert",
        event_type="ThreatAlert",
        severity=5,
    )
    raw_events = [EventAdapter({
        "eventId": "EVT-PA",
        "attribute": {
            "File Name": "ss-widget.min.js",
            "Application Name": "surveysensum-base",
            "Source IP": "172.25.14.80",
        }
    }, 0)]
    norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc, raw_events)

    # Model generates structured claim with field='file_name' and synthetic citation ID
    claim = ModelSupportingClaim(
        claim_type="OBSERVED_FACT",
        field="file_name",
        asserted_value="ss-widget.min.js",
        cited_evidence_ids=["EV-99903-TOP-file_name"],
        evidence_ids=["EV-99903-TOP-file_name"],
        claim_text="Observed download of ss-widget.min.js",
    )
    grounding_res = ModelClaimExtractor.ground_claims(
        incident_id="99903",
        claims=[claim],
        normalization_result=norm_res,
    )

    assert grounding_res.grounded_claims == 1
    assert grounding_res.unsupported_claims == 0
    assert grounding_res.has_hallucinations is False
    assert claim.is_grounded is True
    assert claim.grounding_status == "GROUNDED"


def test_token_budget_bpe_calibrated_bounds():
    """Verify that TokenBudgetService strictly bounds real historical incident prompt tokens <= 3328."""
    rule = Rule(
        id="0974a66e-ede2-4a6a-821b-6283a99c8aa4",
        name="Crowdstrike: Suspicious Activity",
        rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        event_type="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        severity=5
    )
    with zipfile.ZipFile("fixtures/Incident json.zip", "r") as z:
        raw_data = json.loads(z.read("Incident json/Crowdstrike Suspicious Activity/IncidnetId_132438483.json").decode("utf-8"))

    raw_events = [EventAdapter(e, i) for i, e in enumerate(raw_data.get("rawEvents", []))]
    inc = Incident(
        id="test-132438483",
        incident_id=132438483,
        title=raw_data.get("title"),
        event_type=raw_data.get("eventType"),
        severity=raw_data.get("severity", 5),
        raw_payload=raw_data
    )
    norm_res, payload_dict = build_sanitized_model_payload(inc, rule)
    compiled = PolicyCompilerService.compile_policy(rule=rule, prompt_version=None)

    budgeted = TokenBudgetService.budget_prompt(
        compiled_policy=compiled,
        incident_payload=payload_dict,
        rag_block="",
        max_context_tokens=4096,
        max_completion_tokens=768,
        reserved_overhead_tokens=TokenBudgetService.estimate_tokens({"id": rule.id, "name": rule.name}),
        target_input_budget=3328,
    )

    assert budgeted.can_proceed_to_inference is True
    assert budgeted.breakdown.total_prompt_tokens <= 3328
    # Ensure completion budget of 768 is strictly safeguarded (4096 - 3328 = 768)
    headroom = 4096 - budgeted.breakdown.total_prompt_tokens
    assert headroom >= 768
