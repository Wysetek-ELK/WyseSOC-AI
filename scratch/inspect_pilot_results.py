import json

with open('docs/AIS_2_3/GPU_PILOT_RESULTS.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

executions = d.get('executions', [])
print(f"Total executions: {len(executions)}")
for idx, r in enumerate(executions):
    inc_id = r.get("incident_id")
    rule = r.get("rule_name")
    prop = r.get("proposed_verdict")
    eff = r.get("effective_verdict")
    est_tok = r.get("estimated_tokens")
    prov_tok = r.get("provider_tokens")
    reasons = r.get("validation_reasons")
    rule_id = r.get("rule_id")
    pol_id = r.get("policy_version_id")
    val_status = r.get("validation_status")
    print(f"[{idx+1}] ID={inc_id} | Rule={rule} | RuleID={rule_id} | PolVer={pol_id}")
    print(f"     Proposed={prop} -> Effective={eff} | ValStatus={val_status}")
    print(f"     Tokens: Est={est_tok} Prov={prov_tok}")
    print(f"     Val Reasons: {reasons}")
    if r.get("model_reasoning"):
        print(f"     Reasoning: {r.get('model_reasoning')[:140]}...")
    if r.get("missing_evidence"):
        print(f"     Missing Evidence: {r.get('missing_evidence')}")
    print("-" * 60)
