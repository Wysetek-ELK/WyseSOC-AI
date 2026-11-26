"""Audit AIS/LLM service call graph, frontend api.ts unused methods, dependencies, and DB/test/script cross-refs."""
import ast
import json
import re
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = REPO_ROOT / "docs" / "CCA_1_0" / "evidence"


def audit_frontend_api_client():
    api_ts = (REPO_ROOT / "frontend" / "src" / "lib" / "api.ts").read_text(encoding="utf-8")
    fe_files = {
        p.relative_to(REPO_ROOT).as_posix(): p.read_text(encoding="utf-8", errors="replace")
        for p in (REPO_ROOT / "frontend" / "src").rglob("*.ts*")
        if p.relative_to(REPO_ROOT).as_posix() != "frontend/src/lib/api.ts"
    }
    fe_tests = {
        p.relative_to(REPO_ROOT).as_posix(): p.read_text(encoding="utf-8", errors="replace")
        for p in (REPO_ROOT / "frontend" / "tests").glob("*.mjs")
    }

    # Find methods in `export const api = { ... }`
    m_start = api_ts.find("export const api = {")
    api_obj_txt = api_ts[m_start:] if m_start != -1 else ""
    methods = []
    for m in re.finditer(r"^\s{2}(?:async\s+)?([a-zA-Z0-9_]+)\s*\(", api_obj_txt, re.MULTILINE):
        mname = m.group(1)
        if mname in {"if", "for", "switch", "catch", "constructor"}:
            continue
        lineno = api_ts[:m_start].count("\n") + api_obj_txt[:m.start()].count("\n") + 1
        src_refs = [f for f, t in fe_files.items() if re.search(rf"\bapi\.{re.escape(mname)}\b|\b{re.escape(mname)}\b", t)]
        test_refs = [f for f, t in fe_tests.items() if re.search(rf"\b{re.escape(mname)}\b", t)]
        methods.append({
            "method": mname,
            "line": lineno,
            "src_refs": src_refs,
            "test_refs": test_refs,
        })
    unused_api_methods = [x for x in methods if not x["src_refs"]]
    return {
        "total_api_methods": len(methods),
        "unused_in_src": unused_api_methods,
        "all_methods": methods,
    }


def audit_ais_services():
    ais_files = [
        "ai_verdict_service.py",
        "verdict_pipeline.py",
        "prompt_studio_service.py",
        "policy_compiler_service.py",
        "policy_generation_service.py",
        "policy_simulation_service.py",
        "policy_quality_validator.py",
        "policy_governance.py",
        "policy_version_governance_service.py",
        "policy_eligibility_service.py",
        "policy_lifecycle_monitor.py",
        "historical_eligibility_service.py",
        "historical_ground_truth_validator.py",
        "ground_truth_certification_service.py",
        "independent_verdict_validator.py",
        "verdict_claim_validator.py",
        "verdict_guardrails_engine.py",
        "verdict_trustworthiness_engine.py",
        "reasoning_integrity_engine.py",
        "model_claim_extractor.py",
        "model_payload_allowlist.py",
        "evidence_normalization_service.py",
        "evidence_contract_service.py",
        "evidence_preflight_validator.py",
        "evidence_sufficiency_engine.py",
        "evidence_requirement_mapper.py",
        "evidence_compaction_service.py",
        "token_budget_service.py",
        "tokenizer_service.py",
        "verified_semantic_retrieval_service.py",
        "evaluation_service.py",
        "ais_evaluation_service.py",
        "empirical_accuracy_evaluator.py",
        "empirical_benchmark_harness.py",
        "ais27_benchmark_runner.py",
        "calibration_evaluator.py",
        "calibration_evaluation_service.py",
        "wilson_evaluator.py",
        "confidence_normalizer.py",
        "actual_prompt_capture_service.py",
        "production_readiness_service.py",
        "bulk_quality_audit_service.py",
        "rule_learning_service.py",
        "rule_intelligence_analyzer.py",
        "detection_archetype_registry.py",
        "learning_service.py",
        "dry_run_service.py",
    ]
    da = json.loads((EVIDENCE_DIR / "deep_audit.json").read_text(encoding="utf-8"))
    svc_map = {Path(s["file"]).name: s for s in da["backend"]["services"]}
    return [svc_map[f] for f in ais_files if f in svc_map]


def audit_dependencies():
    # Python requirements vs imports
    req_lines = (REPO_ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8").splitlines()
    reqs = []
    for l in req_lines:
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        pkg = re.split(r"[>=<!~\[]", l)[0].strip()
        reqs.append({"raw": l, "pkg": pkg})

    # Map PyPI name -> import name(s)
    import_aliases = {
        "uvicorn": ["uvicorn"],
        "email-validator": ["email_validator"],
        "pydantic-settings": ["pydantic_settings"],
        "python-multipart": ["multipart", "python_multipart"],
        "pytest-asyncio": ["pytest_asyncio"],
        "python-dateutil": ["dateutil"],
        "psycopg2-binary": ["psycopg2"],
    }
    be_corpus = ""
    for p in list((REPO_ROOT / "backend" / "app").rglob("*.py")) + list((REPO_ROOT / "backend" / "tests").rglob("*.py")) + list((REPO_ROOT / "backend" / "alembic").rglob("*.py")):
        be_corpus += "\n" + p.read_text(encoding="utf-8", errors="replace")

    py_dep_status = []
    for r in reqs:
        pkg = r["pkg"]
        names = import_aliases.get(pkg.lower(), [pkg.lower().replace("-", "_")])
        hits = sum(len(re.findall(rf"\b{re.escape(n)}\b", be_corpus)) for n in names)
        py_dep_status.append({**r, "import_names": names, "code_refs": hits})

    # Node package.json vs frontend imports
    pkg_json = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    fe_corpus = ""
    for p in list((REPO_ROOT / "frontend" / "src").rglob("*")) + list((REPO_ROOT / "frontend").glob("*.*")):
        if p.is_file() and p.suffix in {".ts", ".tsx", ".mjs", ".css", ".json"} and p.name != "package-lock.json":
            fe_corpus += "\n" + p.read_text(encoding="utf-8", errors="replace")

    node_deps = []
    for section in ["dependencies", "devDependencies"]:
        for pkg, ver in pkg_json.get(section, {}).items():
            hits = len(re.findall(re.escape(pkg), fe_corpus))
            node_deps.append({"section": section, "pkg": pkg, "version": ver, "refs": hits})

    return {"python": py_dep_status, "node": node_deps}


def main():
    fe_api = audit_frontend_api_client()
    ais = audit_ais_services()
    deps = audit_dependencies()
    out = {"frontend_api": fe_api, "ais_services": ais, "dependencies": deps}
    (EVIDENCE_DIR / "ais_api_deps_audit.json").write_text(json.dumps(out, indent=2), encoding="utf-8")

    print("=== FRONTEND api.ts UNUSED METHODS ===", len(fe_api["unused_in_src"]), "/", fe_api["total_api_methods"])
    for m in fe_api["unused_in_src"]:
        print(f"  L{m['line']:4d} api.{m['method']} (tests={m['test_refs']})")

    print("\n=== PYTHON DEPENDENCIES ===")
    for d in deps["python"]:
        print(f"  {d['pkg']:22s} refs={d['code_refs']:4d}  ({d['raw']})")

    print("\n=== NODE DEPENDENCIES ===")
    for d in deps["node"]:
        print(f"  [{d['section']:15s}] {d['pkg']:28s} refs={d['refs']:4d}  ({d['version']})")

    print("\n=== AIS & LLM SERVICES CALLERS ===")
    for s in ais:
        print(f"  {s['lines']:5d}L  prod={len(s['prod_callers']):2d}  tests={s['test_callers_count']:2d}  {Path(s['file']).name:42s} callers={[Path(c).name for c in s['prod_callers']]}")


if __name__ == "__main__":
    main()
