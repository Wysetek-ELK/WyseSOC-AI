import sys
sys.path.insert(0, 'backend')
import zipfile, json
from app.models.incident import Incident
from app.models.rule import Rule
from app.services.empirical_benchmark_harness import EventAdapter
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.verdict_pipeline import build_sanitized_model_payload

with zipfile.ZipFile('fixtures/Incident json.zip', 'r') as z:
    cs_data = json.loads(z.read('Incident json/Crowdstrike Suspicious Activity/IncidnetId_132438483.json').decode('utf-8'))
    prisma_data = json.loads(z.read('Incident json/Prisma SASE Suspicious File Threat Detection/incidentId_132499009.json').decode('utf-8'))

for label, raw_data, rid, rname in [
    ("Crowdstrike", cs_data, "0974a66e-ede2-4a6a-821b-6283a99c8aa4", "Crowdstrike: Suspicious Activity"),
    ("Prisma SASE", prisma_data, "14481ebd-4e8c-421e-8579-b6ee7995b746", "Prisma SASE: Suspicious File Threat Detection")
]:
    print(f"\n=================== {label} ===================")
    raw_events = [EventAdapter(e, i) for i, e in enumerate(raw_data.get('rawEvents', []))]
    inc = Incident(
        id=f'test-{raw_data.get("incidentId")}',
        incident_id=raw_data.get("incidentId"),
        title=raw_data.get('title'),
        event_type=raw_data.get('eventType'),
        severity=raw_data.get('severity', 5),
        raw_payload=raw_data
    )
    rule = Rule(
        id=rid,
        name=rname,
        rule_id=f"PH_RULE_{label.upper()}",
        event_type=f"PH_RULE_{label.upper()}",
        severity=5
    )
    norm_res, payload_dict = build_sanitized_model_payload(inc, rule)
    print("Total normalized records:", len(norm_res.records))
    
    n_fields = [r.source_field for r in norm_res.records]
    print("In norm_res: process.name?", "process.name" in n_fields,
          "| process.file_name?", "process.file_name" in n_fields,
          "| process.parent_name?", "process.parent_name" in n_fields)
