import sys
sys.path.insert(0, 'backend')
import zipfile, json
from app.models.incident import Incident
from app.models.rule import Rule
from app.services.empirical_benchmark_harness import EventAdapter
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.detection_archetype_registry import DetectionArchetypeRegistry, ArchetypeId
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper

rule = Rule(
    id="0974a66e-ede2-4a6a-821b-6283a99c8aa4",
    name="Crowdstrike: Suspicious Activity",
    rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
    event_type="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
    severity=5
)

compiled = PolicyCompilerService.compile_policy(rule=rule, prompt_version=None)
print("=== COMPILED SYSTEM PROMPT ===")
print(compiled.compiled_system_prompt[:1500])
print("\n=== REQUIRED EVIDENCE / CONDITIONS ===")
for s in compiled.sections:
    if "evidence" in s.section_id.lower() or "condition" in s.section_id.lower():
        print(f"[{s.section_id}] ({s.title}):\n{s.content}\n")
