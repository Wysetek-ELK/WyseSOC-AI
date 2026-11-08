"""
test_evidence_contracts.py
Phase 2 Test Suite: Rule Evidence Contracts (P2-REQ-02)

Tests:
1. Rule with APPROVED prompt version yields APPROVED contract
2. Rule with DRAFT or unapproved prompt version yields UNVERIFIED contract
3. Rule with no prompt version yields UNVERIFIED contract
4. Derivation of PROCESS_EXECUTION archetype contract
5. Derivation of NETWORK_CONNECTION archetype contract
6. Derivation of FILE_MALWARE archetype contract
7. Derivation of AUTHENTICATION archetype contract
8. Derivation of GENERIC archetype contract
9. Critical field requirements and TP/FP criteria presence
10. Contradiction rules presence in contract
"""

import pytest
from app.services.evidence_contract_service import EvidenceContractService
from app.schemas.evidence_contract import RuleEvidenceContract


class DummyRule:
    def __init__(self, rule_id="RULE-101", name="Suspicious PowerShell Execution", event_type="Process-Creation"):
        self.id = rule_id
        self.rule_id = rule_id
        self.name = name
        self.event_type = event_type


class DummyPromptVersion:
    def __init__(self, pv_id="PV-01", version_number=2, status="APPROVED"):
        self.id = pv_id
        self.version_number = version_number
        self.status = status


def test_approved_prompt_yields_approved_contract():
    """An approved prompt version must derive an APPROVED contract."""
    rule = DummyRule(rule_id="RULE-01", name="Powershell Download Cradle")
    pv = DummyPromptVersion(pv_id="PV-10", version_number=3, status="APPROVED")

    contract = EvidenceContractService.get_contract_for_rule(rule, pv)
    assert contract.status == "APPROVED"
    assert contract.contract_id == "EC-RULE-01-V3"
    assert contract.version_number == 3
    assert contract.prompt_version_id == "PV-10"


def test_draft_prompt_yields_unverified_contract():
    """A draft or unapproved prompt version must derive an UNVERIFIED contract."""
    rule = DummyRule(rule_id="RULE-02", name="Powershell Download Cradle")
    pv = DummyPromptVersion(pv_id="PV-11", version_number=4, status="DRAFT")

    contract = EvidenceContractService.get_contract_for_rule(rule, pv)
    assert contract.status == "UNVERIFIED"


def test_missing_prompt_yields_unverified_contract():
    """When no prompt version is associated, contract status is UNVERIFIED."""
    rule = DummyRule(rule_id="RULE-03")
    contract = EvidenceContractService.get_contract_for_rule(rule, None)
    assert contract.status == "UNVERIFIED"
    assert contract.prompt_version_id is None


def test_archetype_process_execution():
    """Process execution archetype requirements."""
    rule = DummyRule(name="Suspicious LOLBin Execution", event_type="Windows-Process-Execution")
    pv = DummyPromptVersion(status="APPROVED")
    contract = EvidenceContractService.get_contract_for_rule(rule, pv)

    assert contract.detection_archetype == "PROCESS_EXECUTION"
    fields = [req.field for req in contract.required_evidence]
    assert "process.command_line" in fields
    assert "process.name" in fields
    assert "process.parent_name" in fields
    assert "user.name" in fields

    # Verify critical requirement flags
    cmd_req = next(r for r in contract.required_evidence if r.field == "process.command_line")
    assert cmd_req.critical is True
    assert cmd_req.required_for_tp is True


def test_archetype_network_connection():
    """Network connection archetype requirements."""
    rule = DummyRule(name="Outbound C2 Beaconing", event_type="Firewall-Traffic-Flow")
    pv = DummyPromptVersion(status="APPROVED")
    contract = EvidenceContractService.get_contract_for_rule(rule, pv)

    assert contract.detection_archetype == "NETWORK_CONNECTION"
    fields = [req.field for req in contract.required_evidence]
    assert "network.destination_ip" in fields
    assert "network.source_ip" in fields
    assert "network.destination_port" in fields


def test_archetype_file_malware():
    """File malware archetype requirements."""
    rule = DummyRule(name="Ransomware Binary Dropped on Disk", event_type="Antivirus-Quarantine")
    pv = DummyPromptVersion(status="APPROVED")
    contract = EvidenceContractService.get_contract_for_rule(rule, pv)

    assert contract.detection_archetype == "FILE_MALWARE"
    fields = [req.field for req in contract.required_evidence]
    assert "file.hash_sha256" in fields
    assert "endpoint.hostname" in fields


def test_archetype_authentication():
    """Authentication archetype requirements."""
    rule = DummyRule(name="Brute Force Login Spike", event_type="Active-Directory-Logon")
    pv = DummyPromptVersion(status="APPROVED")
    contract = EvidenceContractService.get_contract_for_rule(rule, pv)

    assert contract.detection_archetype == "AUTHENTICATION"
    fields = [req.field for req in contract.required_evidence]
    assert "user.name" in fields
    assert "endpoint.hostname" in fields


def test_archetype_generic_fallback():
    """Fallback to generic archetype for unmapped rule types."""
    rule = DummyRule(name="Generic Anomaly", event_type="Custom-Sensor")
    pv = DummyPromptVersion(status="APPROVED")
    contract = EvidenceContractService.get_contract_for_rule(rule, pv)

    assert contract.detection_archetype == "GENERIC"
    fields = [req.field for req in contract.required_evidence]
    assert "security.event_type" in fields


def test_contract_contradiction_rules():
    """Contract includes defined contradiction rules."""
    rule = DummyRule(name="C2 Beaconing", event_type="Network-Traffic")
    pv = DummyPromptVersion(status="APPROVED")
    contract = EvidenceContractService.get_contract_for_rule(rule, pv)

    assert len(contract.contradiction_rules) > 0
    rule_ids = [c["rule_id"] for c in contract.contradiction_rules]
    assert "EXTERNAL_C2_ON_LOOPBACK" in rule_ids
