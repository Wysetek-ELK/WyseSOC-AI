import json

with open('scratch/capture_132499009.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

payload_str = d.get('incident_payload', '')
cleaned = payload_str.replace('<UNTRUSTED_INCIDENT_DATA>\n', '').replace('\n</UNTRUSTED_INCIDENT_DATA>', '')
payload_json = json.loads(cleaned)
inc = payload_json.get('incident', {})
can_ev = inc.get('canonical_evidence', [])
print(f"Total canonical evidence in Prisma capture: {len(can_ev)}")
for item in can_ev:
    print(f"  id={item.get('evidence_id')} | field={item.get('source_field')} | val={item.get('observed_value')}")
