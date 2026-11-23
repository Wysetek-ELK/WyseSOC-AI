"""
Execute AIS 2.3a Real GPU Regression on 5 Targeted Benchmark Incidents.
Targets:
- 2 CrowdStrike: 132438483, 132527297
- 3 Prisma SASE: 132499009, 132499023, 132499745
Evaluates against live Server 1 API (172.26.41.240) bridging to Server 2 Qwen GPU (13.204.214.64:8000/v1).
"""

import os
import sys
import json
import time
import urllib.request

output_file = "scratch/gpu_regression_results_ais_2_3a.json"

# 1. Authenticate on Server 1
print("[1/3] Authenticating on Server 1...")
auth_req = urllib.request.Request(
    "http://172.26.41.240/api/auth/login",
    data=json.dumps({"username": "admin", "password": "AdminPassword123!"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
auth_resp = urllib.request.urlopen(auth_req, timeout=15)
token = json.loads(auth_resp.read().decode("utf-8"))["access_token"]
print("      Authenticated as Administrator.")

# 2. Define Targeted Incidents
targets = [
    {"incident_id": "132438483", "category": "CrowdStrike", "rule_id": "0974a66e-ede2-4a6a-821b-6283a99c8aa4"},
    {"incident_id": "132527297", "category": "CrowdStrike", "rule_id": "0974a66e-ede2-4a6a-821b-6283a99c8aa4"},
    {"incident_id": "132499009", "category": "Prisma SASE", "rule_id": "14481ebd-4e8c-421e-8579-b6ee7995b746"},
    {"incident_id": "132499023", "category": "Prisma SASE", "rule_id": "14481ebd-4e8c-421e-8579-b6ee7995b746"},
    {"incident_id": "132499745", "category": "Prisma SASE", "rule_id": "14481ebd-4e8c-421e-8579-b6ee7995b746"},
]

print(f"\n[2/3] Executing Real GPU Regression across {len(targets)} incidents...")
results = []

for idx, tgt in enumerate(targets):
    inc_id = tgt["incident_id"]
    cat = tgt["category"]
    print(f"\n--- [{idx+1}/{len(targets)}] Evaluating Incident {inc_id} ({cat}) ---")
    
    t0 = time.perf_counter()
    eval_req = urllib.request.Request(
        f"http://172.26.41.240/api/incidents/{inc_id}/ai-verdict",
        data=b"{}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    
    try:
        eval_resp = urllib.request.urlopen(eval_req, timeout=120)
        wall_time_ms = round((time.perf_counter() - t0) * 1000, 2)
        res = json.loads(eval_resp.read().decode("utf-8"))
        
        entry = {
            "index": idx + 1,
            "incident_id": inc_id,
            "rule_category": cat,
            "rule_id": res.get("rule_id"),
            "rule_name": res.get("rule_name"),
            "policy_version_id": res.get("policy_version_id"),
            "policy_version_number": res.get("policy_version_number"),
            "policy_status": res.get("policy_status"),
            "proposed_verdict": res.get("proposed_verdict"),
            "effective_verdict": res.get("verdict"),
            "raw_model_confidence": res.get("raw_model_confidence"),
            "authoritative_confidence": res.get("confidence"),
            "validation_status": res.get("validation_status"),
            "action_directive": res.get("action_directive"),
            "rejection_reasons": res.get("rejection_reasons", []),
            "reason": res.get("reason"),
            "missing_evidence": res.get("missing_evidence", []),
            "prompt_tokens": res.get("prompt_tokens"),
            "completion_tokens": res.get("completion_tokens"),
            "total_tokens": res.get("total_tokens"),
            "wall_time_ms": wall_time_ms,
            "is_simulated": res.get("is_simulated", False),
            "execution_provenance": res.get("execution_provenance"),
            "model_identifier": res.get("model_identifier"),
        }
        
        print(f"      Wall time: {wall_time_ms} ms")
        print(f"      Proposed: {entry['proposed_verdict']} -> Effective: {entry['effective_verdict']}")
        print(f"      Validation: {entry['validation_status']}")
        print(f"      Rule ID: {entry['rule_id']}")
        print(f"      Policy Status: {entry['policy_status']}")
        print(f"      Tokens (P/C/T): {entry['prompt_tokens']} / {entry['completion_tokens']} / {entry['total_tokens']}")
        results.append(entry)
        
    except Exception as e:
        print(f"      ERROR: {e}")
        results.append({
            "index": idx + 1,
            "incident_id": inc_id,
            "rule_category": cat,
            "error": str(e),
        })

# 3. Save Results
with open(output_file, "w") as f:
    json.dump({"executions": results, "timestamp": time.time()}, f, indent=2)

print(f"\n[3/3] Regression results saved to {output_file}")
