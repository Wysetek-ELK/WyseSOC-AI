"""
AIS 2.8 — Deterministic Rule Definition Builder & Evidence Intelligence Engine.

Provides zero-bias, deterministic security engineering context for SOC alert evaluation:
1. RuleDefinitionBuilder:
   - Extracts full FortiSIEM detection rule definitions (pattern_logic, raw_rule_text,
     parsed_metadata, conditions, group-by, windows, exclusions).
   - Evaluates individual rule predicates deterministically against observed telemetry
     into MATCHED / NOT_MATCHED / UNKNOWN / NOT_EVALUABLE.
   - Supplied identically to Neutral (Mode A) and Policy-Assisted (Mode B) evaluation paths.

2. EvidenceIntelligenceEngine:
   - Classifies observed IPs (RFC1918 private, loopback, CGNAT, link-local, public routable)
     and NAT/proxy relationships using Python stdlib ipaddress.
   - Classifies endpoint file/process paths (Program Files vs System32 vs User Temp/AppData)
     and strictly separates download/network events from endpoint process execution.
   - Records explicit telemetry field presence/absence and digital signature reporting status
     so models never invent missing fields or unverified claims.
"""

from __future__ import annotations

import ipaddress
import os
import re
from typing import Any, Dict, List, Optional, Tuple


_COMMON_PORT_SERVICES: Dict[int, str] = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    123: "NTP",
    135: "MSRPC",
    137: "NetBIOS-NS",
    139: "NetBIOS-SSN",
    143: "IMAP",
    389: "LDAP",
    443: "HTTPS",
    445: "SMB",
    465: "SMTPS",
    587: "SMTP-Submission",
    636: "LDAPS",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    1521: "Oracle-DB",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    5985: "WinRM-HTTP",
    5986: "WinRM-HTTPS",
    6379: "Redis",
    8080: "HTTP-Alt",
    8443: "HTTPS-Alt",
}

_EXECUTABLE_EXTS = {
    ".exe", ".dll", ".sys", ".msi", ".msix", ".bat", ".cmd", ".ps1",
    ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta", ".scr", ".com", ".cpl",
}
_ARCHIVE_EXTS = {".zip", ".rar", ".7z", ".tar", ".gz", ".iso", ".img", ".cab"}
_DOCUMENT_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".rtf", ".csv", ".txt"}
_WEB_ASSET_EXTS = {".css", ".scss", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".woff", ".woff2", ".ico", ".map"}


def _collect_telemetry_map(
    incident_payload: Dict[str, Any],
    canonical_records: Optional[List[Any]] = None,
) -> Dict[str, List[Any]]:
    """Collects canonical and event telemetry values keyed by normalized field name."""
    collected: Dict[str, List[Any]] = {}

    def _add(k: str, v: Any) -> None:
        if v is None or v == "":
            return
        key = str(k).strip()
        if not key:
            return
        bucket = collected.setdefault(key, [])
        if v not in bucket:
            bucket.append(v)

    for rec in canonical_records or []:
        if isinstance(rec, dict):
            sf = rec.get("source_field") or rec.get("field")
            ov = rec.get("observed_value") if rec.get("observed_value") is not None else rec.get("value")
        else:
            sf = getattr(rec, "source_field", None)
            ov = getattr(rec, "observed_value", None)
        if sf and ov is not None:
            _add(str(sf), ov)

    for rec in incident_payload.get("canonical_evidence") or []:
        if isinstance(rec, dict):
            sf = rec.get("source_field") or rec.get("field")
            ov = rec.get("observed_value") if rec.get("observed_value") is not None else rec.get("value")
            if sf and ov is not None:
                _add(str(sf), ov)

    for top_k in ("source_ip", "reporting_device", "reporting_ip", "event_type", "severity", "title", "category", "subcategory"):
        if incident_payload.get(top_k):
            _add(top_k, incident_payload[top_k])

    for evt in incident_payload.get("events") or []:
        if not isinstance(evt, dict):
            continue
        if evt.get("event_type"):
            _add("event_type", evt["event_type"])
        attrs = evt.get("attributes") or evt.get("attribute") or {}
        if isinstance(attrs, dict):
            for ak, av in attrs.items():
                if not isinstance(av, (dict, list)):
                    _add(str(ak), av)

    return collected


class RuleDefinitionBuilder:
    """Builds complete, deterministic FortiSIEM rule specifications with predicate match statuses."""

    _PREDICATE_REGEX = re.compile(
        r"""([A-Za-z0-9_.\s]+?)\s+(NOT\s+IN|IN|=|!=|>=|<=|>|<|CONTAINS|REGEXP|MATCHES)\s+([^\r\n;]+?)(?=\s+(?:AND|OR)\s+|$)""",
        re.IGNORECASE,
    )

    @classmethod
    def classify_ip(cls, raw_ip: Any) -> Dict[str, Any]:
        return EvidenceIntelligenceEngine.classify_ip_address(raw_ip)

    @classmethod
    def parse_rule_predicates(cls, pattern_logic: str, raw_rule_text: str = "") -> Dict[str, Any]:
        text = (pattern_logic or "").strip() or (raw_rule_text or "").strip()
        clauses: List[Dict[str, Any]] = []
        group_by: List[str] = []
        window: Optional[str] = None
        threshold: Optional[str] = None
        exclusions: List[str] = []

        if not text:
            return {
                "clauses": clauses,
                "group_by": group_by,
                "window": window,
                "threshold": threshold,
                "exclusions": exclusions,
            }

        gb_match = re.search(r"Group\s+By\s*[:=]\s*([^\r\n]+)", text, re.IGNORECASE)
        if gb_match:
            group_by = [g.strip() for g in gb_match.group(1).split(",") if g.strip()]

        win_match = re.search(r"(?:Window|Time\s*Window|Within)\s*[:=]?\s*(\d+\s*(?:s|sec|seconds|m|min|minutes|h|hr|hours))", text, re.IGNORECASE)
        if win_match:
            window = win_match.group(1).strip()

        cnt_match = re.search(r"(?:COUNT\([^)]*\)|Aggregate\s+Count)\s*(>=|>|=|<=|<)\s*(\d+)", text, re.IGNORECASE)
        if cnt_match:
            threshold = f"COUNT {cnt_match.group(1)} {cnt_match.group(2)}"

        for line in text.splitlines():
            clean_line = line.strip()
            if not clean_line:
                continue
            if re.search(r"(exclude|exception|not\s+in\s+)", clean_line, re.IGNORECASE):
                exclusions.append(clean_line[:240])
            for m in cls._PREDICATE_REGEX.finditer(clean_line):
                lhs = m.group(1).strip(" ()\"")
                op = re.sub(r"\s+", " ", m.group(2).strip().upper())
                rhs = m.group(3).strip(" ()")
                if len(lhs) > 64 or lhs.lower().startswith("http"):
                    continue
                clauses.append({
                    "attribute": lhs,
                    "operator": op,
                    "expected": rhs[:240],
                })
                if len(clauses) >= 16:
                    break
            if len(clauses) >= 16:
                break

        return {
            "clauses": clauses,
            "group_by": group_by,
            "window": window,
            "threshold": threshold,
            "exclusions": exclusions[:8],
        }

    @classmethod
    def evaluate_predicates(
        cls,
        clauses: List[Dict[str, Any]],
        telemetry_map: Dict[str, List[Any]],
    ) -> List[Dict[str, Any]]:
        """Evaluates extracted FortiSIEM predicates deterministically without guessing."""
        evaluations: List[Dict[str, Any]] = []
        norm_lookup = {k.lower().replace(" ", "").replace("_", "").replace(".", ""): (k, vals) for k, vals in telemetry_map.items()}

        alias_map = {
            "eventtype": ["event_type", "security.event_type", "eventType"],
            "filename": ["file.name", "process.file_name", "fileName", "File Name"],
            "processname": ["process.name", "process.file_name", "procName"],
            "command": ["process.command_line", "Command Line", "commandLine"],
            "commandline": ["process.command_line", "Command Line", "commandLine"],
            "srcipaddr": ["network.source_ip", "source_ip", "srcIpAddr"],
            "destipaddr": ["network.destination_ip", "destIpAddr"],
            "hostname": ["endpoint.hostname", "reporting_device", "hostName", "Host Name"],
            "user": ["user.name", "user", "User"],
            "severity": ["severity"],
            "eventseverity": ["severity"],
        }

        for clause in clauses:
            attr = str(clause.get("attribute") or "")
            op = str(clause.get("operator") or "").upper()
            expected = str(clause.get("expected") or "")
            norm_attr = attr.lower().replace(" ", "").replace("_", "").replace(".", "")

            observed_vals: List[Any] = []
            if norm_attr in norm_lookup:
                observed_vals = list(norm_lookup[norm_attr][1])
            else:
                for cand in alias_map.get(norm_attr, []):
                    cand_norm = cand.lower().replace(" ", "").replace("_", "").replace(".", "")
                    if cand_norm in norm_lookup:
                        for v in norm_lookup[cand_norm][1]:
                            if v not in observed_vals:
                                observed_vals.append(v)

            if not observed_vals:
                evaluations.append({
                    "attribute": attr,
                    "operator": op,
                    "expected": expected,
                    "status": "UNKNOWN",
                    "observed_values": [],
                })
                continue

            exp_tokens = [
                t.strip().strip("\"'").lower()
                for t in re.split(r"[,|]", expected.strip("()[]"))
                if t.strip()
            ]
            obs_lower = [str(v).strip().lower() for v in observed_vals]

            status = "NOT_EVALUABLE"
            if op in ("IN", "="):
                if any(o == e or e in o for o in obs_lower for e in exp_tokens):
                    status = "MATCHED"
                elif exp_tokens:
                    status = "NOT_MATCHED"
            elif op in ("NOT IN", "!="):
                if any(o == e for o in obs_lower for e in exp_tokens):
                    status = "NOT_MATCHED"
                elif exp_tokens:
                    status = "MATCHED"
            elif op == "CONTAINS":
                if any(e in o for o in obs_lower for e in exp_tokens):
                    status = "MATCHED"
                elif exp_tokens:
                    status = "NOT_MATCHED"
            elif op in ("REGEXP", "MATCHES"):
                try:
                    pat = re.compile(expected.strip("\"'"), re.IGNORECASE)
                    status = "MATCHED" if any(pat.search(str(v)) for v in observed_vals) else "NOT_MATCHED"
                except re.error:
                    status = "NOT_EVALUABLE"

            evaluations.append({
                "attribute": attr,
                "operator": op,
                "expected": expected,
                "status": status,
                "observed_values": [str(v)[:160] for v in observed_vals[:5]],
            })

        return evaluations

    @classmethod
    def build_complete_rule_spec(
        cls,
        rule_obj: Any,
        canonical_records: Optional[List[Any]] = None,
        incident_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Builds a complete rule specification for equal parity across benchmark & live modes."""
        pattern_logic = str(getattr(rule_obj, "pattern_logic", "") or "").strip() if rule_obj else ""
        raw_rule_text = str(getattr(rule_obj, "raw_rule_text", "") or "").strip() if rule_obj else ""
        parsed_meta = getattr(rule_obj, "parsed_metadata", None) if rule_obj else None
        if not isinstance(parsed_meta, dict):
            parsed_meta = {}

        parsed = cls.parse_rule_predicates(pattern_logic, raw_rule_text)
        t_map = _collect_telemetry_map(incident_payload or {}, canonical_records)
        predicate_evals = cls.evaluate_predicates(parsed["clauses"], t_map)

        return {
            "id": str(getattr(rule_obj, "id", "") or "UNKNOWN"),
            "rule_id": getattr(rule_obj, "rule_id", None) if rule_obj else None,
            "name": getattr(rule_obj, "name", None) if rule_obj else "Unknown Detection Rule",
            "event_type": getattr(rule_obj, "event_type", None) if rule_obj else None,
            "severity": getattr(rule_obj, "severity", None) if rule_obj else None,
            "status": getattr(rule_obj, "status", None) if rule_obj else None,
            "data_source": getattr(rule_obj, "data_source", "") or "",
            "detection_tech": getattr(rule_obj, "detection_tech", "") or "",
            "evaluation_mode": getattr(rule_obj, "evaluation_mode", "") or "",
            "description": (getattr(rule_obj, "description", "") or "")[:1200],
            "pattern_logic": pattern_logic[:1600],
            "raw_rule_text": raw_rule_text[:1800],
            "parsed_metadata": parsed_meta,
            "conditions": parsed["clauses"],
            "group_by": parsed["group_by"],
            "window": parsed["window"],
            "threshold": parsed["threshold"],
            "exclusions": parsed["exclusions"],
            "predicate_evaluations": predicate_evals,
            "rule_definition_completeness": (
                "COMPLETE"
                if (pattern_logic or raw_rule_text or parsed["clauses"])
                else "METADATA_ONLY"
            ),
        }


class EvidenceIntelligenceEngine:
    """
    Deterministic factual evidence intelligence engine (Stage C / WS6).
    Never invents verdicts, external reputation, or authorization context.
    """

    @staticmethod
    def classify_ip_address(raw_ip: Any) -> Dict[str, Any]:
        ip_str = str(raw_ip or "").strip()
        if not ip_str:
            return {"ip": None, "classification": "ABSENT", "is_public": False, "is_rfc1918": False}
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return {"ip": ip_str, "classification": "INVALID_IP", "is_public": False, "is_rfc1918": False}

        cgnat_net = ipaddress.ip_network("100.64.0.0/10")
        test_nets = (
            ipaddress.ip_network("192.0.2.0/24"),
            ipaddress.ip_network("198.51.100.0/24"),
            ipaddress.ip_network("203.0.113.0/24"),
        )
        if ip_obj.is_loopback:
            cls_name = "LOOPBACK"
        elif ip_obj.is_link_local:
            cls_name = "LINK_LOCAL"
        elif ip_obj.version == 4 and ip_obj in cgnat_net:
            cls_name = "CGNAT_100_64"
        elif ip_obj.version == 4 and any(ip_obj in tn for tn in test_nets):
            cls_name = "DOCUMENTATION_TEST_NET"
        elif ip_obj.is_private:
            cls_name = "RFC1918_PRIVATE"
        elif ip_obj.is_multicast:
            cls_name = "MULTICAST"
        elif ip_obj.is_reserved or ip_obj.is_unspecified:
            cls_name = "RESERVED_SPECIAL"
        else:
            cls_name = "PUBLIC_ROUTABLE"

        return {
            "ip": ip_str,
            "version": ip_obj.version,
            "classification": cls_name,
            "is_public": cls_name == "PUBLIC_ROUTABLE",
            "is_rfc1918": cls_name == "RFC1918_PRIVATE",
        }

    @staticmethod
    def classify_path(path_value: Any) -> Dict[str, Any]:
        raw = str(path_value or "").strip()
        if not raw:
            return {"raw_path": None, "path_zone": "NOT_PRESENT"}
        low = raw.lower().replace("/", "\\")
        if "\\windows\\system32\\" in low or "\\windows\\syswow64\\" in low or low.startswith("c:\\windows\\"):
            zone = "WINDOWS_SYSTEM_DIR"
        elif "\\program files (x86)\\" in low or "\\program files\\" in low:
            zone = "PROGRAM_FILES"
        elif "\\appdata\\local\\temp\\" in low or "\\windows\\temp\\" in low or "\\temp\\" in low or "\\tmp\\" in low:
            zone = "WRITABLE_TEMP_DIR"
        elif "\\appdata\\" in low or "\\users\\" in low and "\\downloads\\" in low:
            zone = "USER_PROFILE_OR_DOWNLOADS"
        elif "\\programdata\\" in low:
            zone = "PROGRAMDATA"
        elif raw.startswith(("/usr/bin/", "/bin/", "/sbin/", "/usr/sbin/")):
            zone = "UNIX_SYSTEM_BIN"
        elif raw.startswith(("/tmp/", "/var/tmp/", "/dev/shm/")):
            zone = "WRITABLE_TEMP_DIR"
        else:
            zone = "OTHER_OR_RELATIVE_PATH"

        return {
            "raw_path": raw[:320],
            "path_zone": zone,
            "is_program_files": zone == "PROGRAM_FILES",
            "is_temp_directory": zone == "WRITABLE_TEMP_DIR",
        }

    @staticmethod
    def classify_file_extension(filename: Any) -> str:
        clean = str(filename or "").strip().lower()
        if not clean or "." not in clean:
            return "NO_EXTENSION"
        _, ext = os.path.splitext(clean)
        if ext in _EXECUTABLE_EXTS:
            return "EXECUTABLE_OR_SCRIPT"
        if ext in _ARCHIVE_EXTS:
            return "ARCHIVE"
        if ext in _DOCUMENT_EXTS:
            return "DOCUMENT"
        if ext in _WEB_ASSET_EXTS:
            return "WEB_STATIC_OR_ASSET"
        return f"OTHER ({ext})"

    @classmethod
    def enrich_incident_evidence(
        cls,
        incident_payload: Dict[str, Any],
        canonical_records: Optional[List[Any]] = None,
    ) -> Dict[str, Any]:
        """Produces deterministic factual intelligence summary for LLM grounding and validation."""
        t_map = _collect_telemetry_map(incident_payload, canonical_records)

        def _first(*keys: str) -> Optional[Any]:
            for k in keys:
                vals = t_map.get(k)
                if vals:
                    return vals[0]
            return None

        src_ip = _first("network.source_ip", "source_ip", "srcIpAddr", "Source IP")
        dst_ip = _first("network.destination_ip", "destIpAddr", "Destination IP")
        ep_ip = _first("endpoint.ip", "reporting_ip", "hostIpAddr", "telemetry.host ip")
        nat_ip = _first("network.nat_ip", "postNATSrcIpAddr", "natIp")

        src_cls = cls.classify_ip_address(src_ip)
        dst_cls = cls.classify_ip_address(dst_ip)
        ep_cls = cls.classify_ip_address(ep_ip)
        nat_cls = cls.classify_ip_address(nat_ip)

        dst_port_raw = _first("network.destination_port", "destIpPort", "Destination Port")
        dst_port_service = None
        if dst_port_raw is not None:
            try:
                p_int = int(float(str(dst_port_raw)))
                dst_port_service = _COMMON_PORT_SERVICES.get(p_int, f"PORT_{p_int}")
            except (ValueError, TypeError):
                dst_port_service = None

        has_nat = bool(
            nat_ip
            or (src_cls.get("is_rfc1918") and dst_cls.get("is_public"))
        )

        cmdline = _first("process.command_line", "process.cmdline", "Command Line", "commandLine", "Command")
        proc_name = _first("process.file_name", "process.name", "procName", "Process Name")
        proc_path = _first("process.image_path", "ImageFile", "imagePath") or cmdline
        parent_proc = _first("process.parent_name", "parentProcess", "ParentProcessName")
        parent_cmd = _first("process.parent_command_line", "parentCommandLine")
        proc_blocked = _first("endpoint.process_blocked", "Process Blocked", "process_blocked")
        file_quarantined = _first("endpoint.file_quarantined", "File Quarantined", "file_quarantined")

        file_name = _first("file.name", "process.file_name", "fileName", "File Name")
        http_url = _first("http.url", "requestUrl", "url", "URL")
        web_cat = _first("web.category", "webCategory", "catdesc", "Web Category")
        app_name = _first("application.name", "network.application", "appName", "Application")
        sig_val = _first("process.signature", "file.signature", "signature", "signer", "Signed", "AuthenticodeStatus")

        hashes: Dict[str, str] = {}
        for h_key, h_vals in t_map.items():
            kl = h_key.lower()
            if "sha256" in kl or kl in ("file.hash", "hash"):
                val_s = str(h_vals[0]).strip()
                if re.fullmatch(r"[0-9a-fA-F]{64}", val_s):
                    hashes["sha256"] = val_s.lower()
                elif re.fullmatch(r"[0-9a-fA-F]{40}", val_s):
                    hashes["sha1"] = val_s.lower()
                elif re.fullmatch(r"[0-9a-fA-F]{32}", val_s):
                    hashes["md5"] = val_s.lower()
            elif "md5" in kl:
                hashes["md5"] = str(h_vals[0]).strip().lower()
            elif "sha1" in kl:
                hashes["sha1"] = str(h_vals[0]).strip().lower()

        path_info = cls.classify_path(proc_path)
        has_process_execution = bool(cmdline or proc_name or _first("process.id", "pid", "ppid", "Process ID"))
        has_network_file_transfer = bool(
            http_url or (file_name and (web_cat or app_name or _first("network.application_category", "network.direction")))
        ) and not has_process_execution

        present_canonical_fields = sorted(
            {
                k for k in t_map.keys()
                if "." in k or k in ("source_ip", "reporting_device", "reporting_ip", "event_type", "severity")
            }
        )
        forensic_checklist = [
            "endpoint.hostname",
            "user.name",
            "process.file_name",
            "process.command_line",
            "process.parent_name",
            "file.name",
            "file.hash",
            "http.url",
            "network.source_ip",
            "network.destination_ip",
            "endpoint.process_blocked",
            "endpoint.file_quarantined",
        ]
        present_set = set(present_canonical_fields)
        present_forensic = [f for f in forensic_checklist if f in present_set]
        absent_forensic = [f for f in forensic_checklist if f not in present_set]

        return {
            "network_classification": {
                "source_ip": src_cls,
                "destination_ip": dst_cls,
                "endpoint_ip": ep_cls,
                "nat_ip": nat_cls,
                "destination_port_service": dst_port_service,
                "nat_or_proxy_translation_present": has_nat,
            },
            "endpoint_process_classification": {
                "process_name": str(proc_name) if proc_name else None,
                "command_line_present": bool(cmdline),
                "command_line": str(cmdline)[:320] if cmdline else None,
                "parent_process": str(parent_proc) if parent_proc else None,
                "parent_command_line": str(parent_cmd)[:240] if parent_cmd else None,
                "path_classification": path_info,
                "execution_evidence_present": has_process_execution,
                "download_only_evidence_present": has_network_file_transfer,
                "process_blocked": proc_blocked,
                "file_quarantined": file_quarantined,
                "digital_signature_status": str(sig_val) if sig_val is not None else "NOT_REPORTED_IN_TELEMETRY",
            },
            "file_and_web_context": {
                "file_name": str(file_name) if file_name else None,
                "file_extension_class": cls.classify_file_extension(file_name) if file_name else "ABSENT",
                "hashes": hashes,
                "http_url": str(http_url)[:320] if http_url else None,
                "web_category": str(web_cat) if web_cat else None,
                "application_name": str(app_name) if app_name else None,
            },
            "telemetry_field_presence": {
                "present_fields": present_canonical_fields,
                "present_forensic_fields": present_forensic,
                "absent_forensic_fields": absent_forensic,
                "canonical_record_count": len(canonical_records or incident_payload.get("canonical_evidence") or []),
            },
        }
