import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.incident import Incident
from app.models.analyst_feedback import AnalystVerdictReview
from app.utils.security import get_password_hash
from sqlalchemy import select, delete

async def setup():
    async with AsyncSessionLocal() as db:
        # 1. Ensure analyst_b exists
        res = await db.execute(select(User).where(User.username == "analyst_b"))
        u_b = res.scalar_one_or_none()
        if not u_b:
            u_b = User(
                id="analyst-user-b-004",
                username="analyst_b",
                email="analyst_b@verdictum.test",
                hashed_password=get_password_hash("AnalystPassword123!"),
                role="SOC Analyst",
                is_active=True,
            )
            db.add(u_b)
        else:
            u_b.hashed_password = get_password_hash("AnalystPassword123!")
            db.add(u_b)

        # 2. Pick target incident 132438483
        inc_stmt = select(Incident).where(Incident.incident_id == "132438483")
        inc = (await db.execute(inc_stmt)).scalars().first()
        if not inc:
            inc = (await db.execute(select(Incident).where(Incident.ai_verdict.isnot(None)))).scalars().first()
        
        print("Target Incident:", inc.id, inc.incident_id)

        # 3. Clear existing reviews on this incident for analyst_b
        await db.execute(delete(AnalystVerdictReview).where(
            (AnalystVerdictReview.incident_id.in_([str(inc.id), str(inc.incident_id)])) &
            (AnalystVerdictReview.reviewer_id.in_(["analyst-user-b-004", "analyst_b"]))
        ))

        # 4. Ensure Analyst A ('analyst') HAS submitted a review on this incident
        rev_a_stmt = select(AnalystVerdictReview).where(
            (AnalystVerdictReview.incident_id.in_([str(inc.id), str(inc.incident_id)])) &
            (AnalystVerdictReview.reviewer_id.in_(["analyst-user-002", "analyst"]))
        )
        rev_a = (await db.execute(rev_a_stmt)).scalar_one_or_none()
        if not rev_a:
            rev_a = AnalystVerdictReview(
                incident_id=inc.id,
                rule_id=inc.rule_id or "PH_RULE_TEST",
                reviewer_id="analyst",
                analyst_verdict="TRUE_POSITIVE",
                analyst_notes="Verified by primary analyst during ground truth review",
                revealed_ai_verdict="TRUE_POSITIVE",
                comparison_outcome="AGREEMENT_TP",
            )
            db.add(rev_a)

        # 5. Clear all reviews on incident 170001 (or another incident) so that neither analyst has reviewed it
        other_inc_stmt = select(Incident).where(Incident.incident_id != inc.incident_id).limit(1)
        other_inc = (await db.execute(other_inc_stmt)).scalars().first()
        if other_inc:
            await db.execute(delete(AnalystVerdictReview).where(
                AnalystVerdictReview.incident_id.in_([str(other_inc.id), str(other_inc.incident_id)])
            ))

        await db.commit()
        print("✓ Database state successfully prepared for V1.2.2a validation.")

if __name__ == "__main__":
    asyncio.run(setup())
