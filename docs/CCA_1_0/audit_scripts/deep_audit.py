"""Deep audit script for Services, AIS/LLM legacy overlap, Schemas, Models, Config, Infra, and Frontend summary."""
import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "docs" / "CCA_1_0"
EVIDENCE_DIR = OUT_DIR / "evidence"


def print_frontend_details():
    fe = json.loads((EVIDENCE_DIR / "frontend_analysis.json").read_text(encoding="utf-8"))
    out = {}
    out["active_pages"] = sorted(
        [p for p in fe["pages"] if not p["shadowed_by_redirect_to"]],
        key=lambda x: -x["lines"]
    )
    out["shadowed_pages"] = [p for p in fe["pages"] if p["shadowed_by_redirect_to"]]
    out["unused_exports_by_file"] = {
        m["file"]: m["unused_exports"] for m in fe["modules"] if m["unused_exports"]
    }
    return out


def analyze_services_and_schemas():
    be_app = REPO_ROOT / "backend" / "app"
    be_tests = REPO_ROOT / "backend" / "tests"

    all_prod_files = {
        p.relative_to(REPO_ROOT).as_posix(): p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(be_app.rglob("*.py"))
    }
    all_test_files = {
        p.relative_to(REPO_ROOT).as_posix(): p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(be_tests.rglob("*.py"))
    }
    all_script_files = {}
    for sub in ["scripts", "scratch", "backend/scripts", "backend/app/scripts"]:
        sp = REPO_ROOT / sub
        if sp.exists():
            for p in sorted(sp.rglob("*.py")):
                all_script_files[p.relative_to(REPO_ROOT).as_posix()] = p.read_text(encoding="utf-8", errors="replace")

    # Services inventory + caller tracing
    services = []
    for p in sorted((be_app / "services").rglob("*.py")):
        rel = p.relative_to(REPO_ROOT).as_posix()
        txt = all_prod_files[rel]
        mod = "app." + p.relative_to(be_app).with_suffix("").as_posix().replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[:-9]
        stem = p.stem

        prod_callers = [f for f, ft in all_prod_files.items() if f != rel and (mod in ft or f".{stem}" in ft or f" {stem} " in ft)]
        test_callers = [f for f, ft in all_test_files.items() if mod in ft or f".{stem}" in ft]
        script_callers = [f for f, ft in all_script_files.items() if mod in ft or f".{stem}" in ft]

        # Extract classes & functions
        try:
            tree = ast.parse(txt)
            classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
            funcs = [n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        except SyntaxError:
            classes, funcs = [], []

        services.append({
            "file": rel,
            "module": mod,
            "lines": len(txt.splitlines()),
            "classes": classes,
            "functions": funcs,
            "prod_callers": prod_callers,
            "test_callers_count": len(test_callers),
            "script_callers": script_callers,
        })

    # Schemas usage
    schemas = []
    for p in sorted((be_app / "schemas").glob("*.py")):
        if p.name == "__init__.py":
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        txt = all_prod_files[rel]
        tree = ast.parse(txt)
        cls_list = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
        unused_cls = []
        for c in cls_list:
            prod_hits = [f for f, ft in all_prod_files.items() if f != rel and f != "backend/app/schemas/__init__.py" and re.search(rf"\b{re.escape(c)}\b", ft)]
            same_hits = len(re.findall(rf"\b{re.escape(c)}\b", txt)) - 1
            test_hits = [f for f, ft in all_test_files.items() if re.search(rf"\b{re.escape(c)}\b", ft)]
            if not prod_hits and same_hits == 0:
                unused_cls.append({"class": c, "test_hits": len(test_hits)})
        schemas.append({
            "file": rel,
            "lines": len(txt.splitlines()),
            "total_classes": len(cls_list),
            "unused_in_prod_classes": unused_cls,
        })

    # Config keys usage in backend/app/config.py
    cfg_txt = all_prod_files["backend/app/config.py"]
    cfg_tree = ast.parse(cfg_txt)
    settings_keys = []
    for node in cfg_tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Settings":
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    key = item.target.id
                    if key == "model_config":
                        continue
                    prod_refs = [f for f, ft in all_prod_files.items() if f != "backend/app/config.py" and key in ft]
                    test_refs = [f for f, ft in all_test_files.items() if key in ft]
                    deploy_refs = []
                    for df in (REPO_ROOT / "deployment").rglob("*"):
                        if df.is_file() and key in df.read_text(encoding="utf-8", errors="replace"):
                            deploy_refs.append(df.relative_to(REPO_ROOT).as_posix())
                    settings_keys.append({
                        "key": key,
                        "line": item.lineno,
                        "prod_refs": prod_refs,
                        "test_refs_count": len(test_refs),
                        "deploy_refs": deploy_refs,
                    })

    # Unused service methods check (across services/)
    unused_methods = []
    corpus_prod = "\n".join(all_prod_files.values())
    corpus_tests = "\n".join(all_test_files.values())
    corpus_scripts = "\n".join(all_script_files.values())
    for p in sorted((be_app / "services").rglob("*.py")):
        rel = p.relative_to(REPO_ROOT).as_posix()
        txt = all_prod_files[rel]
        try:
            tree = ast.parse(txt)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        mname = item.name
                        if mname.startswith("__") and mname.endswith("__"):
                            continue
                        # Count occurrences across entire prod codebase (excluding def line in same file)
                        pat = re.compile(rf"\b{re.escape(mname)}\b")
                        prod_hits = sum(len(pat.findall(ft)) for f, ft in all_prod_files.items() if f != rel)
                        same_hits = len(pat.findall(txt)) - 1
                        test_hits = len(pat.findall(corpus_tests))
                        script_hits = len(pat.findall(corpus_scripts))
                        if prod_hits == 0 and same_hits == 0:
                            unused_methods.append({
                                "file": rel,
                                "class": node.name,
                                "method": mname,
                                "lineno": item.lineno,
                                "end_lineno": getattr(item, "end_lineno", item.lineno),
                                "lines": getattr(item, "end_lineno", item.lineno) - item.lineno + 1,
                                "test_hits": test_hits,
                                "script_hits": script_hits,
                            })

    return {
        "services": services,
        "schemas": schemas,
        "settings_keys": settings_keys,
        "unused_service_methods": unused_methods,
    }


def main():
    fe = print_frontend_details()
    be = analyze_services_and_schemas()
    result = {"frontend": fe, "backend": be}
    (EVIDENCE_DIR / "deep_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("=== ACTIVE FRONTEND PAGES ===")
    for p in fe["active_pages"]:
        print(f"  {p['lines']:5d}L  {p['route']:35s} sidebar={p['in_sidebar']}  {p['file']}")

    print("\n=== BACKEND SERVICES SORTED BY LINES (TOP 25) ===")
    for s in sorted(be["services"], key=lambda x: -x["lines"])[:25]:
        print(f"  {s['lines']:5d}L  prod_callers={len(s['prod_callers']):2d}  tests={s['test_callers_count']:2d}  {s['file']}")

    print("\n=== SERVICES WITH <= 1 PROD CALLER ===")
    for s in be["services"]:
        if len(s["prod_callers"]) <= 1:
            print(f"  {s['lines']:5d}L  prod={s['prod_callers']}  tests={s['test_callers_count']}  scripts={s['script_callers']}  {s['file']}")

    print("\n=== SETTINGS KEYS WITH 0 PROD REFS ===")
    for k in be["settings_keys"]:
        if not k["prod_refs"]:
            print(f"  L{k['line']:3d} {k['key']} (tests={k['test_refs_count']}, deploy={k['deploy_refs']})")

    print("\n=== UNUSED SERVICE METHODS IN PROD ===", len(be["unused_service_methods"]))
    for m in be["unused_service_methods"]:
        print(f"  {m['file']}:{m['lineno']} {m['class']}.{m['method']} ({m['lines']}L) tests={m['test_hits']} scripts={m['script_hits']}")


if __name__ == "__main__":
    main()
