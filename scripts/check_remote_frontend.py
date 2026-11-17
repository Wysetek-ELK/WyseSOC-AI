import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, r"C:\Users\amit\.gemini\config\repo_deploy_governor\scripts")
from governor_cli import load_project_config

cfg = load_project_config(os.getcwd())
ssh_info = cfg["deployment"]["ssh"]
host = ssh_info["host"]
user = ssh_info["user"]
port = ssh_info.get("port", 22)
key_ref = os.path.expanduser(ssh_info.get("key_reference", "~/.ssh/id_ed25519"))

cmd = [
    "ssh", "-p", str(port), "-i", key_ref,
    "-o", "StrictHostKeyChecking=yes",
    f"{user}@{host}",
    "curl -s -o /dev/null -w 'AIS HTTP %{http_code}\n' http://127.0.0.1:3000/agent-intelligence-studio; curl -s -o /dev/null -w 'Login HTTP %{http_code}\n' http://127.0.0.1:3000/login"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print(res.stdout)
