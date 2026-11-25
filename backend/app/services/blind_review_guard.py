"""
AIS 2.6f — Blind Review & Frozen Benchmark Isolation Guard

Single authoritative source of truth for:
1. Authoritative AIS 2.6e 20-incident frozen benchmark cohort definitions & ID mappings.
2. Sanitizing handover / analyst notes contaminated by legacy `[AI Verdict (...)]:` writes.
3. Unified server-side blind-review visibility policy (`can_reveal_protected_verdict_info`)
   that ensures:
   - When `blind_review=True`, AI verdicts, trust scores, and historical FortiSIEM labels
     are masked for ALL roles including Administrator and SuperAdmin.
   - Non-admin roles (`SOC Analyst`, `Viewer`) NEVER see protected AI/historical labels
     for unreviewed incidents even if `blind_review=False` is requested.
   - Benchmark certification incidents keep reviewers blind to AI predictions,
     historical FortiSIEM labels, and sibling reviewer verdicts until certification is finalized.
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession


FROZEN_AIS_2_6E_COHORT_ID = "AIS_2_6E_FROZEN_20"
FROZEN_AIS_2_6E_COHORT_NAME = "AIS 2.6e Frozen Benchmark Cohort (CrowdStrike + Prisma SASE)"

PRIORITY_5_INCIDENT_IDS: List[str] = [
    "132474210",
    "132596403",
    "132599145",
    "132438483",
    "132591888",
]

CROWDSTRIKE_FROZEN_INCIDENT_IDS: List[str] = [
    "132438483",
    "132439932",
    "132441815",
    "132461358",
    "132461368",
    "132472498",
    "132474210",
    "132501348",
    "132502453",
    "132527297",
]

PRISMA_SASE_FROZEN_INCIDENT_IDS: List[str] = [
    "132499009",
    "132499023",
    "132499745",
    "132578774",
    "132591888",
    "132595592",
    "132596403",
    "132599145",
    "132599146",
    "132599330",
]

# Ordered authoritative 20 frozen benchmark items: Priority 5 first (1..5), Remaining 15 next (6..20)
FROZEN_AIS_2_6E_ITEMS: List[Dict[str, Any]] = [
    {
        "fortisiem_incident_id": "132474210",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "PC-TSI-DC",
        "priority_tier": "PRIORITY_5",
        "sequence_order": 1,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132596403",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "review.es.system.js",
        "target_host": "172.25.6.101",
        "priority_tier": "PRIORITY_5",
        "sequence_order": 2,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132599145",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "jquery.knob.js",
        "target_host": "172.25.14.157",
        "priority_tier": "PRIORITY_5",
        "sequence_order": 3,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132438483",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "DESKTOP-E0G2R49",
        "priority_tier": "PRIORITY_5",
        "sequence_order": 4,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132591888",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "update.exe",
        "target_host": "172.25.6.208",
        "priority_tier": "PRIORITY_5",
        "sequence_order": 5,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132439932",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "TSI-IT-002-200",
        "priority_tier": "REMAINING_15",
        "sequence_order": 6,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132441815",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "DESKTOP-E0G2R49",
        "priority_tier": "REMAINING_15",
        "sequence_order": 7,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132461358",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "TSI-IT-002-200",
        "priority_tier": "REMAINING_15",
        "sequence_order": 8,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132461368",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "DESKTOP-E0G2R49",
        "priority_tier": "REMAINING_15",
        "sequence_order": 9,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132472498",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "PC-TSI-DC",
        "priority_tier": "REMAINING_15",
        "sequence_order": 10,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132501348",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "WSTPL",
        "observed_entity": "MEGAsync.exe",
        "target_host": "DESKTOP-CQ4A60U",
        "priority_tier": "REMAINING_15",
        "sequence_order": 11,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132502453",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "DESKTOP-KHU6454",
        "priority_tier": "REMAINING_15",
        "sequence_order": 12,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132527297",
        "vendor": "CrowdStrike",
        "event_type": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
        "rule_name": "Crowdstrike: Suspicious Activity",
        "customer": "Tosoh",
        "observed_entity": "UltraViewer_Service.exe",
        "target_host": "TSI-IT-002-95",
        "priority_tier": "REMAINING_15",
        "sequence_order": 13,
        "approved_rule_uuid": "271b0831-f6f5-4d86-9e0b-d53aee948cf0",
        "approved_rule_prompt_id": "08c59656-c002-4a76-b100-3c8d6d645eb2",
        "approved_prompt_version_id": "bd751fac-9bfb-4994-b150-8850bb94dd6c",
    },
    {
        "fortisiem_incident_id": "132499009",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "ss-widget.min.js",
        "target_host": "172.25.14.80",
        "priority_tier": "REMAINING_15",
        "sequence_order": 14,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132499023",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "clientlib-site.min.434edaea5200f31ba33eec0dd0b0cf19.js",
        "target_host": "172.25.14.67",
        "priority_tier": "REMAINING_15",
        "sequence_order": 15,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132499745",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "scripts-QBOKETIS.js",
        "target_host": "172.25.14.80",
        "priority_tier": "REMAINING_15",
        "sequence_order": 16,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132578774",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "adrum22603859.js",
        "target_host": "172.25.2.3",
        "priority_tier": "REMAINING_15",
        "sequence_order": 17,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132595592",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "2005.70cb3d6bf67c91a7.js",
        "target_host": "172.25.6.95",
        "priority_tier": "REMAINING_15",
        "sequence_order": 18,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132599146",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "exporting.js",
        "target_host": "172.25.14.157",
        "priority_tier": "REMAINING_15",
        "sequence_order": 19,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
    {
        "fortisiem_incident_id": "132599330",
        "vendor": "Prisma SASE",
        "event_type": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
        "rule_name": "Prisma SASE: Suspicious File Threat Detection",
        "customer": "Forbes_Marshall",
        "observed_entity": "select2.min.js",
        "target_host": "172.25.14.157",
        "priority_tier": "REMAINING_15",
        "sequence_order": 20,
        "approved_rule_uuid": "b2f1f1e4-117b-4b0e-87ca-65869898630b",
        "approved_rule_prompt_id": "1fe4e834-bd52-4571-95ca-ee329e40e1b2",
        "approved_prompt_version_id": "8ae7beaa-626a-4061-a0c4-8500f7e6a69d",
    },
]

FROZEN_INCIDENT_IDS_SET: Set[str] = {
    item["fortisiem_incident_id"] for item in FROZEN_AIS_2_6E_ITEMS
}
FROZEN_ITEM_BY_FORTISIEM_ID: Dict[str, Dict[str, Any]] = {
    item["fortisiem_incident_id"]: item for item in FROZEN_AIS_2_6E_ITEMS
}

# Patterns written into analyst_notes by legacy _upsert_ai_verdict_note or synthetic/leak helpers
_AI_NOTE_BLOCK_RE = re.compile(
    r"(?:^|\n{2,})\[AI Verdict \([^\)]*\)\]:.*?(?=\n{2,}|\Z)",
    re.IGNORECASE | re.DOTALL,
)
_AI_LINE_MARKER_RE = re.compile(
    r"(?im)^(?:\[AI Verdict\b|AI Proposed Verdict\b|AI Validated Verdict\b|Trust Score\b|Historical Ground Truth\b).*$"
)


def strip_ai_notes_from_handover(notes: Optional[str]) -> str:
    """
    Removes AI verdict contamination (such as `[AI Verdict (REQUIRES_ATTENTION - 0%)]: ...`)
    from analyst handover notes while preserving legitimate human investigation notes.
    """
    if not notes:
        return ""
    cleaned = _AI_NOTE_BLOCK_RE.sub("", str(notes))
    cleaned_lines = [
        line for line in cleaned.splitlines()
        if not _AI_LINE_MARKER_RE.match(line.strip())
    ]
    result = "\n".join(cleaned_lines).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result


def has_ai_notes_contamination(notes: Optional[str]) -> bool:
    """Returns True if notes contain legacy `[AI Verdict (` or AI verdict leakage markers."""
    if not notes:
        return False
    text = str(notes)
    return bool(_AI_NOTE_BLOCK_RE.search(text) or any(
        _AI_LINE_MARKER_RE.match(line.strip()) for line in text.splitlines()
    ))


async def get_benchmark_incident_identifiers(db: AsyncSession) -> Set[str]:
    """
    Returns all incident DB UUIDs and FortiSIEM incident_ids belonging to any registered
    benchmark cohort with `excluded_from_learning=True` so learning/RAG/prompt optimization
    never contaminates itself from benchmark ground truth data.
    """
    identifiers: Set[str] = set()
    try:
        from app.models.analyst_feedback import BenchmarkCohort, BenchmarkCohortItem
        res = await db.execute(
            select(
                BenchmarkCohortItem.incident_db_id,
                BenchmarkCohortItem.fortisiem_incident_id,
            )
            .join(BenchmarkCohort, BenchmarkCohortItem.cohort_id == BenchmarkCohort.id)
            .where(BenchmarkCohort.excluded_from_learning.is_(True))
        )
        for db_id, f_id in res.all():
            if db_id:
                identifiers.add(str(db_id))
            if f_id:
                identifiers.add(str(f_id))
    except Exception:
        # Table may not exist during very early isolated schema bootstrap
        pass
    return identifiers


async def is_frozen_benchmark_incident(
    db: AsyncSession,
    incident_id_or_uuid: Optional[str],
    fortisiem_incident_id: Optional[str] = None,
) -> bool:
    """
    Returns True if an incident (by DB UUID or FortiSIEM vendor ID) is registered in any
    `BenchmarkCohortItem` belonging to an isolated benchmark cohort (`excluded_from_learning=True`).
    """
    candidates = {str(x).strip() for x in (incident_id_or_uuid, fortisiem_incident_id) if x}
    if not candidates:
        return False
    try:
        from app.models.analyst_feedback import BenchmarkCohort, BenchmarkCohortItem
        stmt = (
            select(BenchmarkCohortItem.id)
            .join(BenchmarkCohort, BenchmarkCohortItem.cohort_id == BenchmarkCohort.id)
            .where(
                BenchmarkCohort.excluded_from_learning.is_(True),
                or_(
                    BenchmarkCohortItem.incident_db_id.in_(list(candidates)),
                    BenchmarkCohortItem.fortisiem_incident_id.in_(list(candidates)),
                ),
            )
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none() is not None
    except Exception:
        return False


async def user_has_reviewed_incident(
    db: AsyncSession,
    current_user: Any,
    incident_identifiers: Iterable[Optional[str]],
) -> bool:
    """Checks whether `current_user` has submitted an independent review for the incident."""
    if not current_user:
        return False
    inc_ids = [str(x) for x in incident_identifiers if x]
    if not inc_ids:
        return False
    from app.models.analyst_feedback import AnalystVerdictReview

    user_filters = []
    if getattr(current_user, "id", None):
        user_filters.append(AnalystVerdictReview.reviewer_id == str(current_user.id))
    if getattr(current_user, "username", None):
        user_filters.append(AnalystVerdictReview.reviewer_id == str(current_user.username))
    if not user_filters:
        return False

    rev_q = (
        select(AnalystVerdictReview.id)
        .where(
            AnalystVerdictReview.incident_id.in_(inc_ids),
            or_(*user_filters),
        )
        .limit(1)
    )
    return (await db.execute(rev_q)).scalar_one_or_none() is not None


async def can_reveal_protected_verdict_info(
    db: AsyncSession,
    current_user: Any,
    incident_identifiers: Iterable[Optional[str]],
    blind_review: bool = False,
    reviewed_inc_ids: Optional[Set[str]] = None,
) -> bool:
    """
    Centralized double-blind visibility policy:
    1. If `blind_review=True`, ALWAYS returns False for ALL roles (including Admin/SuperAdmin).
    2. If `current_user` is None, returns False.
    3. If `current_user` is Administrator/SuperAdmin (and `blind_review=False`), returns True
       for operational views (benchmark certification APIs apply stricter cohort lock separately).
    4. If `current_user` is SOC Analyst, returns True ONLY if the analyst has already submitted
       their own independent review for this incident.
    5. All other roles (e.g., Viewer) return False.
    """
    if blind_review:
        return False
    if not current_user:
        return False

    user_role = getattr(current_user, "role", "")
    is_admin = user_role in ("Administrator", "SuperAdmin") or bool(
        getattr(current_user, "is_superuser", False)
    )
    if is_admin:
        return True

    if user_role == "SOC Analyst":
        ids_set = {str(x) for x in incident_identifiers if x}
        if reviewed_inc_ids is not None:
            return bool(ids_set & reviewed_inc_ids)
        return await user_has_reviewed_incident(db, current_user, ids_set)

    return False


def get_blind_mask_response_marker() -> str:
    return "[Hidden - Blind Review]"
