import logging
from typing import Optional, List, Dict, Any, Set
from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.schemas.rule_intelligence import (
    DetectionSemantics,
    ArchetypeId,
    ArchetypeDefinition,
    SemanticsDefinitionStatus,
)
from app.services.detection_archetype_registry import DetectionArchetypeRegistry

logger = logging.getLogger("ai_verdict.evidence_mapper")

# Standard normalized fields known to canonical evidence normalizer
CANONICAL_FIELD_CATALOG: Set[str] = {
    "network.source_ip",
    "network.destination_ip",
    "network.destination_port",
    "network.protocol",
    "network.direction",
    "network.bytes_out",
    "network.bytes_in",
    "network.sent_bytes",
    "network.received_bytes",
    "network.destination_domain",
    "process.name",
    "process.command_line",
    "process.parent_name",
    "process.parent_command_line",
    "process.working_directory",
    "file.hash_sha256",
    "file.path",
    "file.name",
    "file.signature_status",
    "endpoint.hostname",
    "user.name",
    "user.domain",
    "auth.result",
    "auth.failure_reason",
    "auth.failure_count",
    "dns.query_name",
    "dns.record_type",
    "dns.response_code",
    "http.url",
    "http.method",
    "http.status_code",
    "http.user_agent",
    "cloud.user_identity",
    "cloud.service_name",
    "cloud.event_name",
    "cloud.bucket_name",
    "security.event_type",
    "event.timestamp",
    "dlp.findings",
    "sentBytes64",
    "scan.rate_per_second",
    "scan.connection_count",
    "network.destination_ip_list",
    "network.tcp_flags",
    "webCategory",
    "security.action",
    "security.alert_title",
    "endpoint.ip",
    "endpoint.device_id",
    "network.service",
    "network.source_port",
}


class EvidenceRequirementMapper:
    """
    REQ-03: Detection-Aware Evidence Requirement Mapper.
    Maps Detection Semantics + Archetype Definition + Telemetry Schema Availability
    into a candidate machine-verifiable RuleEvidenceContract.
    
    Guarantees:
      - Network rules DO NOT universally require file hashes or process lineage.
      - Large Outbound Transfer strictly requires source, destination, direction, byte count, timestamp.
      - Unavailable or unmapped telemetry fields are explicitly identified.
      - Preserves 100% compatibility with Phase 2 EvidencePreflightValidator and IndependentVerdictValidator.
    """
    MAPPER_VERSION = "v2.0.0"

    @classmethod
    def map_evidence_contract(
        cls,
        rule: Optional[Rule],
        semantics: DetectionSemantics,
        archetype_def: ArchetypeDefinition,
        prompt_version: Optional[PromptVersion] = None,
        available_telemetry_fields: Optional[List[str]] = None,
    ) -> RuleEvidenceContract:
        """
        Synthesizes a candidate machine-verifiable Evidence Contract matching rule semantics.
        """
        rule_id = str(getattr(rule, "id", None) or getattr(rule, "rule_id", None) or semantics.rule_identifier)
        version_num = getattr(prompt_version, "version_number", 1) if prompt_version else 1
        pv_id = getattr(prompt_version, "id", None) if prompt_version else None

        # Determine contract status: strictly UNVERIFIED unless prompt_version is APPROVED
        pv_status = getattr(prompt_version, "status", None) if prompt_version else None
        contract_status = "APPROVED" if pv_status == "APPROVED" else "UNVERIFIED"

        available_set = set(available_telemetry_fields or CANONICAL_FIELD_CATALOG)

        reqs: List[EvidenceFieldRequirement] = []

        # 1. Map Mandatory Core Requirements from Archetype
        for field in archetype_def.mandatory_core_fields:
            is_avail = field in available_set or field in semantics.relevant_fields
            req_lvl = "CORE" if is_avail else "UNAVAILABLE"
            
            req_tp = True
            req_fp = (field in ("network.destination_ip", "network.source_ip", "user.name", "endpoint.hostname", "process.name", "security.event_type"))
            is_crit = field in ("network.destination_ip", "process.command_line", "file.hash_sha256", "user.name", "security.event_type", "network.bytes_out") or (
                archetype_def.archetype_id == ArchetypeId.NETWORK_SCAN and field in ("network.source_ip", "network.destination_port", "security.event_type", "event.timestamp")
            )

            desc = cls._get_field_description(field, archetype_def.archetype_id)
            reqs.append(
                EvidenceFieldRequirement(
                    field=field,
                    evidence_type=cls._get_evidence_type_for_field(field),
                    required_for_tp=req_tp,
                    required_for_fp=req_fp,
                    critical=is_crit,
                    requirement_level=req_lvl,
                    description=desc,
                )
            )

        # 2. Map Conditional Requirements
        for field in archetype_def.conditional_fields:
            is_avail = field in available_set or field in semantics.relevant_fields
            req_lvl = "CONDITIONAL" if is_avail else "UNAVAILABLE"
            reqs.append(
                EvidenceFieldRequirement(
                    field=field,
                    evidence_type=cls._get_evidence_type_for_field(field),
                    required_for_tp=False,
                    required_for_fp=False,
                    critical=False,
                    requirement_level=req_lvl,
                    description=cls._get_field_description(field, archetype_def.archetype_id),
                )
            )

        # 3. Add Authoritative Rule-Specific Requirements
        if semantics.threshold is not None:
            threshold_field = "detection.threshold"
            reqs.append(
                EvidenceFieldRequirement(
                    field=threshold_field,
                    evidence_type="RULE_THRESHOLD",
                    required_for_tp=True,
                    required_for_fp=False,
                    critical=True,
                    requirement_level="CORE",
                    description=f"Authoritative rule threshold ({semantics.threshold} {semantics.threshold_unit or ''})",
                )
            )
        elif semantics.definition_status == SemanticsDefinitionStatus.INCOMPLETE:
            # Mark unverified threshold requirement
            reqs.append(
                EvidenceFieldRequirement(
                    field="detection.authoritative_threshold",
                    evidence_type="RULE_THRESHOLD",
                    required_for_tp=True,
                    required_for_fp=False,
                    critical=False,
                    requirement_level="UNVERIFIED",
                    description="Authoritative SIEM detection threshold (currently unverified / incomplete in SIEM rule)",
                )
            )

        # 4. Handle Observed Telemetry Attributes (e.g. sentBytes64)
        for of in semantics.observed_fields:
            if of not in [r.field for r in reqs]:
                reqs.append(
                    EvidenceFieldRequirement(
                        field=of,
                        evidence_type="OBSERVED_TELEMETRY",
                        required_for_tp=False,
                        required_for_fp=False,
                        critical=False,
                        requirement_level="OPTIONAL",
                        description=f"Observed telemetry attribute from incident data ({of})",
                    )
                )

        # 5. Extract TP/FP criteria and Contradiction Rules
        tp_crits = list(archetype_def.tp_indicator_candidates)
        fp_crits = list(archetype_def.fp_indicator_candidates)

        if prompt_version:
            tp_ind = getattr(prompt_version, "tp_indicators", None)
            if tp_ind:
                tp_crits = [line.strip("- *") for line in str(tp_ind).splitlines() if line.strip("- *")]
            fp_ind = getattr(prompt_version, "fp_indicators", None)
            if fp_ind:
                fp_crits = [line.strip("- *") for line in str(fp_ind).splitlines() if line.strip("- *")]

        contradictions = list(archetype_def.contradiction_rules)

        contract_id = f"EC-{rule_id}-V{version_num}"

        return RuleEvidenceContract(
            contract_id=contract_id,
            rule_id=str(rule_id),
            prompt_version_id=str(pv_id) if pv_id else None,
            version_number=version_num,
            status=contract_status,
            detection_archetype=archetype_def.archetype_id.value,
            required_evidence=reqs,
            tp_criteria=tp_crits[:8],
            fp_criteria=fp_crits[:8],
            contradiction_rules=contradictions,
            on_critical_missing_evidence="REQUIRES_ATTENTION",
        )

    @staticmethod
    def _get_evidence_type_for_field(field: str) -> str:
        if field.startswith("scan."):
            return "SCAN_METRIC"
        elif field.startswith("network.") or field == "sentBytes64":
            return "NETWORK_CONNECTION"
        elif field.startswith("process."):
            return "PROCESS_EXECUTION"
        elif field.startswith("file."):
            return "FILE_HASH" if "hash" in field else "FILE_SYSTEM"
        elif field.startswith("user."):
            return "USER_CONTEXT"
        elif field.startswith("endpoint."):
            return "ENDPOINT_TELEMETRY"
        elif field.startswith("auth."):
            return "AUTHENTICATION"
        elif field.startswith("dns."):
            return "DNS_QUERY"
        elif field.startswith("http."):
            return "HTTP_TRAFFIC"
        elif field.startswith("cloud."):
            return "CLOUD_AUDIT"
        elif field.startswith("dlp."):
            return "DLP_FINDING"
        return "SECURITY_EVENT"

    @staticmethod
    def _get_field_description(field: str, archetype: ArchetypeId) -> str:
        desc_map = {
            "network.source_ip": "Source IP address initiating connection, scan, or data transfer",
            "network.destination_ip": "Target destination IP address receiving connection",
            "network.destination_ip_list": "List of targeted destination IP addresses in network scan",
            "network.direction": "Verified connection direction (outbound vs inbound)",
            "network.bytes_out": "Verified volume of outbound transferred bytes",
            "network.destination_port": "Target destination port (e.g. fixed scanned port)",
            "network.protocol": "Network transport protocol (e.g. TCP, UDP)",
            "network.tcp_flags": "Observed TCP control flags (SYN, RST, ACK)",
            "scan.rate_per_second": "Connection attempt rate per second during scan window",
            "scan.connection_count": "Total count of connection attempts observed in aggregation window",
            "event.timestamp": "Canonical event occurrence timestamp",
            "user.name": "User context or service account performing action",
            "process.name": "Target executing binary or script name",
            "process.command_line": "Full executing command line arguments",
            "process.parent_name": "Parent process name",
            "file.hash_sha256": "Cryptographic SHA-256 hash of suspicious file",
            "endpoint.hostname": "Target host or endpoint system context",
            "dns.query_name": "Full queried DNS domain name",
            "auth.result": "Authentication outcome (SUCCESS or FAILURE)",
            "security.event_type": "Normalized SIEM event type identifier",
        }
        return desc_map.get(field, f"Telemetry field requirement: {field}")
