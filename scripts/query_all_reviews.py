import asyncio
import sys
import json

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule import Rule
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.rule_learning import RuleLearningProfile
from app.models.incident import Incident
from sqlalchemy import select, func

RULE_UUID = '40498741-ee6b-4a71-9101-0d6d3f77154c'

async def query_all():
    async with AsyncSessionLocal() as db:
        # 1. Total reviews in entire database
        all_revs = (await db.execute(select(AnalystVerdictReview))).scalars().all()
        print(f"Total reviews in whole DB: {len(all_revs)}")
        rules_in_revs = {}
        for r in all_revs:
            rules_in_revs[r.rule_id] = rules_in_revs.get(r.rule_id, 0) + 1
        print(f"Reviews by rule_id: {rules_in_revs}")

        # 2. Check RuleLearningProfile for Heavy TCP
        lp_res = await db.execute(select(RuleLearningProfile).where(RuleLearningProfile.rule_id.in_([RULE_UUID, 'PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT'])))
        lp = lp_res.scalars().first()
        if lp:
            print(f"RuleLearningProfile for Heavy TCP:")
            print(f"  total_reviews: {lp.total_reviews}")
            print(f"  verified_ground_truth_count: {lp.verified_ground_truth_count}")
            print(f"  true_positives: {lp.true_positives}")
            print(f"  false_positives: {lp.false_positives}")
            print(f"  accuracy_score: {lp.accuracy_score}")
            print(f"  active_prompt_version_id: {lp.active_prompt_version_id}")
            print(f"  production_readiness_status: {lp.production_readiness_status}")
        else:
            print("No RuleLearningProfile found for Heavy TCP!")

        # 3. Check all RuleLearningProfiles
        all_lp = (await db.execute(select(RuleLearningProfile))).scalars().all()
        print(f"Total RuleLearningProfiles in DB: {len(all_lp)}")
        for p in all_lp:
            print(f"  LP: rule_id={p.rule_id}, total_reviews={p.total_reviews}, TP={p.true_positives}, FP={p.false_positives}, GT={p.verified_ground_truth_count}")

if __name__ == '__main__':
    asyncio.run(query_all())
