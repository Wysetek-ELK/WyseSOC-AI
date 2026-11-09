from typing import Dict, Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.api.deps import require_role, get_current_user
from app.config import settings
from app.schemas.fortisiem import (
    FortiSIEMPullRequest,
    FortiSIEMPullResponse,
    FortiSIEMBatchPullRequest,
    FortiSIEMBatchPullResponse,
    FortiSIEMSchedulerStatusResponse,
    FortiSIEMSchedulerControlRequest,
    FortiSIEMBatchVerdictRequest,
    FortiSIEMBatchVerdictResponse,
    FortiSIEMStatusResponse,
    FortiSIEMConfigResponse,
    FortiSIEMConfigUpdate,
    FortiSIEMTestConnectionRequest,
    FortiSIEMTestConnectionResponse,
    FortiSIEMRuleSyncResponse,
    FortiSIEMRulePullRequest,
    FortiSIEMRulePullResponse,
    FortiSIEMSyncResolutionsResponse,
    FortiSIEMSingleSyncResponse,
)
from app.services.fortisiem_service import FortiSIEMService
from app.services.fortisiem_scheduler import fortisiem_scheduler
from app.services.ai_verdict_service import AIVerdictService

router = APIRouter(prefix="/fortisiem", tags=["FortiSIEM Live Connector"])


@router.get("/status", response_model=FortiSIEMStatusResponse)
async def get_fortisiem_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Checks FortiSIEM connection status and available fixture IDs for testing.
    """
    service = FortiSIEMService(db)
    is_configured = bool(settings.FORTISIEM_HOST and settings.FORTISIEM_HOST.strip())
    mode = "LIVE" if is_configured else "FIXTURE_FALLBACK"
    sample_ids = service.get_available_fixture_ids()
    live_ids = await FortiSIEMService.get_recent_live_incident_ids(limit=8) if is_configured else []

    return FortiSIEMStatusResponse(
        is_configured=is_configured,
        host=settings.FORTISIEM_HOST if is_configured else "Not Configured (Using Fixture Mode)",
        username=settings.FORTISIEM_USERNAME if is_configured else "",
        verify_ssl=settings.FORTISIEM_VERIFY_SSL,
        mode=mode,
        sample_incident_ids=sample_ids,
        live_incident_ids=live_ids,
    )


@router.get("/config", response_model=FortiSIEMConfigResponse)
async def get_fortisiem_config(
    current_user: User = Depends(require_role(["Administrator"])),
):
    """
    Returns current FortiSIEM supervisor configuration with passwords masked.
    Restricted to Administrator role.
    """
    return FortiSIEMService.get_config()


@router.post("/config", response_model=FortiSIEMConfigResponse)
async def update_fortisiem_config(
    config: FortiSIEMConfigUpdate,
    current_user: User = Depends(require_role(["Administrator"])),
):
    """
    Updates FortiSIEM supervisor IP/URL, credentials, and settings dynamically and persists to .env.
    Restricted to Administrator role.
    """
    updated = FortiSIEMService.update_config(
        host=config.host,
        username=config.username,
        password=config.password,
        verify_ssl=config.verify_ssl,
        timeout=config.timeout,
        mock_fallback=config.mock_fallback,
        auto_poll_enabled=config.auto_poll_enabled,
        poll_interval_seconds=config.poll_interval_seconds,
        auto_ai_verdict=config.auto_ai_verdict,
    )
    return updated


@router.post("/test-connection", response_model=FortiSIEMTestConnectionResponse)
async def test_fortisiem_connection(
    req: FortiSIEMTestConnectionRequest,
    current_user: User = Depends(require_role(["Administrator"])),
):
    """
    Probes the specified FortiSIEM supervisor endpoint to verify connectivity and credentials.
    Restricted to Administrator role.
    """
    res = await FortiSIEMService.test_siem_connection(
        host=req.host,
        username=req.username,
        password=req.password,
        verify_ssl=req.verify_ssl,
        timeout=req.timeout,
    )
    return FortiSIEMTestConnectionResponse(**res)


@router.post("/fetch", response_model=FortiSIEMPullResponse)
async def fetch_incident(
    req: FortiSIEMPullRequest,
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Pulls an incident from FortiSIEM by Incident ID, ingests telemetry and raw events,
    safely isolates historical ground truth, and prepares it for AI investigation.
    """
    service = FortiSIEMService(db)
    try:
        result = await service.pull_and_ingest(
            incident_id=req.incident_id,
            force_refresh=req.force_refresh,
            username=current_user.username,
        )
        return FortiSIEMPullResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error while pulling incident from FortiSIEM: {str(exc)}"
        )


@router.post("/pull-all", response_model=FortiSIEMBatchPullResponse)
async def pull_all_incidents(
    req: FortiSIEMBatchPullRequest = FortiSIEMBatchPullRequest(),
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Pulls all incidents from FortiSIEM in batch without requiring any Incident IDs.
    Queries the live FortiSIEM REST API by time range, or falls back to offline fixture archive.
    Automatically generates AI Verdicts for newly ingested alerts using the LLM provider.
    """
    service = FortiSIEMService(db)
    try:
        result = await service.pull_all_incidents(
            time_from=req.time_from,
            time_to=req.time_to,
            max_count=req.max_count,
            auto_triage_llm=req.auto_triage_llm,
            force_refresh=req.force_refresh,
            username=current_user.username,
        )
        return FortiSIEMBatchPullResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during batch incident pull: {str(exc)}"
        )


@router.get("/scheduler/status", response_model=FortiSIEMSchedulerStatusResponse)
async def get_scheduler_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns real-time status, checkpoint watermark, and metrics for continuous 3-minute poller.
    Includes pending AI verdict count and LLM online status.
    """
    ai_service = AIVerdictService(db)
    is_online = await ai_service.is_local_llm_available()
    pending_count = await ai_service.get_pending_incident_count()

    raw_status = fortisiem_scheduler.get_status()
    raw_status["is_llm_online"] = is_online
    raw_status["pending_ai_verdicts_count"] = pending_count
    return FortiSIEMSchedulerStatusResponse(**raw_status)


@router.post("/process-pending-verdicts", response_model=Dict[str, Any])
async def process_pending_verdicts(
    max_count: int = 100,
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates pending incidents lacking AI verdicts one by one once Local LLM is online.
    """
    service = FortiSIEMService(db)
    return await service.process_pending_incidents(max_count=max_count, username=current_user.username)


@router.post("/scheduler/start", response_model=FortiSIEMSchedulerStatusResponse)
async def start_scheduler(
    req: FortiSIEMSchedulerControlRequest = FortiSIEMSchedulerControlRequest(),
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
):
    """
    Starts continuous FortiSIEM incident polling (default: every 180 seconds / 3 minutes).
    Automatically runs AI verdict evaluations on all newly ingested alerts.
    """
    settings.FORTISIEM_AUTO_POLL_ENABLED = True
    status = fortisiem_scheduler.start(
        interval_seconds=req.interval_seconds or 180,
        auto_ai_verdict=req.auto_ai_verdict if req.auto_ai_verdict is not None else True,
    )
    return FortiSIEMSchedulerStatusResponse(**status)


@router.post("/scheduler/stop", response_model=FortiSIEMSchedulerStatusResponse)
async def stop_scheduler(
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
):
    """
    Halts the continuous background poller.
    """
    settings.FORTISIEM_AUTO_POLL_ENABLED = False
    status = fortisiem_scheduler.stop()
    return FortiSIEMSchedulerStatusResponse(**status)


@router.post("/scheduler/trigger", response_model=Dict[str, Any])
async def trigger_scheduler_now(
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
):
    """
    Triggers an immediate sync cycle without waiting for the 3-minute timer.
    """
    result = await fortisiem_scheduler.trigger_immediate_sync()
    return result


@router.post("/batch-ai-verdict", response_model=FortiSIEMBatchVerdictResponse)
async def evaluate_batch_ai_verdicts(
    req: FortiSIEMBatchVerdictRequest = FortiSIEMBatchVerdictRequest(),
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Evaluates pending or selected incidents in batch with the LLM AI Verdict engine.
    """
    service = AIVerdictService(db)
    result = await service.evaluate_batch(
        incident_ids=req.incident_ids,
        only_pending=True if not req.incident_ids else False,
        max_batch=req.max_batch,
        username=current_user.username,
    )
    return FortiSIEMBatchVerdictResponse(**result)


@router.post("/sync-rules", response_model=FortiSIEMRuleSyncResponse)
async def sync_fortisiem_rules(
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronizes all detection rules from FortiSIEM Supervisor into the local database.
    Stores rules locally with prompt drafts so investigations can evaluate them instantly.
    """
    service = FortiSIEMService(db)
    result = await service.sync_all_rules_from_siem()
    return FortiSIEMRuleSyncResponse(**result)


@router.post("/pull-rule", response_model=FortiSIEMRulePullResponse)
async def pull_fortisiem_rule(
    req: FortiSIEMRulePullRequest,
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Pulls a specific detection rule from FortiSIEM Supervisor REST APIs,
    parses its full detection pattern, registers it into the local database,
    and synthesizes an approved RulePrompt template.
    """
    service = FortiSIEMService(db)
    result = await service.pull_rule_and_register(
        rule_identifier=req.rule_id,
        force_refresh=req.force_refresh,
    )
    return FortiSIEMRulePullResponse(**result)


@router.post("/sync-resolutions", response_model=FortiSIEMSyncResolutionsResponse)
async def sync_fortisiem_resolutions(
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Pulls and synchronizes historical incident resolutions, cleared reasons,
    cleared users, and closure status from FortiSIEM across all database incidents.
    """
    service = FortiSIEMService(db)
    result = await service.sync_all_resolutions()
    return FortiSIEMSyncResolutionsResponse(**result)


@router.post("/incident/{incident_id}/sync-resolution", response_model=FortiSIEMSingleSyncResponse)
async def sync_single_incident_resolution(
    incident_id: str,
    current_user: User = Depends(require_role(["Administrator", "SOC Analyst"])),
    db: AsyncSession = Depends(get_db),
):
    """
    Synchronizes the latest resolution, clearing notes, analyst username,
    and closure status for a specific incident from FortiSIEM into the local database.
    """
    service = FortiSIEMService(db)
    result = await service.sync_single_incident_resolution(incident_id)
    return FortiSIEMSingleSyncResponse(**result)
