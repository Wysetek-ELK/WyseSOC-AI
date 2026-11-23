import sys
sys.path.insert(0, 'backend')
from app.models.rule import Rule
from app.services.evidence_contract_service import EvidenceContractService

rule = Rule(
    id='0974a66e-ede2-4a6a-821b-6283a99c8aa4',
    name='Crowdstrike: Suspicious Activity',
    rule_id='PH_RULE_CS_SUSPICIOUS_ACTIVITY',
    event_type='PH_RULE_CS_SUSPICIOUS_ACTIVITY',
    severity=5
)
contract = EvidenceContractService.get_contract_for_rule(rule, None)
for r in contract.required_evidence:
    print(f"field={r.field}, level={getattr(r, 'requirement_level', None)}, critical={r.critical}")
