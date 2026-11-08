import pytest
import os
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.services.ingestion_service import IngestionService

ZIP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fixtures", "Incident json.zip"))


@pytest.mark.asyncio
async def test_prompt_template_generation_and_versioning(
    client: AsyncClient,
    db_session: AsyncSession,
    analyst_token: str,
    admin_token: str,
    viewer_token: str,
):
    # Ingest fixture data so rules exist
    with open(ZIP_PATH, "rb") as f:
        file_bytes = f.read()
    ingestor = IngestionService(db_session)
    await ingestor.ingest_zip(file_bytes=file_bytes, filename="Incident json.zip", username="test_admin")

    # Get rule
    rule_res = await db_session.execute(select(Rule))
    rule = rule_res.scalars().first()
    assert rule is not None

    headers_analyst = {"Authorization": f"Bearer {analyst_token}"}
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_viewer = {"Authorization": f"Bearer {viewer_token}"}

    # 1. Fetch or initialize prompt for rule
    get_res = await client.get(f"/api/prompts/rule/{rule.id}", headers=headers_analyst)
    assert get_res.status_code == 200
    prompt_data = get_res.json()
    assert prompt_data["rule_id"] == rule.id
    assert len(prompt_data["versions"]) >= 1

    initial_ver = prompt_data["versions"][0]
    # Check that initial draft is explicitly labeled template draft
    assert initial_ver["is_template_draft"] is True
    assert "TEMPLATE-GENERATED DRAFT" in initial_ver["change_summary"]
    assert initial_ver["status"] == "DRAFT"
    initial_version_id = initial_ver["id"]

    # 2. Approve template draft (Admin required)
    # Viewer should be forbidden (403)
    forbidden_appr = await client.post(
        f"/api/prompts/rule/{rule.id}/approve/{initial_version_id}",
        headers=headers_viewer,
        json={"change_summary": "Should fail"}
    )
    assert forbidden_appr.status_code == 403

    # Admin approves
    appr_res = await client.post(
        f"/api/prompts/rule/{rule.id}/approve/{initial_version_id}",
        headers=headers_admin,
        json={"change_summary": "Approved baseline template by SOC Lead"}
    )
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "APPROVED"

    # 3. Create a manual draft version (v2)
    draft_res = await client.post(
        f"/api/prompts/rule/{rule.id}/draft",
        headers=headers_analyst,
        json={
            "common_prompt": "Standard SOC baseline v2",
            "rule_specific_prompt": "Custom tailored directive for CrowdStrike Activity",
            "detection_conditions": "Execution of unsigned binaries in temp folders",
            "required_evidence": "Command line, parent PID, file hash",
            "tp_indicators": "Obfuscated PowerShell, base64 payloads",
            "fp_indicators": "Tanium IT management agents",
            "missing_info_criteria": "Missing command line",
            "escalation_conditions": "Ransomware precursor commands",
            "analyst_questions": ["Is this Tanium?", "Does hash match known malware?"],
            "change_summary": "Manual tuning for reduced false positives",
        }
    )
    assert draft_res.status_code == 200
    v2_data = draft_res.json()
    assert v2_data["version_number"] == 2
    assert v2_data["status"] == "DRAFT"
    assert v2_data["is_template_draft"] is False
    v2_id = v2_data["id"]

    # 4. Admin approves v2
    appr_v2 = await client.post(
        f"/api/prompts/rule/{rule.id}/approve/{v2_id}",
        headers=headers_admin,
        json={"change_summary": "Approved v2"}
    )
    assert appr_v2.status_code == 200
    assert appr_v2.json()["status"] == "APPROVED"

    # 5. Rollback to v1
    rollback_res = await client.post(
        f"/api/prompts/rule/{rule.id}/rollback/{initial_version_id}",
        headers=headers_admin,
    )
    assert rollback_res.status_code == 200
    v3_rollback = rollback_res.json()
    assert v3_rollback["version_number"] == 3
    assert v3_rollback["status"] == "APPROVED"
    assert "Rollback to Version 1" in v3_rollback["change_summary"]

    # 6. Export all rules & prompts (JSON & Markdown)
    export_json = await client.get("/api/prompts/export", headers=headers_analyst)
    assert export_json.status_code == 200
    assert "application/json" in export_json.headers["content-type"]
    assert "attachment" in export_json.headers["content-disposition"]
    data = export_json.json()
    assert data["schema_version"] == "1.0"
    assert len(data["rules"]) >= 1
    found_rule = next((r for r in data["rules"] if r["rule_id"] == rule.id), None)
    assert found_rule is not None
    assert found_rule["active_prompt_configuration"] is not None
    assert found_rule["active_prompt_configuration"]["version_number"] == 3

    export_md = await client.get("/api/prompts/export?format=markdown", headers=headers_analyst)
    assert export_md.status_code == 200
    assert "text/markdown" in export_md.headers["content-type"]
    assert rule.name in export_md.text

    # 7. Export single rule prompt (JSON & Markdown)
    single_json = await client.get(f"/api/prompts/rule/{rule.id}/export", headers=headers_analyst)
    assert single_json.status_code == 200
    assert single_json.json()["rule"]["rule_id"] == rule.id

    single_md = await client.get(f"/api/prompts/rule/{rule.id}/export?format=markdown", headers=headers_analyst)
    assert single_md.status_code == 200
    assert rule.name in single_md.text
