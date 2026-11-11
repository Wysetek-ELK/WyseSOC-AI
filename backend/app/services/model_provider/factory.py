from typing import Optional
from app.config import settings
from app.services.model_provider.base import BaseModelProvider
from app.services.model_provider.disabled import DisabledModelProvider
from app.services.model_provider.simulated import SimulatedModelProvider
from app.services.model_provider.openai_compatible import OpenAICompatibleProvider


def get_model_provider(
    provider_type: str = "SIMULATED",
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseModelProvider:
    """
    Factory creating the requested provider instance.
    Defaults safely to DisabledModelProvider if requested or unsupported.
    """
    ptype = provider_type.upper().strip()

    if ptype == "SIMULATED":
        return SimulatedModelProvider(model_name=model_name or "simulated-heuristic-v1")
    elif ptype == "OPENAI_COMPATIBLE":
        if base_url is None or model_name is None:
            from app.services.llm_config_service import LLMConfigService
            LLMConfigService.sync_runtime_settings()
        return OpenAICompatibleProvider(
            base_url=base_url or settings.LOCAL_LLM_BASE_URL,
            api_key=api_key or settings.LOCAL_LLM_API_KEY,
            model_name=model_name or settings.LOCAL_LLM_MODEL_NAME,
            timeout_seconds=settings.LOCAL_LLM_TIMEOUT,
            max_tokens=getattr(settings, "LOCAL_LLM_MAX_TOKENS", 512),
        )
    elif ptype == "DISABLED":
        return DisabledModelProvider()
    else:
        return DisabledModelProvider(f"Unknown provider type '{provider_type}'. Defaulting to disabled.")

