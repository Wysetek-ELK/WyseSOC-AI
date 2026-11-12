"""
Evidence-Aware Compaction, Deduplication, Relevance Selection & Chunking Service.

Solves CONTEXT_WINDOW_EXCEEDED on large FortiSIEM / EDR incidents without
dropping critical security evidence, violating policy directives, or producing
unsupported TP/FP verdicts.

Preserves mandatory policy directives, evidence contract integrity,
cryptographic provenance, and cross-chunk evidence coverage.
"""

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.schemas.canonical_evidence import CanonicalEvidenceRecord
from app.services.tokenizer_service import ModelTokenizerService

logger = logging.getLogger(__name__)


class EvidenceCompactionService:
    """
    Evidence Compaction, Deduplication & Relevance Engine.
    """

    @classmethod
    def compact_and_deduplicate(
        cls,
        records: List[CanonicalEvidenceRecord],
        contract_required_fields: Optional[List[str]] = None,
        rule_pattern_logic: Optional[str] = None,
        max_evidence_budget_tokens: int = 1500,
        enable_chunking: bool = False,
    ) -> Dict[str, Any]:
        """
        Processes a raw list of canonical evidence records through:
        1. Repetitive value and tuple deduplication
        2. Timestamp range aggregation (replaces hundreds of raw timestamps)
        3. Raw syslog template clustering (replaces redundant raw log lines)
        4. Relevance selection (strictly prioritizing contract & detection criteria)
        5. Deterministic chunking when distinct evidence exceeds the budget

        Returns a dictionary containing:
        - 'compacted_records': List[Dict[str, Any]] (the final bounded evidence records)
        - 'all_dedup_canonical_records': List[CanonicalEvidenceRecord] (for validator lookup)
        - 'is_chunked': bool
        - 'chunk_index': int
        - 'total_chunks': int
        - 'all_chunks': List[List[Dict[str, Any]]]
        - 'total_raw_records': int
        - 'deduplicated_record_count': int
        - 'estimated_tokens': int
        - 'deduplication_ratio': float
        """
        contract_fields: Set[str] = set(
            f.lower().strip() for f in (contract_required_fields or [])
        )
        pattern_text = (rule_pattern_logic or "").lower()

        if not records:
            return {
                "compacted_records": [],
                "all_dedup_canonical_records": [],
                "is_chunked": False,
                "chunk_index": 1,
                "total_chunks": 1,
                "all_chunks": [[]],
                "total_raw_records": 0,
                "deduplicated_record_count": 0,
                "estimated_tokens": 0,
                "deduplication_ratio": 1.0,
            }

        total_raw_count = len(records)
        inc_id = records[0].incident_id if records else "INC"
        sys_src = records[0].source_system if records else "FortiSIEM"

        # -------------------------------------------------------------
        # STEP 1: Timestamp Range Aggregation & Collapse
        # -------------------------------------------------------------
        timestamp_records: List[CanonicalEvidenceRecord] = []
        non_timestamp_records: List[CanonicalEvidenceRecord] = []

        for r in records:
            if r.source_field.lower() in ("event.timestamp", "event.time", "event_time", "timestamp"):
                timestamp_records.append(r)
            else:
                non_timestamp_records.append(r)

        aggregated_records: List[CanonicalEvidenceRecord] = []
        extra_canonical_for_validator: List[CanonicalEvidenceRecord] = list(records)

        if len(timestamp_records) > 3:
            valid_times = []
            for tr in timestamp_records:
                val = str(tr.observed_value).strip()
                if val:
                    valid_times.append(val)
            valid_times.sort()

            earliest = valid_times[0] if valid_times else "UNKNOWN"
            latest = valid_times[-1] if valid_times else earliest
            t_count = len(timestamp_records)

            primary_rec = CanonicalEvidenceRecord(
                evidence_id=f"EV-{inc_id}-PRIMARY-trigger_timestamp",
                incident_id=inc_id,
                source_system=sys_src,
                source_event_id="PRIMARY",
                source_field="event.timestamp",
                observed_value=earliest,
                observed_at=earliest,
                evidence_type="SECURITY_EVENT",
                availability="AVAILABLE",
                provenance_status="SOURCE_RECORDED",
                integrity_digest=CanonicalEvidenceRecord.generate_digest("event.timestamp", earliest),
            )
            aggregated_records.append(primary_rec)
            extra_canonical_for_validator.append(primary_rec)

            range_val = f"{earliest} to {latest} ({t_count} event timestamps)"
            range_rec = CanonicalEvidenceRecord(
                evidence_id=f"EV-{inc_id}-SUMMARY-time_window",
                incident_id=inc_id,
                source_system=sys_src,
                source_event_id="SUMMARY",
                source_field="event.time_range",
                observed_value=range_val,
                observed_at=earliest,
                evidence_type="SECURITY_EVENT",
                availability="AVAILABLE",
                provenance_status="SOURCE_RECORDED",
                integrity_digest=CanonicalEvidenceRecord.generate_digest("event.time_range", range_val),
            )
            aggregated_records.append(range_rec)
            extra_canonical_for_validator.append(range_rec)
        else:
            aggregated_records.extend(timestamp_records)

        # -------------------------------------------------------------
        # STEP 2: Raw Syslog Template Clustering
        # -------------------------------------------------------------
        raw_log_records: List[CanonicalEvidenceRecord] = []
        other_records: List[CanonicalEvidenceRecord] = []

        for r in non_timestamp_records:
            if r.source_field.lower() in ("security.raw_log", "security.raw_message", "rawmsg", "raw_log"):
                raw_log_records.append(r)
            else:
                other_records.append(r)

        if len(raw_log_records) > 2:
            clusters: Dict[str, List[CanonicalEvidenceRecord]] = {}
            for r in raw_log_records:
                val = str(r.observed_value)
                norm_template = re.sub(r"\b\d{1,5}\b", "NUM", val)
                norm_template = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "IP", norm_template)
                norm_template = re.sub(r"time=\S+", "time=T", norm_template)
                clusters.setdefault(norm_template[:100], []).append(r)

            for cluster_key, cluster_items in clusters.items():
                first_item = cluster_items[0]
                cluster_len = len(cluster_items)
                if cluster_len == 1:
                    aggregated_records.append(first_item)
                else:
                    # Representative verbatim log
                    setattr(first_item, "_occurrence_count", cluster_len)
                    aggregated_records.append(first_item)
                    # Cluster summary record
                    summary_text = (
                        f"Repeated in {cluster_len} events. "
                        f"Sample: {str(first_item.observed_value)[:160]}..."
                    )
                    cluster_rec = CanonicalEvidenceRecord(
                        evidence_id=f"EV-{inc_id}-CLUSTER-raw_log-{first_item.evidence_id[-6:]}",
                        incident_id=inc_id,
                        source_system=sys_src,
                        source_event_id="CLUSTER",
                        source_field="security.raw_log_cluster",
                        observed_value=summary_text,
                        observed_at=first_item.observed_at,
                        evidence_type="SECURITY_EVENT",
                        availability="AVAILABLE",
                        provenance_status="SOURCE_RECORDED",
                        integrity_digest=CanonicalEvidenceRecord.generate_digest("security.raw_log_cluster", summary_text),
                    )
                    setattr(cluster_rec, "_occurrence_count", cluster_len)
                    aggregated_records.append(cluster_rec)
                    extra_canonical_for_validator.append(cluster_rec)
        else:
            aggregated_records.extend(raw_log_records)

        # -------------------------------------------------------------
        # STEP 3: Repetitive Value Deduplication
        # -------------------------------------------------------------
        # Fields that represent unique forensic entities and should not be collapsed across distinct events
        DO_NOT_COLLAPSE_FIELDS = frozenset({
            "process.command_line",
            "process.parent_command_line",
            "process.file_path",
            "file.hash_sha256",
            "file.hash_md5",
        })

        grouped_records: Dict[Tuple[str, str], List[CanonicalEvidenceRecord]] = {}
        for r in other_records:
            f_norm = r.source_field.lower()
            val_clean = str(r.observed_value).strip()
            if f_norm in DO_NOT_COLLAPSE_FIELDS:
                # Keep distinct forensic executions intact
                aggregated_records.append(r)
            else:
                key = (f_norm, val_clean)
                grouped_records.setdefault(key, []).append(r)

        for (field_norm, val_clean), matching_records in grouped_records.items():
            first_rec = matching_records[0]
            count = len(matching_records)

            if count == 1:
                aggregated_records.append(first_rec)
            else:
                digest_short = CanonicalEvidenceRecord.generate_digest(first_rec.source_field, val_clean)[:6]
                field_slug = first_rec.source_field.replace(".", "_")
                recurring_id = f"EV-{inc_id}-RECURRING-{field_slug}-{digest_short}"

                dedup_rec = CanonicalEvidenceRecord(
                    evidence_id=recurring_id,
                    incident_id=inc_id,
                    source_system=sys_src,
                    source_event_id=f"RECURRING_{count}",
                    source_field=first_rec.source_field,
                    observed_value=val_clean,  # Exact scalar for grounding
                    observed_at=first_rec.observed_at,
                    evidence_type=first_rec.evidence_type,
                    availability="AVAILABLE",
                    provenance_status="SOURCE_RECORDED",
                    integrity_digest=CanonicalEvidenceRecord.generate_digest(first_rec.source_field, val_clean),
                )
                # Store occurrence count on object for serialization
                setattr(dedup_rec, "_occurrence_count", count)
                aggregated_records.append(dedup_rec)
                extra_canonical_for_validator.append(dedup_rec)

        # -------------------------------------------------------------
        # STEP 4: Relevance Selection & Sorting
        # -------------------------------------------------------------
        def score_relevance(rec: CanonicalEvidenceRecord) -> int:
            score = 0
            f_lower = rec.source_field.lower()

            # Priority 1: Evidence Contract Required Field (Must NEVER be lost)
            if f_lower in contract_fields:
                score += 1000

            # Priority 2: In detection rule pattern logic or anomaly trigger fields
            for token in re.findall(r"[a-zA-Z0-9_]+", pattern_text):
                if token and len(token) > 2 and token in f_lower:
                    score += 500

            # High signal anomaly metrics
            if any(term in f_lower for term in ("sdev", "avg", "totflow", "flowcount", "anomaly", "delta", "count")):
                score += 400

            # Priority 3: Core SOC Identifiers
            if any(term in f_lower for term in ("command_line", "destination_port", "destport", "protocol", "proto", "destination_ip", "source_ip", "user.name", "hostname")):
                score += 300

            # Priority 4: Security Action, Severity, Alert Title
            if any(term in f_lower for term in ("security.action", "alert_title", "event_type")):
                score += 200

            # Priority 5: Representative Raw Log or Time Range
            if "time_range" in f_lower or "cluster" in rec.evidence_id.lower():
                score += 150

            # Lower priority: auxiliary ephemeral client ports
            if "source_port" in f_lower or "srcport" in f_lower:
                score -= 50

            return score

        aggregated_records.sort(key=score_relevance, reverse=True)

        # -------------------------------------------------------------
        # STEP 5: Evidence-Aware Compaction Formatting
        # -------------------------------------------------------------
        compacted_dicts: List[Dict[str, Any]] = []
        for r in aggregated_records:
            item = {
                "evidence_id": r.evidence_id,
                "source_field": r.source_field,
                "observed_value": r.observed_value,
                "evidence_type": r.evidence_type,
            }
            count = getattr(r, "_occurrence_count", None)
            if count and count > 1:
                item["occurrence_count"] = count
            compacted_dicts.append(item)

        total_dedup_tokens = ModelTokenizerService.count_json_tokens(compacted_dicts)
        dedup_count = len(compacted_dicts)
        dedup_ratio = round(dedup_count / max(1, total_raw_count), 4)

        # -------------------------------------------------------------
        # STEP 6: Deterministic Chunking (if still over budget and chunking enabled)
        # -------------------------------------------------------------
        if total_dedup_tokens <= max_evidence_budget_tokens or not enable_chunking:
            return {
                "compacted_records": compacted_dicts,
                "all_dedup_canonical_records": extra_canonical_for_validator,
                "is_chunked": False,
                "chunk_index": 1,
                "total_chunks": 1,
                "all_chunks": [compacted_dicts],
                "total_raw_records": total_raw_count,
                "deduplicated_record_count": dedup_count,
                "estimated_tokens": total_dedup_tokens,
                "deduplication_ratio": dedup_ratio,
            }

        # Deterministic Chunking with Anchor Invariant
        anchor_records: List[Dict[str, Any]] = []
        sliceable_records: List[Dict[str, Any]] = []

        for r_dict in compacted_dicts:
            f_norm = r_dict["source_field"].lower()
            if f_norm in contract_fields or score_relevance(
                CanonicalEvidenceRecord(
                    evidence_id=r_dict["evidence_id"],
                    incident_id=inc_id,
                    source_field=r_dict["source_field"],
                    observed_value=r_dict["observed_value"],
                    evidence_type=r_dict["evidence_type"],
                    integrity_digest="anchor",
                )
            ) >= 500:
                anchor_records.append(r_dict)
            else:
                sliceable_records.append(r_dict)

        anchor_tokens = ModelTokenizerService.count_json_tokens(anchor_records)
        remaining_chunk_budget = max(200, max_evidence_budget_tokens - anchor_tokens)

        chunks: List[List[Dict[str, Any]]] = []
        curr_slice: List[Dict[str, Any]] = []
        curr_slice_tokens = 0

        for r_dict in sliceable_records:
            r_tokens = ModelTokenizerService.count_json_tokens(r_dict)
            if curr_slice and (curr_slice_tokens + r_tokens > remaining_chunk_budget):
                chunks.append(list(anchor_records) + curr_slice)
                curr_slice = [r_dict]
                curr_slice_tokens = r_tokens
            else:
                curr_slice.append(r_dict)
                curr_slice_tokens += r_tokens

        if curr_slice or not chunks:
            chunks.append(list(anchor_records) + curr_slice)

        total_chunks = len(chunks)
        selected_chunk = chunks[0] if chunks else anchor_records

        return {
            "compacted_records": selected_chunk,
            "all_dedup_canonical_records": extra_canonical_for_validator,
            "is_chunked": True,
            "chunk_index": 1,
            "total_chunks": total_chunks,
            "all_chunks": chunks,
            "anchor_record_count": len(anchor_records),
            "total_raw_records": total_raw_count,
            "deduplicated_record_count": dedup_count,
            "estimated_tokens": ModelTokenizerService.count_json_tokens(selected_chunk),
            "deduplication_ratio": dedup_ratio,
        }

    @classmethod
    def chunk_oversized_evidence(
        cls,
        records: List[CanonicalEvidenceRecord],
        contract_required_fields: Optional[List[str]] = None,
        rule_pattern_logic: Optional[str] = None,
        max_evidence_budget_tokens: int = 1500,
    ) -> Dict[str, Any]:
        """
        Explicitly executes compaction and deterministic chunking across multiple windows,
        guaranteeing that Mandatory Contract Anchors are preserved in every chunk.
        """
        return cls.compact_and_deduplicate(
            records=records,
            contract_required_fields=contract_required_fields,
            rule_pattern_logic=rule_pattern_logic,
            max_evidence_budget_tokens=max_evidence_budget_tokens,
            enable_chunking=True,
        )
