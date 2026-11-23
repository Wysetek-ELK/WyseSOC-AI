import sys
sys.path.insert(0, 'backend')
import zipfile, json
from app.models.incident import Incident
from app.services.empirical_benchmark_harness import EventAdapter
from app.services.evidence_normalization_service import EvidenceNormalizationService

with zipfile.ZipFile('fixtures/Incident json.zip', 'r') as z:
    raw_data = json.loads(z.read('Incident json/Prisma SASE Suspicious File Threat Detection/incidentId_132499009.json').decode('utf-8'))

raw_events = [EventAdapter(e, i) for i, e in enumerate(raw_data.get('rawEvents', []))]
inc = Incident(
    id='test-132499009',
    incident_id=132499009,
    title=raw_data.get('title'),
    event_type=raw_data.get('eventType'),
    severity=raw_data.get('severity', 5),
    raw_payload=raw_data
)

norm_res = EvidenceNormalizationService.normalize_incident_evidence(inc, raw_events)
print(f"Total canonical records: {len(norm_res.records)}")
for r in norm_res.records:
    print(f"  {r.evidence_id}: source_field={r.source_field} raw={r.raw_field_name} val={str(r.observed_value)[:50]}")
