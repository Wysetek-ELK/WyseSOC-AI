import urllib.request
import json

auth_req = urllib.request.Request(
    "http://172.26.41.240/api/auth/login",
    data=json.dumps({"username": "admin", "password": "AdminPassword123!"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
auth_resp = urllib.request.urlopen(auth_req)
token = json.loads(auth_resp.read().decode("utf-8"))["access_token"]

for inc_id in ["132438483", "132499009"]:
    print(f"\n================ INCIDENT {inc_id} ACTUAL PROMPT ================")
    req = urllib.request.Request(
        f"http://172.26.41.240/api/prompts/actual-prompt/incident/{inc_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    try:
        resp = urllib.request.urlopen(req)
        data = json.loads(resp.read().decode("utf-8"))
        print(f"Capture ID: {data.get('capture_id')}")
        print(f"Capture Status: {data.get('capture_status')}")
        print(f"System Prompt Length: {len(data.get('system_prompt', ''))}")
        print(f"Incident Payload Length: {len(data.get('incident_payload', ''))}")
        print(f"Raw Model Response: {data.get('raw_model_response')}")
        print("\n--- System Prompt (First 800 chars) ---")
        print(data.get('system_prompt', '')[:800])
        print("\n--- Incident Payload (Sample) ---")
        print(data.get('incident_payload', '')[:800])
        
        # Save full capture to scratch for deeper inspection
        with open(f"scratch/capture_{inc_id}.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"Saved to scratch/capture_{inc_id}.json")
    except Exception as e:
        print(f"Error fetching for {inc_id}: {e}")
