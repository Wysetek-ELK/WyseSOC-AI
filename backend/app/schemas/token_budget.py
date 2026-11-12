from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TokenAllocationBreakdown(BaseModel):
    max_context_tokens: int = 16384
    max_completion_tokens: int = 1024
    available_prompt_budget: int = 8192
    target_input_budget: Optional[int] = 8192
    model_name: Optional[str] = None

    # Measured tokens per priority tier
    p1_safety_and_schema_tokens: int = 0
    p2_policy_sections_tokens: int = 0
    p3_mandatory_contract_tokens: int = 0
    p4_critical_telemetry_tokens: int = 0
    p5_correlated_events_tokens: int = 0
    p6_optional_enrichment_tokens: int = 0
    p7_rag_precedents_tokens: int = 0

    total_prompt_tokens: int = 0
    rag_trimmed: bool = False
    enrichment_trimmed: bool = False
    events_pruned_count: int = 0
    events_compacted: bool = False
    evidence_compacted: bool = False
    context_overflow_detected: bool = False
    overflow_reason: Optional[str] = None


class BudgetedPromptResult(BaseModel):
    breakdown: TokenAllocationBreakdown
    budgeted_system_prompt: str
    budgeted_incident_payload: Dict[str, Any]
    budgeted_rag_block: str
    can_proceed_to_inference: bool = True
    abstention_reason: Optional[str] = None

