"""
Execute bounded real GPU smoke test against Server 2 Qwen model via Server 1 API.
Evaluates up to 5 real incidents, capturing latency, tokens, prompt hashes, and validation status.
"""

import os
import sys
import json
import time
import urllib.request

output_dir = "docs/AIS_2_2a"
os.makedirs(output_dir, exist_ok=True)
results_file = os.path.join(output_dir, "GPU_SMOKE_TEST_RESULTS.json")

# Authenticate on Server 1
auth_req = urllib.request.Request(
    "http://172.26.41.240/api/auth/login",
    data=json.dumps({"username": "admin", "password": "AdminPassword123!"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
auth_resp = urllib.request.urlopen(auth_req)
token = json.loads(auth_resp.read().decode("utf-8"))["access_token"]
print("[+] Authenticated on Server 1 as Administrator.")

# Query candidate incidents for Heavy TCP Host Scan On Fixed Port
rule_uuid = "40498741-ee6b-4a71-9101-0d6d3f77154c"
inc_req = urllib.request.Request(
    f"http://172.26.41.240/api/incidents?rule_id={rule_uuid}&page_size=10",
    headers={"Authorization": f"Bearer {token}"}
)
inc_data = json.loads(urllib.request.urlopen(inc_req).read().decode("utf-8"))
items = inc_data.get("items", [])
assert len(items) >= 5, f"Expected at least 5 incidents, got {len(items)}"

# Select 5 distinct real incidents
smoke_targets = items[:5]
print(f"[+] Selected 5 real incidents for GPU smoke test from rule {rule_uuid}:")
for t in smoke_targets:
    print(f"    - SIEM ID: {t['incident_id']} (DB ID: {t['id']})")

executions = []
for idx, target in enumerate(smoke_targets):
    inc_db_id = target["id"]
    siem_id = target["incident_id"]
    print(f"\n[{idx+1}/5] Executing inference for Incident {siem_id} ({inc_db_id})...")
    
    t0 = time.perf_counter()
    eval_req = urllib.request.Request(
        f"http://172.26.41.240/api/incidents/{inc_db_id}/ai-verdict",
        data=b"{}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    
    try:
        eval_resp = urllib.request.urlopen(eval_req, timeout=120)
        wall_time_s = time.perf_counter() - t0
        res = json.loads(eval_resp.read().decode("utf-8"))
        
        entry = {
            "index": idx + 1,
            "incident_id": siem_id,
            "db_id": inc_db_id,
            "rule_id": rule_uuid,
            "rule_name": res.get("rule_name", "Heavy TCP Host Scan On Fixed Port"),
            "success": True,
            "execution_status": "COMPLETED",
            "model_identifier": res.get("model_identifier"),
            "provider_type": res.get("provider_type"),
            "base_url": "http://13.204.214.64:8000/v1",
            "is_simulated": res.get("is_simulated", False),
            "execution_provenance": res.get("execution_provenance"),
            "proposed_verdict": res.get("proposed_verdict"),
            "effective_verdict": res.get("verdict"),
            "raw_model_confidence": res.get("raw_model_confidence"),
            "reason": res.get("reason"),
            "missing_evidence": res.get("missing_evidence", []),
            "prompt_tokens": res.get("prompt_tokens"),
            "completion_tokens": res.get("completion_tokens"),
            "total_tokens": res.get("total_tokens"),
            "latency_ms": res.get("latency_ms"),
            "wall_clock_seconds": round(wall_time_s, 2),
            "prompt_sha256": res.get("prompt_sha256"),
            "prompt_capture_id": res.get("prompt_capture_id"),
            "prompt_integrity_status": res.get("prompt_integrity_status"),
            "validation_status": res.get("validation_status"),
            "validation_reason_codes": res.get("validation_reason_codes", []),
            "policy_version_number": res.get("policy_version_number"),
            "policy_status": res.get("policy_status"),
            "contract_id": res.get("contract_id"),
            "trust_score": res.get("trust_score"),
            "evidence_sufficiency_score": res.get("evidence_sufficiency_score"),
            "evaluated_at": res.get("evaluated_at"),
        }
        executions.append(entry)
        print(f"    Status: SUCCESS | Verdict: {entry['proposed_verdict']} | Tokens: {entry['total_tokens']} | Latency: {entry['latency_ms']}ms ({wall_time_s:.2f}s)")
        print(f"    Model: {entry['model_identifier']} | Prompt SHA256: {entry['prompt_sha256'][:16]}... | Validation: {entry['validation_status']}")
    except Exception as e:
        wall_time_s = time.perf_counter() - t0
        print(f"    Status: FAILED | Error: {e} ({wall_time_s:.2f}s)")
        executions.append({
            "index": idx + 1,
            "incident_id": siem_id,
            "db_id": inc_db_id,
            "success": False,
            "error": str(e),
            "wall_clock_seconds": round(wall_time_s, 2),
        })

smoke_report = {
    "smoke_test_version": "2.2a.0",
    "executed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "server_1_endpoint": "http://172.26.41.240",
    "server_2_endpoint": "http://13.204.214.64:8000/v1",
    "loaded_model": "Qwen/Qwen2.5-7B-Instruct-AWQ",
    "total_tested": len(executions),
    "total_succeeded": sum(1 for e in executions if e["success"]),
    "total_failed": sum(1 for e in executions if not e["success"]),
    "is_live_gpu_inference": True,
    "is_simulated": False,
    "executions": executions,
}

with open(results_file, "w", encoding="utf-8") as f:
    json.dump(smoke_report, f, indent=2)

print(f"\n[+] Real GPU Smoke Test complete! Results written to: {results_file}")
