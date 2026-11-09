from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SemanticsDefinitionStatus(str, Enum):
    VERIFIED = "VERIFIED"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"
    CONFLICTING = "CONFLICTING"


class SourceProvenance(str, Enum):
    AUTHORITATIVE_SIEM_DEFINITION = "AUTHORITATIVE_SIEM_DEFINITION"
    VENDOR_RULE_FILE = "VENDOR_RULE_FILE"
    AUTO_SYNCED_FROM_INCIDENT = "AUTO_SYNCED_FROM_INCIDENT"
    HEURISTIC_PARSER = "HEURISTIC_PARSER"


class ArchetypeId(str, Enum):
    NETWORK_EXFILTRATION = "NETWORK_EXFILTRATION"
    NETWORK_SCAN = "NETWORK_SCAN"
    MALWARE_EXECUTION = "MALWARE_EXECUTION"
    ENDPOINT_MALWARE = "MALWARE_EXECUTION"
    PROCESS_EXECUTION = "PROCESS_EXECUTION"
    NETWORK_CONNECTION = "NETWORK_CONNECTION"
    FILE_MALWARE = "FILE_MALWARE"
    AUTHENTICATION = "AUTHENTICATION"
    CREDENTIAL_ACCESS = "CREDENTIAL_ACCESS"
    BRUTE_FORCE = "BRUTE_FORCE"
    LATERAL_MOVEMENT = "LATERAL_MOVEMENT"
    DNS_TUNNELING = "DNS_TUNNELING"
    WEB_ATTACK = "WEB_ATTACK"
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"
    CLOUD_DATA_ACCESS = "CLOUD_DATA_ACCESS"
    POLICY_VIOLATION = "POLICY_VIOLATION"
    ENDPOINT_DEFENSE_EVASION = "ENDPOINT_DEFENSE_EVASION"
    GENERIC = "GENERIC"
    UNKNOWN = "UNKNOWN"


DetectionArchetype = ArchetypeId


class DetectionSemantics(BaseModel):
    """
    Structured detection semantics model extracted from SIEM rule logic and metadata.
    Distinguishes authoritative conditions from observed incident telemetry.
    """
    rule_identifier: str = Field(..., description="SIEM Rule Identifier, e.g. PH_RULE_LARGE_OUTBOUND_XFER")
    rule_name: str = Field(..., description="Human-readable rule name")
    siem_vendor: str = Field("FortiSIEM", description="Originating SIEM/XDR vendor")
    data_source: str = Field("", description="Primary data source, e.g. MSSP-Primary, FortiGate, EDR")
    tenant_scope: Optional[str] = Field(None, description="Multi-tenant / customer scope")
    event_category: str = Field("", description="Security category, e.g. Exfiltration, Execution")
    sub_category: Optional[str] = Field(None, description="Sub-category or incident tag")
    detection_objective: str = Field("", description="Core detection purpose or behavioral intent")
    
    # Authoritative Detection Logic
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Parsed boolean expressions / conditions")
    boolean_operators: List[str] = Field(default_factory=list, description="Logical operators, e.g. AND, OR, NOT")
    threshold: Optional[float] = Field(None, description="Authoritative detection threshold (None if unverified)")
    threshold_unit: Optional[str] = Field(None, description="Unit for threshold, e.g. bytes, count, requests")
    aggregation_window: Optional[str] = Field(None, description="Time/aggregation window, e.g. 5m, 1h (None if unverified)")
    grouping_keys: List[str] = Field(default_factory=list, description="Aggregation grouping keys, e.g. [srcIp, destIp]")
    suppression_conditions: List[str] = Field(default_factory=list, description="Exclusion or suppression logic")

    # Semantics Context
    source_semantics: Dict[str, Any] = Field(default_factory=dict, description="Expected source entity semantics")
    destination_semantics: Dict[str, Any] = Field(default_factory=dict, description="Expected destination semantics")
    relevant_fields: List[str] = Field(default_factory=list, description="Canonical fields relevant to detection")
    observed_fields: List[str] = Field(default_factory=list, description="Fields observed in sample incidents only")
    
    # MITRE ATT&CK Metadata
    attck_tactics: List[str] = Field(default_factory=list, description="MITRE ATT&CK tactics")
    attck_techniques: List[str] = Field(default_factory=list, description="MITRE ATT&CK techniques")

    # Classification & Provenance
    primary_behavior: str = Field(ArchetypeId.UNKNOWN.value, description="Candidate detection archetype")
    definition_status: SemanticsDefinitionStatus = Field(SemanticsDefinitionStatus.UNKNOWN, description="Definition verification status")
    source_provenance: SourceProvenance = Field(SourceProvenance.HEURISTIC_PARSER, description="Provenance of semantics")
    provenance_details: Dict[str, str] = Field(default_factory=dict, description="Detailed field-level provenance")
    review_required: bool = Field(True, description="Whether human review is required before approval")
    missing_requirements: List[str] = Field(default_factory=list, description="List of unverified / missing rule conditions")
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class ArchetypeDefinition(BaseModel):
    """Specification of a versioned detection archetype in the registry."""
    archetype_id: ArchetypeId
    name: str
    version: str = "v2.0.0"
    detection_purpose: str
    core_telemetry_categories: List[str]
    mandatory_core_fields: List[str]
    conditional_fields: List[str]
    optional_enrichment_fields: List[str]
    unsupported_fields: List[str]
    tp_indicator_candidates: List[str]
    fp_indicator_candidates: List[str]
    abstention_requirements: List[str]
    escalation_considerations: List[str]
    analyst_question_templates: List[str]
    unsupported_assumptions: List[str]
    contradiction_rules: List[Dict[str, Any]] = Field(default_factory=list)


class ArchetypeClassificationResult(BaseModel):
    """Result of classifying a rule into behavioral archetypes."""
    rule_identifier: str
    primary_archetype: ArchetypeId
    secondary_archetype: Optional[ArchetypeId] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    classification_reason: str
    matched_features: List[str] = Field(default_factory=list)
    traceability_log: List[str] = Field(default_factory=list)
    registry_version: str = "v2.0.0"
    classified_at: datetime = Field(default_factory=datetime.utcnow)
