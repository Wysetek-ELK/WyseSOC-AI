"""
Phase 8 Stages 5 & 6 Reproducible Empirical Replay and Policy Quality Gate Runner.

Safely clones `backend/ai_verdict.db` to an isolated temporary SQLite staging database,
upgrades schema to Alembic head (007_distributed_locks), runs genuine PolicySimulationService
replays, leakage checks, empirical accuracy/calibration evaluations, and G1-G8 quality gate
assessments across every rule/version without mutating repository databases or fabricating labels.

Outputs:
  - docs/phase8/evidence/metrics/stage5_historical_replay.json
  - docs/phase8/evidence/metrics/stage6_quality_gates.json
"""

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
METRICS_DIR = REPO_ROOT / "docs" / "phase8" / "evidence" / "metrics"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from app.models.incident import HistoricalGroundTruth, Incident
from app.models.prompt import PromptVersion, RulePrompt
from app.models.rule import Rule
from app.models.rule_intelligence import RuleIntelligenceSnapshot
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.model_payload_allowlist import build_model_facing_payload
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer
from app.services.detection_archetype_registry import DetectionArchetypeRegistry
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper
from app.services.policy_quality_validator import PolicyQualityValidator
from app.services.policy_simulation_service import PolicySimulationService


LEAKAGE_SENSITIVE_TERMS = (
    "resolution",
    "cleared_reason",
    "cleared_user",
    "comments",
    "analyst_verdict",
    "analyst_notes",
    "closure_comments",
)


async def run_all() -> None:
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    src_db = BACKEND_DIR / "ai_verdict.db"
    if not src_db.exists():
        raise FileNotFoundError(f"Seeded corpus database not found: {src_db}")

    td = Path(tempfile.mkdtemp(prefix="phase8_staging_"))
    staging_db = td / "staging_replay.db"
    shutil.copy2(src_db, staging_db)

    # Ensure isolated staging DB is at Alembic head 007
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{staging_db}"
    env["SYNC_DATABASE_URL"] = f"sqlite:///{staging_db}"
    alm = subprocess.run(["alembic", "upgrade", "head"], cwd=str(BACKEND_DIR), env=env, capture_output=True, text=True)
    if alm.returncode != 0:
        raise RuntimeError(f"Alembic upgrade on staging copy failed: {alm.stderr}")

    eng = create_async_engine(f"sqlite+aiosqlite:///{staging_db}", connect_args={"check_same_thread": False})
    SM = async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)

    stage5_report: Dict[str, Any] = {
        "runner": "scripts/run_phase8_empirical_validation.py",
        "source_database": "backend/ai_verdict.db (cloned to isolated temp DB)",
        "alembic_upgrade": "007_distributed_locks",
        "provider_mode": "SIMULATED (Server 2 GPU unavailable offline; deterministic safety/policy replay)",
        "ground_truth_audit": {},
        "leakage_audit": {},
        "partition_distribution": {},
        "duplicate_payload_audit": {},
        "rule_replays": [],
    }
    stage6_report: Dict[str, Any] = {
        "runner": "scripts/run_phase8_empirical_validation.py",
        "policy_version_assessments": [],
        "paired_regression_checks": [],
        "stale_digest_verification": {},
    }

    try:
        async with SM() as db:
            # 1. Audit Ground Truth Provenance, Leakage, Partitioning & Near-Duplicates
            inc_rows = (
                await db.execute(
                    select(Incident, HistoricalGroundTruth)
                    .outerjoin(HistoricalGroundTruth, Incident.id == HistoricalGroundTruth.incident_id)
                    .options(selectinload(Incident.rule), selectinload(Incident.events))
                )
            ).all()

            gt_provenance_counts = Counter()
            partition_counts = Counter()
            payload_hashes = Counter()
            leaked_cases: List[str] = []

            for inc, gt in inc_rows:
                part = HistoricalGroundTruthValidator.assign_partition(str(inc.incident_id or inc.id))
                partition_counts[part.value] += 1

                raw_bytes = json.dumps(inc.raw_payload or {}, sort_keys=True, default=str).encode("utf-8")
                payload_hashes[hashlib.sha256(raw_bytes).hexdigest()[:16]] += 1

                if gt:
                    adj_lbl, rel, _ = HistoricalGroundTruthValidator.adjudicate_label(
                        raw_resolution=gt.resolution,
                        analyst_comments=gt.comments,
                        is_ml_generated=bool(gt.is_ml_generated),
                    )
                    gt_provenance_counts[f"ml={bool(gt.is_ml_generated)}|{adj_lbl.value}|raw={gt.resolution}"] += 1
                    # Verify sanitization guarantees zero leakage when gt.cleared_reason / comments are populated
                    san_live = build_model_facing_payload(incident=inc, rule=inc.rule, events=inc.events or [])
                    san_replay = HistoricalGroundTruthValidator.sanitize_incident_for_inference(
                        {
                            "incident_id": inc.incident_id,
                            "raw_payload": inc.raw_payload or {},
                            "resolution": gt.resolution,
                            "cleared_reason": gt.cleared_reason,
                            "comments": gt.comments,
                            "ground_truth": {"resolution": gt.resolution},
                        }
                    )
                    san_live_txt = json.dumps(san_live, default=str).lower()
                    san_replay_txt = json.dumps(san_replay, default=str).lower()
                    for secret_val in (gt.cleared_reason, gt.comments):
                        if secret_val and len(secret_val.strip()) >= 8:
                            if secret_val.strip().lower() in san_live_txt or secret_val.strip().lower() in san_replay_txt:
                                leaked_cases.append(str(inc.incident_id))
                    for k in LEAKAGE_SENSITIVE_TERMS:
                        if k in san_replay:
                            leaked_cases.append(f"{inc.incident_id}:{k}")

            stage5_report["ground_truth_audit"] = {
                "total_incidents_in_corpus": len(inc_rows),
                "total_ground_truth_rows": sum(1 for _, gt in inc_rows if gt is not None),
                "human_adjudicated_non_ml_rows": sum(1 for _, gt in inc_rows if gt is not None and not gt.is_ml_generated),
                "ml_generated_rows_excluded": sum(1 for _, gt in inc_rows if gt is not None and gt.is_ml_generated),
                "adjudication_breakdown": dict(gt_provenance_counts),
            }
            stage5_report["leakage_audit"] = {
                "checked_incidents": len(inc_rows),
                "leaked_cases_count": len(leaked_cases),
                "leaked_cases": leaked_cases,
                "leakage_free": len(leaked_cases) == 0,
            }
            stage5_report["partition_distribution"] = dict(partition_counts)
            dup_clusters = sum(1 for _, cnt in payload_hashes.items() if cnt > 1)
            stage5_report["duplicate_payload_audit"] = {
                "unique_payload_hashes": len(payload_hashes),
                "duplicate_payload_clusters": dup_clusters,
            }

            # 2. Run PolicySimulationService Replay Across Every Seeded Rule
            rules = (await db.execute(select(Rule))).scalars().all()
            sim_srv = PolicySimulationService(db)

            rule_eval_cache: Dict[str, Dict[str, Any]] = {}
            for rule in rules:
                rp = (await db.execute(select(RulePrompt).where(RulePrompt.rule_id == rule.id))).scalars().first()
                versions = []
                if rp:
                    versions = (
                        await db.execute(
                            select(PromptVersion)
                            .where(PromptVersion.prompt_id == rp.id)
                            .order_by(PromptVersion.version_number.asc())
                        )
                    ).scalars().all()
                target_pv = None
                if rp and rp.active_version_id:
                    target_pv = next((v for v in versions if v.id == rp.active_version_id), None)
                if not target_pv and versions:
                    target_pv = versions[-1]

                sim_res = await sim_srv.evaluate_candidate_policy(rule_id=rule.id, candidate_version=target_pv)
                rule_eval_cache[rule.id] = sim_res
                cm = sim_res.get("confusion_matrix") or {}
                stage5_report["rule_replays"].append(
                    {
                        "rule_id": rule.rule_id,
                        "rule_uuid": rule.id,
                        "rule_name": rule.name,
                        "policy_version_id": str(target_pv.id) if target_pv else None,
                        "policy_status": target_pv.status if target_pv else None,
                        "simulation_status": sim_res.get("simulation_status"),
                        "empirical_validation_status": sim_res.get("empirical_validation_status"),
                        "total_scanned": sim_res.get("total_scanned"),
                        "rule_matched": sim_res.get("rule_matched"),
                        "analyst_labeled": sim_res.get("analyst_labeled"),
                        "eligible_ground_truth_count": sim_res.get("verified_ground_truth_cases"),
                        "excluded_count": sim_res.get("excluded_count"),
                        "exclusion_reasons": sim_res.get("exclusion_reasons"),
                        "confusion_matrix": cm,
                        "ground_truth_distribution": sim_res.get("ground_truth_distribution"),
                        "overall_accuracy": sim_res.get("overall_accuracy"),
                        "balanced_accuracy": sim_res.get("balanced_accuracy"),
                        "precision": sim_res.get("precision"),
                        "recall": sim_res.get("recall"),
                        "specificity": sim_res.get("specificity"),
                        "false_positive_rate": sim_res.get("false_positive_rate"),
                        "false_negative_rate": sim_res.get("false_negative_rate"),
                        "decision_coverage": sim_res.get("decision_coverage"),
                        "abstention_rate": sim_res.get("abstention_rate"),
                        "calibration_status": sim_res.get("calibration_status"),
                        "is_calibrated": sim_res.get("is_calibrated"),
                        "brier_score": sim_res.get("brier_score"),
                        "ece": sim_res.get("ece"),
                        "critical_regressions": sim_res.get("critical_regressions"),
                        "wilson_intervals": {
                            "overall_accuracy_ci": (sim_res.get("candidate_metrics") or {}).get("overall_accuracy_ci"),
                            "tp_precision_ci": (sim_res.get("candidate_metrics") or {}).get("tp_precision_ci"),
                            "fp_precision_ci": (sim_res.get("candidate_metrics") or {}).get("fp_precision_ci"),
                        },
                        "risk_coverage_curve_points": len((sim_res.get("candidate_metrics") or {}).get("risk_coverage_curve") or []),
                        "message": sim_res.get("message"),
                    }
                )

            # 3. Stage 6: Run G1-G8 PolicyQualityValidator on ALL PromptVersions + Stale Digest + Paired Regression
            all_rps = (await db.execute(select(RulePrompt).options(selectinload(RulePrompt.versions)))).scalars().all()
            rules_by_id = {r.id: r for r in rules}
            snaps = {s.rule_id: s for s in (await db.execute(select(RuleIntelligenceSnapshot))).scalars().all()}

            for rp in all_rps:
                r = rules_by_id.get(rp.rule_id)
                if not r:
                    continue
                sim_res = rule_eval_cache.get(r.id)
                for pv in rp.versions:
                    sem = RuleIntelligenceAnalyzer.analyze_rule(r)
                    arch_cls = DetectionArchetypeRegistry.classify_rule(sem, r)
                    arch_def = DetectionArchetypeRegistry.get_archetype_definition(arch_cls.primary_archetype)
                    contract = EvidenceRequirementMapper.map_evidence_contract(
                        rule=r,
                        semantics=sem,
                        archetype_def=arch_def,
                        prompt_version=pv,
                    )
                    assess = PolicyQualityValidator.validate_policy_quality(
                        rule=r,
                        prompt_version=pv,
                        contract=contract,
                        semantics=sem,
                        simulation_results=sim_res,
                    )
                    stage6_report["policy_version_assessments"].append(
                        {
                            "rule_id": r.rule_id,
                            "version_id": pv.id,
                            "version_number": pv.version_number,
                            "version_status": pv.status,
                            "policy_digest": assess.policy_digest,
                            "quality_score": assess.quality_score,
                            "structural_quality_score": assess.structural_quality_score,
                            "empirical_validation_score": assess.empirical_validation_score,
                            "empirical_validation_status": assess.empirical_validation_status,
                            "simulation_status": assess.simulation_status.value,
                            "approval_eligible": assess.approval_eligible,
                            "blocking_issues": list(assess.blocking_issues),
                            "warnings": list(assess.warnings),
                            "gates": [
                                {
                                    "gate_id": g.gate_id,
                                    "gate_name": g.gate_name,
                                    "status": g.status.value,
                                    "score": g.score,
                                    "max_score": g.max_score,
                                    "blocking_findings": list(g.blocking_findings),
                                    "warnings": list(g.warnings),
                                }
                                for g in assess.gate_results.values()
                            ],
                        }
                    )

                # Paired baseline vs candidate regression when >= 2 versions exist
                if len(rp.versions) >= 2:
                    v_sorted = sorted(rp.versions, key=lambda x: x.version_number)
                    base_v, cand_v = v_sorted[0], v_sorted[-1]
                    await sim_srv.evaluate_candidate_policy(rule_id=r.id, candidate_version=base_v)
                    paired = await sim_srv.evaluate_candidate_policy(
                        rule_id=r.id,
                        candidate_version=cand_v,
                        baseline_version=base_v,
                    )
                    stage6_report["paired_regression_checks"].append(
                        {
                            "rule_id": r.rule_id,
                            "baseline_version": base_v.version_number,
                            "candidate_version": cand_v.version_number,
                            "regression_status": paired.get("regression_status"),
                            "regression_detected": paired.get("regression_detected"),
                            "simulation_status": paired.get("simulation_status"),
                            "message": paired.get("message"),
                        }
                    )

                # Verify Stale Digest detection cleanly
                if rp.versions:
                    test_pv = rp.versions[0]
                    sem0 = RuleIntelligenceAnalyzer.analyze_rule(r)
                    arch_cls0 = DetectionArchetypeRegistry.classify_rule(sem0, r)
                    arch_def0 = DetectionArchetypeRegistry.get_archetype_definition(arch_cls0.primary_archetype)
                    contract0 = EvidenceRequirementMapper.map_evidence_contract(
                        rule=r,
                        semantics=sem0,
                        archetype_def=arch_def0,
                        prompt_version=test_pv,
                    )
                    stale_assess = PolicyQualityValidator.validate_policy_quality(
                        rule=r,
                        prompt_version=test_pv,
                        contract=contract0,
                        semantics=sem0,
                        simulation_results={"policy_digest": "00000000stale_digest", "simulation_status": "EVALUATED_PASSED", "sample_count": 10},
                    )
                    g8_stale = stale_assess.gate_results.get("G8_SIMULATION_REGRESSION") or next(iter(stale_assess.gate_results.values()))
                    stage6_report["stale_digest_verification"] = {
                        "rule_id": r.rule_id,
                        "expected_digest": stale_assess.policy_digest,
                        "injected_stale_digest": "00000000stale_digest",
                        "g8_status": g8_stale.status.value,
                        "g8_score": g8_stale.score,
                        "g8_warnings": list(g8_stale.warnings),
                        "g8_details": g8_stale.details,
                    }

    finally:
        await eng.dispose()
        shutil.rmtree(td, ignore_errors=True)

    (METRICS_DIR / "stage5_historical_replay.json").write_text(json.dumps(stage5_report, indent=2, default=str), encoding="utf-8")
    (METRICS_DIR / "stage6_quality_gates.json").write_text(json.dumps(stage6_report, indent=2, default=str), encoding="utf-8")
    print("OK: Phase 8 empirical metrics & quality gates reports written.")


if __name__ == "__main__":
    asyncio.run(run_all())
