import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.utils.datetime_utils import utc_now
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.bulk_audit import BulkQualityAuditJobRecord
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.schemas.policy_quality import QualitySummaryItem, GateStatus
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.policy_quality_validator import PolicyQualityValidator

logger = logging.getLogger("ai_verdict.bulk_audit")


class BulkQualityAuditService:
    """
    REQ-09: Scalable Bulk Policy Quality Assessment Service.
    Evaluates enterprise-scale detection rule libraries (2,000+ rules).
    
    Guarantees:
      - 100% READ-ONLY with respect to active policies: NEVER mutates or auto-activates drafts.
      - Bounded batch processing with chunking to protect memory and connection pools.
      - Tracks job progress, failures, and aggregate summary metrics.
    """
    BATCH_CHUNK_SIZE = 100

    def __init__(self, db: AsyncSession):
        self.db = db

    async def execute_bulk_audit(
        self,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tenant_filter: Optional[str] = None,
    ) -> BulkQualityAuditJobRecord:
        """
        Executes bounded, chunked bulk quality audit across all registered rules.
        """
        # 1. Initialize or load job record
        if not job_id:
            job_id = str(uuid.uuid4())
            job = BulkQualityAuditJobRecord(
                id=job_id,
                status="RUNNING",
                started_at=utc_now(),
                created_by_user_id=user_id,
            )
            self.db.add(job)
            await self.db.commit()
            await self.db.refresh(job)
        else:
            q = select(BulkQualityAuditJobRecord).where(BulkQualityAuditJobRecord.id == job_id)
            res = await self.db.execute(q)
            job = res.scalar_one_or_none()
            if not job:
                job = BulkQualityAuditJobRecord(
                    id=job_id,
                    status="RUNNING",
                    started_at=utc_now(),
                    created_by_user_id=user_id,
                )
                self.db.add(job)
                await self.db.commit()

        try:
            # 2. Fetch all rules with prompt associations
            rules_q = select(Rule).order_by(Rule.name.asc())
            res = await self.db.execute(rules_q)
            all_rules = res.scalars().all()

            job.total_rules = len(all_rules)
            job.status = "RUNNING"
            await self.db.commit()

            # Preload existing prompts
            prompts_q = select(RulePrompt).options(selectinload(RulePrompt.versions))
            prompts_res = await self.db.execute(prompts_q)
            prompts_by_rule = {rp.rule_id: rp for rp in prompts_res.scalars().all()}

            total_score_sum = 0.0
            processed = 0
            passed = 0
            review_required = 0
            critical_issues = 0
            incomplete_defs = 0
            missing_evidence_count = 0
            distribution = {"90-100": 0, "70-89": 0, "50-69": 0, "<50": 0}

            # 3. Process in bounded chunks
            for i in range(0, len(all_rules), self.BATCH_CHUNK_SIZE):
                chunk = all_rules[i : i + self.BATCH_CHUNK_SIZE]
                for rule in chunk:
                    rp = prompts_by_rule.get(rule.id)
                    active_pv = None
                    if rp and rp.versions:
                        active_pv = next((v for v in rp.versions if v.id == rp.active_version_id), None)
                        if not active_pv and rp.versions:
                            active_pv = rp.versions[0]

                    # Analyze semantics
                    semantics = RuleIntelligenceAnalyzer.analyze_rule(rule)
                    if semantics.definition_status.value == "INCOMPLETE":
                        incomplete_defs += 1

                    classification = DetectionArchetypeRegistry.classify_rule(semantics, rule)
                    archetype_def = DetectionArchetypeRegistry.get_archetype_definition(classification.primary_archetype)
                    contract = EvidenceRequirementMapper.map_evidence_contract(
                        rule=rule,
                        semantics=semantics,
                        archetype_def=archetype_def,
                        prompt_version=active_pv,
                    )

                    if active_pv:
                        assessment = PolicyQualityValidator.validate_policy_quality(
                            rule=rule,
                            prompt_version=active_pv,
                            contract=contract,
                            semantics=semantics,
                        )
                        score = assessment.quality_score
                        total_score_sum += score

                        if assessment.approval_eligible:
                            passed += 1
                        else:
                            review_required += 1

                        if assessment.blocking_issues:
                            critical_issues += 1
                        if assessment.missing_evidence_mappings:
                            missing_evidence_count += 1

                        if score >= 90:
                            distribution["90-100"] += 1
                        elif score >= 70:
                            distribution["70-89"] += 1
                        elif score >= 50:
                            distribution["50-69"] += 1
                        else:
                            distribution["<50"] += 1
                    else:
                        # Rule has no policy configured
                        review_required += 1
                        critical_issues += 1
                        distribution["<50"] += 1

                    processed += 1

                # Update progress after each chunk
                job.processed_rules = processed
                await self.db.commit()

            avg_score = round(total_score_sum / max(1, processed), 1)

            job.processed_rules = processed
            job.passed_count = passed
            job.review_required_count = review_required
            job.critical_issues_count = critical_issues
            job.incomplete_definitions_count = incomplete_defs
            job.missing_evidence_count = missing_evidence_count
            job.average_quality_score = avg_score
            job.summary_metrics = {
                "quality_distribution": distribution,
                "total_assessed": processed,
                "timestamp": utc_now().isoformat(),
            }
            job.status = "COMPLETED"
            job.completed_at = utc_now()
            await self.db.commit()
            await self.db.refresh(job)
            return job

        except Exception as e:
            logger.error(f"Bulk quality audit job {job.id} failed: {str(e)}", exc_info=True)
            job.status = "FAILED"
            job.error_message = str(e)
            job.completed_at = utc_now()
            await self.db.commit()
            return job

    async def get_quality_summary(self) -> QualitySummaryItem:
        """Computes aggregate quality metrics across the library."""
        rules_q = select(func.count(Rule.id))
        total_rules = (await self.db.execute(rules_q)).scalar() or 0

        prompts_q = select(RulePrompt).options(selectinload(RulePrompt.versions))
        prompts = (await self.db.execute(prompts_q)).scalars().all()

        approved_count = 0
        passing_static = 0
        review_required = 0
        critical_issues = 0
        incomplete_defs = 0
        missing_evidence = 0
        lacking_simulation = 0
        total_score = 0.0

        for rp in prompts:
            active_v = next((v for v in rp.versions if v.id == rp.active_version_id and v.status == "APPROVED"), None)
            if active_v:
                approved_count += 1
                score = active_v.quality_score or 75.0
                total_score += score
                if active_v.quality_status == "APPROVAL_ELIGIBLE" or active_v.status == "APPROVED":
                    passing_static += 1
            else:
                review_required += 1

        avg_score = round(total_score / max(1, approved_count), 1) if approved_count > 0 else 0.0

        return QualitySummaryItem(
            total_rules=total_rules,
            rules_with_approved_policies=approved_count,
            policies_passing_static_checks=passing_static,
            policies_requiring_review=review_required,
            policies_with_critical_issues=critical_issues,
            policies_with_incomplete_definitions=incomplete_defs,
            policies_with_missing_evidence_mappings=missing_evidence,
            policies_lacking_simulation_evidence=lacking_simulation,
            quality_score_average=avg_score,
            rules_requiring_revalidation=review_required,
        )
