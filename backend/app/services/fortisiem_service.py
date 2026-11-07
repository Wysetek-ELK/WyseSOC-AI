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

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Returns the current FortiSIEM connector configuration (password masked)."""
        is_configured = bool(settings.FORTISIEM_HOST and settings.FORTISIEM_HOST.strip())
        return {
            "is_configured": is_configured,
            "host": settings.FORTISIEM_HOST,
            "username": settings.FORTISIEM_USERNAME,
            "is_password_set": bool(settings.FORTISIEM_PASSWORD and settings.FORTISIEM_PASSWORD.strip()),
            "verify_ssl": settings.FORTISIEM_VERIFY_SSL,
            "timeout": settings.FORTISIEM_TIMEOUT,
            "mock_fallback": settings.FORTISIEM_MOCK_FALLBACK,
        }

    @classmethod
    def update_config(
        cls,
        host: str,
        username: str,
        password: Optional[str] = None,
        verify_ssl: bool = False,
        timeout: float = 25.0,
        mock_fallback: bool = True,
    ) -> Dict[str, Any]:
        """
        Updates FortiSIEM settings dynamically in memory and persists to .env file.
        """
        clean_host = host.strip().rstrip("/")
        if clean_host and not (clean_host.startswith("http://") or clean_host.startswith("https://")):
            clean_host = f"https://{clean_host}"

        clean_user = username.strip()

        # 1. Update in-memory settings
        settings.FORTISIEM_HOST = clean_host
        settings.FORTISIEM_USERNAME = clean_user
        if password is not None and password.strip():
            settings.FORTISIEM_PASSWORD = password.strip()
        settings.FORTISIEM_VERIFY_SSL = verify_ssl
        settings.FORTISIEM_TIMEOUT = float(timeout)
        settings.FORTISIEM_MOCK_FALLBACK = mock_fallback

        # 2. Persist to backend .env file
        env_path = os.path.join(BASE_DIR, ".env")
        env_lines = []

        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
                    if match:
                        key = match.group(1)
                        if key in (
                            "FORTISIEM_HOST",
                            "FORTISIEM_USERNAME",
                            "FORTISIEM_PASSWORD",
                            "FORTISIEM_VERIFY_SSL",
                            "FORTISIEM_TIMEOUT",
                            "FORTISIEM_MOCK_FALLBACK",
                        ):
                            continue  # Rewrite updated values below
                    env_lines.append(line)

        # Append or rewrite FortiSIEM variables
        env_updates = [
            f'\n# FortiSIEM Live Supervisor Connection\n',
            f'FORTISIEM_HOST="{settings.FORTISIEM_HOST}"\n',
            f'FORTISIEM_USERNAME="{settings.FORTISIEM_USERNAME}"\n',
            f'FORTISIEM_PASSWORD="{settings.FORTISIEM_PASSWORD}"\n',
            f'FORTISIEM_VERIFY_SSL={"true" if settings.FORTISIEM_VERIFY_SSL else "false"}\n',
            f'FORTISIEM_TIMEOUT={settings.FORTISIEM_TIMEOUT}\n',
            f'FORTISIEM_MOCK_FALLBACK={"true" if settings.FORTISIEM_MOCK_FALLBACK else "false"}\n',
        ]
        env_lines.extend(env_updates)

        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(env_lines)
            if hasattr(os, "chmod"):
                try:
                    os.chmod(env_path, 0o600)
                except Exception:
                    pass
        except Exception:
            pass

        return cls.get_config()

    @classmethod
    async def test_siem_connection(
        cls,
        host: str,
        username: str,
        password: Optional[str] = None,
        verify_ssl: bool = False,
        timeout: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Tests connection and authentication against the specified FortiSIEM Supervisor.
        """
        import time
        clean_host = host.strip().rstrip("/")
        if not clean_host:
            raise HTTPException(status_code=400, detail="FortiSIEM Host URL/IP is required.")

        if not (clean_host.startswith("http://") or clean_host.startswith("https://")):
            clean_host = f"https://{clean_host}"

        clean_user = username.strip()
        auth_pass = password.strip() if (password is not None and password.strip()) else settings.FORTISIEM_PASSWORD

        if not clean_user:
            raise HTTPException(status_code=400, detail="FortiSIEM Username is required.")

        start_t = time.time()
        auth = (clean_user, auth_pass) if auth_pass else None
        endpoint = f"{clean_host}/phoenix/rest/incident/incidentDetail"

        try:
            async with httpx.AsyncClient(verify=verify_ssl, timeout=timeout) as client:
                res = await client.get(endpoint, params={"incidentId": "0"}, auth=auth, headers={"Accept": "application/json"})
                latency = int((time.time() - start_t) * 1000)

                # Status 200 or 404 indicates server reached and auth passed
                if res.status_code in (200, 404):
                    return {
                        "success": True,
                        "status_code": res.status_code,
                        "latency_ms": latency,
                        "message": f"Successfully connected to FortiSIEM Supervisor at {clean_host} (Latency: {latency}ms).",
                        "details": {"endpoint": endpoint, "status_code": res.status_code},
                    }
                elif res.status_code in (401, 403):
                    return {
                        "success": False,
                        "status_code": res.status_code,
                        "latency_ms": latency,
                        "message": "Authentication failed: FortiSIEM rejected the provided username or password.",
                        "details": {"status_code": res.status_code},
                    }
                else:
                    return {
                        "success": False,
                        "status_code": res.status_code,
                        "latency_ms": latency,
                        "message": f"Supervisor returned HTTP {res.status_code}: {res.text[:150]}",
                        "details": {"status_code": res.status_code},
                    }
        except httpx.ConnectTimeout:
            return {
                "success": False,
                "status_code": None,
                "latency_ms": int((time.time() - start_t) * 1000),
                "message": f"Connection timed out after {timeout} seconds connecting to {clean_host}.",
                "details": {"error": "Timeout"},
            }
        except httpx.ConnectError as ce:
            return {
                "success": False,
                "status_code": None,
                "latency_ms": int((time.time() - start_t) * 1000),
                "message": f"Could not establish network connection to {clean_host}. Verify IP, port 443, and firewall rules.",
                "details": {"error": str(ce)},
            }
        except Exception as exc:
            return {
                "success": False,
                "status_code": None,
                "latency_ms": int((time.time() - start_t) * 1000),
                "message": f"Connection error: {str(exc)}",
                "details": {"error": str(exc)},
            }
