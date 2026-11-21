import asyncio
import sys
import json
import urllib.request

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.user import User
from app.utils.security import create_access_token
from sqlalchemy import select

RULE_UUID = '40498741-ee6b-4a71-9101-0d6d3f77154c'

async def test_endpoint():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.role == 'Administrator'))
        admin = res.scalars().first()
        token = create_access_token({"sub": admin.id, "username": admin.username, "role": admin.role, "customer": admin.customer})

    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test Evaluation Status
    tracking_url = f"http://127.0.0.1:8000/api/ais/rules/{RULE_UUID}/evaluation-status"
    req_t = urllib.request.Request(tracking_url, headers=headers)
    with urllib.request.urlopen(req_t, timeout=5) as r:
        tracking_data = json.loads(r.read().decode())
        summary = tracking_data.get("summary", {})
        print("Summary Data:", json.dumps(summary, indent=2))
        items = tracking_data.get("items", [])
        print(f"Tracking Items Count: {len(items)}")
        for it in items[:6]:
            print(f"  Incident #{it.get('incident_id')} - Customer: {it.get('customer')} - Status: {it.get('status')} ({it.get('status_display')})")

    # 2. Test Rule Summary Header endpoint (AIS overview)
    overview_url = f"http://127.0.0.1:8000/api/prompts/rule/{RULE_UUID}/summary"
    req_o = urllib.request.Request(overview_url, headers=headers)
    with urllib.request.urlopen(req_o, timeout=5) as r:
        overview_data = json.loads(r.read().decode())
        print("Overview Data:", json.dumps({
            "rule_id": overview_data.get("rule_id"),
            "rule_name": overview_data.get("rule_name"),
            "active_version_number": overview_data.get("active_version_number"),
            "active_version_id": overview_data.get("active_version_id"),
            "ai_execution_suspended": overview_data.get("ai_execution_suspended"),
            "suspension_reason": overview_data.get("suspension_reason"),
            "quality_status": overview_data.get("quality_status"),
            "quality_score": overview_data.get("quality_score"),
        }, indent=2))

if __name__ == '__main__':
    asyncio.run(test_endpoint())
