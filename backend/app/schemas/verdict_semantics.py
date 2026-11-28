"""
AIS 3.2 — Separated Verdict Semantics Schema & Policy Mapping Models.

Decouples detection validity, malicious/operational activity characterization,
verified authorization status, and operational impact from the external
TRUE_POSITIVE / FALSE_POSITIVE / REQUIRES_ATTENTION (INCONCLUSIVE) verdict.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.utils.datetime_utils import utc_now


class DetectionValidity(str, Enum):
    CONFIRMED = "CONFIRMED"
    NOT_CONFIRMED = "NOT_CONFIRMED"
    UNKNOWN = "UNKNOWN"


class ActivityCharacterization(str, Enum):
    MALICIOUS = "MALICIOUS"
    SUSPICIOUS = "SUSPICIOUS"
    BENIGN_AUTHORIZED = "BENIGN_AUTHORIZED"
    BENIGN_UNAUTHORIZED = "BENIGN_UNAUTHORIZED"
    OPERATIONAL_ISSUE = "OPERATIONAL_ISSUE"
    UNKNOWN = "UNKNOWN"


class AuthorizationStatus(str, Enum):
    VERIFIED_AUTHORIZED = "VERIFIED_AUTHORIZED"
    VERIFIED_UNAUTHORIZED = "VERIFIED_UNAUTHORIZED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class OperationalImpact(str, Enum):
    CONFIRMED = "CONFIRMED"
    POSSIBLE = "POSSIBLE"
    NOT_DETECTED = "NOT_DETECTED"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class SemanticPolicyApprovalState(str, Enum):
    PROVISIONAL = "PROVISIONAL"
    SOC_APPROVED = "SOC_APPROVED"


class SemanticMappingRule(BaseModel):
    """Formal rule describing how internal semantic dimensions map to final verdict."""
    rule_key: str
    archetype: str
    detection_objective_type: str  # SECURITY_THREAT, POLICY_COMPLIANCE, CONFIGURATION_AUDIT, OPERATIONAL_HEALTH
    tp_semantics: str
    fp_semantics: str
    inconclusive_semantics: str
    operational_is_tp_when_confirmed: bool = False
    requires_authorization_for_fp: bool = True
    blocked_traffic_can_still_be_tp: bool = False
    approval_state: SemanticPolicyApprovalState = SemanticPolicyApprovalState.PROVISIONAL
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None


class VerdictSemanticsEvaluation(BaseModel):
    """Evaluated 4-dimension semantic state reconciled against rule contract."""
    detection_validity: DetectionValidity = DetectionValidity.UNKNOWN
    activity_characterization: ActivityCharacterization = ActivityCharacterization.UNKNOWN
    authorization_status: AuthorizationStatus = AuthorizationStatus.UNKNOWN
    operational_impact: OperationalImpact = OperationalImpact.UNKNOWN
    derived_verdict: str = "REQUIRES_ATTENTION"  # TRUE_POSITIVE | FALSE_POSITIVE | REQUIRES_ATTENTION
    proposed_verdict: str = "REQUIRES_ATTENTION"
    is_semantically_consistent: bool = True
    consistency_issues: List[str] = Field(default_factory=list)
    mapping_rationale: str = ""
    approval_state: SemanticPolicyApprovalState = SemanticPolicyApprovalState.PROVISIONAL
    evaluated_at: datetime = Field(default_factory=utc_now)
