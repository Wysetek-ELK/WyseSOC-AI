import re
import logging
from typing import List, Dict, Any, Optional, Tuple

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_claim import ModelSupportingClaim, ClaimGroundingResult

logger = logging.getLogger(__name__)

# Patterns for extracting factual entities from unstructured text
HASH_SHA256_RE = re.compile(r'\b[a-fA-F0-9]{64}\b')
HASH_MD5_RE = re.compile(r'\b[a-fA-F0-9]{32}\b')
IPV4_RE = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
PROC_RE = re.compile(r'\b([a-zA-Z0-9_\-\.]+\.(?:exe|dll|ps1|bat|sh|bin))\b', re.IGNORECASE)


def compare_evidence_values(field: str, asserted: Any, observed: Any) -> bool:
    """Type-aware, security-conscious comparison between model asserted value and observed evidence value."""
    if asserted is None or observed is None:
        return False

    raw_assert = str(asserted).strip()
    raw_obs = str(observed).strip()
    if not raw_assert or not raw_obs:
        return False

    # Exact string match
    if raw_assert == raw_obs:
        return True

    clean_field = field.strip().lower()

    # 1. IP Address Comparison (handles /32, leading/trailing whitespace, IPv4/IPv6 notation)
    if "ip" in clean_field or "source_ip" in clean_field or "destination_ip" in clean_field:
        try:
            import ipaddress
            clean_a = re.sub(r'/\d+$', '', raw_assert)
            clean_o = re.sub(r'/\d+$', '', raw_obs)
            ip_a = ipaddress.ip_address(clean_a)
            ip_o = ipaddress.ip_address(clean_o)
            return (ip_a == ip_o)
        except Exception:
            pass

    # 2. HTTP Status Code Comparison (handles 200 vs "200" vs "200 OK")
    if "status_code" in clean_field or "statuscode" in clean_field or "http_status" in clean_field:
        try:
            match_a = re.search(r'\b(\d{3})\b', raw_assert)
            match_o = re.search(r'\b(\d{3})\b', raw_obs)
            if match_a and match_o:
                return (int(match_a.group(1)) == int(match_o.group(1)))
        except Exception:
            pass

    # 3. HTTP Method Comparison (case-insensitive GET == get)
    if "method" in clean_field or clean_field == "http.method":
        return (raw_assert.upper() == raw_obs.upper())

    # 4. URL Comparison (normalize scheme/host, trailing slash on root, preserve critical path/query params)
    if "url" in clean_field or clean_field in ("http.url", "web.url"):
        try:
            from urllib.parse import urlsplit
            u_a = urlsplit(raw_assert)
            u_o = urlsplit(raw_obs)
            scheme_a = (u_a.scheme or "http").lower()
            scheme_o = (u_o.scheme or "http").lower()
            netloc_a = u_a.netloc.lower()
            netloc_o = u_o.netloc.lower()
            path_a = u_a.path.rstrip('/') or '/'
            path_o = u_o.path.rstrip('/') or '/'
            query_a = u_a.query
            query_o = u_o.query
            return (scheme_a == scheme_o and netloc_a == netloc_o and path_a == path_o and query_a == query_o)
        except Exception:
            return False

    # 5. Web Category Comparison (case-insensitive trimmed comparison)
    if "category" in clean_field or clean_field == "webcategory":
        return (raw_assert.lower() == raw_obs.lower())

    # 6. Timestamp Comparison (ISO-8601 vs epoch milliseconds tolerance)
    if "timestamp" in clean_field or "time" in clean_field:
        try:
            from dateutil.parser import parse as parse_date
            dt_a = parse_date(raw_assert)
            dt_o = parse_date(raw_obs)
            if abs((dt_a - dt_o).total_seconds()) < 5:
                return True
        except Exception:
            pass

    # 7. Substring / Case-Insensitive String Match
    assert_lower = raw_assert.lower()
    obs_lower = raw_obs.lower()
    if assert_lower == obs_lower:
        return True
    if len(assert_lower) > 4 and assert_lower in obs_lower:
        return True
    if len(obs_lower) >= 3 and obs_lower in assert_lower:
        return True

    return False


class ModelClaimExtractor:
    """
    P2-REQ-04: Structured Model Claim Extractor & Grounding Verifier.
    Extracts explicit or unstructured claims from model output and
    independently checks them against canonical evidence records.
    """

    @classmethod
    def extract_and_ground_claims(
        cls,
        incident_id: str,
        raw_verdict_output: Dict[str, Any],
        normalization_result: EvidenceNormalizationResult,
    ) -> ClaimGroundingResult:
        """
        Parses claims from the model verdict and grounds each against canonical evidence.
        """
        evidence_by_id: Dict[str, CanonicalEvidenceRecord] = {r.evidence_id: r for r in normalization_result.records}
        evidence_by_field: Dict[str, List[CanonicalEvidenceRecord]] = normalization_result.evidence_by_field

        claims: List[ModelSupportingClaim] = []

        # 1. Parse Explicit Structured Claims if provided (supports P2 and PolicyCompiler V3 formats)
        has_explicit_claims_key = ("supporting_claims" in raw_verdict_output) or ("claims" in raw_verdict_output)
        structured_claims = raw_verdict_output.get("supporting_claims") or raw_verdict_output.get("claims")
        if isinstance(structured_claims, list) and structured_claims:
            for item in structured_claims:
                if isinstance(item, dict):
                    raw_ids = item.get("cited_evidence_ids") if item.get("cited_evidence_ids") is not None else item.get("evidence_ids", [])
                    ev_ids = [str(e) for e in raw_ids] if isinstance(raw_ids, list) else []
                    has_explicit_asserted = "asserted_value" in item and item.get("asserted_value") not in (None, "")
                    asserted = item.get("asserted_value") if has_explicit_asserted else (item.get("claim_text") or item.get("claim") or "")
                    field_name = str(item.get("field") or "unknown")
                    if field_name == "unknown" and ev_ids and ev_ids[0] in evidence_by_id:
                        field_name = evidence_by_id[ev_ids[0]].source_field
                    claim_text_val = str(item.get("claim_text") or item.get("claim") or "")
                    claim = ModelSupportingClaim(
                        claim_type=str(item.get("claim_type", "OBSERVED_FACT")),
                        evidence_ids=ev_ids,
                        cited_evidence_ids=ev_ids,
                        field=field_name,
                        asserted_value=asserted,
                        claim_text=claim_text_val,
                    )
                    claims.append(claim)

        # 2. Extract Claims from Legacy Free-Text supporting_evidence / reason ONLY IF no structured claims field was present
        # If the model explicitly provided supporting_claims=[] or claims=[], respect the empty list and do not synthesize.
        if not claims and not has_explicit_claims_key:
            free_text_items = raw_verdict_output.get("supporting_evidence", [])
            reason_text = str(raw_verdict_output.get("reason", ""))
            combined_text = "\n".join(str(s) for s in free_text_items) + "\n" + reason_text

            # Extract SHA256 Hashes
            for h in set(HASH_SHA256_RE.findall(combined_text)):
                claims.append(ModelSupportingClaim(
                    claim_type="FILE_HASH",
                    evidence_ids=[],
                    field="file.hash_sha256",
                    asserted_value=h.lower(),
                    claim_text=f"Observed SHA-256 hash {h.lower()}",
                ))

            # Extract MD5 Hashes
            for h in set(HASH_MD5_RE.findall(combined_text)):
                claims.append(ModelSupportingClaim(
                    claim_type="FILE_HASH",
                    evidence_ids=[],
                    field="file.hash_md5",
                    asserted_value=h.lower(),
                    claim_text=f"Observed MD5 hash {h.lower()}",
                ))

            # Extract IP Addresses
            for ip in set(IPV4_RE.findall(combined_text)):
                claims.append(ModelSupportingClaim(
                    claim_type="NETWORK_CONNECTION",
                    evidence_ids=[],
                    field="network.destination_ip",
                    asserted_value=ip,
                    claim_text=f"Observed network connection to {ip}",
                ))

            # Extract Process Names
            for proc in set(PROC_RE.findall(combined_text)):
                claims.append(ModelSupportingClaim(
                    claim_type="PROCESS_EXECUTION",
                    evidence_ids=[],
                    field="process.name",
                    asserted_value=proc.lower(),
                    claim_text=f"Observed process execution of {proc.lower()}",
                ))

        return cls.ground_claims(incident_id, claims, normalization_result)

    @classmethod
    def verify_semantic_predicate(
        cls,
        claim: ModelSupportingClaim,
        matched_rec: CanonicalEvidenceRecord,
        all_records: List[CanonicalEvidenceRecord],
    ) -> Tuple[bool, str, str]:
        """
        Validates that cited evidence supports the COMPLETE factual predicate asserted in the claim,
        not merely containing a matching filename, IP address, or string.
        Enforces predicate validation, evidence type compatibility, and explicit proof requirements
        for signature, reputation, authorization, execution, and security-action assertions.
        """
        claim_text = str(claim.claim_text or "").strip()
        asserted_val = str(claim.asserted_value or "").strip()
        claim_corpus = f"{claim_text} {asserted_val}".lower()
        rec_field = matched_rec.source_field.lower()
        rec_val = str(matched_rec.observed_value or "").strip().lower()

        # 1. Digital Signature Predicate
        sig_keywords = (
            "not signed", "unsigned", "is signed", "valid signature", "signed by",
            "signature status", "code signing", "signature is valid", "unverified signature",
            "digital signature", "valid digital", "signature verified", "signature invalid"
        )
        if any(kw in claim_corpus for kw in sig_keywords):
            sig_fields = (
                "file.signature_status", "code_signature.status", "signature.status",
                "signature.valid", "file.is_signed", "code_signing.status",
                "file.signature", "digital_signature.status", "digital_signature"
            )
            if not any(rec_field.startswith(sf) or rec_field == sf for sf in sig_fields):
                return (
                    False,
                    "UNSUPPORTED_PREDICATE",
                    f"Claim asserts signature status ('{claim_text or asserted_val}'), but cited evidence '{matched_rec.source_field}' only provides a file/process identifier, not authentic signature telemetry."
                )

        # 2. Threat Intel / Malware / Reputation Predicate
        reputation_keywords = (
            "known malware", "malicious hash", "blacklisted", "known benign",
            "threat intel", "reputation", "ioc match", "malicious domain", "malicious ip",
            "c2 ip", "malware family", "trojan", "ransomware", "malicious binary",
            "known attack tool"
        )
        if any(kw in claim_corpus for kw in reputation_keywords):
            ti_fields = (
                "threat_intel.", "reputation.", "antivirus.", "virustotal.", "ioc.",
                "security_event.threat_name", "mitre."
            )
            if not any(rec_field.startswith(tf) or tf in rec_field for tf in ti_fields):
                return (
                    False,
                    "UNSUPPORTED_PREDICATE",
                    f"Claim asserts malware/reputation status ('{claim_text or asserted_val}'), but cited evidence '{matched_rec.source_field}' only records an entity identifier without threat intelligence corroboration."
                )

        # 3. Authorization / Maintenance Predicate
        auth_keywords = (
            "authorized", "approved", "maintenance window", "scheduled task",
            "change ticket", "change request", "approved maintenance"
        )
        if any(kw in claim_corpus for kw in auth_keywords) and not any(neg in claim_corpus for neg in ("not authorized", "unauthorized", "unapproved", "no change", "without approved", "absence of")):
            auth_fields = (
                "authorization.", "itsm.", "change.", "maintenance.", "asset.scanner_role",
                "asset.is_authorized_scanner"
            )
            if not any(rec_field.startswith(af) or af in rec_field for af in auth_fields):
                return (
                    False,
                    "UNSUPPORTED_PREDICATE",
                    f"Claim asserts administrative authorization ('{claim_text or asserted_val}'), but cited evidence '{matched_rec.source_field}' lacks authoritative ITSM/change telemetry."
                )

        # 4. Security Action Predicate (Blocked, Quarantined, Terminated)
        sec_action_keywords = ("blocked", "quarantined", "terminated", "dropped", "prevented")
        if any(kw in claim_corpus for kw in sec_action_keywords) and not any(neg in claim_corpus for neg in ("not blocked", "unblocked", "not quarantined")):
            action_fields = ("security.action", "endpoint.process_blocked", "endpoint.file_quarantined", "action", "security.event_type")
            if not any(rec_field.startswith(af) or af == rec_field for af in action_fields):
                return (
                    False,
                    "UNSUPPORTED_PREDICATE",
                    f"Claim asserts security action ('{claim_text or asserted_val}'), but cited evidence '{matched_rec.source_field}' does not record an EDR/firewall action."
                )

        # 5. Evidence Type & Field Category Compatibility
        if claim.claim_type == "PROCESS_EXECUTION" or any(kw in claim_corpus for kw in ("process executed", "executed process", "binary executed")):
            if matched_rec.evidence_type in ("NETWORK_CONNECTION", "DNS_QUERY"):
                return (
                    False,
                    "INCOMPATIBLE_EVIDENCE_TYPE",
                    f"Claim asserts process execution ('{claim_text or asserted_val}'), but cited evidence type is '{matched_rec.evidence_type}'."
                )

        if claim.claim_type == "FILE_HASH" and "hash" not in rec_field:
            return (
                False,
                "INCOMPATIBLE_EVIDENCE_TYPE",
                f"Claim type is FILE_HASH, but cited field '{matched_rec.source_field}' is not a hash."
            )

        if claim.claim_type == "NETWORK_CONNECTION" and matched_rec.evidence_type in ("PROCESS_EXECUTION", "USER_CONTEXT", "FILE_HASH"):
            return (
                False,
                "INCOMPATIBLE_EVIDENCE_TYPE",
                f"Claim type is NETWORK_CONNECTION, but cited evidence is '{matched_rec.evidence_type}'."
            )

        return (True, "GROUNDED", "")

    @classmethod
    def ground_claims(
        cls,
        incident_id: str,
        claims: List[ModelSupportingClaim],
        normalization_result: EvidenceNormalizationResult,
    ) -> ClaimGroundingResult:
        """
        Grounds parsed or structured claims directly against canonical evidence.
        """
        evidence_by_id: Dict[str, CanonicalEvidenceRecord] = {r.evidence_id: r for r in normalization_result.records}
        evidence_by_field: Dict[str, List[CanonicalEvidenceRecord]] = normalization_result.evidence_by_field

        # 3. Ground Each Claim against Canonical Evidence
        grounded_count = 0
        unsupported_count = 0
        unsupported_details: List[Dict[str, Any]] = []

        for claim in claims:
            is_grounded = False
            status = "CLAIM_NOT_VERIFIABLE"
            reason_diag = ""
            matched_id = None
            actual_val = None

            # Case A: Model explicitly cited evidence ID(s)
            if claim.evidence_ids:
                all_ids_valid = True
                for eid in claim.evidence_ids:
                    rec = evidence_by_id.get(eid)
                    if not rec:
                        # Resilient alias lookup: check if model referenced an evidence alias or slight field variant
                        clean_eid_field = str(eid).lower().replace(".", "_")
                        for r_cand in normalization_result.records:
                            if compare_evidence_values(r_cand.source_field, claim.asserted_value, r_cand.observed_value):
                                clean_cf = r_cand.source_field.lower().replace(".", "_")
                                if (
                                    clean_cf in clean_eid_field
                                    or (clean_cf in ("process_file_name", "process_name") and any(k in clean_eid_field for k in ("process_name", "process_file_name", "process")))
                                    or (clean_cf in ("file_name", "filename") and any(k in clean_eid_field for k in ("file_name", "filename", "file_path")))
                                    or (clean_cf in ("process_parent_name", "parent_name") and any(k in clean_eid_field for k in ("parent", "parent_file_name")))
                                ):
                                    rec = r_cand
                                    break
                    if not rec:
                        all_ids_valid = False
                        status = "EVIDENCE_REFERENCE_NOT_FOUND"
                        reason_diag = f"Cited evidence ID '{eid}' does not exist in incident telemetry."
                        break
                    if rec.incident_id != incident_id:
                        all_ids_valid = False
                        status = "EVIDENCE_REFERENCE_NOT_FOUND"
                        reason_diag = f"Cited evidence ID '{eid}' belongs to different incident '{rec.incident_id}'."
                        break

                    actual_val = str(rec.observed_value)
                    matched_id = rec.evidence_id

                    # Check type-aware value match and field alias compatibility
                    clean_rec_f = rec.source_field.lower().replace(".", "_")
                    clean_claim_f = claim.field.lower().replace(".", "_")
                    fields_compatible = (
                        rec.source_field == claim.field
                        or claim.field == "unknown"
                        or clean_rec_f == clean_claim_f
                        or (clean_rec_f in ("process_name", "process_file_name", "process") and clean_claim_f in ("process_name", "process_file_name", "process"))
                        or (clean_rec_f in ("file_name", "filename", "file_path", "target_filename") and clean_claim_f in ("file_name", "filename", "file_path", "target_filename"))
                        or (clean_rec_f in ("process_parent_name", "parent_name", "parent_file_name", "parent_process") and clean_claim_f in ("process_parent_name", "parent_name", "parent_file_name", "parent_process"))
                        or (clean_rec_f in ("file_hash_sha256", "file_sha256", "sha256") and clean_claim_f in ("file_hash_sha256", "file_sha256", "sha256"))
                    )

                    if compare_evidence_values(claim.field, claim.asserted_value, actual_val) and fields_compatible:
                        pass
                    else:
                        all_ids_valid = False
                        status = "EVIDENCE_VALUE_MISMATCH"
                        if not fields_compatible and claim.field != "unknown":
                            reason_diag = f"Evidence ID '{eid}' records '{rec.source_field}' ('{actual_val}'), not '{claim.field}' ('{claim.asserted_value}')."
                        else:
                            reason_diag = f"Value mismatch for '{claim.field}': claimed '{claim.asserted_value}', actual is '{actual_val}'."
                        break

                if all_ids_valid and matched_id:
                    is_grounded = True
                    status = "GROUNDED"
                    reason_diag = f"Grounded via cited evidence ID '{matched_id}'."

            # Case B: Model did not cite evidence ID (unstructured / legacy claim)
            else:
                target_field = claim.field
                candidates = evidence_by_field.get(target_field, [])

                # Search matching field candidates using type-aware comparison
                for cand in candidates:
                    if compare_evidence_values(target_field, claim.asserted_value, cand.observed_value):
                        is_grounded = True
                        status = "GROUNDED"
                        matched_id = cand.evidence_id
                        actual_val = str(cand.observed_value)
                        reason_diag = f"Grounded against source field '{target_field}' ({cand.evidence_id})."
                        break

                # If not found in target field, check if it was present anywhere in incident telemetry
                if not is_grounded:
                    found_anywhere = False
                    for any_rec in normalization_result.records:
                        if compare_evidence_values(any_rec.source_field, claim.asserted_value, any_rec.observed_value):
                            found_anywhere = True
                            status = "EVIDENCE_VALUE_MISMATCH"
                            reason_diag = f"Value '{claim.asserted_value}' observed in '{any_rec.source_field}', not '{target_field}'."
                            actual_val = str(any_rec.observed_value)
                            matched_id = any_rec.evidence_id
                            break

                    if not found_anywhere:
                        status = "CLAIM_NOT_VERIFIABLE"
                        reason_diag = f"Fabricated claim: Value '{claim.asserted_value}' for field '{target_field}' was never observed in incident telemetry."

            # Semantic Predicate Validation (Complete Factual Claim Grounding)
            if is_grounded and matched_id:
                matched_rec = evidence_by_id.get(matched_id)
                if matched_rec:
                    pred_valid, pred_status, pred_reason = cls.verify_semantic_predicate(
                        claim=claim,
                        matched_rec=matched_rec,
                        all_records=normalization_result.records,
                    )
                    if not pred_valid:
                        is_grounded = False
                        status = pred_status
                        reason_diag = pred_reason

            claim.is_grounded = is_grounded
            claim.grounding_status = status
            claim.reason = reason_diag
            claim.matched_evidence_id = matched_id
            claim.actual_observed_value = actual_val

            if is_grounded:
                grounded_count += 1
            else:
                unsupported_count += 1
                unsupported_details.append({
                    "claim_type": claim.claim_type,
                    "field": claim.field,
                    "asserted_value": claim.asserted_value,
                    "grounding_status": status,
                    "reason": reason_diag,
                })

        total = len(claims)
        ratio = (grounded_count / total) if total > 0 else 1.0

        return ClaimGroundingResult(
            incident_id=incident_id,
            total_claims=total,
            grounded_claims=grounded_count,
            unsupported_claims=unsupported_count,
            grounding_ratio=round(ratio, 3),
            claims=claims,
            unsupported_claim_details=unsupported_details,
            has_hallucinations=(unsupported_count > 0),
        )

