"""
AIS 3.2 — Dynamic Rule Contract Schema.

Defines the typed, versioned, hash-verified DynamicRuleContract specification
governing rule interpretation, evidence requirements, TP/FP/Inconclusive criteria,
organizational context applicability, and validation boundaries.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from app.utils.datetime_utils import utc_now


class ContractApprovalState(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    APPROVED = "APPROVED"
    DRAFT = "DRAFT"
    REVOKED = "REVOKED"


class DetectionVerificationLevel(str, Enum):
    SIEM_REPORTED_DETECTION = "SIEM_REPORTED_DETECTION"
    INDEPENDENTLY_RECONSTRUCTED = "INDEPENDENTLY_RECONSTRUCTED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    UNVERIFIABLE = "UNVERIFIABLE"


_UNSAFE_OVERRIDE_PATTERNS = (
    re.compile(r"\bignore\s+(?:all\s+)?(?:previous|safety|validator|guardrail)", re.IGNORECASE),
    re.compile(r"\balways\s+(?:return|output|classify\s+as)\s+(?:true_positive|false_positive)\b", re.IGNORECASE),
    re.compile(r"\bground[_\s]?truth\b|\bexpected[_\s]?verdict\b|\bbenchmark[_\s]?label\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+(?:validation|guardrail|safety|authorization)\b", re.IGNORECASE),
    re.compile(r"\bAIS_3_0_INDEPENDENT_HOLDOUT_100\b|\bAIS_2_6E_FROZEN_20\b", re.IGNORECASE),
)


class RuleConditionClause(BaseModel):
    attribute: str
    operator: str
    expected: str
    logical_op: str = "AND"
    negated: bool = False
    nested_group: Optional[str] = None
    evaluation_status: str = "UNKNOWN"  # MATCHED | NOT_MATCHED | UNKNOWN | NOT_EVALUABLE | SIEM_REPORTED
    observed_values: List[str] = Field(default_factory=list)


class DynamicRuleContract(BaseModel):
    """Complete typed contract for universal rule-aware verdict intelligence (AIS 3.2)."""

    contract_id: str
    contract_version: int = 1
    fortisiem_rule_id: str
    rule_name: str
    rule_definition_hash: str
    rule_archetype: str  # Canonical AIS 3.2 archetype
    secondary_archetype: Optional[str] = None
    mapping_rationale: str = ""
    detection_objective: str
    detection_category: str = ""
    source_vendor: str = "FortiSIEM"

    # Parsed Rule Detection Semantics
    rule_conditions: List[RuleConditionClause] = Field(default_factory=list)
    aggregation_logic: str = ""
    thresholds: Dict[str, Any] = Field(default_factory=dict)
    time_window: Optional[str] = None
    group_by_fields: List[str] = Field(default_factory=list)
    correlation_requirements: List[str] = Field(default_factory=list)

    # Evidence Requirements
    mandatory_evidence_fields: List[str] = Field(default_factory=list)
    optional_evidence_fields: List[str] = Field(default_factory=list)

    # Decision Semantics & Criteria
    tp_criteria: List[str] = Field(default_factory=list)
    fp_criteria: List[str] = Field(default_factory=list)
    inconclusive_criteria: List[str] = Field(default_factory=list)
    authorization_requirements: List[str] = Field(default_factory=list)
    known_legitimate_exceptions: List[str] = Field(default_factory=list)
    evidence_completeness_requirements: Dict[str, Any] = Field(default_factory=dict)
    approved_organizational_context_types: List[str] = Field(default_factory=list)
    claim_validation_requirements: List[str] = Field(default_factory=list)
    severity_interpretation: str = ""
    detection_limitations: List[str] = Field(default_factory=list)

    # Governance & Provenance
    approval_state: ContractApprovalState = ContractApprovalState.PROVISIONAL
    reviewer: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    policy_provenance: str = "RULE_INTELLIGENCE_ENGINE_V3_2"
    contract_hash: str = ""
    is_supported_rule: bool = True
    unsupported_reason: Optional[str] = None
    rule_overrides: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("tp_criteria", "fp_criteria", "inconclusive_criteria", "known_legitimate_exceptions")
    @classmethod
    def validate_no_unsafe_directives(cls, v: List[str]) -> List[str]:
        for item in v:
            txt = str(item or "")
            for pat in _UNSAFE_OVERRIDE_PATTERNS:
                if pat.search(txt):
                    raise ValueError(
                        f"Unsafe policy override or benchmark leakage detected in contract criteria: '{txt[:80]}'"
                    )
        return v

    @field_validator("detection_objective", "mapping_rationale", "severity_interpretation")
    @classmethod
    def validate_safe_text_fields(cls, v: str) -> str:
        txt = str(v or "")
        for pat in _UNSAFE_OVERRIDE_PATTERNS:
            if pat.search(txt):
                raise ValueError(
                    f"Unsafe policy override or benchmark leakage detected in contract text: '{txt[:80]}'"
                )
        return txt

    @field_validator("rule_overrides")
    @classmethod
    def validate_safe_rule_overrides(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        forbidden_keys = {"force_verdict", "bypass_validator", "auto_close_incidents", "allow_fabricated_claims", "certified_verdict", "ground_truth", "expected_verdict"}
        for k, val in (v or {}).items():
            kl = str(k).lower().strip()
            if kl in forbidden_keys:
                raise ValueError(f"Unsafe override or benchmark leakage key rejected in rule_overrides: '{k}'")
            serialized = json.dumps(val, default=str) if not isinstance(val, str) else val
            for pat in _UNSAFE_OVERRIDE_PATTERNS:
                if pat.search(serialized):
                    raise ValueError(f"Unsafe policy override or benchmark leakage value in rule_overrides['{k}']")
        return v

    def compute_contract_hash(self) -> str:
        core = self.model_dump(
            mode="json",
            exclude={"contract_hash", "created_at", "updated_at"},
        )
        encoded = json.dumps(core, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
