import sys
import asyncio
from app.database import AsyncSessionLocal
from app.models.prompt import RulePrompt
from app.models.production_governance import ProductionAutomationPolicy
from sqlalchemy import select

async def main(enable: bool):
    async with AsyncSessionLocal() as db:
        p_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == '40498741-ee6b-4a71-9101-0d6d3f77154c'))
        p = p_res.scalar_one_or_none()
        if p:
            p.ai_execution_suspended = not enable

        pols_res = await db.execute(select(ProductionAutomationPolicy).where(
            ProductionAutomationPolicy.rule_id.in_(['PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT', '40498741-ee6b-4a71-9101-0d6d3f77154c'])
        ))
        pols = pols_res.scalars().all()
        for pol in pols:
            pol.is_enabled = enable

        await db.commit()
        print(f"Scenario 8 state updated: enable={enable}")

if __name__ == "__main__":
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "enable"
    asyncio.run(main(action == "enable"))
