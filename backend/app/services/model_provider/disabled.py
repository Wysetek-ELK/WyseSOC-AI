from typing import List, Dict, Any, Optional
from app.services.model_provider.base import BaseModelProvider, ProviderHealthResponse, StructuredModelVerdict


class ProviderDisabledError(Exception):
    pass


class DisabledModelProvider(BaseModelProvider):
    """
    Default safe model provider:
    Explicitly indicates that local LLM on Server 2 is not yet connected.
    Prevents unintended network traffic or crashes.
    """

    def __init__(self, message: str = "Local inference engine (Server 2) is disabled and not yet provisioned."):
        self.message = message

    async def get_health(self) -> ProviderHealthResponse:
        return ProviderHealthResponse(
            status="DISABLED",
            provider_name="DisabledModelProvider",
            is_simulated=False,
            latency_ms=0,
            message=self.message,
            details={"configured": False, "server2_connected": False},
        )

    async def list_models(self) -> List[str]:
        return []

    async def analyze_incident(
        self,
        incident_payload: Dict[str, Any],
        rule_spec: Dict[str, Any],
        prompt_text: str,
        prompt_version_number: int = 1,
    ) -> StructuredModelVerdict:
        raise ProviderDisabledError(self.message)
