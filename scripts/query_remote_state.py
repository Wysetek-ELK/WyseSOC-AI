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
from sqlalchemy import select, func

RULE_UUID = '40498741-ee6b-4a71-9101-0d6d3f77154c'
UNRELATED_RULE_UUID = '7bd13e89-0828-48e6-8cf5-f3cbf12d438c'

async def query_state():
    async with AsyncSessionLocal() as db:
        # 1. Target Rule Prompt State
        rp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == RULE_UUID))
        rp = rp_res.scalar_one_or_none()
        rp_info = {
            'id': rp.id if rp else None,
            'rule_id': rp.rule_id if rp else None,
            'active_version_id': rp.active_version_id if rp else None,
            'ai_execution_suspended': rp.ai_execution_suspended if rp else None,
            'suspension_reason': rp.suspension_reason if rp else None
        } if rp else None

        # 2. Prompt Versions for target rule
        versions = []
        if rp:
            v_res = await db.execute(select(PromptVersion).where(PromptVersion.prompt_id == rp.id).order_by(PromptVersion.version_number.desc()))
            for v in v_res.scalars().all():
                versions.append({
                    'id': v.id,
                    'version_number': v.version_number,
                    'status': v.status,
                    'quality_status': v.quality_status,
                    'quality_score': v.quality_score,
                    'was_ever_approved': v.was_ever_approved,
                    'approved_at': str(v.approved_at) if v.approved_at else None,
                    'revoked_at': str(v.revoked_at) if v.revoked_at else None,
                    'archived_at': str(v.archived_at) if v.archived_at else None
                })

        # 3. Unrelated Rule check
        urp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == UNRELATED_RULE_UUID))
        urp = urp_res.scalar_one_or_none()
        urp_info = {
            'rule_id': urp.rule_id if urp else None,
            'active_version_id': urp.active_version_id if urp else None,
            'ai_execution_suspended': urp.ai_execution_suspended if urp else None
        } if urp else None

        # 4. Analyst Reviews & Ground Truth for target rule
        rev_stmt = select(AnalystVerdictReview).join(Incident, AnalystVerdictReview.incident_id == Incident.id).where(Incident.rule_id == RULE_UUID)
        revs = (await db.execute(rev_stmt)).scalars().all()
        review_summary = {
            'total_reviews': len(revs),
            'tp_count': sum(1 for r in revs if (r.final_verdict or r.verdict) == 'TRUE_POSITIVE'),
            'fp_count': sum(1 for r in revs if (r.final_verdict or r.verdict) == 'FALSE_POSITIVE'),
            'other_count': sum(1 for r in revs if (r.final_verdict or r.verdict) not in ('TRUE_POSITIVE', 'FALSE_POSITIVE')),
            'reviews_by_customer': {}
        }
        for r in revs:
            cust = getattr(r, 'customer', 'UNKNOWN') or 'UNKNOWN'
            review_summary['reviews_by_customer'][cust] = review_summary['reviews_by_customer'].get(cust, 0) + 1

        # 5. Outbound prompt captures
        cap_stmt = select(func.count(ActualLLMPromptCapture.id)).where(ActualLLMPromptCapture.rule_id == RULE_UUID)
        cap_count = (await db.execute(cap_stmt)).scalar() or 0

        print(json.dumps({
            'target_rule_prompt': rp_info,
            'target_rule_versions': versions,
            'unrelated_rule_prompt': urp_info,
            'review_summary': review_summary,
            'captures_count': cap_count
        }, indent=2))

if __name__ == '__main__':
    asyncio.run(query_state())
