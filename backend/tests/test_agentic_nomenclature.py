import pytest
from app.services.verdict_triage_agent import VerdictTriageAgent, AIVerdictService
from app.services.sentinel_ingest_worker import SentinelIngestWorker, FortiSIEMSyncScheduler, sentinel_ingest_worker, fortisiem_scheduler
from app.services.agent_memory_engine import AgentMemoryEngine, LearningService
from app.services.agent_policy_engine import AgentPolicyEngine, PromptStudioService
from app.services.inference_health_monitor import InferenceHealthMonitor, SystemMonitorService
from app.services.evidence_integrity_guardrail import EvidenceIntegrityGuardrail, build_model_facing_payload, sanitize_event_attributes
from app.services.detection_context_engine import DetectionContextEngine, RuleParser
from app.services.review_orchestrator import ReviewOrchestrator, InvestigationService
from app.services.verdict_evaluation_engine import VerdictEvaluationEngine, EvaluationService
from app.services.validation_engine import ValidationEngine, DryRunService
from app.utils.payload_sanitization_guard import PayloadSanitizationGuard, ZipGuard, PayloadSanitizationException, ZipSecurityException


def test_naming_refactor_identity_and_aliases():
    """Verifies that all new Agentic SOC Intelligence Platform nomenclature aliases point to identical classes/singletons."""
    assert VerdictTriageAgent is AIVerdictService
    assert SentinelIngestWorker is FortiSIEMSyncScheduler
    assert sentinel_ingest_worker is fortisiem_scheduler
    assert AgentMemoryEngine is LearningService
    assert AgentPolicyEngine is PromptStudioService
    assert InferenceHealthMonitor is SystemMonitorService
    assert DetectionContextEngine is RuleParser
    assert ReviewOrchestrator is InvestigationService
    assert VerdictEvaluationEngine is EvaluationService
    assert ValidationEngine is DryRunService
    assert PayloadSanitizationGuard is ZipGuard
    assert PayloadSanitizationException is ZipSecurityException


def test_evidence_integrity_guardrail():
    """Verifies EvidenceIntegrityGuardrail methods sanitize attributes and drop forbidden ground truth keys."""
    raw_attrs = {
        "srcIp": "192.168.1.50",
        "resolution": "False Positive",
        "cleared_reason": "Testing",
        "comments": "Should be dropped",
    }
    cleaned = EvidenceIntegrityGuardrail.sanitize_event_attributes(raw_attrs)
    assert "srcIp" in cleaned
    assert "resolution" not in cleaned
    assert "cleared_reason" not in cleaned
    assert "comments" not in cleaned


def test_reconcile_pending_triage_method_exists():
    """Verifies reconcile_pending_triage method exists on VerdictTriageAgent and is aliased."""
    assert hasattr(VerdictTriageAgent, "reconcile_pending_triage")
    assert hasattr(VerdictTriageAgent, "process_pending_incidents")
    assert VerdictTriageAgent.reconcile_pending_triage == VerdictTriageAgent.process_pending_incidents

