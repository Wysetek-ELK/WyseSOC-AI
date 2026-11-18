import logging
import uuid
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.prompt import RulePrompt
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
    Enforces all 12 safety barriers before authorizing automated incident closure on
    FortiSIEM, and governs controlled incident routing for TRUE_POSITIVE, FALSE_POSITIVE,
    and INSUFFICIENT_EVIDENCE verdicts. Automatic closure is strictly disabled by default.
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
        prompt_version_id: Optional[str] = None,
        model_identifier: Optional[str] = None,
    ) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Evaluates all 12 safety barriers. Returns (is_eligible, barrier_results_dict, failure_reasons).
        """
        results: Dict[str, bool] = {}
        failures: List[str] = []

        # 1. Global Kill-Switch Check
        results["barrier_01_global_killswitch"] = not global_kill_switch
        if global_kill_switch:
            failures.append("Global automation kill-switch is active.")

        # 2. Rule Profile & Controlled Production / Monitoring Stage Check
        prof_stmt = select(RuleLearningProfile).where(
            and_(
                or_(
                    RuleLearningProfile.rule_identifier == rule_identifier,
                    RuleLearningProfile.rule_id == rule_identifier,
                ),
                RuleLearningProfile.customer == customer,
            )
        )
        profile = (await db.execute(prof_stmt)).scalars().first()
        in_prod = profile is not None and profile.lifecycle_stage in (
            RuleLearningService.STAGE_CONTROLLED_PRODUCTION,
            RuleLearningService.STAGE_MONITORING,
        )
        results["barrier_02_rule_in_controlled_production"] = in_prod
        if not in_prod:
            failures.append(
                f"Rule {rule_identifier} is not in CONTROLLED_PRODUCTION stage "
                f"(stage: {profile.lifecycle_stage if profile else 'UNKNOWN'})."
            )

        # 3. Rule-Scoped Automation Policy Check
        pol_stmt = select(ProductionAutomationPolicy).where(
            and_(
                or_(
                    ProductionAutomationPolicy.rule_id == rule_identifier,
                    ProductionAutomationPolicy.profile_id == (profile.id if profile else "__none__"),
                ),
                ProductionAutomationPolicy.customer == customer,
            )
        )
        policy = (await db.execute(pol_stmt)).scalars().first()
        pol_enabled = policy is not None and bool(policy.is_enabled) and not bool(policy.emergency_disable)
        results["barrier_03_policy_enabled"] = pol_enabled
        if not pol_enabled:
            failures.append("Production automation policy is not active or has emergency disable engaged.")

        # 4. Validated Verdict Check (False Positive Only — NEVER auto-close TP or Insufficient Evidence)
        norm_verdict = str(validated_verdict or "").upper().strip()
        is_fp = norm_verdict == "FALSE_POSITIVE"
        results["barrier_04_validated_false_positive"] = is_fp
        if not is_fp:
            failures.append(
                f"Automated closure is restricted strictly to FALSE_POSITIVE verdicts (verdict: {norm_verdict})."
            )

        # 5. Zero Contradictions Check
        results["barrier_05_zero_contradictions"] = not has_contradictions
        if has_contradictions:
            failures.append("Evidence validation detected logical contradictions or unsupported assertions.")

        # 6. Trust Score Check
        min_trust = policy.min_trust_score if policy else 8
        trust_ok = int(trust_score) >= int(min_trust)
        results["barrier_06_trust_score_sufficient"] = trust_ok
        if not trust_ok:
            failures.append(
                f"Trust score {trust_score}/10 does not meet required policy threshold ({min_trust}/10)."
            )

        # 7. Empirical FP Precision (>= 99%), Accuracy (>= 95%), Wilson LB (>= 96%), & Zero Missed TP Check
        min_prec = max(RuleLearningService.MIN_PRODUCTION_FP_PRECISION, float(policy.min_fp_precision)) if policy else RuleLearningService.MIN_PRODUCTION_FP_PRECISION
        missed_tp_count = int((profile.error_distribution or {}).get("critical_missed_tp", 0)) if profile else 0
        emp_acc = float(profile.empirical_accuracy or 0.0) if profile else 0.0
        fp_prec = float(profile.fp_precision or 0.0) if profile else 0.0
        wilson_lb = float(profile.wilson_lower_bound or 0.0) if profile else 0.0
        prec_ok = (
            profile is not None
            and fp_prec >= min_prec
            and emp_acc >= RuleLearningService.MIN_PRODUCTION_ACCURACY
            and wilson_lb >= RuleLearningService.MIN_PRODUCTION_WILSON_LOWER
            and missed_tp_count == 0
        )
        results["barrier_07_fp_precision_sufficient"] = prec_ok
        if not prec_ok:
            failures.append(
                f"Empirical safety gate unmet (FP precision={fp_prec:.3f} vs {min_prec:.2f}, "
                f"accuracy={emp_acc:.3f} vs 0.95, wilson_lb={wilson_lb:.3f} vs 0.96, missed_tp={missed_tp_count})."
            )

        # 8. Investigation Status Check (Not actively being investigated by a human)
        inc_stmt = select(Incident).where(
            or_(Incident.incident_id == str(incident_id), Incident.id == str(incident_id))
        )
        incident = (await db.execute(inc_stmt)).scalars().first()
        not_human_assigned = True
        if incident:
            inv_stmt = select(Investigation).where(Investigation.incident_id == incident.id)
            inv = (await db.execute(inv_stmt)).scalars().first()
            if inv and inv.status in ("ASSIGNED", "IN_PROGRESS", "REVIEWED", "DISPUTED"):
                not_human_assigned = False

        results["barrier_08_not_under_human_investigation"] = not_human_assigned
        if not not_human_assigned:
            failures.append("Incident is currently assigned, reviewed, or disputed by a human analyst.")

        # 9. UTC Daily Closure Budget Check (derived dynamically from today's live closure audits + counter)
        daily_limit = int(policy.daily_closure_limit) if policy else 50
        day_start = utc_now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_closures = 0
        if policy:
            cnt_res = await db.execute(
                select(func.count(IncidentAutomationAudit.id)).where(
                    and_(
                        IncidentAutomationAudit.rule_id == policy.rule_id,
                        IncidentAutomationAudit.customer == customer,
                        IncidentAutomationAudit.action_type == "AUTO_CLOSE_FP",
                        IncidentAutomationAudit.execution_status.in_(["CLOSED_AND_VERIFIED", "CLOSED_PENDING_RECONCILIATION"]),
                        IncidentAutomationAudit.executed_at >= day_start,
                    )
                )
            )
            today_closures = max(int(cnt_res.scalar() or 0), int(policy.current_day_closure_count or 0))
        daily_ok = today_closures < daily_limit
        results["barrier_09_daily_budget_available"] = daily_ok
        if not daily_ok:
            failures.append(f"Daily automated closure budget ({today_closures}/{daily_limit}) exhausted.")

        # 10. Multi-Tenant Scoping Match
        tenant_match = incident is None or (incident.customer or "DEFAULT") == customer
        results["barrier_10_tenant_scope_matched"] = tenant_match
        if not tenant_match:
            failures.append("Target incident tenant scope diverged from policy tenant.")

        # 11. Active Approved Policy & Non-Suspended AI Execution Check
        policy_active_ok = True
        if profile:
            rp_res = await db.execute(select(RulePrompt).where(RulePrompt.rule_id == profile.rule_id))
            rp = rp_res.scalar_one_or_none()
            if rp and getattr(rp, "ai_execution_suspended", False):
                policy_active_ok = False
                failures.append(f"Rule AI execution is suspended: {rp.suspension_reason or 'suspended'}.")
            elif rp and prompt_version_id and rp.active_version_id and str(rp.active_version_id) != str(prompt_version_id):
                policy_active_ok = False
                failures.append("Verdict was not produced by the currently approved active prompt version.")
        results["barrier_11_approved_policy_active"] = policy_active_ok

        # 12. Idempotency / Duplicate Closure Guard
        dup_res = await db.execute(
            select(IncidentAutomationAudit).where(
                and_(
                    IncidentAutomationAudit.incident_id == str(incident_id),
                    IncidentAutomationAudit.action_type == "AUTO_CLOSE_FP",
                    IncidentAutomationAudit.execution_status.in_(["CLOSED_AND_VERIFIED", "ALREADY_CLOSED_IN_SIEM"]),
                )
            ).limit(1)
        )
        not_already_closed = dup_res.scalar_one_or_none() is None
        results["barrier_12_idempotent_not_closed"] = not_already_closed
        if not not_already_closed:
            failures.append(f"Incident {incident_id} was already closed via governed automation (idempotent guard).")

        is_eligible = len(failures) == 0
        return is_eligible, results, failures

    @classmethod
    async def execute_governed_incident_decision(
        cls,
        db: AsyncSession,
        incident_id: str,
        customer: Optional[str] = None,
        dry_run: bool = True,
        siem_service: Optional[Any] = None,
        global_kill_switch: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes the full governed production incident decision workflow:
          - AI TRUE_POSITIVE: NEVER auto-closes; routes to SOC analyst with evidence & recommendations.
          - AI INSUFFICIENT_EVIDENCE / REQUIRES_ATTENTION: NEVER auto-closes; routes to manual investigation.
          - AI FALSE_POSITIVE: evaluates all 12 barriers; closes via FortiSIEM (dry-run or live) ONLY when
            all 12 barriers pass, otherwise routes safely to manual review without closing.
        """
        from app.services.fortisiem_service import FortiSIEMService

        inc_stmt = select(Incident).where(
            or_(Incident.incident_id == str(incident_id), Incident.id == str(incident_id))
        )
        incident = (await db.execute(inc_stmt)).scalars().first()
        if not incident:
            raise ValueError(f"Incident '{incident_id}' not found.")

        eff_customer = customer or incident.customer or "DEFAULT"
        ai_v = incident.ai_verdict if isinstance(incident.ai_verdict, dict) else {}
        verdict = str(ai_v.get("verdict") or ai_v.get("effective_verdict") or "INSUFFICIENT_EVIDENCE").upper().strip()
        if verdict in ("REQUIRES_ATTENTION", "REQUIRES_ANALYST_ATTENTION", "ABSTAIN", "UNKNOWN", ""):
            verdict = "INSUFFICIENT_EVIDENCE"

        rule_ref = incident.event_type or incident.rule_id or "UNKNOWN_RULE"
        trust_score = int(ai_v.get("trust_score") or 0)
        confidence = float(ai_v.get("confidence") or 0.0)
        reason = str(ai_v.get("reason") or ai_v.get("reasoning") or "")
        supporting_ev = ai_v.get("supporting_evidence") or []
        missing_ev = ai_v.get("missing_evidence") or []
        recommended_actions = ai_v.get("analyst_questions") or ai_v.get("recommended_actions") or []
        prompt_ver = ai_v.get("prompt_version_number")
        prompt_ver_id = ai_v.get("prompt_version_id")
        model_id = str(ai_v.get("model_identifier") or "UNKNOWN_MODEL")
        has_contradictions = bool(
            ai_v.get("contradictory_evidence")
            or ai_v.get("has_contradictions")
            or str(ai_v.get("validation_status") or "").upper() in ("INVALID_SCHEMA", "INVALID_INCIDENT_REF", "INVALID_CONFIDENCE", "EVIDENCE_CONTRADICTION")
        )

        # Branch 1: AI TRUE_POSITIVE -> NEVER auto-close, route to SOC analyst
        if verdict == "TRUE_POSITIVE":
            summary = (
                f"Routed TRUE_POSITIVE incident {incident.incident_id} to SOC Analyst queue (incident kept OPEN). "
                f"Model={model_id}, PromptV={prompt_ver}. Reason: {reason[:300]}"
            )
            audit = await cls.record_automation_audit(
                db=db,
                incident_id=str(incident.incident_id),
                rule_id=rule_ref,
                customer=eff_customer,
                action_type="ROUTE_TO_ANALYST_TP",
                execution_status="ROUTED_OPEN_FOR_ANALYST",
                safety_checks={"auto_closure_attempted": False, "verdict": "TRUE_POSITIVE"},
                summary=summary,
            )
            return {
                "incident_id": str(incident.incident_id),
                "rule_id": rule_ref,
                "customer": eff_customer,
                "verdict": "TRUE_POSITIVE",
                "action_taken": "ROUTE_TO_ANALYST_TP",
                "execution_status": "ROUTED_OPEN_FOR_ANALYST",
                "incident_closed": False,
                "dry_run": dry_run,
                "audit_id": audit.id,
                "affected_assets": [x for x in (incident.source_ip, incident.reporting_device, incident.reporting_ip) if x],
                "reasoning": reason,
                "supporting_evidence": supporting_ev,
                "recommended_actions": recommended_actions,
            }

        # Branch 2: AI INSUFFICIENT_EVIDENCE -> NEVER auto-close, route to manual investigation
        if verdict != "FALSE_POSITIVE":
            summary = (
                f"Routed {verdict} incident {incident.incident_id} to manual SOC investigation (incident kept OPEN). "
                f"Missing evidence: {', '.join(str(m) for m in missing_ev[:5]) or 'unspecified'}."
            )
            audit = await cls.record_automation_audit(
                db=db,
                incident_id=str(incident.incident_id),
                rule_id=rule_ref,
                customer=eff_customer,
                action_type="ROUTE_TO_MANUAL_REVIEW",
                execution_status="ROUTED_MANUAL_INSUFFICIENT_EVIDENCE",
                safety_checks={"auto_closure_attempted": False, "verdict": verdict},
                summary=summary,
            )
            return {
                "incident_id": str(incident.incident_id),
                "rule_id": rule_ref,
                "customer": eff_customer,
                "verdict": verdict,
                "action_taken": "ROUTE_TO_MANUAL_REVIEW",
                "execution_status": "ROUTED_MANUAL_INSUFFICIENT_EVIDENCE",
                "incident_closed": False,
                "dry_run": dry_run,
                "audit_id": audit.id,
                "missing_evidence": missing_ev,
                "reasoning": reason,
            }

        # Branch 3: AI FALSE_POSITIVE -> Evaluate all 12 safety barriers
        is_eligible, barriers, failures = await cls.evaluate_auto_closure_eligibility(
            db=db,
            incident_id=str(incident.incident_id),
            rule_identifier=rule_ref,
            customer=eff_customer,
            validated_verdict="FALSE_POSITIVE",
            trust_score=trust_score,
            confidence=confidence,
            has_contradictions=has_contradictions,
            global_kill_switch=global_kill_switch,
            prompt_version_id=prompt_ver_id,
            model_identifier=model_id,
        )

        if not is_eligible:
            summary = (
                f"Blocked FP auto-closure for incident {incident.incident_id}; routed to manual review (incident kept OPEN). "
                f"Failing barriers: {'; '.join(failures)}"
            )
            audit = await cls.record_automation_audit(
                db=db,
                incident_id=str(incident.incident_id),
                rule_id=rule_ref,
                customer=eff_customer,
                action_type="AUTO_CLOSE_FP_BLOCKED",
                execution_status="BLOCKED_SAFETY_BARRIER",
                safety_checks=barriers,
                summary=summary,
            )
            return {
                "incident_id": str(incident.incident_id),
                "rule_id": rule_ref,
                "customer": eff_customer,
                "verdict": "FALSE_POSITIVE",
                "action_taken": "ROUTE_TO_MANUAL_REVIEW",
                "execution_status": "BLOCKED_SAFETY_BARRIER",
                "incident_closed": False,
                "dry_run": dry_run,
                "audit_id": audit.id,
                "barriers": barriers,
                "blocking_reasons": failures,
            }

        # All 12 barriers passed! Execute dry-run or controlled live FortiSIEM closure
        audit_id_pre = str(uuid.uuid4())
        siem = siem_service or FortiSIEMService(db)
        closure_comments = (
            f"Verdictum AI Governed FP Closure | AuditID={audit_id_pre} | Rule={rule_ref} | "
            f"Model={model_id} | PromptVersion={prompt_ver} | Trust={trust_score}/10 | "
            f"Evidence={','.join(str(e) for e in supporting_ev[:5])} | Reason={reason[:300]}"
        )
        siem_res = await siem.close_incident_in_fortisiem(
            incident_id=str(incident.incident_id),
            resolution_reason=f"Verified False Positive via Verdictum AI ({rule_ref})",
            comments=closure_comments,
            audit_id=audit_id_pre,
            dry_run=dry_run,
        )

        exec_status = str(siem_res.get("execution_status") or "FAILED")
        audit = IncidentAutomationAudit(
            id=audit_id_pre,
            incident_id=str(incident.incident_id),
            rule_id=rule_ref,
            customer=eff_customer,
            action_type="AUTO_CLOSE_FP_DRY_RUN" if dry_run else "AUTO_CLOSE_FP",
            siem_target="FortiSIEM",
            siem_response_code=siem_res.get("siem_status_code"),
            siem_transaction_id=siem_res.get("siem_transaction_id"),
            execution_status=exec_status,
            safety_checks_passed=barriers,
            closure_summary=closure_comments,
        )
        db.add(audit)

        # Increment daily counter ONLY on real live closure (never dry-run)
        if not dry_run and siem_res.get("ok") and exec_status in ("CLOSED_AND_VERIFIED", "CLOSED_PENDING_RECONCILIATION"):
            pol_stmt = select(ProductionAutomationPolicy).where(
                and_(
                    ProductionAutomationPolicy.rule_id == rule_ref,
                    ProductionAutomationPolicy.customer == eff_customer,
                )
            )
            pol = (await db.execute(pol_stmt)).scalars().first()
            if pol:
                pol.current_day_closure_count = int(pol.current_day_closure_count or 0) + 1
                db.add(pol)

        await db.flush()
        return {
            "incident_id": str(incident.incident_id),
            "rule_id": rule_ref,
            "customer": eff_customer,
            "verdict": "FALSE_POSITIVE",
            "action_taken": "AUTO_CLOSE_FP_DRY_RUN" if dry_run else "AUTO_CLOSE_FP",
            "execution_status": exec_status,
            "incident_closed": bool(not dry_run and siem_res.get("ok")),
            "remote_verified": bool(siem_res.get("remote_verified")),
            "dry_run": dry_run,
            "audit_id": audit.id,
            "siem_transaction_id": siem_res.get("siem_transaction_id"),
            "siem_response_code": siem_res.get("siem_status_code"),
            "barriers": barriers,
            "message": siem_res.get("message"),
        }

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
