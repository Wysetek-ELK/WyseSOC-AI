import zipfile, json, os
from datetime import datetime, timezone

z = zipfile.ZipFile('fixtures/Incident json.zip')
records = []
for name in sorted(z.namelist()):
    if not name.endswith('.json'):
        continue
    raw_data = json.loads(z.open(name).read().decode('utf-8', 'ignore'))
    inc_id = str(raw_data.get('incidentId') or raw_data.get('id'))
    evs = raw_data.get('rawEvents') or raw_data.get('events') or []
    target = str(raw_data.get('target') or raw_data.get('incidentTarget') or raw_data.get('reportingDevice') or 'none').strip()
    rule_name = 'Crowdstrike' if 'Crowdstrike' in name else 'Prisma SASE'
    
    file_names = set()
    hashes = set()
    src_ips = set()
    dst_ips = set()
    event_ids = []
    
    for e in evs:
        attr = e.get('attribute', {})
        event_ids.append(str(e.get('eventId') or attr.get('Event ID')))
        fn = attr.get('File Name') or attr.get('fileName')
        if fn: file_names.add(fn)
        h = attr.get('SHA256 Hash') or attr.get('MD5 Hash') or attr.get('hash')
        if h: hashes.add(h)
        sip = attr.get('Source IP') or attr.get('Host IP')
        if sip: src_ips.add(sip)
        dip = attr.get('Destination IP')
        if dip: dst_ips.add(dip)
        
    res = raw_data.get('resolution')
    cleared_reason = raw_data.get('clearedReason') or ''
    comments = raw_data.get('comments') or ''
    cleared_user = raw_data.get('clearedUser') or ''
    first_seen = raw_data.get('firstSeen')
    
    records.append({
        'id': inc_id,
        'rule': rule_name,
        'target': target,
        'events_count': len(evs),
        'first_seen': first_seen,
        'first_seen_str': datetime.fromtimestamp(first_seen/1000, timezone.utc).isoformat() if first_seen else 'N/A',
        'file_names': list(file_names),
        'hashes': list(hashes),
        'src_ips': list(src_ips),
        'dst_ips': list(dst_ips),
        'res': res,
        'cleared_user': cleared_user,
        'cleared_reason': cleared_reason,
        'comments': comments,
        'event_ids': event_ids,
    })

print(f"Total records: {len(records)}")
print("\n=== PRISMA SASE INCIDENTS ===")
prisma = [r for r in records if r['rule'] == 'Prisma SASE']
for p in sorted(prisma, key=lambda x: (x['target'], x['events_count'], x['first_seen'])):
    print(f"ID: {p['id']} | Target: {p['target']:25} | Evts: {p['events_count']:2} | Time: {p['first_seen_str']} | Files: {p['file_names'][:2]} | Sip: {p['src_ips'][:2]} | Res: {p['res']}")
    print(f"   Reason: {p['cleared_reason'][:80]}")
    print(f"   Event IDs: {p['event_ids'][:3]}")

print("\n=== CROWDSTRIKE INCIDENTS ===")
cs = [r for r in records if r['rule'] == 'Crowdstrike']
for c in sorted(cs, key=lambda x: (x['target'], x['events_count'], x['first_seen'])):
    print(f"ID: {c['id']} | Target: {c['target']:25} | Evts: {c['events_count']:2} | Time: {c['first_seen_str']} | Files: {c['file_names'][:2]} | Sip: {c['src_ips'][:2]} | Res: {c['res']}")
    print(f"   Reason: {c['cleared_reason'][:80]}")
    print(f"   Event IDs: {c['event_ids'][:3]}")
