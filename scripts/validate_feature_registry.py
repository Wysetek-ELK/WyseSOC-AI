#!/usr/bin/env python3
"""
Deterministic validator and Markdown generator/reconciler for the AI Verdict
Centralized Feature Implementation Registry (docs/feature_registry.json ->
docs/FEATURE_IMPLEMENTATION_STATUS.md).

Usage:
  python scripts/validate_feature_registry.py           # Validate registry + Markdown parity
  python scripts/validate_feature_registry.py --sync    # Validate registry + regenerate Markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "feature_registry.json"
STATUS_MD_PATH = REPO_ROOT / "docs" / "FEATURE_IMPLEMENTATION_STATUS.md"

VALID_STATUSES = {
    "IMPLEMENTED_VERIFIED",
    "IMPLEMENTED_UNVERIFIED",
    "PARTIAL",
    "MISSING",
    "DEFECTIVE",
    "NOT_APPLICABLE",
}

VALID_IMPL_STATES = {"SATISFIED", "PARTIAL", "UNSATISFIED", "NOT_APPLICABLE"}
VALID_VERIF_STATES = {"VERIFIED", "UNVERIFIED", "FAILED", "NOT_TESTED", "BLOCKED", "NOT_APPLICABLE"}

REQUIRED_MODULES = [
    "Agent Intelligence Studio 2.0",
    "Rule Management & Policy Generation",
    "Policy Quality Gates & Simulation",
    "Verdict Triage Agent",
    "Evidence Normalization & Contracts",
    "Independent Verdict Validation",
    "Verdict Trustworthiness & Confidence",
    "Historical Ground Truth & Empirical Accuracy",
    "FortiSIEM Integration & Incident Ingestion",
    "Local LLM / Server 2 Integration",
    "Background Workers & Reconciliation",
    "Analyst Investigation & Review",
    "Frontend UI & Navigation",
    "Backend APIs & Services",
    "Database Models & Migrations",
    "Authentication, Authorization & Audit Logs",
    "Monitoring & Operational Reliability",
    "Automated Testing & End-to-End Validation",
    "Documentation & Governance",
]


def _compute_feature_metrics(feature: Dict[str, Any]) -> Tuple[int, int, float, int, int, float]:
    """Compute (satisfied_impl, applicable_impl, impl_pct, verified_acc, applicable_acc, verif_pct)."""
    criteria = feature.get("acceptance_criteria", [])
    if not criteria:
        raise ValueError(f"Feature '{feature.get('feature_id')}' has empty acceptance_criteria.")

    satisfied_impl = 0
    applicable_impl = 0
    verified_acc = 0
    applicable_acc = 0

    for c in criteria:
        cid = c.get("id", "unknown")
        impl_state = c.get("implementation_state")
        verif_state = c.get("verification_state")
        if impl_state not in VALID_IMPL_STATES:
            raise ValueError(f"Feature {feature['feature_id']} criterion {cid}: invalid implementation_state '{impl_state}'")
        if verif_state not in VALID_VERIF_STATES:
            raise ValueError(f"Feature {feature['feature_id']} criterion {cid}: invalid verification_state '{verif_state}'")

        if impl_state == "NOT_APPLICABLE" or verif_state == "NOT_APPLICABLE":
            if not str(c.get("not_applicable_justification", "")).strip():
                raise ValueError(
                    f"Feature {feature['feature_id']} criterion {cid}: NOT_APPLICABLE requires non-empty not_applicable_justification."
                )

        if impl_state != "NOT_APPLICABLE":
            applicable_impl += 1
            if impl_state == "SATISFIED":
                satisfied_impl += 1

        if verif_state != "NOT_APPLICABLE":
            applicable_acc += 1
            if verif_state == "VERIFIED":
                verified_acc += 1

    impl_pct = round((satisfied_impl / applicable_impl) * 100.0, 1) if applicable_impl > 0 else 100.0
    verif_pct = round((verified_acc / applicable_acc) * 100.0, 1) if applicable_acc > 0 else 0.0
    return satisfied_impl, applicable_impl, impl_pct, verified_acc, applicable_acc, verif_pct


def validate_registry(
    registry: Dict[str, Any],
    repo_root: Path = REPO_ROOT,
    allow_missing_generated_md: bool = False,
    update_summary: bool = False,
) -> Dict[str, Any]:
    """Validates registry schema, path integrity, required modules, and recomputes all rollups."""
    features: List[Dict[str, Any]] = registry.get("features", [])
    if not features:
        raise ValueError("Registry contains no features.")

    seen_ids = set()
    present_modules = set()
    module_totals: Dict[str, Dict[str, Any]] = {}

    overall_sat_impl = 0
    overall_app_impl = 0
    overall_ver_acc = 0
    overall_app_acc = 0

    for feat in features:
        fid = feat.get("feature_id", "")
        if not fid:
            raise ValueError("Feature missing 'feature_id'")
        if fid in seen_ids:
            raise ValueError(f"Duplicate feature_id: '{fid}'")
        seen_ids.add(fid)

        status = feat.get("implementation_status")
        if status not in VALID_STATUSES:
            raise ValueError(f"Feature {fid} has invalid implementation_status '{status}'")

        mod = feat.get("module", "")
        if not mod:
            raise ValueError(f"Feature {fid} missing 'module'")
        present_modules.add(mod)

        # Verify all referenced workspace paths exist
        for field_name in ("frontend_files", "backend_files", "test_files", "evidence_files"):
            for rel_path in feat.get(field_name, []):
                clean_rel = str(rel_path).split("#")[0].strip()
                if allow_missing_generated_md and clean_rel == "docs/FEATURE_IMPLEMENTATION_STATUS.md":
                    continue
                if clean_rel and not (repo_root / clean_rel).exists():
                    raise ValueError(f"Feature {fid} references nonexistent path in {field_name}: '{clean_rel}'")

        sat_i, app_i, calc_i_pct, ver_a, app_a, calc_v_pct = _compute_feature_metrics(feat)
        reg_i_pct = float(feat.get("completion_pct", -1))
        reg_v_pct = float(feat.get("verification_pct", -1))
        if abs(reg_i_pct - calc_i_pct) > 0.11:
            raise ValueError(f"Feature {fid} completion_pct mismatch: JSON={reg_i_pct}, computed={calc_i_pct}")
        if abs(reg_v_pct - calc_v_pct) > 0.11:
            raise ValueError(f"Feature {fid} verification_pct mismatch: JSON={reg_v_pct}, computed={calc_v_pct}")

        # Prevent claiming IMPLEMENTED_VERIFIED when verification_pct < 100
        if status == "IMPLEMENTED_VERIFIED" and calc_v_pct < 100.0:
            raise ValueError(f"Feature {fid} marked IMPLEMENTED_VERIFIED but verification_pct is {calc_v_pct}% (< 100%).")

        overall_sat_impl += sat_i
        overall_app_impl += app_i
        overall_ver_acc += ver_a
        overall_app_acc += app_a

        m = module_totals.setdefault(mod, {
            "module": mod,
            "feature_count": 0,
            "satisfied_impl": 0,
            "applicable_impl": 0,
            "verified_acc": 0,
            "applicable_acc": 0,
        })
        m["feature_count"] += 1
        m["satisfied_impl"] += sat_i
        m["applicable_impl"] += app_i
        m["verified_acc"] += ver_a
        m["applicable_acc"] += app_a

    missing_modules = [m for m in REQUIRED_MODULES if m not in present_modules]
    if missing_modules:
        raise ValueError(f"Missing required modules in registry: {missing_modules}")

    for m in module_totals.values():
        m["completion_pct"] = round((m["satisfied_impl"] / m["applicable_impl"]) * 100.0, 1) if m["applicable_impl"] else 100.0
        m["verification_pct"] = round((m["verified_acc"] / m["applicable_acc"]) * 100.0, 1) if m["applicable_acc"] else 0.0

    summary = {
        "total_features": len(features),
        "total_modules": len(module_totals),
        "satisfied_impl_criteria": overall_sat_impl,
        "applicable_impl_criteria": overall_app_impl,
        "overall_completion_pct": round((overall_sat_impl / overall_app_impl) * 100.0, 1) if overall_app_impl else 0.0,
        "verified_acc_criteria": overall_ver_acc,
        "applicable_acc_criteria": overall_app_acc,
        "overall_verification_pct": round((overall_ver_acc / overall_app_acc) * 100.0, 1) if overall_app_acc else 0.0,
        "modules": list(module_totals.values()),
    }

    reg_summary = registry.get("summary", {})
    if update_summary:
        registry["summary"] = {
            "total_features": summary["total_features"],
            "total_modules": summary["total_modules"],
            "satisfied_impl_criteria": summary["satisfied_impl_criteria"],
            "applicable_impl_criteria": summary["applicable_impl_criteria"],
            "overall_completion_pct": summary["overall_completion_pct"],
            "verified_acc_criteria": summary["verified_acc_criteria"],
            "applicable_acc_criteria": summary["applicable_acc_criteria"],
            "overall_verification_pct": summary["overall_verification_pct"],
        }
    elif reg_summary:
        if int(reg_summary.get("total_features", -1)) != summary["total_features"]:
            raise ValueError(
                f"Registry total_features mismatch: JSON={reg_summary.get('total_features')}, computed={summary['total_features']}"
            )
        if abs(float(reg_summary.get("overall_completion_pct", -1)) - summary["overall_completion_pct"]) > 0.11:
            raise ValueError(
                f"Registry overall_completion_pct mismatch: JSON={reg_summary.get('overall_completion_pct')}, computed={summary['overall_completion_pct']}"
            )
        if abs(float(reg_summary.get("overall_verification_pct", -1)) - summary["overall_verification_pct"]) > 0.11:
            raise ValueError(
                f"Registry overall_verification_pct mismatch: JSON={reg_summary.get('overall_verification_pct')}, computed={summary['overall_verification_pct']}"
            )

    return summary


def render_markdown(registry: Dict[str, Any], summary: Dict[str, Any]) -> str:
    """Renders docs/FEATURE_IMPLEMENTATION_STATUS.md deterministically from docs/feature_registry.json."""
    meta = registry.get("metadata", {})
    lines = [
        "# AI Verdict — Centralized Feature Implementation & Verification Registry",
        "",
        f"- **Generated / Reconciled From:** [`docs/feature_registry.json`](file:///{REPO_ROOT.as_posix()}/docs/feature_registry.json)",
        f"- **Last Updated:** {meta.get('updated_at', 'N/A')}",
        f"- **Repository Commit:** `{meta.get('git_commit', 'N/A')}`",
        f"- **Architecture Version:** `{meta.get('architecture_version', 'N/A')}`",
        "- **Registry Consistency Validator:** `python scripts/validate_feature_registry.py`",
        "",
        "> [!IMPORTANT]",
        "> **Strict Accounting Policy:** Implementation Completion % and Verification % are computed strictly from explicit per-feature acceptance criteria in `docs/feature_registry.json`. `NOT_APPLICABLE` criteria are excluded from denominators with written justification. A 100% implementation score does **not** imply live Server 2 GPU / live FortiSIEM hardware verification or proven empirical accuracy.",
        "",
        "---",
        "",
        "## 1. Overall Project Summary (Criteria-Derived)",
        "",
        "| Metric | Value | Calculation Basis |",
        "|---|---|---|",
        f"| **Registered Modules** | {summary['total_modules']} | Covers all 19 core architectural domains |",
        f"| **Registered Features** | {summary['total_features']} | Unique feature IDs with measurable criteria |",
        f"| **Overall Implementation Completion** | **{summary['overall_completion_pct']}%** | {summary['satisfied_impl_criteria']} / {summary['applicable_impl_criteria']} applicable implementation criteria satisfied |",
        f"| **Overall Independent Verification** | **{summary['overall_verification_pct']}%** | {summary['verified_acc_criteria']} / {summary['applicable_acc_criteria']} applicable acceptance criteria verified |",
        "",
        "---",
        "",
        "## 2. Consolidated Module-Level Summary",
        "",
        "| Module | Features | Impl Criteria (Sat / App) | Implementation % | Verif Criteria (Ver / App) | Verification % |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for m in summary["modules"]:
        lines.append(
            f"| {m['module']} | {m['feature_count']} | {m['satisfied_impl']}/{m['applicable_impl']} | **{m['completion_pct']}%** | {m['verified_acc']}/{m['applicable_acc']} | **{m['verification_pct']}%** |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 3. Feature-Level Status Registry",
        "",
        "| Feature ID | Module | Feature | Implementation Status | Completion % | Verification % | Frontend | Backend | Tests | Evidence | Remaining Gap |",
        "|---|---|---|---|---:|---:|---|---|---|---|---|",
    ])

    for feat in registry["features"]:
        fe = ", ".join(f"`{p}`" for p in feat.get("frontend_files", [])) or "N/A"
        be = ", ".join(f"`{p}`" for p in feat.get("backend_files", [])) or "N/A"
        ts = ", ".join(f"`{p}`" for p in feat.get("test_files", [])) or "None"
        ev = "; ".join(feat.get("evidence_notes", [])) or ", ".join(f"`{p}`" for p in feat.get("evidence_files", []))
        gap = feat.get("remaining_gap", "None")
        lines.append(
            f"| `{feat['feature_id']}` | {feat['module']} | {feat['feature_name']} | **{feat['implementation_status']}** | {feat['completion_pct']}% | {feat['verification_pct']}% | {fe} | {be} | {ts} | {ev} | {gap} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Maintenance Workflow (Phase 7)",
        "",
        "Whenever a feature is added, modified, fixed, deprecated, or removed:",
        "1. Update its entry, criteria states, file paths, and percentages inside [`docs/feature_registry.json`](file:///{}/docs/feature_registry.json).".format(REPO_ROOT.as_posix()),
        "2. Run `python scripts/validate_feature_registry.py --sync` to recalculate totals and regenerate this file.",
        "3. Run `python scripts/validate_feature_registry.py` and `pytest tests/test_feature_registry.py` before completion.",
        "",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AI Verdict feature registry and Markdown sync.")
    parser.add_argument("--sync", action="store_true", help="Regenerate docs/FEATURE_IMPLEMENTATION_STATUS.md from JSON.")
    args = parser.parse_args()

    if not REGISTRY_PATH.exists():
        print(f"ERROR: Missing registry file {REGISTRY_PATH}", file=sys.stderr)
        return 1

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    summary = validate_registry(
        registry,
        REPO_ROOT,
        allow_missing_generated_md=args.sync,
        update_summary=args.sync,
    )
    expected_md = render_markdown(registry, summary)

    if args.sync:
        REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
        STATUS_MD_PATH.write_text(expected_md, encoding="utf-8")
        print(f"SYNCHRONIZED: {STATUS_MD_PATH} ({summary['total_features']} features, Impl={summary['overall_completion_pct']}%, Verif={summary['overall_verification_pct']}%)")
        return 0

    if not STATUS_MD_PATH.exists():
        print(f"ERROR: Missing Markdown report {STATUS_MD_PATH}. Run with --sync.", file=sys.stderr)
        return 1

    actual_md = STATUS_MD_PATH.read_text(encoding="utf-8")
    if actual_md != expected_md:
        print("ERROR: docs/FEATURE_IMPLEMENTATION_STATUS.md is out of sync with docs/feature_registry.json. Run with --sync.", file=sys.stderr)
        return 1

    print(
        f"OK: Registry verified ({summary['total_features']} features, {summary['total_modules']} modules, "
        f"Impl={summary['overall_completion_pct']}%, Verif={summary['overall_verification_pct']}%)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
