import sys
sys.path.insert(0, 'backend')
import zipfile, json
from app.models.incident import Incident
from app.models.rule import Rule
from app.services.empirical_benchmark_harness import EventAdapter
from app.services.verdict_pipeline import build_sanitized_model_payload
from app.services.evidence_compaction_service import EvidenceCompactionService
from app.schemas.canonical_evidence import CanonicalEvidenceRecord

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
rec_objs = [CanonicalEvidenceRecord(**item) for item in payload_dict.get("canonical_evidence", [])]

# What did TokenBudgetService pass as contract_req?
# Notice: contract_info from compiled policy or contract:
# In TokenBudgetService line 355:
# contract_req = list(dict.fromkeys(
#     list(contract_info.get("required_fields") or [])
#     + list(contract_info.get("conditional_fields") or [])
#     + _orig_conditional_fields
# ))
# If contract_info came from the compiled policy or contract, what were required_fields and conditional_fields?

for c_req in [
    ['process.name', 'process.command_line', 'endpoint.hostname', 'user.name', 'event.timestamp'], # Without conditional fields
    ['process.name', 'process.command_line', 'endpoint.hostname', 'user.name', 'event.timestamp', 'process.parent_name', 'file.hash_sha256'] # With conditional fields
]:
    res = EvidenceCompactionService.compact_and_deduplicate(
        records=rec_objs,
        contract_required_fields=c_req,
        rule_pattern_logic="",
        max_evidence_budget_tokens=1500,
    )
    compacted = res["compacted_records"]
    c_fields = [r["source_field"] for r in compacted]
    print(f"\n--- contract_req={c_req} ---")
    print(f"Count: {len(compacted)}")
    print(f"Has process.name: {'process.name' in c_fields}")
    print(f"Has process.file_name: {'process.file_name' in c_fields}")
    print(f"Has process.parent_name: {'process.parent_name' in c_fields}")
    print(f"Has file.hash_sha256: {'file.hash_sha256' in c_fields}")
    print("Compacted fields:", c_fields)
