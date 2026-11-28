"""
AIS 3.2 — Verdict Semantics Engine.

Separates detection validity from malicious intent so operational monitoring,
configuration monitoring, firewall/IPS perimeter blocks, and security threats
are evaluated according to the approved detection objective and rule contract.

NOTE: Formal TP/FP mappings remain marked PROVISIONAL until explicit SOC/business
owner approval is recorded.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.schemas.verdict_semantics import (
    ActivityCharacterization,
    AuthorizationStatus,
    DetectionValidity,
    OperationalImpact,
    SemanticMappingRule,
    SemanticPolicyApprovalState,
    VerdictSemanticsEvaluation,
)


# Canonical archetype -> semantic policy mapping registry
# Marked PROVISIONAL until formal SOC/business owner sign-off in governance workflow.
DEFAULT_SEMANTIC_MAPPINGS: Dict[str, SemanticMappingRule] = {
    "OPERATIONAL_MONITORING": SemanticMappingRule(
        rule_key="SEM_OPERATIONAL_MONITORING",
        archetype="OPERATIONAL_MONITORING",
        detection_objective_type="OPERATIONAL_HEALTH",
        tp_semantics=(
            "Confirmed log collection outage, collector delay, device silence, or telemetry EPS drop "
            "matching the rule condition (represents an operational health True Positive, not a cyberattack)."
        ),
        fp_semantics=(
            "Telemetry confirms logs/heartbeats resumed normally, planned maintenance window explains silence, "
            "or rule triggered on transient noise/decommissioned host."
        ),
        inconclusive_semantics="Reporting device/collector state or outage telemetry is missing or contradictory.",
        operational_is_tp_when_confirmed=True,
        requires_authorization_for_fp=False,
        blocked_traffic_can_still_be_tp=False,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "CONFIGURATION_MONITORING": SemanticMappingRule(
        rule_key="SEM_CONFIGURATION_MONITORING",
        archetype="CONFIGURATION_MONITORING",
        detection_objective_type="CONFIGURATION_AUDIT",
        tp_semantics=(
            "Confirmed configuration modification on firewall/network/security appliance that is "
            "verified unauthorized or unapproved (lacks verified change ticket/approved config context)."
        ),
        fp_semantics=(
            "Configuration change is corroborated by an approved change ticket, maintenance window, "
            "or verified authorized administrative baseline."
        ),
        inconclusive_semantics="Change event lacks target object/user context or authorization state cannot be verified.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=False,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "NETWORK_RECONNAISSANCE": SemanticMappingRule(
        rule_key="SEM_NETWORK_RECONNAISSANCE",
        archetype="NETWORK_RECONNAISSANCE",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics=(
            "Confirmed horizontal host sweep or multi-port TCP scan from an unapproved/untrusted source "
            "targeting internal or monitored assets without verified scanner authorization."
        ),
        fp_semantics=(
            "Source IP is verified in organizational context as an authorized vulnerability scanner, "
            "IT discovery/monitoring system, or approved penetration test within valid change/maintenance scope."
        ),
        inconclusive_semantics="Scan target/source telemetry is missing or scanner authorization cannot be established.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=True,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "FIREWALL_SECURITY": SemanticMappingRule(
        rule_key="SEM_FIREWALL_SECURITY",
        archetype="FIREWALL_SECURITY",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics=(
            "Confirmed sustained unauthorized probing, excessive perimeter denies from untrusted/external sources, "
            "or active policy-violating traffic matching rule criteria. Firewall deny/block does NOT automatically make a scan/probe FP."
        ),
        fp_semantics=(
            "Traffic originates from verified authorized infrastructure, approved external service, or benign "
            "enterprise web/application traffic with verified organizational/policy context."
        ),
        inconclusive_semantics="Source/destination, firewall action, or authorization context is insufficient.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=True,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "IPS_IDS": SemanticMappingRule(
        rule_key="SEM_IPS_IDS",
        archetype="IPS_IDS",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics=(
            "Confirmed exploit payload, SQLi/XSS/RCE signature match, or intrusion attempt targeting exposed services "
            "(even if blocked/dropped by IPS when rule detects attempted attack)."
        ),
        fp_semantics=(
            "Verified signature false alarm on benign application input, authorized security assessment/pen-test, "
            "or approved test traffic with verified context."
        ),
        inconclusive_semantics="Payload/URL/signature detail is absent or target/authorization context cannot be verified.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=True,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "THREAT_INTELLIGENCE": SemanticMappingRule(
        rule_key="SEM_THREAT_INTELLIGENCE",
        archetype="THREAT_INTELLIGENCE",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics=(
            "Confirmed communication with a threat-intelligence IOC (malicious IP/domain/hash), especially permitted "
            "or bidirectional traffic without verified sinkhole/authorized security tool context."
        ),
        fp_semantics=(
            "Traffic is verified benign (e.g., authorized threat-intel lookup, sinkhole, or verified stale/reclaimed IP "
            "with clean organizational destination context)."
        ),
        inconclusive_semantics="Matched IOC, traffic direction, or firewall action is missing or ambiguous.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=True,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "DNS_SECURITY": SemanticMappingRule(
        rule_key="SEM_DNS_SECURITY",
        archetype="DNS_SECURITY",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics=(
            "Confirmed anomalous/excessive DNS queries, DGA/tunneling indicators, or unauthorized DNS resolver usage "
            "from non-resolver hosts without verified infrastructure authorization."
        ),
        fp_semantics=(
            "Source is a verified corporate DNS forwarder/resolver, authorized AD domain controller, or approved "
            "monitoring/CDN resolver in organizational context."
        ),
        inconclusive_semantics="Query details, source host role, or DNS destination context is missing.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=True,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "DATA_TRANSFER": SemanticMappingRule(
        rule_key="SEM_DATA_TRANSFER",
        archetype="DATA_TRANSFER",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics=(
            "Confirmed large or anomalous outbound transfer to an unapproved external destination, personal cloud, "
            "or foreign endpoint without verified business authorization."
        ),
        fp_semantics=(
            "Transfer matches verified authorized backup, corporate cloud destination, CDN, or approved data transfer "
            "in organizational context."
        ),
        inconclusive_semantics="Transfer direction, byte volume, or destination authorization cannot be established.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=False,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "AUTHENTICATION_SECURITY": SemanticMappingRule(
        rule_key="SEM_AUTHENTICATION_SECURITY",
        archetype="AUTHENTICATION_SECURITY",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics=(
            "Confirmed credential stuffing, brute force, account lockout storm, cleartext credential exposure, "
            "or anomalous impossible-travel/foreign logon without verified user travel/VPN authorization."
        ),
        fp_semantics=(
            "Verified authorized user/VPN travel, expired service account under documented rotation, or approved "
            "security testing with verified identity/change context."
        ),
        inconclusive_semantics="User identity, source IP, or authentication outcome is missing.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=True,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "ENDPOINT_SECURITY": SemanticMappingRule(
        rule_key="SEM_ENDPOINT_SECURITY",
        archetype="ENDPOINT_SECURITY",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics=(
            "Confirmed malicious process execution, unauthorized remote admin tool, credential access, "
            "tampering, or known malware file hash without verified authorization."
        ),
        fp_semantics=(
            "Verified approved administrative software from trusted path/signature, or authorized IT maintenance "
            "backed by verified change/tool context."
        ),
        inconclusive_semantics="Process/file/command-line or authorization evidence is insufficient.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=True,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
    "GENERIC_UNKNOWN": SemanticMappingRule(
        rule_key="SEM_GENERIC_UNKNOWN",
        archetype="GENERIC_UNKNOWN",
        detection_objective_type="SECURITY_THREAT",
        tp_semantics="Confirmed rule condition match with verified malicious or unauthorized activity.",
        fp_semantics="Verified authorized benign activity or confirmed detection error.",
        inconclusive_semantics="Rule semantics or telemetry are insufficient for safe classification.",
        operational_is_tp_when_confirmed=False,
        requires_authorization_for_fp=True,
        blocked_traffic_can_still_be_tp=False,
        approval_state=SemanticPolicyApprovalState.PROVISIONAL,
    ),
}


# Canonicalize granular/legacy archetype names to the 11 universal archetypes
CANONICAL_ARCHETYPE_MAP: Dict[str, str] = {
    "NETWORK_RECONNAISSANCE": "NETWORK_RECONNAISSANCE",
    "NETWORK_SCAN": "NETWORK_RECONNAISSANCE",
    "FIREWALL_SECURITY": "FIREWALL_SECURITY",
    "POLICY_VIOLATION": "FIREWALL_SECURITY",
    "NETWORK_CONNECTION": "FIREWALL_SECURITY",
    "ENDPOINT_SECURITY": "ENDPOINT_SECURITY",
    "MALWARE_EXECUTION": "ENDPOINT_SECURITY",
    "ENDPOINT_MALWARE": "ENDPOINT_SECURITY",
    "PROCESS_EXECUTION": "ENDPOINT_SECURITY",
    "FILE_MALWARE": "ENDPOINT_SECURITY",
    "CREDENTIAL_ACCESS": "ENDPOINT_SECURITY",
    "PRIVILEGE_ESCALATION": "ENDPOINT_SECURITY",
    "ENDPOINT_DEFENSE_EVASION": "ENDPOINT_SECURITY",
    "LATERAL_MOVEMENT": "ENDPOINT_SECURITY",
    "AUTHENTICATION_SECURITY": "AUTHENTICATION_SECURITY",
    "AUTHENTICATION": "AUTHENTICATION_SECURITY",
    "BRUTE_FORCE": "AUTHENTICATION_SECURITY",
    "DNS_SECURITY": "DNS_SECURITY",
    "DNS_TUNNELING": "DNS_SECURITY",
    "DATA_TRANSFER": "DATA_TRANSFER",
    "NETWORK_EXFILTRATION": "DATA_TRANSFER",
    "CLOUD_DATA_ACCESS": "DATA_TRANSFER",
    "IPS_IDS": "IPS_IDS",
    "WEB_ATTACK": "IPS_IDS",
    "CONFIGURATION_MONITORING": "CONFIGURATION_MONITORING",
    "OPERATIONAL_MONITORING": "OPERATIONAL_MONITORING",
    "THREAT_INTELLIGENCE": "THREAT_INTELLIGENCE",
    "GENERIC_UNKNOWN": "GENERIC_UNKNOWN",
    "GENERIC": "GENERIC_UNKNOWN",
    "UNKNOWN": "GENERIC_UNKNOWN",
}


class VerdictSemanticsEngine:
    """Evaluates and reconciles multi-dimensional verdict semantics with external TP/FP/REQUIRES_ATTENTION."""

    @classmethod
    def canonical_archetype(cls, archetype: Optional[str]) -> str:
        raw = str(archetype or "GENERIC_UNKNOWN").upper().strip()
        return CANONICAL_ARCHETYPE_MAP.get(raw, "GENERIC_UNKNOWN")

    @classmethod
    def get_mapping_rule(cls, archetype: Optional[str]) -> SemanticMappingRule:
        canon = cls.canonical_archetype(archetype)
        return DEFAULT_SEMANTIC_MAPPINGS.get(canon, DEFAULT_SEMANTIC_MAPPINGS["GENERIC_UNKNOWN"])

    @classmethod
    def list_semantic_mappings(cls) -> List[Dict[str, Any]]:
        return [m.model_dump(mode="json") for m in DEFAULT_SEMANTIC_MAPPINGS.values()]

    @classmethod
    def evaluate_semantics(
        cls,
        *,
        archetype: str,
        proposed_verdict: str,
        detection_validity: Optional[str] = None,
        activity_characterization: Optional[str] = None,
        authorization_status: Optional[str] = None,
        operational_impact: Optional[str] = None,
        mapping_override: Optional[SemanticMappingRule] = None,
    ) -> VerdictSemanticsEvaluation:
        """
        Validates internal semantic dimensions against the proposed external verdict
        according to the archetype's semantic mapping rule.
        """
        mapping = mapping_override or cls.get_mapping_rule(archetype)
        canon_arch = cls.canonical_archetype(archetype)
        prop = str(proposed_verdict or "REQUIRES_ATTENTION").upper().strip()
        if prop in ("INCONCLUSIVE", "INSUFFICIENT_EVIDENCE", "REQUIRES_ANALYST_ATTENTION"):
            prop = "REQUIRES_ATTENTION"

        def _enum_val(enum_cls, raw_val, default_val):
            try:
                return enum_cls(str(raw_val or "").upper().strip())
            except ValueError:
                return default_val

        dv = _enum_val(DetectionValidity, detection_validity, DetectionValidity.UNKNOWN)
        ac = _enum_val(ActivityCharacterization, activity_characterization, ActivityCharacterization.UNKNOWN)
        au = _enum_val(AuthorizationStatus, authorization_status, AuthorizationStatus.UNKNOWN)
        oi = _enum_val(OperationalImpact, operational_impact, OperationalImpact.UNKNOWN)

        issues: List[str] = []

        # Consistency checks between internal dimensions and proposed verdict
        if prop == "FALSE_POSITIVE":
            if ac == ActivityCharacterization.MALICIOUS:
                issues.append("Proposed FALSE_POSITIVE contradicts activity_characterization=MALICIOUS.")
            if mapping.archetype == "OPERATIONAL_MONITORING" and dv == DetectionValidity.CONFIRMED and ac == ActivityCharacterization.OPERATIONAL_ISSUE and au != AuthorizationStatus.VERIFIED_AUTHORIZED:
                issues.append(
                    "Confirmed operational monitoring outage/delay without verified maintenance authorization "
                    "maps to TRUE_POSITIVE (operational detection), not FALSE_POSITIVE."
                )
        elif prop == "TRUE_POSITIVE":
            if dv == DetectionValidity.NOT_CONFIRMED:
                issues.append("Proposed TRUE_POSITIVE contradicts detection_validity=NOT_CONFIRMED.")
            if ac == ActivityCharacterization.BENIGN_AUTHORIZED and au == AuthorizationStatus.VERIFIED_AUTHORIZED:
                issues.append("Proposed TRUE_POSITIVE contradicts BENIGN_AUTHORIZED + VERIFIED_AUTHORIZED.")
            if ac == ActivityCharacterization.OPERATIONAL_ISSUE and not mapping.operational_is_tp_when_confirmed:
                issues.append(
                    f"Archetype {canon_arch} does not map purely benign OPERATIONAL_ISSUE to TRUE_POSITIVE."
                )

        # Derive expected verdict from semantic dimensions when dimensions are explicitly populated
        derived = prop
        rationale_parts: List[str] = [f"Archetype={canon_arch} ({mapping.detection_objective_type})"]

        if dv == DetectionValidity.CONFIRMED:
            if ac == ActivityCharacterization.OPERATIONAL_ISSUE and mapping.operational_is_tp_when_confirmed:
                if au == AuthorizationStatus.VERIFIED_AUTHORIZED:
                    derived = "FALSE_POSITIVE"
                    rationale_parts.append("Confirmed operational alert inside verified maintenance/exception -> FALSE_POSITIVE")
                else:
                    derived = "TRUE_POSITIVE"
                    rationale_parts.append("Confirmed operational health outage/delay -> TRUE_POSITIVE (PROVISIONAL)")
            elif ac == ActivityCharacterization.MALICIOUS:
                derived = "TRUE_POSITIVE"
                rationale_parts.append("Confirmed malicious activity -> TRUE_POSITIVE")
            elif ac == ActivityCharacterization.BENIGN_AUTHORIZED and au == AuthorizationStatus.VERIFIED_AUTHORIZED:
                derived = "FALSE_POSITIVE"
                rationale_parts.append("Verified authorized benign activity -> FALSE_POSITIVE")
            elif mapping.archetype == "CONFIGURATION_MONITORING":
                if au == AuthorizationStatus.VERIFIED_AUTHORIZED:
                    derived = "FALSE_POSITIVE"
                    rationale_parts.append("Authorized configuration change -> FALSE_POSITIVE")
                elif au == AuthorizationStatus.VERIFIED_UNAUTHORIZED:
                    derived = "TRUE_POSITIVE"
                    rationale_parts.append("Unauthorized configuration change -> TRUE_POSITIVE")

        return VerdictSemanticsEvaluation(
            detection_validity=dv,
            activity_characterization=ac,
            authorization_status=au,
            operational_impact=oi,
            derived_verdict=derived,
            proposed_verdict=prop,
            is_semantically_consistent=(len(issues) == 0),
            consistency_issues=issues,
            mapping_rationale="; ".join(rationale_parts),
            approval_state=mapping.approval_state,
        )
