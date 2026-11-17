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

script = """
import asyncio
import sys
sys.path.insert(0, "/opt/wysesoc-ai/backend")
from app.database import AsyncSessionLocal
from app.models.user import User
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User.id, User.username, User.role))
        for row in res.all():
            print(row)

asyncio.run(run())
"""

base_ssh = [
    "ssh", "-T",
    "-p", str(port),
    "-i", key_ref,
    "-o", "StrictHostKeyChecking=yes",
    f"{user}@{host}",
    "/opt/wysesoc-ai/backend/venv/bin/python -"
]

proc = subprocess.run(base_ssh, input=script.encode(), capture_output=True)
print(proc.stdout.decode("utf-8", errors="replace"))
if proc.stderr:
    print("STDERR:", proc.stderr.decode("utf-8", errors="replace"))
