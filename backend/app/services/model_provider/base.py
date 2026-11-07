from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field


class ProviderHealthResponse(BaseModel):
    status: str  # HEALTHY, DEGRADED, OFFLINE, DISABLED
    provider_name: str
    is_simulated: bool
    latency_ms: Optional[int] = None
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class StructuredModelVerdict(BaseModel):
    incident_id: str
    rule_id: str
    verdict: str = Field(..., description="TRUE_POSITIVE, FALSE_POSITIVE, or REQUIRES_ATTENTION")
    confidence: float = Field(100.0, ge=0.0, le=100.0)
    reason: str = Field(..., description="Technical justification for verdict")
    supporting_evidence: List[str] = Field(default_factory=list)
    missing_evidence: List[str] = Field(default_factory=list)
    analyst_questions: List[str] = Field(default_factory=list)
    latency_ms: int = Field(0, ge=0)
    model_identifier: str = Field("default-model")
    prompt_version_number: int = Field(1, ge=1)
    validation_status: str = Field("VALID", description="VALID, INVALID_SCHEMA, UNEXPECTED_VERDICT")
    is_simulated: bool = Field(False, description="CRITICAL: True if output is from test simulator, False if real LLM")
    prompt_tokens: int = Field(0, ge=0, description="Tokens used for input prompt")
    completion_tokens: int = Field(0, ge=0, description="Tokens generated in output")
    total_tokens: int = Field(0, ge=0, description="Total tokens consumed by inference")


class BaseModelProvider(ABC):
    """
    Abstract Base Class for model inference providers.
    Ensures provider-agnostic integration for future local LLM (Server 2).
    """

    @abstractmethod
    async def get_health(self) -> ProviderHealthResponse:
        """Check provider status and latency."""
        pass

    @abstractmethod
    async def list_models(self) -> List[str]:
        """List available models served by the endpoint."""
        pass

    @abstractmethod
    async def analyze_incident(
        self,
        incident_payload: Dict[str, Any],
        rule_spec: Dict[str, Any],
        prompt_text: str,
        prompt_version_number: int = 1,
    ) -> StructuredModelVerdict:
        """Execute incident triage analysis and return structured validated verdict."""
        pass

    def validate_verdict_schema(self, raw_verdict: Dict[str, Any]) -> Tuple[bool, str, Optional[str]]:
        """
        Defensive schema validation:
        Invalid/incomplete outputs must NEVER be defaulted to False Positive.
        Returns: (is_valid, validation_status, error_message)
        """
        if not isinstance(raw_verdict, dict):
            return False, "INVALID_SCHEMA", "Response payload is not a JSON object"

        verdict = str(raw_verdict.get("verdict", "")).upper().strip()
        valid_verdicts = {"TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION"}

        if not verdict:
            return False, "INVALID_SCHEMA", "Missing required field: verdict"

        if verdict not in valid_verdicts:
            return False, "UNEXPECTED_VERDICT", f"Unknown verdict: {verdict}. Allowed: {valid_verdicts}"

        if not raw_verdict.get("reason"):
            return False, "INVALID_SCHEMA", "Missing required field: reason"

        return True, "VALID", None

