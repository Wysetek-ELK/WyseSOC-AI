import asyncio
import sys
import json

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule import Rule
from app.models.analyst_feedback import AnalystVerdictReview
from app.models.incident import Incident
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from sqlalchemy import select, func, or_

RULE_UUID = '40498741-ee6b-4a71-9101-0d6d3f77154c'
RULE_EVENT_TYPE = 'PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT'

async def query_reviews():
    async with AsyncSessionLocal() as db:
        # Check rule
        r_res = await db.execute(select(Rule).where(or_(Rule.id == RULE_UUID, Rule.rule_id == RULE_EVENT_TYPE)))
        rule = r_res.scalar_one_or_none()
        print(f"Rule: id={rule.id}, rule_id={rule.rule_id}, name={rule.name}")

        # Check incidents for this rule
        inc_stmt = select(Incident).where(or_(Incident.rule_id == RULE_UUID, Incident.rule_id == RULE_EVENT_TYPE, Incident.rule_id == rule.id, Incident.rule_id == rule.rule_id))
        incidents = (await db.execute(inc_stmt)).scalars().all()
        print(f"Total Incidents for rule: {len(incidents)}")
        inc_ids = [inc.id for inc in incidents]
        customers = {}
        for inc in incidents:
            c = getattr(inc, 'customer', 'UNKNOWN') or 'UNKNOWN'
            customers[c] = customers.get(c, 0) + 1
        print(f"Incidents by customer: {customers}")

        # Check AnalystVerdictReview records matching rule_id or incident_id
        rev_stmt = select(AnalystVerdictReview).where(
            or_(
                AnalystVerdictReview.rule_id.in_([RULE_UUID, RULE_EVENT_TYPE, rule.id, rule.rule_id]),
                AnalystVerdictReview.incident_id.in_(inc_ids) if inc_ids else False
            )
        )
        reviews = (await db.execute(rev_stmt)).scalars().all()
        print(f"Total Analyst Verdict Reviews found: {len(reviews)}")

        tp = 0
        fp = 0
        other = 0
        for r in reviews:
            v = r.analyst_verdict
            if v == 'TRUE_POSITIVE':
                tp += 1
            elif v == 'FALSE_POSITIVE':
                fp += 1
            else:
                other += 1

        print(f"Breakdown: TP={tp}, FP={fp}, Other/Insufficient={other}")
        ground_truth_statuses = {}
        for r in reviews:
            gt = r.ground_truth_status
            ground_truth_statuses[gt] = ground_truth_statuses.get(gt, 0) + 1
        print(f"Ground Truth Statuses: {ground_truth_statuses}")

if __name__ == '__main__':
    asyncio.run(query_reviews())
