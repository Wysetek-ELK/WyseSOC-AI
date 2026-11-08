import logging
from typing import Optional, List, Dict, Any
from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement

logger = logging.getLogger(__name__)


class EvidenceContractService:
    """
    P2-REQ-02: Evidence Contract Service.
    Derives and validates machine-verifiable evidence contracts tied to approved
    rule policies in Agent Intelligence Studio.
    """

    @classmethod
    def get_contract_for_rule(
        cls,
        rule: Optional[Rule],
        prompt_version: Optional[PromptVersion],
    ) -> RuleEvidenceContract:
        """
        Builds or resolves the machine-verifiable evidence contract for a rule.
        Strictly checks that the contract status matches the policy approval state.
        If prompt_version is not APPROVED, the contract is marked UNVERIFIED.
        """
        rule_id = getattr(rule, "id", None) or getattr(rule, "rule_id", "UNKNOWN_RULE")
        rule_name = str(getattr(rule, "name", "") or "").lower()
        event_type = str(getattr(rule, "event_type", "") or "").lower()

        # 1. Determine Status: Only APPROVED PromptVersions yield APPROVED contracts
        contract_status = "UNVERIFIED"
        version_num = 1
        pv_id = None
        if prompt_version:
            pv_id = prompt_version.id
            version_num = prompt_version.version_number
            if prompt_version.status == "APPROVED":
                contract_status = "APPROVED"
            else:
                contract_status = "UNVERIFIED"

        # 2. Identify Detection Archetype
        combo = f"{rule_name} {event_type}"
        if any(term in combo for term in ("process", "crowdstrike", "powershell", "cmd", "script", "execution", "lolbin", "wscript")):
            archetype = "PROCESS_EXECUTION"
            reqs = [
                EvidenceFieldRequirement(
                    field="process.command_line",
                    evidence_type="PROCESS_EXECUTION",
                    required_for_tp=True,
                    required_for_fp=False,
                    critical=True,
                    description="Full executing command line arguments",
                ),
                EvidenceFieldRequirement(
                    field="process.name",
                    evidence_type="PROCESS_EXECUTION",
                    required_for_tp=True,
                    required_for_fp=True,
                    critical=False,
                    description="Target executing binary or script name",
                ),
                EvidenceFieldRequirement(
                    field="user.name",
                    evidence_type="USER_CONTEXT",
                    required_for_tp=True,
                    required_for_fp=False,
                    critical=False,
                    description="User or service account context executing the command",
                ),
                EvidenceFieldRequirement(
                    field="process.parent_name",
                    evidence_type="PROCESS_LINEAGE",
                    required_for_tp=False,
                    required_for_fp=False,
                    critical=False,
                    description="Parent process name",
                ),
            ]
            contradiction_rules = [
                {
                    "rule_id": "NO_PROCESS_LINEAGE_ON_MALICIOUS_EXECUTION",
                    "rule_type": "NO_PROCESS_LINEAGE_ON_MALICIOUS_EXECUTION",
                    "description": "Claiming unauthorized process spawn when no command line or parent process exists",
                }
            ]
        elif any(term in combo for term in ("network", "web", "traffic", "c2", "beacon", "dns", "http", "outbound", "port")):
            archetype = "NETWORK_CONNECTION"
            reqs = [
                EvidenceFieldRequirement(
                    field="network.destination_ip",
                    evidence_type="NETWORK_CONNECTION",
                    required_for_tp=True,
                    required_for_fp=True,
                    critical=True,
                    description="Remote destination IP address or host",
                ),
                EvidenceFieldRequirement(
                    field="network.source_ip",
                    evidence_type="NETWORK_CONNECTION",
                    required_for_tp=True,
                    required_for_fp=True,
                    critical=False,
                    description="Source IP initiating the connection",
                ),
                EvidenceFieldRequirement(
                    field="network.destination_port",
                    evidence_type="NETWORK_CONNECTION",
                    required_for_tp=True,
                    required_for_fp=False,
                    critical=False,
                    description="Target destination port",
                ),
            ]
            contradiction_rules = [
                {
                    "rule_id": "EXTERNAL_C2_ON_LOOPBACK",
                    "rule_type": "EXTERNAL_C2_ON_LOOPBACK",
                    "description": "Claiming external C2 beaconing when destination is loopback or internal RFC1918 IP",
                }
            ]
        elif any(term in combo for term in ("malware", "virus", "trojan", "hash", "sha256", "file", "download")):
            archetype = "FILE_MALWARE"
            reqs = [
                EvidenceFieldRequirement(
                    field="file.hash_sha256",
                    evidence_type="FILE_HASH",
                    required_for_tp=True,
                    required_for_fp=False,
                    critical=True,
                    description="Cryptographic SHA-256 hash of the suspicious file",
                ),
                EvidenceFieldRequirement(
                    field="endpoint.hostname",
                    evidence_type="ENDPOINT_TELEMETRY",
                    required_for_tp=True,
                    required_for_fp=True,
                    critical=False,
                    description="Host where the file was written or executed",
                ),
            ]
            contradiction_rules = [
                {
                    "rule_type": "MALWARE_EXECUTION_WITHOUT_FILE_HASH",
                    "description": "Claiming known malware signature match when file hash is completely absent",
                }
            ]
        elif any(term in combo for term in ("auth", "login", "brute", "password", "credential", "kerberos", "ldap")):
            archetype = "AUTHENTICATION"
            reqs = [
                EvidenceFieldRequirement(
                    field="user.name",
                    evidence_type="USER_CONTEXT",
                    required_for_tp=True,
                    required_for_fp=True,
                    critical=True,
                    description="Target account targeted for authentication",
                ),
                EvidenceFieldRequirement(
                    field="network.source_ip",
                    evidence_type="NETWORK_CONNECTION",
                    required_for_tp=True,
                    required_for_fp=False,
                    critical=False,
                    description="Source IP originating the authentication attempt",
                ),
                EvidenceFieldRequirement(
                    field="endpoint.hostname",
                    evidence_type="ENDPOINT_TELEMETRY",
                    required_for_tp=True,
                    required_for_fp=False,
                    critical=False,
                    description="Target system or domain controller receiving authentication",
                ),
            ]
            contradiction_rules = []
        else:
            archetype = "GENERIC"
            reqs = [
                EvidenceFieldRequirement(
                    field="security.event_type",
                    evidence_type="SECURITY_EVENT",
                    required_for_tp=True,
                    required_for_fp=True,
                    critical=True,
                    description="Normalized SIEM event type identifier",
                ),
            ]
            contradiction_rules = []

        # 3. Extract any specific criteria from prompt version text if present
        tp_crits = []
        fp_crits = []
        if prompt_version:
            tp_ind = getattr(prompt_version, "tp_indicators", None)
            if tp_ind:
                tp_crits = [line.strip("- *") for line in tp_ind.splitlines() if line.strip("- *")]
            fp_ind = getattr(prompt_version, "fp_indicators", None)
            if fp_ind:
                fp_crits = [line.strip("- *") for line in fp_ind.splitlines() if line.strip("- *")]

        contract_id = f"EC-{rule_id}-V{version_num}"
        return RuleEvidenceContract(
            contract_id=contract_id,
            rule_id=str(rule_id),
            prompt_version_id=pv_id,
            version_number=version_num,
            status=contract_status,
            detection_archetype=archetype,
            required_evidence=reqs,
            tp_criteria=tp_crits[:6],
            fp_criteria=fp_crits[:6],
            contradiction_rules=contradiction_rules,
            on_critical_missing_evidence="REQUIRES_ATTENTION",
        )
