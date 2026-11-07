import os
import json
import zipfile
import re
from typing import Dict, Any, Tuple, List, Optional
import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.config import settings, BASE_DIR
from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.services.ingestion_service import IngestionService
from app.services.investigation_service import InvestigationService


class FortiSIEMService:
    """
    Client and ingestion coordinator for FortiSIEM REST API.
    Enables on-demand pulling of incidents by Incident ID.
    Supports live FortiSIEM API and fixture fallback for offline/development environments.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.fixtures_zip_path = os.path.join(os.path.dirname(BASE_DIR), "fixtures", "Incident json.zip")

    def get_available_fixture_ids(self) -> List[str]:
        """Returns incident IDs discovered in the local fixtures archive."""
        if not os.path.exists(self.fixtures_zip_path):
            return []
        ids = []
        try:
            with zipfile.ZipFile(self.fixtures_zip_path, "r") as z:
                for name in z.namelist():
                    match = re.search(r"incid\w*id_(\d+)\.json", name, re.IGNORECASE)
                    if match:
                        ids.append(match.group(1))
        except Exception:
            pass
        return sorted(list(set(ids)))

    async def fetch_incident_from_siem(self, incident_id: str) -> Tuple[Dict[str, Any], str]:
        """
        Fetches incident JSON from FortiSIEM REST API.
        Falls back to local fixture archive if SIEM host is unconfigured or in offline fallback mode.
        """
        clean_id = str(incident_id).strip()
        if not clean_id:
            raise HTTPException(status_code=400, detail="Incident ID cannot be empty.")

        # 1. Try Live FortiSIEM REST API if host is configured
        if settings.FORTISIEM_HOST and settings.FORTISIEM_HOST.strip():
            base_url = settings.FORTISIEM_HOST.strip().rstrip("/")
            endpoint = f"{base_url}/phoenix/rest/incident/incidentDetail"
            params = {"incidentId": clean_id}

            auth = None
            if settings.FORTISIEM_USERNAME and settings.FORTISIEM_PASSWORD:
                auth = (settings.FORTISIEM_USERNAME, settings.FORTISIEM_PASSWORD)

            try:
                async with httpx.AsyncClient(
                    verify=settings.FORTISIEM_VERIFY_SSL,
                    timeout=settings.FORTISIEM_TIMEOUT,
                ) as client:
                    res = await client.get(endpoint, params=params, auth=auth, headers={"Accept": "application/json"})
                    
                    if res.status_code == 200:
                        try:
                            data = res.json()
                            return data, "LIVE"
                        except json.JSONDecodeError:
                            # Parse potential XML response or non-standard payload
                            raise HTTPException(
                                status_code=502,
                                detail=f"FortiSIEM returned non-JSON response: {res.text[:200]}"
                            )
                    elif res.status_code == 404:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Incident '{clean_id}' was not found in FortiSIEM."
                        )
                    elif res.status_code in (401, 403):
                        raise HTTPException(
                            status_code=502,
                            detail="FortiSIEM authentication failed. Verify FORTISIEM_USERNAME and FORTISIEM_PASSWORD."
                        )
                    else:
                        raise HTTPException(
                            status_code=502,
                            detail=f"FortiSIEM API returned HTTP {res.status_code}: {res.text[:200]}"
                        )
            except httpx.RequestError as exc:
                if not settings.FORTISIEM_MOCK_FALLBACK:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to connect to FortiSIEM host ({base_url}): {str(exc)}"
                    )
                # Fall through to fixture fallback if enabled

        # 2. Fixture fallback (Development, offline, or demo mode)
        if settings.FORTISIEM_MOCK_FALLBACK and os.path.exists(self.fixtures_zip_path):
            with zipfile.ZipFile(self.fixtures_zip_path, "r") as z:
                for name in z.namelist():
                    match = re.search(r"incid\w*id_(\d+)\.json", name, re.IGNORECASE)
                    if match and match.group(1) == clean_id:
                        raw_bytes = z.read(name)
                        data = json.loads(raw_bytes.decode("utf-8"))
                        return data, "FIXTURE_FALLBACK"

        # Not found in live or fixture fallback
        available = self.get_available_fixture_ids()
        hint = f" Available sample IDs: {', '.join(available[:8])}..." if available else ""
        msg = (
            f"Incident '{clean_id}' not found. "
            f"FortiSIEM host is {'not configured' if not settings.FORTISIEM_HOST else 'unreachable'}."
            f"{hint}"
        )
        raise HTTPException(status_code=404, detail=msg)

    async def pull_and_ingest(
        self,
        incident_id: str,
        force_refresh: bool = False,
        username: str = "system",
    ) -> Dict[str, Any]:
        """
        Pulls incident telemetry from FortiSIEM, parses rules & raw events,
        isolates ground-truth, and registers in the analyst queue.
        """
        clean_id = str(incident_id).strip()

        # Check existing record
        existing_stmt = select(Incident).where(
            Incident.incident_id == clean_id
        ).options(selectinload(Incident.events))
        existing_res = await self.db.execute(existing_stmt)
        existing_inc = existing_res.scalar_one_or_none()

        if existing_inc and not force_refresh:
            return {
                "success": True,
                "incident_id": existing_inc.incident_id,
                "db_id": existing_inc.id,
                "title": existing_inc.title,
                "event_type": existing_inc.event_type,
                "severity": existing_inc.severity,
                "status_name": existing_inc.status_name,
                "event_count": len(existing_inc.events),
                "source": "DATABASE_CACHE",
                "message": f"Incident '{clean_id}' is already present in the local database.",
            }

        # Fetch telemetry
        raw_data, source_type = await self.fetch_incident_from_siem(clean_id)

        # Handle force refresh deletion if present
        if existing_inc and force_refresh:
            # Delete old ground truth and investigation
            await self.db.execute(delete(HistoricalGroundTruth).where(HistoricalGroundTruth.incident_id == existing_inc.id))
            await self.db.execute(delete(Investigation).where(Investigation.incident_id == existing_inc.id))
            await self.db.execute(delete(IncidentEvent).where(IncidentEvent.incident_id == existing_inc.id))
            await self.db.execute(delete(Incident).where(Incident.id == existing_inc.id))
            await self.db.commit()

        # Ingest using IngestionService
        ingestion = IngestionService(self.db)
        job, result, msg = await ingestion.ingest_single_json(
            raw_data=raw_data,
            filename=f"fortisiem_{clean_id}.json",
            username=username,
        )

        if result == "error":
            raise HTTPException(status_code=500, detail=f"Ingestion processing error: {msg}")

        # Ensure investigation record is created for this incident
        investigation_svc = InvestigationService(self.db)
        await investigation_svc.ensure_all_incidents_have_investigations()

        # Retrieve saved incident
        res = await self.db.execute(
            select(Incident).where(Incident.incident_id == clean_id).options(selectinload(Incident.events))
        )
        saved = res.scalar_one_or_none()
        if not saved:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved incident after ingestion.")

        return {
            "success": True,
            "incident_id": saved.incident_id,
            "db_id": saved.id,
            "title": saved.title,
            "event_type": saved.event_type,
            "severity": saved.severity,
            "status_name": saved.status_name,
            "event_count": len(saved.events),
            "source": source_type,
            "message": f"Incident '{clean_id}' successfully pulled from FortiSIEM and ingested into AI Verdict.",
        }
