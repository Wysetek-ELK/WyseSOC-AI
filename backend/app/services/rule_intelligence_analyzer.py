import re
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from app.models.rule import Rule
from app.schemas.rule_intelligence import (
    DetectionSemantics,
    SemanticsDefinitionStatus,
    SourceProvenance,
    ArchetypeId,
)

logger = logging.getLogger("ai_verdict.rule_intelligence")


class RuleIntelligenceAnalyzer:
    """
    REQ-01: Authoritative Detection Rule Intelligence Analyzer.
    Analyzes SIEM detection rules to extract structured detection semantics.
    Enforces the strict input hierarchy:
      1. Authoritative SIEM rule definition and version
      2. Parsed detection conditions
      3. Vendor detection metadata (ATT&CK, category)
      4. Available telemetry field definitions
      5. Verified rule documentation
      6. Observed incident samples (attributes only, NEVER thresholds)
      7. Rule name and keyword hints
    
    Guarantees:
      - Incident values CANNOT silently become rule thresholds.
      - Missing detection logic remains UNKNOWN or INCOMPLETE.
      - Vendor-specific operators are preserved.
      - Incomplete rules trigger review requirements.
    """
    ANALYZER_VERSION = "v2.0.0"

    @classmethod
    def analyze_rule(
        cls,
        rule: Rule,
        authoritative_siem_definition: Optional[Dict[str, Any]] = None,
        observed_incident_sample: Optional[Dict[str, Any]] = None,
    ) -> DetectionSemantics:
        """
        Builds a comprehensive DetectionSemantics model for the given rule.
        """
        rule_identifier = getattr(rule, "rule_id", None) or getattr(rule, "event_type", "UNKNOWN_RULE")
        rule_name = getattr(rule, "name", "") or rule_identifier
        raw_metadata = getattr(rule, "parsed_metadata", {}) or {}
        raw_pattern = getattr(rule, "pattern_logic", "") or ""
        raw_text = getattr(rule, "raw_rule_text", "") or ""
        data_source = getattr(rule, "data_source", "") or "FortiSIEM"

        provenance_details: Dict[str, str] = {}
        missing_requirements: List[str] = []
        observed_fields: List[str] = []

        # 1. Determine Source Provenance
        if authoritative_siem_definition:
            source_prov = SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION
            source_version = str(authoritative_siem_definition.get("version") or "1.0")
            prov_note = "Extracted from authoritative live SIEM supervisor definition"
        elif raw_metadata.get("source") in ("FORTISIEM_LIVE_RULE_API", "AUTHORITATIVE_XML_IMPORT") or raw_metadata.get("provenance") in ("AUTHORITATIVE_XML_IMPORT", "AUTHORITATIVE_SIEM_DEFINITION"):
            source_prov = SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION
            source_version = str(raw_metadata.get("version") or "1.0")
            prov_note = "Extracted from authoritative XML/rule definition import"
        elif raw_text and ("Pattern Conditions:" in raw_text or "Pattern:" in raw_text) and raw_metadata.get("source") != "AUTO_SYNCED_FROM_INCIDENT":
            source_prov = SourceProvenance.VENDOR_RULE_FILE
            source_version = "1.0"
            prov_note = "Extracted from vendor rule text file"
        elif raw_metadata.get("source") == "AUTO_SYNCED_FROM_INCIDENT":
            source_prov = SourceProvenance.AUTO_SYNCED_FROM_INCIDENT
            source_version = "unversioned"
            prov_note = "Rule was automatically registered from incident telemetry cache-miss"
        else:
            source_prov = SourceProvenance.HEURISTIC_PARSER
            source_version = "unversioned"
            prov_note = "Inferred from available metadata and naming"

        provenance_details["rule_origin"] = prov_note

        # 2. Extract Event Category & Sub-Category
        category = (
            (authoritative_siem_definition and authoritative_siem_definition.get("category"))
            or raw_metadata.get("category")
            or raw_metadata.get("phIncidentCategory")
            or ""
        )
        sub_category = (
            (authoritative_siem_definition and authoritative_siem_definition.get("sub_category"))
            or raw_metadata.get("subCategory")
            or raw_metadata.get("phSubIncidentCategory")
            or raw_metadata.get("incidentTagName")
            or getattr(rule, "detection_tech", "")
            or ""
        )

        # 3. Extract MITRE ATT&CK Metadata
        attck_tactics: List[str] = []
        attck_techniques: List[str] = []
        if raw_metadata.get("attackTactic"):
            t = raw_metadata.get("attackTactic")
            attck_tactics = [t] if isinstance(t, str) else list(t)
        if raw_metadata.get("attackTechnique"):
            tech = raw_metadata.get("attackTechnique")
            attck_techniques = [tech] if isinstance(tech, str) else list(tech)

        # 4. Analyze Detection Pattern & Conditions
        conditions: List[Dict[str, Any]] = []
        boolean_operators: List[str] = []
        threshold: Optional[float] = None
        threshold_unit: Optional[str] = None
        aggregation_window: Optional[str] = None
        grouping_keys: List[str] = []
        suppression_conditions: List[str] = []
        primary_behavior_override: Optional[str] = None

        if authoritative_siem_definition and isinstance(authoritative_siem_definition, dict):
            if authoritative_siem_definition.get("threshold") is not None:
                try:
                    threshold = float(authoritative_siem_definition["threshold"])
                except (ValueError, TypeError):
                    threshold = None
            if authoritative_siem_definition.get("threshold_unit"):
                threshold_unit = str(authoritative_siem_definition["threshold_unit"])
            if authoritative_siem_definition.get("aggregation_window"):
                aggregation_window = str(authoritative_siem_definition["aggregation_window"])
            if authoritative_siem_definition.get("grouping_keys"):
                grouping_keys = list(authoritative_siem_definition["grouping_keys"])
            if authoritative_siem_definition.get("conditions"):
                conditions = list(authoritative_siem_definition["conditions"])
            if authoritative_siem_definition.get("primary_behavior"):
                primary_behavior_override = str(authoritative_siem_definition["primary_behavior"])

        is_authoritative = (source_prov in (SourceProvenance.AUTHORITATIVE_SIEM_DEFINITION, SourceProvenance.VENDOR_RULE_FILE))

        # Check for incident-derived pseudo-pattern or runtime counter string (e.g. {"sentBytes64": 2130499380}, incidentCount=3)
        # Runtime incident counters MUST NOT be mistaken for authoritative rule correlation thresholds.
        pattern_is_incident_dump = False
        parsed_json_pattern = None
        if raw_pattern.strip().startswith("{") and raw_pattern.strip().endswith("}"):
            try:
                parsed_json_pattern = json.loads(raw_pattern)
                if isinstance(parsed_json_pattern, dict):
                    observed_fields.extend(list(parsed_json_pattern.keys()))
                    if not is_authoritative or source_prov == SourceProvenance.AUTO_SYNCED_FROM_INCIDENT or any(
                        rk in raw_pattern for rk in ("incidentCount", "incidentDetail", "incidentId")
                    ):
                        pattern_is_incident_dump = True
            except Exception:
                pass
        elif raw_pattern.strip() and (
            ("incidentCount" in raw_pattern or "incidentDetail" in raw_pattern)
            and "COUNT(" not in raw_pattern
            and "Pattern Conditions:" not in raw_text
        ):
            pattern_is_incident_dump = True

        if observed_incident_sample and isinstance(observed_incident_sample, dict):
            for k in observed_incident_sample.keys():
                if k not in observed_fields:
                    observed_fields.append(k)

        # Parse Authoritative Conditions if genuinely present
        if authoritative_siem_definition and (threshold is not None or conditions or grouping_keys):
            provenance_details["authoritative_parameters"] = "Threshold and conditions verified from live SIEM definition"
        elif is_authoritative and not pattern_is_incident_dump and raw_pattern:
            # Parse text condition lines like "sentBytes64 > 100000000", "COUNT(Matched Events) >= 1", "window: 5m", "groupBy: srcIp"
            cls._parse_authoritative_pattern(
                pattern_text=raw_pattern,
                conditions=conditions,
                boolean_operators=boolean_operators,
                grouping_keys=grouping_keys,
                suppression_conditions=suppression_conditions,
                provenance_details=provenance_details,
            )
            threshold, threshold_unit = cls._extract_threshold_from_conditions(conditions)
            aggregation_window = cls._extract_window_from_text_or_conditions(raw_text or raw_pattern, conditions)
            if threshold == 1.0 and "single match" in str(threshold_unit):
                provenance_details["threshold_semantics"] = "COUNT >= 1 indicates single-event occurrence trigger; not an aggregated volume threshold."
        elif pattern_is_incident_dump:
            # Explicitly log that observed values must not become verified thresholds
            obs_keys = list(parsed_json_pattern.keys()) if isinstance(parsed_json_pattern, dict) else ["runtime_counter"]
            provenance_details["pattern_warning"] = (
                f"Observed pattern metadata {obs_keys} represents runtime incident "
                "telemetry counters/attributes. It is NOT an authoritative SIEM rule correlation threshold."
            )
            missing_requirements.append("Authoritative SIEM detection condition and threshold definition missing")
            missing_requirements.append("Aggregation window and grouping keys unverified")
        else:
            missing_requirements.append("SIEM pattern logic is empty or unparseable")

        # Extract Triggered Event Attributes if present
        triggered_attrs = raw_metadata.get("triggered_attributes", [])
        if not triggered_attrs and raw_text and "Triggered Event Attributes" in raw_text:
            m_trig = re.search(r"Triggered Event Attributes\r?\n([^\r\n]+)", raw_text)
            if m_trig:
                triggered_attrs = [a.strip() for a in m_trig.group(1).split(",") if a.strip()]

        if triggered_attrs:
            provenance_details["triggered_attributes"] = ", ".join(triggered_attrs)
            for attr in triggered_attrs:
                if attr not in observed_fields:
                    observed_fields.append(attr)

        # 5. Extract Source and Destination Semantics
        src_sem, dest_sem = cls._extract_entity_semantics(rule, category, sub_category)

        # 6. Map Relevant Fields based on category & rule behavior
        relevant_fields = cls._determine_relevant_fields(rule_identifier, rule_name, category, sub_category, observed_fields)
        if triggered_attrs:
            for attr in triggered_attrs:
                canon = cls.ATTRIBUTE_TO_CANONICAL.get(attr)
                if canon and canon not in relevant_fields:
                    relevant_fields.append(canon)

        # 7. Identify Primary Behavior (Candidate Archetype)
        primary_behavior = primary_behavior_override or cls._infer_primary_behavior(
            rule_identifier=rule_identifier,
            rule_name=rule_name,
            category=category,
            sub_category=sub_category,
            attck_tactics=attck_tactics,
            observed_fields=observed_fields,
        )

        # 8. Determine Definition Status & Review Requirement
        # Mandatory reference case check:
        # PH_RULE_LARGE_OUTBOUND_XFER with auto-synced telemetry and no authoritative SIEM definition
        if source_prov == SourceProvenance.AUTO_SYNCED_FROM_INCIDENT or not is_authoritative:
            definition_status = SemanticsDefinitionStatus.INCOMPLETE
            review_required = True
        elif missing_requirements:
            definition_status = SemanticsDefinitionStatus.INCOMPLETE
            review_required = True
        elif not conditions and not raw_pattern and not raw_text and not (authoritative_siem_definition and (threshold is not None or grouping_keys)):
            definition_status = SemanticsDefinitionStatus.INCOMPLETE
            missing_requirements.append("SIEM detection logic is empty; cannot be verified")
            review_required = True
        else:
            definition_status = SemanticsDefinitionStatus.VERIFIED
            review_required = False

        detection_obj = cls._build_detection_objective(primary_behavior, rule_name, category)

        return DetectionSemantics(
            rule_identifier=rule_identifier,
            rule_name=rule_name,
            siem_vendor="FortiSIEM",
            data_source=data_source,
            tenant_scope=raw_metadata.get("customer"),
            event_category=category,
            sub_category=sub_category,
            detection_objective=detection_obj,
            conditions=conditions,
            boolean_operators=boolean_operators,
            threshold=threshold,
            threshold_unit=threshold_unit,
            aggregation_window=aggregation_window,
            grouping_keys=grouping_keys,
            suppression_conditions=suppression_conditions,
            source_semantics=src_sem,
            destination_semantics=dest_sem,
            relevant_fields=relevant_fields,
            observed_fields=observed_fields,
            attck_tactics=attck_tactics,
            attck_techniques=attck_techniques,
            primary_behavior=primary_behavior,
            definition_status=definition_status,
            source_provenance=source_prov,
            provenance_details=provenance_details,
            review_required=review_required,
            missing_requirements=missing_requirements,
        )

    ATTRIBUTE_TO_CANONICAL: Dict[str, str] = {
        "Host Name": "endpoint.hostname",
        "User": "user.name",
        "Command": "process.command_line",
        "File Name": "file.name",
        "Attack Tactic": "mitre.tactic",
        "Attack Technique": "mitre.technique",
        "Process Blocked": "endpoint.process_blocked",
        "File Quarantined": "endpoint.file_quarantined",
        "Machine Quarantined": "endpoint.machine_quarantined",
        "Informational URL": "intel.url",
        "Raw Event Log": "event.raw_log",
        "Event Receive Time": "event.timestamp",
        "Source IP": "network.source_ip",
        "Destination IP": "network.destination_ip",
        "Destination Port": "network.destination_port",
    }

    @classmethod
    def _parse_authoritative_pattern(
        cls,
        pattern_text: str,
        conditions: List[Dict[str, Any]],
        boolean_operators: List[str],
        grouping_keys: List[str],
        suppression_conditions: List[str],
        provenance_details: Dict[str, str],
    ) -> None:
        """Parses vendor rule text conditions into structured condition objects."""
        lines = pattern_text.splitlines()
        in_group_by_block = False

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Check if entering/exiting a GROUP BY block
            if re.match(r"^(?:Pattern|IF|WHERE|OCCURS|Incidents|Watch Lists|Triggered Event Attributes|HAVING|ORDER BY)\b", line_str, re.IGNORECASE):
                in_group_by_block = False

            if in_group_by_block:
                keys = [k.strip() for k in line_str.split(",") if k.strip()]
                if keys:
                    grouping_keys.extend(keys)
                continue

            # Check for boolean operators
            if re.search(r"\bAND\b", line_str, re.IGNORECASE):
                boolean_operators.append("AND")
            if re.search(r"\bOR\b", line_str, re.IGNORECASE):
                boolean_operators.append("OR")
            if re.search(r"\bNOT\b", line_str, re.IGNORECASE):
                boolean_operators.append("NOT")

            # Check for grouping keys
            inline_group = re.search(r"(?:group\s*by|groupBy)\s*(?:[:=]|\s+)\s*([^\n;]+)", line_str, re.IGNORECASE)
            if inline_group and inline_group.group(1).strip():
                rest = inline_group.group(1).strip()
                if not rest.upper().startswith("BY"):
                    keys = [k.strip() for k in rest.split(",") if k.strip()]
                    grouping_keys.extend(keys)
                else:
                    in_group_by_block = True
                continue
            elif line_str.upper() in ("GROUP BY", "GROUPBY"):
                in_group_by_block = True
                continue

            # Check for threshold / window / comparison conditions (supports COUNT(Matched Events), Event Type IN ..., etc.)
            cond_match = re.search(r"([a-zA-Z0-9_\.\(\)\s]+?)\s*(>=|<=|>|<|==|=|!=|\bIN\b|\bCONTAINS\b)\s*([^\n;]+)", line_str, re.IGNORECASE)
            if cond_match:
                field, op, val = cond_match.groups()
                field_clean = field.strip()
                if field_clean.upper() not in ("WHERE", "IF", "AND", "OR", "NOT"):
                    conditions.append({
                        "field": field_clean,
                        "operator": op.strip().upper(),
                        "value": val.strip(),
                        "raw": line_str,
                    })
            elif "suppress" in line_str.lower() or "exclude" in line_str.lower():
                suppression_conditions.append(line_str)

        provenance_details["parsed_conditions_count"] = str(len(conditions))

    @classmethod
    def _extract_threshold_from_conditions(cls, conditions: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[str]]:
        for c in conditions:
            val_str = c.get("value", "")
            field = c.get("field", "").lower()
            field_compact = re.sub(r"[^a-z0-9]", "", field)
            # Reject runtime incident counters masquerading as rule correlation thresholds
            if field_compact in ("incidentcount", "incidentdetail", "incidentid", "eventcount", "totalcount"):
                continue
            if any(term in field for term in ("byte", "count", "size", "rate", "threshold", "volume")):
                # Check for numeric match
                num_match = re.search(r"(\d+(?:\.\d+)?)", val_str)
                if num_match:
                    try:
                        num = float(num_match.group(1))
                        if "byte" in field:
                            unit = "bytes"
                        elif "count" in field:
                            unit = "event (single match trigger)" if num == 1.0 else "events (aggregation threshold)"
                        else:
                            unit = "count"
                        return num, unit
                    except Exception:
                        pass
        return None, None

    @classmethod
    def _extract_window_from_text_or_conditions(
        cls, raw_text: str, conditions: List[Dict[str, Any]]
    ) -> Optional[str]:
        if raw_text:
            m = re.search(r"(?:in any|within|over a?)\s*(\d+)\s*(second|sec|minute|min|hour|hr)s?\s*(?:time\s*)?window", raw_text, re.IGNORECASE)
            if m:
                val, unit = m.groups()
                return f"{val} {unit}s"
            m2 = re.search(r"(?:window|aggregation_window)\s*[:=]\s*([a-zA-Z0-9_\s]+)", raw_text, re.IGNORECASE)
            if m2:
                return m2.group(1).strip()
        for c in conditions:
            field = c.get("field", "").lower()
            val_str = c.get("value", "")
            if "window" in field or "duration" in field or "time" in field:
                return val_str.strip()
        return None

    @classmethod
    def _extract_window_from_conditions(cls, conditions: List[Dict[str, Any]]) -> Optional[str]:
        return cls._extract_window_from_text_or_conditions("", conditions)

    @classmethod
    def _extract_entity_semantics(cls, rule: Rule, category: str, sub_category: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        norm = f"{category} {sub_category} {rule.name}".lower()
        if "outbound" in norm or "exfiltration" in norm or "traffic" in norm:
            src = {"type": "INTERNAL_HOST_OR_USER", "description": "Internal host or user initiating transfer"}
            dest = {"type": "EXTERNAL_ENDPOINT_OR_IP", "description": "External target destination or remote entity"}
        elif "inbound" in norm or "web" in norm:
            src = {"type": "EXTERNAL_SOURCE_IP", "description": "Remote external source client/adversary"}
            dest = {"type": "INTERNAL_PROTECTED_ASSET", "description": "Internal protected server/service"}
        elif "process" in norm or "malware" in norm:
            src = {"type": "LOCAL_SYSTEM_OR_ENDPOINT", "description": "Host endpoint executing binary"}
            dest = {"type": "TARGET_SYSTEM_RESOURCES", "description": "Local process tree / filesystem"}
        else:
            src = {"type": "ORIGINATING_ENTITY", "description": "Source identity or network entity"}
            dest = {"type": "TARGET_ENTITY", "description": "Target identity or network entity"}
        return src, dest

    @classmethod
    def _determine_relevant_fields(
        cls,
        rule_identifier: str,
        rule_name: str,
        category: str,
        sub_category: str,
        observed_fields: List[str]
    ) -> List[str]:
        combo = f"{rule_identifier} {rule_name} {category} {sub_category}".lower()
        fields = []
        if "exfiltration" in combo or "outbound" in combo or "xfer" in combo or "transfer" in combo:
            fields = [
                "network.source_ip",
                "network.destination_ip",
                "network.destination_port",
                "network.direction",
                "network.bytes_out",
                "network.sent_bytes",
                "event.timestamp",
                "user.name",
                "network.destination_domain",
            ]
        elif "process" in combo or "execution" in combo or "powershell" in combo or "crowdstrike" in combo:
            fields = [
                "process.command_line",
                "process.name",
                "process.parent_name",
                "user.name",
                "endpoint.hostname",
            ]
        elif "malware" in combo or "file" in combo or "hash" in combo:
            fields = [
                "file.hash_sha256",
                "file.path",
                "file.name",
                "endpoint.hostname",
                "user.name",
            ]
        elif "auth" in combo or "login" in combo or "brute" in combo:
            fields = [
                "user.name",
                "network.source_ip",
                "endpoint.hostname",
                "auth.result",
                "auth.failure_count",
            ]
        elif "dns" in combo or "tunnel" in combo:
            fields = [
                "dns.query_name",
                "dns.record_type",
                "network.source_ip",
                "network.destination_ip",
                "dns.response_code",
            ]
        elif (
            "scan" in combo
            or "reconnaissance" in combo
            or "t1595" in combo
            or "t1018" in combo
            or "host_scan" in combo
            or "port_scan" in combo
        ):
            fields = [
                "security.event_type",
                "event.timestamp",
                "network.source_ip",
                "network.destination_port",
                "network.destination_ip",
                "network.protocol",
                "scan.rate_per_second",
                "scan.connection_count",
            ]
        else:
            fields = [
                "network.source_ip",
                "network.destination_ip",
                "user.name",
                "endpoint.hostname",
                "security.event_type",
            ]

        # Add observed fields if not present
        for of in observed_fields:
            if of not in fields:
                fields.append(of)

        return fields

    @classmethod
    def _infer_primary_behavior(
        cls,
        rule_identifier: str,
        rule_name: str,
        category: str,
        sub_category: str,
        attck_tactics: List[str],
        observed_fields: List[str],
    ) -> str:
        """
        Infers candidate detection archetype.
        Uses rule identifier, category, name, and ATT&CK as supporting evidence.
        """
        combo = f"{rule_identifier} {rule_name} {category} {sub_category}".lower()
        tactics = [t.lower() for t in attck_tactics]

        if ("beacon" in combo or "c2" in combo) and "exfiltration" not in combo and "xfer" not in combo:
            return ArchetypeId.NETWORK_CONNECTION.value

        if (
            "exfiltration" in combo
            or "xfer" in combo
            or ("outbound" in combo and "transfer" in combo)
            or ("large" in combo and "outbound" in combo)
            or "exfiltration" in tactics
            or any("sentbytes" in f.lower() for f in observed_fields)
        ):
            return ArchetypeId.NETWORK_EXFILTRATION.value

        if "dns" in combo and ("tunnel" in combo or "covert" in combo):
            return ArchetypeId.DNS_TUNNELING.value

        if (
            "scan" in combo
            or "reconnaissance" in combo
            or "t1595" in combo
            or "t1018" in combo
            or "host_scan" in combo
            or "port_scan" in combo
            or ("discovery" in combo and "scan" in combo)
        ) and "malware" not in combo and "process" not in combo and "powershell" not in combo:
            return ArchetypeId.NETWORK_SCAN.value

        if "brute" in combo or ("auth" in combo and "fail" in combo) or "credential access" in tactics:
            return ArchetypeId.BRUTE_FORCE.value

        if "privilege" in combo or "escalation" in combo or "privilege escalation" in tactics:
            return ArchetypeId.PRIVILEGE_ESCALATION.value

        if "lateral" in combo or "movement" in combo or "lateral movement" in tactics:
            return ArchetypeId.LATERAL_MOVEMENT.value

        if "web" in combo or "sql" in combo or "xss" in combo or "injection" in combo:
            return ArchetypeId.WEB_ATTACK.value

        if "cloud" in combo or "s3" in combo or "iam" in combo or "azure" in combo or "gcp" in combo:
            return ArchetypeId.CLOUD_DATA_ACCESS.value

        if "policy" in combo or "violation" in combo or "compliance" in combo:
            return ArchetypeId.POLICY_VIOLATION.value

        if "defense evasion" in tactics or "evasion" in combo or "tamper" in combo:
            return ArchetypeId.ENDPOINT_DEFENSE_EVASION.value

        if "malware" in combo or "trojan" in combo or "virus" in combo or "hash" in combo:
            return ArchetypeId.MALWARE_EXECUTION.value

        if "process" in combo or "powershell" in combo or "execution" in combo or "execution" in tactics:
            return ArchetypeId.MALWARE_EXECUTION.value

        if "credential" in combo or "mimikatz" in combo or "lsass" in combo:
            return ArchetypeId.CREDENTIAL_ACCESS.value

        return ArchetypeId.UNKNOWN.value

    @classmethod
    def _build_detection_objective(cls, archetype: str, rule_name: str, category: str) -> str:
        if archetype == ArchetypeId.NETWORK_EXFILTRATION.value:
            return (
                f"Detect unauthorized or anomalous outbound network data transfer from internal systems "
                f"to external destinations in violation of acceptable use or security baselines ({rule_name})."
            )
        elif archetype == ArchetypeId.MALWARE_EXECUTION.value:
            return (
                f"Detect execution of malicious binaries, untrusted scripts, or abused Living-off-the-Land "
                f"binaries on endpoint infrastructure ({rule_name})."
            )
        elif archetype == ArchetypeId.BRUTE_FORCE.value:
            return f"Detect repeated unauthorized authentication attempts or credential stuffing campaigns ({rule_name})."
        elif archetype == ArchetypeId.CREDENTIAL_ACCESS.value:
            return f"Detect unauthorized access to credential stores, memory scraping, or token theft ({rule_name})."
        elif archetype == ArchetypeId.DNS_TUNNELING.value:
            return f"Detect covert command-and-control or data exfiltration over anomalous DNS queries ({rule_name})."
        elif archetype == ArchetypeId.NETWORK_SCAN.value:
            return (
                f"Detect unauthorized or anomalous network scanning, host reconnaissance, or port sweeps "
                f"attempting to map internal or perimeter attack surface ({rule_name})."
            )
        else:
            return f"Investigate SIEM detection alert '{rule_name}' within category '{category}'."
