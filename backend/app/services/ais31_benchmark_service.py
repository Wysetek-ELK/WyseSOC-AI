"""
AIS 3.1 — Frozen Holdout Manifest, Token Budget Audit, Idempotent Live GPU Benchmark Runner,
and Empirical Statistical Evaluation Engine.

Design Invariants:
- Inference path (`_prepare_incident_wire_payload`, `execute_run`) NEVER queries
  `AnalystVerdictReview`, `HistoricalGroundTruth`, `LearningRecord`, or `Incident.ai_verdict`.
- RAG is strictly disabled (`rag_block=""`, `rag_excluded=True`, `memory_excluded=True`).
- Mock fallback is strictly disabled.
- Raw LLM verdict and Validated Application verdict are captured and scored separately.
- Checkpointed per-incident persistence supports crash-safe idempotent resume without duplicates.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import uuid
from collections import Counter, defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.ais31_benchmark import AIS31BenchmarkResult, AIS31BenchmarkRun
from app.models.analyst_feedback import AnalystVerdictReview, BenchmarkCohort, BenchmarkCohortItem
from app.models.incident import Incident
from app.models.learning import LearningRecord
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.schemas.compiled_policy import CompilationExecutionMode
from app.services.ais27_benchmark_runner import AIS27BenchmarkRunner, _MODE_A_SCHEMA_SUFFIX
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator
from app.services.empirical_benchmark_harness import EmpiricalBenchmarkHarness, IncidentAdapter
from app.services.evidence_intelligence_service import EvidenceIntelligenceEngine, RuleDefinitionBuilder
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.ground_truth_certification_service import (
    _classify_item_exposure,
    _resolve_cohort_item_vendor,
)
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.policy_governance import get_rule_semantics_and_contract
from app.services.token_budget_service import TokenBudgetService
from app.services.tokenizer_service import ModelTokenizerService
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.utils.datetime_utils import utc_now

EXPECTED_TARGET_MODEL = "Qwen/Qwen3-14B-AWQ"
FROZEN_NEUTRAL_PROMPT_VERSION = "NEUTRAL_SOC_BASELINE_V2"
FROZEN_NEUTRAL_SYSTEM_PROMPT = EmpiricalBenchmarkHarness.NEUTRAL_SOC_BASELINE_V2 + _MODE_A_SCHEMA_SUFFIX


def _sha256_canonical(obj: Any) -> str:
    if isinstance(obj, str):
        return hashlib.sha256(obj.encode("utf-8")).hexdigest()
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str, ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _wilson_pct(successes: int, trials: int) -> Optional[Dict[str, float]]:
    if trials <= 0:
        return None
    ci = EmpiricalAccuracyEvaluator.calculate_wilson_ci(successes, trials)
    return {
        "point": round((ci.point_estimate or 0.0) * 100.0, 2),
        "lower_95": round((ci.lower_bound or 0.0) * 100.0, 2),
        "upper_95": round((ci.upper_bound or 0.0) * 100.0, 2),
    }


def _pct(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return round((num / den) * 100.0, 2)


class AIS31BenchmarkService:
    """Authoritative AIS 3.1 holdout manifest, token budgeter, GPU benchmark runner, and evaluator."""

    @staticmethod
    def _extract_sanitized_raw_events_and_summary(inc: Optional[Incident]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Extracts blind, leakage-free raw events and safe FortiSIEM incident summary metadata.
        Mirrors GroundTruthCertificationService._build_raw_logs fallback to `inc.raw_payload`
        when `inc.events` is empty, while stripping `incidentReso`, `cleared*`, `comments`,
        and historical ML `confidence` fields so zero historical verdict signals reach the LLM.
        """
        if not inc:
            return [], {}

        _DROP_FALLBACK_KEYS = {"incidentreso", "reso", "incidentstatus", "confidence", "rawevents", "events"}

        def _strip_fallback_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            cleaned_step = HistoricalGroundTruthValidator.sanitize_incident_for_inference(d)
            out: Dict[str, Any] = {}
            for k, v in cleaned_step.items():
                nk = "".join(ch for ch in str(k).lower() if ch.isalnum())
                if nk in _DROP_FALLBACK_KEYS:
                    continue
                out[k] = v
            return out

        safe_summary: Dict[str, Any] = {}
        raw_payload = getattr(inc, "raw_payload", None)
        if isinstance(raw_payload, dict) and raw_payload:
            safe_summary = _strip_fallback_dict(raw_payload)
        elif isinstance(raw_payload, list) and raw_payload and isinstance(raw_payload[0], dict):
            safe_summary = _strip_fallback_dict(raw_payload[0])

        raw_events: List[Dict[str, Any]] = []
        if inc.events:
            for ev in inc.events:
                ev_attrs = _strip_fallback_dict(ev.attributes or {}) if isinstance(ev.attributes, dict) else {}
                raw_events.append({
                    "eventId": ev.event_id,
                    "eventType": ev.event_type or inc.event_type,
                    "receiveTime": ev.event_receive_time,
                    "rawMessage": ev.raw_log or "",
                    "attribute": ev_attrs,
                })
        elif raw_payload:
            raw_list = raw_payload if isinstance(raw_payload, list) else [raw_payload]
            for idx, item_raw in enumerate(raw_list, start=1):
                if isinstance(item_raw, dict):
                    clean_raw = _strip_fallback_dict(item_raw)
                    attrs_src = clean_raw.get("attribute") or clean_raw.get("attributes") or clean_raw
                    attrs_flat = dict(attrs_src) if isinstance(attrs_src, dict) else {}
                    det_json = attrs_flat.get("incidentDetailJson")
                    if isinstance(det_json, dict):
                        for dk, dv in det_json.items():
                            if dk not in attrs_flat and dv is not None and dv != "":
                                attrs_flat[dk] = dv
                    raw_events.append({
                        "eventId": str(clean_raw.get("eventId") or clean_raw.get("id") or f"raw-{idx}"),
                        "eventType": clean_raw.get("eventType") or inc.event_type,
                        "receiveTime": clean_raw.get("receiveTime") or clean_raw.get("incidentFirstSeen") or inc.first_seen_epoch,
                        "rawMessage": str(attrs_flat.get("rawMessage") or json.dumps(clean_raw, default=str, ensure_ascii=True)),
                        "attribute": attrs_flat,
                    })
                else:
                    raw_events.append({
                        "eventId": f"raw-{idx}",
                        "eventType": inc.event_type,
                        "receiveTime": inc.first_seen_epoch,
                        "rawMessage": str(item_raw),
                        "attribute": {},
                    })

        return raw_events, safe_summary

    @classmethod
    async def build_frozen_manifest(
        cls,
        db: AsyncSession,
        cohort_key: str,
        include_ground_truth: bool = False,
    ) -> Dict[str, Any]:
        cohort = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key))
        ).scalar_one_or_none()
        if not cohort:
            raise ValueError(f"Benchmark cohort '{cohort_key}' not found.")

        items = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(BenchmarkCohortItem.cohort_id == cohort.id)
                .options(
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.events),
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule),
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.ground_truth),
                )
                .order_by(BenchmarkCohortItem.priority_rank.asc(), BenchmarkCohortItem.fortisiem_incident_id.asc())
            )
        ).scalars().all()

        inc_ids = [it.incident_db_id for it in items if it.incident_db_id]
        learned_ids = set()
        other_cohort_ids = set()
        rev_by_inc: Dict[str, List[AnalystVerdictReview]] = {}
        if inc_ids:
            learned_ids = {
                row[0]
                for row in (
                    await db.execute(
                        select(LearningRecord.incident_id).where(LearningRecord.incident_id.in_(inc_ids))
                    )
                ).all()
            }
            other_cohort_ids = {
                row[0]
                for row in (
                    await db.execute(
                        select(BenchmarkCohortItem.incident_db_id).where(
                            BenchmarkCohortItem.cohort_id != cohort.id,
                            BenchmarkCohortItem.incident_db_id.in_(inc_ids),
                        )
                    )
                ).all()
            }
            if include_ground_truth:
                revs = (
                    await db.execute(
                        select(AnalystVerdictReview).where(
                            AnalystVerdictReview.incident_id.in_(inc_ids),
                            AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                            AnalystVerdictReview.is_locked.is_(True),
                        )
                    )
                ).scalars().all()
                for r in revs:
                    rev_by_inc.setdefault(r.incident_id, []).append(r)

        inference_members: List[Dict[str, Any]] = []
        gt_members: List[Dict[str, Any]] = []
        raw_log_hash_counts: Counter = Counter()

        temp_rows = []
        for it in items:
            inc = it.incident
            raw_logs_payload, _ = cls._extract_sanitized_raw_events_and_summary(inc)
            raw_sig = _sha256_canonical(raw_logs_payload)
            raw_log_hash_counts[raw_sig] += 1
            temp_rows.append((it, inc, raw_sig))

        for it, inc, raw_sig in temp_rows:
            exp_status, _, exp_reason, exp_details = _classify_item_exposure(
                inc=inc,
                in_learning=(it.incident_db_id in learned_ids) if it.incident_db_id else False,
                in_other_cohort=(it.incident_db_id in other_cohort_ids) if it.incident_db_id else False,
                has_unmasked_ai_notes=False,
                has_prompt_capture=False,
            )
            quarantined = exp_status == "CONFIRMED_EXPOSURE" or it.eligibility_status != "ELIGIBLE"
            excl_reason = exp_reason if quarantined else None
            vendor = _resolve_cohort_item_vendor(it.rule_id, inc.rule if inc else None, {})

            entry = {
                "sequence_rank": it.priority_rank,
                "cohort_item_id": it.id,
                "incident_db_id": it.incident_db_id,
                "fortisiem_incident_id": it.fortisiem_incident_id,
                "rule_id": it.rule_id,
                "rule_name": it.rule_name,
                "vendor": vendor,
                "customer": it.customer,
                "severity": inc.severity if inc else None,
                "raw_evidence_sha256": it.raw_evidence_sha256 or raw_sig,
                "canonical_evidence_sha256": it.canonical_evidence_sha256,
                "rule_definition_sha256": it.rule_definition_sha256,
                "raw_logs_sha256": raw_sig,
                "cross_rule_duplicate_raw_logs": raw_log_hash_counts[raw_sig] > 1,
                "certification_status": it.certification_status,
                "certification_version": it.certification_version,
                "exposure_status": exp_status,
                "exposure_details": exp_details,
                "eligibility_state": "QUARANTINED" if quarantined else "ELIGIBLE",
                "exclusion_reason": excl_reason,
            }
            inference_members.append(entry)

            if include_ground_truth:
                locked_revs = rev_by_inc.get(it.incident_db_id or "", [])
                gt_members.append({
                    "fortisiem_incident_id": it.fortisiem_incident_id,
                    "incident_db_id": it.incident_db_id,
                    "certification_status": it.certification_status,
                    "certified_verdict": it.certified_verdict,
                    "locked_reviewers": [
                        {
                            "review_id": r.id,
                            "reviewer_id": r.reviewer_id,
                            "analyst_verdict": r.analyst_verdict,
                            "confidence_level": r.confidence_level,
                            "evidence_sufficiency_status": r.evidence_sufficiency_status,
                            "created_at": r.created_at.isoformat() if r.created_at else None,
                        }
                        for r in locked_revs
                    ],
                })

        manifest_core = {
            "cohort_id": cohort.cohort_key,
            "cohort_version": cohort.version,
            "original_population": len(items),
            "eligible_count": sum(1 for m in inference_members if m["eligibility_state"] == "ELIGIBLE"),
            "quarantined_count": sum(1 for m in inference_members if m["eligibility_state"] == "QUARANTINED"),
            "gt2_count": sum(1 for m in inference_members if m["certification_status"] == "GT2_SINGLE_REVIEW"),
            "gt3_count": sum(1 for m in inference_members if m["certification_status"] in ("GT3_CERTIFIED", "CERTIFIED_INCONCLUSIVE")),
            "members": inference_members,
        }
        manifest_sha = _sha256_canonical(manifest_core)

        res: Dict[str, Any] = {
            "schema_version": "ais31.manifest.v1",
            "created_at_utc": utc_now().isoformat(),
            "manifest_sha256": manifest_sha,
            "rag_excluded": True,
            "memory_excluded": True,
            **manifest_core,
        }
        if include_ground_truth:
            res["restricted_ground_truth"] = gt_members
        return res

    @classmethod
    async def _resolve_rule_and_policy(
        cls, db: AsyncSession, inc: Incident, item: BenchmarkCohortItem
    ) -> Tuple[Rule, Optional[PromptVersion], str]:
        rule_obj = inc.rule
        if not rule_obj:
            rule_obj = (
                await db.execute(
                    select(Rule).where(
                        or_(Rule.event_type == item.rule_id, Rule.rule_id == item.rule_id)
                    )
                )
            ).scalars().first()
        if not rule_obj:
            raise ValueError(f"Canonical Rule not found for incident '{item.fortisiem_incident_id}' ({item.rule_id}).")

        rp, pv = await AIS27BenchmarkRunner._resolve_approved_policy(db, rule_obj)
        if pv and pv.status == "APPROVED":
            policy_elig = f"APPROVED_V{pv.version_number}"
        else:
            policy_elig = "DRAFT_NOT_APPROVED"
        return rule_obj, pv, policy_elig

    @classmethod
    async def _prepare_incident_wire_payload(
        cls,
        *,
        db: AsyncSession,
        item: BenchmarkCohortItem,
        inc: Incident,
        max_context_tokens: int = 8192,
        max_completion_tokens: int = 768,
        target_input_budget: int = 7424,
        verify_remote_tokenize: bool = False,
        timeout_seconds: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Builds the strictly blind, sanitized, budgeted Mode-A wire prompt for one incident.
        NEVER queries ground truth, human reviews, LearningRecord, or operational ai_verdict.
        """
        rule_obj, approved_pv, policy_elig = await cls._resolve_rule_and_policy(db, inc, item)

        raw_events, safe_summary = cls._extract_sanitized_raw_events_and_summary(inc)
        inc_dict = {
            **safe_summary,
            "incidentId": item.fortisiem_incident_id,
            "title": inc.title or safe_summary.get("incidentTitle") or item.rule_name,
            "severity": inc.severity or safe_summary.get("eventSeverityCat") or "MEDIUM",
            "category": inc.category or safe_summary.get("phIncidentCategory") or "",
            "reportingDevice": inc.reporting_device or safe_summary.get("incidentRptDevName") or "",
            "reportingIp": inc.reporting_ip or safe_summary.get("incidentRptIp") or inc.source_ip or "",
            "eventType": rule_obj.event_type,
            "firstSeen": inc.first_seen_epoch or safe_summary.get("incidentFirstSeen"),
            "lastSeen": inc.last_seen_epoch or safe_summary.get("incidentLastSeen"),
            "createdAt": inc.created_at_epoch or safe_summary.get("origFirstSeenTime"),
            "rawEvents": raw_events,
        }
        sanitized_payload = HistoricalGroundTruthValidator.sanitize_incident_for_inference(inc_dict)
        inc_adapter = IncidentAdapter(sanitized_payload, item.fortisiem_incident_id)
        norm_result = EvidenceNormalizationService.normalize_incident_evidence(
            incident=inc_adapter, events=None
        )
        _, contract, _ = await get_rule_semantics_and_contract(
            db, rule_obj, prompt_version=approved_pv
        )
        preflight = EvidencePreflightValidator.validate_preflight(
            incident_id=item.fortisiem_incident_id,
            contract=contract,
            normalization_result=norm_result,
            allow_simulation=False,
        )

        compiled_policy = PolicyCompilerService.compile_policy(
            rule=rule_obj,
            prompt_version=approved_pv,
            execution_mode=CompilationExecutionMode.SIMULATION,
            raise_on_unapproved=False,
            modular_optimization=False,
        )

        payload_dict = build_model_facing_payload(
            incident=inc_adapter, rule=rule_obj, events=inc_adapter.events, max_events=10
        )
        payload_dict = HistoricalGroundTruthValidator.sanitize_incident_for_inference(payload_dict)
        payload_dict["canonical_evidence"] = [r.model_dump() for r in norm_result.records]
        payload_dict["evidence_contract"] = {
            "contract_id": contract.contract_id,
            "version": contract.version_number,
            "required_fields": [
                r.field for r in contract.required_evidence
                if not str(r.field).startswith("detection.")
                and getattr(r, "requirement_level", "CORE") == "CORE"
            ],
        }
        payload_dict["evidence_intelligence"] = EvidenceIntelligenceEngine.enrich_incident_evidence(
            payload_dict, norm_result.records
        )
        rule_spec = RuleDefinitionBuilder.build_complete_rule_spec(
            rule_obj=rule_obj,
            canonical_records=norm_result.records,
            incident_payload=payload_dict,
        )

        model_name_cfg = str(getattr(settings, "LOCAL_LLM_MODEL_NAME", EXPECTED_TARGET_MODEL) or EXPECTED_TARGET_MODEL)
        base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        sys_prompt = FROZEN_NEUTRAL_SYSTEM_PROMPT

        max_input_allowed = min(
            max(512, int(max_context_tokens) - int(max_completion_tokens)),
            int(target_input_budget),
        )
        rule_overhead = TokenBudgetService.estimate_tokens(rule_spec, model_name=model_name_cfg)
        safety_margin = 0
        rebudget_iterations = 0
        wire_token_audit: Dict[str, Any] = {}
        overflow_error: Optional[str] = None
        budgeted = None
        user_content = ""

        while True:
            budgeted = TokenBudgetService.budget_prompt(
                compiled_policy=compiled_policy,
                incident_payload=payload_dict,
                rag_block="",
                max_context_tokens=max_context_tokens,
                max_completion_tokens=max_completion_tokens,
                reserved_overhead_tokens=rule_overhead,
                model_name=model_name_cfg,
                target_input_budget=target_input_budget,
                wire_system_prompt=sys_prompt,
                wire_rule_spec=rule_spec,
                safety_margin_tokens=safety_margin,
            )
            if not budgeted.can_proceed_to_inference:
                overflow_error = f"CONTEXT_WINDOW_EXCEEDED: {budgeted.abstention_reason}"
                break

            user_content = ModelTokenizerService.render_wire_user_message(
                budgeted.budgeted_incident_payload, rule_spec
            )
            local_tok = ModelTokenizerService.count_wire_prompt_tokens(
                sys_prompt, user_content, model_name_cfg
            )

            if verify_remote_tokenize and base_url:
                remote_chk = await ModelTokenizerService.count_wire_prompt_tokens_remote(
                    base_url=base_url,
                    api_key=settings.LOCAL_LLM_API_KEY,
                    model_name=model_name_cfg,
                    system_prompt=sys_prompt,
                    user_message=user_content,
                    timeout_seconds=min(10.0, float(timeout_seconds)),
                    enable_thinking=False,
                )
                wire_token_audit = {
                    **remote_chk,
                    "max_input_allowed": max_input_allowed,
                    "rebudget_iterations": rebudget_iterations,
                    "safety_margin_applied": safety_margin,
                }
                if remote_chk["token_count"] > max_input_allowed:
                    if rebudget_iterations < 3:
                        rebudget_iterations += 1
                        drift = max(0, int(remote_chk.get("drift_tokens") or 0))
                        excess = remote_chk["token_count"] - max_input_allowed
                        safety_margin += excess + max(64, drift // 2)
                        continue
                    overflow_error = (
                        f"CONTEXT_WINDOW_EXCEEDED: Wire prompt ({remote_chk['token_count']} tokens via "
                        f"{remote_chk.get('source')}) exceeds ceiling ({max_input_allowed})."
                    )
                    break
            else:
                wire_token_audit = {
                    "token_count": local_tok,
                    "local_estimate": local_tok,
                    "drift_tokens": 0,
                    "source": "local_bpe_calibrated",
                    "tokenize_mode": "offline_bpe_estimate",
                    "max_input_allowed": max_input_allowed,
                    "rebudget_iterations": rebudget_iterations,
                    "safety_margin_applied": safety_margin,
                }
                if local_tok > max_input_allowed:
                    if rebudget_iterations < 3:
                        rebudget_iterations += 1
                        safety_margin += (local_tok - max_input_allowed) + 64
                        continue
                    overflow_error = f"CONTEXT_WINDOW_EXCEEDED: Local BPE wire estimate {local_tok} > {max_input_allowed}."
                    break
            break

        return {
            "rule_obj": rule_obj,
            "approved_pv": approved_pv,
            "mode_b_policy_eligibility": policy_elig,
            "sanitized_payload": sanitized_payload,
            "norm_result": norm_result,
            "contract": contract,
            "preflight": preflight,
            "rule_spec": rule_spec,
            "budgeted": budgeted,
            "sys_prompt": sys_prompt,
            "user_content": user_content,
            "wire_token_audit": wire_token_audit,
            "overflow_error": overflow_error,
            "system_tokens": ModelTokenizerService.count_tokens(sys_prompt, model_name=model_name_cfg),
            "rule_tokens": rule_overhead,
            "total_prompt_tokens_est": wire_token_audit.get("token_count", 0),
            "canonical_evidence_total": len(norm_result.records),
            "canonical_evidence_budgeted": len(
                (budgeted.budgeted_incident_payload.get("canonical_evidence") or [])
                if budgeted
                else []
            ),
            "events_total": len(raw_events),
            "events_budgeted": len(
                (budgeted.budgeted_incident_payload.get("events") or [])
                if budgeted
                else []
            ),
            "raw_evidence_sha256": item.raw_evidence_sha256 or _sha256_canonical(raw_events),
            "canonical_evidence_sha256": item.canonical_evidence_sha256 or _sha256_canonical([r.model_dump() for r in norm_result.records]),
            "rule_definition_sha256": item.rule_definition_sha256 or _sha256_canonical(rule_spec),
            "wire_prompt_sha256": _sha256_canonical(sys_prompt + "\n" + user_content),
        }

    @classmethod
    async def audit_token_budgets(
        cls,
        db: AsyncSession,
        cohort_key: str,
        max_context_tokens: int = 8192,
        max_completion_tokens: int = 768,
        target_input_budget: int = 7424,
        verify_remote_tokenize: bool = False,
    ) -> Dict[str, Any]:
        cohort = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == cohort_key))
        ).scalar_one_or_none()
        if not cohort:
            raise ValueError(f"Benchmark cohort '{cohort_key}' not found.")

        items = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(BenchmarkCohortItem.cohort_id == cohort.id)
                .options(
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.events),
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule),
                )
                .order_by(BenchmarkCohortItem.priority_rank.asc(), BenchmarkCohortItem.fortisiem_incident_id.asc())
            )
        ).scalars().all()

        results: List[Dict[str, Any]] = []
        overflow_count = 0
        max_tok = 0
        for it in items:
            if not it.incident:
                overflow_count += 1
                results.append({
                    "fortisiem_incident_id": it.fortisiem_incident_id,
                    "rule_id": it.rule_id,
                    "status": "MISSING_INCIDENT",
                    "fits_budget": False,
                })
                continue
            prep = await cls._prepare_incident_wire_payload(
                db=db,
                item=it,
                inc=it.incident,
                max_context_tokens=max_context_tokens,
                max_completion_tokens=max_completion_tokens,
                target_input_budget=target_input_budget,
                verify_remote_tokenize=verify_remote_tokenize,
            )
            tok = int(prep["total_prompt_tokens_est"] or 0)
            max_tok = max(max_tok, tok)
            fits = prep["overflow_error"] is None
            if not fits:
                overflow_count += 1
            results.append({
                "fortisiem_incident_id": it.fortisiem_incident_id,
                "rule_id": it.rule_id,
                "fits_budget": fits,
                "overflow_error": prep["overflow_error"],
                "system_tokens": prep["system_tokens"],
                "rule_tokens": prep["rule_tokens"],
                "wire_prompt_tokens": tok,
                "tokenize_source": prep["wire_token_audit"].get("source"),
                "rebudget_iterations": prep["wire_token_audit"].get("rebudget_iterations", 0),
                "events_total": prep["events_total"],
                "events_budgeted": prep["events_budgeted"],
                "canonical_evidence_total": prep["canonical_evidence_total"],
                "canonical_evidence_budgeted": prep["canonical_evidence_budgeted"],
                "mode_b_policy_eligibility": prep["mode_b_policy_eligibility"],
            })

        return {
            "cohort_key": cohort_key,
            "total_items": len(items),
            "context_limit": max_context_tokens,
            "reserved_completion_tokens": max_completion_tokens,
            "target_input_budget": target_input_budget,
            "overflow_count": overflow_count,
            "max_wire_prompt_tokens": max_tok,
            "all_fit_safely": overflow_count == 0,
            "items": results,
        }

    @classmethod
    async def create_or_resume_run(
        cls,
        db: AsyncSession,
        *,
        cohort_key: str,
        run_type: str = "FULL_HOLDOUT_100",
        created_by_user: str = "admin",
        run_key: Optional[str] = None,
        max_context_tokens: int = 8192,
        max_completion_tokens: int = 768,
        target_input_budget: int = 7424,
        transport_override: Optional[Callable[..., Any]] = None,
    ) -> AIS31BenchmarkRun:
        if run_key:
            existing = (
                await db.execute(select(AIS31BenchmarkRun).where(AIS31BenchmarkRun.run_key == run_key))
            ).scalar_one_or_none()
            if existing:
                return existing

        runtime_info: Dict[str, Any] = {}
        actual_model = EXPECTED_TARGET_MODEL
        vllm_ver = None
        if transport_override is None:
            runtime_info = await AIS27BenchmarkRunner.verify_gpu_runtime()
            models_data = ((runtime_info.get("models_payload") or {}).get("data") or [])
            available_ids = [str(m.get("id")) for m in models_data if m.get("id")]
            if runtime_info.get("models_http_status") != 200 or EXPECTED_TARGET_MODEL not in available_ids:
                raise RuntimeError(
                    f"Server 2 target model '{EXPECTED_TARGET_MODEL}' not available (status={runtime_info.get('models_http_status')}, available={available_ids})."
                )
            actual_model = EXPECTED_TARGET_MODEL
            vllm_ver = (runtime_info.get("version_payload") or {}).get("version")

        manifest = await cls.build_frozen_manifest(db, cohort_key, include_ground_truth=False)
        gt3_all = manifest["gt3_count"] >= manifest["original_population"] and manifest["original_population"] > 0
        grade = "CERTIFIED_GT3_BENCHMARK" if gt3_all else "PROVISIONAL_SINGLE_REVIEW_BENCHMARK"
        neutral_sha = _sha256_canonical(FROZEN_NEUTRAL_SYSTEM_PROMPT)

        key = run_key or f"AIS31-{run_type}-{utc_now().strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:6]}"
        run = AIS31BenchmarkRun(
            run_key=key,
            cohort_key=cohort_key,
            run_type=run_type,
            benchmark_grade=grade,
            status="CREATED",
            expected_model=EXPECTED_TARGET_MODEL,
            actual_model_returned=actual_model,
            vllm_version=vllm_ver,
            context_limit=max_context_tokens,
            max_completion_tokens=max_completion_tokens,
            target_input_budget=target_input_budget,
            neutral_prompt_version=FROZEN_NEUTRAL_PROMPT_VERSION,
            neutral_prompt_sha256=neutral_sha,
            policy_freeze_sha256=neutral_sha,
            manifest_sha256=manifest["manifest_sha256"],
            rag_excluded=True,
            memory_excluded=True,
            temperature=0.0,
            enable_thinking=False,
            total_target_count=manifest["eligible_count"],
            created_by_user=created_by_user,
            config_json={
                "cohort_key": cohort_key,
                "run_type": run_type,
                "temperature": 0.0,
                "top_p": 1.0,
                "enable_thinking": False,
                "max_context_tokens": max_context_tokens,
                "max_completion_tokens": max_completion_tokens,
                "target_input_budget": target_input_budget,
            },
            runtime_manifest_json=runtime_info,
        )
        db.add(run)
        await db.commit()
        await db.refresh(run)
        return run

    @classmethod
    async def execute_run(
        cls,
        db: AsyncSession,
        *,
        run_id: str,
        target_fids: Optional[List[str]] = None,
        max_incidents: Optional[int] = None,
        timeout_seconds: float = 180.0,
        transport_override: Optional[Callable[..., Any]] = None,
        retry_failed: bool = True,
    ) -> Dict[str, Any]:
        run = (await db.execute(select(AIS31BenchmarkRun).where(AIS31BenchmarkRun.id == run_id))).scalar_one_or_none()
        if not run:
            raise ValueError(f"Benchmark run '{run_id}' not found.")

        cohort = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == run.cohort_key))
        ).scalar_one_or_none()
        if not cohort:
            raise ValueError(f"Cohort '{run.cohort_key}' not found.")

        items = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(BenchmarkCohortItem.cohort_id == cohort.id)
                .options(
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.events),
                    selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule),
                )
                .order_by(BenchmarkCohortItem.priority_rank.asc(), BenchmarkCohortItem.fortisiem_incident_id.asc())
            )
        ).scalars().all()

        if target_fids:
            fid_set = {str(x).strip() for x in target_fids}
            items = [it for it in items if it.fortisiem_incident_id in fid_set]
        if max_incidents is not None and max_incidents > 0:
            items = items[:max_incidents]

        existing_rows = (
            await db.execute(select(AIS31BenchmarkResult).where(AIS31BenchmarkResult.run_id == run.id))
        ).scalars().all()
        existing_by_fid = {r.fortisiem_incident_id: r for r in existing_rows}

        run.status = "RUNNING"
        run.total_target_count = len(items)
        db.add(run)
        await db.commit()

        base_url = str(getattr(settings, "LOCAL_LLM_BASE_URL", "") or "").rstrip("/")
        api_key = str(getattr(settings, "LOCAL_LLM_API_KEY", "EMPTY") or "EMPTY")
        executed_now = 0

        for it in items:
            fid = it.fortisiem_incident_id
            prev = existing_by_fid.get(fid)
            if prev and prev.execution_status in ("COMPLETED", "QUARANTINED"):
                continue
            if prev and prev.execution_status == "FAILED" and not retry_failed:
                continue

            if not it.incident or it.eligibility_status != "ELIGIBLE":
                row = prev or AIS31BenchmarkResult(
                    run_id=run.id,
                    cohort_item_id=it.id,
                    incident_db_id=it.incident_db_id,
                    fortisiem_incident_id=fid,
                    rule_id=it.rule_id,
                    rule_name=it.rule_name,
                    sequence_rank=it.priority_rank or 0,
                )
                row.execution_status = "QUARANTINED"
                row.eligibility_state = "QUARANTINED"
                row.exclusion_reason = "Incident missing or ineligible"
                db.add(row)
                await db.commit()
                continue

            prep = await cls._prepare_incident_wire_payload(
                db=db,
                item=it,
                inc=it.incident,
                max_context_tokens=run.context_limit,
                max_completion_tokens=run.max_completion_tokens,
                target_input_budget=run.target_input_budget,
                verify_remote_tokenize=(transport_override is None),
                timeout_seconds=timeout_seconds,
            )

            row = prev or AIS31BenchmarkResult(
                run_id=run.id,
                cohort_item_id=it.id,
                incident_db_id=it.incident_db_id,
                fortisiem_incident_id=fid,
                rule_id=prep["rule_obj"].rule_id or it.rule_id,
                rule_name=prep["rule_obj"].name or it.rule_name,
                sequence_rank=it.priority_rank or 0,
            )
            row.attempts = (prev.attempts + 1) if prev else 1
            row.evidence_sha256 = prep["raw_evidence_sha256"]
            row.canonical_evidence_sha256 = prep["canonical_evidence_sha256"]
            row.rule_definition_sha256 = prep["rule_definition_sha256"]
            row.policy_sha256 = run.policy_freeze_sha256
            row.wire_prompt_sha256 = prep["wire_prompt_sha256"]
            row.wire_system_prompt = prep["sys_prompt"]
            row.wire_user_content = prep["user_content"]
            row.wire_token_audit_json = prep["wire_token_audit"]
            row.mode_b_policy_eligibility = prep["mode_b_policy_eligibility"]

            if prep["overflow_error"]:
                row.execution_status = "CONTEXT_OVERFLOW"
                row.error_classification = "CONTEXT_WINDOW_EXCEEDED"
                row.error_message = prep["overflow_error"]
                row.validated_application_verdict = "REQUIRES_ATTENTION"
                row.validator_status = "CONTEXT_WINDOW_EXCEEDED"
                row.validator_action = "OVERRULED_TO_ABSTAIN"
                row.inconclusive_reason = prep["overflow_error"]
                db.add(row)
                await db.commit()
                continue

            # Dispatch live GPU inference (max 1 transient transport retry)
            raw_env: Dict[str, Any] = {}
            max_attempts = 2
            for attempt_idx in range(1, max_attempts + 1):
                if transport_override is not None:
                    raw_env = await transport_override(
                        system_instruction=prep["sys_prompt"],
                        user_content=prep["user_content"],
                        model_name=run.expected_model,
                        max_tokens=run.max_completion_tokens,
                        temperature=run.temperature,
                    )
                else:
                    raw_env = await AIS27BenchmarkRunner._dispatch_vllm(
                        system_instruction=prep["sys_prompt"],
                        user_content=prep["user_content"],
                        model_name=run.expected_model,
                        max_tokens=run.max_completion_tokens,
                        temperature=run.temperature,
                        timeout_seconds=timeout_seconds,
                        base_url=base_url,
                        api_key=api_key,
                        top_p=1.0,
                        enable_thinking=False,
                    )
                if raw_env.get("ok"):
                    break
                if raw_env.get("error_type") == "HTTP_ERROR" and (raw_env.get("http_status") or 500) < 500:
                    break

            row.request_timestamp_utc = raw_env.get("request_timestamp_utc")
            row.response_timestamp_utc = raw_env.get("response_timestamp_utc")
            row.latency_ms = float(raw_env.get("latency_ms") or 0.0)
            row.gpu_provenance = "TEST_TRANSPORT" if transport_override is not None else "LIVE_SERVER2_VLLM"

            if not raw_env.get("ok"):
                row.execution_status = "FAILED"
                row.error_classification = str(raw_env.get("error_type") or "PROVIDER_FAILURE")
                row.error_message = str(raw_env.get("error_message") or "Inference dispatch failed")
                row.validated_application_verdict = "REQUIRES_ATTENTION"
                row.validator_status = "PROVIDER_FAILURE"
                row.validator_action = "FAILED_EXECUTION"
                db.add(row)
                await db.commit()
                continue

            executed_now += 1
            row.execution_status = "COMPLETED"
            row.error_classification = None
            row.error_message = None
            row.actual_model_returned = raw_env.get("model_returned")
            row.inference_request_id = raw_env.get("vllm_response_id")
            row.prompt_tokens = int(raw_env.get("prompt_tokens") or 0)
            row.completion_tokens = int(raw_env.get("completion_tokens") or 0)
            row.total_tokens = int(raw_env.get("total_tokens") or 0)
            row.finish_reason = raw_env.get("finish_reason")
            row.raw_response_text = str(raw_env.get("raw_response_text") or "")
            row.raw_vllm_envelope_json = raw_env.get("raw_vllm_envelope") or {}

            parsed = AIS27BenchmarkRunner._parse_raw_vllm_reply(
                raw_reply=row.raw_response_text,
                finish_reason=row.finish_reason,
                incident_id=fid,
                rule_spec=prep["rule_spec"],
                prompt_tokens=row.prompt_tokens,
                completion_tokens=row.completion_tokens,
                requested_max_tokens=run.max_completion_tokens,
            )
            row.parsed_output_json = parsed
            row.parsed_verdict = parsed.get("parsed_verdict")
            row.raw_llm_verdict = parsed.get("parsed_verdict")
            row.raw_llm_confidence = parsed.get("confidence")

            if not parsed.get("parsed_verdict") or parsed.get("truncated_output") or not parsed.get("schema_valid"):
                trunc = bool(parsed.get("truncated_output"))
                row.validated_application_verdict = "REQUIRES_ATTENTION"
                row.validator_status = "TRUNCATED_OUTPUT" if trunc else (parsed.get("validation_status") or "INVALID_SCHEMA")
                row.validator_action = "OVERRULED_TO_ABSTAIN" if row.raw_llm_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE") else "ABSTENTION_PRESERVED"
                row.validator_rejection_reason = parsed.get("parse_error") or row.validator_status
                row.validator_reason_codes_json = ["OUTPUT_TRUNCATED" if trunc else "MODEL_OUTPUT_INVALID"]
                row.deterministic_override = row.raw_llm_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE")
                row.evidence_grounding_status = "FAILED"
                row.grounding_ratio = 0.0
                row.inconclusive_reason = row.validator_rejection_reason
            else:
                model_out = {
                    "verdict": parsed["parsed_verdict"],
                    "confidence": parsed.get("confidence", 0.0),
                    "confidence_scale": parsed.get("confidence_scale"),
                    "reason": parsed.get("reason", ""),
                    "supporting_claims": parsed.get("supporting_claims", []),
                    "supporting_evidence": parsed.get("supporting_evidence", []),
                    "contradictory_evidence": parsed.get("contradictory_evidence", []),
                    "missing_evidence": parsed.get("missing_evidence", []),
                    "analyst_questions": parsed.get("analyst_questions", []),
                }
                grounding = ModelClaimExtractor.extract_and_ground_claims(
                    incident_id=fid,
                    raw_verdict_output=model_out,
                    normalization_result=prep["norm_result"],
                )
                val_res = IndependentVerdictValidator.validate_verdict(
                    incident_id=fid,
                    proposed_verdict=parsed["parsed_verdict"],
                    raw_model_confidence=float(parsed.get("confidence", 0.0)),
                    preflight=prep["preflight"],
                    claim_grounding=grounding,
                    normalization_result=prep["norm_result"],
                    contract=prep["contract"],
                    model_reason=str(parsed.get("reason", "")),
                    contradictory_evidence=parsed.get("contradictory_evidence") or None,
                    confidence_scale=parsed.get("confidence_scale"),
                )
                row.validated_application_verdict = val_res.final_verdict
                row.validator_status = val_res.validation_status
                row.validator_reason_codes_json = list(val_res.validation_reason_codes)
                row.grounding_ratio = float(val_res.grounding_ratio)
                row.evidence_grounding_status = "GROUNDED" if grounding.grounded_claims > 0 and not grounding.has_hallucinations else "UNGROUNDED"
                if row.raw_llm_verdict != val_res.final_verdict:
                    row.validator_action = "OVERRULED_TO_ABSTAIN"
                    row.deterministic_override = True
                    row.validator_rejection_reason = val_res.analyst_action_directive
                elif val_res.final_verdict == "REQUIRES_ATTENTION":
                    row.validator_action = "ABSTENTION_PRESERVED"
                    row.deterministic_override = False
                    row.inconclusive_reason = parsed.get("reason") or val_res.analyst_action_directive
                else:
                    row.validator_action = "ACCEPTED"
                    row.deterministic_override = False

            row.result_integrity_sha256 = _sha256_canonical({
                "run_id": run.id,
                "fid": fid,
                "wire_sha": row.wire_prompt_sha256,
                "vllm_id": row.inference_request_id,
                "raw_verdict": row.raw_llm_verdict,
                "app_verdict": row.validated_application_verdict,
            })
            db.add(row)
            await db.commit()

        # Recompute aggregate run counters
        all_rows = (
            await db.execute(select(AIS31BenchmarkResult).where(AIS31BenchmarkResult.run_id == run.id))
        ).scalars().all()
        comp_cnt = sum(1 for r in all_rows if r.execution_status == "COMPLETED")
        fail_cnt = sum(1 for r in all_rows if r.execution_status in ("FAILED", "CONTEXT_OVERFLOW"))
        run.completed_count = comp_cnt
        run.failed_count = fail_cnt
        if len(all_rows) >= run.total_target_count and fail_cnt == 0:
            run.status = "COMPLETED"
            run.completed_at = utc_now()
        elif comp_cnt > 0:
            run.status = "PARTIAL"
        else:
            run.status = "FAILED"
        db.add(run)
        await db.commit()

        return {
            "run_id": run.id,
            "run_key": run.run_key,
            "status": run.status,
            "benchmark_grade": run.benchmark_grade,
            "total_target_count": run.total_target_count,
            "completed_count": comp_cnt,
            "failed_count": fail_cnt,
            "executed_in_call": executed_now,
        }

    @classmethod
    def compute_metrics_for_subset(
        cls,
        rows: List[Dict[str, Any]],
        verdict_key: str,
        original_cohort_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Computes mathematically exact AIS 3.1 metrics & expanded confusion matrix for a population slice.
        Uses TRUE_POSITIVE as positive class, FALSE_POSITIVE as negative class.
        """
        eligible_rows = [r for r in rows if r["eligibility_state"] == "ELIGIBLE"]
        eligible_n = len(eligible_rows)
        exec_success = sum(1 for r in eligible_rows if r["execution_status"] == "COMPLETED")
        tech_failed = eligible_n - exec_success

        # Expanded confusion matrix: GT in {TRUE_POSITIVE, FALSE_POSITIVE, INCONCLUSIVE/OTHER}
        expanded = {
            "TRUE_POSITIVE": {"TRUE_POSITIVE": 0, "FALSE_POSITIVE": 0, "INCONCLUSIVE": 0, "FAILED_NOT_EXECUTED": 0},
            "FALSE_POSITIVE": {"TRUE_POSITIVE": 0, "FALSE_POSITIVE": 0, "INCONCLUSIVE": 0, "FAILED_NOT_EXECUTED": 0},
            "OTHER_OR_INCONCLUSIVE": {"TRUE_POSITIVE": 0, "FALSE_POSITIVE": 0, "INCONCLUSIVE": 0, "FAILED_NOT_EXECUTED": 0},
        }
        tp = fp = tn = fn = 0
        inconclusive_cnt = 0
        conclusive_cnt = 0
        correct_cnt = 0
        incorrect_cnt = 0

        for r in eligible_rows:
            gt = r["human_gt_verdict"]
            gt_bucket = gt if gt in ("TRUE_POSITIVE", "FALSE_POSITIVE") else "OTHER_OR_INCONCLUSIVE"
            if r["execution_status"] != "COMPLETED":
                expanded[gt_bucket]["FAILED_NOT_EXECUTED"] += 1
                continue

            pred = str(r.get(verdict_key) or "REQUIRES_ATTENTION").upper().strip()
            if pred in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
                expanded[gt_bucket][pred] += 1
                if gt in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
                    conclusive_cnt += 1
                    if pred == gt:
                        correct_cnt += 1
                    else:
                        incorrect_cnt += 1
                if gt == "TRUE_POSITIVE" and pred == "TRUE_POSITIVE":
                    tp += 1
                elif gt == "FALSE_POSITIVE" and pred == "TRUE_POSITIVE":
                    fp += 1
                elif gt == "FALSE_POSITIVE" and pred == "FALSE_POSITIVE":
                    tn += 1
                elif gt == "TRUE_POSITIVE" and pred == "FALSE_POSITIVE":
                    fn += 1
            else:
                expanded[gt_bucket]["INCONCLUSIVE"] += 1
                inconclusive_cnt += 1

        # Binary GT subset for coverage/correctness denominators
        binary_gt_n = sum(1 for r in eligible_rows if r["human_gt_verdict"] in ("TRUE_POSITIVE", "FALSE_POSITIVE"))
        precision = _pct(tp, tp + fp)
        recall = _pct(tp, tp + fn)
        specificity = _pct(tn, tn + fp)
        fpr = _pct(fp, fp + tn)
        fnr = _pct(fn, tp + fn)
        f1 = round((2 * precision * recall) / (precision + recall), 2) if (precision is not None and recall is not None and (precision + recall) > 0) else None
        balanced_acc = round((recall + specificity) / 2.0, 2) if (recall is not None and specificity is not None) else None

        latencies = [float(r["latency_ms"]) for r in eligible_rows if r["execution_status"] == "COMPLETED" and r.get("latency_ms")]
        sorted_lat = sorted(latencies)
        p95_lat = round(sorted_lat[min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))], 2) if sorted_lat else None

        return {
            "original_cohort_size": original_cohort_size,
            "eligible_population": eligible_n,
            "binary_gt_population": binary_gt_n,
            "execution_success_count": exec_success,
            "execution_success_rate_pct": _pct(exec_success, eligible_n),
            "technical_failure_count": tech_failed,
            "technical_failure_rate_pct": _pct(tech_failed, eligible_n),
            "conclusive_count": conclusive_cnt,
            "inconclusive_count": inconclusive_cnt,
            "inconclusive_rate_pct": _pct(inconclusive_cnt, exec_success),
            "decision_coverage_eligible_pct": _pct(conclusive_cnt, eligible_n),
            "decision_coverage_binary_gt_pct": _pct(conclusive_cnt, binary_gt_n),
            "decision_coverage_original_100_pct": _pct(conclusive_cnt, original_cohort_size),
            "correct_verdict_count": correct_cnt,
            "incorrect_verdict_count": incorrect_cnt,
            "conclusive_accuracy_pct": _pct(correct_cnt, conclusive_cnt),
            "conclusive_accuracy_ci95": _wilson_pct(correct_cnt, conclusive_cnt),
            "eligible_end_to_end_correct_rate_pct": _pct(correct_cnt, eligible_n),
            "binary_gt_end_to_end_correct_rate_pct": _pct(correct_cnt, binary_gt_n),
            "original_cohort_correct_rate_pct": _pct(correct_cnt, original_cohort_size),
            "binary_confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
            "expanded_confusion_matrix": expanded,
            "precision_pct": precision,
            "precision_ci95": _wilson_pct(tp, tp + fp),
            "recall_pct": recall,
            "recall_ci95": _wilson_pct(tp, tp + fn),
            "specificity_pct": specificity,
            "specificity_ci95": _wilson_pct(tn, tn + fp),
            "f1_pct": f1,
            "balanced_accuracy_pct": balanced_acc,
            "false_positive_rate_pct": fpr,
            "false_negative_rate_pct": fnr,
            "abstention_missed_tp_count": expanded["TRUE_POSITIVE"]["INCONCLUSIVE"],
            "incorrect_fn_count": fn,
            "latency_avg_ms": round(statistics.mean(latencies), 2) if latencies else None,
            "latency_median_ms": round(statistics.median(latencies), 2) if latencies else None,
            "latency_p95_ms": p95_lat,
            "total_prompt_tokens": sum(int(r.get("prompt_tokens") or 0) for r in eligible_rows),
            "total_completion_tokens": sum(int(r.get("completion_tokens") or 0) for r in eligible_rows),
        }

    @classmethod
    async def evaluate_run_against_ground_truth(
        cls,
        db: AsyncSession,
        run_id: str,
    ) -> Dict[str, Any]:
        run = (await db.execute(select(AIS31BenchmarkRun).where(AIS31BenchmarkRun.id == run_id))).scalar_one_or_none()
        if not run:
            raise ValueError(f"Benchmark run '{run_id}' not found.")

        cohort = (
            await db.execute(select(BenchmarkCohort).where(BenchmarkCohort.cohort_key == run.cohort_key))
        ).scalar_one_or_none()
        cohort_items = (
            await db.execute(
                select(BenchmarkCohortItem)
                .where(BenchmarkCohortItem.cohort_id == cohort.id)
                .options(selectinload(BenchmarkCohortItem.incident).selectinload(Incident.ground_truth), selectinload(BenchmarkCohortItem.incident).selectinload(Incident.rule))
            )
        ).scalars().all()
        item_by_fid = {it.fortisiem_incident_id: it for it in cohort_items}

        res_rows = (
            await db.execute(
                select(AIS31BenchmarkResult)
                .where(AIS31BenchmarkResult.run_id == run.id)
                .order_by(AIS31BenchmarkResult.sequence_rank.asc())
            )
        ).scalars().all()

        inc_ids = [it.incident_db_id for it in cohort_items if it.incident_db_id]
        revs_by_inc: Dict[str, List[AnalystVerdictReview]] = {}
        if inc_ids:
            revs = (
                await db.execute(
                    select(AnalystVerdictReview).where(
                        AnalystVerdictReview.incident_id.in_(inc_ids),
                        AnalystVerdictReview.review_mode == "BENCHMARK_CERTIFICATION",
                        AnalystVerdictReview.is_locked.is_(True),
                    )
                )
            ).scalars().all()
            for r in revs:
                revs_by_inc.setdefault(r.incident_id, []).append(r)

        joined: List[Dict[str, Any]] = []
        for rr in res_rows:
            it = item_by_fid.get(rr.fortisiem_incident_id)
            inc = it.incident if it else None
            locked = revs_by_inc.get(rr.incident_db_id or "", [])
            if it and it.certified_verdict:
                gt_verdict = it.certified_verdict
                cert_tier = "GT3_CERTIFIED"
            elif locked:
                gt_verdict = locked[0].analyst_verdict
                cert_tier = "GT2_SINGLE_REVIEW"
            else:
                gt_verdict = "UNREVIEWED"
                cert_tier = "GT0"

            exp_status, _, _, _ = _classify_item_exposure(
                inc=inc,
                in_learning=False,
                in_other_cohort=False,
                has_unmasked_ai_notes=False,
                has_prompt_capture=False,
            )
            joined.append({
                "fortisiem_incident_id": rr.fortisiem_incident_id,
                "incident_db_id": rr.incident_db_id,
                "rule_id": rr.rule_id,
                "rule_name": rr.rule_name,
                "vendor": _resolve_cohort_item_vendor(rr.rule_id, inc.rule if inc else None, {}),
                "customer": it.customer if it else "DEFAULT",
                "severity": inc.severity if inc else None,
                "eligibility_state": rr.execution_status if rr.execution_status == "QUARANTINED" else rr.eligibility_state,
                "execution_status": rr.execution_status,
                "certification_tier": cert_tier,
                "exposure_status": exp_status,
                "human_gt_verdict": gt_verdict,
                "raw_llm_verdict": rr.raw_llm_verdict,
                "raw_llm_confidence": rr.raw_llm_confidence,
                "validated_application_verdict": rr.validated_application_verdict,
                "validator_status": rr.validator_status,
                "validator_action": rr.validator_action,
                "validator_rejection_reason": rr.validator_rejection_reason,
                "deterministic_override": rr.deterministic_override,
                "grounding_ratio": rr.grounding_ratio,
                "latency_ms": rr.latency_ms,
                "prompt_tokens": rr.prompt_tokens,
                "completion_tokens": rr.completion_tokens,
                "finish_reason": rr.finish_reason,
                "inference_request_id": rr.inference_request_id,
                "wire_prompt_sha256": rr.wire_prompt_sha256,
            })

        orig_n = len(cohort_items) or len(joined)
        raw_all = cls.compute_metrics_for_subset(joined, "raw_llm_verdict", orig_n)
        app_all = cls.compute_metrics_for_subset(joined, "validated_application_verdict", orig_n)

        gt2_rows = [r for r in joined if r["certification_tier"] == "GT2_SINGLE_REVIEW"]
        gt3_rows = [r for r in joined if r["certification_tier"] == "GT3_CERTIFIED"]
        clean_rows = [r for r in joined if r["exposure_status"] == "VERIFIED_NO_DETECTED_EXPOSURE"]
        masked_rows = [r for r in joined if r["exposure_status"] == "HISTORICAL_LABEL_EXISTS_BUT_MASKED"]

        # Validator stats
        completed_n = sum(1 for r in joined if r["execution_status"] == "COMPLETED")
        override_n = sum(1 for r in joined if r["deterministic_override"])
        rejected_n = sum(1 for r in joined if r["validator_status"] in ("REJECTED", "REASONING_CONTRADICTION", "INSUFFICIENT_EVIDENCE", "TRUNCATED_OUTPUT", "INVALID_SCHEMA", "INVALID_MODEL_OUTPUT"))
        grounded_n = sum(1 for r in joined if r["execution_status"] == "COMPLETED" and (r.get("grounding_ratio") or 0.0) >= 1.0)

        # Baselines on binary GT
        bin_gt = [r for r in joined if r["human_gt_verdict"] in ("TRUE_POSITIVE", "FALSE_POSITIVE")]
        gt_tp = sum(1 for r in bin_gt if r["human_gt_verdict"] == "TRUE_POSITIVE")
        gt_fp = sum(1 for r in bin_gt if r["human_gt_verdict"] == "FALSE_POSITIVE")
        maj_class = "FALSE_POSITIVE" if gt_fp >= gt_tp else "TRUE_POSITIVE"
        maj_correct = max(gt_tp, gt_fp)

        # Group breakdowns by rule, vendor, customer, severity
        def _group_metrics(key: str) -> Dict[str, Any]:
            buckets: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for r in joined:
                buckets[str(r.get(key) or "UNKNOWN")].append(r)
            return {
                k: {
                    "sample_count": len(v),
                    "raw_llm": cls.compute_metrics_for_subset(v, "raw_llm_verdict", len(v)),
                    "validated_app": cls.compute_metrics_for_subset(v, "validated_application_verdict", len(v)),
                }
                for k, v in sorted(buckets.items())
            }

        return {
            "run_id": run.id,
            "run_key": run.run_key,
            "cohort_key": run.cohort_key,
            "benchmark_grade": run.benchmark_grade,
            "model": run.expected_model,
            "actual_model_returned": run.actual_model_returned,
            "policy_freeze_sha256": run.policy_freeze_sha256,
            "manifest_sha256": run.manifest_sha256,
            "raw_llm_metrics": raw_all,
            "application_metrics": app_all,
            "subpopulations": {
                "gt2_provisional": {
                    "count": len(gt2_rows),
                    "raw_llm": cls.compute_metrics_for_subset(gt2_rows, "raw_llm_verdict", orig_n),
                    "application": cls.compute_metrics_for_subset(gt2_rows, "validated_application_verdict", orig_n),
                },
                "gt3_certified": {
                    "count": len(gt3_rows),
                    "raw_llm": cls.compute_metrics_for_subset(gt3_rows, "raw_llm_verdict", orig_n),
                    "application": cls.compute_metrics_for_subset(gt3_rows, "validated_application_verdict", orig_n),
                },
                "verified_no_detected_exposure": {
                    "count": len(clean_rows),
                    "raw_llm": cls.compute_metrics_for_subset(clean_rows, "raw_llm_verdict", len(clean_rows)),
                    "application": cls.compute_metrics_for_subset(clean_rows, "validated_application_verdict", len(clean_rows)),
                },
                "historical_masked": {
                    "count": len(masked_rows),
                    "raw_llm": cls.compute_metrics_for_subset(masked_rows, "raw_llm_verdict", len(masked_rows)),
                    "application": cls.compute_metrics_for_subset(masked_rows, "validated_application_verdict", len(masked_rows)),
                },
            },
            "validator_telemetry": {
                "completed_count": completed_n,
                "validator_override_count": override_n,
                "validator_override_rate_pct": _pct(override_n, completed_n),
                "validator_rejection_count": rejected_n,
                "validator_rejection_rate_pct": _pct(rejected_n, completed_n),
                "grounding_pass_count": grounded_n,
                "grounding_pass_rate_pct": _pct(grounded_n, completed_n),
            },
            "baselines": {
                "binary_gt_total": len(bin_gt),
                "gt_true_positive": gt_tp,
                "gt_false_positive": gt_fp,
                "always_true_positive_accuracy_pct": _pct(gt_tp, len(bin_gt)),
                "always_false_positive_accuracy_pct": _pct(gt_fp, len(bin_gt)),
                "majority_class": maj_class,
                "majority_class_accuracy_pct": _pct(maj_correct, len(bin_gt)),
            },
            "breakdowns": {
                "by_rule": _group_metrics("rule_id"),
                "by_vendor": _group_metrics("vendor"),
                "by_customer": _group_metrics("customer"),
                "by_severity": _group_metrics("severity"),
            },
            "incident_results": joined,
        }

    @classmethod
    async def get_wire_prompt_capture(
        cls,
        db: AsyncSession,
        run_id: str,
        fortisiem_incident_id: str,
    ) -> Dict[str, Any]:
        row = (
            await db.execute(
                select(AIS31BenchmarkResult).where(
                    AIS31BenchmarkResult.run_id == run_id,
                    AIS31BenchmarkResult.fortisiem_incident_id == fortisiem_incident_id,
                )
            )
        ).scalar_one_or_none()
        if not row:
            raise ValueError(f"Benchmark result not found for run '{run_id}', incident '{fortisiem_incident_id}'.")
        return {
            "run_id": row.run_id,
            "fortisiem_incident_id": row.fortisiem_incident_id,
            "rule_id": row.rule_id,
            "model_identifier": row.model_identifier,
            "actual_model_returned": row.actual_model_returned,
            "inference_request_id": row.inference_request_id,
            "wire_prompt_sha256": row.wire_prompt_sha256,
            "policy_sha256": row.policy_sha256,
            "wire_system_prompt": row.wire_system_prompt,
            "wire_user_content": row.wire_user_content,
            "wire_token_audit": row.wire_token_audit_json,
            "raw_response_text": row.raw_response_text,
            "raw_llm_verdict": row.raw_llm_verdict,
            "validated_application_verdict": row.validated_application_verdict,
            "validator_status": row.validator_status,
            "validator_action": row.validator_action,
        }
