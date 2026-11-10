import re
import logging
from typing import List, Dict, Any, Optional

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_claim import ModelSupportingClaim, ClaimGroundingResult

logger = logging.getLogger(__name__)

# Patterns for extracting factual entities from unstructured text
HASH_SHA256_RE = re.compile(r'\b[a-fA-F0-9]{64}\b')
HASH_MD5_RE = re.compile(r'\b[a-fA-F0-9]{32}\b')
IPV4_RE = re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b')
PROC_RE = re.compile(r'\b([a-zA-Z0-9_\-\.]+\.(?:exe|dll|ps1|bat|sh|bin))\b', re.IGNORECASE)


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
        structured_claims = raw_verdict_output.get("supporting_claims") or raw_verdict_output.get("claims")
        if isinstance(structured_claims, list) and structured_claims:
            for item in structured_claims:
                if isinstance(item, dict):
                    raw_ids = item.get("evidence_ids") if item.get("evidence_ids") is not None else item.get("cited_evidence_ids", [])
                    ev_ids = [str(e) for e in raw_ids] if isinstance(raw_ids, list) else []
                    has_explicit_asserted = "asserted_value" in item and item.get("asserted_value") not in (None, "")
                    asserted = item.get("asserted_value") if has_explicit_asserted else (item.get("claim_text") or item.get("claim") or "")
                    field_name = str(item.get("field") or "unknown")
                    if field_name == "unknown" and ev_ids and ev_ids[0] in evidence_by_id:
                        field_name = evidence_by_id[ev_ids[0]].source_field
                    claim = ModelSupportingClaim(
                        claim_type=str(item.get("claim_type", "PROCESS_EXECUTION")),
                        evidence_ids=ev_ids,
                        field=field_name,
                        asserted_value=asserted,
                    )
                    claims.append(claim)

        # 2. Extract Claims from Legacy Free-Text supporting_evidence / reason if no structured claims
        if not claims:
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
                ))

            # Extract MD5 Hashes
            for h in set(HASH_MD5_RE.findall(combined_text)):
                claims.append(ModelSupportingClaim(
                    claim_type="FILE_HASH",
                    evidence_ids=[],
                    field="file.hash_md5",
                    asserted_value=h.lower(),
                ))

            # Extract IP Addresses
            for ip in set(IPV4_RE.findall(combined_text)):
                claims.append(ModelSupportingClaim(
                    claim_type="NETWORK_CONNECTION",
                    evidence_ids=[],
                    field="network.destination_ip",
                    asserted_value=ip,
                ))

            # Extract Process Names
            for proc in set(PROC_RE.findall(combined_text)):
                claims.append(ModelSupportingClaim(
                    claim_type="PROCESS_EXECUTION",
                    evidence_ids=[],
                    field="process.name",
                    asserted_value=proc.lower(),
                ))

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

                    # Check value match (handles both exact asserted values and sentence-style claim_text citations)
                    assert_str = str(claim.asserted_value).strip().lower()
                    obs_str = actual_val.strip().lower()

                    if (
                        assert_str == obs_str
                        or (len(assert_str) > 4 and assert_str in obs_str)
                        or (len(obs_str) >= 3 and obs_str in assert_str)
                    ):
                        pass
                    else:
                        all_ids_valid = False
                        status = "EVIDENCE_VALUE_MISMATCH"
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
                assert_str = str(claim.asserted_value).strip().lower()

                # Search matching field candidates
                for cand in candidates:
                    obs_str = str(cand.observed_value).strip().lower()
                    if assert_str == obs_str or (len(assert_str) > 4 and assert_str in obs_str) or (len(obs_str) > 4 and obs_str in assert_str):
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
                        any_obs = str(any_rec.observed_value).strip().lower()
                        if assert_str == any_obs or (len(assert_str) > 5 and assert_str in any_obs):
                            found_anywhere = True
                            status = "EVIDENCE_VALUE_MISMATCH"
                            reason_diag = f"Value '{claim.asserted_value}' observed in '{any_rec.source_field}', not '{target_field}'."
                            actual_val = str(any_rec.observed_value)
                            matched_id = any_rec.evidence_id
                            break

                    if not found_anywhere:
                        status = "CLAIM_NOT_VERIFIABLE"
                        reason_diag = f"Fabricated claim: Value '{claim.asserted_value}' for field '{target_field}' was never observed in incident telemetry."

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

