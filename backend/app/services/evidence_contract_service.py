import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload
from app.models.rule import Rule
from app.models.prompt import PromptVersion, RulePrompt
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.schemas.rule_intelligence import DetectionSemantics, ArchetypeId, SemanticsDefinitionStatus
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper

logger = logging.getLogger(__name__)


class EvidenceContractService:
    """
    P2-REQ-02 / AIS 2.0 REQ-03: Evidence Contract Service.
    Derives and validates machine-verifiable evidence contracts tied to approved
    rule policies in Agent Intelligence Studio.
    """

    def __init__(self, db: Optional[Any] = None):
        self.db = db

    async def get_active_contract_for_rule(self, rule_id: str) -> Optional[RuleEvidenceContract]:
        """
        Retrieves the active evidence contract for a given rule_id (UUID or rule_identifier).
        """
        if not self.db:
            return None
        try:
            q = select(Rule).where(or_(Rule.id == rule_id, Rule.rule_id == rule_id))
            res = await self.db.execute(q)
            rule = res.scalars().first()
            if not rule:
                return None

            p_q = select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
            p_res = await self.db.execute(p_q)
            rp = p_res.scalars().first()

            active_ver = None
            if rp and rp.versions:
                active_ver = next((v for v in rp.versions if v.id == rp.active_version_id), None) or (rp.versions[0] if rp.versions else None)

            return self.get_contract_for_rule(rule, active_ver)
        except Exception as exc:
            logger.warning(f"Error fetching active contract for rule {rule_id}: {exc}")
            return None

    @classmethod
    def get_contract_for_rule(
        cls,
        rule: Optional[Rule],
        prompt_version: Optional[PromptVersion],
    ) -> RuleEvidenceContract:
        """
        Builds or resolves the machine-verifiable evidence contract for a rule.
        Strictly checks that the contract status matches the policy approval state.
        If prompt_version is not APPROVED, the contract is marked UNVERIFIED.
        Uses RuleIntelligenceAnalyzer and DetectionArchetypeRegistry for detection-aware
        evidence mapping.
        """
        rule_id = getattr(rule, "id", None) or getattr(rule, "rule_id", "UNKNOWN_RULE")
        rule_name = str(getattr(rule, "name", "") or "").lower()
        event_type = str(getattr(rule, "event_type", "") or "").lower()

        # 1. Determine Status: Only APPROVED PromptVersions yield APPROVED contracts
        contract_status = "UNVERIFIED"
        version_num = 1
        pv_id = None
        if prompt_version:
            pv_id = prompt_version.id
            version_num = prompt_version.version_number
            if prompt_version.status == "APPROVED":
                contract_status = "APPROVED"
            else:
                contract_status = "UNVERIFIED"

        # 2. Extract structured detection semantics using RuleIntelligenceAnalyzer
        if rule:
            semantics = RuleIntelligenceAnalyzer.analyze_rule(rule)
            classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
            archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
            
            # Map candidate contract using EvidenceRequirementMapper
            contract = EvidenceRequirementMapper.map_evidence_contract(
                rule=rule,
                semantics=semantics,
                archetype_def=archetype_def,
                prompt_version=prompt_version,
            )
            # Ensure status is bound to prompt_version approval
            contract.status = contract_status
            return contract

        # Fallback for null rule
        combo = f"{rule_name} {event_type}"
        archetype = "GENERIC"
        reqs = [
            EvidenceFieldRequirement(
                field="security.event_type",
                evidence_type="SECURITY_EVENT",
                required_for_tp=True,
                required_for_fp=True,
                critical=True,
                requirement_level="CORE",
                description="Normalized SIEM event type identifier",
            ),
        ]
        return RuleEvidenceContract(
            contract_id=f"EC-{rule_id}-V{version_num}",
            rule_id=str(rule_id),
            prompt_version_id=pv_id,
            version_number=version_num,
            status=contract_status,
            detection_archetype=archetype,
            required_evidence=reqs,
            tp_criteria=[],
            fp_criteria=[],
            contradiction_rules=[],
            on_critical_missing_evidence="REQUIRES_ATTENTION",
        )
