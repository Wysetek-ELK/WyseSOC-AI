import os
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, r"C:\Users\amit\.gemini\config\repo_deploy_governor\scripts")
from governor_cli import load_project_config

cfg = load_project_config(os.getcwd())
print("Remote app config:", cfg["deployment"]["app"])
ssh_info = cfg["deployment"]["ssh"]
host = ssh_info["host"]
user = ssh_info["user"]
port = ssh_info.get("port", 22)
key_ref = os.path.expanduser(ssh_info.get("key_reference", "~/.ssh/id_ed25519"))

cmd = [
    "ssh", "-p", str(port), "-i", key_ref,
    "-o", "StrictHostKeyChecking=yes",
    f"{user}@{host}",
    "find /home -name 'main.py' 2>/dev/null; which python3; systemctl cat ai-verdict-backend.service | grep ExecStart"
]
res = subprocess.run(cmd, capture_output=True, text=True)
print("SSH result:")
print(res.stdout)
