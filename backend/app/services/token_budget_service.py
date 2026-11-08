import json
import copy
from typing import Optional, Dict, Any, List
from app.schemas.token_budget import TokenAllocationBreakdown, BudgetedPromptResult
from app.schemas.compiled_policy import CompiledPolicyPrompt


class TokenBudgetService:
    """
    Evidence-Preserving Token Budgeting Service (P3-REQ-05 / Finding AV-009).
    Allocates tokens across prompt sections according to strict priority hierarchy:
    P1: System safety instructions & JSON schema (IMMUTABLE)
    P2: Approved policy directives (IMMUTABLE)
    P3: Mandatory Evidence Contract requirements (IMMUTABLE)
    P4: Critical current incident telemetry & evidence IDs (IMMUTABLE)
    P5: Correlated secondary events (TRIMMABLE)
    P6: Optional enrichment fields (TRIMMABLE)
    P7: Verified historical precedents (TRIMMED FIRST)

    Guarantees that critical evidence values, command lines, and evidence IDs are NEVER naively truncated.
    If the mandatory core exceeds available budget, triggers safe abstention.
    """
    DEFAULT_MAX_CONTEXT = 4096
    DEFAULT_MAX_COMPLETION = 1024

    @staticmethod
    def estimate_tokens(obj: Any) -> int:
        if obj is None:
            return 0
        if isinstance(obj, str):
            text = obj
        elif isinstance(obj, (dict, list)):
            text = json.dumps(obj)
        else:
            text = str(obj)
        return max(1, len(text) // 4)

    @classmethod
    def budget_prompt(
        cls,
        compiled_policy: CompiledPolicyPrompt,
        incident_payload: Dict[str, Any],
        rag_block: str = "",
        max_context_tokens: int = DEFAULT_MAX_CONTEXT,
        max_completion_tokens: int = DEFAULT_MAX_COMPLETION,
    ) -> BudgetedPromptResult:
        available_budget = max(512, max_context_tokens - max_completion_tokens)

        # Deepcopy payload so original is unmutated
        payload_work = copy.deepcopy(incident_payload)
        rag_work = rag_block or ""

        # Measure Priority 1 & 2 (Compiled System Prompt)
        # Note: sections 1-9 are P2, sections 10-11 are P1
        p1_schema_tokens = cls.estimate_tokens(compiled_policy.model_response_schema) + 120
        p2_policy_tokens = max(0, cls.estimate_tokens(compiled_policy.compiled_system_prompt) - p1_schema_tokens)

        # Measure Priority 3: Mandatory Evidence Contract requirements in payload
        contract_info = payload_work.get("evidence_contract") or {}
        p3_contract_tokens = cls.estimate_tokens(contract_info)

        # Measure Priority 4: Critical telemetry (canonical evidence records, primary event command lines)
        canonical_ev = payload_work.get("canonical_evidence") or []
        p4_critical_tokens = cls.estimate_tokens(canonical_ev) + cls.estimate_tokens(payload_work.get("title"))

        # Measure Priority 5: Correlated events (beyond first event)
        events = payload_work.get("events") or []
        p5_events_tokens = cls.estimate_tokens(events[1:]) if len(events) > 1 else 0

        # Measure Priority 6: Optional enrichment
        enrichment = payload_work.get("enrichment") or {}
        p6_enrichment_tokens = cls.estimate_tokens(enrichment)

        # Measure Priority 7: Historical RAG precedents
        p7_rag_tokens = cls.estimate_tokens(rag_work)

        total_tokens = (
            cls.estimate_tokens(compiled_policy.compiled_system_prompt)
            + cls.estimate_tokens(payload_work)
            + p7_rag_tokens
        )

        rag_trimmed = False
        enrichment_trimmed = False
        events_pruned = 0
        overflow_detected = False
        overflow_reason = None

        # Trimming Step 1: If over budget, trim RAG precedents (P7 trimmed first)
        if total_tokens > available_budget and p7_rag_tokens > 0:
            rag_work = ""
            rag_trimmed = True
            p7_rag_tokens = 0
            total_tokens = (
                cls.estimate_tokens(compiled_policy.compiled_system_prompt)
                + cls.estimate_tokens(payload_work)
            )

        # Trimming Step 2: If still over budget, trim optional enrichment (P6)
        if total_tokens > available_budget and p6_enrichment_tokens > 0:
            if "enrichment" in payload_work:
                del payload_work["enrichment"]
            enrichment_trimmed = True
            p6_enrichment_tokens = 0
            total_tokens = (
                cls.estimate_tokens(compiled_policy.compiled_system_prompt)
                + cls.estimate_tokens(payload_work)
            )

        # Trimming Step 3: If still over budget, prune secondary events (P5), preserving primary event
        if total_tokens > available_budget and len(events) > 1:
            orig_count = len(events)
            # Keep primary event only
            payload_work["events"] = events[:1]
            events_pruned = orig_count - 1
            p5_events_tokens = 0
            total_tokens = (
                cls.estimate_tokens(compiled_policy.compiled_system_prompt)
                + cls.estimate_tokens(payload_work)
            )

        # Trimming Step 4: Check if mandatory core (P1 + P2 + P3 + P4) still exceeds budget
        if total_tokens > available_budget:
            overflow_detected = True
            overflow_reason = (
                f"CONTEXT_WINDOW_EXCEEDED: Mandatory policy directives and critical telemetry "
                f"({total_tokens} tokens) exceed available prompt budget ({available_budget} tokens). "
                "Refusing naive truncation to preserve evidence integrity."
            )

        breakdown = TokenAllocationBreakdown(
            max_context_tokens=max_context_tokens,
            max_completion_tokens=max_completion_tokens,
            available_prompt_budget=available_budget,
            p1_safety_and_schema_tokens=p1_schema_tokens,
            p2_policy_sections_tokens=p2_policy_tokens,
            p3_mandatory_contract_tokens=p3_contract_tokens,
            p4_critical_telemetry_tokens=p4_critical_tokens,
            p5_correlated_events_tokens=p5_events_tokens,
            p6_optional_enrichment_tokens=p6_enrichment_tokens,
            p7_rag_precedents_tokens=p7_rag_tokens,
            total_prompt_tokens=total_tokens,
            rag_trimmed=rag_trimmed,
            enrichment_trimmed=enrichment_trimmed,
            events_pruned_count=events_pruned,
            context_overflow_detected=overflow_detected,
            overflow_reason=overflow_reason,
        )

        return BudgetedPromptResult(
            breakdown=breakdown,
            budgeted_system_prompt=compiled_policy.compiled_system_prompt,
            budgeted_incident_payload=payload_work,
            budgeted_rag_block=rag_work,
            can_proceed_to_inference=not overflow_detected,
            abstention_reason=overflow_reason,
        )

