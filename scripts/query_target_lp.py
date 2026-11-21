import asyncio
import sys
import json

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.rule_learning import RuleLearningProfile
from sqlalchemy import select

RULE_UUID = '40498741-ee6b-4a71-9101-0d6d3f77154c'

async def query_target_lp():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(RuleLearningProfile).where(RuleLearningProfile.rule_id == RULE_UUID))
        for p in res.scalars().all():
            print(json.dumps({
                "rule_id": p.rule_id,
                "customer": p.customer,
                "lifecycle_stage": p.lifecycle_stage,
                "active_prompt_version_id": p.active_prompt_version_id,
                "total_incidents_processed": p.total_incidents_processed,
                "total_analyst_reviews": p.total_analyst_reviews,
                "verified_tp_count": p.verified_tp_count,
                "verified_fp_count": p.verified_fp_count,
                "ai_correct_count": p.ai_correct_count,
                "ai_incorrect_count": p.ai_incorrect_count,
                "abstention_count": p.abstention_count,
                "validation_failure_count": p.validation_failure_count,
                "empirical_accuracy": p.empirical_accuracy
            }, indent=2))

if __name__ == '__main__':
    asyncio.run(query_target_lp())
