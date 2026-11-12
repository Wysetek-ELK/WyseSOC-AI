import hashlib
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field


class CanonicalEvidenceRecord(BaseModel):
    """
    Structured, traceable representation of a single unit of incident telemetry.
    Strictly isolated from ground truth and model-generated interpretations.
    """
    evidence_id: str = Field(..., description="Deterministic, unique evidence identifier suitable for audit and replay")
    incident_id: str = Field(..., description="Associated incident ID")
    source_system: str = Field("FortiSIEM", description="Original SIEM or EDR telemetry provider")
    source_event_id: Optional[str] = Field(None, description="Source event ID if extracted from a specific raw event")
    source_field: str = Field(..., description="Canonical source field path (e.g. process.command_line)")
    observed_value: Any = Field(..., description="Original observed value extracted from telemetry")
    observed_at: Optional[str] = Field(None, description="Observation or event timestamp in ISO-8601 format")
    evidence_type: str = Field(..., description="Category: PROCESS_EXECUTION, PROCESS_LINEAGE, USER_CONTEXT, NETWORK_CONNECTION, DNS_QUERY, FILE_HASH, ENDPOINT_TELEMETRY, SECURITY_EVENT")
    availability: str = Field("AVAILABLE", description="AVAILABLE or UNAVAILABLE")
    provenance_status: str = Field("SOURCE_RECORDED", description="Provenance status of the evidence")
    integrity_digest: str = Field(..., description="SHA-256 cryptographic digest of source field and value")
    raw_field_name: Optional[str] = Field(None, description="Original source field or attribute name before normalization")
    transformation: Optional[str] = Field("DIRECT", description="Transformation applied: DIRECT, ALIASED, KEY_VALUE_EXTRACTED")
    validation_status: Optional[str] = Field("PRESENT_VALID", description="Validation status: PRESENT_VALID, PRESENT_INVALID, NOT_IN_SOURCE, etc.")

    @classmethod
    def generate_digest(cls, source_field: str, observed_value: Any) -> str:
        """Computes a deterministic SHA-256 integrity digest for the evidence record."""
        raw_token = f"{source_field.strip().lower()}:{str(observed_value).strip()}"
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def generate_id(cls, incident_id: str, source_event_id: Optional[str], source_field: str) -> str:
        """Constructs a deterministic evidence identifier."""
        evt_key = (source_event_id or "TOP").replace(" ", "_")
        clean_field = source_field.replace(".", "_").replace(" ", "_").lower()
        return f"EV-{incident_id}-{evt_key}-{clean_field}"


class EvidenceNormalizationResult(BaseModel):
    """Aggregate result from evidence normalization service."""
    incident_id: str
    total_evidence_count: int
    available_evidence_count: int
    records: List[CanonicalEvidenceRecord]
    evidence_by_type: Dict[str, List[CanonicalEvidenceRecord]] = Field(default_factory=dict)
    evidence_by_field: Dict[str, List[CanonicalEvidenceRecord]] = Field(default_factory=dict)
    unmapped_fields: List[Dict[str, Any]] = Field(default_factory=list, description="Raw fields present in telemetry that had no canonical mapping")
    missing_fields: List[str] = Field(default_factory=list, description="Contract fields missing from source telemetry")
    field_validation_status: Dict[str, str] = Field(default_factory=dict, description="Per-field validation status mapping")

