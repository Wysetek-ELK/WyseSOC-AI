"""Non-invasive codebase inventory & static AST/import analyzer for Verdictum AI CCA 1.0."""
import ast
import csv
import json
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "docs" / "CCA_1_0"
EVIDENCE_DIR = OUT_DIR / "evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def get_git_info() -> Dict[str, Any]:
    branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    tracked = subprocess.check_output(["git", "ls-files"], cwd=REPO_ROOT, text=True).splitlines()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT, text=True).splitlines()
    return {
        "branch": branch,
        "commit": commit,
        "tracked_count": len(tracked),
        "tracked_files": tracked,
        "git_status_lines": status,
    }


def count_lines(filepath: Path) -> Dict[str, int]:
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"total": 0, "non_empty": 0, "code": 0}
    lines = text.splitlines()
    non_empty = sum(1 for l in lines if l.strip())
    suffix = filepath.suffix.lower()
    if suffix == ".py":
        code = sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))
    elif suffix in {".ts", ".tsx", ".js", ".jsx", ".mjs", ".css"}:
        code = sum(1 for l in lines if l.strip() and not l.strip().startswith("//"))
    elif suffix == ".sh":
        code = sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))
    else:
        code = non_empty
    return {"total": len(lines), "non_empty": non_empty, "code": code}


def classify_file(rel_path: str) -> str:
    p = rel_path.replace("\\", "/")
    if p.startswith("frontend/"):
        if p.startswith("frontend/tests/"):
            return "frontend_test"
        if p.startswith("frontend/public/") or p.endswith((".png", ".ico", ".svg", ".jpg", ".jpeg")):
            return "frontend_asset"
        if (p.startswith("frontend/src/app/") and p.endswith("/page.tsx")) or p == "frontend/src/app/page.tsx":
            return "frontend_page"
        if p.startswith("frontend/src/app/"):
            return "frontend_app_support"
        if p.startswith("frontend/src/components/"):
            return "frontend_component"
        if p.startswith("frontend/src/lib/"):
            return "frontend_lib"
        if p.startswith("frontend/src/context/"):
            return "frontend_context"
        if p.startswith("frontend/src/config/"):
            return "frontend_config"
        if p.startswith("frontend/src/data/"):
            return "frontend_data"
        return "frontend_build_config"
    if p.startswith("backend/"):
        if p.startswith("backend/tests/"):
            return "backend_test"
        if p.startswith("backend/alembic/versions/"):
            return "backend_migration"
        if p.startswith("backend/alembic/"):
            return "backend_migration_config"
        if p.startswith("backend/app/api/"):
            return "backend_api"
        if p.startswith("backend/app/models/"):
            return "backend_model"
        if p.startswith("backend/app/schemas/"):
            return "backend_schema"
        if p.startswith("backend/app/services/"):
            return "backend_service"
        if p.startswith("backend/app/workers/"):
            return "backend_worker"
        if p.startswith("backend/app/utils/"):
            return "backend_util"
        if p.startswith("backend/app/core/"):
            return "backend_core"
        if p.startswith("backend/app/scripts/") or p.startswith("backend/scripts/"):
            return "backend_script"
        if p.startswith("backend/app/"):
            return "backend_entrypoint"
        return "backend_config"
    if p.startswith("deployment/"):
        return "deployment"
    if p.startswith("scripts/"):
        return "root_script"
    if p.startswith("scratch/"):
        return "scratch"
    if p.startswith("fixtures/"):
        return "fixture"
    if p.startswith("docs/"):
        return "docs"
    if p.endswith(".md"):
        return "root_docs"
    if p.endswith(".png") or p.endswith(".jpg") or p.endswith(".ico"):
        return "root_asset"
    return "root_config"


def analyze_python_file(filepath: Path) -> Dict[str, Any]:
    src = filepath.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(src, filename=str(filepath))
    except SyntaxError as e:
        return {"syntax_error": str(e), "imports": [], "functions": [], "classes": []}

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({"module": alias.name, "name": alias.asname or alias.name, "line": node.lineno})
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            for alias in node.names:
                imports.append({"module": f"{mod}.{alias.name}" if mod else alias.name, "from": mod, "name": alias.name, "asname": alias.asname, "line": node.lineno})

    functions = []
    classes = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            decs = [ast.unparse(d) for d in node.decorator_list]
            functions.append({
                "name": node.name,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "lineno": node.lineno,
                "end_lineno": getattr(node, "end_lineno", node.lineno),
                "lines": getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                "decorators": decs,
            })
        elif isinstance(node, ast.ClassDef):
            methods = []
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    decs = [ast.unparse(d) for d in item.decorator_list]
                    methods.append({
                        "name": item.name,
                        "is_async": isinstance(item, ast.AsyncFunctionDef),
                        "lineno": item.lineno,
                        "end_lineno": getattr(item, "end_lineno", item.lineno),
                        "lines": getattr(item, "end_lineno", item.lineno) - item.lineno + 1,
                        "decorators": decs,
                    })
            bases = [ast.unparse(b) for b in node.bases]
            classes.append({
                "name": node.name,
                "bases": bases,
                "lineno": node.lineno,
                "end_lineno": getattr(node, "end_lineno", node.lineno),
                "lines": getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                "methods": methods,
            })

    return {
        "imports": imports,
        "functions": functions,
        "classes": classes,
        "text_length": len(src),
    }


def analyze_ts_file(filepath: Path) -> Dict[str, Any]:
    src = filepath.read_text(encoding="utf-8", errors="replace")
    imports = []
    for m in re.finditer(r"import\s+(?:type\s+)?(?:[\s\S]*?)\s+from\s+['\"]([^'\"]+)['\"]", src):
        imports.append(m.group(1))
    # dynamic imports
    for m in re.finditer(r"import\(['\"]([^'\"]+)['\"]\)", src):
        imports.append(m.group(1))

    exports = []
    for m in re.finditer(r"^\s*export\s+(?:default\s+)?(?:async\s+)?(function|const|let|type|interface|class|enum)\s+([A-Za-z0-9_]+)", src, re.MULTILINE):
        exports.append({"kind": m.group(1), "name": m.group(2), "line": src[:m.start()].count("\n") + 1})
    for m in re.finditer(r"^\s*export\s+\{([^}]+)\}", src, re.MULTILINE):
        names = [x.strip().split(" as ")[-1].strip() for x in m.group(1).split(",") if x.strip()]
        for n in names:
            exports.append({"kind": "reexport", "name": n, "line": src[:m.start()].count("\n") + 1})

    hooks = []
    for m in re.finditer(r"export\s+(?:function|const)\s+(use[A-Z][A-Za-z0-9_]*)", src):
        hooks.append(m.group(1))

    return {"imports": imports, "exports": exports, "hooks": hooks}


def main():
    git_info = get_git_info()
    files_data = []
    cat_counts = Counter()
    cat_lines = defaultdict(lambda: {"total": 0, "non_empty": 0, "code": 0})

    for rel in git_info["tracked_files"]:
        full = REPO_ROOT / rel
        if not full.exists():
            continue
        cat = classify_file(rel)
        cat_counts[cat] += 1
        is_binary = full.suffix.lower() in {".png", ".jpg", ".jpeg", ".ico", ".zip", ".docx", ".db", ".svg"}
        lc = {"total": 0, "non_empty": 0, "code": 0} if is_binary else count_lines(full)
        cat_lines[cat]["total"] += lc["total"]
        cat_lines[cat]["non_empty"] += lc["non_empty"]
        cat_lines[cat]["code"] += lc["code"]

        entry: Dict[str, Any] = {
            "path": rel,
            "category": cat,
            "size_bytes": full.stat().st_size,
            "lines": lc,
            "is_binary": is_binary,
        }
        if rel.startswith("backend/") and rel.endswith(".py"):
            entry["ast"] = analyze_python_file(full)
        elif rel.startswith("frontend/") and full.suffix in {".ts", ".tsx", ".mjs"}:
            entry["ts"] = analyze_ts_file(full)
        files_data.append(entry)

    # Compute app source code metrics cleanly
    frontend_src_cats = {
        "frontend_page", "frontend_app_support", "frontend_component",
        "frontend_lib", "frontend_context", "frontend_config", "frontend_data"
    }
    backend_src_cats = {
        "backend_api", "backend_model", "backend_schema", "backend_service",
        "backend_worker", "backend_util", "backend_core", "backend_entrypoint",
        "backend_script"
    }

    fe_files = [f for f in files_data if f["category"] in frontend_src_cats]
    be_files = [f for f in files_data if f["category"] in backend_src_cats]
    mig_files = [f for f in files_data if f["category"] == "backend_migration"]
    test_files = [f for f in files_data if f["category"] in {"frontend_test", "backend_test"}]
    script_files = [f for f in files_data if f["category"] in {"root_script", "backend_script", "scratch"}]
    deploy_files = [f for f in files_data if f["category"] == "deployment"]

    summary = {
        "git_branch": git_info["branch"],
        "git_commit": git_info["commit"],
        "tracked_files_total": git_info["tracked_count"],
        "untracked_files_count": len([l for l in git_info["git_status_lines"] if l.startswith("??")]),
        "modified_files_count": len([l for l in git_info["git_status_lines"] if not l.startswith("??")]),
        "category_counts": dict(cat_counts),
        "category_lines": dict(cat_lines),
        "frontend_source_files": len(fe_files),
        "frontend_source_lines_total": sum(f["lines"]["total"] for f in fe_files),
        "frontend_source_lines_code": sum(f["lines"]["code"] for f in fe_files),
        "backend_source_files": len(be_files),
        "backend_source_lines_total": sum(f["lines"]["total"] for f in be_files),
        "backend_source_lines_code": sum(f["lines"]["code"] for f in be_files),
        "total_app_source_files": len(fe_files) + len(be_files),
        "total_app_source_lines_total": sum(f["lines"]["total"] for f in fe_files + be_files),
        "total_app_source_lines_code": sum(f["lines"]["code"] for f in fe_files + be_files),
        "migration_files": len(mig_files),
        "test_files": len(test_files),
        "deployment_files": len(deploy_files),
        "scripts_and_scratch_files": len(script_files),
    }

    inventory = {
        "summary": summary,
        "counting_methodology": {
            "application_source": "Tracked files under frontend/src/ (excluding non-code assets) and backend/app/ (including backend/app/scripts/), excluding tests, alembic migrations, docs, scratch, root scripts, deployment scripts, and node_modules/venv/.next.",
            "total_lines": "Raw newline-delimited lines including blanks and comments.",
            "code_lines": "Non-empty lines excluding single-line comments (# for Python/shell, // for TS/JS/CSS).",
        },
        "files": files_data,
    }

    (OUT_DIR / "CODEBASE_INVENTORY.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
