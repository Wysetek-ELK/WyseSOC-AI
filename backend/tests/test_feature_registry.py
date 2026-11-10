import json
from pathlib import Path
import importlib.util


def test_centralized_feature_registry_and_markdown_sync():
    repo_root = Path(__file__).resolve().parent.parent.parent
    validator_path = repo_root / "scripts" / "validate_feature_registry.py"
    registry_path = repo_root / "docs" / "feature_registry.json"
    status_md_path = repo_root / "docs" / "FEATURE_IMPLEMENTATION_STATUS.md"

    assert validator_path.exists(), "Registry validator script missing"
    assert registry_path.exists(), "docs/feature_registry.json missing"
    assert status_md_path.exists(), "docs/FEATURE_IMPLEMENTATION_STATUS.md missing"

    spec = importlib.util.spec_from_file_location("validate_feature_registry", validator_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)

    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    summary = mod.validate_registry(registry, repo_root)
    expected_md = mod.render_markdown(registry, summary)
    actual_md = status_md_path.read_text(encoding="utf-8")
    assert actual_md == expected_md, "FEATURE_IMPLEMENTATION_STATUS.md drifted from feature_registry.json"

