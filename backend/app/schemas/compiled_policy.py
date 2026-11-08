from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PolicySectionType(str, Enum):
    COMMON_SOC_BASELINE = "COMMON_SOC_BASELINE"
    RULE_SPECIFIC_DIRECTIVE = "RULE_SPECIFIC_DIRECTIVE"
    DETECTION_CONDITIONS = "DETECTION_CONDITIONS"
    REQUIRED_EVIDENCE = "REQUIRED_EVIDENCE"
    TRUE_POSITIVE_INDICATORS = "TRUE_POSITIVE_INDICATORS"
    FALSE_POSITIVE_INDICATORS = "FALSE_POSITIVE_INDICATORS"
    ABSTENTION_CRITERIA = "ABSTENTION_CRITERIA"
    ESCALATION_CONDITIONS = "ESCALATION_CONDITIONS"
    ANALYST_QUESTIONS = "ANALYST_QUESTIONS"


class CompilationExecutionMode(str, Enum):
    LIVE = "LIVE"
    SIMULATION = "SIMULATION"
    REPLAY = "REPLAY"


class CompiledPromptSection(BaseModel):
    section_index: int = Field(..., ge=1, le=9, description="Section order index (1-9)")
    section_id: PolicySectionType
    title: str
    content: str
    is_trusted: bool = True
    estimated_tokens: int = 0


class CompiledPolicyPrompt(BaseModel):
    """
    Structured nine-section policy compilation product (P3-REQ-01).
    Ensures complete prompt parity across Live, Simulation, and Replay environments.
    """
    compiler_version: str = "v3.0.0"
    policy_id: Optional[str] = None
    policy_version_id: Optional[str] = None
    version_number: Optional[int] = None
    rule_id: str
    rule_name: str
    execution_mode: CompilationExecutionMode = CompilationExecutionMode.LIVE
    policy_status: str = "APPROVED"
    is_approved: bool = True
    sections: List[CompiledPromptSection] = []
    compiled_system_prompt: str
    untrusted_data_enclosure_open: str = "<UNTRUSTED_INCIDENT_DATA>"
    untrusted_data_enclosure_close: str = "</UNTRUSTED_INCIDENT_DATA>"
    rag_enclosure_open: str = "<VERIFIED_HISTORICAL_PRECEDENTS>"
    rag_enclosure_close: str = "</VERIFIED_HISTORICAL_PRECEDENTS>"
    model_response_schema: Dict[str, Any] = Field(default_factory=dict)
    compilation_digest: str
    total_estimated_tokens: int = 0
    compiled_at: str

