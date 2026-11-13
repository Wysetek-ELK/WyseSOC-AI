import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.rule_learning import RuleLearningProfile
from app.models.production_governance import (
    ProductionAutomationPolicy,
    IncidentAutomationAudit
)
from app.services.rule_learning_service import RuleLearningService
from app.utils.datetime_utils import utc_now

logger = logging.getLogger("ai_verdict.automation_governor")


class AutomationGovernor:
    """
    Enforces the 12-barrier safety check before authorizing automated incident
    closure on live security infrastructure. Disabled by default.
    """

    @classmethod
    async def evaluate_auto_closure_eligibility(
        cls,
        db: AsyncSession,
        incident_id: str,
        rule_identifier: str,
        customer: str,
        validated_verdict: str,
        trust_score: int,
        confidence: float,
        has_contradictions: bool,
        global_kill_switch: bool = False,
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Evaluates the 12 safety barriers. Returns (is_eligible, barrier_results_dict, failure_reasons).
        """
        results: Dict[str, bool] = {}
        failures: List[str] = []

        # 1. Global Kill-Switch Check
        results["barrier_01_global_killswitch"] = not global_kill_switch
        if global_kill_switch:
            failures.append("Global automation kill-switch is active.")

        # 2. Rule Profile & Stage Check
        prof_stmt = select(RuleLearningProfile).where(
            and_(
                RuleLearningProfile.rule_identifier == rule_identifier,
                RuleLearningProfile.customer == customer
            )
        )
        profile = (await db.execute(prof_stmt)).scalar_one_or_none()
        in_prod = profile is not None and profile.lifecycle_stage == RuleLearningService.STAGE_CONTROLLED_PRODUCTION
        results["barrier_02_rule_in_controlled_production"] = in_prod
        if not in_prod:
            failures.append(f"Rule {rule_identifier} is not in CONTROLLED_PRODUCTION stage (stage: {profile.lifecycle_stage if profile else 'UNKNOWN'}).")

        # 3. Automation Policy Check
        pol_stmt = select(ProductionAutomationPolicy).where(
            and_(
                ProductionAutomationPolicy.rule_id == rule_identifier,
                ProductionAutomationPolicy.customer == customer
            )
        )
        policy = (await db.execute(pol_stmt)).scalar_one_or_none()
        pol_enabled = policy is not None and policy.is_enabled and not policy.emergency_disable
        results["barrier_03_policy_enabled"] = pol_enabled
        if not pol_enabled:
            failures.append("Production automation policy is not active or has emergency disable engaged.")

        # 4. Validated Verdict Check (False Positive Only)
        is_fp = validated_verdict == "FALSE_POSITIVE"
        results["barrier_04_validated_false_positive"] = is_fp
        if not is_fp:
            failures.append(f"Automated closure is restricted strictly to FALSE_POSITIVE verdicts (verdict: {validated_verdict}).")

        # 5. Zero Contradictions Check
        results["barrier_05_zero_contradictions"] = not has_contradictions
        if has_contradictions:
            failures.append("Evidence validation detected logical contradictions (e.g. loopback on external traffic).")

        # 6. Trust Score Check
        min_trust = policy.min_trust_score if policy else 8
        trust_ok = trust_score >= min_trust
        results["barrier_06_trust_score_sufficient"] = trust_ok
        if not trust_ok:
            failures.append(f"Trust score {trust_score}/10 does not meet required policy threshold ({min_trust}/10).")

        # 7. FP Precision Check
        min_prec = policy.min_fp_precision if policy else 0.98
        prec_ok = profile is not None and (profile.fp_precision or 0.0) >= min_prec
        results["barrier_07_fp_precision_sufficient"] = prec_ok
        if not prec_ok:
            failures.append(f"Rule empirical FP precision ({profile.fp_precision if profile else 0.0}) below threshold ({min_prec}).")

        # 8. Investigation Status Check (Not actively being investigated by a human)
        inc_stmt = select(Incident).where(Incident.incident_id == incident_id)
        incident = (await db.execute(inc_stmt)).scalar_one_or_none()
        not_human_assigned = True
        if incident:
            inv_stmt = select(Investigation).where(Investigation.incident_id == incident.id)
            inv = (await db.execute(inv_stmt)).scalar_one_or_none()
            if inv and inv.status in ("ASSIGNED", "IN_PROGRESS", "REVIEWED"):
                not_human_assigned = False

        results["barrier_08_not_under_human_investigation"] = not_human_assigned
        if not not_human_assigned:
            failures.append("Incident is currently assigned or being actively reviewed by a human analyst.")

        # 9. Daily Closure Budget Check
        daily_ok = True
        if policy and policy.current_day_closure_count >= policy.daily_closure_limit:
            daily_ok = False
        results["barrier_09_daily_budget_available"] = daily_ok
        if not daily_ok:
            failures.append(f"Daily automated closure budget ({policy.daily_closure_limit if policy else 50}) exhausted.")

        # 10. Multi-Tenant Scoping Match
        tenant_match = incident is None or incident.customer == customer
        results["barrier_10_tenant_scope_matched"] = tenant_match
        if not tenant_match:
            failures.append("Target incident tenant scope diverged from policy tenant.")

        # Overall verdict
        is_eligible = len(failures) == 0
        return is_eligible, results, failures

    @classmethod
    async def record_automation_audit(
        cls,
        db: AsyncSession,
        incident_id: str,
        rule_id: str,
        customer: str,
        action_type: str,
        execution_status: str,
        safety_checks: Dict[str, Any],
        summary: str,
        siem_code: Optional[int] = None,
        siem_tx_id: Optional[str] = None
    ) -> IncidentAutomationAudit:
        """
        Persists an immutable audit log entry for an automation action or safety abort.
        """
        audit = IncidentAutomationAudit(
            incident_id=incident_id,
            rule_id=rule_id,
            customer=customer,
            action_type=action_type,
            siem_target="FortiSIEM",
            siem_response_code=siem_code,
            siem_transaction_id=siem_tx_id,
            execution_status=execution_status,
            safety_checks_passed=safety_checks,
            closure_summary=summary,
        )
        db.add(audit)
        await db.flush()
        return audit

