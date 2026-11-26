"""Non-invasive Frontend & API Usage Audit Script for Verdictum AI CCA 1.0."""
import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set

REPO_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "docs" / "CCA_1_0"
EVIDENCE_DIR = OUT_DIR / "evidence"
FE_SRC = REPO_ROOT / "frontend" / "src"
FE_TESTS = REPO_ROOT / "frontend" / "tests"
BE_API = REPO_ROOT / "backend" / "app" / "api"


def resolve_ts_import(imp: str, from_file: Path) -> str | None:
    if imp.startswith("@/"):
        target = FE_SRC / imp[2:]
    elif imp.startswith("."):
        target = (from_file.parent / imp).resolve()
    else:
        return None  # npm package

    for ext in ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.tsx"]:
        cand = Path(str(target) + ext)
        if cand.is_file():
            try:
                return cand.relative_to(REPO_ROOT).as_posix()
            except ValueError:
                return None
    return None


def analyze_frontend() -> Dict[str, Any]:
    # 1. Parse next.config.ts redirects
    next_cfg = (REPO_ROOT / "frontend" / "next.config.ts").read_text(encoding="utf-8")
    redirects = []
    for m in re.finditer(r'source:\s*"([^"]+)"[\s\S]*?destination:\s*"([^"]+)"', next_cfg):
        redirects.append({"source": m.group(1), "destination": m.group(2)})

    # 2. Parse Sidebar NAV_GROUPS
    sidebar_src = (FE_SRC / "components" / "layout" / "Sidebar.tsx").read_text(encoding="utf-8")
    sidebar_hrefs = re.findall(r'href:\s*"([^"]+)"', sidebar_src)

    # 3. Collect all TS/TSX files in frontend/src
    src_files = sorted(
        list(FE_SRC.rglob("*.ts")) + list(FE_SRC.rglob("*.tsx")) + list(FE_SRC.rglob("*.css"))
    )
    file_texts = {f.relative_to(REPO_ROOT).as_posix(): f.read_text(encoding="utf-8", errors="replace") for f in src_files}
    test_texts = {f.relative_to(REPO_ROOT).as_posix(): f.read_text(encoding="utf-8", errors="replace") for f in FE_TESTS.rglob("*.*") if f.is_file()}
    script_texts = {}
    for folder in ["scripts", "backend/tests"]:
        p = REPO_ROOT / folder
        if p.exists():
            for f in p.rglob("*.*"):
                if f.is_file() and f.suffix in {".py", ".mjs", ".ts", ".js", ".sh"}:
                    script_texts[f.relative_to(REPO_ROOT).as_posix()] = f.read_text(encoding="utf-8", errors="replace")

    # 4. Build import graph
    imports_out: Dict[str, List[str]] = defaultdict(list)
    imported_by: Dict[str, List[str]] = defaultdict(list)
    npm_deps_used: Set[str] = set()

    for rel, txt in file_texts.items():
        if not rel.endswith((".ts", ".tsx")):
            continue
        f_path = REPO_ROOT / rel
        imps = re.findall(r"""(?:import|export)\s+(?:type\s+)?(?:[\s\S]*?\s+from\s+)?['"]([^'"]+)['"]""", txt)
        imps += re.findall(r"""import\(\s*['"]([^'"]+)['"]\s*\)""", txt)
        for imp in imps:
            resolved = resolve_ts_import(imp, f_path)
            if resolved:
                if resolved not in imports_out[rel]:
                    imports_out[rel].append(resolved)
                if rel not in imported_by[resolved]:
                    imported_by[resolved].append(rel)
            elif not imp.startswith(".") and not imp.startswith("@/") and not imp.startswith("next/") and imp != "react" and imp != "react-dom":
                pkg = imp.split("/")[0] if not imp.startswith("@") else "/".join(imp.split("/")[:2])
                npm_deps_used.add(pkg)
            elif imp.startswith("next") or imp in {"react", "react-dom"}:
                npm_deps_used.add(imp.split("/")[0])

    # 5. Analyze pages & routes
    pages = []
    redirect_sources = {r["source"] for r in redirects}
    # Normalize :id -> [id] for matching
    def route_to_pattern(route: str) -> str:
        return re.sub(r":([a-zA-Z0-9_]+)", r"[\1]", route)

    redirect_patterns = {route_to_pattern(r["source"]): r["destination"] for r in redirects}

    for rel, txt in file_texts.items():
        if rel.startswith("frontend/src/app/") and (rel.endswith("/page.tsx") or rel == "frontend/src/app/page.tsx"):
            route = "/" + rel[len("frontend/src/app/"):-len("/page.tsx")] if rel != "frontend/src/app/page.tsx" else "/"
            route = route.rstrip("/") or "/"
            shadowed_by = redirect_patterns.get(route)
            in_sidebar = route in sidebar_hrefs
            # Search hrefs across all frontend/src + tests + scripts
            link_refs_src = [f for f, t in file_texts.items() if f != rel and (f'"{route}"' in t or f"'{route}'" in t or f"`{route}`" in t or ( "[id]" in route and route.replace("[id]", "") in t ))]
            link_refs_tests = [f for f, t in {**test_texts, **script_texts}.items() if route in t]
            pages.append({
                "file": rel,
                "route": route,
                "lines": len(txt.splitlines()),
                "in_sidebar": in_sidebar,
                "shadowed_by_redirect_to": shadowed_by,
                "src_string_refs": link_refs_src,
                "test_script_refs": link_refs_tests,
                "imports_count": len(imports_out[rel]),
            })

    # 6. Analyze non-page modules (components, lib, config, context, data)
    modules = []
    for rel, txt in file_texts.items():
        if rel.startswith("frontend/src/app/") and (rel.endswith("/page.tsx") or rel in {"frontend/src/app/page.tsx", "frontend/src/app/layout.tsx", "frontend/src/app/globals.css"}):
            continue
        importers = imported_by.get(rel, [])
        # Also check if all importers are shadowed pages!
        active_importers = []
        shadowed_page_routes = {p["file"] for p in pages if p["shadowed_by_redirect_to"]}
        for imp_f in importers:
            if imp_f not in shadowed_page_routes:
                active_importers.append(imp_f)
        # Test references
        test_refs = [f for f, t in {**test_texts, **script_texts}.items() if Path(rel).stem in t or rel in t]
        # Exports
        exports = []
        for m in re.finditer(r"^\s*export\s+(?:default\s+)?(?:async\s+)?(function|const|let|type|interface|class|enum)\s+([A-Za-z0-9_]+)", txt, re.MULTILINE):
            exports.append({"kind": m.group(1), "name": m.group(2), "line": txt[:m.start()].count("\n") + 1})
        unused_exports = []
        for exp in exports:
            name = exp["name"]
            ref_files = [f for f, t in file_texts.items() if f != rel and re.search(rf"\b{re.escape(name)}\b", t)]
            t_ref_files = [f for f, t in test_texts.items() if re.search(rf"\b{re.escape(name)}\b", t)]
            if not ref_files and not t_ref_files:
                unused_exports.append(exp)
        modules.append({
            "file": rel,
            "lines": len(txt.splitlines()),
            "imported_by": importers,
            "active_importers": active_importers,
            "test_refs": test_refs,
            "export_count": len(exports),
            "unused_exports": unused_exports,
        })

    # 7. Check public/ assets
    public_assets = []
    pub_dir = REPO_ROOT / "frontend" / "public"
    all_fe_str = "\n".join(file_texts.values()) + "\n" + "\n".join(test_texts.values())
    for asset in sorted(pub_dir.rglob("*")):
        if asset.is_file():
            rel = asset.relative_to(REPO_ROOT).as_posix()
            fname = asset.name
            refs = [f for f, t in {**file_texts, **test_texts}.items() if fname in t]
            public_assets.append({"file": rel, "size_bytes": asset.stat().st_size, "refs": refs})

    return {
        "redirects": redirects,
        "sidebar_hrefs": sidebar_hrefs,
        "pages": pages,
        "modules": modules,
        "public_assets": public_assets,
        "npm_deps_imported": sorted(npm_deps_used),
        "imports_out": dict(imports_out),
        "imported_by": dict(imported_by),
    }


def analyze_api_endpoints() -> Dict[str, Any]:
    main_src = (REPO_ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    # Parse include_router calls in main.py
    router_mounts = defaultdict(list)
    for m in re.finditer(r"app\.include_router\(\s*([a-zA-Z0-9_]+)\.router(?:\s*,\s*prefix=([^\)]+))?\s*\)", main_src):
        mod_name = m.group(1)
        pref = (m.group(2) or '""').strip()
        if pref == "settings.API_V1_STR":
            pref = "/api"
        elif pref.startswith('"') or pref.startswith("'"):
            pref = pref.strip("\"'")
        router_mounts[mod_name].append(pref)

    # Parse each api/*.py
    endpoints = []
    fe_api_ts = (FE_SRC / "lib" / "api.ts").read_text(encoding="utf-8")
    fe_all = {f.relative_to(REPO_ROOT).as_posix(): f.read_text(encoding="utf-8", errors="replace") for f in FE_SRC.rglob("*") if f.is_file() and f.suffix in {".ts", ".tsx"}}
    be_tests = {f.relative_to(REPO_ROOT).as_posix(): f.read_text(encoding="utf-8", errors="replace") for f in (REPO_ROOT / "backend" / "tests").rglob("*.py")}
    scripts_all = {}
    for d in ["scripts", "scratch", "deployment", "backend/scripts", "backend/app/scripts"]:
        p = REPO_ROOT / d
        if p.exists():
            for f in p.rglob("*"):
                if f.is_file() and f.suffix in {".py", ".sh", ".mjs", ".conf", ".service"}:
                    scripts_all[f.relative_to(REPO_ROOT).as_posix()] = f.read_text(encoding="utf-8", errors="replace")

    for api_file in sorted(BE_API.glob("*.py")):
        if api_file.name in {"__init__.py", "deps.py"}:
            continue
        src = api_file.read_text(encoding="utf-8")
        mod_name = api_file.stem
        # Find router prefix inside file: APIRouter(prefix="...")
        r_pref_m = re.search(r'APIRouter\([^)]*prefix\s*=\s*["\']([^"\']+)["\']', src)
        router_prefix = r_pref_m.group(1) if r_pref_m else ""
        mounts = router_mounts.get(mod_name, [])

        tree = ast.parse(src, filename=str(api_file))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    dec_str = ast.unparse(dec)
                    rm = re.match(r"^router\.(get|post|put|patch|delete|options|head)\(\s*['\"]([^'\"]*)['\"]", dec_str)
                    if rm:
                        method = rm.group(1).upper()
                        subpath = rm.group(2)
                        rel_path = f"{router_prefix}{subpath}"
                        full_paths = [f"{m}{rel_path}" or "/" for m in mounts] if mounts else [f"(UNMOUNTED){rel_path}"]
                        # Auth inspection in args
                        fn_src = ast.get_source_segment(src, node) or ""
                        auth_deps = re.findall(r"Depends\(\s*([a-zA-Z0-9_.]+)\s*\)", fn_src)

                        # Search consumers by normalizing path params {foo} -> regex
                        regex_pat = re.sub(r"\{[^}]+\}", r"[^/\"'`\\s?]+", rel_path)
                        # Also match suffix without /api prefix or with /api or /api/v1
                        suffix_pat = regex_pat.lstrip("/")
                        fe_refs = []
                        if suffix_pat:
                            for ff, ft in fe_all.items():
                                if re.search(re.escape(rel_path).replace(r"\{", "{").replace(r"\}", "}"), ft) or re.search(regex_pat, ft):
                                    fe_refs.append(ff)
                        else:
                            # e.g. "/" or prefix root
                            for ff, ft in fe_all.items():
                                if router_prefix and router_prefix in ft:
                                    fe_refs.append(ff)

                        test_refs = []
                        for tf, tt in be_tests.items():
                            if re.search(regex_pat, tt) and (router_prefix in tt or subpath.strip("/") in tt):
                                test_refs.append(tf)

                        script_refs = []
                        for sf, st in scripts_all.items():
                            if re.search(regex_pat, st) and (router_prefix in st or subpath.strip("/") in st):
                                script_refs.append(sf)

                        endpoints.append({
                            "module": mod_name,
                            "file": api_file.relative_to(REPO_ROOT).as_posix(),
                            "function": node.name,
                            "lineno": node.lineno,
                            "end_lineno": getattr(node, "end_lineno", node.lineno),
                            "method": method,
                            "router_prefix": router_prefix,
                            "subpath": subpath,
                            "full_paths": full_paths,
                            "mounts": mounts,
                            "auth_deps": auth_deps,
                            "fe_refs": fe_refs,
                            "test_refs": test_refs,
                            "script_refs": script_refs,
                        })

    # Also find all API paths called by frontend/src/lib/api.ts
    fe_called_paths = set()
    for m in re.finditer(r"""[`'"](/[a-zA-Z0-9_/\-${}.?=&]+)[`'"]""", fe_api_ts):
        p = m.group(1)
        if not p.startswith("/_next"):
            fe_called_paths.add(p.split("?")[0])

    return {
        "router_mounts": dict(router_mounts),
        "endpoints": endpoints,
        "fe_api_ts_paths": sorted(fe_called_paths),
    }


def main():
    fe = analyze_frontend()
    api = analyze_api_endpoints()
    (EVIDENCE_DIR / "frontend_analysis.json").write_text(json.dumps(fe, indent=2), encoding="utf-8")
    (OUT_DIR / "API_USAGE_MATRIX.json").write_text(json.dumps(api, indent=2), encoding="utf-8")

    print("=== FRONTEND SUMMARY ===")
    print("Total pages:", len(fe["pages"]))
    shadowed = [p for p in fe["pages"] if p["shadowed_by_redirect_to"]]
    print("Pages shadowed by next.config.ts redirects:", len(shadowed))
    for p in shadowed:
        print(f"  SHADOWED: {p['route']} -> {p['shadowed_by_redirect_to']} ({p['file']}, {p['lines']} lines)")
    print("\nNon-shadowed pages NOT in Sidebar:")
    for p in fe["pages"]:
        if not p["shadowed_by_redirect_to"] and not p["in_sidebar"]:
            print(f"  {p['route']} ({p['file']}, {p['lines']} lines) src_refs={len(p['src_string_refs'])}")

    print("\nModules with 0 active importers:")
    for m in fe["modules"]:
        if not m["active_importers"]:
            print(f"  ORPHAN/SHADOWED-ONLY: {m['file']} ({m['lines']} lines) total_importers={m['imported_by']} test_refs={m['test_refs']}")

    print("\nPublic assets with 0 refs:")
    for a in fe["public_assets"]:
        if not a["refs"]:
            print(f"  UNUSED ASSET: {a['file']} ({a['size_bytes']} bytes)")

    print("\n=== API SUMMARY ===")
    print("Total endpoint handlers:", len(api["endpoints"]))
    no_fe = [e for e in api["endpoints"] if not e["fe_refs"]]
    print("Endpoints without frontend refs:", len(no_fe))
    for e in no_fe:
        print(f"  {e['method']:6s} {e['full_paths'][0]:45s} ({e['file']}:{e['lineno']}) tests={len(e['test_refs'])} scripts={len(e['script_refs'])}")


if __name__ == "__main__":
    main()
