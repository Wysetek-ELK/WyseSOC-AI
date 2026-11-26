"""Non-invasive Backend, AIS/LLM, DB, Worker, Config & Duplicate Audit Script for Verdictum AI CCA 1.0."""
import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "docs" / "CCA_1_0"
EVIDENCE_DIR = OUT_DIR / "evidence"
BE_APP = REPO_ROOT / "backend" / "app"
BE_TESTS = REPO_ROOT / "backend" / "tests"
BE_ALEMBIC = REPO_ROOT / "backend" / "alembic"


def module_name_from_path(p: Path) -> str:
    rel = p.relative_to(REPO_ROOT / "backend").with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def analyze_backend_graph() -> Dict[str, Any]:
    app_py_files = sorted(BE_APP.rglob("*.py"))
    other_py_files = []
    for sub in ["backend/tests", "backend/scripts", "backend/alembic", "scripts", "scratch", "deployment"]:
        sp = REPO_ROOT / sub
        if sp.exists():
            other_py_files.extend(sorted(sp.rglob("*.py")))

    mod_to_file = {module_name_from_path(p): p.relative_to(REPO_ROOT).as_posix() for p in app_py_files}
    file_texts: Dict[str, str] = {}
    for p in app_py_files + other_py_files:
        file_texts[p.relative_to(REPO_ROOT).as_posix()] = p.read_text(encoding="utf-8", errors="replace")

    imports_out: Dict[str, Set[str]] = defaultdict(set)
    imported_by: Dict[str, Set[str]] = defaultdict(set)
    external_pkgs: Set[str] = set()

    # Parse imports across all python files
    for rel, txt in file_texts.items():
        try:
            tree = ast.parse(txt, filename=rel)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top == "app":
                        # match longest module
                        parts = alias.name.split(".")
                        for i in range(len(parts), 0, -1):
                            cand = ".".join(parts[:i])
                            if cand in mod_to_file:
                                imports_out[rel].add(mod_to_file[cand])
                                imported_by[mod_to_file[cand]].add(rel)
                                break
                    else:
                        external_pkgs.add(top)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith("app"):
                    for alias in node.names:
                        full_cand = f"{mod}.{alias.name}"
                        if full_cand in mod_to_file:
                            imports_out[rel].add(mod_to_file[full_cand])
                            imported_by[mod_to_file[full_cand]].add(rel)
                    parts = mod.split(".")
                    for i in range(len(parts), 0, -1):
                        cand = ".".join(parts[:i])
                        if cand in mod_to_file:
                            imports_out[rel].add(mod_to_file[cand])
                            imported_by[mod_to_file[cand]].add(rel)
                            break
                elif mod:
                    external_pkgs.add(mod.split(".")[0])

    # Check string-based references (e.g. celery task routes, dynamic importlib)
    all_app_text = "\n".join(file_texts[p.relative_to(REPO_ROOT).as_posix()] for p in app_py_files)
    all_deploy_text = ""
    for df in (REPO_ROOT / "deployment").rglob("*"):
        if df.is_file():
            all_deploy_text += "\n" + df.read_text(encoding="utf-8", errors="replace")

    modules_info = []
    for p in app_py_files:
        rel = p.relative_to(REPO_ROOT).as_posix()
        mod = module_name_from_path(p)
        importers = sorted(imported_by.get(rel, set()))
        prod_importers = [x for x in importers if x.startswith("backend/app/")]
        test_importers = [x for x in importers if x.startswith("backend/tests/")]
        script_importers = [x for x in importers if not x.startswith("backend/app/") and not x.startswith("backend/tests/")]
        deploy_refs = mod in all_deploy_text or p.stem in all_deploy_text
        modules_info.append({
            "file": rel,
            "module": mod,
            "lines": len(file_texts[rel].splitlines()),
            "prod_importers": prod_importers,
            "test_importers": test_importers,
            "script_importers": script_importers,
            "deploy_refs": deploy_refs,
            "imports_out": sorted(imports_out.get(rel, set())),
        })

    # Inspect SQLAlchemy models & columns
    models_info = []
    for p in sorted((BE_APP / "models").glob("*.py")):
        if p.name == "__init__.py":
            continue
        rel = p.relative_to(REPO_ROOT).as_posix()
        txt = file_texts[rel]
        tree = ast.parse(txt)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                bases = [ast.unparse(b) for b in node.bases]
                if any("Base" in b for b in bases):
                    tablename = None
                    cols = []
                    rels = []
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for t in item.targets:
                                if isinstance(t, ast.Name):
                                    if t.id == "__tablename__" and isinstance(item.value, ast.Constant):
                                        tablename = item.value.value
                                    elif "Column(" in ast.unparse(item.value) or "mapped_column(" in ast.unparse(item.value):
                                        cols.append(t.id)
                                    elif "relationship(" in ast.unparse(item.value):
                                        rels.append(t.id)
                        elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            val_s = ast.unparse(item.value) if item.value else ""
                            if "mapped_column" in val_s or "Column" in val_s:
                                cols.append(item.target.id)
                            elif "relationship" in val_s:
                                rels.append(item.target.id)
                    # Check references to class name across backend/app (excluding models) and backend/tests
                    cls_name = node.name
                    app_refs = [f for f, ft in file_texts.items() if f.startswith("backend/app/") and not f.startswith("backend/app/models/") and re.search(rf"\b{re.escape(cls_name)}\b", ft)]
                    test_refs = [f for f, ft in file_texts.items() if f.startswith("backend/tests/") and re.search(rf"\b{re.escape(cls_name)}\b", ft)]
                    models_info.append({
                        "model": cls_name,
                        "tablename": tablename,
                        "file": rel,
                        "lineno": node.lineno,
                        "columns": cols,
                        "relationships": rels,
                        "app_refs": app_refs,
                        "test_refs": test_refs,
                    })

    # Inspect unused top-level functions & classes in backend/app/services, utils, core, schemas
    unused_symbols = []
    # Build unified corpus of all python + frontend + scripts text for reference checking
    all_texts_no_self = {f: t for f, t in file_texts.items()}
    for p in sorted(BE_APP.rglob("*.py")):
        rel = p.relative_to(REPO_ROOT).as_posix()
        if rel.startswith("backend/app/api/"):
            continue  # API handlers are registered via decorators
        txt = file_texts[rel]
        try:
            tree = ast.parse(txt)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = node.name
                if name.startswith("__") and name.endswith("__"):
                    continue
                # Check occurrences in other files OR inside same file (other than definition line)
                other_refs = [f for f, ft in all_texts_no_self.items() if f != rel and re.search(rf"\b{re.escape(name)}\b", ft)]
                # Check occurrences within same file excluding def line
                lines = txt.splitlines()
                same_file_hits = 0
                for idx, l in enumerate(lines, 1):
                    if idx != node.lineno and re.search(rf"\b{re.escape(name)}\b", l):
                        same_file_hits += 1
                if not other_refs and same_file_hits == 0:
                    unused_symbols.append({
                        "file": rel,
                        "symbol": name,
                        "kind": "class" if isinstance(node, ast.ClassDef) else "function",
                        "lineno": node.lineno,
                        "end_lineno": getattr(node, "end_lineno", node.lineno),
                        "lines": getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                    })

    # Inspect duplicate function/method bodies (normalized AST or normalized text hash)
    func_hashes = defaultdict(list)
    for p in app_py_files:
        rel = p.relative_to(REPO_ROOT).as_posix()
        txt = file_texts[rel]
        try:
            tree = ast.parse(txt)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body_lines = getattr(node, "end_lineno", node.lineno) - node.lineno + 1
                if body_lines >= 8:
                    # Normalize body AST dump without name
                    body_dump = "|".join(ast.dump(stmt) for stmt in node.body)
                    h = hashlib.sha256(body_dump.encode()).hexdigest()[:16]
                    func_hashes[h].append({
                        "file": rel,
                        "name": node.name,
                        "lineno": node.lineno,
                        "end_lineno": getattr(node, "end_lineno", node.lineno),
                        "lines": body_lines,
                    })
    exact_ast_duplicates = [v for v in func_hashes.values() if len(v) > 1]

    # Check unused imports in backend/app using AST
    unused_imports = []
    for p in app_py_files:
        rel = p.relative_to(REPO_ROOT).as_posix()
        if p.name == "__init__.py":
            continue
        txt = file_texts[rel]
        try:
            tree = ast.parse(txt)
        except SyntaxError:
            continue
        # Collect all Name and Attribute references outside Import/ImportFrom
        used_names: Set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # forward type annotations like "Incident"
                for tok in re.findall(r"[A-Za-z_][A-Za-z0-9_]*", node.value):
                    used_names.add(tok)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bound = alias.asname or alias.name.split(".")[0]
                    if bound not in used_names:
                        unused_imports.append({"file": rel, "line": node.lineno, "import": alias.name, "bound": bound})
            elif isinstance(node, ast.ImportFrom):
                if node.module == "__future__":
                    continue
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    bound = alias.asname or alias.name
                    if bound not in used_names:
                        unused_imports.append({"file": rel, "line": node.lineno, "import": f"from {node.module} import {alias.name}", "bound": bound})

    return {
        "modules": modules_info,
        "models": models_info,
        "unused_top_level_symbols": unused_symbols,
        "exact_ast_duplicates": exact_ast_duplicates,
        "unused_imports": unused_imports,
        "external_pkgs_imported": sorted(external_pkgs),
    }


def main():
    res = analyze_backend_graph()
    (EVIDENCE_DIR / "backend_analysis.json").write_text(json.dumps(res, indent=2), encoding="utf-8")

    print("=== BACKEND MODULES WITH 0 PROD IMPORTERS ===")
    for m in res["modules"]:
        if not m["prod_importers"] and m["file"] not in {"backend/app/main.py", "backend/app/cli.py", "backend/app/__init__.py"}:
            print(f"  {m['file']} ({m['lines']}L) tests={len(m['test_importers'])} scripts={len(m['script_importers'])} deploy={m['deploy_refs']}")

    print("\n=== DB MODELS WITH 0 NON-MODEL APP REFS ===")
    for md in res["models"]:
        if not md["app_refs"]:
            print(f"  {md['model']} (table={md['tablename']}, {md['file']}:{md['lineno']}) tests={len(md['test_refs'])}")

    print("\n=== UNUSED TOP-LEVEL SYMBOLS (outside api/) ===", len(res["unused_top_level_symbols"]))
    for s in res["unused_top_level_symbols"][:40]:
        print(f"  {s['file']}:{s['lineno']} {s['kind']} {s['symbol']} ({s['lines']}L)")

    print("\n=== EXACT AST DUPLICATE FUNCTIONS (>=8 lines) ===", len(res["exact_ast_duplicates"]))
    for grp in res["exact_ast_duplicates"]:
        print("  DUP GROUP:", [(g["file"], g["name"], g["lineno"], g["lines"]) for g in grp])

    print("\n=== UNUSED IMPORTS IN backend/app ===", len(res["unused_imports"]))


if __name__ == "__main__":
    main()
