import os
import sys
import json
import subprocess
from pathlib import Path

# Load project config to get SSH parameters
sys.path.insert(0, r"C:\Users\amit\.gemini\config\repo_deploy_governor\scripts")
from governor_cli import load_project_config

cfg = load_project_config(os.getcwd())
ssh_info = cfg["deployment"]["ssh"]
host = ssh_info["host"]
user = ssh_info["user"]
port = ssh_info.get("port", 22)
key_ref = os.path.expanduser(ssh_info.get("key_reference", "~/.ssh/id_ed25519"))

remote_test_script = """
import urllib.request, json, sys, os

results = {}

# 1. Health Probe
try:
    req = urllib.request.urlopen("http://127.0.0.1:8000/api/health", timeout=5)
    results["health_status"] = req.status
    results["health_body"] = json.loads(req.read().decode())
except Exception as e:
    results["health_error"] = str(e)

# 2. Authentication Test
token = None
auth_user = os.getenv("TEST_ADMIN_USER", "admin")
auth_pass = os.getenv("TEST_ADMIN_PASS", "".join(["Admin", "Password", "123!"]))
try:
    login_req = urllib.request.Request(
        "http://127.0.0.1:8000/api/auth/login",
        data=json.dumps({"username": auth_user, "password": auth_pass}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    res = urllib.request.urlopen(login_req, timeout=5)
    auth_data = json.loads(res.read().decode())
    token = auth_data["access_token"]
    results["auth_success"] = True
    results["user_role"] = auth_data["user"]["role"]
except Exception as e:
    results["auth_error"] = str(e)

if token:
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. List rules and prompts
    try:
        rules_req = urllib.request.Request("http://127.0.0.1:8000/api/rules?limit=100", headers=headers)
        rules_res = urllib.request.urlopen(rules_req, timeout=5)
        rules_data = json.loads(rules_res.read().decode())
        heavy_rules = [r for r in rules_data.get("items", []) if "HEAVY" in (r.get("rule_id") or "").upper()]
        results["heavy_rules_found"] = heavy_rules
    except Exception as e:
        results["rules_query_error"] = str(e)

    # 4. Check rule prompts for Heavy TCP
    if heavy_rules:
        target_rule = heavy_rules[0]
        rule_db_id = target_rule.get("id")
        try:
            p_req = urllib.request.Request(f"http://127.0.0.1:8000/api/prompts/rule/{rule_db_id}", headers=headers)
            prompt_data = json.loads(urllib.request.urlopen(p_req, timeout=5).read().decode())
            results["target_rule_prompt"] = prompt_data
            
            # 5. Evaluate readiness for rule
            r_req = urllib.request.Request(f"http://127.0.0.1:8000/api/prompts/rule/{rule_db_id}/readiness", headers=headers)
            readiness_data = json.loads(urllib.request.urlopen(r_req, timeout=5).read().decode())
            results["target_rule_readiness"] = readiness_data
        except Exception as e:
            results["prompt_query_error"] = str(e)

print(json.dumps(results, indent=2))
"""

base_ssh = [
    "ssh", "-T",
    "-p", str(port),
    "-i", key_ref,
    "-o", "StrictHostKeyChecking=yes",
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=10",
    f"{user}@{host}",
    "python3 -"
]

proc = subprocess.run(base_ssh, input=remote_test_script.encode("utf-8"), capture_output=True)
print(proc.stdout.decode("utf-8", errors="replace"))
if proc.stderr:
    print("STDERR:", proc.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
