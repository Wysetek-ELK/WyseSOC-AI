import hashlib
import ipaddress
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

from app.schemas.canonical_evidence import CanonicalEvidenceRecord, EvidenceNormalizationResult
from app.schemas.evidence_contract import RuleEvidenceContract
from app.schemas.evidence_preflight import PreflightValidationResult
from app.schemas.evidence_claim import ClaimGroundingResult
from app.schemas.verdict_validation import VerdictValidationResult

logger = logging.getLogger(__name__)


class IndependentVerdictValidator:
    """
    P2-REQ-05: Independent Deterministic Verdict Validator.
    The authoritative verification engine that evaluates model propositions against
    real normalized evidence, approved policy contracts, and grounding checks.
    The model's confidence or claims can never override this validator.
    """

    VALIDATOR_VERSION = "2.0.0"

    @staticmethod
    def _parse_timestamp(val: Any) -> Optional[float]:
        if val is None:
            return None
        val_str = str(val).strip()
        if not val_str:
            return None
        try:
            return float(val_str)
        except (ValueError, TypeError):
            pass
        from datetime import datetime
        for fmt in (
            "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%SZ", "%Y-%m-%d %H:%M:%S%z",
            "%Y-%m-%d", "%m/%d/%Y %H:%M:%S"
        ):
            try:
                return datetime.strptime(val_str, fmt).timestamp()
            except (ValueError, TypeError):
                continue
        return None

    @classmethod
    def validate_verdict(
        cls,
        incident_id: str,
        proposed_verdict: str,
        raw_model_confidence: float,
        preflight: PreflightValidationResult,
        claim_grounding: ClaimGroundingResult,
        normalization_result: EvidenceNormalizationResult,
        contract: RuleEvidenceContract,
        allow_simulation: bool = False,
        compilation_digest: Optional[str] = None,
        model_reason: str = "",
        contradictory_evidence: Optional[List[str]] = None,
    ) -> VerdictValidationResult:
        """
        Executes the 8 mandatory deterministic checks and determines the final authoritative verdict.
        """
        raw_prop = str(proposed_verdict or "REQUIRES_ATTENTION").upper().strip()
        if raw_prop == "REQUIRES_ANALYST_ATTENTION":
            clean_prop_verdict = "REQUIRES_ATTENTION"
        else:
            clean_prop_verdict = raw_prop

        reason_codes: List[str] = []
        contradictions: List[str] = list(preflight.detected_contradictions)
        if contradictory_evidence:
            for ce in contradictory_evidence:
                if str(ce).strip():
                    contradictions.append(str(ce).strip())
        unsupported_claims: List[Dict[str, Any]] = list(claim_grounding.unsupported_claim_details)

        # Output Integrity Check (Check 8)
        invalid_output_flag = clean_prop_verdict not in ("TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION")
        if invalid_output_flag:
            clean_prop_verdict = "REQUIRES_ATTENTION"
            reason_codes.append("MODEL_OUTPUT_INVALID")

        final_verdict = clean_prop_verdict
        validation_status = "INVALID_MODEL_OUTPUT" if invalid_output_flag else "VALIDATED"
        is_decisive = False
        action_directive = "Verdict verified against canonical evidence contract."

        # Check 1: Policy & Contract Authorization
        if contract.status != "APPROVED":
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "ABSTAINED"
            reason_codes.append("EVIDENCE_CONTRACT_UNVERIFIED")
            action_directive = "Please review and approve the investigation policy in Agent Intelligence Studio before automated triage."

        # Check 2: Mandatory Evidence Completeness
        if preflight.critical_missing_fields:
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "INSUFFICIENT_EVIDENCE"
            reason_codes.append("EVIDENCE_MISSING")
            action_directive = f"Collect missing mandatory telemetry ({', '.join(preflight.critical_missing_fields)}) before closing incident."

        # Check 3: Source Grounding & Unsupported Model Claims
        if claim_grounding.has_hallucinations and clean_prop_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "REJECTED"

            # Discern specific grounding failure reasons
            for c in claim_grounding.claims:
                if not c.is_grounded:
                    if c.grounding_status == "EVIDENCE_REFERENCE_NOT_FOUND":
                        if "EVIDENCE_REFERENCE_NOT_FOUND" not in reason_codes:
                            reason_codes.append("EVIDENCE_REFERENCE_NOT_FOUND")
                    elif c.grounding_status == "EVIDENCE_VALUE_MISMATCH":
                        if "EVIDENCE_VALUE_MISMATCH" not in reason_codes:
                            reason_codes.append("EVIDENCE_VALUE_MISMATCH")
                    else:
                        if "CLAIM_NOT_VERIFIABLE" not in reason_codes:
                            reason_codes.append("CLAIM_NOT_VERIFIABLE")

            action_directive = "Model fabricated or asserted unverified evidence claims. Human Tier 2 investigation required."

        # Check 4: Evidence Consistency & Contradictions
        # Detect model-telemetry contradictions
        if clean_prop_verdict == "TRUE_POSITIVE":
            # Example: Model asserts external C2 or remote download when all IPs are internal loopback
            all_ips = [r.observed_value for r in normalization_result.records if r.source_field in ("network.source_ip", "network.destination_ip")]
            def _is_loopback_addr(ip_val: Any) -> bool:
                s = str(ip_val).strip().lower()
                if s in ("127.0.0.1", "::1", "localhost"):
                    return True
                try:
                    return ipaddress.ip_address(s).is_loopback
                except ValueError:
                    return False

            if all_ips and all(_is_loopback_addr(ip) for ip in all_ips):
                for claim in claim_grounding.claims:
                    if "c2" in str(claim.asserted_value).lower() or "external" in str(claim.asserted_value).lower():
                        contradictions.append("Contradiction: Claiming external communication on loopback/local interfaces")
                        reason_codes.append("EVIDENCE_CONTRADICTION")
                        final_verdict = "REQUIRES_ATTENTION"
                        validation_status = "REJECTED"
                        action_directive = "Activity occurs strictly on internal/loopback stack. Verify if local proxy reflection or healthcheck."

        elif clean_prop_verdict == "FALSE_POSITIVE":
            # Detect loopback / same-source-and-destination contradiction:
            # If model reason or claims assert "loopback", "same source and destination", "internal reflection"
            # BUT telemetry shows external destination IP or srcip != dstip:
            reason_lower = (model_reason or "").lower()
            claims_text = " ".join(str(c.asserted_value).lower() for c in claim_grounding.claims)
            all_fp_text = f"{reason_lower} {claims_text}"

            src_ips = [r.observed_value for r in normalization_result.records if r.source_field == "network.source_ip"]
            dst_ips = [r.observed_value for r in normalization_result.records if r.source_field == "network.destination_ip"]

            if any(term in all_fp_text for term in ("loopback", "same source and destination", "internal reflection", "local reflection")):
                if src_ips and dst_ips and src_ips[0] != dst_ips[0]:
                    contradictions.append(
                        f"Contradiction: Model claims internal loopback or same source/destination, but telemetry confirms source {src_ips[0]} connects to distinct destination {dst_ips[0]}"
                    )
                    if "EVIDENCE_CONTRADICTION" not in reason_codes:
                        reason_codes.append("EVIDENCE_CONTRADICTION")
                    final_verdict = "REQUIRES_ATTENTION"
                    validation_status = "REJECTED"
                    action_directive = "Model falsely inferred loopback based on rule name; telemetry confirms distinct source and destination IPs. Human review required."

        # Check 4b: Unresolved Contradictions Prevent Decisive Classification
        if contradictions and clean_prop_verdict in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
            final_verdict = "REQUIRES_ATTENTION"
            validation_status = "REJECTED"
            if "EVIDENCE_CONTRADICTION" not in reason_codes:
                reason_codes.append("EVIDENCE_CONTRADICTION")
            action_directive = "Material contradictory evidence detected in incident telemetry. Human Tier 2 review required."

        # Check 5: Verdict-Specific Decision Criteria
        if clean_prop_verdict == "TRUE_POSITIVE":
            # For TP: must meet evidence completeness AND provide at least one grounded claim representing security tradecraft
            has_grounded_security_tradecraft = False
            for c in claim_grounding.claims:
                if c.is_grounded:
                    c_type_str = str(c.claim_type or "").upper()
                    if c_type_str in (
                        "PROCESS_EXECUTION", "NETWORK_CONNECTION", "FILE_HASH",
                        "OBSERVED_FACT", "TELEMETRY_OBSERVATION", "CORRELATION_ASSERTION"
                    ):
                        has_grounded_security_tradecraft = True
                        break

            if preflight.evidence_completeness < 0.6 or claim_grounding.grounded_claims == 0 or not has_grounded_security_tradecraft:
                final_verdict = "REQUIRES_ATTENTION"
                if validation_status not in ("REJECTED", "ABSTAINED"):
                    validation_status = "INSUFFICIENT_EVIDENCE"
                if "TP_CRITERIA_UNSATISFIED" not in reason_codes:
                    reason_codes.append("TP_CRITERIA_UNSATISFIED")
                if "Model fabricated" not in action_directive:
                    action_directive = "Insufficient grounded claims or corroborating evidence to confirm malicious attack. Manual triage required."
            elif not reason_codes and final_verdict == "TRUE_POSITIVE":
                is_decisive = True
                reason_codes.append("EVIDENCE_VALIDATED")
                action_directive = "High-confidence malicious attack confirmed with verified evidence. Escalate to IR team."

        elif clean_prop_verdict == "FALSE_POSITIVE":
            # For FP: must have verified telemetry, at least one grounded claim, and independently verifiable authorization
            reason_lower = (model_reason or "").lower()

            # 1. Check for Invented Change Tickets in model rationale (excluding networking RFC standards like RFC-1918)
            ticket_patterns = set(re.findall(
                r'\b(?:CHG|CR|TICKET|WO|REQ)[-_]?[0-9]{3,}\b|\bRFC[-_]?(?!1918|5737|3330)[0-9]{3,}\b',
                model_reason,
                re.IGNORECASE,
            ))
            invented_tickets = []
            for tp in ticket_patterns:
                # Must be present in canonical evidence records belonging to this incident
                if not any(tp.lower() in str(r.observed_value).lower() or tp.lower() in str(r.source_field).lower() for r in normalization_result.records):
                    invented_tickets.append(tp)

            # 2. Check for Untrusted Command-Line Ticket Assertions (Reliability 1.3 - Requirement 3)
            # Ticket IDs, --ticket parameters, and maintenance flags in command lines are untrusted assertions, NOT proof of approval.
            authoritative_auth_fields = {
                "authorization.ticket_id", "authorization.change_ticket", "authorization.change_request",
                "itsm.ticket_id", "change_management.ticket", "policy.approved_baseline",
                "authorization.ticket", "itsm.change_id"
            }
            untrusted_cmdline_tickets = []
            for tp in ticket_patterns:
                in_cmdline = any(tp.lower() in str(r.observed_value).lower() for r in normalization_result.records if r.source_field in ("process.command_line", "cmdline", "rawmsg"))
                in_authoritative = any(tp.lower() in str(r.observed_value).lower() for r in normalization_result.records if r.source_field in authoritative_auth_fields)
                if in_cmdline and not in_authoritative:
                    untrusted_cmdline_tickets.append(tp)

            # 3. Check for Unsupported Maintenance Window Claims in model rationale
            has_maintenance_claim = bool(re.search(
                r'\b(?:maintenance window|scheduled maintenance|maintenance mode|authorized maintenance)\b',
                reason_lower
            ))
            maintenance_fields = {
                "maintenance.window", "authorization.maintenance_window", "is_maintenance",
                "maintenance.active", "scheduled_task.name", "scheduled_maintenance",
                "authorization.status", "itsm.maintenance_active"
            }
            has_grounded_maintenance = any(
                r.source_field in maintenance_fields
                or "maintenance" in str(r.observed_value).lower()
                or "scheduled" in str(r.observed_value).lower()
                for r in normalization_result.records
            )

            # 4. Check for Maintenance Window Expiration, Inactivity, or Time Bounds (Reliability 1.3 & Phase A - Item 3)
            maintenance_expired = False
            maintenance_time_detail = ""
            for r in normalization_result.records:
                if r.source_field in ("maintenance.active", "authorization.maintenance_active", "authorization.window_active", "maintenance.is_active"):
                    if str(r.observed_value).strip().lower() in ("false", "0", "inactive", "expired", "closed", "no"):
                        maintenance_expired = True
                        break
                elif r.source_field in ("authorization.is_expired", "maintenance.is_expired"):
                    if str(r.observed_value).strip().lower() in ("true", "1", "yes", "expired"):
                        maintenance_expired = True
                        break
                elif r.source_field in ("authorization.status", "itsm.status") and str(r.observed_value).strip().lower() == "expired":
                    maintenance_expired = True
                    break

            # 4b. Check Maintenance Start / End Window Matching against Incident Timestamp (Phase A - Item 3)
            inc_times: List[float] = []
            for r in normalization_result.records:
                if r.source_field in (
                    "incident.time", "incident.timestamp", "event.time", "event.timestamp",
                    "timestamp", "time", "generation_time", "detection_time", "phRecvTime"
                ):
                    ts = cls._parse_timestamp(r.observed_value)
                    if ts is not None:
                        inc_times.append(ts)

            start_times: List[float] = []
            end_times: List[float] = []
            for r in normalization_result.records:
                if r.source_field in ("maintenance.start_time", "maintenance.start", "authorization.start_time", "itsm.start_time", "window_start"):
                    ts = cls._parse_timestamp(r.observed_value)
                    if ts is not None:
                        start_times.append(ts)
                elif r.source_field in ("maintenance.end_time", "maintenance.end", "authorization.end_time", "itsm.end_time", "window_end"):
                    ts = cls._parse_timestamp(r.observed_value)
                    if ts is not None:
                        end_times.append(ts)

            if inc_times and (start_times or end_times):
                inc_ts = inc_times[0]
                if start_times and inc_ts < min(start_times):
                    maintenance_expired = True
                    maintenance_time_detail = f"Incident timestamp ({inc_ts}) occurred before scheduled maintenance start ({min(start_times)})"
                elif end_times and inc_ts > max(end_times):
                    maintenance_expired = True
                    maintenance_time_detail = f"Incident timestamp ({inc_ts}) occurred after scheduled maintenance end ({max(end_times)})"

            # 5. Check Digital Signature Validity vs Metadata (Reliability 1.3 - Requirement 6)
            # Ensure signature fields indicate successful validation, not merely metadata presence.
            invalid_sig_values = {
                "invalid", "unsigned", "revoked", "expired", "failed", "untrusted",
                "malformed", "self_signed_untrusted", "signature_verification_failed"
            }
            valid_sig_values = {"valid", "trusted", "verified", "signed_verified"}

            has_invalid_signature = False
            invalid_sig_detail = ""
            for r in normalization_result.records:
                if r.source_field in ("code_signature.status", "signature.status", "file.signature_status"):
                    val_clean = str(r.observed_value).strip().lower()
                    if val_clean in invalid_sig_values:
                        has_invalid_signature = True
                        invalid_sig_detail = str(r.observed_value)
                        break
                elif r.source_field == "signature.valid" and str(r.observed_value).strip().lower() in ("false", "0", "no"):
                    has_invalid_signature = True
                    invalid_sig_detail = "signature.valid=False"
                    break

            has_pki_claim = bool(re.search(
                r'\b(?:signed by corporate pki|corporate code-signing|valid digital signature|verified vendor signature|trusted certificate)\b',
                reason_lower
            ))
            has_verified_valid_signature = any(
                (r.source_field in ("code_signature.status", "file.signature_status", "signature.status") and str(r.observed_value).strip().lower() in valid_sig_values)
                or (r.source_field == "signature.valid" and str(r.observed_value).strip().lower() in ("true", "1", "yes", "valid", "verified"))
                for r in normalization_result.records
            )

            # 6. Check for Contradictory Adversary Tradecraft (e.g. Obfuscated LOLBins or Credential Dumping)
            adversary_patterns = [
                r"\bpowershell(?:\.exe)?\s+.*(?:-enc\b|-encodedcommand\b)",
                r"\b(?:mimikatz|sekurlsa|privilege::debug)\b",
                r"\bvssadmin(?:\.exe)?\s+delete\s+shadows\b",
                r"\bcertutil(?:\.exe)?\s+.*-urlcache\b",
                r"\b(?:downloadstring|iex\s*\(|invoke-expression)\b",
            ]
            has_adversary_tradecraft = False
            for r in normalization_result.records:
                if r.source_field in ("process.command_line", "process.name", "rawmsg", "cmdline"):
                    val_str = str(r.observed_value).lower()
                    for ap in adversary_patterns:
                        if re.search(ap, val_str, re.IGNORECASE):
                            has_adversary_tradecraft = True
                            break
                if has_adversary_tradecraft:
                    break

            # 7. Check Process-Name Spoofing & Trusted Binary Evidence (Reliability 1.3 - Requirements 1 & 2)
            # Do NOT accept a process solely because its executable name is allowlisted.
            # Require rule-appropriate trusted binary evidence (path, signature, hash, or management agent).
            approved_management_binaries = {
                "ccmexec.exe", "tanclient.exe", "qualysagent.exe", "nessusagent.exe",
                "archive_agent.exe", "endpointagent.exe"
            }
            suspicious_path_patterns = (
                r"\\temp\\", r"\\tmp\\", r"\\users\\", r"\\appdata\\",
                r"\\downloads\\", r"\\perflogs\\", r"\\programdata\\",
                r"/tmp/", r"/var/tmp/", r"/dev/shm/"
            )
            approved_path_patterns = {
                "ccmexec.exe": (r"\\windows\\ccm\\", r"\\system32\\"),
                "tanclient.exe": (r"\\program files\\tanium\\", r"\\program files \(x86\)\\tanium\\"),
                "qualysagent.exe": (r"\\program files\\qualys\\", r"\\program files \(x86\)\\qualys\\"),
                "nessusagent.exe": (r"\\program files\\tenable\\",),
                "archive_agent.exe": (r"\\program files\\", r"/opt/"),
                "endpointagent.exe": (r"\\program files\\", r"/opt/"),
            }

            has_spoofed_admin_binary = False
            spoofed_detail = ""
            unverified_binary_provenance = False
            unverified_binary_detail = ""

            proc_names = [str(r.observed_value).strip().lower() for r in normalization_result.records if r.source_field in ("process.name", "process.file_name")]
            exec_paths = [str(r.observed_value).strip().lower() for r in normalization_result.records if r.source_field in ("process.executable_path", "process.path", "file.path")]
            cmdlines = [str(r.observed_value).strip().lower() for r in normalization_result.records if r.source_field in ("process.command_line", "cmdline")]

            has_admin_binary_in_telemetry = any(p in approved_management_binaries for p in proc_names)
            if has_admin_binary_in_telemetry:
                all_paths_to_check = exec_paths + cmdlines
                for path_str in all_paths_to_check:
                    for sp in suspicious_path_patterns:
                        if re.search(sp, path_str, re.IGNORECASE):
                            has_spoofed_admin_binary = True
                            spoofed_detail = f"Executable executing from suspicious path ({path_str})"
                            break
                    if has_spoofed_admin_binary:
                        break

                has_trusted_path = False
                for p in proc_names:
                    if p in approved_path_patterns:
                        for app_pattern in approved_path_patterns[p]:
                            if any(re.search(app_pattern, path_str, re.IGNORECASE) for path_str in all_paths_to_check):
                                has_trusted_path = True
                                break
                    elif any(re.search(r"\\program files\\|\\system32\\|/opt/", path_str, re.IGNORECASE) for path_str in all_paths_to_check):
                        has_trusted_path = True

                has_trusted_hash = any(r.source_field in ("file.sha256", "process.sha256", "hash") for r in normalization_result.records)
                has_mgmt_agent = any(r.source_field in ("system.management_agent", "endpoint.management_status", "edr.managed") for r in normalization_result.records)

                has_trusted_binary_evidence = (
                    has_verified_valid_signature
                    or (has_trusted_path and not has_spoofed_admin_binary)
                    or has_trusted_hash
                    or has_mgmt_agent
                )
                if not has_trusted_binary_evidence:
                    unverified_binary_provenance = True
                    unverified_binary_detail = "Allowlisted binary name lacks rule-appropriate trusted binary evidence (path, signature, hash, or management confirmation)."

            # 8. Check Authoritative Authorization State, Scope, and Provenance (Reliability 1.3 & Phase A - Items 3, 4, 5)
            unapproved_auth_state = False
            auth_state_detail = ""
            unapproved_states = {
                "draft", "pending", "pending_approval", "rejected", "denied",
                "cancelled", "canceled", "expired", "closed", "revoked", "unknown"
            }
            approved_states = {"approved", "active", "implemented", "implementing", "authorized", "validated"}

            has_ticket_record = any(r.source_field in authoritative_auth_fields for r in normalization_result.records)
            status_records = [
                r for r in normalization_result.records
                if r.source_field in (
                    "authorization.status", "authorization.approval_state", "authorization.state",
                    "itsm.status", "itsm.state", "change_ticket.status"
                )
            ]

            # Phase A - Item 4: Treat absent authorization attributes as unknown, not approved
            if has_ticket_record:
                if not status_records:
                    unapproved_auth_state = True
                    auth_state_detail = "UNKNOWN (authorization status attribute absent)"
                else:
                    for r in status_records:
                        val_clean = str(r.observed_value).strip().lower()
                        if val_clean in unapproved_states or (val_clean not in approved_states and not any(s in val_clean for s in ("approv", "authoriz", "valid", "active"))):
                            unapproved_auth_state = True
                            auth_state_detail = str(r.observed_value)
                            break
            elif status_records:
                for r in status_records:
                    val_clean = str(r.observed_value).strip().lower()
                    if val_clean in unapproved_states or (val_clean not in approved_states and not any(s in val_clean for s in ("approv", "authoriz", "valid", "active"))):
                        unapproved_auth_state = True
                        auth_state_detail = str(r.observed_value)
                        break

            # Phase A - Item 5: Verify authoritative evidence provenance and prevent untrusted SIEM fields from masquerading as validated ITSM approvals
            untrusted_auth_provenance = False
            untrusted_auth_detail = ""
            untrusted_provenance_sources = {
                "untrusted", "rawsyslog", "userpayload", "telemetrycommandline",
                "siem_raw", "user_input", "adversary_content"
            }
            for r in normalization_result.records:
                if r.source_field in authoritative_auth_fields or r.source_field in (
                    "authorization.status", "authorization.approval_state", "authorization.state",
                    "itsm.status", "itsm.state", "change_ticket.status"
                ):
                    src_sys = str(r.source_system or "").strip().lower()
                    if src_sys in untrusted_provenance_sources or any(u in src_sys for u in ("untrusted", "rawsyslog", "userpayload")):
                        untrusted_auth_provenance = True
                        untrusted_auth_detail = f"Record '{r.source_field}' originates from untrusted source '{r.source_system}'"
                        break
                    if r.source_field in ("rawmsg", "user_note", "description", "command_line", "untrusted_payload"):
                        untrusted_auth_provenance = True
                        untrusted_auth_detail = f"Record '{r.source_field}' is an unverified free-text/raw field"
                        break

            # Scope / Hostname validation
            scope_mismatch = False
            scope_mismatch_detail = ""
            auth_target_hosts = [str(r.observed_value).strip().lower() for r in normalization_result.records if r.source_field in ("authorization.target_host", "authorization.hostname", "authorization.scope", "itsm.target_host", "authorization.target_asset")]
            inc_hosts = [str(r.observed_value).strip().lower() for r in normalization_result.records if r.source_field in ("host.name", "endpoint.hostname", "source_host", "destination_host", "host")]
            if auth_target_hosts and inc_hosts:
                auth_h = auth_target_hosts[0]
                inc_h = inc_hosts[0]
                if auth_h != inc_h and auth_h not in inc_h and inc_h not in auth_h:
                    scope_mismatch = True
                    scope_mismatch_detail = f"Ticket target '{auth_target_hosts[0]}' does not match incident host '{inc_hosts[0]}'"

            # 9. Check Grounded Claims Substance: Cannot rely solely on internal IP or user account existence
            grounded_claims = [c for c in claim_grounding.claims if c.is_grounded]
            grounded_fields = {c.field for c in grounded_claims if c.field}
            only_unprivileged_identities = bool(grounded_fields and grounded_fields.issubset({
                "network.source_ip", "network.destination_ip", "source_ip", "dest_ip", "user.name", "user"
            }))

            # 10. Check for Grounded Affirmative Authorization or Trusted Administrative Software (Phase A - Item 2)
            # Signed binaries and approved paths alone CANNOT establish benign authorization.
            has_grounded_authorization = False
            for c in grounded_claims:
                c_field_lower = str(c.field or "").lower()
                c_val_lower = str(c.asserted_value or "").lower()
                # A: Authoritative authorization / maintenance field (verified in-scope, approved, and trusted provenance)
                if c_field_lower in authoritative_auth_fields and not unapproved_auth_state and not scope_mismatch and not untrusted_auth_provenance:
                    has_grounded_authorization = True
                    break
                # B: Approved enterprise administrative binary WITH verified vendor path and NOT spoofed
                if c_field_lower in ("process.name", "process.file_name") and c_val_lower in approved_management_binaries:
                    if not has_spoofed_admin_binary and not unverified_binary_provenance:
                        has_grounded_authorization = True
                        break

            # Evaluate Gates:
            if preflight.preflight_status == "INSUFFICIENT" or preflight.evidence_completeness < 0.5 or claim_grounding.grounded_claims == 0:
                final_verdict = "REQUIRES_ATTENTION"
                if validation_status not in ("REJECTED", "ABSTAINED"):
                    validation_status = "INSUFFICIENT_EVIDENCE"
                if "FP_CRITERIA_UNSATISFIED" not in reason_codes:
                    reason_codes.append("FP_CRITERIA_UNSATISFIED")
                action_directive = "Missing grounded claim or benign evidence prevents confirming false positive. Human verification required."

            elif has_adversary_tradecraft:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "EVIDENCE_CONTRADICTION" not in reason_codes:
                    reason_codes.append("EVIDENCE_CONTRADICTION")
                action_directive = "False positive rejected: active adversary attack tradecraft (e.g. obfuscated LOLBin execution) contradicts benign authorization."

            elif invented_tickets:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "INVENTED_CHANGE_TICKET" not in reason_codes:
                    reason_codes.append("INVENTED_CHANGE_TICKET")
                action_directive = f"False positive rejected: Model asserted invented or unverified change ticket(s) ({', '.join(invented_tickets)}) not present in canonical evidence."

            elif untrusted_cmdline_tickets:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "UNVERIFIED_COMMAND_LINE_TICKET" not in reason_codes:
                    reason_codes.append("UNVERIFIED_COMMAND_LINE_TICKET")
                action_directive = f"False positive rejected: Ticket reference(s) ({', '.join(untrusted_cmdline_tickets)}) originate solely from untrusted command-line parameters without authoritative ITSM authorization."

            elif untrusted_auth_provenance:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "UNTRUSTED_AUTHORIZATION_PROVENANCE" not in reason_codes:
                    reason_codes.append("UNTRUSTED_AUTHORIZATION_PROVENANCE")
                action_directive = f"False positive rejected: Authorization evidence originates from untrusted source ({untrusted_auth_detail})."

            elif has_invalid_signature:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "INVALID_DIGITAL_SIGNATURE" not in reason_codes:
                    reason_codes.append("INVALID_DIGITAL_SIGNATURE")
                action_directive = f"False positive rejected: Digital signature verification failed ({invalid_sig_detail})."

            elif has_pki_claim and not has_verified_valid_signature:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "UNVERIFIED_SIGNATURE_CLAIM" not in reason_codes:
                    reason_codes.append("UNVERIFIED_SIGNATURE_CLAIM")
                action_directive = "False positive rejected: Model asserted corporate PKI code signing, but canonical evidence lacks verified valid signature status."

            elif has_maintenance_claim and not has_grounded_maintenance:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "UNSUPPORTED_MAINTENANCE_CLAIM" not in reason_codes:
                    reason_codes.append("UNSUPPORTED_MAINTENANCE_CLAIM")
                action_directive = "False positive rejected: Model asserted maintenance window or scheduled activity, but no maintenance record or parameter exists in canonical telemetry."

            elif maintenance_expired:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "MAINTENANCE_WINDOW_EXPIRED" not in reason_codes:
                    reason_codes.append("MAINTENANCE_WINDOW_EXPIRED")
                detail_str = f" ({maintenance_time_detail})" if maintenance_time_detail else ""
                action_directive = f"False positive rejected: Scheduled maintenance window is inactive, expired, or out of time bounds{detail_str}."

            elif unapproved_auth_state:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "AUTHORIZATION_STATE_UNAPPROVED" not in reason_codes:
                    reason_codes.append("AUTHORIZATION_STATE_UNAPPROVED")
                action_directive = f"False positive rejected: Authoritative authorization status '{auth_state_detail}' is unapproved or inactive."

            elif scope_mismatch:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "AUTHORIZATION_SCOPE_MISMATCH" not in reason_codes:
                    reason_codes.append("AUTHORIZATION_SCOPE_MISMATCH")
                action_directive = f"False positive rejected: Authorization scope mismatch ({scope_mismatch_detail})."

            elif has_spoofed_admin_binary:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "SPOOFED_ADMIN_BINARY" not in reason_codes:
                    reason_codes.append("SPOOFED_ADMIN_BINARY")
                action_directive = f"False positive rejected: Process-name spoofing detected ({spoofed_detail})."

            elif unverified_binary_provenance:
                final_verdict = "REQUIRES_ATTENTION"
                validation_status = "REJECTED"
                if "UNVERIFIED_BINARY_PROVENANCE" not in reason_codes:
                    reason_codes.append("UNVERIFIED_BINARY_PROVENANCE")
                action_directive = f"False positive rejected: {unverified_binary_detail}"

            elif only_unprivileged_identities or not has_grounded_authorization:
                final_verdict = "REQUIRES_ATTENTION"
                if validation_status not in ("REJECTED", "ABSTAINED"):
                    validation_status = "INSUFFICIENT_EVIDENCE"
                if "FP_CRITERIA_UNSATISFIED" not in reason_codes:
                    reason_codes.append("FP_CRITERIA_UNSATISFIED")
                action_directive = "False positive rejected: requires independently verified affirmative authorization evidence. Internal IP, service accounts, or routine assertions alone cannot justify False Positive."

            elif not reason_codes and final_verdict == "FALSE_POSITIVE":
                is_decisive = True
                reason_codes.append("EVIDENCE_VALIDATED")
                action_directive = "Activity verified benign against approved detection baseline and verified authorization evidence."

        elif clean_prop_verdict == "REQUIRES_ATTENTION":
            final_verdict = "REQUIRES_ATTENTION"
            is_decisive = False
            if invalid_output_flag or "MODEL_OUTPUT_INVALID" in reason_codes:
                validation_status = "INVALID_MODEL_OUTPUT"
                action_directive = "Model returned invalid or malformed structured output; safely abstained and routed to analyst review."
            else:
                if not reason_codes:
                    reason_codes.append("EVIDENCE_VALIDATED")
                action_directive = "Follow standard SOC tier-1 investigation runbook for ambiguous telemetry."

        # Audit Verification Token (Cryptographically binds contract, verdict, evidence count, and policy digest)
        comp_part = f":{compilation_digest}" if compilation_digest else ""
        sig_payload = f"{incident_id}:{contract.contract_id}:{proposed_verdict}:{final_verdict}:{cls.VALIDATOR_VERSION}{comp_part}"
        replay_sig = hashlib.sha256(sig_payload.encode("utf-8")).hexdigest()[:16]

        return VerdictValidationResult(
            incident_id=incident_id,
            proposed_verdict=clean_prop_verdict,
            final_verdict=final_verdict,
            validation_status=validation_status,
            validation_reason_codes=reason_codes,
            is_decisive_accepted=is_decisive,
            evidence_completeness=preflight.evidence_completeness,
            grounding_ratio=claim_grounding.grounding_ratio,
            total_claims_count=claim_grounding.total_claims,
            grounded_claims_count=claim_grounding.grounded_claims,
            unsupported_claims_count=claim_grounding.unsupported_claims,
            missing_evidence_fields=preflight.missing_evidence_fields,
            unsupported_claims=unsupported_claims,
            detected_contradictions=contradictions,
            field_validation_status=getattr(preflight, "field_validation_status", {}),
            analyst_action_directive=action_directive,
            contract_id=contract.contract_id,
            contract_version=contract.version_number,
            validator_version=cls.VALIDATOR_VERSION,
            raw_model_confidence=raw_model_confidence,
            validated_confidence_display=raw_model_confidence if is_decisive else 0.0,
            replay_signature=replay_sig,
        )

    @classmethod
    def replay_validation(
        cls,
        incident_id: str,
        saved_evidence_records: List[Dict[str, Any]],
        contract_dict: Dict[str, Any],
        saved_model_output: Dict[str, Any],
    ) -> VerdictValidationResult:
        """
        Deterministic Replay Engine.
        Reconstructs the exact validation outcome from a saved evidence snapshot and contract.
        """
        from app.services.model_claim_extractor import ModelClaimExtractor
        from app.services.evidence_preflight_validator import EvidencePreflightValidator

        # Rehydrate canonical records
        records = [CanonicalEvidenceRecord(**r) for r in saved_evidence_records]
        by_type: Dict[str, List[CanonicalEvidenceRecord]] = {}
        by_field: Dict[str, List[CanonicalEvidenceRecord]] = {}
        for r in records:
            by_type.setdefault(r.evidence_type, []).append(r)
            by_field.setdefault(r.source_field, []).append(r)

        norm_result = EvidenceNormalizationResult(
            incident_id=incident_id,
            total_evidence_count=len(records),
            available_evidence_count=len(records),
            records=records,
            evidence_by_type=by_type,
            evidence_by_field=by_field,
        )

        contract = RuleEvidenceContract(**contract_dict)
        preflight = EvidencePreflightValidator.validate_preflight(incident_id, contract, norm_result, allow_simulation=True)
        grounding = ModelClaimExtractor.extract_and_ground_claims(incident_id, saved_model_output, norm_result)

        return cls.validate_verdict(
            incident_id=incident_id,
            proposed_verdict=saved_model_output.get("verdict", "REQUIRES_ATTENTION"),
            raw_model_confidence=float(saved_model_output.get("confidence", 0.0)),
            preflight=preflight,
            claim_grounding=grounding,
            normalization_result=norm_result,
            contract=contract,
            allow_simulation=True,
            model_reason=str(saved_model_output.get("reason", "")),
            contradictory_evidence=saved_model_output.get("contradictory_evidence") if isinstance(saved_model_output.get("contradictory_evidence"), list) else None,
        )
