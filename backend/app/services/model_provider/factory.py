from typing import Optional
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
        return OpenAICompatibleProvider(
            base_url=base_url or "http://127.0.0.1:8001/v1",
            api_key=api_key,
            model_name=model_name or "qwen3-8b-instruct",
        )
    elif ptype == "DISABLED":
        return DisabledModelProvider()
    else:
        return DisabledModelProvider(f"Unknown provider type '{provider_type}'. Defaulting to disabled.")

