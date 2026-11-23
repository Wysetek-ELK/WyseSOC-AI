import zipfile, json, os

z = zipfile.ZipFile('fixtures/Incident json.zip')
records = []
for name in sorted(z.namelist()):
    if not name.endswith('.json'):
        continue
    raw = json.loads(z.open(name).read().decode('utf-8', 'ignore'))
    inc_id = str(raw.get('incidentId') or raw.get('id'))
    res = raw.get('resolution') or ''
    reason = str(raw.get('clearedReason') or '').strip()
    comments = str(raw.get('comments') or '').strip()
    user = str(raw.get('clearedUser') or '').strip()
    rule = 'Crowdstrike' if 'Crowdstrike' in name else 'Prisma SASE'
    
    res_lower = res.lower()
    reason_lower = (reason + ' ' + comments).lower()
    
    tier = 'UNVERIFIED'
    rationale = ''
    
    if not reason and not comments:
        tier = 'UNVERIFIED'
        rationale = 'No cleared reason or analyst comments provided.'
    elif any(k in reason_lower for k in ['kill process', 'proccess is kiled', 'process is killed']):
        tier = 'PROVISIONAL_ANALYST_FP'
        rationale = 'Analyst marked False Positive but note indicates containment action (process killed), representing operational containment ambiguity.'
    elif 'legitimate activity' in reason_lower or 'clean' in reason_lower or 'not suspicious' in reason_lower or 'not found suspicious' in reason_lower:
        tier = 'VERIFIED_ANALYST_FP'
        rationale = f'Analyst confirmed benign/clean status: "{reason}"'
    elif any(k in reason_lower for k in ['case raised', 'client are working', 'informed to client', 'mail has been sent', 'endpoint security has blocked', 'case has been raised']):
        tier = 'PROVISIONAL_ANALYST_TP'
        rationale = f'Operational triage / escalation without forensic IOC confirmation: "{reason}"'
    elif 'true positive' in res_lower:
        tier = 'VERIFIED_ANALYST_TP'
        rationale = f'Confirmed true positive: "{reason}"'
    elif 'false positive' in res_lower:
        tier = 'VERIFIED_ANALYST_FP'
        rationale = f'Confirmed false positive: "{reason}"'
        
    records.append((inc_id, rule, res, tier, reason, rationale))

print("=== MULTI-TIER GROUND TRUTH CLASSIFICATION ===")
tier_counts = {}
for inc_id, rule, res, tier, reason, rationale in records:
    tier_counts[tier] = tier_counts.get(tier, 0) + 1
    print(f"{inc_id} ({rule:11}) | Raw: {res:14} | Tier: {tier:23} | Reason: {reason[:45]}")

print("\nTier Census:")
for t, c in sorted(tier_counts.items()):
    print(f"  {t:25}: {c}")
