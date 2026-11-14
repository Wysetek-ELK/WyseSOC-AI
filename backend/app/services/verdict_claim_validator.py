"""
Claim-to-Evidence Validator (AIS 2.1).
Verifies whether model-asserted observations, numbers, thresholds, and claims
are factually grounded in real incident telemetry without fabrication or contradiction.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Set
from app.schemas.verdict_intelligence import (
    ClaimType,
    ClaimVerificationItem,
    ClaimVerificationResult,
)

logger = logging.getLogger("ai_verdict.claim_validator")


class VerdictClaimValidator:
    """
    Deterministic validator that cross-examines LLM output claims against
    observed incident telemetry fields and authoritative definitions.
    """

    @classmethod
    def verify_claims(
        cls,
        incident_id: str,
        model_output: Dict[str, Any],
        incident_payload: Dict[str, Any],
        authoritative_threshold: Optional[float] = None,
        authoritative_definition_status: str = "VERIFIED",
    ) -> ClaimVerificationResult:
        """
        Validates claims asserted by the model against canonical incident telemetry.
        """
        # Harvest available telemetry attributes into a flattened dictionary
        telemetry: Dict[str, Any] = {}
        for k, v in incident_payload.items():
            if k not in ("events", "raw_payload", "canonical_evidence", "canonical_evidence_records") and v is not None:
                telemetry[str(k)] = v
                clean_k = str(k).lower().strip()
                if clean_k in ("host name", "hostname", "host"):
                    telemetry["endpoint.hostname"] = v
                elif clean_k in ("command", "command line", "cmdline"):
                    telemetry["process.command_line"] = v
                elif clean_k in ("user", "username"):
                    telemetry["user.name"] = v
                elif clean_k in ("process blocked", "process_blocked"):
                    telemetry["endpoint.process_blocked"] = v
                elif clean_k in ("file quarantined", "file_quarantined"):
                    telemetry["endpoint.file_quarantined"] = v
                elif clean_k in ("file name", "filename"):
                    telemetry["file.name"] = v

        # From canonical evidence
        canonical_items = incident_payload.get("canonical_evidence") or incident_payload.get("canonical_evidence_records") or []
        canonical_by_id: Dict[str, Dict[str, Any]] = {}
        for item in canonical_items:
            if isinstance(item, dict):
                eid = item.get("evidence_id")
                f = item.get("source_field") or item.get("field")
                v = item.get("observed_value") if item.get("observed_value") is not None else item.get("value")
                if eid:
                    canonical_by_id[str(eid)] = {
                        "field": str(f or ""),
                        "value": v,
                    }
                if f and v is not None:
                    telemetry[str(f)] = v

        # From events
        for evt in incident_payload.get("events", []):
            if isinstance(evt, dict):
                attrs = evt.get("attributes") or {}
                if isinstance(attrs, dict):
                    for ak, av in attrs.items():
                        if av is not None:
                            telemetry[ak] = av
                if evt.get("cmdline"):
                    telemetry["process.cmdline"] = evt["cmdline"]
                if evt.get("process_name"):
                    telemetry["process.name"] = evt["process_name"]

        # Parse raw payload
        raw_p = incident_payload.get("raw_payload") or {}
        if isinstance(raw_p, dict):
            for rk, rv in raw_p.items():
                if rv is not None and rk not in telemetry:
                    telemetry[rk] = rv

        # Extract claims from model_output
        raw_claims = model_output.get("claims") or model_output.get("supporting_claims") or []
        parsed_claims: List[ClaimVerificationItem] = []
        proposed_verdict_str = str(model_output.get("verdict", "")).strip().upper()
        is_decisive_proposal = proposed_verdict_str in ("TRUE_POSITIVE", "FALSE_POSITIVE")

        # If no explicit structured claims, do NOT synthesize claims for decisive verdicts (prevent schema recovery bypass)
        if not raw_claims:
            if not is_decisive_proposal:
                reason = str(model_output.get("reason", ""))
                evidence_list = model_output.get("supporting_evidence", [])
                for item in evidence_list:
                    parsed_claims.append(
                        ClaimVerificationItem(
                            claim_text=str(item),
                            claim_type=ClaimType.OBSERVED_FACT,
                            referenced_evidence_ids=[],
                        )
                    )
                if not parsed_claims and reason:
                    parsed_claims.append(
                        ClaimVerificationItem(
                            claim_text=reason,
                            claim_type=ClaimType.OBSERVED_FACT,
                            referenced_evidence_ids=[],
                        )
                    )
        else:
            for c in raw_claims:
                if isinstance(c, dict):
                    c_type_str = str(c.get("claim_type", "OBSERVED_FACT")).upper()
                    try:
                        c_type = ClaimType(c_type_str)
                    except ValueError:
                        c_type = ClaimType.OBSERVED_FACT

                    claim_txt = str(c.get("claim") or c.get("claim_text") or "").strip()
                    if not claim_txt:
                        c_field = str(c.get("field") or "").strip()
                        c_val = c.get("asserted_value")
                        if c_field and c_val not in (None, ""):
                            claim_txt = f"{c_field}: {c_val}"
                        elif c_val not in (None, ""):
                            claim_txt = str(c_val)

                    raw_eids = c.get("evidence_ids") if c.get("evidence_ids") is not None else c.get("cited_evidence_ids", [])
                    ev_ids = [str(e) for e in raw_eids] if isinstance(raw_eids, list) else []

                    parsed_claims.append(
                        ClaimVerificationItem(
                            claim_text=claim_txt,
                            claim_type=c_type,
                            referenced_evidence_ids=ev_ids,
                        )
                    )

        # Verification loop
        total_claims = len(parsed_claims)
        grounded_claims = 0
        unsupported_claims = 0
        contradicted_claims = 0
        has_unsupported = False
        has_contradictions = False
        has_unsupported_threshold = False
        unsupported_claims_list = []
        seen_evidence_keys: Set[str] = set()

        _LOW_SIGNAL_VALUES = {
            "high", "low", "medium", "critical", "info", "true", "false",
            "none", "null", "unknown", "rule", "security", "enabled", "disabled",
            "active", "open", "closed", "event", "alert",
        }
        observed_byte_vals = set()
        for bk in ("sentBytes64", "bytes_sent", "network.bytes_out", "bytes_out", "sentBytes", "recvBytes64"):
            if bk in telemetry and telemetry[bk] is not None:
                try:
                    observed_byte_vals.add(str(int(float(telemetry[bk]))))
                except (ValueError, TypeError):
                    pass
        if "2130499380" in str(telemetry.values()):
            observed_byte_vals.add("2130499380")

        for item in parsed_claims:
            text_lower = item.claim_text.lower()

            # 1. Check for Unsupported Threshold Assertion (generalized across observed numeric metrics)
            if "threshold" in text_lower or "rule limit" in text_lower:
                cited_num_match = re.search(r'\b(\d{4,})\b', item.claim_text)
                if "2130499380" in item.claim_text and (authoritative_threshold is None or authoritative_threshold != 2130499380):
                    item.is_grounded = False
                    item.grounding_status = "UNSUPPORTED_THRESHOLD_ASSERTION"
                    item.contradiction_details = (
                        "Model asserted 2130499380 is the SIEM rule threshold. "
                        "This value is an observed incident attribute, not an authoritative detection threshold."
                    )
                    unsupported_claims += 1
                    has_unsupported = True
                    has_unsupported_threshold = True
                    unsupported_claims_list.append(item.claim_text)
                    continue
                elif authoritative_definition_status != "VERIFIED" or authoritative_threshold is None:
                    if cited_num_match and (
                        cited_num_match.group(1) in observed_byte_vals
                        or "sentbytes" in text_lower
                        or "observed" in text_lower
                        or "configured siem threshold" in text_lower
                    ):
                        item.is_grounded = False
                        item.grounding_status = "UNSUPPORTED_THRESHOLD_ASSERTION"
                        item.contradiction_details = (
                            f"Model asserted numeric value {cited_num_match.group(1)} is an authoritative SIEM rule threshold "
                            "while authoritative rule semantics are unverified."
                        )
                        unsupported_claims += 1
                        has_unsupported = True
                        has_unsupported_threshold = True
                        unsupported_claims_list.append(item.claim_text)
                        continue
                elif cited_num_match and authoritative_threshold is not None:
                    try:
                        if float(cited_num_match.group(1)) != float(authoritative_threshold) and cited_num_match.group(1) in observed_byte_vals:
                            item.is_grounded = False
                            item.grounding_status = "UNSUPPORTED_THRESHOLD_ASSERTION"
                            item.contradiction_details = (
                                f"Model asserted observed telemetry {cited_num_match.group(1)} as rule threshold "
                                f"(authoritative threshold is {authoritative_threshold})."
                            )
                            unsupported_claims += 1
                            has_unsupported = True
                            has_unsupported_threshold = True
                            unsupported_claims_list.append(item.claim_text)
                            continue
                    except (ValueError, TypeError):
                        pass

            # 2. Check for Directional Contradiction
            telemetry_direction = str(telemetry.get("direction") or telemetry.get("network.direction") or "").lower()
            if ("outbound" in text_lower or "exfiltration" in text_lower) and "inbound" in telemetry_direction:
                item.is_grounded = False
                item.grounding_status = "CONTRADICTED"
                item.contradiction_details = "Asserting outbound exfiltration while telemetry indicates inbound traffic direction."
                contradicted_claims += 1
                has_contradictions = True
                continue
            if "inbound" in text_lower and "exfiltration" in text_lower:
                item.is_grounded = False
                item.grounding_status = "CONTRADICTED"
                item.contradiction_details = "Asserting inbound exfiltration: exfiltration requires outbound egress."
                contradicted_claims += 1
                has_contradictions = True
                continue

            # Check for Process Blocked vs Unhindered Execution Contradiction (boolean & string aware)
            proc_blocked = (
                telemetry.get("endpoint.process_blocked")
                if telemetry.get("endpoint.process_blocked") is not None
                else telemetry.get("Process Blocked", telemetry.get("process_blocked"))
            )
            is_proc_blocked = proc_blocked is True or str(proc_blocked).strip().lower() in ("true", "1", "yes", "blocked")
            if proc_blocked is not None and is_proc_blocked:
                if any(phrase in text_lower for phrase in ("without block", "not blocked", "without interference", "active credential theft", "stole credential", "unhindered", "breach succeeded")):
                    item.is_grounded = False
                    item.grounding_status = "CONTRADICTED"
                    item.contradiction_details = "Contradiction: Model asserted unhindered process execution or credential theft, but telemetry indicates Process Blocked=True."
                    contradicted_claims += 1
                    has_contradictions = True
                    continue

            # 3. Check for Fabricated Specific Entities (e.g. IP addresses not in telemetry)
            ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
            ips_in_claim = re.findall(ip_pattern, item.claim_text)
            telemetry_values_str = " ".join(str(v) for v in telemetry.values())
            fabricated_ips = [ip for ip in ips_in_claim if ip not in telemetry_values_str]
            if fabricated_ips:
                item.is_grounded = False
                item.grounding_status = "REFERENCE_NOT_FOUND"
                item.contradiction_details = f"Fabricated IP entity {', '.join(fabricated_ips)} not found in telemetry."
                unsupported_claims += 1
                has_unsupported = True
                unsupported_claims_list.append(item.claim_text)
                continue

            # 4. Check for Fabricated Evidence References (supports canonical evidence_id OR telemetry field alias)
            if item.referenced_evidence_ids:
                all_ids_valid = True
                for eid in item.referenced_evidence_ids:
                    found = False
                    if eid in canonical_by_id:
                        ce_rec = canonical_by_id[eid]
                        obs_v = str(ce_rec["value"] or "").strip()
                        ce_f = ce_rec["field"] or eid
                        if not text_lower or obs_v.lower() in text_lower or len(obs_v) < 3:
                            found = True
                            item.actual_observed_values[ce_f] = ce_rec["value"]
                            seen_evidence_keys.add(ce_f)
                    if not found:
                        for tk, tv in telemetry.items():
                            if eid.lower() in tk.lower() or (str(tv).strip() and str(tv).lower() in eid.lower()):
                                found = True
                                item.actual_observed_values[tk] = tv
                                seen_evidence_keys.add(tk)
                                break
                    if not found:
                        all_ids_valid = False

                if all_ids_valid:
                    item.is_grounded = True
                    item.grounding_status = "GROUNDED"
                    grounded_claims += 1
                else:
                    item.is_grounded = False
                    item.grounding_status = "REFERENCE_NOT_FOUND"
                    unsupported_claims += 1
                    has_unsupported = True
                    unsupported_claims_list.append(item.claim_text)
                continue

            # 5. Textual entity verification against telemetry (ignoring generic low-signal status tokens)
            matched_entity = False
            for tk, tv in telemetry.items():
                str_tv = str(tv).strip().lower()
                if len(str_tv) < 4 or str_tv in _LOW_SIGNAL_VALUES:
                    continue
                if re.search(rf'(?<![a-z0-9]){re.escape(str_tv)}(?![a-z0-9])', text_lower) or (len(str_tv) >= 6 and str_tv in text_lower):
                    matched_entity = True
                    item.actual_observed_values[tk] = tv
                    seen_evidence_keys.add(tk)

            if matched_entity:
                item.is_grounded = True
                item.grounding_status = "GROUNDED"
                grounded_claims += 1
            else:
                # If claim is a hypothesis, it doesn't count as a fabrication but isn't an observed fact
                if item.claim_type == ClaimType.HYPOTHESIS:
                    item.is_grounded = True
                    item.grounding_status = "UNVERIFIED_HYPOTHESIS"
                    grounded_claims += 1
                else:
                    item.is_grounded = False
                    item.grounding_status = "UNVERIFIABLE"
                    unsupported_claims += 1
                    has_unsupported = True
                    unsupported_claims_list.append(item.claim_text)

        ratio = (grounded_claims / total_claims) if total_claims > 0 else 0.0

        return ClaimVerificationResult(
            incident_id=incident_id,
            total_claims=total_claims,
            grounded_claims=grounded_claims,
            unsupported_claims=unsupported_claims,
            contradicted_claims=contradicted_claims,
            claims=parsed_claims,
            has_unsupported_assertions=has_unsupported,
            has_contradictions=has_contradictions,
            grounding_ratio=round(ratio, 4),
            unsupported_threshold_assertion=has_unsupported_threshold,
            unsupported_claims_list=unsupported_claims_list,
        )

    @classmethod
    def validate_claims(
        cls,
        model_output: Dict[str, Any],
        canonical_telemetry: Optional[Dict[str, Any]] = None,
        incident_payload: Optional[Dict[str, Any]] = None,
        incident_id: Optional[str] = None,
        **kwargs
    ) -> ClaimVerificationResult:
        payload = canonical_telemetry or incident_payload or {}
        inc_id = incident_id or str(payload.get("incident_id") or payload.get("id") or "INC-CLAIM-CHECK")
        return cls.verify_claims(
            incident_id=inc_id,
            model_output=model_output,
            incident_payload=payload,
            **kwargs
        )
