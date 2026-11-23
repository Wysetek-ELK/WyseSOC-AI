import sys
sys.path.insert(0, 'backend')
import zipfile, json
from app.models.incident import Incident
from app.services.empirical_benchmark_harness import EventAdapter
from app.services.evidence_normalization_service import EvidenceNormalizationService

with zipfile.ZipFile('fixtures/Incident json.zip', 'r') as z:
    for name in z.namelist():
        if 'Crowdstrike' in name and name.endswith('.json'):
            raw_data = json.loads(z.read(name).decode('utf-8'))
            inc_id = raw_data.get('incidentId')
            raw_events = [EventAdapter(e, i) for i, e in enumerate(raw_data.get('rawEvents', []))]
            inc = Incident(
                id=f'test-{inc_id}',
                incident_id=inc_id,
                title=raw_data.get('title'),
                event_type=raw_data.get('eventType'),
                severity=raw_data.get('severity', 5),
                raw_payload=raw_data
            )
            norm = EvidenceNormalizationService.normalize_incident_evidence(inc, raw_events)
            fields = {r.source_field: str(r.observed_value)[:30] for r in norm.records}
            has_pname = "process.name" in fields
            has_pfname = "process.file_name" in fields
            has_ppname = "process.parent_name" in fields
            has_sha256 = "file.hash_sha256" in fields
            has_cmd = "process.command_line" in fields
            print(f"Incident {inc_id}: p.name={has_pname}, p.file_name={has_pfname} ({fields.get('process.file_name')}), p.parent_name={has_ppname} ({fields.get('process.parent_name')}), sha256={has_sha256}, cmd={has_cmd}")
