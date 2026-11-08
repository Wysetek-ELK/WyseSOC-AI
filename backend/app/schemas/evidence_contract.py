from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, computed_field


class EvidenceFieldRequirement(BaseModel):
    """Specific field requirement in an evidence contract."""
    field: str = Field(..., description="Canonical field path, e.g. process.command_line")
    evidence_type: str = Field(..., description="Expected evidence category")
    required_for_tp: bool = Field(True, description="Whether this field is mandatory to accept TRUE_POSITIVE")
    required_for_fp: bool = Field(False, description="Whether this field is mandatory to accept FALSE_POSITIVE")
    critical: bool = Field(True, description="If True, missing this field forces REQUIRES_ATTENTION")
    requirement_level: str = Field("CORE", description="CORE, CONDITIONAL, OPTIONAL, UNAVAILABLE, or UNVERIFIED")
    description: str = Field("", description="Human-readable requirement rationale")


class RuleEvidenceContract(BaseModel):
    """
    P2-REQ-02: Rule-Specific Machine-Verifiable Evidence Contract.
    Binds directly to an approved PromptVersion for the rule.
    """
    contract_id: str = Field(..., description="Deterministic contract identifier")
    rule_id: str = Field(..., description="SIEM Rule ID")
    prompt_version_id: Optional[str] = Field(None, description="Linked approved PromptVersion ID")
    version_number: int = Field(1, description="Contract revision matching prompt version")
    status: str = Field("UNVERIFIED", description="APPROVED, DRAFT, or UNVERIFIED")
    detection_archetype: str = Field("GENERIC", description="PROCESS_EXECUTION, NETWORK_CONNECTION, FILE_MALWARE, AUTHENTICATION, GENERIC")
    required_evidence: List[EvidenceFieldRequirement] = Field(default_factory=list)
    tp_criteria: List[str] = Field(default_factory=list, description="Machine-evaluable TP criteria strings")
    fp_criteria: List[str] = Field(default_factory=list, description="Machine-evaluable FP criteria strings")
    contradiction_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Defined conflicting conditions")
    on_critical_missing_evidence: str = Field("REQUIRES_ATTENTION", description="Action when critical evidence is absent")

    @computed_field
    @property
    def target_archetype(self) -> str:
        return self.detection_archetype

    @computed_field
    @property
    def core_fields(self) -> List[Dict[str, Any]]:
        return [
            {
                "field_name": r.field,
                "field_type": r.evidence_type,
                "critical": r.critical,
                "required_for_tp": r.required_for_tp,
                "required_for_fp": r.required_for_fp,
                "description": r.description,
            }
            for r in self.required_evidence
            if r.requirement_level == "CORE"
        ]

    @computed_field
    @property
    def conditional_fields(self) -> List[Dict[str, Any]]:
        return [
            {
                "field_name": r.field,
                "field_type": r.evidence_type,
                "condition": r.description or "When relevant context observed",
                "critical": r.critical,
            }
            for r in self.required_evidence
            if r.requirement_level == "CONDITIONAL"
        ]

    @computed_field
    @property
    def unsupported_fields(self) -> List[str]:
        return [
            r.field
            for r in self.required_evidence
            if r.requirement_level == "UNAVAILABLE"
        ]


