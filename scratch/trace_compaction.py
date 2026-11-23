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
can_ev = payload_dict.get("canonical_evidence", [])
print(f"Total raw canonical_evidence: {len(can_ev)}")

rec_objs = [CanonicalEvidenceRecord(**item) for item in can_ev]
fields = [r.source_field for r in rec_objs]
print("Is 'process.file_name' in rec_objs?", 'process.file_name' in fields)
print("Is 'process.parent_name' in rec_objs?", 'process.parent_name' in fields)
print("Is 'process.name' in rec_objs?", 'process.name' in fields)

contract_req = ['process.name', 'process.command_line', 'endpoint.hostname', 'user.name', 'event.timestamp', 'process.parent_name', 'file.hash_sha256']
print("contract_req:", contract_req)

res = EvidenceCompactionService.compact_and_deduplicate(
    records=rec_objs,
    contract_required_fields=contract_req,
    rule_pattern_logic="",
    max_evidence_budget_tokens=1500,
)
compacted = res["compacted_records"]
c_fields = [r["source_field"] for r in compacted]
print(f"Compacted records count: {len(compacted)}")
print("Is 'process.file_name' in compacted?", 'process.file_name' in c_fields)
print("Is 'process.parent_name' in compacted?", 'process.parent_name' in c_fields)
print("Is 'process.name' in compacted?", 'process.name' in c_fields)
