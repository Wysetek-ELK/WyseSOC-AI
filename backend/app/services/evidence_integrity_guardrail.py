"""
Evidence Integrity Guardrail Module.
Guarantees input evidence protection and zero leakage of historical resolution/closure data into LLM prompts.
"""
from app.services.model_payload_allowlist import (
    EvidenceIntegrityGuardrail,
    build_model_facing_payload,
    sanitize_event_attributes,
    FORBIDDEN_GROUND_TRUTH_KEYS,
)

__all__ = [
    "EvidenceIntegrityGuardrail",
    "build_model_facing_payload",
    "sanitize_event_attributes",
    "FORBIDDEN_GROUND_TRUTH_KEYS",
]

