import asyncio
import sys
import json

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.incident import Incident
from sqlalchemy import select

async def inspect_335():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Incident).where(Incident.incident_id == '335'))
        inc = res.scalars().first()
        if inc:
            print(json.dumps({
                "id": inc.id,
                "incident_id": inc.incident_id,
                "source_ip": inc.source_ip,
                "reporting_device": inc.reporting_device,
                "reporting_ip": inc.reporting_ip,
                "customer": inc.customer,
                "raw_keys": list((inc.raw_payload or {}).keys()),
                "raw_src": (inc.raw_payload or {}).get("srcIp") or (inc.raw_payload or {}).get("sourceIp"),
                "raw_dest": (inc.raw_payload or {}).get("destIp"),
                "raw_port": (inc.raw_payload or {}).get("destPort"),
            }, indent=2))

if __name__ == '__main__':
    asyncio.run(inspect_335())
