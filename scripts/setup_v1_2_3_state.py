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
        # 1. Ensure users exist with correct credentials and tenant assignments
        users_config = [
            ("admin-user-001", "admin", "admin@verdictum.test", "AdminPassword123!", "Administrator", None),
            ("analyst-user-002", "analyst", "analyst@tenant-alpha.test", "AnalystPassword123!", "SOC Analyst", "TENANT_ALPHA"),
            ("analyst-user-b-004", "analyst_b", "analyst_b@tenant-alpha.test", "AnalystPassword123!", "SOC Analyst", "TENANT_ALPHA"),
            ("viewer-user-003", "viewer", "viewer@tenant-alpha.test", "ViewerPassword123!", "Read-Only Viewer", "TENANT_ALPHA"),
            ("analyst-tenant-b-006", "analyst_tenant_b", "analyst_b@tenant-beta.test", "AnalystPassword123!", "SOC Analyst", "TENANT_BETA"),
            ("analyst-default-007", "analyst_default", "analyst_def@default.test", "AnalystPassword123!", "SOC Analyst", "DEFAULT"),
        ]

        for uid, uname, uemail, upass, urole, ucustomer in users_config:
            res = await db.execute(select(User).where(User.username == uname))
            u = res.scalar_one_or_none()
            if not u:
                u = User(
                    id=uid,
                    username=uname,
                    email=uemail,
                    hashed_password=get_password_hash(upass),
                    role=urole,
                    is_active=True,
                    customer=ucustomer,
                )
                db.add(u)
            else:
                u.customer = ucustomer
                u.role = urole
                u.hashed_password = get_password_hash(upass)
                db.add(u)

        # 2. Ensure target incident 132438483 belongs to TENANT_ALPHA
        inc_stmt = select(Incident).where(Incident.incident_id == "132438483")
        inc = (await db.execute(inc_stmt)).scalars().first()
        if inc:
            inc.customer = "TENANT_ALPHA"
            db.add(inc)

        # 3. Ensure Tenant Beta incident exists for cross-tenant testing
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
        else:
            beta_inc.customer = "TENANT_BETA"
            db.add(beta_inc)

        # 4. Ensure Legacy DEFAULT incident exists
        def_inc_stmt = select(Incident).where(Incident.incident_id == "inc-legacy-default-901")
        def_inc = (await db.execute(def_inc_stmt)).scalars().first()
        if not def_inc:
            def_inc = Incident(
                id="incident-uuid-default-901",
                incident_id="inc-legacy-default-901",
                event_type="LEGACY_UNASSIGNED_EVENT",
                title="Legacy Unassigned Platform Incident",
                severity="HIGH",
                customer="DEFAULT",
                ai_verdict={"verdict": "FALSE_POSITIVE", "reason": "Platform test incident"},
                raw_payload={"event": "legacy_syslog", "customer": "DEFAULT"}
            )
            db.add(def_inc)
        else:
            def_inc.customer = "DEFAULT"
            db.add(def_inc)

        # 5. Reset reviews on 132438483: Analyst A submitted, Analyst B unsubmitted
        if inc:
            # Clear Analyst B reviews
            await db.execute(delete(AnalystVerdictReview).where(
                (AnalystVerdictReview.incident_id.in_([str(inc.id), str(inc.incident_id)])) &
                (AnalystVerdictReview.reviewer_id.in_(["analyst-user-b-004", "analyst_b"]))
            ))

            # Ensure Analyst A review exists
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
        print("✓ Database state successfully prepared for V1.2.3 validation.")

if __name__ == "__main__":
    asyncio.run(setup())
