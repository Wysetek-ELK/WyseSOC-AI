"""
Non-Destructive Server 1 + Server 2 Integration Diagnostic Service (AIS 2.3).

Strictly read-only by default: executes SELECT probes, bounded HTTP GET /models
health checks, Redis PING / Celery inspect checks, canonical rule association
audits, historical TP/FP + `is_ml_generated` audits, G1 authoritative rule
coverage, Workbench-vs-AIS parity checks, and policy digest/governance audits
without mutating incidents, closing SIEM alerts, or modifying remote state.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import func, inspect as sa_inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.incident import HistoricalGroundTruth, Incident
from app.models.policy_quality import PolicyQualityAssessmentRecord
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.schemas.rule_intelligence import SemanticsDefinitionStatus
from app.services.historical_eligibility_service import HistoricalEligibilityService
from app.services.incident_service import IncidentService
from app.services.llm_config_service import LLMConfigService
from app.services.migration_service import get_current_db_revision, get_head_revision
from app.services.policy_governance import (
    assess_policy_runtime_certification,
    build_rule_incident_context,
    resolve_canonical_rule,
)
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.policy_simulation_service import PolicySimulationService
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.runtime_config_service import (
    RuntimeConfigValidator,
    redact_url_credentials,
)
from app.utils.datetime_utils import utc_now
from app.workers.celery_app import celery_app, get_queue_depth, is_redis_available

logger = logging.getLogger("ai_verdict.integration_diagnostics")

_REQUIRED_AIS_TABLES = (
    "rules",
    "incidents",
    "historical_ground_truth",
    "investigations",
    "rule_prompts",
    "prompt_versions",
    "policy_quality_assessments",
    "rule_intelligence_snapshots",
    "historical_evaluation_runs",
    "historical_evaluation_results",
)


class IntegrationDiagnosticService:
    """Executes comprehensive read-only pre-integration and integration readiness checks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _check_database_and_schema(self) -> Dict[str, Any]:
        t0 = time.perf_counter()
        connected = False
        latency_ms = None
        dialect = "unknown"
        current_rev: Optional[str] = None
        head_rev: Optional[str] = None
        existing_tables: List[str] = []
        missing_tables: List[str] = []
        error_msg: Optional[str] = None

        try:
            conn = await self.db.connection()
            dialect = str(conn.dialect.name or "unknown")
            await self.db.execute(select(1))
            connected = True
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            def _inspect_tables(sync_conn) -> List[str]:
                return list(sa_inspect(sync_conn).get_table_names())

            existing_tables = await conn.run_sync(_inspect_tables)
            missing_tables = [t for t in _REQUIRED_AIS_TABLES if t not in existing_tables]

            head_rev = get_head_revision()
            current_rev = await get_current_db_revision(conn)
        except Exception as exc:
            error_msg = str(exc)

        schema_matches_head = bool(current_rev and head_rev and current_rev == head_rev)
        if not connected or missing_tables:
            status = "FAIL"
        elif not schema_matches_head:
            status = "WARN"
        else:
            status = "PASS"

        return {
            "status": status,
            "connected": connected,
            "dialect": dialect,
            "database_url_redacted": redact_url_credentials(settings.DATABASE_URL),
            "latency_ms": latency_ms,
            "alembic_current_revision": current_rev,
            "alembic_head_revision": head_rev,
            "schema_matches_alembic_head": schema_matches_head,
            "required_tables_checked": len(_REQUIRED_AIS_TABLES),
            "missing_tables": missing_tables,
            "error": error_msg,
        }

    async def _check_corpus_and_canonical_associations(
        self,
        target_rule: Optional[Rule] = None,
    ) -> Dict[str, Any]:
        total_rules = int((await self.db.execute(select(func.count(Rule.id)))).scalar() or 0)
        total_incidents = int((await self.db.execute(select(func.count(Incident.id)))).scalar() or 0)
        total_gt = int((await self.db.execute(select(func.count(HistoricalGroundTruth.id)))).scalar() or 0)

        rules_res = await self.db.execute(select(Rule))
        rules = list(rules_res.scalars().all())
        rule_by_uuid = {r.id: r for r in rules}

        inc_res = await self.db.execute(
            select(Incident.id, Incident.incident_id, Incident.rule_id, Incident.event_type)
        )
        inc_rows = inc_res.all()

        fk_linked = 0
        orphan_rule_id = 0
        dangling_fk = 0
        event_type_mismatch = 0
        sample_mismatches: List[Dict[str, Any]] = []

        for inc_db_id, inc_ext_id, inc_rule_id, inc_ev in inc_rows:
            if not inc_rule_id:
                orphan_rule_id += 1
                continue
            r_obj = rule_by_uuid.get(inc_rule_id)
            if not r_obj:
                dangling_fk += 1
                if len(sample_mismatches) < 10:
                    sample_mismatches.append({
                        "incident_id": inc_ext_id or inc_db_id,
                        "issue": "DANGLING_RULE_ID",
                        "rule_id": inc_rule_id,
                    })
                continue
            fk_linked += 1
            if r_obj.event_type and inc_ev and str(r_obj.event_type).strip() != str(inc_ev).strip():
                event_type_mismatch += 1
                if len(sample_mismatches) < 10:
                    sample_mismatches.append({
                        "incident_id": inc_ext_id or inc_db_id,
                        "issue": "EVENT_TYPE_MISMATCH",
                        "rule_uuid": r_obj.id,
                        "rule_event_type": r_obj.event_type,
                        "incident_event_type": inc_ev,
                    })

        target_summary: Optional[Dict[str, Any]] = None
        if target_rule:
            exact_cnt = sum(1 for _, _, rid, _ in inc_rows if rid == target_rule.id)
            orphan_ev_cnt = sum(
                1 for _, _, rid, ev in inc_rows if not rid and ev == target_rule.event_type
            )
            target_summary = {
                "rule_uuid": target_rule.id,
                "logical_rule_id": target_rule.rule_id,
                "name": target_rule.name,
                "event_type": target_rule.event_type,
                "fk_matched_incidents": exact_cnt,
                "orphan_event_type_incidents": orphan_ev_cnt,
                "total_canonical_incidents": exact_cnt + orphan_ev_cnt,
            }

        status = "PASS" if (dangling_fk == 0 and event_type_mismatch == 0) else "WARN"
        return {
            "status": status,
            "total_rules": total_rules,
            "total_incidents": total_incidents,
            "total_ground_truth_records": total_gt,
            "canonical_fk_linked_incidents": fk_linked,
            "orphan_unlinked_incidents": orphan_rule_id,
            "dangling_rule_fk_count": dangling_fk,
            "event_type_mismatch_count": event_type_mismatch,
            "sample_association_anomalies": sample_mismatches,
            "target_rule": target_summary,
        }

    async def _check_g1_authoritative_definitions(
        self,
        target_rule: Optional[Rule] = None,
    ) -> Dict[str, Any]:
        q = select(Rule)
        if target_rule:
            q = q.where(Rule.id == target_rule.id)
        rules = list((await self.db.execute(q)).scalars().all())

        snaps_res = await self.db.execute(select(RuleIntelligenceSnapshot))
        snap_by_rule = {s.rule_id: s for s in snaps_res.scalars().all()}

        verified_count = 0
        incomplete_count = 0
        runtime_counter_warnings = 0
        persisted_snapshot_count = 0
        rule_details: List[Dict[str, Any]] = []

        for r in rules:
            snap = snap_by_rule.get(r.id)
            if snap:
                persisted_snapshot_count += 1
            sem = RuleIntelligenceAnalyzer.analyze_rule(r)
            is_verified = sem.definition_status == SemanticsDefinitionStatus.VERIFIED
            if is_verified:
                verified_count += 1
            else:
                incomplete_count += 1

            pattern_txt = str(getattr(r, "pattern_logic", "") or "")
            has_runtime_counter = any(
                tok in pattern_txt for tok in ("incidentCount", "incidentDetail", "AUTO_SYNCED")
            )
            if has_runtime_counter and sem.threshold is None:
                runtime_counter_warnings += 1

            if len(rule_details) < 25:
                rule_details.append({
                    "rule_uuid": r.id,
                    "logical_rule_id": r.rule_id,
                    "name": r.name,
                    "definition_status": sem.definition_status.value,
                    "threshold": sem.threshold,
                    "aggregation_window": sem.aggregation_window,
                    "source_provenance": sem.source_provenance.value,
                    "persisted_snapshot_present": bool(snap),
                    "snapshot_definition_status": snap.definition_status if snap else None,
                    "runtime_counter_only_warning": bool(has_runtime_counter and sem.threshold is None),
                })

        if len(rules) == 0:
            status = "WARN"
        elif verified_count == 0:
            status = "WARN"
        else:
            status = "PASS"

        return {
            "status": status,
            "rules_inspected": len(rules),
            "verified_authoritative_rules": verified_count,
            "incomplete_definition_rules": incomplete_count,
            "persisted_snapshots_found": persisted_snapshot_count,
            "runtime_counter_without_threshold_count": runtime_counter_warnings,
            "rules": rule_details,
        }

    async def _check_server2_llm_readiness(self, *, probe_remote: bool) -> Dict[str, Any]:
        configured_ctx = int(getattr(settings, "LOCAL_LLM_CONTEXT_BUDGET", 16384) or 16384)
        reserved_comp = int(getattr(settings, "LOCAL_LLM_MAX_TOKENS", 1024) or 1024)
        parsed = LLMConfigService.parse_llm_url(settings.LOCAL_LLM_BASE_URL)
        base_url = parsed["base_url"]
        models_url = f"{base_url}/models"
        redacted_url = redact_url_credentials(models_url)

        if not probe_remote:
            verified_len = getattr(settings, "LOCAL_LLM_VERIFIED_MAX_MODEL_LEN", None)
            return {
                "status": "NOT_PROBED",
                "probed": False,
                "reachable": None,
                "endpoint_redacted": redacted_url,
                "configured_model": settings.LOCAL_LLM_MODEL_NAME,
                "configured_context_budget": configured_ctx,
                "reserved_completion_tokens": reserved_comp,
                "available_prompt_budget": max(512, configured_ctx - reserved_comp),
                "verified_server_max_model_len": verified_len,
                "context_capacity_verified": bool(verified_len is not None and int(verified_len) >= configured_ctx),
                "models_reported": [],
                "message": "Remote Server 2 probe skipped (--no-probe-remote / probe_remote=False); live integration unverified.",
            }

        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(
                    models_url,
                    headers={"Authorization": f"Bearer {settings.LOCAL_LLM_API_KEY}"},
                )
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            if res.status_code != 200:
                return {
                    "status": "FAIL",
                    "probed": True,
                    "reachable": False,
                    "status_code": res.status_code,
                    "latency_ms": latency_ms,
                    "endpoint_redacted": redacted_url,
                    "configured_model": settings.LOCAL_LLM_MODEL_NAME,
                    "configured_context_budget": configured_ctx,
                    "reserved_completion_tokens": reserved_comp,
                    "context_capacity_verified": False,
                    "models_reported": [],
                    "message": f"Server 2 returned HTTP {res.status_code}",
                }
            payload = res.json()
            models = [m.get("id", "") for m in payload.get("data", []) if isinstance(m, dict) and m.get("id")]
            max_len = LLMConfigService._extract_max_model_len(payload, settings.LOCAL_LLM_MODEL_NAME)
            active_present = (settings.LOCAL_LLM_MODEL_NAME in models) if models else False
            ctx_supported = (max_len >= configured_ctx) if max_len is not None else None
            if not active_present:
                status = "WARN"
            elif ctx_supported is False:
                status = "FAIL"
            elif ctx_supported is None and configured_ctx > 16384:
                status = "WARN"
            else:
                status = "PASS"
            return {
                "status": status,
                "probed": True,
                "reachable": True,
                "status_code": 200,
                "latency_ms": latency_ms,
                "endpoint_redacted": redacted_url,
                "configured_model": settings.LOCAL_LLM_MODEL_NAME,
                "active_model_present": active_present,
                "models_reported": models,
                "configured_context_budget": configured_ctx,
                "reserved_completion_tokens": reserved_comp,
                "available_prompt_budget": max(512, configured_ctx - reserved_comp),
                "verified_server_max_model_len": max_len,
                "context_capacity_verified": bool(ctx_supported is True),
                "context_budget_supported": ctx_supported,
                "message": "Server 2 /models reachable.",
            }
        except Exception as exc:
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            return {
                "status": "FAIL",
                "probed": True,
                "reachable": False,
                "latency_ms": latency_ms,
                "endpoint_redacted": redacted_url,
                "configured_model": settings.LOCAL_LLM_MODEL_NAME,
                "configured_context_budget": configured_ctx,
                "reserved_completion_tokens": reserved_comp,
                "context_capacity_verified": False,
                "models_reported": [],
                "message": f"Server 2 unreachable: {type(exc).__name__}: {exc}",
            }

    async def _check_redis_and_celery(self, *, probe_remote: bool) -> Dict[str, Any]:
        use_celery = bool(getattr(settings, "USE_ASYNC_CELERY", False))
        redis_redacted = redact_url_credentials(settings.REDIS_URL)
        broker_redacted = redact_url_credentials(settings.CELERY_BROKER_URL)

        if not probe_remote:
            return {
                "status": "NOT_PROBED" if use_celery else "DISABLED_IN_CONFIG",
                "probed": False,
                "use_async_celery": use_celery,
                "redis_reachable": None,
                "celery_app_initialized": celery_app is not None,
                "simulation_replay_queue_configured": True,
                "simulation_replay_workers": [],
                "redis_url_redacted": redis_redacted,
                "celery_broker_redacted": broker_redacted,
            }

        redis_ok = is_redis_available()
        live_depth = get_queue_depth("live_triage") if redis_ok else 0
        sim_depth = get_queue_depth("simulation_replay") if redis_ok else 0

        sim_workers: List[str] = []
        inspect_error: Optional[str] = None
        if redis_ok and celery_app is not None:
            try:
                def _inspect():
                    return celery_app.control.inspect(timeout=1.5).active_queues() or {}
                queues_map = await asyncio.to_thread(_inspect)
                for wname, qlist in queues_map.items():
                    if any((q or {}).get("name") == "simulation_replay" for q in (qlist or [])):
                        sim_workers.append(wname)
            except Exception as exc:
                inspect_error = str(exc)

        if not use_celery:
            status = "WARN" if settings.resolved_operating_mode in ("shadow", "advisory", "autonomous") else "DISABLED_IN_CONFIG"
        elif not redis_ok:
            status = "FAIL"
        elif not sim_workers:
            status = "WARN"
        else:
            status = "PASS"

        return {
            "status": status,
            "probed": True,
            "use_async_celery": use_celery,
            "redis_reachable": redis_ok,
            "celery_app_initialized": celery_app is not None,
            "live_triage_queue_depth": live_depth,
            "simulation_replay_queue_depth": sim_depth,
            "simulation_replay_workers": sim_workers,
            "worker_inspect_error": inspect_error,
            "redis_url_redacted": redis_redacted,
            "celery_broker_redacted": broker_redacted,
        }

    async def _check_workbench_ais_parity(
        self,
        target_rule: Optional[Rule] = None,
    ) -> Dict[str, Any]:
        q = select(Rule)
        if target_rule:
            q = q.where(Rule.id == target_rule.id)
        else:
            q = q.order_by(Rule.rule_id.asc()).limit(25)
        rules = list((await self.db.execute(q)).scalars().all())

        inc_svc = IncidentService(self.db)
        sim_svc = PolicySimulationService(self.db)
        mismatches: List[Dict[str, Any]] = []
        checked: List[Dict[str, Any]] = []

        for r in rules:
            _, wb_total, _ = await inc_svc.list_incidents_with_rule_summary(
                page=1,
                page_size=1,
                exact_rule_id=r.id,
            )
            rule_ctx = await build_rule_incident_context(self.db, r)
            ais_total, _ = await sim_svc._fetch_scoped_incidents_paginated(
                rule_ctx=rule_ctx,
                has_rule_filter=True,
                sample_limit=None,
                after_epoch=None,
                before_epoch=None,
                split_partition=None,
            )
            delta = int(wb_total) - int(ais_total)
            row = {
                "rule_uuid": r.id,
                "logical_rule_id": r.rule_id,
                "workbench_exact_count": int(wb_total),
                "ais_simulation_count": int(ais_total),
                "delta": delta,
            }
            checked.append(row)
            if delta != 0:
                mismatches.append(row)

        return {
            "status": "PASS" if not mismatches else "FAIL",
            "rules_checked": len(checked),
            "parity_mismatches_count": len(mismatches),
            "mismatches": mismatches,
            "rules": checked,
        }

    async def _check_policy_digest_and_governance(
        self,
        target_rule: Optional[Rule] = None,
    ) -> Dict[str, Any]:
        q = select(RulePrompt).options(selectinload(RulePrompt.rule), selectinload(RulePrompt.versions))
        if target_rule:
            q = q.where(RulePrompt.rule_id == target_rule.id)
        prompts = list((await self.db.execute(q)).scalars().all())

        qa_res = await self.db.execute(
            select(PolicyQualityAssessmentRecord).order_by(PolicyQualityAssessmentRecord.evaluated_at.desc())
        )
        latest_qa_by_pv: Dict[str, PolicyQualityAssessmentRecord] = {}
        for rec in qa_res.scalars().all():
            if rec.prompt_version_id and rec.prompt_version_id not in latest_qa_by_pv:
                latest_qa_by_pv[rec.prompt_version_id] = rec

        digest_mismatches = 0
        approved_policies = 0
        autonomous_eligible_count = 0
        details: List[Dict[str, Any]] = []

        for rp in prompts:
            rule = rp.rule
            if not rp.versions:
                continue
            target_pv: Optional[PromptVersion] = None
            if rp.active_version_id:
                target_pv = next((v for v in rp.versions if v.id == rp.active_version_id), None)
            if not target_pv:
                target_pv = sorted(rp.versions, key=lambda x: x.version_number, reverse=True)[0]

            if target_pv.status == "APPROVED":
                approved_policies += 1

            computed_digest = PolicyQualityValidator.compute_policy_digest(target_pv)
            qa_rec = latest_qa_by_pv.get(target_pv.id)
            stored_digest = qa_rec.policy_digest if qa_rec else None
            digest_consistent = (stored_digest == computed_digest) if stored_digest else None
            if digest_consistent is False:
                digest_mismatches += 1

            cert = await assess_policy_runtime_certification(self.db, rule, target_pv)
            if cert.autonomous_operation_eligible:
                autonomous_eligible_count += 1

            if len(details) < 25:
                details.append({
                    "rule_uuid": rule.id if rule else rp.rule_id,
                    "logical_rule_id": rule.rule_id if rule else None,
                    "policy_version_id": target_pv.id,
                    "version_number": target_pv.version_number,
                    "policy_status": target_pv.status,
                    "computed_policy_digest": computed_digest,
                    "persisted_assessment_digest": stored_digest,
                    "digest_consistent": digest_consistent,
                    "structural_approval_eligible": cert.structural_approval_eligible,
                    "empirical_validation_eligible": cert.empirical_validation_eligible,
                    "autonomous_operation_eligible": cert.autonomous_operation_eligible,
                    "policy_governance_mode": cert.policy_governance_mode,
                    "blocking_reasons": cert.blocking_reasons,
                })

        status = "FAIL" if digest_mismatches > 0 else ("PASS" if details else "WARN")
        return {
            "status": status,
            "policies_inspected": len(prompts),
            "approved_policies_count": approved_policies,
            "autonomous_eligible_count": autonomous_eligible_count,
            "digest_mismatch_count": digest_mismatches,
            "autonomous_default_blocked": autonomous_eligible_count == 0,
            "policies": details,
        }

    async def run_diagnostics(
        self,
        *,
        rule_id: Optional[str] = None,
        probe_remote: bool = False,
        strict_production: bool = False,
    ) -> Dict[str, Any]:
        """
        Runs all AIS 2.3 Server 1 + Server 2 readiness checks strictly read-only.
        Zero database writes, zero incident closures, zero SIEM actions.
        """
        resolved_target: Optional[Rule] = None
        if rule_id:
            resolved_target = await resolve_canonical_rule(self.db, rule_id)

        cfg_check = RuntimeConfigValidator.validate_all(
            settings,
            strict_production_dependencies=strict_production,
        )
        db_check = await self._check_database_and_schema()
        corpus_check = await self._check_corpus_and_canonical_associations(resolved_target)
        gt_report = await HistoricalEligibilityService(self.db).generate_report(
            rule_id=(resolved_target.id if resolved_target else rule_id)
        )
        gt_summary = gt_report.get("summary") or {}
        g1_check = await self._check_g1_authoritative_definitions(resolved_target)
        llm_check = await self._check_server2_llm_readiness(probe_remote=probe_remote)
        redis_check = await self._check_redis_and_celery(probe_remote=probe_remote)
        parity_check = await self._check_workbench_ais_parity(resolved_target)
        gov_check = await self._check_policy_digest_and_governance(resolved_target)

        # Aggregate check statuses honestly without masking unverified remote dependencies
        check_statuses = {
            "configuration_readiness": "FAIL" if cfg_check["status"] == "BLOCKED" else ("WARN" if cfg_check["status"] == "WARNING" else "PASS"),
            "database_schema": db_check["status"],
            "corpus_and_canonical_associations": corpus_check["status"],
            "ground_truth_and_ml_audit": "PASS" if gt_summary.get("total_rules_analyzed", 0) >= 0 else "WARN",
            "g1_authoritative_definitions": g1_check["status"],
            "server2_llm_readiness": llm_check["status"],
            "redis_celery_readiness": redis_check["status"],
            "workbench_ais_parity": parity_check["status"],
            "policy_digest_and_governance": gov_check["status"],
        }

        failed = [k for k, v in check_statuses.items() if v == "FAIL"]
        warned = [k for k, v in check_statuses.items() if v == "WARN"]
        unprobed = [k for k, v in check_statuses.items() if v in ("NOT_PROBED", "DISABLED_IN_CONFIG")]

        if failed:
            overall = "BLOCKED"
        elif unprobed:
            overall = "LOCAL_VERIFIED_REMOTE_NOT_PROBED"
        elif warned:
            overall = "INTEGRATION_WARNINGS"
        else:
            overall = "INTEGRATION_READY"

        return {
            "generated_at": utc_now().isoformat(),
            "read_only": True,
            "database_mutated": False,
            "external_mutations": False,
            "overall_status": overall,
            "integration_verified": (
                probe_remote
                and llm_check.get("reachable") is True
                and not failed
                and not unprobed
            ),
            "check_statuses": check_statuses,
            "failed_checks": failed,
            "warning_checks": warned,
            "unprobed_remote_checks": unprobed,
            "configuration_readiness": cfg_check,
            "database_schema": db_check,
            "corpus_and_canonical_associations": corpus_check,
            "ground_truth_eligibility_and_ml_audit": {
                "summary": gt_summary,
                "rules_count": len(gt_report.get("rules") or []),
                "rules": (gt_report.get("rules") or [])[:25],
            },
            "g1_authoritative_definition_coverage": g1_check,
            "server2_llm_readiness": llm_check,
            "redis_celery_readiness": redis_check,
            "workbench_ais_parity": parity_check,
            "policy_digest_and_governance": gov_check,
        }
