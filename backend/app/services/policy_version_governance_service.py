import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.utils.datetime_utils import utc_now
from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule_learning import RuleLearningProfile
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.pilot import PilotEvaluationRecord
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord
from app.models.dry_run import DryRunConfig
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.policy_drift import PolicyDriftEvent
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.prompt import (
    PolicyVersionHistoryItem,
    VersionDeletionPreviewResponse,
    BulkVersionDeleteResponse,
)

logger = logging.getLogger("ai_verdict.policy_version_governance")


class PolicyVersionGovernanceService:
    """
    Authoritative Policy Version Governance Service for AIS 2.0.
    Enforces strict referential-integrity, provenance preservation, and RBAC controls:
      - Active Approved/Draft versions: Permanent deletion & archiving strictly prohibited.
      - Approved Historical versions: Physical deletion prohibited; reversible archival permitted.
      - Referenced versions: Never deleted while linked to inference, simulations, or benchmarks.
      - Eligible Obsolete Drafts: Server-side preview, validation, typed confirmation, and audit logs.
    """

    @classmethod
    async def get_version_history(
        cls,
        db: AsyncSession,
        rule_identifier: str,
    ) -> List[PolicyVersionHistoryItem]:
        from app.services.policy_governance import resolve_canonical_rule

        rule = await resolve_canonical_rule(db, rule_identifier)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Detection rule '{rule_identifier}' not found")

        prompt_res = await db.execute(
            select(RulePrompt)
            .where(RulePrompt.rule_id == rule.id)
            .options(selectinload(RulePrompt.versions))
        )
        rule_prompt = prompt_res.scalars().first()
        if not rule_prompt or not rule_prompt.versions:
            return []

        # Sort versions by version_number descending
        sorted_versions = sorted(rule_prompt.versions, key=lambda v: v.version_number, reverse=True)

        items: List[PolicyVersionHistoryItem] = []
        for version in sorted_versions:
            dep_info = await cls.check_version_dependencies(db, rule, version, rule_prompt)
            items.append(
                PolicyVersionHistoryItem(
                    id=version.id,
                    prompt_id=version.prompt_id,
                    version_number=version.version_number,
                    status=version.status,
                    previous_status=version.previous_status,
                    quality_status=version.quality_status or "GENERATED_DRAFT",
                    quality_score=version.quality_score,
                    change_summary=version.change_summary or "",
                    is_active=dep_info["is_active"],
                    is_eligible_for_deletion=dep_info["is_eligible_for_deletion"],
                    is_eligible_for_archive=dep_info["is_eligible_for_archive"],
                    blocking_reasons=dep_info["blocking_reasons"],
                    dependency_counts=dep_info["dependency_counts"],
                    usage_label=dep_info["usage_label"],
                    created_at=version.created_at,
                    approved_at=version.approved_at,
                    archived_at=getattr(version, "archived_at", None),
                    archival_reason=getattr(version, "archival_reason", None),
                )
            )

        return items

    @classmethod
    async def is_version_ever_approved(
        cls,
        db: AsyncSession,
        version: PromptVersion,
    ) -> bool:
        """
        Authoritative provenance check to determine whether a policy version has ever been approved.
        A version that has ever been approved must NEVER become eligible for physical deletion.
        """
        # 1. Authoritative model column flags
        if getattr(version, "was_ever_approved", False):
            return True
        if version.status == "APPROVED":
            return True
        if getattr(version, "previous_status", None) == "APPROVED":
            return True
        if version.approved_at is not None:
            return True
        if version.approved_by_user_id is not None:
            return True

        # 2. Immutable audit trail verification
        try:
            version_id_str = str(version.id)
            audit_stmt = select(func.count(AuditLog.id)).where(
                AuditLog.resource_id == version_id_str,
                AuditLog.action.in_([
                    "POLICY_APPROVE",
                    "POLICY_VERSION_APPROVE",
                    "PROMPT_VERSION_APPROVED",
                    "POLICY_VERSION_APPROVED",
                ]),
            )
            audit_count = (await db.execute(audit_stmt)).scalar() or 0
            if audit_count > 0:
                return True
        except Exception as exc:
            logger.warning(f"Audit log approval provenance check error for version {version.id}: {exc}")
            # Fail-safe: if provenance cannot be determined due to DB error, protect the version
            return True

        return False

    @classmethod
    async def check_version_dependencies(
        cls,
        db: AsyncSession,
        rule: Rule,
        version: PromptVersion,
        rule_prompt: RulePrompt,
    ) -> Dict[str, Any]:
        """
        Inspects foreign-key and soft string dependencies across all subsystems.
        """
        version_id_str = str(version.id)
        blocking_reasons: List[str] = []
        dep_counts: Dict[str, int] = {}

        # 1. Active Version Check (RulePrompt & RuleLearningProfile)
        is_active = (rule_prompt.active_version_id == version_id_str)
        if not is_active:
            # Check learning profile active version binding
            lp_res = await db.execute(
                select(RuleLearningProfile).where(
                    RuleLearningProfile.rule_id.in_([rule.id, rule.rule_id]),
                    RuleLearningProfile.active_prompt_version_id == version_id_str,
                )
            )
            if lp_res.scalars().first():
                is_active = True

        if is_active:
            blocking_reasons.append("Active policy version is currently bound to production/pilot execution.")

        # 2. Authoritative Ever-Approved Check (Immutable historical baselines)
        is_ever_approved = await cls.is_version_ever_approved(db, version)
        if is_ever_approved:
            blocking_reasons.append("Historical approved policy version: Approved policies are permanently immutable to preserve regulatory sign-off and audit trails.")

        # 3. Actual Outbound LLM Prompt Captures (Inference Provenance)
        captures_count_res = await db.execute(
            select(func.count(ActualLLMPromptCapture.id)).where(
                ActualLLMPromptCapture.policy_version_id == version_id_str
            )
        )
        captures_count = captures_count_res.scalar() or 0
        dep_counts["actual_prompt_captures"] = captures_count
        if captures_count > 0:
            blocking_reasons.append(f"Referenced by {captures_count} outbound LLM inference captures (immutable provenance).")

        # 4. Pilot Verdicts
        pilot_count_res = await db.execute(
            select(func.count(PilotEvaluationRecord.id)).where(
                PilotEvaluationRecord.policy_version_id == version_id_str
            )
        )
        pilot_count = pilot_count_res.scalar() or 0
        dep_counts["pilot_verdicts"] = pilot_count
        if pilot_count > 0:
            blocking_reasons.append(f"Referenced by {pilot_count} pilot verdict records.")

        # 5. Historical Evaluation Runs (G8 Benchmarks)
        eval_count_res = await db.execute(
            select(func.count(HistoricalEvaluationRunRecord.id)).where(
                HistoricalEvaluationRunRecord.policy_version_id == version_id_str
            )
        )
        eval_count = eval_count_res.scalar() or 0
        dep_counts["historical_evaluation_runs"] = eval_count
        if eval_count > 0:
            blocking_reasons.append(f"Referenced by {eval_count} historical evaluation benchmark runs.")

        # 6. Dry Run Configs
        dry_run_count_res = await db.execute(
            select(func.count(DryRunConfig.id)).where(
                DryRunConfig.prompt_version_id == version_id_str
            )
        )
        dry_run_count = dry_run_count_res.scalar() or 0
        dep_counts["dry_run_configs"] = dry_run_count
        if dry_run_count > 0:
            blocking_reasons.append(f"Referenced by {dry_run_count} dry run simulation configurations.")

        # 7. Quality Assessments (Draft assessments may be deleted along with an unreferenced draft)
        qa_count_res = await db.execute(
            select(func.count(PolicyQualityAssessmentRecord.id)).where(
                PolicyQualityAssessmentRecord.prompt_version_id == version_id_str
            )
        )
        qa_count = qa_count_res.scalar() or 0
        dep_counts["quality_assessments"] = qa_count

        # 8. Policy Drift Events
        drift_count_res = await db.execute(
            select(func.count(PolicyDriftEvent.id)).where(
                PolicyDriftEvent.prompt_version_id == version_id_str
            )
        )
        drift_count = drift_count_res.scalar() or 0
        dep_counts["policy_drift_events"] = drift_count

        # Eligibility determination: permanently prohibited if active, ever approved, or referenced
        is_eligible_for_archive = not is_active and version.status != "ARCHIVED"
        is_eligible_for_deletion = (
            not is_active
            and not is_ever_approved
            and captures_count == 0
            and pilot_count == 0
            and eval_count == 0
            and dry_run_count == 0
            and drift_count == 0
        )

        # Derive usage label
        if is_active:
            usage_label = f"Active {version.status.title()}"
        elif is_ever_approved:
            usage_label = "Approved Historical (Permanently Protected)"
        elif captures_count > 0 or pilot_count > 0 or eval_count > 0 or dry_run_count > 0:
            ref_total = captures_count + pilot_count + eval_count + dry_run_count
            usage_label = f"Referenced ({ref_total} execution records)"
        elif version.status == "ARCHIVED":
            usage_label = "Archived Draft (Eligible for Delete)"
        else:
            usage_label = "Unreferenced Draft (Eligible for Delete)"

        return {
            "is_active": is_active,
            "is_approved": is_ever_approved,
            "is_eligible_for_archive": is_eligible_for_archive,
            "is_eligible_for_deletion": is_eligible_for_deletion,
            "blocking_reasons": blocking_reasons,
            "dependency_counts": dep_counts,
            "usage_label": usage_label,
        }

    @classmethod
    async def get_deletion_preview(
        cls,
        db: AsyncSession,
        rule_identifier: str,
        version_id: str,
    ) -> VersionDeletionPreviewResponse:
        from app.services.policy_governance import resolve_canonical_rule

        rule = await resolve_canonical_rule(db, rule_identifier)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Detection rule '{rule_identifier}' not found")

        prompt_res = await db.execute(
            select(RulePrompt)
            .where(RulePrompt.rule_id == rule.id)
            .options(selectinload(RulePrompt.versions))
        )
        rule_prompt = prompt_res.scalars().first()
        if not rule_prompt:
            raise HTTPException(status_code=404, detail="Rule prompt definition not found")

        target_version = next((v for v in rule_prompt.versions if v.id == version_id), None)
        if not target_version:
            raise HTTPException(status_code=404, detail=f"Policy version '{version_id}' not found")

        dep_info = await cls.check_version_dependencies(db, rule, target_version, rule_prompt)

        # Records that would be deleted (the version row + associated draft assessments)
        records_affected = 1 + dep_info["dependency_counts"].get("quality_assessments", 0)

        warning_message = ""
        if not dep_info["is_eligible_for_deletion"]:
            warning_message = "This policy version is PROTECTED from deletion: " + " ".join(dep_info["blocking_reasons"])
        else:
            warning_message = f"Permanent deletion will remove version v{target_version.version_number} and its draft quality assessments. This operation is IRREVERSIBLE."

        return VersionDeletionPreviewResponse(
            rule_id=rule.id,
            rule_name=rule.name,
            version_id=target_version.id,
            version_number=target_version.version_number,
            status=target_version.status,
            is_active=dep_info["is_active"],
            is_eligible=dep_info["is_eligible_for_deletion"],
            blocking_reasons=dep_info["blocking_reasons"],
            dependency_counts=dep_info["dependency_counts"],
            records_affected=records_affected,
            is_reversible=False,
            warning_message=warning_message,
        )

    @classmethod
    async def delete_version(
        cls,
        db: AsyncSession,
        rule_identifier: str,
        version_id: str,
        current_user: User,
        justification: str = "Administrative cleanup of obsolete draft",
    ) -> Dict[str, Any]:
        from app.services.policy_governance import resolve_canonical_rule

        rule = await resolve_canonical_rule(db, rule_identifier)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Detection rule '{rule_identifier}' not found")

        prompt_res = await db.execute(
            select(RulePrompt)
            .where(RulePrompt.rule_id == rule.id)
            .options(selectinload(RulePrompt.versions))
        )
        rule_prompt = prompt_res.scalars().first()
        if not rule_prompt:
            raise HTTPException(status_code=404, detail="Rule prompt definition not found")

        target_version = next((v for v in rule_prompt.versions if v.id == version_id), None)
        if not target_version:
            raise HTTPException(status_code=404, detail=f"Policy version '{version_id}' not found")

        # Explicit lock on the PromptVersion row in PostgreSQL to prevent race conditions with concurrent approval
        try:
            bind = db.get_bind()
            if bind and bind.dialect.name == "postgresql":
                await db.execute(
                    select(PromptVersion.id)
                    .where(PromptVersion.id == version_id)
                    .with_for_update()
                )
        except Exception as lock_err:
            logger.debug(f"Row locking skipped/handled: {lock_err}")

        # Explicit invariant check: never allow deletion of any version that was ever approved
        is_ever_approved = await cls.is_version_ever_approved(db, target_version)
        if is_ever_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version v{target_version.version_number} has been historically approved and is permanently immutable. It cannot be deleted.",
            )

        dep_info = await cls.check_version_dependencies(db, rule, target_version, rule_prompt)
        if not dep_info["is_eligible_for_deletion"]:
            reasons = "; ".join(dep_info["blocking_reasons"])
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version v{target_version.version_number} cannot be deleted: {reasons}",
            )

        v_num = target_version.version_number
        prev_status = target_version.status

        # 1. Safely remove associated draft quality assessments
        await db.execute(
            delete(PolicyQualityAssessmentRecord).where(
                PolicyQualityAssessmentRecord.prompt_version_id == target_version.id
            )
        )

        # 2. Delete the version record
        await db.delete(target_version)

        # 3. Create immutable audit record
        audit = AuditLog(
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else "admin",
            action="POLICY_VERSION_DELETE",
            resource_type="POLICY_VERSION",
            resource_id=version_id,
            details={
                "rule_id": rule.id,
                "rule_identifier": rule.rule_id,
                "rule_name": rule.name,
                "version_number": v_num,
                "previous_status": prev_status,
                "justification": justification,
                "deleted_at": utc_now().isoformat(),
            },
        )
        db.add(audit)
        await db.commit()

        logger.info(
            f"Policy version v{v_num} (id={version_id}) of rule {rule.rule_id} safely deleted by {current_user.username}"
        )

        return {
            "success": True,
            "deleted_version_id": version_id,
            "deleted_version_number": v_num,
            "rule_id": rule.id,
            "message": f"Successfully deleted policy version v{v_num} for rule '{rule.name}'.",
        }

    @classmethod
    async def archive_version(
        cls,
        db: AsyncSession,
        rule_identifier: str,
        version_id: str,
        current_user: User,
        reason: str = "Archived by SOC Administrator",
    ) -> PromptVersion:
        from app.services.policy_governance import resolve_canonical_rule

        rule = await resolve_canonical_rule(db, rule_identifier)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Detection rule '{rule_identifier}' not found")

        prompt_res = await db.execute(
            select(RulePrompt)
            .where(RulePrompt.rule_id == rule.id)
            .options(selectinload(RulePrompt.versions))
        )
        rule_prompt = prompt_res.scalars().first()
        if not rule_prompt:
            raise HTTPException(status_code=404, detail="Rule prompt definition not found")

        target_version = next((v for v in rule_prompt.versions if v.id == version_id), None)
        if not target_version:
            raise HTTPException(status_code=404, detail=f"Policy version '{version_id}' not found")

        if rule_prompt.active_version_id == str(target_version.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version v{target_version.version_number} is currently ACTIVE. An active policy cannot be archived.",
            )

        if target_version.status == "ARCHIVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version v{target_version.version_number} is already archived.",
            )

        is_ever_approved = await cls.is_version_ever_approved(db, target_version)
        if is_ever_approved:
            target_version.was_ever_approved = True
            target_version.previous_status = "APPROVED"
        else:
            target_version.previous_status = target_version.status
        target_version.status = "ARCHIVED"
        target_version.archived_at = utc_now()
        target_version.archived_by_user_id = current_user.id if current_user else None
        target_version.archival_reason = reason

        audit = AuditLog(
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else "admin",
            action="POLICY_VERSION_ARCHIVE",
            resource_type="POLICY_VERSION",
            resource_id=version_id,
            details={
                "rule_id": rule.id,
                "rule_identifier": rule.rule_id,
                "rule_name": rule.name,
                "version_number": target_version.version_number,
                "previous_status": target_version.previous_status,
                "archival_reason": reason,
                "archived_at": utc_now().isoformat(),
            },
        )
        db.add(audit)
        await db.commit()
        await db.refresh(target_version)

        return target_version

    @classmethod
    async def restore_version(
        cls,
        db: AsyncSession,
        rule_identifier: str,
        version_id: str,
        current_user: User,
    ) -> PromptVersion:
        from app.services.policy_governance import resolve_canonical_rule

        rule = await resolve_canonical_rule(db, rule_identifier)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Detection rule '{rule_identifier}' not found")

        prompt_res = await db.execute(
            select(RulePrompt)
            .where(RulePrompt.rule_id == rule.id)
            .options(selectinload(RulePrompt.versions))
        )
        rule_prompt = prompt_res.scalars().first()
        if not rule_prompt:
            raise HTTPException(status_code=404, detail="Rule prompt definition not found")

        target_version = next((v for v in rule_prompt.versions if v.id == version_id), None)
        if not target_version:
            raise HTTPException(status_code=404, detail=f"Policy version '{version_id}' not found")

        if target_version.status != "ARCHIVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version v{target_version.version_number} is not archived (current status: {target_version.status}).",
            )

        is_ever_approved = await cls.is_version_ever_approved(db, target_version)
        if is_ever_approved:
            # Under NO circumstance may a historically approved policy version be restored to DRAFT!
            # It must be restored to its immutable APPROVED status as an inactive historical approved baseline.
            restored_status = "APPROVED"
            target_version.was_ever_approved = True
            target_version.previous_status = "APPROVED"
        else:
            restored_status = target_version.previous_status or "DRAFT"

        target_version.status = restored_status
        target_version.archived_at = None
        target_version.archived_by_user_id = None
        target_version.archival_reason = None

        audit = AuditLog(
            user_id=current_user.id if current_user else None,
            username=current_user.username if current_user else "admin",
            action="POLICY_VERSION_RESTORE",
            resource_type="POLICY_VERSION",
            resource_id=version_id,
            details={
                "rule_id": rule.id,
                "rule_identifier": rule.rule_id,
                "rule_name": rule.name,
                "version_number": target_version.version_number,
                "restored_status": restored_status,
                "restored_at": utc_now().isoformat(),
            },
        )
        db.add(audit)
        await db.commit()
        await db.refresh(target_version)

        return target_version

    @classmethod
    async def bulk_delete_versions(
        cls,
        db: AsyncSession,
        rule_identifier: str,
        version_ids: List[str],
        current_user: User,
        justification: str = "Bulk administrative cleanup of obsolete drafts",
    ) -> BulkVersionDeleteResponse:
        from app.services.policy_governance import resolve_canonical_rule

        rule = await resolve_canonical_rule(db, rule_identifier)
        if not rule:
            raise HTTPException(status_code=404, detail=f"Detection rule '{rule_identifier}' not found")

        prompt_res = await db.execute(
            select(RulePrompt)
            .where(RulePrompt.rule_id == rule.id)
            .options(selectinload(RulePrompt.versions))
        )
        rule_prompt = prompt_res.scalars().first()
        if not rule_prompt:
            raise HTTPException(status_code=404, detail="Rule prompt definition not found")

        selected_count = len(version_ids)
        deleted_vnums: List[int] = []
        protected_items: List[Dict[str, Any]] = []

        for vid in version_ids:
            target_version = next((v for v in rule_prompt.versions if v.id == vid), None)
            if not target_version:
                continue

            # Invariant check: Historically approved versions are permanently protected
            is_ever_approved = await cls.is_version_ever_approved(db, target_version)
            if is_ever_approved:
                protected_items.append({
                    "version_id": target_version.id,
                    "version_number": target_version.version_number,
                    "status": target_version.status,
                    "blocking_reasons": ["Historical approved policy: Approved policies are permanently immutable to preserve regulatory sign-off."],
                })
                continue

            dep_info = await cls.check_version_dependencies(db, rule, target_version, rule_prompt)
            if not dep_info["is_eligible_for_deletion"]:
                protected_items.append({
                    "version_id": target_version.id,
                    "version_number": target_version.version_number,
                    "status": target_version.status,
                    "blocking_reasons": dep_info["blocking_reasons"],
                })
                continue

            # Eligible -> delete safely
            v_num = target_version.version_number
            await db.execute(
                delete(PolicyQualityAssessmentRecord).where(
                    PolicyQualityAssessmentRecord.prompt_version_id == target_version.id
                )
            )
            await db.delete(target_version)
            deleted_vnums.append(v_num)

        deleted_count = len(deleted_vnums)
        protected_count = len(protected_items)
        eligible_count = deleted_count

        if deleted_count > 0:
            audit = AuditLog(
                user_id=current_user.id if current_user else None,
                username=current_user.username if current_user else "admin",
                action="POLICY_VERSION_BULK_DELETE",
                resource_type="POLICY_VERSION",
                resource_id=rule.id,
                details={
                    "rule_id": rule.id,
                    "rule_identifier": rule.rule_id,
                    "rule_name": rule.name,
                    "deleted_version_numbers": deleted_vnums,
                    "protected_count": protected_count,
                    "justification": justification,
                    "deleted_at": utc_now().isoformat(),
                },
            )
            db.add(audit)
            await db.commit()

        return BulkVersionDeleteResponse(
            selected_count=selected_count,
            eligible_count=eligible_count,
            deleted_count=deleted_count,
            protected_count=protected_count,
            deleted_version_numbers=deleted_vnums,
            protected_items=protected_items,
        )
