"""
Historical Ground Truth Validator (AIS 2.1).
Adjudicates historical analyst labels, prevents inference data leakage,
and partitions historical datasets into strict evaluation splits.

Adjudicated Labels:
- VERIFIED_TP: Confirmed True Positive supported by analyst evidence
- VERIFIED_FP: Confirmed False Positive supported by analyst rationale
- UNVERIFIED: Analyst decision lacking documented rationale or evidence
- CONFLICTING: Divergent verdicts across multiple analyst reviews
- UNKNOWN: Unclosed or unadjudicated incident

Data Leakage Prevention:
- Automatically sanitizes incident payloads before inference, stripping
  resolution notes, analyst verdicts, closure comments, and ground-truth hints.
"""

import copy
import hashlib
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.verdict_intelligence import (
    GroundTruthLabel,
    GroundTruthProvenance,
    DatasetPartition,
    GroundTruthItem,
)

logger = logging.getLogger("ai_verdict.ground_truth_validator")


class HistoricalGroundTruthValidator:
    """
    Validates the integrity of historical ground truth labels and guarantees
    that model inference inputs are strictly blinded to outcome labels.
    """

    _NORMALIZED_LEAKAGE_KEYS = frozenset({
        "groundtruth", "historicalgroundtruth", "aiverdict",
        "resolution", "clearedreason", "cleareduser", "cmsclearuser",
        "clearedtime", "resolvedat", "comments", "closurecomments",
        "analystverdict", "analystnotes", "closecode", "resolutionsummary",
        "adjudicatedverdict", "feedback", "analystfeedback",
        "ticketstatus", "statusname", "historicalresolution", "ismllgenerated",
        "ismlgenerated", "mttr", "incidentclearedreason", "incidentcomments",
        "incidentresolution",
    })

    @classmethod
    def _normalize_key(cls, key: Any) -> str:
        return re.sub(r"[^a-z0-9]", "", str(key or "").lower())

    @classmethod
    def _deep_strip_leakage(cls, obj: Any) -> Any:
        if isinstance(obj, dict):
            cleaned: Dict[str, Any] = {}
            for k, v in obj.items():
                nk = cls._normalize_key(k)
                if nk in cls._NORMALIZED_LEAKAGE_KEYS or "cleared" in nk or "groundtruth" in nk or "analystverdict" in nk:
                    continue
                cleaned[k] = cls._deep_strip_leakage(v)
            return cleaned
        if isinstance(obj, list):
            return [cls._deep_strip_leakage(item) for item in obj]
        return obj

    @classmethod
    def sanitize_incident_for_inference(cls, incident_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        CRITICAL DATA LEAKAGE PREVENTION:
        Produces a sanitized incident dictionary for model consumption.
        Recursively strips resolution notes, analyst comments, camelCase/snake_case
        FortiSIEM closure fields, historical ground truth, and feedback hints at all depths.
        """
        sanitized = copy.deepcopy(incident_payload)
        result = cls._deep_strip_leakage(sanitized)
        return result if isinstance(result, dict) else {}

    @classmethod
    def _is_automated_resolution_text(
        cls,
        is_ml_generated: bool = False,
        comments: str = "",
        cleared_reason: str = "",
        cleared_user: str = "",
        provenance: str = "",
    ) -> bool:
        combined = " ".join([comments, cleared_reason, cleared_user, provenance]).lower()
        return bool(
            is_ml_generated
            or "machine learning" in combined
            or "resolution set by machine learning" in combined
            or "automated" in combined
            or "auto-cleared" in combined
            or "auto cleared" in combined
            or "ai verdict" in combined
            or "simulated-heuristic" in combined
            or "ml generated" in combined
            or str(provenance or "").upper().strip() in ("AI_GENERATED", "ML_GENERATED", "SIMULATED", "HEURISTIC")
        )

    @classmethod
    def is_synthetic_fixture(
        cls,
        incident: Any,
        raw_payload: Dict[str, Any],
        ground_truth: Optional[Any] = None,
    ) -> Optional[str]:
        """
        Identifies zero-event synthetic/debug fixtures so they never enter
        empirical evaluation cohorts silently.
        """
        inc_id = str(getattr(incident, "incident_id", "") or "").upper().strip()
        gt_prov = str(getattr(ground_truth, "provenance", "") or "").upper().strip()
        if raw_payload.get("is_synthetic") is True or raw_payload.get("synthetic") is True or gt_prov == "SYNTHETIC_FIXTURE":
            return "Incident is explicitly tagged as a synthetic test fixture without production telemetry."

        ev_list = getattr(incident, "events", None) or []
        raw_events = raw_payload.get("rawEvents") if isinstance(raw_payload, dict) else None
        has_real_events = bool(len(ev_list) > 0 or (isinstance(raw_events, list) and len(raw_events) > 0))
        is_debug_prefix = inc_id.startswith(("INC-DEBUG", "SYNTHETIC-", "DEBUG-FIXTURE"))
        if is_debug_prefix and not has_real_events:
            return f"Zero-event synthetic debug fixture '{inc_id}' lacks real SIEM rawEvents telemetry."
        return None

    @classmethod
    def is_missing_evidence(cls, incident: Any, raw_payload: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
        """
        Distinguishes corrupt/empty payloads from metadata-only wrappers lacking telemetry.
        Returns: (reason_code, detail) or (None, None).
        """
        ev_list = getattr(incident, "events", None) or []
        src_ip = getattr(incident, "source_ip", None)
        if not raw_payload or (isinstance(raw_payload, dict) and len(raw_payload) == 0 and not src_ip and len(ev_list) == 0):
            return "CORRUPT_OR_EMPTY_PAYLOAD", "Incident telemetry payload is empty or corrupt."

        if isinstance(raw_payload, dict) and len(ev_list) == 0 and not src_ip:
            raw_events = raw_payload.get("rawEvents")
            non_meta_keys = [k for k in raw_payload.keys() if k not in ("metadata", "rawEventCount", "incidentId", "id")]
            if not non_meta_keys and not (isinstance(raw_events, list) and len(raw_events) > 0):
                return "MISSING_EVIDENCE", "Incident contains wrapper metadata only with zero normalized or raw event telemetry."
        return None, None

    @classmethod
    def is_containment_only_fp_note(
        cls,
        raw_resolution: Optional[str],
        cleared_reason: Optional[str] = None,
        analyst_comments: Optional[str] = None,
        cleared_user: Optional[str] = None,
    ) -> bool:
        """
        Flags False Positive closures whose rationale only states EDR process kill/block
        without benign/authorized justification or cleared_user attribution.
        """
        res_upper = str(raw_resolution or "").upper()
        if "FALSE POSITIVE" not in res_upper and "FALSE_POSITIVE" not in res_upper:
            return False
        note = " ".join([str(cleared_reason or ""), str(analyst_comments or "")]).lower().strip()
        benign_markers = ("legitimate", "benign", "authorized", "approved", "scheduled", "expected", "maintenance")
        containment_markers = ("kill process", "proccess is kiled", "process killed", "blocked", "quarantined")
        return bool(any(m in note for m in containment_markers) and not any(b in note for b in benign_markers) and not str(cleared_user or "").strip())

    @classmethod
    def compute_duplicate_cluster_key(
        cls,
        incident: Any,
        ground_truth: Any,
        adjudicated_label: str,
    ) -> Optional[str]:
        """
        Computes a conservative near-duplicate batch closure cluster key so batch-closed
        identical incident groups do not inflate sample counts or empirical confidence.
        """
        rule_key = str(getattr(incident, "rule_id", "") or getattr(incident, "event_type", "") or "").strip()
        cleared_epoch = getattr(ground_truth, "cleared_time_epoch", None)
        reason_norm = re.sub(r"\s+", " ", str(getattr(ground_truth, "cleared_reason", "") or "").strip().lower())
        if not rule_key or not adjudicated_label:
            return None
        if cleared_epoch and len(reason_norm) >= 8:
            raw_key = f"{rule_key}|{adjudicated_label}|epoch:{cleared_epoch}|{reason_norm}"
            return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]
        return None

    @classmethod
    def adjudicate_label(
        cls,
        raw_resolution: str,
        analyst_comments: Optional[str] = None,
        is_ml_generated: bool = False,
        provenance: str = "HISTORICAL_IMPORT",
        cleared_reason: Optional[str] = None,
        cleared_user: Optional[str] = None,
    ) -> Tuple[GroundTruthLabel, float, str]:
        """
        Adjudicates a raw incident resolution into a verified ground truth label.
        Returns: (label, reliability_score, rationale)
        """
        clean_res = str(raw_resolution or "").strip().upper()
        comments = str(analyst_comments or "").strip()
        reason_txt = str(cleared_reason or "").strip()
        user_txt = str(cleared_user or "").strip()
        combined_rationale = comments or reason_txt

        # If resolution was ML-generated or automated without human verification, mark UNVERIFIED
        is_automated = cls._is_automated_resolution_text(
            is_ml_generated=is_ml_generated,
            comments=comments,
            cleared_reason=reason_txt,
            cleared_user=user_txt,
            provenance=provenance,
        )
        if is_automated:
            return (
                GroundTruthLabel.UNVERIFIED,
                0.5,
                "Resolution was generated by previous ML model or automated rule without human adjudication.",
            )

        # Check for empty / unknown
        if not clean_res or clean_res in ("UNKNOWN", "OPEN", "IN_PROGRESS", "NEW"):
            return GroundTruthLabel.UNKNOWN, 0.0, "Incident is open or lacks resolution."

        # Incident closure alone without explicit TP/FP disposition is unverified
        if clean_res in ("CLOSED", "MANUALLY CLEARED", "AUTO CLEARED", "CLEARED", "RESOLVED", "CLOSE", "MITIGATED", "BLOCKED", "KILLED"):
            return (
                GroundTruthLabel.UNVERIFIED,
                0.5,
                f"Incident closure status '{raw_resolution}' alone without explicit TP/FP disposition cannot serve as ground truth.",
            )

        # Check for True Positive variants
        if any(term in clean_res for term in ("TRUE POSITIVE", "TRUE_POSITIVE", "MALICIOUS", "ATTACK", "INCIDENT")):
            if len(combined_rationale) >= 10:
                return GroundTruthLabel.VERIFIED_TP, 1.0, f"Verified TP with analyst rationale: {combined_rationale[:80]}"
            else:
                return GroundTruthLabel.VERIFIED_TP, 0.85, "TP indicated by analyst without extensive comments."

        # Check for False Positive variants
        if any(term in clean_res for term in ("FALSE POSITIVE", "FALSE_POSITIVE", "BENIGN", "AUTHORIZED", "EXPECTED", "NO_ACTION")):
            if len(combined_rationale) >= 10:
                return GroundTruthLabel.VERIFIED_FP, 1.0, f"Verified FP with analyst rationale: {combined_rationale[:80]}"
            else:
                return GroundTruthLabel.VERIFIED_FP, 0.85, "FP indicated by analyst without extensive comments."

        # Check for conflicting or ambiguous closure
        if any(term in clean_res for term in ("CONFLICT", "DISPUTED", "AMBIGUOUS", "INCONCLUSIVE")):
            return GroundTruthLabel.CONFLICTING, 0.3, "Conflicting analyst assessments logged."

        return GroundTruthLabel.UNVERIFIED, 0.5, f"Unrecognized resolution string: '{raw_resolution}'."

    @classmethod
    def assign_partition(cls, incident_id: str, salt: str = "ais_v2_1_partition") -> DatasetPartition:
        """
        Deterministically assigns an incident to an evaluation split via SHA-256:
        - 0-49: TRAIN (50%)
        - 50-69: TUNING (20%)
        - 70-84: CALIBRATION (15%)
        - 85-99: LOCKED_TEST (15%)
        """
        key = f"{salt}:{incident_id}".encode("utf-8")
        bucket = int(hashlib.sha256(key).hexdigest()[:8], 16) % 100

        if bucket < 50:
            return DatasetPartition.TRAIN
        elif bucket < 70:
            return DatasetPartition.TUNING
        elif bucket < 85:
            return DatasetPartition.CALIBRATION
        else:
            return DatasetPartition.LOCKED_TEST

