import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule import Rule
from app.models.user import User
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.schemas.prompt import (
    RulePromptResponse,
    PromptVersionResponse,
    PromptVersionCreate,
)
from app.schemas.rule_intelligence import DetectionSemantics
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.policy_generation_service import PolicyGenerationService, ENTERPRISE_SOC_BASELINE_V2
from app.services.policy_quality_validator import PolicyQualityValidator

logger = logging.getLogger("ai_verdict.prompt_studio")

# Versioned, reviewed enterprise SOC baseline protocol (v2.0.0)
COMMON_SOC_BASELINE = ENTERPRISE_SOC_BASELINE_V2


class AgentPolicyEngine:
    """
    Agent Policy Engine (AIS 2.0).
    Manages detection-aware rule-level triage policies, versioning, quality validation,
    and approval governance for the Agentic SOC Intelligence Platform.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_rule_prompt(self, rule_id: str) -> RulePrompt:
        query = select(RulePrompt).where(RulePrompt.rule_id == rule_id).options(
            selectinload(RulePrompt.rule),
            selectinload(RulePrompt.versions)
        )
        res = await self.db.execute(query)
        prompt = res.scalars().first()

        if not prompt:
            rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
            rule = rule_res.scalars().first()
            if not rule:
                raise ValueError(f"SIEM Rule {rule_id} not found")

            prompt = RulePrompt(
                rule_id=rule.id,
                title=f"Investigation Prompt — {rule.name}",
            )
            self.db.add(prompt)
            await self.db.commit()
            await self.db.refresh(prompt)

            # Auto-generate initial template draft
            await self.generate_template_draft(rule_id=rule.id, user_id=None)
            if prompt in self.db:
                self.db.expire(prompt)
            prompt = await self.get_rule_prompt(rule_id)
        elif not prompt.versions or len(prompt.versions) == 0:
            # Self-healing: if rule_prompt exists in database but has no versions, auto-generate initial template draft
            await self.generate_template_draft(rule_id=rule_id, user_id=None)
            if prompt in self.db:
                self.db.expire(prompt)
            prompt = await self.get_rule_prompt(rule_id)

        return prompt

    async def get_rule_prompt(self, rule_id: str) -> Optional[RulePrompt]:
        query = select(RulePrompt).where(RulePrompt.rule_id == rule_id).options(
            selectinload(RulePrompt.rule),
            selectinload(RulePrompt.versions)
        )
        res = await self.db.execute(query)
        return res.scalars().first()

    async def generate_template_draft(
        self,
        rule_id: str,
        user_id: Optional[str] = None,
        authoritative_siem_definition: Optional[Dict[str, Any]] = None,
    ) -> PromptVersion:
        """
        Synthesizes a detection-aware, evidence-grounded rule prompt draft via PolicyGenerationService.
        This is explicitly tagged as a TEMPLATE-GENERATED DRAFT (NOT AI-generated).
        """
        rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_res.scalars().first()
        if not rule:
            raise ValueError(f"Rule with id {rule_id} not found")

        # Get or create rule prompt parent record
        prompt_res = await self.db.execute(
            select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
        )
        rule_prompt = prompt_res.scalars().first()
        if not rule_prompt:
            rule_prompt = RulePrompt(
                rule_id=rule.id,
                title=f"Investigation Prompt — {rule.name}",
            )
            self.db.add(rule_prompt)
            await self.db.flush()

        ver_res = await self.db.execute(select(PromptVersion).where(PromptVersion.prompt_id == rule_prompt.id))
        existing_versions = ver_res.scalars().all()
        next_ver = 1
        if existing_versions:
            next_ver = max(v.version_number for v in existing_versions) + 1

        # Synthesize detection-aware nine-section draft using PolicyGenerationService
        draft_dict = PolicyGenerationService.generate_nine_section_draft(
            rule=rule,
            authoritative_siem_definition=authoritative_siem_definition,
            user_id=user_id,
        )

        new_version = PromptVersion(
            prompt_id=rule_prompt.id,
            version_number=next_ver,
            status="DRAFT",
            is_template_draft=True,
            quality_status=draft_dict["quality_status"],
            common_prompt=draft_dict["common_prompt"],
            rule_specific_prompt=draft_dict["rule_specific_prompt"],
            detection_conditions=draft_dict["detection_conditions"],
            required_evidence=draft_dict["required_evidence"],
            tp_indicators=draft_dict["tp_indicators"],
            fp_indicators=draft_dict["fp_indicators"],
            missing_info_criteria=draft_dict["missing_info_criteria"],
            escalation_conditions=draft_dict["escalation_conditions"],
            analyst_questions=draft_dict["analyst_questions"],
            change_summary=f"TEMPLATE-GENERATED DRAFT: {draft_dict['change_summary']}",
            created_by_user_id=user_id,
        )

        # Execute initial static quality validation
        semantics = RuleIntelligenceAnalyzer.analyze_rule(rule, authoritative_siem_definition)
        classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
        archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
        contract = EvidenceRequirementMapper.map_evidence_contract(
            rule=rule,
            semantics=semantics,
            archetype_def=archetype_def,
            prompt_version=new_version,
        )
        assessment = PolicyQualityValidator.validate_policy_quality(
            rule=rule,
            prompt_version=new_version,
            contract=contract,
            semantics=semantics,
        )

        new_version.quality_score = assessment.quality_score
        new_version.quality_assessment_id = assessment.assessment_id
        if assessment.approval_eligible:
            new_version.quality_status = "APPROVAL_ELIGIBLE"
        elif assessment.blocking_issues:
            new_version.quality_status = "REWORK_REQUIRED"

        self.db.add(new_version)
        await self.db.commit()
        await self.db.refresh(new_version)

        # Persist Rule Intelligence Snapshot
        await self._persist_rule_intelligence_snapshot(rule, semantics, assessment)

        return new_version

    async def create_draft_version(
        self,
        rule_id: str,
        data: PromptVersionCreate,
        user_id: Optional[str] = None
    ) -> PromptVersion:
        rule_prompt = await self.get_or_create_rule_prompt(rule_id)
        rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_res.scalars().first()

        ver_res = await self.db.execute(select(PromptVersion).where(PromptVersion.prompt_id == rule_prompt.id))
        existing_versions = ver_res.scalars().all()
        next_ver = 1
        if existing_versions:
            next_ver = max(v.version_number for v in existing_versions) + 1

        new_ver = PromptVersion(
            prompt_id=rule_prompt.id,
            version_number=next_ver,
            status="DRAFT",
            is_template_draft=False,
            quality_status="GENERATED_DRAFT",
            common_prompt=data.common_prompt or COMMON_SOC_BASELINE.strip(),
            rule_specific_prompt=data.rule_specific_prompt,
            detection_conditions=data.detection_conditions,
            required_evidence=data.required_evidence,
            tp_indicators=data.tp_indicators,
            fp_indicators=data.fp_indicators,
            missing_info_criteria=data.missing_info_criteria,
            escalation_conditions=data.escalation_conditions,
            analyst_questions=data.analyst_questions,
            change_summary=data.change_summary or f"Version {next_ver} manual draft update",
            created_by_user_id=user_id,
        )

        if rule:
            semantics = RuleIntelligenceAnalyzer.analyze_rule(rule)
            classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
            archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
            contract = EvidenceRequirementMapper.map_evidence_contract(
                rule=rule,
                semantics=semantics,
                archetype_def=archetype_def,
                prompt_version=new_ver,
            )
            assessment = PolicyQualityValidator.validate_policy_quality(
                rule=rule,
                prompt_version=new_ver,
                contract=contract,
                semantics=semantics,
            )
            new_ver.quality_score = assessment.quality_score
            new_ver.quality_assessment_id = assessment.assessment_id
            new_ver.quality_status = "APPROVAL_ELIGIBLE" if assessment.approval_eligible else "REWORK_REQUIRED"

        self.db.add(new_ver)
        await self.db.commit()
        await self.db.refresh(new_ver)
        return new_ver

    async def approve_version(
        self,
        rule_id: str,
        version_id: str,
        user_id: Optional[str] = None,
        change_summary: Optional[str] = None
    ) -> PromptVersion:
        """
        REQ-05 / REQ-08: Enhanced Approval Governance Gate.
        Strictly enforces 8 Policy Quality Gates before production approval.
        Blocks approval if any blocking findings exist.
        Binds cryptographic digests of policy, contract, and rule.
        """
        rule_prompt = await self.get_or_create_rule_prompt(rule_id)
        rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_res.scalars().first()
        if not rule:
            raise ValueError(f"SIEM Rule {rule_id} not found")

        ver_res = await self.db.execute(select(PromptVersion).where(PromptVersion.prompt_id == rule_prompt.id))
        all_versions = ver_res.scalars().all()
        target_version = next((v for v in all_versions if v.id == version_id), None)

        if not target_version:
            raise ValueError(f"Prompt version {version_id} not found for rule {rule_id}")

        # Derive semantics and machine-verifiable contract (check snapshot)
        snap_q = select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id == rule.id)
        snap_res = await self.db.execute(snap_q)
        snap = snap_res.scalar_one_or_none()
        auth_def = None
        if snap and snap.definition_status == "VERIFIED" and snap.threshold is not None:
            auth_def = {
                "threshold": snap.threshold,
                "threshold_unit": snap.threshold_unit,
                "aggregation_window": snap.aggregation_window,
            }

        semantics = RuleIntelligenceAnalyzer.analyze_rule(rule, authoritative_siem_definition=auth_def)
        classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
        archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
        contract = EvidenceRequirementMapper.map_evidence_contract(
            rule=rule,
            semantics=semantics,
            archetype_def=archetype_def,
            prompt_version=target_version,
        )

        # Execute Strict Quality Validation
        quality_res = PolicyQualityValidator.validate_policy_quality(
            rule=rule,
            prompt_version=target_version,
            contract=contract,
            semantics=semantics,
        )

        # STRICT QUALITY GATE CHECK
        # Hard gate failure overrides total score
        if not quality_res.approval_eligible:
            blocker_text = "; ".join(quality_res.blocking_issues)
            raise ValueError(
                f"Policy approval rejected by Quality Validation Gates ({len(quality_res.blocking_issues)} blockers): {blocker_text}"
            )

        # Persist Assessment Record
        assessment_record = PolicyQualityAssessmentRecord(
            id=quality_res.assessment_id,
            rule_id=rule.id,
            prompt_version_id=target_version.id,
            version_number=target_version.version_number,
            archetype=quality_res.archetype,
            quality_score=quality_res.quality_score,
            approval_eligible=True,
            simulation_status=quality_res.simulation_status.value,
            score_breakdown=quality_res.score_breakdown,
            gate_results={k: v.model_dump(mode="json") for k, v in quality_res.gate_results.items()},
            blocking_issues=quality_res.blocking_issues,
            warnings=quality_res.warnings,
            missing_evidence_mappings=quality_res.missing_evidence_mappings,
            recommendations=quality_res.recommendations,
            policy_digest=quality_res.policy_digest,
            contract_digest=quality_res.contract_digest,
            rule_digest=quality_res.rule_digest,
            validator_version=quality_res.validator_version,
            evaluated_at=datetime.utcnow(),
        )
        self.db.add(assessment_record)

        # Archive any currently active approved version
        for v in all_versions:
            if v.status == "APPROVED" and v.id != version_id:
                v.status = "ARCHIVED"

        # Atomically activate approved version
        target_version.status = "APPROVED"
        target_version.quality_status = "APPROVED"
        target_version.quality_score = quality_res.quality_score
        target_version.quality_assessment_id = quality_res.assessment_id
        target_version.approved_by_user_id = user_id
        target_version.approved_at = datetime.utcnow()
        if change_summary:
            target_version.change_summary = change_summary

        rule_prompt.active_version_id = target_version.id
        rule_prompt.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(target_version)
        return target_version

    async def rollback_version(
        self,
        rule_id: str,
        target_version_id: str,
        user_id: Optional[str] = None
    ) -> PromptVersion:
        rule_prompt = await self.get_or_create_rule_prompt(rule_id)

        ver_res = await self.db.execute(select(PromptVersion).where(PromptVersion.prompt_id == rule_prompt.id))
        all_versions = ver_res.scalars().all()
        source_version = next((v for v in all_versions if v.id == target_version_id), None)

        if not source_version:
            raise ValueError(f"Target version {target_version_id} not found")

        # Create a new version that clones source_version and approves it
        next_ver = max(v.version_number for v in all_versions) + 1 if all_versions else 1

        rolled_version = PromptVersion(
            prompt_id=rule_prompt.id,
            version_number=next_ver,
            status="APPROVED",
            quality_status="APPROVED",
            quality_score=source_version.quality_score,
            is_template_draft=source_version.is_template_draft,
            common_prompt=source_version.common_prompt,
            rule_specific_prompt=source_version.rule_specific_prompt,
            detection_conditions=source_version.detection_conditions,
            required_evidence=source_version.required_evidence,
            tp_indicators=source_version.tp_indicators,
            fp_indicators=source_version.fp_indicators,
            missing_info_criteria=source_version.missing_info_criteria,
            escalation_conditions=source_version.escalation_conditions,
            analyst_questions=source_version.analyst_questions,
            change_summary=f"Rollback to Version {source_version.version_number}",
            created_by_user_id=user_id,
            approved_by_user_id=user_id,
            approved_at=datetime.utcnow(),
        )

        # Archive others
        for v in all_versions:
            if v.status == "APPROVED":
                v.status = "ARCHIVED"

        self.db.add(rolled_version)
        await self.db.flush()

        rule_prompt.active_version_id = rolled_version.id
        rule_prompt.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(rolled_version)
        return rolled_version

    async def _persist_rule_intelligence_snapshot(
        self,
        rule: Rule,
        semantics: DetectionSemantics,
        assessment: Optional[Any] = None,
    ) -> None:
        """Persists or updates the RuleIntelligenceSnapshot for the rule."""
        q = select(RuleIntelligenceSnapshot).where(RuleIntelligenceSnapshot.rule_id == rule.id)
        res = await self.db.execute(q)
        snap = res.scalar_one_or_none()

        if not snap:
            snap = RuleIntelligenceSnapshot(
                rule_id=rule.id,
                rule_identifier=semantics.rule_identifier,
                primary_archetype=semantics.primary_behavior,
                definition_status=semantics.definition_status.value,
                source_provenance=semantics.source_provenance.value,
                threshold=semantics.threshold,
                threshold_unit=semantics.threshold_unit,
                aggregation_window=semantics.aggregation_window,
                review_required=semantics.review_required,
                semantics_payload=semantics.model_dump(mode="json"),
                rule_digest=assessment.rule_digest if assessment else "",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            self.db.add(snap)
        else:
            snap.primary_archetype = semantics.primary_behavior
            snap.definition_status = semantics.definition_status.value
            snap.source_provenance = semantics.source_provenance.value
            snap.threshold = semantics.threshold
            snap.threshold_unit = semantics.threshold_unit
            snap.aggregation_window = semantics.aggregation_window
            snap.review_required = semantics.review_required
            snap.semantics_payload = semantics.model_dump(mode="json")
            snap.updated_at = datetime.utcnow()

        await self.db.commit()

    def _version_to_dict(self, v: PromptVersion) -> Dict[str, Any]:
        return {
            "version_id": v.id,
            "version_number": v.version_number,
            "status": v.status,
            "quality_status": getattr(v, "quality_status", "GENERATED_DRAFT"),
            "quality_score": getattr(v, "quality_score", None),
            "quality_assessment_id": getattr(v, "quality_assessment_id", None),
            "is_template_draft": v.is_template_draft,
            "common_prompt": v.common_prompt,
            "rule_specific_prompt": v.rule_specific_prompt,
            "detection_conditions": v.detection_conditions,
            "required_evidence": v.required_evidence,
            "tp_indicators": v.tp_indicators,
            "fp_indicators": v.fp_indicators,
            "missing_info_criteria": v.missing_info_criteria,
            "escalation_conditions": v.escalation_conditions,
            "analyst_questions": v.analyst_questions or [],
            "change_summary": v.change_summary,
            "created_by_user_id": v.created_by_user_id,
            "approved_by_user_id": v.approved_by_user_id,
            "approved_at": v.approved_at.isoformat() if v.approved_at else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }

    def _rule_to_export_item(self, rule: Rule, prompt: Optional[RulePrompt]) -> Dict[str, Any]:
        versions = prompt.versions if (prompt and prompt.versions) else []
        active_v = next((v for v in versions if v.id == prompt.active_version_id), None) if prompt else None
        if not active_v and versions:
            active_v = versions[0]

        return {
            "rule_id": rule.id,
            "rule_identifier": rule.rule_id,
            "rule_name": rule.name,
            "event_type": rule.event_type,
            "severity": rule.severity,
            "status": rule.status,
            "data_source": rule.data_source,
            "detection_tech": rule.detection_tech,
            "evaluation_mode": rule.evaluation_mode,
            "description": rule.description,
            "pattern_logic": rule.pattern_logic,
            "remediation": rule.remediation,
            "parsed_metadata": rule.parsed_metadata or {},
            "prompt_metadata": {
                "prompt_id": prompt.id if prompt else None,
                "has_approved_prompt": any(v.status == "APPROVED" for v in versions),
                "total_versions": len(versions),
                "active_version_id": prompt.active_version_id if prompt else None,
                "active_version_number": active_v.version_number if active_v else None,
                "last_updated": (prompt.updated_at if prompt else rule.updated_at).isoformat() if (prompt or rule) else None,
            },
            "active_prompt_configuration": self._version_to_dict(active_v) if active_v else None,
            "all_versions": [self._version_to_dict(v) for v in versions],
        }

    def _format_markdown_report(self, export_items: List[Dict[str, Any]], title: str = "Agent Intelligence Studio — Rule-Wise Prompts & Configurations") -> str:
        lines = [
            f"# {title}",
            "",
            f"- **Generated At:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Total Rules Included:** {len(export_items)}",
            "",
            "---",
            "",
        ]

        for idx, item in enumerate(export_items, start=1):
            rule_name = item.get("rule_name", "Unknown Rule")
            severity = item.get("severity", "MEDIUM")
            lines.append(f"## {idx}. {rule_name} `[{severity}]`")
            lines.append(f"- **Internal Rule ID:** `{item.get('rule_id')}`")
            lines.append(f"- **Event Type:** `{item.get('event_type')}`")
            lines.append(f"- **Data Source:** {item.get('data_source') or 'N/A'}")

            active_cfg = item.get("active_prompt_configuration")
            if active_cfg:
                status_badge = active_cfg.get("status")
                is_template = " (Template Synthesized)" if active_cfg.get("is_template_draft") else " (Manual Draft)"
                lines.append(f"- **Active Baseline:** Version {active_cfg.get('version_number')} `[{status_badge}]`{is_template}")
                lines.append(f"- **Change Summary:** *{active_cfg.get('change_summary') or 'N/A'}*")
                lines.append("")
                lines.append("### 1. COMMON SOC BASELINE PROTOCOL")
                lines.append("```")
                lines.append(active_cfg.get("common_prompt") or "N/A")
                lines.append("```")
                lines.append("")
                lines.append("### 2. RULE-SPECIFIC DIRECTIVE & PATTERN DETAILS")
                lines.append("```")
                lines.append(active_cfg.get("rule_specific_prompt") or "N/A")
                lines.append("```")
                lines.append("")
                lines.append("### 3. DETECTION CONDITIONS & PATTERN LOGIC")
                lines.append(f"> {active_cfg.get('detection_conditions') or 'None specified'}")
                lines.append("")
                lines.append("### 4. MANDATORY EVIDENCE GATHERING CHECKLIST")
                lines.append(active_cfg.get("required_evidence") or "None specified")
                lines.append("")
                lines.append("### 5. TRUE POSITIVE INDICATORS (MALICIOUS ATTACK)")
                lines.append(active_cfg.get("tp_indicators") or "None specified")
                lines.append("")
                lines.append("### 6. FALSE POSITIVE INDICATORS (BENIGN OPERATIONAL NOISE)")
                lines.append(active_cfg.get("fp_indicators") or "None specified")
                lines.append("")
                lines.append("### 7. WHEN TO ABSTAIN (REQUIRES ATTENTION)")
                lines.append(active_cfg.get("missing_info_criteria") or "None specified")
                lines.append("")
                lines.append("### 8. P1/P2 ESCALATION CONDITIONS")
                lines.append(active_cfg.get("escalation_conditions") or "None specified")
                lines.append("")
                lines.append("### 9. TARGETED ANALYST INVESTIGATION QUESTIONS")
                questions = active_cfg.get("analyst_questions") or []
                for q_idx, q in enumerate(questions, start=1):
                    lines.append(f"{q_idx}. {q}")
                lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    async def export_all_rule_prompts(self, format: str = "json") -> Tuple[str, str, str]:
        rules_res = await self.db.execute(select(Rule).order_by(Rule.name.asc()))
        rules = rules_res.scalars().all()

        prompts_res = await self.db.execute(select(RulePrompt).options(selectinload(RulePrompt.versions)))
        prompts_by_rule_id = {rp.rule_id: rp for rp in prompts_res.scalars().all()}

        items = []
        for r in rules:
            rp = prompts_by_rule_id.get(r.id)
            items.append(self._rule_to_export_item(r, rp))

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if format.lower() in ("markdown", "md"):
            md_content = self._format_markdown_report(items)
            return md_content, "text/markdown; charset=utf-8", f"agent_intelligence_studio_rules_prompts_{timestamp}.md"

        export_data = {
            "schema_version": "1.0",
            "title": "Agent Intelligence Studio 2.0 — Rule-Wise Prompts & Configurations",
            "exported_at": datetime.utcnow().isoformat(),
            "total_rules": len(items),
            "rules": items,
        }
        return json.dumps(export_data, indent=2), "application/json", f"agent_intelligence_studio_rules_prompts_{timestamp}.json"

    async def export_single_rule_prompt(self, rule_id: str, format: str = "json") -> Tuple[str, str, str]:
        rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_res.scalars().first()
        if not rule:
            raise ValueError(f"Rule with id {rule_id} not found")

        prompt = await self.get_or_create_rule_prompt(rule_id)
        item = self._rule_to_export_item(rule, prompt)

        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in rule.name.lower())[:40]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if format.lower() in ("markdown", "md"):
            md_content = self._format_markdown_report([item], title=f"Agent Intelligence Policy — {rule.name}")
            return md_content, "text/markdown; charset=utf-8", f"rule_prompt_{safe_name}_{timestamp}.md"

        export_data = {
            "schema_version": "1.0",
            "title": f"Agent Intelligence Policy — {rule.name}",
            "exported_at": datetime.utcnow().isoformat(),
            "rule": item,
        }
        return json.dumps(export_data, indent=2), "application/json", f"rule_prompt_{safe_name}_{timestamp}.json"

    async def compile_active_policy(
        self,
        rule_id: str,
        execution_mode: str = "LIVE",
    ):
        """
        Compiles the active prompt policy for a rule into the unified nine-section format (P3-REQ-01).
        """
        from app.schemas.compiled_policy import CompilationExecutionMode
        from app.services.policy_compiler_service import PolicyCompilerService

        rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_res.scalars().first()
        if not rule:
            raise ValueError(f"Rule with id {rule_id} not found")

        prompt = await self.get_or_create_rule_prompt(rule_id)
        versions = prompt.versions if (prompt and prompt.versions) else []
        active_v = next((v for v in versions if v.id == prompt.active_version_id), None) if prompt else None

        try:
            mode = CompilationExecutionMode(execution_mode.upper())
        except Exception:
            mode = CompilationExecutionMode.LIVE

        return PolicyCompilerService.compile_policy(
            rule=rule,
            prompt_version=active_v,
            execution_mode=mode,
            raise_on_unapproved=False,
        )


# Backward compatibility alias
PromptStudioService = AgentPolicyEngine
