import pytest
from app.services.model_provider import (
    BaseModelProvider,
    StructuredModelVerdict,
    ProviderDisabledError,
    DisabledModelProvider,
    SimulatedModelProvider,
    OpenAICompatibleProvider,
    get_model_provider,
)


@pytest.mark.asyncio
async def test_disabled_model_provider():
    provider = DisabledModelProvider()
    health = await provider.get_health()
    assert health.status == "DISABLED"
    assert "disabled" in health.message.lower()

    with pytest.raises(ProviderDisabledError) as exc_info:
        await provider.analyze_incident(
            incident_payload={"incident_id": "TEST-1"},
            rule_spec={"name": "Test Rule"},
            prompt_text="Analyze this",
            prompt_version_number=1,
        )
    assert "disabled" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_simulated_model_provider():
    provider = SimulatedModelProvider()
    health = await provider.get_health()
    assert health.status == "HEALTHY"
    assert health.is_simulated is True

    # Test incident with powershell download (likely TP)
    tp_incident = {
        "incident_id": "INC-SIM-01",
        "title": "Powershell encoded download cradle executed",
        "severity": "HIGH",
        "event_type": "Suspicious Activity",
        "source_ip": "198.51.100.22",
        "events": [
            {
                "event_type": "ProcessCreate",
                "source_ip": "198.51.100.22",
                "attributes": {
                    "CommandLine": "powershell.exe -enc aQB3AHIAIABoAHQAdABwADoALwAv...",
                    "FileName": "powershell.exe",
                },
            }
        ],
    }

    verdict = await provider.analyze_incident(
        incident_payload=tp_incident,
        rule_spec={"id": "R-1", "name": "Suspicious Activity", "severity": "HIGH"},
        prompt_text="Investigate command line cradle",
        prompt_version_number=1,
    )

    assert isinstance(verdict, StructuredModelVerdict)
    assert verdict.is_simulated is True
    assert verdict.validation_status == "VALID"
    assert verdict.verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
    assert 0 <= verdict.confidence <= 100
    assert len(verdict.reason) > 0
    assert verdict.model_identifier == "simulated-heuristic-v1"


@pytest.mark.asyncio
async def test_simulated_model_provider_abstains_on_empty_evidence():
    provider = SimulatedModelProvider()
    empty_incident = {
        "incident_id": "INC-EMPTY",
        "title": "Vague activity",
        "severity": "LOW",
        "events": [],
    }

    verdict = await provider.analyze_incident(
        incident_payload=empty_incident,
        rule_spec={"id": "R-EMPTY", "name": "Generic Rule"},
        prompt_text="Analyze",
        prompt_version_number=2,
    )

    assert verdict.is_simulated is True
    assert verdict.verdict == "REQUIRES_ATTENTION"
    assert len(verdict.missing_evidence) > 0
    assert len(verdict.analyst_questions) > 0


def test_factory_provider_resolution():
    assert isinstance(get_model_provider("DISABLED"), DisabledModelProvider)
    assert isinstance(get_model_provider("SIMULATED"), SimulatedModelProvider)
    assert isinstance(get_model_provider("OPENAI_COMPATIBLE"), OpenAICompatibleProvider)

    # Defaults to disabled on unknown provider
    default_p = get_model_provider("UNKNOWN_PROVIDER")
    assert isinstance(default_p, DisabledModelProvider)


def test_robust_parse_model_verdict_json():
    from app.services.model_provider.openai_compatible import robust_parse_model_verdict_json

    # 1. Clean JSON
    clean_json = '{"verdict": "TRUE_POSITIVE", "confidence": 95, "reason": "Attack confirmed"}'
    res, err = robust_parse_model_verdict_json(clean_json)
    assert err is None
    assert res["verdict"] == "TRUE_POSITIVE"
    assert res["confidence"] == 95

    # 2. Markdown fenced JSON
    fenced_json = '```json\n{"verdict": "FALSE_POSITIVE", "confidence": 80.5, "reason": "Expected cron job"}\n```'
    res, err = robust_parse_model_verdict_json(fenced_json)
    assert err is None
    assert res["verdict"] == "FALSE_POSITIVE"
    assert res["confidence"] == 80.5

    # 3. Truncated mid-string (the exact issue seen in production)
    truncated = '{\n  "verdict": "TRUE_POSITIVE",\n  "confidence": 88,\n  "reason": "Suspicious execution of cmd.exe and powershell\n  "supporting_evidence": [\n    "Parent process is explorer.exe'
    res, err = robust_parse_model_verdict_json(truncated)
    assert res is not None
    assert res["verdict"] == "TRUE_POSITIVE"
    assert res["confidence"] == 88.0
    assert "Suspicious execution" in res["reason"]

    # 4. Raw unescaped newlines in reason string
    raw_newlines = '{\n  "verdict": "REQUIRES_ATTENTION",\n  "confidence": 50,\n  "reason": "Line 1\nLine 2"\n}'
    res, err = robust_parse_model_verdict_json(raw_newlines)
    assert err is None
    assert res["verdict"] == "REQUIRES_ATTENTION"
    assert "Line 1" in res["reason"]
