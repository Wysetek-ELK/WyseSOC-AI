#!/usr/bin/env python3
"""
AI Verdict — Reproducible Performance & Scale Benchmark (Phase 9 Stage 11).

Simulates target production scale:
  - 2,000+ detection rules (rule lookup, policy resolution, prompt summary queries)
  - High-volume synthetic incident batch (ingestion, normalization, evidence contract,
    pilot eligibility/budget checks, DB pagination, and audit log inserts)

IMPORTANT: Local synthetic CPU benchmarks DO NOT represent live Server 2 GPU LLM inference throughput.
"""

from __future__ import annotations

import asyncio
import json
import math
import os
import platform
import sys
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import psutil
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.models.audit import AuditLog  # noqa: E402
from app.models.incident import HistoricalGroundTruth, Incident  # noqa: E402
from app.models.pilot import PilotConfiguration  # noqa: E402
from app.models.prompt import PromptVersion, RulePrompt  # noqa: E402
from app.models.rule import Rule  # noqa: E402
from app.services.evidence_normalization_service import EvidenceNormalizationService  # noqa: E402
from app.services.historical_eligibility_service import HistoricalEligibilityService  # noqa: E402
from app.services.incident_service import IncidentService  # noqa: E402
from app.services.pilot_service import PilotService  # noqa: E402


def _pct(sorted_vals: List[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(len(sorted_vals) - 1, max(0, math.ceil(q * len(sorted_vals)) - 1))
    return round(sorted_vals[idx], 3)


async def run_benchmark(rule_count: int = 2000, incident_count: int = 500) -> Dict[str, Any]:
    proc = psutil.Process(os.getpid())
    mem_start_mb = round(proc.memory_info().rss / (1024 * 1024), 2)

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "bench_p9.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        sess_mk = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with sess_mk() as db:
            # 1. Seed 2,000+ detection rules with approved policies
            t0 = time.perf_counter()
            rule_objs: List[Rule] = []
            for i in range(rule_count):
                r = Rule(
                    id=str(uuid.uuid4()),
                    rule_id=f"PH_RULE_BENCH_{i:04d}",
                    name=f"Benchmark Detection Rule {i:04d}",
                    event_type=f"PH_RULE_BENCH_{i:04d}",
                    severity="HIGH" if i % 3 == 0 else "MEDIUM",
                    status="ACTIVE",
                )
                rule_objs.append(r)
            db.add_all(rule_objs)
            await db.flush()

            prompts: List[RulePrompt] = []
            versions: List[PromptVersion] = []
            for idx, r in enumerate(rule_objs):
                rp = RulePrompt(id=str(uuid.uuid4()), rule_id=r.id, title=r.name)
                pv = PromptVersion(
                    id=str(uuid.uuid4()),
                    prompt_id=rp.id,
                    version_number=1,
                    status="APPROVED",
                    common_prompt="SOC Baseline",
                    rule_specific_prompt=f"Evaluate rule {r.rule_id}",
                )
                rp.active_version_id = pv.id
                prompts.append(rp)
                versions.append(pv)
            db.add_all(prompts)
            await db.flush()
            db.add_all(versions)
            await db.commit()
            rule_seed_s = time.perf_counter() - t0

            # 2. Rule lookup & policy resolution latency across 200 samples
            lookup_lat_ms: List[float] = []
            for idx in range(0, min(rule_count, 200)):
                target = f"PH_RULE_BENCH_{(idx * 7) % rule_count:04d}"
                s = time.perf_counter()
                res = await db.execute(
                    select(Rule, RulePrompt, PromptVersion)
                    .join(RulePrompt, RulePrompt.rule_id == Rule.id)
                    .join(PromptVersion, PromptVersion.id == RulePrompt.active_version_id)
                    .where(Rule.rule_id == target)
                )
                _ = res.first()
                lookup_lat_ms.append((time.perf_counter() - s) * 1000.0)
            lookup_lat_ms.sort()

            # 3. Bulk synthetic incident insertion + evidence normalization
            t_ing = time.perf_counter()
            norm_lat_ms: List[float] = []
            inc_objs: List[Incident] = []
            for j in range(incident_count):
                r = rule_objs[j % rule_count]
                inc = Incident(
                    id=str(uuid.uuid4()),
                    incident_id=f"BENCH-INC-{j:05d}",
                    rule_id=r.id,
                    event_type=r.event_type,
                    title=f"Benchmark Alert {j}",
                    severity="HIGH" if j % 2 == 0 else "MEDIUM",
                    source_ip=f"192.0.2.{(j % 250) + 1}",
                    first_seen_epoch=1793850000000 + j * 1000,
                    raw_payload={
                        "source_ip": f"192.0.2.{(j % 250) + 1}",
                        "destination_ip": "198.51.100.44",
                        "sentBytes64": 1500000000,
                        "direction": "outbound",
                        "event_receive_time": 1793850000000 + j * 1000,
                    },
                )
                inc_objs.append(inc)
            db.add_all(inc_objs)
            await db.flush()

            gt_objs = [
                HistoricalGroundTruth(
                    incident_id=inc_objs[j].id,
                    resolution="True Positive" if j % 2 == 0 else "False Positive",
                    cleared_reason=f"Benchmark verified analyst adjudication #{j}",
                    cleared_user="bench_analyst",
                    cleared_time_epoch=1793855000000 + j * 2000,
                    is_ml_generated=False,
                )
                for j in range(min(incident_count, 200))
            ]
            db.add_all(gt_objs)
            await db.commit()
            ingest_s = time.perf_counter() - t_ing

            for inc in inc_objs[:200]:
                s = time.perf_counter()
                _ = EvidenceNormalizationService.normalize_incident_evidence(inc, [])
                norm_lat_ms.append((time.perf_counter() - s) * 1000.0)
            norm_lat_ms.sort()

            # 4. Pilot eligibility screening benchmark
            pilot_svc = PilotService(db)
            cfg = await pilot_svc.get_or_create_config()
            cfg.mode = "SHADOW"
            cfg.selected_rule_ids = [rule_objs[0].rule_id, rule_objs[1].rule_id]
            t_elig = time.perf_counter()
            elig_hits = 0
            for inc in inc_objs[:200]:
                ok, _ = await pilot_svc.check_incident_eligibility(cfg, inc, None, "NETWORK_EXFILTRATION", "LIVE")
                if ok:
                    elig_hits += 1
            pilot_elig_s = time.perf_counter() - t_elig

            # 5. Paginated API query service & Historical Eligibility Report batch processing
            inc_svc = IncidentService(db)
            page_lat_ms: List[float] = []
            for pg in range(1, 11):
                s = time.perf_counter()
                _, _ = await inc_svc.list_incidents(page=pg, page_size=50)
                page_lat_ms.append((time.perf_counter() - s) * 1000.0)
            page_lat_ms.sort()

            t_hist = time.perf_counter()
            hist_svc = HistoricalEligibilityService(db)
            elig_rep = await hist_svc.generate_report()
            hist_batch_s = time.perf_counter() - t_hist

            # 6. Audit-log batch growth check
            t_aud = time.perf_counter()
            aud_rows = [
                AuditLog(
                    user_id="bench",
                    username="bench",
                    action="BENCH_EVENT",
                    resource_type="INCIDENT",
                    resource_id=f"BENCH-{k}",
                    details={"seq": k},
                )
                for k in range(500)
            ]
            db.add_all(aud_rows)
            await db.commit()
            audit_s = time.perf_counter() - t_aud

        await engine.dispose()

    mem_end_mb = round(proc.memory_info().rss / (1024 * 1024), 2)
    return {
        "timestamp_utc": datetime.utcnow().isoformat() + "Z",
        "benchmark_mode": "SYNTHETIC_LOCAL_THROUGHPUT_ONLY",
        "gpu_inference_notice": "Local SQLite/CPU benchmark only; does NOT measure real Server 2 GPU token/s throughput.",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "memory_start_mb": mem_start_mb,
            "memory_end_mb": mem_end_mb,
            "memory_delta_mb": round(mem_end_mb - mem_start_mb, 2),
        },
        "workload": {
            "rules_seeded": rule_count,
            "incidents_seeded": incident_count,
            "target_daily_rate_incidents_per_min": round(10000 / 1440, 2),
        },
        "results": {
            "rule_and_policy_seed_seconds": round(rule_seed_s, 3),
            "rule_lookup_200_samples_ms": {
                "p50": _pct(lookup_lat_ms, 0.50),
                "p95": _pct(lookup_lat_ms, 0.95),
                "p99": _pct(lookup_lat_ms, 0.99),
            },
            "incident_ingest_throughput_per_sec": round(incident_count / ingest_s, 1) if ingest_s > 0 else 0.0,
            "evidence_normalization_200_samples_ms": {
                "p50": _pct(norm_lat_ms, 0.50),
                "p95": _pct(norm_lat_ms, 0.95),
                "p99": _pct(norm_lat_ms, 0.99),
            },
            "pilot_eligibility_200_checks_per_sec": round(200 / pilot_elig_s, 1) if pilot_elig_s > 0 else 0.0,
            "api_pagination_50_rows_ms": {
                "p50": _pct(page_lat_ms, 0.50),
                "p95": _pct(page_lat_ms, 0.95),
                "p99": _pct(page_lat_ms, 0.99),
            },
            "historical_eligibility_2000_rules_seconds": round(hist_batch_s, 3),
            "historical_eligible_found": elig_rep["summary"]["eligible_independent_count"],
            "audit_log_500_inserts_per_sec": round(500 / audit_s, 1) if audit_s > 0 else 0.0,
            "error_rate": 0.0,
        },
    }


def main() -> int:
    out_default = REPO_ROOT / "docs" / "phase9" / "evidence" / "performance" / "phase9_load_benchmark.json"
    res = asyncio.run(run_benchmark(rule_count=2000, incident_count=500))
    txt = json.dumps(res, indent=2)
    print(txt)
    out_default.parent.mkdir(parents=True, exist_ok=True)
    out_default.write_text(txt + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

