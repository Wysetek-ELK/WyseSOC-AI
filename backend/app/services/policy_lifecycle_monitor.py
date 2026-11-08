import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.rule import Rule
from app.models.prompt import RulePrompt, PromptVersion
from app.models.policy_drift import PolicyDriftEvent
from app.schemas.rule_intelligence import DetectionSemantics
from app.services.rule_intelligence_analyzer import RuleIntelligenceAnalyzer

logger = logging.getLogger("ai_verdict.lifecycle_monitor")


class PolicyLifecycleMonitor:
    """
    REQ-10: Continuous Policy Monitoring & Drift Detection Engine.
    Monitors upstream dependencies for changes that impact policy validity:
      1. SIEM Rule Definition Drift (thresholds, windows, pattern conditions)
      2. Telemetry Schema Drift (field additions/renames)
      3. Archetype Registry & Baseline Updates
      4. Verified Analyst Feedback
      
    Guarantees:
      - Changes mark policy REVALIDATION_REQUIRED.
      - Approved historical policies remain intact (no silent rewrites).
      - Verified analyst feedback informs drafts, NEVER automatically rewrites production.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_and_handle_rule_drift(
        self,
        rule: Rule,
        updated_rule_dict: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> List[PolicyDriftEvent]:
        """
        Compares existing rule logic with updated SIEM rule definition.
        Creates drift events and marks dependent prompt versions for revalidation.
        """
        drift_events: List[PolicyDriftEvent] = []
        changed_fields: Dict[str, Any] = {}

        old_pattern = rule.pattern_logic or ""
        new_pattern = updated_rule_dict.get("pattern_logic", old_pattern)
        if old_pattern != new_pattern:
            changed_fields["pattern_logic"] = {"old": old_pattern, "new": new_pattern}

        old_sev = rule.severity or "MEDIUM"
        new_sev = updated_rule_dict.get("severity", old_sev)
        if old_sev != new_sev:
            changed_fields["severity"] = {"old": old_sev, "new": new_sev}

        old_meta = rule.parsed_metadata or {}
        new_meta = updated_rule_dict.get("parsed_metadata", old_meta)
        if old_meta != new_meta:
            changed_fields["parsed_metadata"] = {"old": old_meta, "new": new_meta}

        if not changed_fields:
            return []

        # Find active prompt
        q = select(RulePrompt).where(RulePrompt.rule_id == rule.id)
        res = await self.db.execute(q)
        prompt = res.scalars().first()

        active_ver_id = prompt.active_version_id if prompt else None

        # Determine trigger type
        if "pattern_logic" in changed_fields:
            trigger_type = "SIEM_RULE_DEFINITION_CHANGED"
            summary = f"SIEM rule detection logic changed for rule '{rule.name}' ({rule.rule_id})."
        elif "severity" in changed_fields:
            trigger_type = "RULE_SEVERITY_CHANGED"
            summary = f"Rule severity changed from {old_sev} to {new_sev} for '{rule.name}'."
        else:
            trigger_type = "RULE_METADATA_UPDATED"
            summary = f"Metadata or telemetry configuration updated for rule '{rule.name}'."

        event = PolicyDriftEvent(
            rule_id=rule.id,
            prompt_version_id=active_ver_id,
            trigger_type=trigger_type,
            summary=summary,
            changed_fields=changed_fields,
            revalidation_required=True,
            acknowledged=False,
        )
        self.db.add(event)

        # Update prompt version quality status to REVIEW_REQUIRED if active
        if active_ver_id:
            pv_res = await self.db.execute(select(PromptVersion).where(PromptVersion.id == active_ver_id))
            active_pv = pv_res.scalar_one_or_none()
            if active_pv:
                active_pv.quality_status = "REVIEW_REQUIRED"

        await self.db.commit()
        await self.db.refresh(event)
        drift_events.append(event)
        return drift_events

    async def ingest_verified_analyst_feedback(
        self,
        rule_id: str,
        incident_id: str,
        adjudicated_verdict: str,
        model_verdict: str,
        analyst_notes: str,
        user_id: Optional[str] = None,
    ) -> Optional[PolicyDriftEvent]:
        """
        Captures independently verified analyst corrections to surface continuous improvement suggestions.
        Does NOT automatically rewrite active policies.
        """
        if adjudicated_verdict == model_verdict:
            return None  # No divergence, feedback agrees

        q = select(RulePrompt).where(RulePrompt.rule_id == rule_id)
        res = await self.db.execute(q)
        prompt = res.scalars().first()
        active_ver_id = prompt.active_version_id if prompt else None

        summary = (
            f"Verified analyst correction on incident {incident_id}: "
            f"Adjudicated={adjudicated_verdict} vs Model={model_verdict}. Notes: {analyst_notes}"
        )
        changed_fields = {
            "incident_id": incident_id,
            "adjudicated_verdict": adjudicated_verdict,
            "model_verdict": model_verdict,
            "analyst_notes": analyst_notes,
            "recommendation": "Review False Positive exceptions or Missing Evidence criteria in Section 6 & 7."
        }

        event = PolicyDriftEvent(
            rule_id=rule_id,
            prompt_version_id=active_ver_id,
            trigger_type="ANALYST_FEEDBACK_VERIFIED",
            summary=summary,
            changed_fields=changed_fields,
            revalidation_required=True,
            acknowledged=False,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def acknowledge_drift(
        self,
        rule_id: str,
        user_id: Optional[str] = None,
    ) -> int:
        """
        Acknowledges unacknowledged drift events for a rule.
        """
        q = select(PolicyDriftEvent).where(
            PolicyDriftEvent.rule_id == rule_id,
            PolicyDriftEvent.acknowledged == False,
        )
        res = await self.db.execute(q)
        events = res.scalars().all()
        for e in events:
            e.acknowledged = True
            if user_id:
                e.acknowledged_by_user_id = user_id
        await self.db.commit()
        return len(events)
