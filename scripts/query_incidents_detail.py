import asyncio
import sys
import json

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.incident import Incident
from app.models.rule import Rule
from sqlalchemy import select, or_

async def inspect_incidents():
    async with AsyncSessionLocal() as db:
        # Check specific incident IDs mentioned in prompt: 335, 543, 546, 1477
        target_inc_ids = ['335', '543', '546', '1477', 'INC-335', 'INC-543', 'INC-546', 'INC-1477']
        res = await db.execute(select(Incident).where(or_(Incident.id.in_(target_inc_ids), Incident.incident_id.in_(target_inc_ids))))
        incs = res.scalars().all()
        print(f"Found {len(incs)} specific target incidents:")
        for inc in incs:
            print(json.dumps({
                "id": inc.id,
                "incident_id": getattr(inc, 'incident_id', None),
                "rule_id": inc.rule_id,
                "event_type": getattr(inc, 'event_type', None),
                "customer": getattr(inc, 'customer', None),
                "src_ip": getattr(inc, 'src_ip', None),
                "dest_ip": getattr(inc, 'dest_ip', None),
                "dest_port": getattr(inc, 'dest_port', None),
                "timestamp": str(getattr(inc, 'timestamp', None)),
                "raw_events_count": len(getattr(inc, 'raw_events', []) or [])
            }, indent=2))

        # Check total incidents in DB
        all_incs = (await db.execute(select(Incident))).scalars().all()
        print(f"Total incidents across all rules in DB: {len(all_incs)}")
        rules_map = {}
        for i in all_incs:
            rules_map[i.rule_id] = rules_map.get(i.rule_id, 0) + 1
        print("Incidents by rule_id:", json.dumps(rules_map, indent=2))

if __name__ == '__main__':
    asyncio.run(inspect_incidents())
