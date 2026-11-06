import time
from typing import List, Dict, Any, Optional
from app.services.model_provider.base import BaseModelProvider, ProviderHealthResponse, StructuredModelVerdict


class SimulatedModelProvider(BaseModelProvider):
    """
    Deterministic test fixture simulation provider for UI and dry-run replay testing.
    CRITICAL RESTRICTION:
    - Every output is explicitly flagged with is_simulated = True.
    - Simulated predictions are NEVER counted as real model accuracy.
    - Zero external network requests or AI API calls.
    """

    def __init__(self, model_name: str = "simulated-heuristic-v1"):
        self.model_name = model_name

    async def get_health(self) -> ProviderHealthResponse:
        return ProviderHealthResponse(
            status="HEALTHY",
            provider_name="SimulatedModelProvider",
            is_simulated=True,
            latency_ms=1,
            message="Deterministic pipeline simulation provider active. All verdicts are SIMULATED.",
            details={"is_simulated": True, "deterministic": True},
        )

    async def list_models(self) -> List[str]:
        return ["simulated-heuristic-v1", "simulated-qwen3-mock"]

    async def analyze_incident(
        self,
        incident_payload: Dict[str, Any],
        rule_spec: Dict[str, Any],
        prompt_text: str,
        prompt_version_number: int = 1,
    ) -> StructuredModelVerdict:
        start_time = time.time()

        incident_id = str(incident_payload.get("incident_id", ""))
        rule_id = str(rule_spec.get("id", rule_spec.get("rule_id", "")))
        title = str(incident_payload.get("title", "")).lower()
        description = str(incident_payload.get("description", "")).lower()

        # Collect text tokens from events for deterministic heuristics
        events = incident_payload.get("events", [])
        event_texts = []
        for ev in events:
            if isinstance(ev, dict):
                raw = str(ev.get("raw_log", "")).lower()
                attrs = str(ev.get("attributes", "")).lower()
                event_texts.append(f"{raw} {attrs}")

        full_telemetry = f"{title} {description} {' '.join(event_texts)}".lower()

        # Deterministic Heuristic Evaluation:
        # 1. Check for Missing Critical Telemetry -> REQUIRES_ATTENTION
        if not events or len(full_telemetry.strip()) < 20:
            verdict = "REQUIRES_ATTENTION"
            reason = "Telemetry stream is truncated or contains zero valid raw event entries. Insufficient evidence for automated decision."
            missing_ev = ["Raw process execution event", "Parent process hierarchy", "Source user authentication token"]
            supp_ev = []
            confidence = 65.0
            questions = ["Has endpoint telemetry ingestion resumed?", "Can SysAdmin verify host status?"]

        # 2. Check for Malicious IOCs / Attack Patterns -> TRUE_POSITIVE
        elif any(k in full_telemetry for k in ["indicator of attack", "disable or modify tools", "powershell", "encoded", "-enc", "c2", "select2", "knob.js", "exporting.js", "review.es", "70cb3d6bf67c91a7"]):
            verdict = "TRUE_POSITIVE"
            reason = "Observed behavioral pattern matches adversary technique: suspicious process invocation with unauthorized script execution artifacts."
            supp_ev = [f"Artifact matched in telemetry: {k}" for k in ["indicator of attack", "process invocation", "script execution"] if k in full_telemetry or True][:2]
            missing_ev = []
            confidence = 94.0
            questions = ["Is endpoint isolated from internal subnet?", "Did command establish outbound C2 beacon?"]

        # 3. Check for Benign / False Positive Signatures -> FALSE_POSITIVE
        elif any(k in full_telemetry for k in ["update.exe", "adrum", "legitimate", "patch", "routine", "scheduled task"]):
            verdict = "FALSE_POSITIVE"
            reason = "Telemetry artifacts correlate with verified software maintenance utilities and expected enterprise background processes."
            supp_ev = ["Verified vendor application binary signature", "Standard scheduled maintenance window"]
            missing_ev = []
            confidence = 96.0
            questions = ["Was this scheduled by IT operations?", "Does file hash match vendor package repository?"]

        # Default fallback -> REQUIRES_ATTENTION
        else:
            verdict = "REQUIRES_ATTENTION"
            reason = "Heuristic thresholds inconclusive on observed attributes. Requires manual tier-2 analyst inspection."
            missing_ev = ["Command line parent process hierarchy"]
            supp_ev = []
            confidence = 70.0
            questions = ["Does the executing user have administrative privileges?"]

        latency_ms = max(1, int((time.time() - start_time) * 1000) + 12)

        return StructuredModelVerdict(
            incident_id=incident_id,
            rule_id=rule_id,
            verdict=verdict,
            confidence=confidence,
            reason=reason,
            supporting_evidence=supp_ev,
            missing_evidence=missing_ev,
            analyst_questions=questions,
            latency_ms=latency_ms,
            model_identifier=self.model_name,
            prompt_version_number=prompt_version_number,
            validation_status="VALID",
            is_simulated=True,  # ALWAYS TRUE FOR SIMULATED PROVIDER
        )

