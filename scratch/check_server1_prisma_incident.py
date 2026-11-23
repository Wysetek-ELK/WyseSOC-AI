import urllib.request
import json

auth_req = urllib.request.Request(
    "http://172.26.41.240/api/auth/login",
    data=json.dumps({"username": "admin", "password": "AdminPassword123!"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
auth_resp = urllib.request.urlopen(auth_req)
token = json.loads(auth_resp.read().decode("utf-8"))["access_token"]

req = urllib.request.Request(
    "http://172.26.41.240/api/incidents/132499009",
    headers={"Authorization": f"Bearer {token}"}
)
try:
    resp = urllib.request.urlopen(req)
    inc_data = json.loads(resp.read().decode("utf-8"))
    print("Incident ID:", inc_data.get("incident_id"))
    print("Title:", inc_data.get("title"))
    print("Events count:", len(inc_data.get("events", [])))
    if inc_data.get("events"):
        ev = inc_data["events"][0]
        print("Event 0 keys:", list(ev.keys()))
        print("Event 0 raw_log length:", len(ev.get("raw_log") or ""))
        print("Event 0 attributes:", ev.get("attributes"))
except Exception as e:
    print("Error:", e)
