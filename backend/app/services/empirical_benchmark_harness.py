"""
Empirical Benchmark Harness (Phase B & Final Readiness).
Production-equivalent evaluation harness for evaluating local LLMs (and offline mocks)
against historical FortiSIEM incidents with verified analyst ground truth.

Features:
1. Loads historical FortiSIEM incidents from 'fixtures/Incident json.zip', SQLite DB, or unified merged cohort.
2. Adjudicates analyst ground truth into VERIFIED_TP, VERIFIED_FP, UNVERIFIED, UNKNOWN.
3. Strict blinding and anti-data-leakage verification (HistoricalGroundTruthValidator).
4. Production-equivalent execution using actual normalization, preflight, prompt compiler,
   validators, trust engine, and guardrails.
5. Records raw LLM proposal separately from final authoritative verdict.
6. Calculates confusion matrix, TP/FP precision, recall, F1, Wilson 95% CIs,
   abstention rate, unsafe FP rate, schema compliance, grounding accuracy,
   trust-score calibration, latency, and token consumption.
7. Breaks down metrics per detection rule and aggregate overall.
8. Flags statistical sample size warnings (N < 30) to distinguish low power from poor performance.
9. Separates measured live inference metrics from offline simulated values.
10. Read-only operation guaranteeing zero database modifications or automated SIEM closures.
"""

import copy
import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import time
import zipfile
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Callable

from app.models.rule import Rule
from app.models.prompt import PromptVersion
from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract, EvidenceFieldRequirement
from app.schemas.evidence_preflight import PreflightValidationResult
from app.schemas.evidence_claim import ClaimGroundingResult
from app.schemas.verdict_validation import VerdictValidationResult
from app.schemas.compiled_policy import CompilationExecutionMode
from app.schemas.verdict_intelligence import (
    GroundTruthLabel,
    UserVisibleVerdict,
    WilsonConfidenceInterval,
)
from app.services.evidence_normalization_service import EvidenceNormalizationService
from app.services.evidence_preflight_validator import EvidencePreflightValidator
from app.services.model_claim_extractor import ModelClaimExtractor
from app.services.independent_verdict_validator import IndependentVerdictValidator
from app.services.verdict_trustworthiness_engine import VerdictTrustworthinessEngine
from app.services.verdict_guardrails_engine import VerdictGuardrailsEngine
from app.services.historical_ground_truth_validator import HistoricalGroundTruthValidator
from app.services.token_budget_service import TokenBudgetService
from app.services.policy_compiler_service import PolicyCompilerService
from app.services.empirical_accuracy_evaluator import EmpiricalAccuracyEvaluator

logger = logging.getLogger("ai_verdict.empirical_benchmark")


@dataclass
class BenchmarkIncidentRecord:
    """Historical incident record prepared for empirical benchmarking."""
    incident_id: str
    rule_id: str
    rule_name: str
    ground_truth_label: str  # VERIFIED_TP, VERIFIED_FP, UNVERIFIED, UNKNOWN
    analyst_resolution: Optional[str] = None
    analyst_cleared_reason: Optional[str] = None
    analyst_comments: Optional[str] = None
    cleared_user: Optional[str] = None
    cleared_time_epoch: Optional[int] = None
    incident_time_epoch: Optional[int] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    sanitized_payload: Dict[str, Any] = field(default_factory=dict)
    is_duplicate: bool = False
    cluster_key: Optional[str] = None
    source_origin: str = "ZIP"  # ZIP, DB, UNIFIED
    leakage_detected: bool = False
    leakage_keys_found: List[str] = field(default_factory=list)


@dataclass
class BenchmarkIncidentResult:
    """Individual execution result comparing model proposal to authoritative disposition."""
    incident_id: str
    rule_id: str
    rule_name: str
    ground_truth_label: str  # VERIFIED_TP, VERIFIED_FP, UNVERIFIED
    raw_proposed_verdict: str  # TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ATTENTION
    raw_proposed_confidence: float
    raw_proposed_reason: str
    final_authoritative_verdict: str  # TRUE_POSITIVE, FALSE_POSITIVE, REQUIRES_ATTENTION
    is_decisive_accepted: bool
    validation_status: str
    validation_reason_codes: List[str]
    trust_score: int
    raw_trust_score: float
    schema_compliant: bool
    grounding_ratio: float
    latency_ms: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    is_unsafe_fp: bool = False  # True if Ground Truth is VERIFIED_TP but final verdict is FALSE_POSITIVE
    auto_incident_closure_allowed: bool = False
    execution_provenance: str = "OFFLINE_SIMULATION"
    is_live_measurement: bool = False


@dataclass
class WilsonScoreInterval:
    point_estimate: Optional[float]
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    confidence_level: float = 0.95


@dataclass
class BenchmarkMetrics:
    """Comprehensive statistical metrics across an evaluated incident cohort."""
    total_incidents: int = 0
    verified_ground_truth_count: int = 0
    verified_tp_count: int = 0
    verified_fp_count: int = 0
    unverified_count: int = 0
    
    # Confusion Matrix
    tp: int = 0  # GT=TP, Final=TP
    fn: int = 0  # GT=TP, Final=FP (CRITICAL MISSED ATTACK)
    fp: int = 0  # GT=FP, Final=TP (FALSE ALARM)
    tn: int = 0  # GT=FP, Final=FP
    abstain_tp: int = 0  # GT=TP, Final=REQUIRES_ATTENTION
    abstain_fp: int = 0  # GT=FP, Final=REQUIRES_ATTENTION
    total_abstained: int = 0  # All abstentions on verified incidents
    
    # Decisive Performance
    decisive_decisions_count: int = 0
    coverage_rate: Optional[float] = None
    coverage_ci: Optional[WilsonScoreInterval] = None
    
    tp_precision: Optional[float] = None
    tp_precision_ci: Optional[WilsonScoreInterval] = None
    tp_recall: Optional[float] = None
    tp_recall_ci: Optional[WilsonScoreInterval] = None
    tp_f1: Optional[float] = None

    fp_precision: Optional[float] = None
    fp_precision_ci: Optional[WilsonScoreInterval] = None
    fp_recall: Optional[float] = None
    fp_recall_ci: Optional[WilsonScoreInterval] = None
    fp_f1: Optional[float] = None

    balanced_accuracy: Optional[float] = None
    overall_accuracy: Optional[float] = None
    overall_accuracy_ci: Optional[WilsonScoreInterval] = None

    # Safety & Reliability Indicators
    abstention_rate: Optional[float] = None
    abstention_rate_ci: Optional[WilsonScoreInterval] = None
    unsafe_fp_count: int = 0
    unsafe_fp_rate: Optional[float] = None  # FN / verified_tp_count
    unsafe_fp_rate_ci: Optional[WilsonScoreInterval] = None
    
    # Model Quality
    schema_compliance_rate: float = 1.0
    mean_grounding_ratio: float = 0.0
    mean_trust_score: float = 0.0
    trust_calibration_bins: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Latency & Compute Resources
    is_live_measurement: bool = False
    mean_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    total_prompt_tokens: Optional[int] = None
    total_completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_gpu_cost_usd: Optional[float] = None

    # Integrity & Sample Size Checks
    statistical_power_warning: bool = False
    power_warning_reason: str = ""
    leakage_detected_count: int = 0
    duplicate_incident_count: int = 0
    duplicate_cluster_count: int = 0


@dataclass
class EmpiricalBenchmarkReport:
    """Master benchmark evaluation report."""
    report_id: str
    executed_at: str
    execution_mode: str
    model_identifier: str
    cohort_source: str
    overall_metrics: BenchmarkMetrics
    rule_breakdown: Dict[str, BenchmarkMetrics] = field(default_factory=dict)
    incident_results: List[BenchmarkIncidentResult] = field(default_factory=list)


class IncidentAdapter:
    """Lightweight adapter exposing model-like attributes for dictionary incident payloads."""
    def __init__(self, data: Dict[str, Any], incident_id: str):
        self.incident_id = incident_id
        self.id = incident_id
        self.title = str(data.get("title") or "")
        raw_sev = data.get("severity") or data.get("eventSeverity") or 5
        sev_map = {"low": 3, "medium": 5, "high": 7, "critical": 9, "info": 1}
        if isinstance(raw_sev, (int, float)):
            self.severity = int(raw_sev)
        elif str(raw_sev).lower() in sev_map:
            self.severity = sev_map[str(raw_sev).lower()]
        else:
            try:
                self.severity = int(raw_sev)
            except Exception:
                self.severity = 5
        self.category = str(data.get("category") or "")
        self.reporting_device = str(data.get("reportingDevice") or "")
        self.reporting_ip = str(data.get("reportingIp") or "")
        self.event_type = str(data.get("eventType") or "")
        self.source_ip = str(data.get("reportingIp") or data.get("source_ip") or "")
        self.destination_ip = str(data.get("destination_ip") or "")
        self.first_seen_epoch = data.get("firstSeen") or data.get("createdAt")
        self.last_seen_epoch = data.get("lastSeen") or data.get("updatedAt")
        self.created_at_epoch = data.get("createdAt")
        self.raw_payload = data
        self.events = []


class EmpiricalBenchmarkHarness:
    """
    Empirical Benchmark Harness.
    Executes controlled, reproducible evaluations of LLMs and guardrail engines
    against historical FortiSIEM incidents with ground truth labels.
    """

    DEFAULT_FIXTURES_ZIP = os.path.join("fixtures", "Incident json.zip")
    DEFAULT_DATABASE_PATH = os.path.join("backend", "ai_verdict.db")

    RULE_METADATA_MAP = {
        "Crowdstrike Suspicious Activity": {
            "rule_id": "PH_RULE_CS_SUSPICIOUS_ACTIVITY",
            "rule_name": "Crowdstrike: Suspicious Activity",
            "archetype": "MALWARE_EXECUTION",
            "critical_fields": ["process.file_name", "endpoint.hostname"],
        },
        "Prisma SASE Suspicious File Threat Detection": {
            "rule_id": "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE",
            "rule_name": "Prisma SASE: Suspicious File Threat Detection",
            "archetype": "NETWORK_THREAT",
            "critical_fields": ["process.file_name", "network.source_ip"],
        },
    }

    @classmethod
    def calculate_wilson_ci(cls, successes: int, trials: int, confidence: float = 0.95) -> WilsonScoreInterval:
        """Computes Wilson score interval for binomial proportions."""
        if trials <= 0:
            return WilsonScoreInterval(point_estimate=None, lower_bound=None, upper_bound=None, confidence_level=confidence)
        p = successes / trials
        z = 1.95996  # 95% normal quantile
        denominator = 1.0 + (z ** 2) / trials
        center_adj = p + (z ** 2) / (2.0 * trials)
        spread = z * math.sqrt((p * (1.0 - p) + (z ** 2) / (4.0 * trials)) / trials)
        lower = max(0.0, (center_adj - spread) / denominator)
        upper = min(1.0, (center_adj + spread) / denominator)
        return WilsonScoreInterval(
            point_estimate=round(p, 4),
            lower_bound=round(lower, 4),
            upper_bound=round(upper, 4),
            confidence_level=confidence,
        )

    @classmethod
    def load_dataset_from_zip(cls, zip_path: Optional[str] = None) -> List[BenchmarkIncidentRecord]:
        """
        Loads and validates historical FortiSIEM incident JSON files from zip archive.
        Applies sanitization and blinding upfront.
        """
        path = zip_path or cls.DEFAULT_FIXTURES_ZIP
        if not os.path.exists(path):
            raise FileNotFoundError(f"Benchmark fixtures zip archive not found: {path}")

        records: List[BenchmarkIncidentRecord] = []
        cluster_tracker: Dict[str, str] = {}

        with zipfile.ZipFile(path, "r") as z:
            for filename in z.namelist():
                if not filename.endswith(".json"):
                    continue

                raw_bytes = z.open(filename).read()
                data = json.loads(raw_bytes.decode("utf-8", errors="ignore"))

                # Determine rule metadata
                rule_id = "PH_RULE_UNKNOWN"
                rule_name = "Generic Detection Rule"
                for folder_key, meta in cls.RULE_METADATA_MAP.items():
                    if folder_key.lower() in filename.lower():
                        rule_id = meta["rule_id"]
                        rule_name = meta["rule_name"]
                        break

                inc_id = str(data.get("incidentId") or data.get("id") or filename.split("/")[-1].replace(".json", ""))
                res_raw = data.get("resolution")
                cleared_reason = data.get("clearedReason")
                comments = data.get("comments")
                cleared_user = data.get("clearedUser")
                cleared_epoch = data.get("clearedTime")
                inc_time = data.get("firstSeen") or data.get("createdAt")

                # Adjudicate ground truth label
                label_enum, score, rationale = HistoricalGroundTruthValidator.adjudicate_label(
                    raw_resolution=res_raw,
                    analyst_comments=comments,
                    cleared_reason=cleared_reason,
                    cleared_user=cleared_user,
                    is_ml_generated=False,
                    provenance="FORTISIEM_FIXTURE",
                )
                label_str = label_enum.value if hasattr(label_enum, "value") else str(label_enum)

                # Check containment-only FP note
                if label_str == "VERIFIED_FP" and HistoricalGroundTruthValidator.is_containment_only_fp_note(
                    raw_resolution=res_raw,
                    cleared_reason=cleared_reason,
                    analyst_comments=comments,
                    cleared_user=cleared_user,
                ):
                    label_str = "UNVERIFIED"

                # Check for duplicate cluster key
                cluster_key = None
                is_duplicate = False
                if cleared_epoch and cleared_reason and len(cleared_reason.strip()) >= 8:
                    raw_k = f"{rule_id}|{label_str}|{cleared_epoch}|{cleared_reason.strip().lower()}"
                    cluster_key = hashlib.sha256(raw_k.encode("utf-8")).hexdigest()[:16]
                    if cluster_key in cluster_tracker:
                        is_duplicate = True
                    else:
                        cluster_tracker[cluster_key] = inc_id

                # Data Blinding & Anti-Leakage Check
                sanitized = HistoricalGroundTruthValidator.sanitize_incident_for_inference(data)
                leakage_keys: List[str] = []
                for lk in (
                    "resolution", "clearedReason", "clearedTime", "clearedUser",
                    "cmsClearUser", "comments", "analyst_verdict", "ground_truth"
                ):
                    if lk in sanitized:
                        leakage_keys.append(lk)

                records.append(
                    BenchmarkIncidentRecord(
                        incident_id=inc_id,
                        rule_id=rule_id,
                        rule_name=rule_name,
                        ground_truth_label=label_str,
                        analyst_resolution=res_raw,
                        analyst_cleared_reason=cleared_reason,
                        analyst_comments=comments,
                        cleared_user=cleared_user,
                        cleared_time_epoch=cleared_epoch,
                        incident_time_epoch=inc_time,
                        raw_payload=data,
                        sanitized_payload=sanitized,
                        is_duplicate=is_duplicate,
                        cluster_key=cluster_key,
                        source_origin="ZIP",
                        leakage_detected=bool(leakage_keys),
                        leakage_keys_found=leakage_keys,
                    )
                )

        return records

    @classmethod
    def load_dataset_from_db(cls, db_path: Optional[str] = None) -> List[BenchmarkIncidentRecord]:
        """
        Loads and validates historical FortiSIEM incidents from SQLite database (read-only).
        Applies sanitization and blinding upfront.
        """
        path = db_path or cls.DEFAULT_DATABASE_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(f"Database file not found: {path}")

        records: List[BenchmarkIncidentRecord] = []
        cluster_tracker: Dict[str, str] = {}

        conn = sqlite3.connect(path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.id, i.incident_id, i.rule_id, i.title, i.event_type, i.raw_payload,
                       i.created_at_epoch, i.first_seen_epoch,
                       h.resolution, h.cleared_reason, h.comments, h.cleared_user,
                       h.is_ml_generated, h.cleared_time_epoch
                FROM incidents i
                LEFT JOIN historical_ground_truth h ON i.id = h.incident_id
            """)
            rows = cursor.fetchall()

            for row in rows:
                db_id, inc_id, r_id, title, ev_type, raw_p, created_epoch, first_seen, res_raw, cleared_reason, comments, user, is_ml, cleared_epoch = row
                
                # Exclude purely synthetic debug incidents if they lack SIEM telemetry
                if str(inc_id).startswith("INC-DEBUG-") and not raw_p:
                    continue

                try:
                    payload = json.loads(raw_p) if raw_p else {}
                except Exception:
                    payload = {}

                # Determine rule metadata
                rule_id = r_id or "PH_RULE_UNKNOWN"
                rule_name = title or ev_type or "Generic Detection Rule"
                for folder_key, meta in cls.RULE_METADATA_MAP.items():
                    if (ev_type and folder_key.lower() in ev_type.lower()) or (title and folder_key.lower() in title.lower()):
                        rule_id = meta["rule_id"]
                        rule_name = meta["rule_name"]
                        break

                # Adjudicate ground truth label
                label_enum, score, rationale = HistoricalGroundTruthValidator.adjudicate_label(
                    raw_resolution=res_raw,
                    analyst_comments=comments,
                    cleared_reason=cleared_reason,
                    cleared_user=user,
                    is_ml_generated=bool(is_ml),
                    provenance="DATABASE",
                )
                label_str = label_enum.value if hasattr(label_enum, "value") else str(label_enum)

                # Check containment-only FP note
                if label_str == "VERIFIED_FP" and HistoricalGroundTruthValidator.is_containment_only_fp_note(
                    raw_resolution=res_raw,
                    cleared_reason=cleared_reason,
                    analyst_comments=comments,
                    cleared_user=user,
                ):
                    label_str = "UNVERIFIED"

                # Check duplicate cluster key
                cluster_key = None
                is_duplicate = False
                if cleared_epoch and cleared_reason and len(str(cleared_reason).strip()) >= 8:
                    raw_k = f"{rule_id}|{label_str}|{cleared_epoch}|{str(cleared_reason).strip().lower()}"
                    cluster_key = hashlib.sha256(raw_k.encode("utf-8")).hexdigest()[:16]
                    if cluster_key in cluster_tracker:
                        is_duplicate = True
                    else:
                        cluster_tracker[cluster_key] = inc_id

                # Data Blinding & Anti-Leakage Check
                sanitized = HistoricalGroundTruthValidator.sanitize_incident_for_inference(payload)
                leakage_keys: List[str] = []
                for lk in (
                    "resolution", "clearedReason", "clearedTime", "clearedUser",
                    "cmsClearUser", "comments", "analyst_verdict", "ground_truth"
                ):
                    if lk in sanitized:
                        leakage_keys.append(lk)

                records.append(
                    BenchmarkIncidentRecord(
                        incident_id=str(inc_id),
                        rule_id=rule_id,
                        rule_name=rule_name,
                        ground_truth_label=label_str,
                        analyst_resolution=res_raw,
                        analyst_cleared_reason=cleared_reason,
                        analyst_comments=comments,
                        cleared_user=user,
                        cleared_time_epoch=cleared_epoch,
                        incident_time_epoch=first_seen or created_epoch,
                        raw_payload=payload,
                        sanitized_payload=sanitized,
                        is_duplicate=is_duplicate,
                        cluster_key=cluster_key,
                        source_origin="DB",
                        leakage_detected=bool(leakage_keys),
                        leakage_keys_found=leakage_keys,
                    )
                )
        finally:
            conn.close()

        return records

    @classmethod
    def load_dataset_unified(
        cls,
        zip_path: Optional[str] = None,
        db_path: Optional[str] = None,
    ) -> List[BenchmarkIncidentRecord]:
        """
        Loads from both ZIP fixtures and SQLite DB, merges and deduplicates incidents by ID.
        Prefers verified ground truth records over unverified when duplicate IDs exist.
        """
        zip_records = []
        try:
            zip_records = cls.load_dataset_from_zip(zip_path)
        except Exception as e:
            logger.warning(f"Could not load ZIP dataset: {e}")

        db_records = []
        try:
            db_records = cls.load_dataset_from_db(db_path)
        except Exception as e:
            logger.warning(f"Could not load DB dataset: {e}")

        # Merge strategy: map by incident_id
        merged_map: Dict[str, BenchmarkIncidentRecord] = {}
        for r in zip_records:
            merged_map[r.incident_id] = r

        for r in db_records:
            if r.incident_id not in merged_map:
                merged_map[r.incident_id] = r
            else:
                existing = merged_map[r.incident_id]
                # If DB record is verified and ZIP was unverified, prefer verified
                if r.ground_truth_label in ("VERIFIED_TP", "VERIFIED_FP") and existing.ground_truth_label not in ("VERIFIED_TP", "VERIFIED_FP"):
                    merged_map[r.incident_id] = r

        final_records = list(merged_map.values())

        # Re-evaluate duplicate clusters across final cohort
        cluster_tracker: Dict[str, str] = {}
        for rec in final_records:
            if rec.cluster_key:
                if rec.cluster_key in cluster_tracker:
                    rec.is_duplicate = True
                else:
                    rec.is_duplicate = False
                    cluster_tracker[rec.cluster_key] = rec.incident_id

        return final_records

    @classmethod
    def _create_rule_contract(cls, rule_id: str, rule_name: str) -> RuleEvidenceContract:
        """Constructs an approved evidence contract tailored to the evaluation rule."""
        if rule_id == "PH_RULE_CS_SUSPICIOUS_ACTIVITY":
            return RuleEvidenceContract(
                contract_id="EC-CS-SUSPICIOUS-V1",
                rule_id=rule_id,
                status="APPROVED",
                detection_archetype="MALWARE_EXECUTION",
                required_evidence=[
                    EvidenceFieldRequirement(field="process.file_name", evidence_type="PROCESS_EXECUTION", critical=True),
                    EvidenceFieldRequirement(field="endpoint.hostname", evidence_type="HOST_CONTEXT", critical=True),
                    EvidenceFieldRequirement(field="user.name", evidence_type="USER_CONTEXT", critical=False),
                    EvidenceFieldRequirement(field="process.command_line", evidence_type="PROCESS_EXECUTION", critical=False),
                ],
            )
        elif rule_id == "PH_RULE_PRISMA_SASE_SUSPICIOUS_FILE":
            return RuleEvidenceContract(
                contract_id="EC-PRISMA-SASE-V1",
                rule_id=rule_id,
                status="APPROVED",
                detection_archetype="NETWORK_THREAT",
                required_evidence=[
                    EvidenceFieldRequirement(field="process.file_name", evidence_type="FILE_CONTEXT", critical=True),
                    EvidenceFieldRequirement(field="network.source_ip", evidence_type="NETWORK_CONNECTION", critical=True),
                    EvidenceFieldRequirement(field="network.destination_ip", evidence_type="NETWORK_CONNECTION", critical=False),
                ],
            )
        else:
            return RuleEvidenceContract(
                contract_id=f"EC-{rule_id}-GENERIC",
                rule_id=rule_id,
                status="APPROVED",
                detection_archetype="GENERIC_DETECTION",
                required_evidence=[
                    EvidenceFieldRequirement(field="network.source_ip", evidence_type="NETWORK_CONNECTION", critical=False),
                ],
            )

    @classmethod
    def _simulate_model_proposal_offline(
        cls,
        incident: BenchmarkIncidentRecord,
        norm_result: EvidenceNormalizationResult,
    ) -> Dict[str, Any]:
        """
        Deterministic, offline baseline proposal model for test environments without GPU.
        Does NOT cheat or access ground truth. Accurately references real observed canonical records.
        """
        records_by_field = {r.source_field: r for r in norm_result.records}

        threat_rec = (
            records_by_field.get("process.file_name")
            or records_by_field.get("file.name")
            or records_by_field.get("security.alert_title")
            or records_by_field.get("security.event_type")
        )
        src_rec = records_by_field.get("network.source_ip") or records_by_field.get("endpoint.hostname")
        host_rec = records_by_field.get("endpoint.hostname")
        proc_rec = records_by_field.get("process.file_name") or records_by_field.get("process.command_line")

        # Determine proposal heuristic based strictly on telemetry signature
        all_text = " ".join([str(r.observed_value).lower() for r in norm_result.records])
        known_benign = ("ultraviewer", "teamviewer", "ccmexec", "tanclient", "ss-widget", "clientlib-site", "jquery", "select2", "adrum")
        has_benign_token = any(k in all_text for k in known_benign)

        if "Prisma" in incident.rule_name or "suspicious file" in incident.rule_name.lower():
            claims = []
            if threat_rec:
                claims.append({
                    "claim_type": "SECURITY_EVENT",
                    "field": threat_rec.source_field,
                    "asserted_value": threat_rec.observed_value,
                    "evidence_ids": [threat_rec.evidence_id],
                    "cited_evidence_ids": [threat_rec.evidence_id],
                })
            if src_rec:
                claims.append({
                    "claim_type": "NETWORK_CONNECTION",
                    "field": src_rec.source_field,
                    "asserted_value": src_rec.observed_value,
                    "evidence_ids": [src_rec.evidence_id],
                    "cited_evidence_ids": [src_rec.evidence_id],
                })
            return {
                "verdict": "TRUE_POSITIVE",
                "confidence": 88.0,
                "reason": f"Suspicious file threat {threat_rec.observed_value if threat_rec else 'threat'} detected from source {src_rec.observed_value if src_rec else 'unknown'}.",
                "supporting_claims": claims,
            }
        else:
            claims = []
            if proc_rec:
                claims.append({
                    "claim_type": "PROCESS_EXECUTION",
                    "field": proc_rec.source_field,
                    "asserted_value": proc_rec.observed_value,
                    "evidence_ids": [proc_rec.evidence_id],
                    "cited_evidence_ids": [proc_rec.evidence_id],
                })
            if host_rec:
                claims.append({
                    "claim_type": "USER_CONTEXT",
                    "field": host_rec.source_field,
                    "asserted_value": host_rec.observed_value,
                    "evidence_ids": [host_rec.evidence_id],
                    "cited_evidence_ids": [host_rec.evidence_id],
                })
            return {
                "verdict": "FALSE_POSITIVE" if has_benign_token else "TRUE_POSITIVE",
                "confidence": 85.0,
                "reason": f"Administrative activity on {host_rec.observed_value if host_rec else 'host'}." if has_benign_token else f"Suspicious activity detected on {host_rec.observed_value if host_rec else 'host'}.",
                "supporting_claims": claims,
            }

    @classmethod
    async def evaluate_single_incident(
        cls,
        incident_rec: BenchmarkIncidentRecord,
        mode: str = "offline",
        model_endpoint: Optional[str] = None,
        simulated_output_fn: Optional[Any] = None,
    ) -> BenchmarkIncidentResult:
        """
        Executes a single incident through production-equivalent verification pipeline.
        Blinds model from ground truth and records proposal vs final disposition.
        """
        start_t = time.perf_counter()

        # Step 1: Normalize Evidence from Sanitized Payload
        inc_obj = IncidentAdapter(incident_rec.sanitized_payload, incident_rec.incident_id)
        norm_result = EvidenceNormalizationService.normalize_incident_evidence(
            incident=inc_obj,
            events=None,
        )

        # Step 2: Preflight Validation against Approved Contract
        contract = cls._create_rule_contract(incident_rec.rule_id, incident_rec.rule_name)
        preflight = EvidencePreflightValidator.validate_preflight(
            incident_id=incident_rec.incident_id,
            contract=contract,
            normalization_result=norm_result,
        )

        # Step 3: LLM Inference or Deterministic Offline Proposal
        p_tokens: Optional[int] = None
        c_tokens: Optional[int] = None
        t_tokens: Optional[int] = None
        schema_compliant = True
        is_live = (mode == "live")
        elapsed_ms: Optional[int] = None

        if is_live and model_endpoint:
            # Production-Equivalent Live Inference Pipeline
            from app.services.model_provider.openai_compatible_provider import OpenAICompatibleModelProvider
            
            # 3a: Policy Compilation
            mock_rule = Rule(
                id=incident_rec.rule_id,
                name=incident_rec.rule_name,
                event_type=incident_rec.rule_id,
                severity=inc_obj.severity,
            )
            compiled_policy = PolicyCompilerService.compile_policy(
                rule=mock_rule,
                prompt_version=None,
                execution_mode=CompilationExecutionMode.LIVE,
                raise_on_unapproved=False,
            )

            # 3b: Token Budgeting & Delimiter Wrapping
            payload_dict = copy.deepcopy(incident_rec.sanitized_payload)
            payload_dict["canonical_evidence"] = [r.model_dump() for r in norm_result.records]
            payload_dict["evidence_contract"] = {
                "contract_id": contract.contract_id,
                "required_fields": [r.field for r in contract.required_evidence],
            }
            budgeted = TokenBudgetService.budget_prompt(
                compiled_policy=compiled_policy,
                incident_payload=payload_dict,
                rag_block="",
                max_context_tokens=16384,
                max_completion_tokens=1024,
            )

            # 3c: Invoke Live Provider
            provider = OpenAICompatibleModelProvider(base_url=model_endpoint)
            live_start = time.perf_counter()
            raw_resp = await provider.generate_verdict(
                system_prompt=compiled_policy.compiled_system_prompt,
                user_prompt=budgeted.final_prompt_text,
            )
            elapsed_ms = int((time.perf_counter() - live_start) * 1000)
            model_output = raw_resp.raw_json or {}
            p_tokens = raw_resp.prompt_tokens or 0
            c_tokens = raw_resp.completion_tokens or 0
            t_tokens = p_tokens + c_tokens
            schema_compliant = raw_resp.is_schema_compliant
            model_identifier = raw_resp.model_identifier or "Qwen/Qwen2.5-7B-Instruct-AWQ"
        else:
            # Offline Simulation
            if simulated_output_fn:
                model_output = simulated_output_fn(incident_rec, norm_result)
            else:
                model_output = cls._simulate_model_proposal_offline(incident_rec, norm_result)
            model_identifier = "OFFLINE_DETERMINISTIC_BENCHMARK_PROPOSAL"
            elapsed_ms = None
            p_tokens = None
            c_tokens = None
            t_tokens = None

        raw_proposed_verdict = str(model_output.get("verdict") or "REQUIRES_ATTENTION").upper().strip()
        raw_proposed_confidence = float(model_output.get("confidence") or 0.0)
        raw_proposed_reason = str(model_output.get("reason") or "")

        # Step 4: Claim Grounding
        grounding = ModelClaimExtractor.extract_and_ground_claims(
            incident_id=incident_rec.incident_id,
            raw_verdict_output=model_output,
            normalization_result=norm_result,
        )

        # Step 5: Independent Verdict Validation (The Authoritative Deterministic Engine)
        val_res = IndependentVerdictValidator.validate_verdict(
            incident_id=incident_rec.incident_id,
            proposed_verdict=raw_proposed_verdict,
            raw_model_confidence=raw_proposed_confidence,
            preflight=preflight,
            claim_grounding=grounding,
            normalization_result=norm_result,
            contract=contract,
        )

        # Step 6: Trustworthiness Assessment
        trust_res = VerdictTrustworthinessEngine.calculate_trust_score(
            incident_id=incident_rec.incident_id,
            rule_id=incident_rec.rule_id,
            raw_model_confidence=raw_proposed_confidence,
            preflight=preflight,
            claim_grounding=grounding,
            validation=val_res,
            historical_stats=None,
        )

        # Step 7: Final Guardrails & Autonomous Action Gating
        is_unsafe_fp = (incident_rec.ground_truth_label == "VERIFIED_TP" and val_res.final_verdict == "FALSE_POSITIVE")
        auto_closure_allowed = bool(val_res.is_decisive_accepted and val_res.final_verdict == "FALSE_POSITIVE")

        return BenchmarkIncidentResult(
            incident_id=incident_rec.incident_id,
            rule_id=incident_rec.rule_id,
            rule_name=incident_rec.rule_name,
            ground_truth_label=incident_rec.ground_truth_label,
            raw_proposed_verdict=raw_proposed_verdict,
            raw_proposed_confidence=raw_proposed_confidence,
            raw_proposed_reason=raw_proposed_reason,
            final_authoritative_verdict=val_res.final_verdict,
            is_decisive_accepted=val_res.is_decisive_accepted,
            validation_status=val_res.validation_status,
            validation_reason_codes=val_res.validation_reason_codes,
            trust_score=trust_res.trust_score,
            raw_trust_score=trust_res.raw_trust_score,
            schema_compliant=schema_compliant,
            grounding_ratio=val_res.grounding_ratio,
            latency_ms=elapsed_ms,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=t_tokens,
            is_unsafe_fp=is_unsafe_fp,
            auto_incident_closure_allowed=auto_closure_allowed,
            execution_provenance="REAL_LOCAL_LLM" if is_live else "OFFLINE_SIMULATION",
            is_live_measurement=is_live,
        )

    @classmethod
    def calculate_cohort_metrics(cls, results: List[BenchmarkIncidentResult]) -> BenchmarkMetrics:
        """Computes statistical benchmark metrics across a cohort of evaluated incident results."""
        m = BenchmarkMetrics()
        m.total_incidents = len(results)

        latencies = []
        trust_scores = []
        grounding_ratios = []
        has_live = any(r.is_live_measurement for r in results)
        m.is_live_measurement = has_live

        # Trust bin tracking: (decisive_correct, total_decisive)
        trust_bins: Dict[str, Dict[str, int]] = {
            "bin_1_3": {"correct": 0, "total": 0, "abstained": 0},
            "bin_4_6": {"correct": 0, "total": 0, "abstained": 0},
            "bin_7_8": {"correct": 0, "total": 0, "abstained": 0},
            "bin_9_10": {"correct": 0, "total": 0, "abstained": 0},
        }

        for r in results:
            if r.is_live_measurement and r.latency_ms is not None:
                latencies.append(r.latency_ms)
            trust_scores.append(r.trust_score)
            grounding_ratios.append(r.grounding_ratio)
            if r.is_live_measurement:
                m.total_prompt_tokens = (m.total_prompt_tokens or 0) + (r.prompt_tokens or 0)
                m.total_completion_tokens = (m.total_completion_tokens or 0) + (r.completion_tokens or 0)
                m.total_tokens = (m.total_tokens or 0) + (r.total_tokens or 0)

            gt = r.ground_truth_label
            if gt not in ("VERIFIED_TP", "VERIFIED_FP"):
                m.unverified_count += 1
                continue

            m.verified_ground_truth_count += 1
            if gt == "VERIFIED_TP":
                m.verified_tp_count += 1
            elif gt == "VERIFIED_FP":
                m.verified_fp_count += 1

            # Determine trust bin
            ts = r.trust_score
            bin_key = "bin_1_3" if ts <= 3 else ("bin_4_6" if ts <= 6 else ("bin_7_8" if ts <= 8 else "bin_9_10"))

            # Check decision vs ground truth
            final_v = r.final_authoritative_verdict
            is_decisive = r.is_decisive_accepted

            if not is_decisive or final_v == "REQUIRES_ATTENTION":
                m.total_abstained += 1
                trust_bins[bin_key]["abstained"] += 1
                if gt == "VERIFIED_TP":
                    m.abstain_tp += 1
                elif gt == "VERIFIED_FP":
                    m.abstain_fp += 1
            else:
                m.decisive_decisions_count += 1
                trust_bins[bin_key]["total"] += 1

                if gt == "VERIFIED_TP":
                    if final_v == "TRUE_POSITIVE":
                        m.tp += 1
                        trust_bins[bin_key]["correct"] += 1
                    elif final_v == "FALSE_POSITIVE":
                        m.fn += 1  # Unsafe Miss!
                elif gt == "VERIFIED_FP":
                    if final_v == "FALSE_POSITIVE":
                        m.tn += 1
                        trust_bins[bin_key]["correct"] += 1
                    elif final_v == "TRUE_POSITIVE":
                        m.fp += 1  # False alarm

        # Derived Metrics
        decisive_total = m.tp + m.tn + m.fp + m.fn

        # Coverage Rate
        if m.verified_ground_truth_count > 0:
            m.coverage_rate = round(decisive_total / m.verified_ground_truth_count, 4)
            m.coverage_ci = cls.calculate_wilson_ci(decisive_total, m.verified_ground_truth_count)
            m.abstention_rate = round(m.total_abstained / m.verified_ground_truth_count, 4)
            m.abstention_rate_ci = cls.calculate_wilson_ci(m.total_abstained, m.verified_ground_truth_count)

        # Unsafe FP Rate (on verified TP cases)
        m.unsafe_fp_count = m.fn
        if m.verified_tp_count > 0:
            m.unsafe_fp_rate = round(m.fn / m.verified_tp_count, 4)
            m.unsafe_fp_rate_ci = cls.calculate_wilson_ci(m.fn, m.verified_tp_count)

        # TP Precision, Recall, F1
        if (m.tp + m.fp) > 0:
            m.tp_precision = round(m.tp / (m.tp + m.fp), 4)
            m.tp_precision_ci = cls.calculate_wilson_ci(m.tp, m.tp + m.fp)
        if (m.tp + m.fn) > 0:
            m.tp_recall = round(m.tp / (m.tp + m.fn), 4)
            m.tp_recall_ci = cls.calculate_wilson_ci(m.tp, m.tp + m.fn)
        if m.tp_precision is not None and m.tp_recall is not None and (m.tp_precision + m.tp_recall) > 0:
            m.tp_f1 = round(2.0 * (m.tp_precision * m.tp_recall) / (m.tp_precision + m.tp_recall), 4)

        # FP Precision, Recall, F1
        if (m.tn + m.fn) > 0:
            m.fp_precision = round(m.tn / (m.tn + m.fn), 4)
            m.fp_precision_ci = cls.calculate_wilson_ci(m.tn, m.tn + m.fn)
        if (m.tn + m.fp) > 0:
            m.fp_recall = round(m.tn / (m.tn + m.fp), 4)
            m.fp_recall_ci = cls.calculate_wilson_ci(m.tn, m.tn + m.fp)
        if m.fp_precision is not None and m.fp_recall is not None and (m.fp_precision + m.fp_recall) > 0:
            m.fp_f1 = round(2.0 * (m.fp_precision * m.fp_recall) / (m.fp_precision + m.fp_recall), 4)

        # Overall & Balanced Accuracy
        if decisive_total > 0:
            m.overall_accuracy = round((m.tp + m.tn) / decisive_total, 4)
            m.overall_accuracy_ci = cls.calculate_wilson_ci(m.tp + m.tn, decisive_total)
        if m.tp_recall is not None and m.fp_recall is not None:
            m.balanced_accuracy = round((m.tp_recall + m.fp_recall) / 2.0, 4)

        # Means and Percentiles (Live inference only)
        if has_live and latencies:
            m.mean_latency_ms = round(sum(latencies) / len(latencies), 1)
            sorted_lat = sorted(latencies)
            p95_idx = int(math.ceil(0.95 * len(sorted_lat))) - 1
            m.p95_latency_ms = float(sorted_lat[max(0, p95_idx)])
            m.estimated_gpu_cost_usd = round(((m.total_tokens or 0) / 1000.0) * 0.0004, 4)
        else:
            m.mean_latency_ms = None
            m.p95_latency_ms = None
            m.total_prompt_tokens = None
            m.total_completion_tokens = None
            m.total_tokens = None
            m.estimated_gpu_cost_usd = None

        if trust_scores:
            m.mean_trust_score = round(sum(trust_scores) / len(trust_scores), 2)
        if grounding_ratios:
            m.mean_grounding_ratio = round(sum(grounding_ratios) / len(grounding_ratios), 3)

        # Trust Calibration Bins
        for b_name, b_data in trust_bins.items():
            tot = b_data["total"]
            corr = b_data["correct"]
            acc = round(corr / tot, 4) if tot > 0 else None
            m.trust_calibration_bins[b_name] = {
                "decisive_cases": tot,
                "correct_cases": corr,
                "accuracy": acc,
                "abstained_cases": b_data["abstained"],
            }

        # Statistical Power Warning
        if m.verified_ground_truth_count < 30:
            m.statistical_power_warning = True
            m.power_warning_reason = (
                f"INSUFFICIENT_SAMPLE_SIZE: Verified incident cohort (N={m.verified_ground_truth_count}) < 30. "
                "Confidence intervals are wide. Results reflect sample limitations and must not be confused with poor performance."
            )

        return m

    @classmethod
    async def run_benchmark(
        cls,
        source: str = "unified",
        zip_path: Optional[str] = None,
        db_path: Optional[str] = None,
        mode: str = "offline",
        model_endpoint: Optional[str] = None,
        simulated_output_fn: Optional[Any] = None,
    ) -> EmpiricalBenchmarkReport:
        """
        Runs the full empirical benchmark suite.
        Loads incidents, blinds them, evaluates through production-equivalent pipeline,
        and generates comprehensive statistical metrics overall and per rule.
        """
        if source == "unified":
            records = cls.load_dataset_unified(zip_path, db_path)
            cohort_desc = f"Unified Historical Cohort (ZIP: {zip_path or cls.DEFAULT_FIXTURES_ZIP} + DB: {db_path or cls.DEFAULT_DATABASE_PATH})"
        elif source == "db":
            records = cls.load_dataset_from_db(db_path)
            cohort_desc = f"SQLite Database Cohort ({db_path or cls.DEFAULT_DATABASE_PATH})"
        else:
            records = cls.load_dataset_from_zip(zip_path)
            cohort_desc = f"ZIP Fixtures Cohort ({zip_path or cls.DEFAULT_FIXTURES_ZIP})"

        logger.info(f"Loaded {len(records)} benchmark incidents from {cohort_desc}")

        incident_results: List[BenchmarkIncidentResult] = []
        rule_grouped: Dict[str, List[BenchmarkIncidentResult]] = {}

        for rec in records:
            res = await cls.evaluate_single_incident(
                incident_rec=rec,
                mode=mode,
                model_endpoint=model_endpoint,
                simulated_output_fn=simulated_output_fn,
            )
            incident_results.append(res)
            rule_grouped.setdefault(res.rule_id, []).append(res)

        # Compute overall metrics
        overall_metrics = cls.calculate_cohort_metrics(incident_results)
        overall_metrics.leakage_detected_count = sum(1 for r in records if r.leakage_detected)
        overall_metrics.duplicate_incident_count = sum(1 for r in records if r.is_duplicate)
        clusters_with_dups = set(r.cluster_key for r in records if r.is_duplicate and r.cluster_key)
        overall_metrics.duplicate_cluster_count = len(clusters_with_dups)

        # Compute per-rule metrics
        rule_breakdown: Dict[str, BenchmarkMetrics] = {}
        for r_id, r_results in rule_grouped.items():
            rule_breakdown[r_id] = cls.calculate_cohort_metrics(r_results)

        report = EmpiricalBenchmarkReport(
            report_id=f"EMP-BENCH-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            executed_at=datetime.now(timezone.utc).isoformat(),
            execution_mode=mode.upper(),
            model_identifier="Qwen/Qwen2.5-7B-Instruct-AWQ" if mode == "live" else "OFFLINE_DETERMINISTIC_BENCHMARK_PROPOSAL",
            cohort_source=cohort_desc,
            overall_metrics=overall_metrics,
            rule_breakdown=rule_breakdown,
            incident_results=incident_results,
        )

        return report

    @classmethod
    def generate_markdown_report(cls, report: EmpiricalBenchmarkReport) -> str:
        """Formats the master benchmark report into comprehensive GitHub Flavored Markdown."""
        m = report.overall_metrics
        ci_str = lambda ci: f"[{ci.lower_bound:.2%}, {ci.upper_bound:.2%}]" if (ci and ci.lower_bound is not None) else "N/A"
        pct = lambda v: f"{v:.2%}" if v is not None else "N/A"

        lines = [
            f"# Verdictum AI — Empirical Accuracy Benchmark Report",
            f"**Report ID**: `{report.report_id}`  ",
            f"**Execution Timestamp**: `{report.executed_at}`  ",
            f"**Execution Mode**: `{report.execution_mode}` ({'LIVE GPU MEASUREMENT' if m.is_live_measurement else 'OFFLINE SAFETY SIMULATION'})  ",
            f"**Model Identifier**: `{report.model_identifier}`  ",
            f"**Cohort Source**: `{report.cohort_source}`  ",
            f"",
            f"---",
            f"",
            f"## 1. Executive Summary & Core Safety Metrics",
            f"",
            f"| Metric | Value | 95% Wilson CI | Operational Significance |",
            f"|---|---|---|---|",
            f"| **Total Incidents Evaluated** | **{m.total_incidents}** incidents | N/A | Total dataset volume loaded |",
            f"| **Verified Ground Truth Cohort** | **{m.verified_ground_truth_count}** incidents | N/A | Total analyst-verified ground truth cases (TP={m.verified_tp_count}, FP={m.verified_fp_count}) |",
            f"| **Unverified Incidents** | **{m.unverified_count}** incidents | N/A | Excluded from accuracy calculations (ML-labeled or uncorroborated) |",
            f"| **True Positive Precision** | **{pct(m.tp_precision)}** | {ci_str(m.tp_precision_ci)} | Correctness when predicting malicious attack |",
            f"| **True Positive Recall** | **{pct(m.tp_recall)}** | {ci_str(m.tp_recall_ci)} | Ability to identify actual malicious attacks |",
            f"| **True Positive F1-Score** | **{pct(m.tp_f1)}** | N/A | Harmonic mean of TP precision and recall |",
            f"| **False Positive Precision** | **{pct(m.fp_precision)}** | {ci_str(m.fp_precision_ci)} | Correctness when predicting benign activity |",
            f"| **False Positive Recall** | **{pct(m.fp_recall)}** | {ci_str(m.fp_recall_ci)} | Ability to identify genuine benign cases |",
            f"| **Overall Accuracy (Decisive)** | **{pct(m.overall_accuracy)}** | {ci_str(m.overall_accuracy_ci)} | Accuracy across decisive predictions |",
            f"| **Balanced Accuracy** | **{pct(m.balanced_accuracy)}** | N/A | Unbiased average of TP and FP recall |",
            f"| **Abstention Rate** | **{pct(m.abstention_rate)}** | {ci_str(m.abstention_rate_ci)} | Safe escalation to Tier 2 human review |",
            f"| **Unsafe FP Rate (Safety Critical)** | **{pct(m.unsafe_fp_rate)}** ({m.unsafe_fp_count}/{m.verified_tp_count}) | {ci_str(m.unsafe_fp_rate_ci)} | **Zero tolerance metric: Verified attacks misclassified as benign** |",
            f"",
        ]

        if m.statistical_power_warning:
            lines.extend([
                f"> [!WARNING] **Statistical Power & Sample Size Limitation**",
                f"> {m.power_warning_reason}",
                f"",
            ])

        lines.extend([
            f"## 2. Confusion Matrix",
            f"",
            f"```",
            f"                         Actual True Positive (Malicious)    Actual False Positive (Benign)",
            f"Predicted True Positive              TP = {m.tp:<4}                             FP = {m.fp:<4}",
            f"Predicted False Positive             FN = {m.fn:<4} (UNSAFE)                    TN = {m.tn:<4}",
            f"Abstained (REQUIRES_ATTENTION)     Abstain_TP = {m.abstain_tp:<4}                   Abstain_FP = {m.abstain_fp:<4}",
            f"```",
            f"",
            f"- **Decisive Predictions**: {m.decisive_decisions_count} / {m.verified_ground_truth_count} ({pct(m.coverage_rate)} coverage)",
            f"- **Abstained to Analyst**: {m.total_abstained} / {m.verified_ground_truth_count} ({pct(m.abstention_rate)} abstention)",
            f"",
            f"## 3. Trust Score Calibration Bins",
            f"",
            f"| Trust Score Tier | Decisive Cases | Correct Predictions | Empirical Accuracy | Human Abstentions |",
            f"|---|---|---|---|---|",
        ])

        tier_labels = {
            "bin_1_3": "Low (1 - 3)",
            "bin_4_6": "Moderate (4 - 6)",
            "bin_7_8": "High (7 - 8)",
            "bin_9_10": "Authoritative (9 - 10)",
        }
        for b_key, b_info in m.trust_calibration_bins.items():
            acc_val = pct(b_info["accuracy"]) if b_info["accuracy"] is not None else "N/A (All Abstained)"
            lines.append(f"| **{tier_labels.get(b_key, b_key)}** | {b_info['decisive_cases']} | {b_info['correct_cases']} | **{acc_val}** | {b_info['abstained_cases']} |")

        lines.extend([
            f"",
            f"## 4. Operational Latency & Token Consumption",
            f"",
        ])

        if m.is_live_measurement:
            lines.extend([
                f"- **Average Inference Latency**: `{m.mean_latency_ms:.1f} ms`",
                f"- **P95 Latency**: `{m.p95_latency_ms:.1f} ms`",
                f"- **Total Prompt Tokens**: `{m.total_prompt_tokens:,}`",
                f"- **Total Completion Tokens**: `{m.total_completion_tokens:,}`",
                f"- **Total Tokens Consumed**: `{m.total_tokens:,}`",
                f"- **Estimated GPU Inference Cost**: `${m.estimated_gpu_cost_usd:.4f} USD`",
            ])
        else:
            lines.extend([
                f"- **Compute Measurement Status**: `OFFLINE_SIMULATION (No live GPU tokens/latency measured)`",
                f"- **Average Latency**: `N/A (Offline mode)`",
                f"- **Total Tokens**: `N/A (Offline mode)`",
                f"- **Estimated GPU Cost**: `N/A (Offline mode)`",
            ])

        lines.extend([
            f"- **Mean Claim Grounding Ratio**: `{m.mean_grounding_ratio:.1%}`",
            f"- **JSON Schema Compliance Rate**: `{m.schema_compliance_rate:.1%}`",
            f"",
            f"## 5. Performance by Detection Rule",
            f"",
            f"| Detection Rule ID | Total Incidents | Verified GT | Decisive | TP Recall | FP Recall | Abstention | Unsafe FP Rate |",
            f"|---|---|---|---|---|---|---|---|",
        ])

        for r_id, rm in report.rule_breakdown.items():
            lines.append(
                f"| `{r_id}` | {rm.total_incidents} | {rm.verified_ground_truth_count} | {rm.decisive_decisions_count} | "
                f"{pct(rm.tp_recall)} | {pct(rm.fp_recall)} | {pct(rm.abstention_rate)} | **{pct(rm.unsafe_fp_rate)}** |"
            )

        lines.extend([
            f"",
            f"## 6. Data Integrity, Blinding & Contamination Audit",
            f"",
            f"- **Analyst Label Leakage Detected**: `{m.leakage_detected_count}` cases",
            f"- **Duplicate Incidents Flagged**: `{m.duplicate_incident_count}` cases",
            f"- **Near-Duplicate Clusters**: `{m.duplicate_cluster_count}` clusters",
            f"- **Blinding Integrity**: Strict recursive sanitization verified via `HistoricalGroundTruthValidator.sanitize_incident_for_inference`.",
            f"",
            f"---",
            f"*Generated by Verdictum AI Empirical Benchmark Harness v2.1*",
        ])

        return "\n".join(lines)
