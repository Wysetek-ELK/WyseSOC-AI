from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class RetrievedPrecedent(BaseModel):
    precedent_id: str
    incident_id: str
    incident_title: str
    rule_id: str
    tenant_id: Optional[str] = None
    verified_verdict: str
    analyst_explanation: str
    key_evidence_summary: Optional[str] = None
    similarity_score: float = Field(0.0, ge=0.0, le=1.0)
    feedback_timestamp: str
    is_exact_rule_match: bool = True
    temporal_check_passed: bool = True


class RAGRetrievalResult(BaseModel):
    """
    Result of verified semantic precedent retrieval (P3-REQ-03, P3-REQ-04).
    Enforces strict tenant isolation, verified supervisor approval, and temporal integrity.
    """
    query_incident_id: str
    tenant_id: Optional[str] = None
    rule_id: str
    precedents: List[RetrievedPrecedent] = Field(default_factory=list)
    total_candidates_examined: int = 0
    candidates_rejected_unverified: int = 0
    candidates_rejected_cross_tenant: int = 0
    candidates_rejected_cross_rule: int = 0
    candidates_rejected_future_leakage: int = 0
    candidates_rejected_duplicate: int = 0
    retrieval_status: str = "NO_VERIFIED_PRECEDENT"
    formatted_rag_block: str = ""

