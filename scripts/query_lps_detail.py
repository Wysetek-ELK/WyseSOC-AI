import asyncio
import sys
import json

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule import Rule
from app.models.rule_learning import RuleLearningProfile
from sqlalchemy import select

RULE_UUID = '40498741-ee6b-4a71-9101-0d6d3f77154c'

async def query_lps():
    async with AsyncSessionLocal() as db:
        all_lp = (await db.execute(select(RuleLearningProfile))).scalars().all()
        print(f"Total RuleLearningProfiles in DB: {len(all_lp)}")
        for p in all_lp:
            print(json.dumps({
                "rule_id": p.rule_id,
                "rule_identifier": p.rule_identifier,
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
                "empirical_accuracy": p.empirical_accuracy,
                "fp_precision": p.fp_precision,
                "tp_recall": p.tp_recall,
                "wilson_lower_bound": p.wilson_lower_bound
            }, indent=2))

if __name__ == '__main__':
    asyncio.run(query_lps())
