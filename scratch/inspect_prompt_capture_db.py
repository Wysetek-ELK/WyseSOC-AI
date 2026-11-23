import asyncio, sys, os, json
sys.path.insert(0, os.path.abspath("backend"))

from app.database import AsyncSessionLocal
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as session:
        stmt = select(ActualLLMPromptCapture).where(ActualLLMPromptCapture.incident_id == "132438483").order_by(ActualLLMPromptCapture.captured_at.desc())
        res = await session.execute(stmt)
        capture = res.scalars().first()
        if not capture:
            print("No prompt capture found for incident 132438483 in local DB")
            stmt_all = select(ActualLLMPromptCapture).limit(5)
            all_caps = (await session.execute(stmt_all)).scalars().all()
            print(f"Total prompt captures sample: {len(all_caps)}")
            for c in all_caps:
                print(f"  Capture {c.id}: inc={c.incident_id}, rule={c.rule_name}, captured_at={c.captured_at}")
            return
        
        print(f"Capture ID: {capture.id}")
        print(f"Rule: {capture.rule_name} (ID: {capture.rule_id})")
        print(f"Captured: {capture.captured_at}")
        print(f"System prompt length: {len(capture.compiled_system_prompt or '')}")
        print(f"User message length: {len(capture.user_message or '')}")
        print(f"Raw response length: {len(capture.response_raw or '')}")
        if capture.response_raw:
            print(f"Response raw: {capture.response_raw}")
        if capture.user_message:
            print(f"User message snippet: {capture.user_message[:1500]}")

asyncio.run(check())
