"""
AIS 3.2 — Centralized Rule Intelligence Engine & FortiSIEM Rule Definition Interpreter.

Converts FortiSIEM rule definitions into typed, versioned, hash-verified DynamicRuleContracts
without requiring custom standalone prompts per rule or per incident.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ais32_intelligence import RuleContractRecord
from app.models.prompt import PromptVersion
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.schemas.dynamic_rule_contract import (
    ContractApprovalState,
    DetectionVerificationLevel,
    DynamicRuleContract,
    RuleConditionClause,
)
from app.schemas.evidence_contract import EvidenceFieldRequirement, RuleEvidenceContract
from app.schemas.rule_intelligence import ArchetypeId, DetectionSemantics
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_intelligence_service import RuleDefinitionBuilder
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.verdict_semantics_engine import VerdictSemanticsEngine
from app.utils.datetime_utils import utc_now


# Approved organizational context types relevant per canonical archetype
ARCHETYPE_ORG_CONTEXT_MAP: Dict[str, List[str]] = {
    "NETWORK_RECONNAISSANCE": [
        "AUTHORIZED_SCANNER",
        "SECURITY_ASSESSMENT_SYSTEM",
        "INTERNAL_IP_RANGE",
        "ASSET_INVENTORY",
        "NETWORK_ZONE",
        "MAINTENANCE_WINDOW",
        "CUSTOMER_EXCEPTION",
    ],
    "FIREWALL_SECURITY": [
        "INTERNAL_IP_RANGE",
        "NETWORK_ZONE",
        "ASSET_INVENTORY",
        "CRITICAL_ASSET",
        "APPROVED_EXTERNAL_DESTINATION",
        "CUSTOMER_EXCEPTION",
        "MAINTENANCE_WINDOW",
    ],
    "ENDPOINT_SECURITY": [
        "ASSET_INVENTORY",
        "CRITICAL_ASSET",
        "SERVER_CLASSIFICATION",
        "APPROVED_ADMIN_TOOL",
        "APPROVED_SOFTWARE",
        "SERVICE_ACCOUNT",
        "MAINTENANCE_WINDOW",
        "CUSTOMER_EXCEPTION",
    ],
    "AUTHENTICATION_SECURITY": [
        "IDENTITY_INFO",
        "SERVICE_ACCOUNT",
        "INTERNAL_IP_RANGE",
        "NETWORK_ZONE",
        "APPROVED_EXTERNAL_DESTINATION",
        "MAINTENANCE_WINDOW",
        "CUSTOMER_EXCEPTION",
    ],
    "DNS_SECURITY": [
        "ASSET_INVENTORY",
        "SERVER_CLASSIFICATION",
        "INTERNAL_IP_RANGE",
        "APPROVED_EXTERNAL_DESTINATION",
        "NETWORK_ZONE",
        "CUSTOMER_EXCEPTION",
    ],
    "DATA_TRANSFER": [
        "AUTHORIZED_DATA_TRANSFER",
        "APPROVED_EXTERNAL_DESTINATION",
        "ASSET_INVENTORY",
        "CRITICAL_ASSET",
        "SERVICE_ACCOUNT",
        "MAINTENANCE_WINDOW",
        "CUSTOMER_EXCEPTION",
    ],
    "IPS_IDS": [
        "AUTHORIZED_SCANNER",
        "SECURITY_ASSESSMENT_SYSTEM",
        "ASSET_INVENTORY",
        "CRITICAL_ASSET",
        "CUSTOMER_EXCEPTION",
        "MAINTENANCE_WINDOW",
    ],
    "CONFIGURATION_MONITORING": [
        "APPROVED_CONFIG_CHANGE",
        "MAINTENANCE_WINDOW",
        "IDENTITY_INFO",
        "SERVICE_ACCOUNT",
        "ASSET_INVENTORY",
        "CRITICAL_ASSET",
        "CUSTOMER_EXCEPTION",
    ],
    "OPERATIONAL_MONITORING": [
        "ASSET_INVENTORY",
        "DEVICE_OWNERSHIP",
        "MAINTENANCE_WINDOW",
        "CUSTOMER_EXCEPTION",
    ],
    "THREAT_INTELLIGENCE": [
        "SECURITY_ASSESSMENT_SYSTEM",
        "APPROVED_EXTERNAL_DESTINATION",
        "ASSET_INVENTORY",
        "CRITICAL_ASSET",
        "CUSTOMER_EXCEPTION",
    ],
    "GENERIC_UNKNOWN": [
        "ASSET_INVENTORY",
        "MAINTENANCE_WINDOW",
        "CUSTOMER_EXCEPTION",
    ],
}


# Rule-family specific TP/FP/Inconclusive refinements (generic, zero benchmark leakage)
_ARCHETYPE_RULE_GUIDANCE: Dict[str, Dict[str, Any]] = {
    "OPERATIONAL_MONITORING": {
        "tp_criteria": [
            "SIEM telemetry confirms collector delay, device log silence, or EPS drop outside verified planned maintenance.",
            "Affected collector or reporting device identity is observed in incident telemetry.",
        ],
        "fp_criteria": [
            "Verified planned maintenance window or decommissioned device record in organizational context explains log absence.",
            "Telemetry explicitly shows log receipt recovered immediately without outage.",
        ],
        "inconclusive_criteria": [
            "Affected device/collector identity and delay/outage metrics are missing or contradictory.",
        ],
        "authorization_requirements": [
            "Do NOT require malicious attacker indicators or endpoint process logs for operational monitoring rules.",
            "Planned maintenance FP requires verified MAINTENANCE_WINDOW or CUSTOMER_EXCEPTION organizational context.",
        ],
        "severity_interpretation": "Operational telemetry availability alert; TRUE_POSITIVE indicates a genuine monitoring/logging health condition requiring SOC/infra follow-up, not a cyberattack.",
    },
    "CONFIGURATION_MONITORING": {
        "tp_criteria": [
            "Confirmed modification of firewall, router, identity, or security control configuration without verified change approval.",
            "Sensitive policy/external-resource/admin configuration change observed in audit telemetry.",
        ],
        "fp_criteria": [
            "Verified APPROVED_CONFIG_CHANGE, active MAINTENANCE_WINDOW, or authoritative change ticket matches device, actor, and window.",
        ],
        "inconclusive_criteria": [
            "Target configuration object or actor is missing, or authorization status cannot be verified when required by policy.",
        ],
        "authorization_requirements": [
            "Admin username or internal source IP alone does NOT establish configuration authorization.",
            "Requires verified APPROVED_CONFIG_CHANGE, MAINTENANCE_WINDOW, or authoritative ITSM ticket in evidence/context.",
        ],
        "severity_interpretation": "Configuration integrity audit alert; unauthorized or unverified changes on security controls require immediate validation.",
    },
    "FIREWALL_SECURITY": {
        "tp_criteria": [
            "Sustained or high-volume denied/probing connections from untrusted external or anomalous sources matching rule thresholds.",
            "Prohibited outbound/inbound access or bogon/policy-violating traffic without verified exception.",
        ],
        "fp_criteria": [
            "Source/destination matches verified organizational asset, authorized scanner, approved external destination, or documented exception.",
            "Confirmed benign business SaaS/web resource traffic with clean context and no probing escalation.",
        ],
        "inconclusive_criteria": [
            "Source IP, destination IP, firewall action, or rule-triggered counts are missing or contradictory.",
        ],
        "authorization_requirements": [
            "Firewall DENY/BLOCK action confirms perimeter enforcement, NOT necessarily a False Positive for attack/probing rules.",
            "Do NOT require endpoint process execution or file hashes for perimeter firewall alerts.",
        ],
        "severity_interpretation": "Perimeter enforcement / traffic anomaly alert; evaluate external source risk, target exposure, volume, and policy intent.",
    },
    "NETWORK_RECONNAISSANCE": {
        "tp_criteria": [
            "High-rate or high-breadth sequential port/host scanning attempts from an unverified source without scanner authorization.",
            "Scanning targeting sensitive internal subnets or perimeter infrastructure with unanswered/RST/denied probes.",
        ],
        "fp_criteria": [
            "Source IP is verified in organizational context as AUTHORIZED_SCANNER or SECURITY_ASSESSMENT_SYSTEM or active MAINTENANCE_WINDOW.",
            "Confirmed legitimate bidirectional application/CDN/load-balancer health probe with verified asset context.",
        ],
        "inconclusive_criteria": [
            "Source IP, target port/host scope, or scan connection metrics are absent or conflicting.",
        ],
        "authorization_requirements": [
            "Internal RFC1918 source IP is NOT automatically an authorized scanner.",
            "Scanner FP requires verified AUTHORIZED_SCANNER, SECURITY_ASSESSMENT_SYSTEM, or change ticket context.",
        ],
        "severity_interpretation": "Network reconnaissance alert; distinguish verified authorized vulnerability scanners from unapproved probing.",
    },
    "IPS_IDS": {
        "tp_criteria": [
            "Confirmed exploit signature or malicious payload (SQLi, path traversal, RCE, buffer overflow) in IPS/WAF telemetry.",
        ],
        "fp_criteria": [
            "Source is a verified AUTHORIZED_SCANNER / SECURITY_ASSESSMENT_SYSTEM during active window, or verified benign payload false match.",
        ],
        "inconclusive_criteria": [
            "IPS signature, target IP/URL, or payload context is unavailable.",
        ],
        "authorization_requirements": [
            "IPS block/drop does NOT invalidate an attempted intrusion True Positive when the rule detects exploit attempts.",
        ],
        "severity_interpretation": "Intrusion prevention signature alert; verify payload authenticity, action taken (blocked vs allowed), and target criticality.",
    },
    "THREAT_INTELLIGENCE": {
        "tp_criteria": [
            "Confirmed network connection involving a threat-intelligence IOC (MISP/malware IP/domain), particularly permitted/established traffic.",
        ],
        "fp_criteria": [
            "Verified sinkhole, security assessment system, or approved external destination with documented exception.",
        ],
        "inconclusive_criteria": [
            "Matched IOC address/domain or traffic action/direction is missing.",
        ],
        "authorization_requirements": [
            "Permitted inbound or outbound communication with a threat-intel IP requires explicit verified exception to mark FP.",
        ],
        "severity_interpretation": "Threat intelligence indicator match; permitted sessions to/from IOC infrastructure are high-priority investigations.",
    },
    "DNS_SECURITY": {
        "tp_criteria": [
            "Non-resolver host generating excessive DNS queries, unauthorized external DNS requests, or high-entropy/DGA query anomalies.",
        ],
        "fp_criteria": [
            "Source host is a verified corporate DNS resolver/domain controller or destination is an approved external DNS forwarder.",
        ],
        "inconclusive_criteria": [
            "Source host identity or DNS destination/query context is missing.",
        ],
        "authorization_requirements": [
            "Verify whether source/destination belongs to corporate DNS infrastructure before classifying as benign.",
        ],
        "severity_interpretation": "DNS telemetry anomaly; distinguish authoritative DNS forwarders from anomalous client exfiltration/tunneling.",
    },
    "DATA_TRANSFER": {
        "tp_criteria": [
            "Confirmed high-volume outbound data transfer to unapproved external/foreign destination without verified business authorization.",
        ],
        "fp_criteria": [
            "Transfer matches verified AUTHORIZED_DATA_TRANSFER, APPROVED_EXTERNAL_DESTINATION, or scheduled corporate backup.",
        ],
        "inconclusive_criteria": [
            "Traffic direction, byte volume, or destination authorization cannot be verified.",
        ],
        "authorization_requirements": [
            "Large byte count alone does not prove exfiltration, and internal/partner name alone does not prove authorization without verified context.",
        ],
        "severity_interpretation": "Outbound data transfer anomaly; verify directionality, volume, destination reputation, and business transfer authorization.",
    },
    "AUTHENTICATION_SECURITY": {
        "tp_criteria": [
            "Repeated failed logins, account lockout storm, cleartext password transmission, or impossible-travel VPN logon without authorization.",
        ],
        "fp_criteria": [
            "Verified authorized user travel/VPN exception, approved service account rotation, or verified benign administrative test.",
        ],
        "inconclusive_criteria": [
            "User identity, source IP, or authentication outcome is missing.",
        ],
        "authorization_requirements": [
            "Do NOT assume a logon or cleartext service event is benign without verified identity/exception context.",
        ],
        "severity_interpretation": "Identity and authentication security alert; verify account privilege, source IP/geo, and whether success followed failures.",
    },
    "ENDPOINT_SECURITY": {
        "tp_criteria": [
            "Confirmed malicious binary, unauthorized remote admin tool (e.g. UltraViewer/AnyDesk), LOLBin abuse, or credential dumping without IT authorization.",
        ],
        "fp_criteria": [
            "Verified approved enterprise management/security agent from trusted vendor path/signature, or verified change ticket.",
        ],
        "inconclusive_criteria": [
            "Executing process/command line/file hash or authorization context is missing or contradictory.",
        ],
        "authorization_requirements": [
            "Executable name or digital signature alone does NOT prove authorization; check path, command line, and approved tool/change context.",
        ],
        "severity_interpretation": "Endpoint security execution alert; verify full process lineage, path classification, and administrative authorization.",
    },
    "GENERIC_UNKNOWN": {
        "tp_criteria": [
            "Rule conditions match verified malicious or unauthorized activity supported by concrete telemetry.",
        ],
        "fp_criteria": [
            "Verified authorized activity or documented exception in organizational context.",
        ],
        "inconclusive_criteria": [
            "Rule semantics or mandatory telemetry are insufficient or unsupported for confident automated classification.",
        ],
        "authorization_requirements": [
            "Require explicit verified authorization context before classifying as FALSE_POSITIVE.",
        ],
        "severity_interpretation": "Unclassified/generic detection rule; handle conservatively and escalate ambiguous evidence.",
    },
}


class RuleIntelligenceEngine:
    """
    Centralized Rule Intelligence Engine (AIS 3.2).
    Builds versioned, auditable DynamicRuleContracts from FortiSIEM rule definitions,
    DetectionArchetypeRegistry, RuleDefinitionBuilder, and persisted overrides.
    """

    ENGINE_VERSION = "3.2.0"

    @classmethod
    def interpret_rule_definition(
        cls,
        rule: Optional[Rule],
        canonical_records: Optional[List[Any]] = None,
        incident_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Interprets FortiSIEM detection logic: filters, AND/OR/NOT, nested blocks,
        COUNT / DISTINCT counts, aggregation, correlation, thresholds, time windows,
        group-by fields, exceptions, and verification level (SIEM_REPORTED vs RECONSTRUCTED).
        Never invents missing events or thresholds.
        """
        base_spec = RuleDefinitionBuilder.build_complete_rule_spec(
            rule_obj=rule,
            canonical_records=canonical_records,
            incident_payload=incident_payload,
        )
        pattern_text = str(base_spec.get("pattern_logic") or "").strip()
        raw_text = str(base_spec.get("raw_rule_text") or "").strip()
        combined_logic = f"{pattern_text}\n{raw_text}".strip()

        # Logical operators & negation & nested conditions
        logical_ops: List[str] = []
        if re.search(r"\bAND\b", combined_logic, re.IGNORECASE):
            logical_ops.append("AND")
        if re.search(r"\bOR\b", combined_logic, re.IGNORECASE):
            logical_ops.append("OR")
        if re.search(r"\bNOT\b|!=", combined_logic, re.IGNORECASE):
            logical_ops.append("NOT")
        has_nested = "(" in pattern_text and ")" in pattern_text

        # Distinct count / aggregation / correlation extraction
        distinct_matches = re.findall(r"COUNT\s*\(\s*DISTINCT\s+([^)]+)\)", combined_logic, re.IGNORECASE)
        count_matches = re.findall(r"COUNT\s*\(\s*([^)]+)\)\s*(>=|>|=|<=|<)\s*(\d+)", combined_logic, re.IGNORECASE)
        aggregation_logic_parts: List[str] = []
        if distinct_matches:
            aggregation_logic_parts.append("DISTINCT(" + ", ".join(m.strip() for m in distinct_matches) + ")")
        for fld, op, num in count_matches:
            aggregation_logic_parts.append(f"COUNT({fld.strip()}) {op} {num}")

        # Correlation requirements (e.g., FOLLOWED BY, SubPattern, Group By)
        corr_reqs: List[str] = []
        if re.search(r"\bFOLLOWED\s+BY\b|\bSubPattern\b", combined_logic, re.IGNORECASE):
            corr_reqs.append("Multi-stage event correlation sequence specified in SIEM rule")
        if base_spec.get("group_by"):
            corr_reqs.append(f"Grouped by: {', '.join(base_spec['group_by'])}")
        if base_spec.get("window"):
            corr_reqs.append(f"Evaluation window: {base_spec['window']}")

        # Structured condition clauses
        clause_objs: List[RuleConditionClause] = []
        eval_by_attr = {
            (ev.get("attribute"), ev.get("operator"), ev.get("expected")): ev
            for ev in (base_spec.get("predicate_evaluations") or [])
        }
        for c in base_spec.get("conditions") or []:
            key = (c.get("attribute"), c.get("operator"), c.get("expected"))
            ev = eval_by_attr.get(key, {})
            op_u = str(c.get("operator") or "").upper()
            clause_objs.append(
                RuleConditionClause(
                    attribute=str(c.get("attribute") or ""),
                    operator=op_u,
                    expected=str(c.get("expected") or ""),
                    logical_op="OR" if "OR" in logical_ops and "AND" not in logical_ops else "AND",
                    negated=("NOT" in op_u or "!=" in op_u),
                    nested_group="NESTED" if has_nested else None,
                    evaluation_status=str(ev.get("status") or "UNKNOWN"),
                    observed_values=list(ev.get("observed_values") or []),
                )
            )

        # Determine detection verification level without reconstructing missing events
        has_siem_agg_summary = bool(
            incident_payload
            and (
                incident_payload.get("raw_payload")
                or (isinstance(incident_payload.get("evidence_intelligence"), dict)
                    and incident_payload["evidence_intelligence"].get("scan_metrics"))
            )
        )
        events_count = len((incident_payload or {}).get("events") or [])
        statuses = [c.evaluation_status for c in clause_objs]
        if clause_objs and all(s == "MATCHED" for s in statuses) and events_count > 0:
            verification_level = DetectionVerificationLevel.INDEPENDENTLY_RECONSTRUCTED
        elif any(s == "MATCHED" for s in statuses) or (events_count > 0 and base_spec.get("rule_definition_completeness") == "COMPLETE"):
            verification_level = DetectionVerificationLevel.PARTIALLY_VERIFIED
        elif rule is not None and (events_count > 0 or has_siem_agg_summary or canonical_records):
            verification_level = DetectionVerificationLevel.SIEM_REPORTED_DETECTION
        else:
            verification_level = DetectionVerificationLevel.UNVERIFIABLE

        return {
            **base_spec,
            "logical_operators": logical_ops,
            "has_nested_conditions": has_nested,
            "aggregation_logic": "; ".join(aggregation_logic_parts) if aggregation_logic_parts else "SIEM event/correlation trigger",
            "correlation_requirements": corr_reqs,
            "structured_clauses": clause_objs,
            "detection_verification_level": verification_level.value,
        }

    @classmethod
    def build_dynamic_contract(
        cls,
        *,
        rule: Optional[Rule],
        semantics: Optional[DetectionSemantics] = None,
        prompt_version: Optional[PromptVersion] = None,
        persisted_record: Optional[RuleContractRecord] = None,
        canonical_records: Optional[List[Any]] = None,
        incident_payload: Optional[Dict[str, Any]] = None,
    ) -> DynamicRuleContract:
        """
        Builds a typed, hashed DynamicRuleContract for any FortiSIEM rule.
        Applies validated rule-specific overrides if persisted in DB.
        """
        rule_ident = str(
            getattr(rule, "rule_id", None)
            or getattr(rule, "event_type", None)
            or getattr(rule, "id", None)
            or "UNKNOWN_RULE"
        )
        rule_name = str(getattr(rule, "name", None) or rule_ident)
        if semantics is None and rule is not None:
            semantics = RuleIntelligenceAnalyzer.analyze_rule(rule)

        if semantics is not None:
            classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
        else:
            from app.schemas.rule_intelligence import ArchetypeClassificationResult
            classification = ArchetypeClassificationResult(
                rule_identifier=rule_ident,
                primary_archetype=ArchetypeId.UNKNOWN,
                canonical_archetype="GENERIC_UNKNOWN",
                confidence_score=0.3,
                classification_reason="Rule metadata absent; mapped safely to GENERIC_UNKNOWN.",
                mapping_rationale="Rule metadata absent; mapped safely to GENERIC_UNKNOWN.",
            )

        canon_arch = VerdictSemanticsEngine.canonical_archetype(
            classification.canonical_archetype or classification.primary_archetype.value
        )
        arch_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
        interp = cls.interpret_rule_definition(rule, canonical_records=canonical_records, incident_payload=incident_payload)

        # Vendor resolution
        data_src = str(getattr(rule, "data_source", "") or "")
        vendor = "FortiSIEM"
        combo_v = f"{rule_ident} {rule_name} {data_src}".lower()
        if "crowdstrike" in combo_v or "cs_" in combo_v:
            vendor = "CrowdStrike"
        elif "prisma" in combo_v:
            vendor = "Prisma SASE"
        elif "fgt" in combo_v or "fortigate" in combo_v:
            vendor = "FortiGate"

        # Mandatory & optional fields from archetype + mapped contract
        ev_contract = (
            EvidenceRequirementMapper.map_evidence_contract(
                rule=rule,
                semantics=semantics,
                archetype_def=arch_def,
                prompt_version=prompt_version,
            )
            if rule is not None and semantics is not None
            else None
        )
        mandatory_fields = (
            [r.field for r in ev_contract.required_evidence if r.requirement_level == "CORE"]
            if ev_contract
            else list(arch_def.mandatory_core_fields)
        )
        optional_fields = (
            [r.field for r in ev_contract.required_evidence if r.requirement_level in ("CONDITIONAL", "OPTIONAL")]
            if ev_contract
            else list(arch_def.conditional_fields) + list(arch_def.optional_enrichment_fields)
        )

        guidance = _ARCHETYPE_RULE_GUIDANCE.get(canon_arch, _ARCHETYPE_RULE_GUIDANCE["GENERIC_UNKNOWN"])
        tp_crits = list(guidance["tp_criteria"])
        fp_crits = list(guidance["fp_criteria"])
        inc_crits = list(guidance["inconclusive_criteria"])

        # Incorporate non-empty rule-specific PromptVersion indicators if approved
        if prompt_version and getattr(prompt_version, "status", "") == "APPROVED":
            pv_tp = [l.strip("- *") for l in str(getattr(prompt_version, "tp_indicators", "") or "").splitlines() if l.strip("- *")]
            pv_fp = [l.strip("- *") for l in str(getattr(prompt_version, "fp_indicators", "") or "").splitlines() if l.strip("- *")]
            if pv_tp:
                tp_crits = pv_tp[:6]
            if pv_fp:
                fp_crits = pv_fp[:6]

        # Approval state & version
        approval_state = ContractApprovalState.PROVISIONAL
        contract_ver = 1
        reviewer = None
        overrides: Dict[str, Any] = {}
        if persisted_record is not None:
            contract_ver = int(persisted_record.contract_version or 1)
            reviewer = persisted_record.reviewer
            overrides = dict(persisted_record.overrides_json or {})
            try:
                approval_state = ContractApprovalState(str(persisted_record.approval_state or "PROVISIONAL").upper())
            except ValueError:
                approval_state = ContractApprovalState.PROVISIONAL
        elif prompt_version and getattr(prompt_version, "status", "") == "APPROVED":
            contract_ver = int(getattr(prompt_version, "version_number", 1) or 1)

        # Apply validated rule-specific overrides (safe keys only)
        if overrides.get("primary_archetype"):
            canon_arch = VerdictSemanticsEngine.canonical_archetype(str(overrides["primary_archetype"]))
        if isinstance(overrides.get("tp_criteria"), list) and overrides["tp_criteria"]:
            tp_crits = [str(x) for x in overrides["tp_criteria"][:8]]
        if isinstance(overrides.get("fp_criteria"), list) and overrides["fp_criteria"]:
            fp_crits = [str(x) for x in overrides["fp_criteria"][:8]]
        if isinstance(overrides.get("known_legitimate_exceptions"), list):
            exceptions = [str(x) for x in overrides["known_legitimate_exceptions"][:8]]
        else:
            exceptions = list(interp.get("exclusions") or [])

        rule_def_hash = hashlib.sha256(
            json.dumps(
                {
                    "rule_id": rule_ident,
                    "name": rule_name,
                    "pattern_logic": interp.get("pattern_logic") or "",
                    "raw_rule_text": interp.get("raw_rule_text") or "",
                    "parsed_metadata": interp.get("parsed_metadata") or {},
                },
                sort_keys=True,
                default=str,
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()

        thresholds_dict: Dict[str, Any] = {}
        if semantics and semantics.threshold is not None:
            thresholds_dict = {
                "value": semantics.threshold,
                "unit": semantics.threshold_unit or "count",
                "source": "AUTHORITATIVE_SIEM_DEFINITION",
            }
        elif interp.get("threshold"):
            thresholds_dict = {
                "raw": interp.get("threshold"),
                "source": "PARSED_RULE_TEXT",
            }
        else:
            thresholds_dict = {
                "value": None,
                "source": "UNVERIFIED_IN_INCIDENT_API",
            }

        is_supported = canon_arch != "GENERIC_UNKNOWN"
        unsupported_reason = (
            None
            if is_supported
            else f"Rule '{rule_ident}' lacks specialized archetype classification; handled under safe GENERIC_UNKNOWN fallback."
        )

        limitations: List[str] = []
        if interp.get("rule_definition_completeness") != "COMPLETE":
            limitations.append(
                "Authoritative FortiSIEM rule XML/pattern block is not fully published over incident API; "
                "do not invent thresholds or missing rule conditions."
            )
        if interp.get("detection_verification_level") == DetectionVerificationLevel.SIEM_REPORTED_DETECTION.value:
            limitations.append(
                "Detection count/aggregation is SIEM-reported; individual sub-events may be aggregated or sampled."
            )

        contract = DynamicRuleContract(
            contract_id=f"DRC-{rule_ident}-V{contract_ver}",
            contract_version=contract_ver,
            fortisiem_rule_id=rule_ident,
            rule_name=rule_name,
            rule_definition_hash=rule_def_hash,
            rule_archetype=canon_arch,
            secondary_archetype=(
                VerdictSemanticsEngine.canonical_archetype(classification.secondary_archetype.value)
                if classification.secondary_archetype
                else None
            ),
            mapping_rationale=classification.mapping_rationale or classification.classification_reason,
            detection_objective=(
                (semantics.detection_objective if semantics and semantics.detection_objective else "")
                or arch_def.detection_purpose
            ),
            detection_category=str(
                (semantics.event_category if semantics else "")
                or getattr(rule, "detection_tech", "")
                or canon_arch
            ),
            source_vendor=vendor,
            rule_conditions=interp.get("structured_clauses") or [],
            aggregation_logic=str(interp.get("aggregation_logic") or ""),
            thresholds=thresholds_dict,
            time_window=(semantics.aggregation_window if semantics else None) or interp.get("window"),
            group_by_fields=(semantics.grouping_keys if semantics and semantics.grouping_keys else []) or list(interp.get("group_by") or []),
            correlation_requirements=list(interp.get("correlation_requirements") or []),
            mandatory_evidence_fields=mandatory_fields,
            optional_evidence_fields=optional_fields,
            tp_criteria=tp_crits,
            fp_criteria=fp_crits,
            inconclusive_criteria=inc_crits,
            authorization_requirements=list(guidance["authorization_requirements"]),
            known_legitimate_exceptions=exceptions,
            evidence_completeness_requirements={
                "min_core_completeness": 0.5,
                "verification_level": interp.get("detection_verification_level"),
                "allow_siem_reported_aggregation": True,
                "require_endpoint_process_telemetry": canon_arch == "ENDPOINT_SECURITY",
            },
            approved_organizational_context_types=list(
                ARCHETYPE_ORG_CONTEXT_MAP.get(canon_arch, ARCHETYPE_ORG_CONTEXT_MAP["GENERIC_UNKNOWN"])
            ),
            claim_validation_requirements=[
                "Every factual claim must reference an observed canonical EV-* record or verified organizational context.",
                "Never assert missing evidence fields as observed facts or claim threshold breaches unless threshold is verified.",
            ],
            severity_interpretation=str(guidance["severity_interpretation"]),
            detection_limitations=limitations,
            approval_state=approval_state,
            reviewer=reviewer,
            policy_provenance=(
                f"APPROVED_PROMPT_V{prompt_version.version_number}"
                if prompt_version and getattr(prompt_version, "status", "") == "APPROVED"
                else "AIS32_UNIVERSAL_RULE_INTELLIGENCE"
            ),
            is_supported_rule=is_supported,
            unsupported_reason=unsupported_reason,
            rule_overrides=overrides,
        )
        contract.contract_hash = contract.compute_contract_hash()
        return contract

    @classmethod
    def to_legacy_evidence_contract(
        cls,
        dynamic_contract: DynamicRuleContract,
        *,
        force_approved_for_eval: bool = False,
    ) -> RuleEvidenceContract:
        """Converts DynamicRuleContract to RuleEvidenceContract for seamless pipeline & preflight compatibility."""
        reqs: List[EvidenceFieldRequirement] = []
        for mf in dynamic_contract.mandatory_evidence_fields:
            reqs.append(
                EvidenceFieldRequirement(
                    field=mf,
                    evidence_type=EvidenceRequirementMapper._get_evidence_type_for_field(mf),
                    required_for_tp=True,
                    required_for_fp=(mf in ("network.source_ip", "network.destination_ip", "user.name", "endpoint.hostname", "security.event_type")),
                    critical=(mf in ("security.event_type",)),
                    requirement_level="CORE",
                    description=f"Core requirement for {dynamic_contract.rule_archetype}",
                )
            )
        for of in dynamic_contract.optional_evidence_fields:
            if of not in dynamic_contract.mandatory_evidence_fields:
                reqs.append(
                    EvidenceFieldRequirement(
                        field=of,
                        evidence_type=EvidenceRequirementMapper._get_evidence_type_for_field(of),
                        required_for_tp=False,
                        required_for_fp=False,
                        critical=False,
                        requirement_level="CONDITIONAL",
                        description=f"Contextual/conditional field for {dynamic_contract.rule_archetype}",
                    )
                )

        status_str = "APPROVED" if (
            force_approved_for_eval or dynamic_contract.approval_state == ContractApprovalState.APPROVED
        ) else "UNVERIFIED"

        return RuleEvidenceContract(
            contract_id=dynamic_contract.contract_id,
            rule_id=dynamic_contract.fortisiem_rule_id,
            version_number=dynamic_contract.contract_version,
            status=status_str,
            detection_archetype=dynamic_contract.rule_archetype,
            required_evidence=reqs,
            tp_criteria=dynamic_contract.tp_criteria,
            fp_criteria=dynamic_contract.fp_criteria,
            contradiction_rules=[],
            on_critical_missing_evidence="REQUIRES_ATTENTION",
        )

    @classmethod
    async def get_or_build_contract_for_rule(
        cls,
        db: AsyncSession,
        rule: Rule,
        prompt_version: Optional[PromptVersion] = None,
        canonical_records: Optional[List[Any]] = None,
        incident_payload: Optional[Dict[str, Any]] = None,
    ) -> Tuple[DynamicRuleContract, Optional[RuleContractRecord]]:
        """Loads latest active RuleContractRecord from PostgreSQL if present, else synthesizes contract."""
        rec = (
            await db.execute(
                select(RuleContractRecord)
                .where(RuleContractRecord.rule_db_id == rule.id, RuleContractRecord.is_active.is_(True))
                .order_by(desc(RuleContractRecord.contract_version))
                .limit(1)
            )
        ).scalar_one_or_none()

        snap = (
            await db.execute(select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id == rule.id))
        ).scalar_one_or_none()
        from app.services.policy_governance import reconstruct_semantics_from_snapshot
        semantics = reconstruct_semantics_from_snapshot(snap) if snap else RuleIntelligenceAnalyzer.analyze_rule(rule)

        contract = cls.build_dynamic_contract(
            rule=rule,
            semantics=semantics,
            prompt_version=prompt_version,
            persisted_record=rec,
            canonical_records=canonical_records,
            incident_payload=incident_payload,
        )
        return contract, rec

    @classmethod
    async def save_contract_version(
        cls,
        db: AsyncSession,
        *,
        rule: Rule,
        overrides: Optional[Dict[str, Any]] = None,
        created_by: str = "admin",
        approve: bool = False,
        reviewer: Optional[str] = None,
    ) -> Tuple[DynamicRuleContract, RuleContractRecord]:
        """Persists a new versioned RuleContractRecord in PostgreSQL (validating safety before commit)."""
        existing = (
            await db.execute(
                select(RuleContractRecord)
                .where(RuleContractRecord.rule_db_id == rule.id)
                .order_by(desc(RuleContractRecord.contract_version))
            )
        ).scalars().all()
        next_ver = (max(r.contract_version for r in existing) + 1) if existing else 1
        for prev in existing:
            prev.is_active = False
            db.add(prev)

        # Validate contract schema + safety overrides BEFORE persisting
        temp_rec = RuleContractRecord(
            contract_id=f"DRC-{rule.rule_id}-V{next_ver}",
            contract_version=next_ver,
            rule_db_id=rule.id,
            fortisiem_rule_id=rule.rule_id,
            rule_name=rule.name,
            primary_archetype="GENERIC_UNKNOWN",
            approval_state="APPROVED" if approve else "PROVISIONAL",
            overrides_json=overrides or {},
            reviewer=reviewer if approve else None,
            approved_at=utc_now() if approve else None,
            created_by=created_by,
        )
        contract = cls.build_dynamic_contract(rule=rule, persisted_record=temp_rec)

        temp_rec.contract_id = contract.contract_id
        temp_rec.rule_definition_hash = contract.rule_definition_hash
        temp_rec.primary_archetype = contract.rule_archetype
        temp_rec.secondary_archetype = contract.secondary_archetype
        temp_rec.mapping_rationale = contract.mapping_rationale
        temp_rec.contract_hash = contract.contract_hash
        temp_rec.contract_json = contract.model_dump(mode="json")
        db.add(temp_rec)
        await db.commit()
        await db.refresh(temp_rec)
        return contract, temp_rec
