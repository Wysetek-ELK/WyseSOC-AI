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
        # 1. Ensure analyst and analyst_b have customer = 'TENANT_ALPHA'
        res_a = await db.execute(select(User).where(User.username == "analyst"))
        u_a = res_a.scalar_one_or_none()
        if u_a:
            u_a.customer = "TENANT_ALPHA"
            u_a.hashed_password = get_password_hash("AnalystPassword123!")
            db.add(u_a)

        res_b = await db.execute(select(User).where(User.username == "analyst_b"))
        u_b = res_b.scalar_one_or_none()
        if not u_b:
            u_b = User(
                id="analyst-user-b-004",
                username="analyst_b",
                email="analyst_b@verdictum.test",
                hashed_password=get_password_hash("AnalystPassword123!"),
                role="SOC Analyst",
                is_active=True,
                customer="TENANT_ALPHA",
            )
            db.add(u_b)
        else:
            u_b.customer = "TENANT_ALPHA"
            u_b.hashed_password = get_password_hash("AnalystPassword123!")
            db.add(u_b)

        # Ensure viewer exists
        res_v = await db.execute(select(User).where(User.username == "viewer"))
        u_v = res_v.scalar_one_or_none()
        if u_v:
            u_v.customer = "TENANT_ALPHA"
            u_v.hashed_password = get_password_hash("ViewerPassword123!")
            db.add(u_v)

        # 2. Pick target incident 132438483 and set customer = 'TENANT_ALPHA'
        inc_stmt = select(Incident).where(Incident.incident_id == "132438483")
        inc = (await db.execute(inc_stmt)).scalars().first()
        if inc:
            inc.customer = "TENANT_ALPHA"
            db.add(inc)
            print("Target Incident 132438483 set to TENANT_ALPHA")

        # 3. Create Tenant Beta incident for cross-tenant testing
        beta_inc_stmt = select(Incident).where(Incident.incident_id == "INC-TENANT-BETA-001")
        beta_inc = (await db.execute(beta_inc_stmt)).scalars().first()
        if not beta_inc:
            beta_inc = Incident(
                id="incident-uuid-beta-001",
                incident_id="INC-TENANT-BETA-001",
                event_type="PH_RULE_BETA_EXFIL",
                title="Unauthorized Data Exfiltration from Beta Storage",
                rule_id="PH_RULE_BETA_EXFIL",
                severity="HIGH",
                customer="TENANT_BETA",
                ai_verdict={"verdict": "TRUE_POSITIVE", "confidence": 0.94, "explanation": "Exfiltration pattern detected across Tenant Beta cloud endpoints"},
                raw_payload={"event": "cloud_storage_bulk_read", "customer": "TENANT_BETA"}
            )
            db.add(beta_inc)
            print("Created Tenant Beta Incident: INC-TENANT-BETA-001")
        else:
            beta_inc.customer = "TENANT_BETA"
            db.add(beta_inc)

        # 4. Clear existing reviews on 132438483 for analyst_b
        if inc:
            await db.execute(delete(AnalystVerdictReview).where(
                (AnalystVerdictReview.incident_id.in_([str(inc.id), str(inc.incident_id)])) &
                (AnalystVerdictReview.reviewer_id.in_(["analyst-user-b-004", "analyst_b"]))
            ))

            # 5. Ensure Analyst A ('analyst') HAS submitted a review on 132438483
            rev_a_stmt = select(AnalystVerdictReview).where(
                (AnalystVerdictReview.incident_id.in_([str(inc.id), str(inc.incident_id)])) &
                (AnalystVerdictReview.reviewer_id.in_(["analyst-user-002", "analyst"]))
            )
            rev_a = (await db.execute(rev_a_stmt)).scalar_one_or_none()
            if not rev_a:
                rev_a = AnalystVerdictReview(
                    incident_id=inc.id,
                    rule_id=inc.rule_id or "PH_RULE_TEST",
                    customer="TENANT_ALPHA",
                    reviewer_id="analyst",
                    analyst_verdict="TRUE_POSITIVE",
                    analyst_notes="Verified by primary analyst during ground truth review",
                    revealed_ai_verdict="TRUE_POSITIVE",
                    comparison_outcome="AGREEMENT_TP",
                )
                db.add(rev_a)
            else:
                rev_a.customer = "TENANT_ALPHA"
                db.add(rev_a)

        await db.commit()
        print("✓ Database state successfully prepared for V1.2.2b validation.")

if __name__ == "__main__":
    asyncio.run(setup())
