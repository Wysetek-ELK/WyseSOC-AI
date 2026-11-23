import json
with open('docs/AIS_2_3/GPU_PILOT_RESULTS.json') as f:
    d = json.load(f)
for i in range(10):
    ex = d['executions'][i]
    print(f"[{i+1}] ID={ex['incident_id']}:")
    print(f"     Reason: {ex.get('reason')}")
    print(f"     Missing: {ex.get('missing_evidence')}")
