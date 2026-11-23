import sys
sys.path.insert(0, 'backend')
import zipfile, json
from app.models.incident import Incident
from app.models.rule import Rule
from app.services.empirical_benchmark_harness import EventAdapter
from app.services.verdict_pipeline import build_sanitized_model_payload
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.token_budget_service import TokenBudgetService

with zipfile.ZipFile('fixtures/Incident json.zip', 'r') as z:
    raw_data = json.loads(z.read('Incident json/Crowdstrike Suspicious Activity/IncidnetId_132438483.json').decode('utf-8'))

raw_events = [EventAdapter(e, i) for i, e in enumerate(raw_data.get('rawEvents', []))]
inc = Incident(
    id='test-132438483',
    incident_id=132438483,
    title=raw_data.get('title'),
    event_type=raw_data.get('eventType'),
    severity=raw_data.get('severity', 5),
    raw_payload=raw_data
)
rule = Rule(
    id="0974a66e-ede2-4a6a-821b-6283a99c8aa4",
    name="Crowdstrike: Suspicious Activity",
    rule_id="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
    event_type="PH_RULE_CS_SUSPICIOUS_ACTIVITY",
    severity=5
)

norm_res, payload_dict = build_sanitized_model_payload(inc, rule)
compiled = PolicyCompilerService.compile_policy(rule=rule, prompt_version=None)

budgeted = TokenBudgetService.budget_prompt(
    compiled_policy=compiled,
    incident_payload=payload_dict,
    rag_block="",
    max_context_tokens=4096,
    max_completion_tokens=768,
    reserved_overhead_tokens=TokenBudgetService.estimate_tokens({"id": rule.id, "name": rule.name}),
    target_input_budget=3328,
)

print("Can proceed to inference:", budgeted.can_proceed_to_inference)
print("Budgeted total tokens (estimated):", budgeted.breakdown.total_prompt_tokens)
final_can_ev = budgeted.budgeted_incident_payload.get("canonical_evidence", [])
print(f"Final canonical_evidence count: {len(final_can_ev)}")
for item in final_can_ev:
    print(f"  field={item.get('source_field')} | id={item.get('evidence_id')} | val={str(item.get('observed_value'))[:40]}")
