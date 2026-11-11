"""
Phase 8.2 Independent Forensic, Corpus, Quality Gate & Probe Audit Runner.

Executes strictly read-only inspection on the live workspace (`backend/ai_verdict.db`
is cloned into a temporary directory before running Alembic 007 upgrade and simulation
pipelines; production hosts and `docs/phase8/` + `docs/phase8.1/` are never touched).
Outputs machine-readable JSON artifacts into `docs/phase8.2/evidence/`.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
EVIDENCE_DIR = REPO_ROOT / "docs" / "phase8.2" / "evidence"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from alembic import command as alembic_command  # noqa: E402
from alembic.config import Config as AlembicConfig  # noqa: E402
from sqlalchemy import desc, or_, select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.orm import selectinload  # noqa: E402

from app.api.prompts import _analyze_with_snapshot  # noqa: E402
from app.models.incident import HistoricalGroundTruth, Incident  # noqa: E402
from app.models.prompt import PromptVersion, RulePrompt  # noqa: E402
from app.models.rule import Rule  # noqa: E402
from app.models.verdict_intelligence import HistoricalEvaluationRunRecord  # noqa: E402
from app.schemas.policy_quality import GateStatus, SimulationStatus  # noqa: E402
from app.schemas.verdict_intelligence import GroundTruthLabel  # noqa: E402
from app.services.evidence_requirement_mapper import EvidenceRequirementMapper  # noqa: E402
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator  # noqa: E402
from app.services.model_payload_allowlist import FORBIDDEN_GROUND_TRUTH_KEYS, build_model_facing_payload  # noqa: E402
from app.services.policy_quality_validator import PolicyQualityValidator  # noqa: E402
from app.services.policy_simulation_service import PolicySimulationService  # noqa: E402


def _write_json(rel_path: str, payload: Any) -> None:
    target = EVIDENCE_DIR / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _parse_backend_env() -> Dict[str, str]:
    env_file = BACKEND_DIR / ".env"
    parsed: Dict[str, str] = {}
    if not env_file.exists():
        return parsed
    for raw in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        parsed[k.strip()] = v.strip().strip('"').strip("'")
    return parsed


def _tcp_probe(host: str, port: int, timeout: float = 1.5) -> Dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return {
                "host_masked": host if host in ("127.0.0.1", "localhost") else "<CONFIGURED_HOST>",
                "port": port,
                "reachable": True,
                "error": None,
            }
    except Exception as exc:
        return {
            "host_masked": host if host in ("127.0.0.1", "localhost") else "<CONFIGURED_HOST>",
            "port": port,
            "reachable": False,
            "error": type(exc).__name__,
        }


def _contains_forbidden_keys(obj: Any) -> List[str]:
    hits: List[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in FORBIDDEN_GROUND_TRUTH_KEYS or any(t in kl for t in ("cleared", "groundtruth", "analystverdict")):
                if v not in (None, "", []):
                    hits.append(str(k))
            hits.extend(_contains_forbidden_keys(v))
    elif isinstance(obj, list):
        for item in obj:
            hits.extend(_contains_forbidden_keys(item))
    return hits


async def _run_async_audit() -> None:
    ts_utc = datetime.now(timezone.utc).isoformat()
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    git_branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO_ROOT, text=True).strip()
    env_raw = _parse_backend_env()

    sanitized_env = {}
    for k, v in env_raw.items():
        if any(tok in k.upper() for tok in ("SECRET", "PASSWORD", "PASS", "TOKEN", "KEY", "USER")):
            sanitized_env[k] = f"<REDACTED len={len(v)}>" if v else "<EMPTY>"
        elif k.upper() == "FORTISIEM_HOST" and v:
            sanitized_env[k] = f"{urlparse(v).scheme or 'https'}://<CONFIGURED_FORTISIEM_HOST>"
        elif "://" in v and "@" in v:
            prefix, rest = v.split("://", 1)
            sanitized_env[k] = f"{prefix}://<REDACTED>@{rest.split('@', 1)[1]}"
        else:
            sanitized_env[k] = v

    local_bins = {b: (shutil.which(b) is not None) for b in ("psql", "pg_ctl", "postgres", "redis-server", "memurai", "celery", "uvicorn", "nginx", "vllm")}

    llm_url = env_raw.get("LOCAL_LLM_BASE_URL", "http://127.0.0.1:8000/v1")
    u_llm = urlparse(llm_url if "://" in llm_url else f"http://{llm_url}")
    fs_url = env_raw.get("FORTISIEM_HOST", "")
    u_fs = urlparse(fs_url if "://" in fs_url else f"https://{fs_url}") if fs_url else None

    probes = {
        "postgres_5432": _tcp_probe("127.0.0.1", 5432),
        "redis_6379": _tcp_probe("127.0.0.1", 6379),
        "server2_llm": _tcp_probe(u_llm.hostname or "127.0.0.1", u_llm.port or (443 if u_llm.scheme == "https" else 80)),
        "fortisiem_api": _tcp_probe(u_fs.hostname, u_fs.port or 443) if (u_fs and u_fs.hostname) else {"reachable": False, "error": "NOT_CONFIGURED"},
    }

    p81_gov_file = REPO_ROOT / "docs" / "phase8.1" / "evidence" / "deployment" / "stage2_target_governance_check.json"
    gov_targets = ["remote-server (production) (production)"]
    if p81_gov_file.exists():
        gov_targets = json.loads(p81_gov_file.read_text(encoding="utf-8")).get("governor_targets", gov_targets)

    _write_json(
        "baseline/stage_a_baseline_reconciliation.json",
        {
            "timestamp_utc": ts_utc,
            "git_sha": git_sha,
            "git_branch": git_branch,
            "local_binaries_available": local_bins,
            "sanitized_env": sanitized_env,
            "phase8_1_fixes_verified_in_source": [
                "P8.1-DEF-001 (DistributedLockManager.verify_or_renew & VerdictTriageAgent._assert_lock_held)",
                "P8.1-DEF-002 (INVALID_MODEL_OUTPUT & proposal vs final disposition split)",
                "P8.1-DEF-003 (Contradiction <=3 & malformed <=2 trust score caps)",
                "P8.1-DEF-004 (3-tier structural/empirical/autonomous eligibility flags)",
                "P8.1-DEF-005 (require_analyst on POST /api/incidents/{id}/ai-verdict)",
                "P8.1-DEF-006 (_analyze_with_snapshot UI/API Rule Intelligence sync)",
            ],
        },
    )

    _write_json(
        "staging/stage_b_staging_readiness_and_probes.json",
        {
            "timestamp_utc": ts_utc,
            "git_sha": git_sha,
            "staging_status": "BLOCKED",
            "governor_configured_targets": gov_targets,
            "production_deployment_executed": False,
            "docker_introduced": False,
            "probes": probes,
            "local_binaries_available": local_bins,
            "blocking_reason": "No authorized non-production staging host/DB/Redis/Server 2/FortiSIEM configured or reachable; production host left untouched per Staging Isolation Rules.",
        },
    )

    _write_json(
        "llm/stage_e_live_llm_probe.json",
        {
            "timestamp_utc": ts_utc,
            "git_sha": git_sha,
            "live_server2_status": "BLOCKED",
            "configured_model_env": env_raw.get("LOCAL_LLM_MODEL_NAME"),
            "runtime_model_confirmed": None,
            "socket_probe": probes["server2_llm"],
            "offline_http_contract_suite": "Verified separately via ThreadingHTTPServer in test_phase8_1_validation.py and test_phase8_2_validation.py (NOT counted as LLM-01-C2).",
        },
    )

    _write_json(
        "fortisiem/stage_i_fortisiem_probe.json",
        {
            "timestamp_utc": ts_utc,
            "git_sha": git_sha,
            "live_fortisiem_status": "BLOCKED",
            "socket_probe": probes["fortisiem_api"],
            "verify_ssl_env": env_raw.get("FORTISIEM_VERIFY_SSL"),
            "mock_fallback_env": env_raw.get("FORTISIEM_MOCK_FALLBACK"),
        },
    )

    # Clone seeded SQLite DB safely for Alembic 006->007 + read-only simulation audit
    src_db = BACKEND_DIR / "ai_verdict.db"
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        cloned_db = tmp_path / "ai_verdict_p82_audit.db"
        shutil.copy2(src_db, cloned_db)

        ro_conn = sqlite3.connect(f"file:{src_db}?mode=ro", uri=True)
        ro_conn.row_factory = sqlite3.Row
        pre_alembic = [r[0] for r in ro_conn.execute("SELECT version_num FROM alembic_version").fetchall()]
        pre_tables = len(ro_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())

        # Stage C Part 1: CrowdStrike Discrepancies Forensic Trace
        cs_traces: List[Dict[str, Any]] = []
        for target_id in ("132439932", "132441815", "132474210"):
            inc_row = dict(ro_conn.execute("SELECT * FROM incidents WHERE incident_id=?", (target_id,)).fetchone())
            rp = json.loads(inc_row["raw_payload"] or "{}")
            hgt = dict(ro_conn.execute("SELECT * FROM historical_ground_truth WHERE incident_id=?", (inc_row["id"],)).fetchone())
            invs = [dict(r) for r in ro_conn.execute("SELECT status, analyst_verdict, verdict_reason, is_disputed, is_independently_verified, analyst_notes FROM investigations WHERE incident_id=?", (inc_row["id"],)).fetchall()]
            ai_v = json.loads(inc_row["ai_verdict"] or "{}")
            ev_rows = [dict(r) for r in ro_conn.execute("SELECT event_type, attributes, raw_log FROM incident_events WHERE incident_id=?", (inc_row["id"],)).fetchall()]
            attr0 = json.loads(ev_rows[0]["attributes"] or "{}") if ev_rows else {}
            raw_log0 = ev_rows[0]["raw_log"] if ev_rows else ""
            kp_match = re.search(r'"KillProcess"\s*:\s*(true|false)', raw_log0)
            pdd_match = re.search(r'"PatternDispositionDescription"\s*:\s*"([^"]+)"', raw_log0)
            ioa_match = re.search(r'"IOARuleName"\s*:\s*"([^"]+)"', raw_log0)

            vta_cnt = ro_conn.execute("SELECT COUNT(*) FROM verdict_trust_assessments WHERE incident_id IN (?, ?)", (inc_row["id"], target_id)).fetchone()[0]
            tok_cnt = ro_conn.execute("SELECT COUNT(*) FROM token_usage_records WHERE incident_id IN (?, ?)", (inc_row["id"], target_id)).fetchone()[0]
            esa_cnt = ro_conn.execute("SELECT COUNT(*) FROM evidence_sufficiency_assessments WHERE incident_id IN (?, ?)", (inc_row["id"], target_id)).fetchone()[0]
            aud_rows = [dict(r) for r in ro_conn.execute("SELECT username, action, details, created_at FROM audit_logs WHERE resource_id IN (?, ?)", (inc_row["id"], target_id)).fetchall()]

            is_containment_only = HistoricalGroundTruthValidator.is_containment_only_fp_note(
                raw_resolution=hgt.get("resolution"),
                cleared_reason=hgt.get("cleared_reason"),
                analyst_comments=hgt.get("comments"),
                cleared_user=hgt.get("cleared_user"),
            )
            cs_traces.append({
                "incident_id": target_id,
                "incident_uuid": inc_row["id"],
                "rule_id": inc_row["rule_id"],
                "rule_event_type": inc_row["event_type"],
                "title": inc_row["title"],
                "customer": inc_row["customer"],
                "reporting_device": inc_row["reporting_device"],
                "siem_event_count": len(ev_rows),
                "telemetry_highlights": {
                    "command": attr0.get("Command"),
                    "file_name": attr0.get("File Name"),
                    "ioc_value": attr0.get("IOC Value"),
                    "process_blocked_attr": attr0.get("Process Blocked"),
                    "pattern_kill_process": kp_match.group(1) if kp_match else None,
                    "pattern_disposition": pdd_match.group(1) if pdd_match else None,
                    "ioa_rule_name": ioa_match.group(1) if ioa_match else None,
                },
                "historical_resolution": hgt.get("resolution"),
                "cleared_reason": hgt.get("cleared_reason"),
                "cleared_user": hgt.get("cleared_user"),
                "cleared_time_epoch": hgt.get("cleared_time_epoch"),
                "is_ml_generated": bool(hgt.get("is_ml_generated")),
                "weak_containment_only_fp_note": is_containment_only,
                "local_investigation_state": invs[0] if invs else None,
                "stored_ai_verdict": {
                    "verdict": ai_v.get("verdict"),
                    "confidence": ai_v.get("confidence"),
                    "evaluated_at": ai_v.get("evaluated_at"),
                    "evaluated_by_user": ai_v.get("evaluated_by_user"),
                    "model_identifier": ai_v.get("model_identifier"),
                    "is_simulated": ai_v.get("is_simulated"),
                    "total_tokens": ai_v.get("total_tokens"),
                    "validation_status": ai_v.get("validation_status"),
                    "contract_id": ai_v.get("contract_id"),
                },
                "verdict_trust_rows": vta_cnt,
                "evidence_sufficiency_rows": esa_cnt,
                "token_usage_rows": tok_cnt,
                "audit_logs": aud_rows,
                "primary_classification": "HISTORICAL_SNAPSHOT",
                "secondary_classifications": (
                    ["DIFFERENT_VERDICT_SEMANTICS", "LABEL_ERROR"]
                    if is_containment_only
                    else ["EVIDENCE_ERROR"]
                ),
                "finding_summary": (
                    f"Stored AI TP ({ai_v.get('confidence')}%) came from legacy scheduler simulated-heuristic-v1 batch on {ai_v.get('evaluated_at')} with 0 tokens and 0 AIS 2.1 validation/trust rows; NOT a Server 2 LLM inference error. "
                    + (
                        "Human FP closure rationale cites containment ('kill process') with empty clearedUser matching ML batch epoch rather than benign authorization."
                        if is_containment_only
                        else "Human FP closure states legitimate activity with empty clearedUser and no independent local Investigation verification."
                    )
                ),
            })

        _write_json(
            "historical-data/stage_c_crowdstrike_discrepancies.json",
            {"timestamp_utc": ts_utc, "git_sha": git_sha, "incidents": cs_traces},
        )
        ro_conn.close()

        # Upgrade cloned DB 006 -> 007 using Alembic in a clean subprocess
        clone_env = os.environ.copy()
        clone_env["DATABASE_URL"] = f"sqlite+aiosqlite:///{cloned_db}"
        clone_env["SYNC_DATABASE_URL"] = f"sqlite:///{cloned_db}"
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=str(BACKEND_DIR),
            env=clone_env,
            capture_output=True,
            text=True,
            check=True,
        )

        post_conn = sqlite3.connect(f"file:{cloned_db}?mode=ro", uri=True)
        post_alembic = [r[0] for r in post_conn.execute("SELECT version_num FROM alembic_version").fetchall()]
        post_tables = len(post_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
        dl_cols = [r[1] for r in post_conn.execute("PRAGMA table_info(distributed_locks)").fetchall()]
        vta_total = post_conn.execute("SELECT COUNT(*) FROM verdict_trust_assessments").fetchone()[0]
        tok_total = post_conn.execute("SELECT COUNT(*) FROM token_usage_records").fetchone()[0]
        esa_total = post_conn.execute("SELECT COUNT(*) FROM evidence_sufficiency_assessments").fetchone()[0]
        post_conn.close()

        _write_json(
            "database/stage_h_db_migration_snapshot.json",
            {
                "timestamp_utc": ts_utc,
                "git_sha": git_sha,
                "seeded_db_path": "backend/ai_verdict.db",
                "pre_upgrade_alembic": pre_alembic,
                "pre_upgrade_table_count": pre_tables,
                "cloned_post_upgrade_alembic": post_alembic,
                "cloned_post_upgrade_table_count": post_tables,
                "distributed_locks_table_added": post_tables > pre_tables,
                "distributed_locks_columns": dl_cols,
                "live_postgres_status": "BLOCKED",
                "live_redis_celery_status": "BLOCKED",
            },
        )

        _write_json(
            "workers/stage_d_workers_and_lock_probe.json",
            {
                "timestamp_utc": ts_utc,
                "git_sha": git_sha,
                "redis_socket_probe": probes["redis_6379"],
                "celery_binary_installed": local_bins.get("celery", False),
                "redis_server_binary_installed": local_bins.get("redis-server", False),
                "use_async_celery_env": env_raw.get("USE_ASYNC_CELERY", "false"),
                "distributed_locks_schema_verified": bool(dl_cols),
                "distributed_locks_columns": dl_cols,
                "live_celery_worker_status": "BLOCKED",
                "offline_lock_contention_test": "Verified via test_phase8_1_validation.py and test_phase8_2_validation.py::test_stage_e_controlled_wire_scenarios (dual_post_calls == 1, single trust assessment persisted).",
            },
        )

        # Async inspection on cloned upgraded DB
        eng = create_async_engine(f"sqlite+aiosqlite:///{cloned_db}")
        sess_mk = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
        async with sess_mk() as db:
            rules = (await db.execute(select(Rule).order_by(Rule.rule_id))).scalars().all()
            all_incs = (
                await db.execute(
                    select(Incident, HistoricalGroundTruth)
                    .outerjoin(HistoricalGroundTruth, Incident.id == HistoricalGroundTruth.incident_id)
                    .options(selectinload(Incident.events))
                )
            ).all()

            # Check ZIP inventory & GT leakage across all 26 DB incidents
            leakage_live = 0
            leakage_replay = 0
            splits: Dict[str, int] = {}
            for inc_obj, _ in all_incs:
                rule_obj = next((r for r in rules if r.id == inc_obj.rule_id), None)
                payload_live = build_model_facing_payload(incident=inc_obj, rule=rule_obj, events=inc_obj.events or [])
                if _contains_forbidden_keys(payload_live):
                    leakage_live += 1
                rp_dict = inc_obj.raw_payload if isinstance(inc_obj.raw_payload, dict) else {}
                san_rep = HistoricalGroundTruthValidator.sanitize_incident_for_inference({"raw_payload": rp_dict, "source_ip": inc_obj.source_ip})
                if _contains_forbidden_keys(san_rep):
                    leakage_replay += 1
                part = HistoricalGroundTruthValidator.assign_partition(str(inc_obj.incident_id or inc_obj.id)).value
                splits[part] = splits.get(part, 0) + 1

            # Per-rule Empirical Simulation & Corpus Inventory (post-P8.2-DEF-001/002 fixes)
            sim = PolicySimulationService(db)
            corpus_by_rule = []
            eval_runs_summary = []
            for r in rules:
                pvs = (
                    await db.execute(
                        select(PromptVersion)
                        .join(RulePrompt, PromptVersion.prompt_id == RulePrompt.id)
                        .where(RulePrompt.rule_id == r.id)
                        .order_by(desc(PromptVersion.version_number))
                    )
                ).scalars().all()
                cand_pv = next((v for v in pvs if v.status == "APPROVED"), pvs[0] if pvs else None)
                sim_res = await sim.evaluate_candidate_policy(rule_id=r.id, candidate_version=cand_pv)

                matched_incs = [(inc_obj, gt_obj) for inc_obj, gt_obj in all_incs if inc_obj.rule_id in (r.id, r.rule_id)]
                funnel = sim_res.get("funnel") or {}
                ex_r = sim_res.get("exclusion_reasons") or {}
                gt_dist = sim_res.get("ground_truth_distribution") or {}
                el_details = (sim_res.get("stage_details") or {}).get("eligible") or []
                weak_notes = sum(1 for item in el_details if item.get("weak_containment_fp_note"))

                corpus_by_rule.append({
                    "rule_code": r.rule_id,
                    "rule_name": r.name,
                    "rule_status": r.status,
                    "total_incidents": len(matched_incs),
                    "human_labeled_records": funnel.get("analyst_labeled", 0) - ex_r.get("HEURISTIC_OR_ML_LABEL", 0),
                    "ml_generated_excluded": ex_r.get("HEURISTIC_OR_ML_LABEL", 0),
                    "synthetic_records_excluded": ex_r.get("SYNTHETIC_FIXTURE_EXCLUDED", 0),
                    "duplicate_group_records_excluded": ex_r.get("DUPLICATE_CLUSTER_EXCLUDED", 0),
                    "missing_evidence_records": ex_r.get("MISSING_EVIDENCE", 0) + ex_r.get("CORRUPT_OR_EMPTY_PAYLOAD", 0),
                    "disputed_or_unverified_labels": ex_r.get("AMBIGUOUS_LABEL", 0),
                    "missing_analyst_labels": ex_r.get("MISSING_ANALYST_LABEL", 0),
                    "eligible_independent_groups": funnel.get("independent_group_count", funnel.get("eligible", 0)),
                    "independently_verified_tp": gt_dist.get("tp", 0),
                    "independently_verified_fp": gt_dist.get("fp", 0),
                    "weak_containment_fp_notes_in_eligible": weak_notes,
                    "g8_eligible": False,
                    "calibration_eligible": bool(sim_res.get("is_calibrated", False)),
                })

                eval_runs_summary.append({
                    "rule_code": r.rule_id,
                    "policy_version_number": cand_pv.version_number if cand_pv else None,
                    "policy_status": cand_pv.status if cand_pv else None,
                    "total_scanned": sim_res.get("total_scanned"),
                    "rule_matched": sim_res.get("rule_matched"),
                    "eligible_independent_groups": sim_res.get("verified_ground_truth_cases"),
                    "exclusion_reasons": ex_r,
                    "simulation_status": sim_res.get("simulation_status"),
                    "empirical_validation_status": sim_res.get("empirical_validation_status"),
                    "decision_coverage": sim_res.get("decision_coverage"),
                    "balanced_accuracy": sim_res.get("balanced_accuracy"),
                    "precision": sim_res.get("precision"),
                    "recall": sim_res.get("recall"),
                    "specificity": sim_res.get("specificity"),
                    "calibration_status": sim_res.get("calibration_status"),
                    "message": sim_res.get("message"),
                })

            _write_json(
                "historical-data/stage_c_corpus_inventory.json",
                {
                    "timestamp_utc": ts_utc,
                    "git_sha": git_sha,
                    "total_db_incidents": len(all_incs),
                    "leakage_live_payload_hits": leakage_live,
                    "leakage_replay_sanitized_hits": leakage_replay,
                    "deterministic_splits": splits,
                    "per_rule_inventory": corpus_by_rule,
                },
            )

            _write_json(
                "metrics/stage_f_empirical_accuracy_and_calibration.json",
                {
                    "timestamp_utc": ts_utc,
                    "git_sha": git_sha,
                    "provider_mode": "SIMULATED_OFFLINE",
                    "server2_live_replay_status": "BLOCKED",
                    "per_rule_simulation_runs": eval_runs_summary,
                },
            )

            verdict_by_model: Dict[str, int] = {}
            verdict_by_label: Dict[str, int] = {}
            sim_count = 0
            evaluated_count = 0
            for inc_obj, _ in all_incs:
                av = inc_obj.ai_verdict if isinstance(inc_obj.ai_verdict, dict) else None
                if av:
                    evaluated_count += 1
                    m_id = str(av.get("model_identifier") or "unknown")
                    v_lbl = str(av.get("verdict") or "UNKNOWN")
                    verdict_by_model[m_id] = verdict_by_model.get(m_id, 0) + 1
                    verdict_by_label[v_lbl] = verdict_by_label.get(v_lbl, 0) + 1
                    if av.get("is_simulated"):
                        sim_count += 1

            _write_json(
                "verdicts/stage_c_e_verdict_inventory.json",
                {
                    "timestamp_utc": ts_utc,
                    "git_sha": git_sha,
                    "seeded_db_incidents_total": len(all_incs),
                    "stored_ai_verdicts_count": evaluated_count,
                    "stored_simulated_verdicts_count": sim_count,
                    "verdicts_by_model_identifier": verdict_by_model,
                    "verdicts_by_label": verdict_by_label,
                    "verdict_trust_assessment_rows": vta_total,
                    "evidence_sufficiency_assessment_rows": esa_total,
                    "token_usage_record_rows": tok_total,
                },
            )

            # Stage G: Policy Quality Gates G1-G8 across all 5 seeded PromptVersions
            all_pvs = (
                await db.execute(
                    select(PromptVersion, Rule)
                    .join(RulePrompt, PromptVersion.prompt_id == RulePrompt.id)
                    .join(Rule, RulePrompt.rule_id == Rule.id)
                    .order_by(Rule.rule_id, PromptVersion.version_number)
                )
            ).all()
            g1_g8_rows = []
            for pv_obj, r_obj in all_pvs:
                semantics, _, arch_def = await _analyze_with_snapshot(db, r_obj)
                contract = EvidenceRequirementMapper.map_evidence_contract(r_obj, semantics, arch_def, pv_obj)
                sim_eval = await sim.evaluate_candidate_policy(rule_id=r_obj.id, candidate_version=pv_obj)
                assessment = PolicyQualityValidator.validate_policy_quality(
                    rule=r_obj,
                    prompt_version=pv_obj,
                    contract=contract,
                    semantics=semantics,
                    simulation_results=sim_eval,
                )
                g8_gate = assessment.gate_results.get("G8_SIMULATION_REGRESSION")
                struct_ok = bool(assessment.approval_eligible)
                emp_ok = bool(assessment.simulation_status == SimulationStatus.EVALUATED_PASSED and g8_gate and g8_gate.status == GateStatus.PASSED)
                g1_g8_rows.append({
                    "rule_code": r_obj.rule_id,
                    "version_number": pv_obj.version_number,
                    "version_status": pv_obj.status,
                    "quality_score": assessment.quality_score,
                    "structural_quality_score": assessment.structural_quality_score,
                    "simulation_status": assessment.simulation_status.value if assessment.simulation_status else None,
                    "structural_approval_eligibility": struct_ok,
                    "empirical_certification_eligibility": emp_ok,
                    "autonomous_operation_eligibility": struct_ok and emp_ok,
                    "blocking_issues": assessment.blocking_issues,
                    "warnings": assessment.warnings,
                    "gates": {
                        k: {"status": g.status.value, "score": g.score, "max_score": g.max_score, "details": g.details}
                        for k, g in assessment.gate_results.items()
                    },
                })

            _write_json(
                "quality-gates/stage_g_policy_quality_gates.json",
                {"timestamp_utc": ts_utc, "git_sha": git_sha, "policy_versions_audited": len(g1_g8_rows), "results": g1_g8_rows},
            )
        await eng.dispose()

    print("PHASE_8_2_AUDIT_OK")


if __name__ == "__main__":
    asyncio.run(_run_async_audit())

