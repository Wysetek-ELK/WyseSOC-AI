import asyncio
import sys
import json
import urllib.request
import time

sys.path.insert(0, '/opt/wysesoc-ai/backend')
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.actual_prompt_capture import ActualLLMPromptCapture
from app.models.incident import Incident
from app.utils.security import create_access_token
from sqlalchemy import select, desc

RULE_UUID = '40498741-ee6b-4a71-9101-0d6d3f77154c'
V7_VERSION_ID = 'd79fb576-c6b9-4f63-9167-3c7a2419b70a'

async def run_single_inference():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.role == 'Administrator'))
        admin = res.scalars().first()
        token = create_access_token({"sub": admin.id, "username": admin.username, "role": admin.role, "customer": admin.customer})

        # Find eligible incident
        inc_res = await db.execute(select(Incident).where(Incident.rule_id == RULE_UUID).order_by(Incident.id))
        target_inc = inc_res.scalars().first()
        if not target_inc:
            print("No incidents found for target rule!")
            return
        inc_id = target_inc.id
        print(f"Targeting single incident: id={inc_id}, incident_id={target_inc.incident_id}, customer={target_inc.customer}")

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "version_id": V7_VERSION_ID,
        "version_number": 7,
        "incident_ids": [inc_id],
        "max_concurrency": 1,
        "confirm_execution": True
    }

    url = f"http://127.0.0.1:8000/api/ais/rules/{RULE_UUID}/evaluate-missing-batch"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")

    print(f"Triggering controlled live inference on Server 2 (Qwen/Qwen2.5-7B-Instruct-AWQ)...")
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=45) as resp:
        result = json.loads(resp.read().decode())
        elapsed = round(time.perf_counter() - t0, 3)
        print(f"Batch inference request completed in {elapsed}s: {json.dumps(result, indent=2)}")

    # Allow a moment for DB persistence
    await asyncio.sleep(2)

    # Inspect captured prompt record in PostgreSQL
    async with AsyncSessionLocal() as db:
        cap_stmt = select(ActualLLMPromptCapture).where(
            ActualLLMPromptCapture.incident_id == inc_id,
            ActualLLMPromptCapture.policy_version_id == V7_VERSION_ID
        ).order_by(desc(ActualLLMPromptCapture.captured_at))
        cap = (await db.execute(cap_stmt)).scalars().first()

        if cap:
            capture_evidence = {
                "capture_id": cap.id,
                "execution_id": cap.execution_id,
                "incident_id": cap.incident_id,
                "rule_id": cap.rule_id,
                "rule_name": cap.rule_name,
                "policy_version_id": cap.policy_version_id,
                "policy_version_number": cap.policy_version_number,
                "dispatch_status": cap.dispatch_status,
                "is_simulated": cap.is_simulated,
                "model_name": cap.model_name,
                "request_sha256": cap.request_sha256,
                "response_verdict": cap.response_verdict,
                "response_confidence": cap.response_confidence,
                "latency_ms": cap.latency_ms,
                "token_usage": {
                    "prompt_tokens": cap.prompt_tokens,
                    "completion_tokens": cap.completion_tokens,
                    "total_tokens": cap.total_tokens
                },
                "response_raw": cap.response_raw[:500] if cap.response_raw else None,
                "captured_at": str(cap.captured_at)
            }
            print("\nAuthoritative Prompt Capture Record:")
            print(json.dumps(capture_evidence, indent=2))
        else:
            print("Warning: No capture record found for evaluated incident.")

if __name__ == '__main__':
    asyncio.run(run_single_inference())
