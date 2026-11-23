import asyncio, sys, os
sys.path.insert(0, os.path.abspath("backend"))

from app.database import AsyncSessionLocal
from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.rule import Rule
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

async def check():
    async with AsyncSessionLocal() as session:
        inc_count = (await session.execute(select(func.count(Incident.id)))).scalar()
        ev_count = (await session.execute(select(func.count(IncidentEvent.id)))).scalar()
        gt_count = (await session.execute(select(func.count(HistoricalGroundTruth.id)))).scalar()
        print(f"Local DB Incidents: {inc_count}, Events: {ev_count}, GroundTruth: {gt_count}")
        
        stmt = select(Incident).options(selectinload(Incident.events), selectinload(Incident.ground_truth)).where(Incident.incident_id == "132438483")
        res = await session.execute(stmt)
        inc = res.scalar_one_or_none()
        if inc:
            print(f"Incident 132438483: title={inc.title}, rule_id={inc.rule_id}, events_count={len(inc.events)}")
            if inc.events:
                ev = inc.events[0]
                print(f"   First event ID: {ev.event_id}, raw_log length: {len(ev.raw_log)}, attrs count: {len(ev.attributes)}")
                print(f"   Sample attrs: {list(ev.attributes.keys())[:5]}")
            if inc.ground_truth:
                print(f"   Ground truth: res={inc.ground_truth.resolution}, reason={inc.ground_truth.cleared_reason[:40]}")

asyncio.run(check())
