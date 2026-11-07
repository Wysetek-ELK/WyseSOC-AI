import os
import json
import zipfile
import re
import time
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional
import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.config import settings, BASE_DIR
from app.models.incident import Incident, IncidentEvent, HistoricalGroundTruth
from app.models.investigation import Investigation
from app.models.rule import Rule
from app.models.prompt import RulePrompt
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

    @classmethod
    async def get_recent_live_incident_ids(cls, limit: int = 8) -> List[str]:
        """Queries the live supervisor for the most recent incident IDs for quick selection."""
        if not (settings.FORTISIEM_HOST and settings.FORTISIEM_HOST.strip()):
            return []

        base_url = settings.FORTISIEM_HOST.strip().rstrip("/")
        auth = None
        if settings.FORTISIEM_USERNAME and settings.FORTISIEM_PASSWORD:
            auth = (settings.FORTISIEM_USERNAME, settings.FORTISIEM_PASSWORD)

        now_ms = int(time.time() * 1000)
        past_ms = now_ms - (30 * 86400 * 1000)  # last 30 days
        try:
            async with httpx.AsyncClient(verify=settings.FORTISIEM_VERIFY_SSL, timeout=5.0) as client:
                res = await client.get(
                    f"{base_url}/phoenix/rest/pub/incident",
                    params={"timeFrom": past_ms, "timeTo": now_ms, "size": limit},
                    auth=auth,
                    headers={"Accept": "application/json"}
                )
                if res.status_code == 200:
                    d = res.json()
                    items = d.get("data", []) if isinstance(d, dict) else (d if isinstance(d, list) else [])
                    ids = []
                    for item in items:
                        if isinstance(item, dict):
                            iid = str(item.get("incidentId") or item.get("id") or "").strip()
                            if iid and iid not in ids:
                                ids.append(iid)
                    return ids[:limit]
        except Exception:
            pass
        return []

    async def sync_all_rules_from_siem(self) -> Dict[str, Any]:
        """
        Discovers and synchronizes all active detection rules from FortiSIEM Supervisor
        and registers them into the local Rule and RulePrompt repositories.
        """
        # 1. Fetch current local rules into memory
        rules_res = await self.db.execute(select(Rule))
        local_rules = rules_res.scalars().all()
        rules_by_type = {r.event_type: r for r in local_rules}
        rules_by_id = {r.rule_id: r for r in local_rules}

        discovered_incidents: List[Dict[str, Any]] = []

        # 2. Query FortiSIEM live if host is configured
        if settings.FORTISIEM_HOST and settings.FORTISIEM_HOST.strip():
            base_url = settings.FORTISIEM_HOST.strip().rstrip("/")
            auth = None
            if settings.FORTISIEM_USERNAME and settings.FORTISIEM_PASSWORD:
                auth = (settings.FORTISIEM_USERNAME, settings.FORTISIEM_PASSWORD)

            now_ms = int(time.time() * 1000)
            past_ms = now_ms - (180 * 86400 * 1000)  # last 180 days

            try:
                async with httpx.AsyncClient(verify=settings.FORTISIEM_VERIFY_SSL, timeout=settings.FORTISIEM_TIMEOUT) as client:
                    # Query batch 1: past 180 days
                    res1 = await client.get(
                        f"{base_url}/phoenix/rest/pub/incident",
                        params={"timeFrom": past_ms, "timeTo": now_ms, "size": 500},
                        auth=auth,
                        headers={"Accept": "application/json"}
                    )
                    if res1.status_code == 200:
                        d1 = res1.json()
                        discovered_incidents.extend(d1.get("data", []) if isinstance(d1, dict) else [])

                    # If needed, query batch 2: all time / epoch 0
                    if len(discovered_incidents) < 50:
                        res2 = await client.get(
                            f"{base_url}/phoenix/rest/pub/incident",
                            params={"timeFrom": 0, "timeTo": now_ms, "size": 500},
                            auth=auth,
                            headers={"Accept": "application/json"}
                        )
                        if res2.status_code == 200:
                            d2 = res2.json()
                            for item in (d2.get("data", []) if isinstance(d2, dict) else []):
                                if isinstance(item, dict) and item not in discovered_incidents:
                                    discovered_incidents.append(item)
            except Exception:
                pass

        # 3. Offline / Fixture discovery fallback if live returned empty
        if not discovered_incidents and os.path.exists(self.fixtures_zip_path):
            try:
                with zipfile.ZipFile(self.fixtures_zip_path, "r") as z:
                    for name in z.namelist():
                        if name.lower().endswith(".json"):
                            try:
                                raw_bytes = z.read(name)
                                d = json.loads(raw_bytes.decode("utf-8"))
                                if isinstance(d, dict) and ("eventType" in d or "eventName" in d):
                                    discovered_incidents.append(d)
                            except Exception:
                                pass
            except Exception:
                pass

        # 4. Extract and register unique rules
        new_count = 0
        updated_count = 0
        synced_rules_summary = []

        unique_rules_map: Dict[str, Dict[str, Any]] = {}
        for inc in discovered_incidents:
            if not isinstance(inc, dict):
                continue
            event_type = str(inc.get("eventType") or "").strip()
            event_name = str(inc.get("eventName") or inc.get("incidentTitle") or "").strip()
            if not event_type and not event_name:
                continue
            key = event_type or event_name
            if key not in unique_rules_map:
                unique_rules_map[key] = inc

        for key, inc in unique_rules_map.items():
            event_type = str(inc.get("eventType") or key).strip()
            event_name = str(inc.get("eventName") or inc.get("incidentTitle") or event_type).strip()

            raw_sev = str(inc.get("eventSeverityCat") or inc.get("eventSeverity") or "MEDIUM").upper()
            if "CRIT" in raw_sev:
                severity = "CRITICAL"
            elif "HIGH" in raw_sev:
                severity = "HIGH"
            elif "LOW" in raw_sev or "INFO" in raw_sev:
                severity = "LOW"
            else:
                severity = "MEDIUM"

            category = str(inc.get("phIncidentCategory") or "Security")
            sub_cat = str(inc.get("phSubIncidentCategory") or inc.get("incidentTagName") or "Policy Violation")
            data_src = str(inc.get("incidentRptDevName") or "FortiSIEM")
            pattern = str(inc.get("incidentDetail") or "")
            if not pattern and inc.get("incidentDetailJson"):
                try:
                    pattern = json.dumps(inc.get("incidentDetailJson"))
                except Exception:
                    pattern = str(inc.get("incidentDetailJson"))

            metadata = {
                "source": "FORTISIEM_LIVE_SYNC",
                "category": category,
                "subCategory": sub_cat,
                "attackTechnique": inc.get("attackTechnique"),
                "attackTactic": inc.get("attackTactic"),
                "customer": inc.get("customer"),
                "synced_at": datetime.utcnow().isoformat(),
            }

            existing = rules_by_type.get(event_type) or rules_by_id.get(event_type)
            if not existing:
                # Create new Rule
                new_rule = Rule(
                    rule_id=event_type,
                    name=event_name,
                    event_type=event_type,
                    description=f"Detection rule '{event_name}' ({category} / {sub_cat}) synchronized from FortiSIEM.",
                    severity=severity,
                    status="ACTIVE",
                    data_source=data_src,
                    detection_tech=sub_cat or "SIEM Rule Engine",
                    evaluation_mode="ONLINE",
                    pattern_logic=pattern,
                    raw_rule_text=f"Rule: {event_name}\nEventType: {event_type}\nCategory: {category}\nSubCategory: {sub_cat}\nPattern: {pattern}",
                    parsed_metadata=metadata,
                )
                self.db.add(new_rule)
                await self.db.flush()

                # Generate template draft prompt
                try:
                    from app.services.prompt_studio_service import PromptStudioService
                    ps_svc = PromptStudioService(self.db)
                    draft = await ps_svc.generate_template_draft(rule_id=new_rule.id)
                    rp_q = await self.db.execute(select(RulePrompt).where(RulePrompt.rule_id == new_rule.id))
                    rp = rp_q.scalars().first()
                    if rp and not rp.active_version_id and draft:
                        rp.active_version_id = draft.id
                        await self.db.flush()
                except Exception:
                    pass

                rules_by_type[event_type] = new_rule
                rules_by_id[event_type] = new_rule
                new_count += 1
                synced_rules_summary.append({
                    "rule_id": new_rule.rule_id,
                    "name": new_rule.name,
                    "severity": new_rule.severity,
                    "event_type": new_rule.event_type,
                    "is_new": True,
                })
            else:
                # Update metadata if needed
                existing.severity = severity
                existing.status = "ACTIVE"
                if pattern and not existing.pattern_logic:
                    existing.pattern_logic = pattern
                existing.parsed_metadata = metadata
                existing.updated_at = datetime.utcnow()
                updated_count += 1
                synced_rules_summary.append({
                    "rule_id": existing.rule_id,
                    "name": existing.name,
                    "severity": existing.severity,
                    "event_type": existing.event_type,
                    "is_new": False,
                })

        await self.db.commit()

        # Total rules count
        total_q = await self.db.execute(select(Rule))
        total_rules = len(total_q.scalars().all())

        return {
            "success": True,
            "synced_rules_count": len(unique_rules_map),
            "new_rules_count": new_count,
            "updated_rules_count": updated_count,
            "total_local_rules": total_rules,
            "synced_rules": synced_rules_summary[:30],
            "message": f"Successfully synchronized {len(unique_rules_map)} detection rules from FortiSIEM ({new_count} newly cached, {updated_count} refreshed). Total local rules: {total_rules}."
        }

    def _parse_siem_response(self, res: httpx.Response, target_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Parses a response from FortiSIEM, supporting both JSON and XML formats."""
        clean_id = str(target_id).strip() if target_id else ""
        try:
            val = res.json()
            if isinstance(val, dict):
                iid = str(val.get("incidentId") or val.get("id") or "").strip()
                if clean_id and iid and iid != clean_id:
                    return None
                if "incidentId" in val or "id" in val or "eventName" in val or "title" in val:
                    return val
            elif isinstance(val, list) and len(val) > 0:
                return self._extract_incident_from_pub_response(val, clean_id)
        except Exception:
            pass
        text = res.text.strip()
        if text.startswith("<") and text.endswith(">"):
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(text)
                res_dict: Dict[str, Any] = {}
                for child in root:
                    tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                    res_dict[tag] = child.text.strip() if child.text else ""
                iid = str(res_dict.get("incidentId") or res_dict.get("id") or "").strip()
                if clean_id and iid and iid != clean_id:
                    return None
                return res_dict if res_dict and ("incidentId" in res_dict or "id" in res_dict) else None
            except Exception:
                pass
        return None

    def _extract_incident_from_pub_response(self, data: Any, target_id: str) -> Optional[Dict[str, Any]]:
        """Extracts target incident object from FortiSIEM /pub/incident payload."""
        clean_id = str(target_id).strip()
        if not clean_id:
            return None

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    iid = str(item.get("incidentId") or item.get("id") or "").strip()
                    if iid == clean_id:
                        return item
        elif isinstance(data, dict):
            for key in ("data", "incidents", "incidentList", "results", "items"):
                if key in data and isinstance(data[key], list):
                    for item in data[key]:
                        if isinstance(item, dict):
                            iid = str(item.get("incidentId") or item.get("id") or "").strip()
                            if iid == clean_id:
                                return item
            iid = str(data.get("incidentId") or data.get("id") or "").strip()
            if iid == clean_id:
                return data
        return None

    async def _enrich_triggering_events(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        incident_id: str,
        auth: Optional[Tuple[str, str]],
        incident_data: Dict[str, Any],
    ) -> None:
        """Fetches and populates rawEvents if the main incident object lacks triggering events."""
        if incident_data.get("rawEvents") and isinstance(incident_data["rawEvents"], list) and len(incident_data["rawEvents"]) > 0:
            return

        probe_urls = [
            (f"{base_url}/phoenix/rest/pub/incident/triggeringEvents", {"incidentId": incident_id, "size": 100}),
            (f"{base_url}/phoenix/rest/incident/triggeringEvents", {"incidentIds": incident_id}),
        ]
        for url, params in probe_urls:
            try:
                res = await client.get(url, params=params, auth=auth, headers={"Accept": "application/json"})
                if res.status_code == 200:
                    evts = res.json()
                    if isinstance(evts, list):
                        incident_data["rawEvents"] = evts
                        return
                    elif isinstance(evts, dict):
                        for k in ("events", "rawEvents", "data", "triggeringEvents"):
                            if k in evts and isinstance(evts[k], list):
                                incident_data["rawEvents"] = evts[k]
                                return
            except Exception:
                continue

    async def _query_live_siem_endpoints(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        clean_id: str,
        auth: Optional[Tuple[str, str]],
    ) -> Optional[Dict[str, Any]]:
        """
        Queries FortiSIEM REST API endpoints in sequence to locate the target incident.
        Supports both legacy incidentDetail and modern JSON Public Incident API.
        """
        numeric_id = int(clean_id) if clean_id.isdigit() else clean_id

        # Strategy 1: /phoenix/rest/incident/incidentDetail (Standard & Mocked endpoint)
        try:
            res = await client.get(
                f"{base_url}/phoenix/rest/incident/incidentDetail",
                params={"incidentId": clean_id},
                auth=auth,
                headers={"Accept": "application/json, application/xml;q=0.9, */*;q=0.8"},
            )
            if res.status_code == 200:
                parsed = self._parse_siem_response(res, clean_id)
                if parsed:
                    await self._enrich_triggering_events(client, base_url, clean_id, auth, parsed)
                    return parsed
            elif res.status_code in (401, 403):
                raise HTTPException(
                    status_code=502,
                    detail="FortiSIEM authentication failed. Verify FORTISIEM_USERNAME and FORTISIEM_PASSWORD."
                )
        except HTTPException:
            raise
        except Exception:
            pass

        # Strategy 2: Modern Public JSON Incident API (POST filter)
        try:
            post_payload = {
                "filters": {
                    "incidentId": [numeric_id]
                },
                "start": 0,
                "size": 10,
            }
            res = await client.post(
                f"{base_url}/phoenix/rest/pub/incident",
                json=post_payload,
                auth=auth,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            if res.status_code == 200:
                parsed = self._extract_incident_from_pub_response(res.json(), clean_id)
                if parsed:
                    await self._enrich_triggering_events(client, base_url, clean_id, auth, parsed)
                    return parsed
            elif res.status_code in (401, 403):
                raise HTTPException(
                    status_code=502,
                    detail="FortiSIEM authentication failed. Verify FORTISIEM_USERNAME and FORTISIEM_PASSWORD."
                )
        except HTTPException:
            raise
        except Exception:
            pass

        # Strategy 3: Modern Public JSON Incident API (GET filter)
        try:
            res = await client.get(
                f"{base_url}/phoenix/rest/pub/incident",
                params={"incidentId": clean_id},
                auth=auth,
                headers={"Accept": "application/json"},
            )
            if res.status_code == 200:
                parsed = self._extract_incident_from_pub_response(res.json(), clean_id)
                if parsed:
                    await self._enrich_triggering_events(client, base_url, clean_id, auth, parsed)
                    return parsed
        except HTTPException:
            raise
        except Exception:
            pass

        # Strategy 4: Direct path /phoenix/rest/pub/incident/{id}
        try:
            res = await client.get(
                f"{base_url}/phoenix/rest/pub/incident/{clean_id}",
                auth=auth,
                headers={"Accept": "application/json"},
            )
            if res.status_code == 200:
                parsed = self._parse_siem_response(res, clean_id)
                if parsed:
                    await self._enrich_triggering_events(client, base_url, clean_id, auth, parsed)
                    return parsed
        except HTTPException:
            raise
        except Exception:
            pass

        return None

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
            auth = None
            if settings.FORTISIEM_USERNAME and settings.FORTISIEM_PASSWORD:
                auth = (settings.FORTISIEM_USERNAME, settings.FORTISIEM_PASSWORD)

            live_data = None
            try:
                async with httpx.AsyncClient(
                    verify=settings.FORTISIEM_VERIFY_SSL,
                    timeout=settings.FORTISIEM_TIMEOUT,
                ) as client:
                    live_data = await self._query_live_siem_endpoints(client, base_url, clean_id, auth)
            except HTTPException:
                raise
            except httpx.RequestError as exc:
                if not settings.FORTISIEM_MOCK_FALLBACK:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Failed to connect to FortiSIEM host ({base_url}): {str(exc)}"
                    )

            if live_data:
                return live_data, "LIVE"

            # If not found on live SIEM, and mock fallback is explicitly disabled, raise 404
            if not settings.FORTISIEM_MOCK_FALLBACK:
                raise HTTPException(
                    status_code=404,
                    detail=f"Incident '{clean_id}' was not found in live FortiSIEM ({base_url})."
                )

        # 2. Fixture fallback (Development, offline, demo mode, or when not found on live SIEM)
        if settings.FORTISIEM_MOCK_FALLBACK and os.path.exists(self.fixtures_zip_path):
            with zipfile.ZipFile(self.fixtures_zip_path, "r") as z:
                for name in z.namelist():
                    match = re.search(r"incid\w*id_(\d+)\.json", name, re.IGNORECASE)
                    if match and match.group(1) == clean_id:
                        raw_bytes = z.read(name)
                        data = json.loads(raw_bytes.decode("utf-8"))
                        return data, "FIXTURE_FALLBACK"

        # Not found in live SIEM and not found in fixture fallback
        available = self.get_available_fixture_ids()
        fixture_hint = f" Available fixture samples: {', '.join(available[:6])}." if available else ""
        if settings.FORTISIEM_HOST and settings.FORTISIEM_HOST.strip():
            msg = (
                f"Incident '{clean_id}' was not found on FortiSIEM Supervisor ({settings.FORTISIEM_HOST}). "
                f"Please verify the ID or select one of the live active incidents displayed on the ingestion portal.{fixture_hint}"
            )
        else:
            msg = (
                f"Incident '{clean_id}' was not found in offline sample fixtures.{fixture_hint}"
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
            "message": (
                f"Incident '{clean_id}' successfully pulled live from FortiSIEM Supervisor."
                if source_type == "LIVE"
                else f"Incident '{clean_id}' successfully loaded from offline fixture archive (not found on live FortiSIEM)."
            ),
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
