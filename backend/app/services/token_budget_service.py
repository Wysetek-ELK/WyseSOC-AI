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
    P5: Correlated secondary events (PROGRESSIVELY TRIMMABLE)
    P6: Optional enrichment fields (TRIMMABLE)
    P7: Verified historical precedents (TRIMMED FIRST)

    Guarantees that critical evidence values, command lines, and evidence IDs are NEVER naively truncated.
    If the mandatory core exceeds available budget, triggers safe fail-closed CONTEXT_WINDOW_EXCEEDED abstention.
    """
    DEFAULT_MAX_CONTEXT = 16384
    DEFAULT_MAX_COMPLETION = 1024
    DEFAULT_TARGET_INPUT_BUDGET = 8192

    @classmethod
    def calculate_available_input_tokens(
        cls,
        max_context_tokens: int = DEFAULT_MAX_CONTEXT,
        reserved_output_tokens: Optional[int] = None,
        max_completion_tokens: Optional[int] = None,
        target_input_budget: Optional[int] = None,
    ) -> int:
        """
        Dynamically calculates available input tokens based on model context capacity,
        reserved output tokens, and optional target input budget.
        - Headroom: max(512, max_context_tokens - comp_tokens).
        - When target_input_budget is provided, effective input is bounded by available headroom
          and target_input_budget.
        Guarantees at least 512 prompt tokens if context allows.
        """
        comp_tokens = (
            int(reserved_output_tokens)
            if reserved_output_tokens is not None
            else (int(max_completion_tokens) if max_completion_tokens is not None else cls.DEFAULT_MAX_COMPLETION)
        )
        headroom = max(512, int(max_context_tokens) - comp_tokens)
        if target_input_budget is not None and int(target_input_budget) > 0:
            return max(512, min(int(target_input_budget), headroom))
        return headroom

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

    @staticmethod
    def _compact_canonical_evidence(
        payload_work: Dict[str, Any],
    ) -> bool:
        """
        Strips non-reasoning forensic digest/null metadata from canonical_evidence
        while strictly preserving every evidence_id, source_field, observed_value,
        and evidence_type required for grounded LLM citations.
        Returns True if payload_work changed.
        """
        can_ev = payload_work.get("canonical_evidence")
        if not isinstance(can_ev, list) or not can_ev:
            return False

        has_event_raw_log = bool(
            isinstance(payload_work.get("events"), list)
            and payload_work["events"]
            and isinstance(payload_work["events"][0], dict)
            and payload_work["events"][0].get("raw_log")
        )
        compacted: List[Dict[str, Any]] = []
        changed = False
        preserved_keys = ("evidence_id", "source_field", "field", "observed_value", "value", "evidence_type")
        for item in can_ev:
            if not isinstance(item, dict):
                compacted.append(item)
                continue
            # Avoid duplicating the raw log string twice when events[0].raw_log is already present
            if (
                has_event_raw_log
                and item.get("source_field") == "security.raw_log"
                and len(can_ev) > 1
            ):
                changed = True
                continue
            minimal: Dict[str, Any] = {}
            for keep_key in preserved_keys:
                if keep_key in item and item[keep_key] is not None:
                    minimal[keep_key] = item[keep_key]
            if len(minimal) < len(item):
                changed = True
            compacted.append(minimal if minimal else item)

        if changed:
            payload_work["canonical_evidence"] = compacted
        return changed

    @staticmethod
    def _compact_events(
        payload_work: Dict[str, Any],
        contract_fields: set,
    ) -> bool:
        """
        Compacts remaining events by stripping empty/null attributes and long non-contract fields
        while strictly preserving all fields defined in the Evidence Contract.
        Returns True if payload_work changed.
        """
        events = payload_work.get("events")
        if not isinstance(events, list) or not events:
            return False

        compacted_events: List[Dict[str, Any]] = []
        changed = False
        for ev in events:
            if not isinstance(ev, dict):
                compacted_events.append(ev)
                continue
            ev_copy = dict(ev)
            attrs = ev_copy.get("attributes")
            if isinstance(attrs, dict):
                min_attrs = {
                    k: v for k, v in attrs.items()
                    if v is not None and v != "" and (k in contract_fields or len(str(v)) < 250)
                }
                if len(min_attrs) < len(attrs):
                    ev_copy["attributes"] = min_attrs
                    changed = True
            compacted_events.append(ev_copy)

        if changed:
            payload_work["events"] = compacted_events
        return changed

    @classmethod
    def budget_prompt(
        cls,
        compiled_policy: CompiledPolicyPrompt,
        incident_payload: Dict[str, Any],
        rag_block: str = "",
        max_context_tokens: int = DEFAULT_MAX_CONTEXT,
        max_completion_tokens: int = DEFAULT_MAX_COMPLETION,
        reserved_overhead_tokens: int = 0,
        model_name: Optional[str] = None,
        target_input_budget: Optional[int] = None,
    ) -> BudgetedPromptResult:
        available_budget = cls.calculate_available_input_tokens(
            max_context_tokens=max_context_tokens,
            reserved_output_tokens=max_completion_tokens,
            target_input_budget=target_input_budget,
        )

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
            + max(0, int(reserved_overhead_tokens))
        )

        rag_trimmed = False
        enrichment_trimmed = False
        events_pruned = 0
        events_compacted = False
        evidence_compacted = False
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
                + max(0, int(reserved_overhead_tokens))
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
                + max(0, int(reserved_overhead_tokens))
            )

        # Trimming Step 3a: Progressive pruning of secondary events (P5)
        # Pruning from the last secondary event backwards, preserving events[0]
        # and as many correlated events as fit in budget.
        if total_tokens > available_budget and len(events) > 1:
            orig_count = len(events)
            current_events = list(events)
            while len(current_events) > 1 and total_tokens > available_budget:
                current_events.pop()
                payload_work["events"] = current_events
                events_pruned = orig_count - len(current_events)
                p5_events_tokens = cls.estimate_tokens(current_events[1:]) if len(current_events) > 1 else 0
                total_tokens = (
                    cls.estimate_tokens(compiled_policy.compiled_system_prompt)
                    + cls.estimate_tokens(payload_work)
                    + max(0, int(reserved_overhead_tokens))
                )

        # Trimming Step 3b: Event attribute and log compaction for remaining events
        if total_tokens > available_budget and payload_work.get("events"):
            contract_fields = set(contract_info.get("required_fields") or [])
            if cls._compact_events(payload_work, contract_fields):
                events_compacted = True
                remaining_events = payload_work.get("events") or []
                p5_events_tokens = cls.estimate_tokens(remaining_events[1:]) if len(remaining_events) > 1 else 0
                total_tokens = (
                    cls.estimate_tokens(compiled_policy.compiled_system_prompt)
                    + cls.estimate_tokens(payload_work)
                    + max(0, int(reserved_overhead_tokens))
                )

        # Trimming Step 3c: Canonical evidence compaction
        # Strips non-reasoning forensic digest/null metadata inside canonical_evidence
        # while strictly preserving every evidence_id, source_field, and observed_value.
        if total_tokens > available_budget:
            if cls._compact_canonical_evidence(payload_work):
                evidence_compacted = True
                p4_critical_tokens = cls.estimate_tokens(payload_work.get("canonical_evidence") or []) + cls.estimate_tokens(payload_work.get("title"))
                total_tokens = (
                    cls.estimate_tokens(compiled_policy.compiled_system_prompt)
                    + cls.estimate_tokens(payload_work)
                    + max(0, int(reserved_overhead_tokens))
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
            target_input_budget=target_input_budget,
            model_name=model_name,
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
            events_compacted=events_compacted,
            evidence_compacted=evidence_compacted,
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

