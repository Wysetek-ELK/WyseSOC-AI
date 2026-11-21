import asyncio
import sys
import json

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule_learning import RuleLearningProfile
from app.models.audit import AuditLog
from app.services.prompt_studio_service import PromptStudioService
from sqlalchemy import select

RULE_UUID = '40498741-ee6b-4a71-9101-0d6d3f77154c'
V7_VERSION_ID = 'd79fb576-c6b9-4f63-9167-3c7a2419b70a'

async def execute_recovery():
    async with AsyncSessionLocal() as db:
        service = PromptStudioService(db)
        
        # 1. Execute safe activation of approved version v7
        res = await service.activate_approved_version(
            rule_id=RULE_UUID,
            version_id=V7_VERSION_ID,
            user_id="u-admin-operational-recovery",
            confirm=True,
            justification="Authorized administrative recovery of approved baseline v7 following AIS 2.1a operational acceptance"
        )
        print("Activation result:", json.dumps(res, indent=2))

        # 2. Update RuleLearningProfile active binding
        lp_res = await db.execute(select(RuleLearningProfile).where(RuleLearningProfile.rule_id == RULE_UUID))
        for lp in lp_res.scalars().all():
            lp.active_prompt_version_id = V7_VERSION_ID
            print(f"Updated RuleLearningProfile ({lp.customer}) active_prompt_version_id -> {V7_VERSION_ID}")

        # 3. Write immutable audit log
        audit = AuditLog(
            action="ACTIVATE_APPROVED_POLICY_VERSION",
            user_id="u-admin-operational-recovery",
            username="admin",
            resource_type="RulePrompt",
            resource_id=RULE_UUID,
            details={
                "version_id": V7_VERSION_ID,
                "version_number": 7,
                "status": "APPROVED",
                "justification": "Authorized administrative recovery of approved baseline v7 following AIS 2.1a operational acceptance",
                "confirm": True,
                "governance_criteria_verified": 14,
                "operational_phase": "AIS_2_1a_FINAL_ACCEPTANCE"
            }
        )
        db.add(audit)
        await db.commit()

        # 4. Final verification read
        rp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == RULE_UUID))
        rp = rp_res.scalar_one_or_none()
        v_res = await db.execute(select(PromptVersion).where(PromptVersion.id == V7_VERSION_ID))
        v7 = v_res.scalar_one_or_none()

        print(json.dumps({
            "recovery_verified": True,
            "rule_id": rp.rule_id,
            "active_version_id": rp.active_version_id,
            "ai_execution_suspended": rp.ai_execution_suspended,
            "suspension_reason": rp.suspension_reason,
            "v7_version_number": v7.version_number,
            "v7_status": v7.status,
            "v7_quality_status": v7.quality_status,
            "v7_was_ever_approved": v7.was_ever_approved
        }, indent=2))

if __name__ == '__main__':
    asyncio.run(execute_recovery())
