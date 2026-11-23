import urllib.request
import json

auth_req = urllib.request.Request(
    "http://172.26.41.240/api/auth/login",
    data=json.dumps({"username": "admin", "password": "AdminPassword123!"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
auth_resp = urllib.request.urlopen(auth_req)
token = json.loads(auth_resp.read().decode("utf-8"))["access_token"]

cs_rule_id = "0974a66e-ede2-4a6a-821b-6283a99c8aa4"
req = urllib.request.Request(
    f"http://172.26.41.240/api/prompts/rule/{cs_rule_id}",
    headers={"Authorization": f"Bearer {token}"}
)
try:
    resp = urllib.request.urlopen(req)
    prompt_data = json.loads(resp.read().decode("utf-8"))
    print("Rule Title:", prompt_data.get("title"))
    print("Active Version ID:", prompt_data.get("active_version_id"))
    versions = prompt_data.get("versions", [])
    print("Versions count:", len(versions))
    for v in versions:
        print(f"  v{v.get('version_number')}: status={v.get('status')}, id={v.get('id')}")
        print(f"     Required evidence: {v.get('required_evidence')}")
        print(f"     TP indicators: {v.get('tp_indicators')}")
        print(f"     FP indicators: {v.get('fp_indicators')}")
except Exception as e:
    print("Error:", e)
