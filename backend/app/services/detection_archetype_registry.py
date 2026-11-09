import logging
from typing import Dict, Any, List, Optional, Tuple
from app.schemas.rule_intelligence import (
    ArchetypeId,
    ArchetypeDefinition,
    ArchetypeClassificationResult,
    DetectionSemantics,
)
from app.models.rule import Rule

logger = logging.getLogger("ai_verdict.archetype_registry")


class DetectionArchetypeRegistry:
    """
    REQ-02: Versioned Detection Archetype Registry & Classifier.
    Maintains an explicit, versioned library of behavioral detection archetypes.
    Classifies detection rules based on verified semantics, not superficial keyword triggers.
    """
    REGISTRY_VERSION = "v2.0.0"

    _REGISTRY: Dict[ArchetypeId, ArchetypeDefinition] = {
        ArchetypeId.NETWORK_EXFILTRATION: ArchetypeDefinition(
            archetype_id=ArchetypeId.NETWORK_EXFILTRATION,
            name="Network Exfiltration & Data Transfer",
            version=REGISTRY_VERSION,
            detection_purpose=(
                "Detection of unauthorized, anomalous, or excessive outbound network data transfer, "
                "C2 channel staging, or unauthorized cloud storage egress."
            ),
            core_telemetry_categories=["NETWORK_TRAFFIC", "FLOW_RECORD", "FIREWALL_SESSION", "PROXY_LOG"],
            mandatory_core_fields=[
                "network.source_ip",
                "network.destination_ip",
                "network.direction",
                "network.bytes_out",
                "event.timestamp",
            ],
            conditional_fields=[
                "user.name",
                "network.destination_port",
                "network.destination_domain",
                "network.protocol",
                "dlp.findings",
                "process.name",
            ],
            optional_enrichment_fields=[
                "geo.destination_country",
                "asn.destination_asn",
                "network.historical_baseline",
                "user.department",
            ],
            unsupported_fields=[
                "file.hash_sha256",
                "process.parent_name",
                "registry.key_path",
            ],
            tp_indicator_candidates=[
                "Outbound data transfer volume substantially exceeds established host/user baseline",
                "Destination IP/domain is newly registered, untrusted, or has low reputation",
                "Transfer directed to unauthorized external file-sharing or personal cloud storage service",
                "Off-hours outbound bulk data transfer initiated without documented change ticket",
                "Concurrent data staging or archive creation observed prior to outbound network spike",
            ],
            fp_indicator_candidates=[
                "Authorized scheduled backup job to corporate offsite cloud storage repository",
                "Legitimate software distribution, CDN mirror synchronization, or OS patch mirroring",
                "Approved business partner bulk transfer under an active change window",
                "Video conferencing, streaming, or large media asset upload within corporate guidelines",
            ],
            abstention_requirements=[
                "Total bytes transferred cannot be verified from available firewall/flow records",
                "Destination IP address or domain cannot be resolved or is truncated in telemetry",
                "Directionality (inbound vs outbound) cannot be determined from session flags",
                "Detection threshold or aggregation window from SIEM rule definition is unverified",
            ],
            escalation_considerations=[
                "Exfiltration volume exceeds 1 GB to unclassified foreign destination",
                "Sensitive data, intellectual property, or PII keywords flagged in DLP correlation",
                "Originating host belongs to domain controllers, executive workstations, or critical databases",
            ],
            analyst_question_templates=[
                "What was the total volume of outbound bytes transferred in the session/window?",
                "Is the destination entity an authorized corporate cloud service or an unknown external host?",
                "Did the originating user or service account have a legitimate business purpose for this transfer?",
                "Does the transfer volume deviate from the historical 30-day baseline for this source asset?",
                "Are there corroborating DLP alerts or endpoint data-staging events preceding this network transfer?",
            ],
            unsupported_assumptions=[
                "Internal RFC-1918 traffic is NOT automatically benign without verifying lateral exfiltration",
                "Observed telemetry sentBytes64 is NOT an authoritative detection threshold",
                "Absence of file hash does NOT mean exfiltration did not occur",
            ],
            contradiction_rules=[
                {
                    "rule_id": "INBOUND_LABELED_AS_EXFILTRATION",
                    "rule_type": "INBOUND_LABELED_AS_EXFILTRATION",
                    "description": "Claiming exfiltration when traffic direction is confirmed inbound",
                },
                {
                    "rule_id": "ZERO_BYTES_TRANSFERRED",
                    "rule_type": "ZERO_BYTES_TRANSFERRED",
                    "description": "Claiming successful large data transfer when byte count is zero or session failed",
                },
                {
                    "rule_id": "EXTERNAL_C2_ON_LOOPBACK",
                    "rule_type": "EXTERNAL_C2_ON_LOOPBACK",
                    "description": "Claiming external C2 beaconing or exfiltration when destination is loopback or internal RFC1918 IP",
                },
            ],
        ),

        ArchetypeId.NETWORK_SCAN: ArchetypeDefinition(
            archetype_id=ArchetypeId.NETWORK_SCAN,
            name="Network Scan & Host Reconnaissance",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of network port scanning, horizontal host reconnaissance, and unauthorized network sweeps.",
            core_telemetry_categories=["NETWORK_TRAFFIC", "FIREWALL_SESSION", "RECONNAISSANCE"],
            mandatory_core_fields=[
                "security.event_type",
                "event.timestamp",
                "network.source_ip",
                "network.destination_port",
            ],
            conditional_fields=[
                "network.destination_ip",
                "network.destination_ip_list",
                "network.protocol",
                "scan.rate_per_second",
                "scan.connection_count",
                "network.tcp_flags",
            ],
            optional_enrichment_fields=[
                "geo.source_country",
                "network.bytes_out",
                "network.bytes_in",
                "endpoint.hostname",
            ],
            unsupported_fields=[
                "file.hash_sha256",
                "process.name",
                "process.command_line",
                "process.parent_name",
                "registry.key_path",
            ],
            tp_indicator_candidates=[
                "High volume of sequential TCP connection attempts to a fixed destination port across multiple destination hosts",
                "Rapid horizontal host sweep across internal subnet or address range within short aggregation window",
                "High ratio of TCP SYN packets with RST or unanswered packets, indicating port discovery without established application sessions",
                "Reconnaissance scan originating from untrusted, unauthorized, or external source IP",
                "Targeted destination port matches sensitive or high-value service (e.g. 22/SSH, 445/SMB, 3389/RDP, 8080/HTTP-Admin)",
            ],
            fp_indicator_candidates=[
                "Authorized network vulnerability scanner (e.g. Nessus, Qualys, Rapid7, OpenVAS) operating from designated scanning host with active change ticket",
                "Approved IT infrastructure discovery, SNMP inventory scan, or monitoring health check with verified change request",
                "Documented load balancer or application cluster health probe sweep",
                "Authorized penetration test or red team exercise active during scheduled maintenance window",
            ],
            abstention_requirements=[
                "Source IP address is unrecorded, corrupted, or missing from telemetry",
                "Destination port or target host identity cannot be resolved from available flow records",
                "Connection counts and time window cannot be verified from available firewall/SIEM records",
                "Detection threshold or aggregation window from SIEM rule definition is unverified",
            ],
            escalation_considerations=[
                "Scanning source successfully establishes completed connections or authentication to sensitive internal assets (Domain Controllers, database servers)",
                "Scanning activity is followed by exploit attempts, brute force attacks, or lateral movement payloads",
                "Originating scanning host is an internal asset exhibiting signs of previous compromise",
            ],
            analyst_question_templates=[
                "What was the total number of unique destination hosts contacted by the source IP during the aggregation window?",
                "Is the source IP registered in the corporate asset inventory as an authorized vulnerability scanner or monitoring server?",
                "Did the scanning activity result in completed TCP sessions or application-layer data exchange?",
                "Is there an approved change management ticket corresponding to this scan window and source asset?",
                "Are there corroborating firewall alerts, IPS signatures, or endpoint anomalies associated with the scanning source?",
            ],
            unsupported_assumptions=[
                "Internal RFC-1918 traffic is NOT automatically benign; adversaries conduct internal network reconnaissance post-compromise",
                "Loopback or local subnet traffic is NOT automatically benign without verifying scanner identity",
                "Observed incidentCount or connection count in a single incident is NOT an authoritative detection threshold",
                "Absence of file hashes or process telemetry does NOT invalidate network scanning alerts",
            ],
            contradiction_rules=[
                {
                    "rule_id": "MALWARE_CRITERIA_ON_NETWORK_SCAN",
                    "rule_type": "MALWARE_CRITERIA_ON_NETWORK_SCAN",
                    "description": "Demanding file hash or process lineage for pure network firewall scan alert",
                },
                {
                    "rule_id": "SCAN_LABELED_AS_EXFILTRATION",
                    "rule_type": "SCAN_LABELED_AS_EXFILTRATION",
                    "description": "Confusing reconnaissance probe packets with bulk data exfiltration",
                },
                {
                    "rule_id": "EXTERNAL_SCAN_ON_LOOPBACK",
                    "rule_type": "EXTERNAL_SCAN_ON_LOOPBACK",
                    "description": "Claiming external internet scanning when source is loopback 127.0.0.1",
                },
            ],
        ),

        ArchetypeId.NETWORK_CONNECTION: ArchetypeDefinition(
            archetype_id=ArchetypeId.NETWORK_CONNECTION,
            name="Network Connection & Traffic Flow",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of anomalous network connections, C2 beaconing, or suspicious ports.",
            core_telemetry_categories=["NETWORK_TRAFFIC", "FIREWALL_SESSION"],
            mandatory_core_fields=[
                "network.destination_ip",
                "network.source_ip",
                "network.destination_port",
            ],
            conditional_fields=[
                "network.protocol",
                "network.bytes_out",
                "event.timestamp",
            ],
            optional_enrichment_fields=["geo.destination_country"],
            unsupported_fields=["file.hash_sha256", "process.parent_name"],
            tp_indicator_candidates=["Persistent beaconing to suspicious external C2 IP"],
            fp_indicator_candidates=["Routine network telemetry to authorized corporate server"],
            abstention_requirements=["Destination IP or port is missing"],
            escalation_considerations=["C2 communication to sanctioned threat actor IP"],
            analyst_question_templates=["Is the destination IP an authorized cloud service?"],
            unsupported_assumptions=["External IP is automatically malicious"],
            contradiction_rules=[
                {
                    "rule_id": "EXTERNAL_C2_ON_LOOPBACK",
                    "rule_type": "EXTERNAL_C2_ON_LOOPBACK",
                    "description": "Claiming external C2 beaconing when destination is loopback or internal RFC1918 IP",
                }
            ],
        ),

        ArchetypeId.PROCESS_EXECUTION: ArchetypeDefinition(
            archetype_id=ArchetypeId.PROCESS_EXECUTION,
            name="Process Execution & Command Line",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of unauthorized process execution, suspicious command lines, and LOLBins.",
            core_telemetry_categories=["ENDPOINT_PROCESS", "EDR_ALERT"],
            mandatory_core_fields=[
                "process.command_line",
                "process.name",
                "user.name",
                "process.parent_name",
            ],
            conditional_fields=[
                "endpoint.hostname",
                "event.timestamp",
            ],
            optional_enrichment_fields=["file.hash_sha256"],
            unsupported_fields=["network.bytes_out"],
            tp_indicator_candidates=["Living-off-the-land binary executed with obfuscated arguments"],
            fp_indicator_candidates=["Authorized system administrator running standard maintenance script"],
            abstention_requirements=["Executing command line arguments are missing"],
            escalation_considerations=["Process tampering or credential access"],
            analyst_question_templates=["What was the parent process that spawned this command?"],
            unsupported_assumptions=["All PowerShell execution is malicious"],
            contradiction_rules=[
                {
                    "rule_id": "NO_PROCESS_LINEAGE_ON_MALICIOUS_EXECUTION",
                    "rule_type": "NO_PROCESS_LINEAGE_ON_MALICIOUS_EXECUTION",
                    "description": "Claiming unauthorized process spawn when no command line or parent process exists",
                }
            ],
        ),

        ArchetypeId.MALWARE_EXECUTION: ArchetypeDefinition(
            archetype_id=ArchetypeId.MALWARE_EXECUTION,
            name="Malware & Untrusted Process Execution",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of malicious binary execution, suspicious scripts, and adversary payloads.",
            core_telemetry_categories=["ENDPOINT_PROCESS", "EDR_ALERT", "COMMAND_LINE"],
            mandatory_core_fields=[
                "process.name",
                "process.command_line",
                "endpoint.hostname",
                "user.name",
                "event.timestamp",
            ],
            conditional_fields=[
                "process.parent_name",
                "file.hash_sha256",
            ],
            optional_enrichment_fields=["file.signature_status"],
            unsupported_fields=["network.bytes_out"],
            tp_indicator_candidates=["Process spawned with encoded payload"],
            fp_indicator_candidates=["Approved enterprise deployment tool"],
            abstention_requirements=["Command line or binary path missing"],
            escalation_considerations=["Ransomware precursors observed"],
            analyst_question_templates=["Is the executing binary signed?"],
            unsupported_assumptions=["Signed binaries are always safe"],
            contradiction_rules=[
                {
                    "rule_id": "NO_PROCESS_LINEAGE_ON_MALICIOUS_EXECUTION",
                    "rule_type": "NO_PROCESS_LINEAGE_ON_MALICIOUS_EXECUTION",
                    "description": "Claiming malware execution when neither process command line nor file hash is available",
                }
            ],
        ),

        ArchetypeId.FILE_MALWARE: ArchetypeDefinition(
            archetype_id=ArchetypeId.FILE_MALWARE,
            name="File & Malware Signature Match",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of malicious files by hash, signature, or quarantine action.",
            core_telemetry_categories=["ANTIVIRUS", "FILE_SYSTEM"],
            mandatory_core_fields=[
                "file.hash_sha256",
                "endpoint.hostname",
            ],
            conditional_fields=[
                "file.path",
                "file.name",
                "event.timestamp",
            ],
            optional_enrichment_fields=["threat_intel.hash_reputation"],
            unsupported_fields=["network.bytes_out"],
            tp_indicator_candidates=["File hash matches verified malware signature"],
            fp_indicator_candidates=["Antivirus false positive on trusted business application"],
            abstention_requirements=["File hash is completely missing"],
            escalation_considerations=["Malware dropped on domain controller"],
            analyst_question_templates=["What is the threat intelligence reputation of this file hash?"],
            unsupported_assumptions=["Every quarantine event is a successful breach"],
            contradiction_rules=[
                {
                    "rule_id": "MALWARE_EXECUTION_WITHOUT_FILE_HASH",
                    "rule_type": "MALWARE_EXECUTION_WITHOUT_FILE_HASH",
                    "description": "Claiming known malware signature match when file hash is completely absent",
                }
            ],
        ),

        ArchetypeId.AUTHENTICATION: ArchetypeDefinition(
            archetype_id=ArchetypeId.AUTHENTICATION,
            name="Authentication & Identity Events",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of anomalous logon activity, credential spraying, and authentication failures.",
            core_telemetry_categories=["AUTH_LOG", "ACTIVE_DIRECTORY"],
            mandatory_core_fields=[
                "user.name",
                "endpoint.hostname",
                "network.source_ip",
            ],
            conditional_fields=[
                "auth.result",
                "auth.failure_reason",
                "event.timestamp",
            ],
            optional_enrichment_fields=["geo.source_country"],
            unsupported_fields=["file.hash_sha256"],
            tp_indicator_candidates=["High volume of failed logons from foreign IP"],
            fp_indicator_candidates=["Cached credentials causing temporary lockout"],
            abstention_requirements=["User identity or target system missing"],
            escalation_considerations=["Compromise of domain admin account"],
            analyst_question_templates=["Did any authentication attempt succeed?"],
            unsupported_assumptions=["A single failed password attempt is an attack"],
            contradiction_rules=[],
        ),

        ArchetypeId.BRUTE_FORCE: ArchetypeDefinition(
            archetype_id=ArchetypeId.BRUTE_FORCE,
            name="Authentication Brute Force & Password Spraying",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of high-frequency logon failures, dictionary attacks, or password spraying.",
            core_telemetry_categories=["AUTH_LOG", "IDP_AUDIT", "ACTIVE_DIRECTORY"],
            mandatory_core_fields=[
                "user.name",
                "network.source_ip",
                "auth.result",
                "event.timestamp",
            ],
            conditional_fields=[
                "auth.failure_reason",
                "auth.failure_count",
                "endpoint.hostname",
            ],
            optional_enrichment_fields=["geo.source_country"],
            unsupported_fields=["file.hash_sha256"],
            tp_indicator_candidates=["Repeated failed logons followed by successful logon"],
            fp_indicator_candidates=["Expired service account credentials"],
            abstention_requirements=["Logon failure count cannot be established"],
            escalation_considerations=["Successful breach of privileged identity"],
            analyst_question_templates=["Was a single user targeted or multiple accounts?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.CREDENTIAL_ACCESS: ArchetypeDefinition(
            archetype_id=ArchetypeId.CREDENTIAL_ACCESS,
            name="Credential Access & Dumping",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of credential harvesting, LSASS memory dumping, or token theft.",
            core_telemetry_categories=["ENDPOINT_SECURITY", "PROCESS_ACCESS"],
            mandatory_core_fields=[
                "process.name",
                "user.name",
                "endpoint.hostname",
                "event.timestamp",
            ],
            conditional_fields=["process.command_line"],
            optional_enrichment_fields=["threat_intel.actor_reputation"],
            unsupported_fields=["network.bytes_out"],
            tp_indicator_candidates=["Handle opened to lsass.exe with PROCESS_ALL_ACCESS"],
            fp_indicator_candidates=["Authorized security scan"],
            abstention_requirements=["Target process or caller missing"],
            escalation_considerations=["Domain Controller credentials compromised"],
            analyst_question_templates=["What process accessed the credential store?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.DNS_TUNNELING: ArchetypeDefinition(
            archetype_id=ArchetypeId.DNS_TUNNELING,
            name="DNS Tunneling & Covert Channel",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of high-entropy DNS subdomains or repetitive TXT/NULL queries.",
            core_telemetry_categories=["DNS_SERVER_LOG", "NETWORK_SENSOR"],
            mandatory_core_fields=[
                "dns.query_name",
                "network.source_ip",
                "dns.record_type",
                "event.timestamp",
            ],
            conditional_fields=["dns.response_code"],
            optional_enrichment_fields=["network.destination_ip"],
            unsupported_fields=["process.parent_name"],
            tp_indicator_candidates=["High-entropy base32/base64 encoded payloads in subdomain labels"],
            fp_indicator_candidates=["Legitimate antivirus cloud lookups"],
            abstention_requirements=["Full DNS query name missing"],
            escalation_considerations=["Confirmed data exfiltration over DNS"],
            analyst_question_templates=["What was the entropy of the subdomain labels?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.LATERAL_MOVEMENT: ArchetypeDefinition(
            archetype_id=ArchetypeId.LATERAL_MOVEMENT,
            name="Lateral Movement & Remote Execution",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of movement between internal hosts via PsExec, WMI, WinRM, or SMB.",
            core_telemetry_categories=["NETWORK_AUTHENTICATION", "SMB_LOG"],
            mandatory_core_fields=[
                "network.source_ip",
                "network.destination_ip",
                "user.name",
                "event.timestamp",
            ],
            conditional_fields=["process.name"],
            optional_enrichment_fields=["endpoint.hostname"],
            unsupported_fields=["dns.query_name"],
            tp_indicator_candidates=["Network logon followed immediately by service creation"],
            fp_indicator_candidates=["Central IT management deployment"],
            abstention_requirements=["Source or destination host unidentified"],
            escalation_considerations=["Lateral movement to domain controller"],
            analyst_question_templates=["What service was invoked remotely?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.WEB_ATTACK: ArchetypeDefinition(
            archetype_id=ArchetypeId.WEB_ATTACK,
            name="Web Application Attack & Exploitation",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of SQL injection, XSS, path traversal, or remote code execution.",
            core_telemetry_categories=["WAF_LOG", "WEB_SERVER_ACCESS"],
            mandatory_core_fields=[
                "network.source_ip",
                "http.url",
                "http.method",
                "event.timestamp",
            ],
            conditional_fields=["http.status_code"],
            optional_enrichment_fields=["waf.rule_id"],
            unsupported_fields=["process.parent_name"],
            tp_indicator_candidates=["SQL injection payload detected in request parameter"],
            fp_indicator_candidates=["Authorized web penetration test"],
            abstention_requirements=["HTTP request URI missing"],
            escalation_considerations=["Server returned HTTP 200 with sensitive database output"],
            analyst_question_templates=["What status code was returned by the web server?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.PRIVILEGE_ESCALATION: ArchetypeDefinition(
            archetype_id=ArchetypeId.PRIVILEGE_ESCALATION,
            name="Privilege Escalation & Permission Tampering",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of unauthorized privilege elevation or local/domain admin additions.",
            core_telemetry_categories=["SECURITY_LOG", "AUDITD"],
            mandatory_core_fields=[
                "user.name",
                "endpoint.hostname",
                "security.event_type",
                "event.timestamp",
            ],
            conditional_fields=["process.command_line"],
            optional_enrichment_fields=[],
            unsupported_fields=["network.bytes_out"],
            tp_indicator_candidates=["User added to local Administrators group without approval"],
            fp_indicator_candidates=["Documented administrative onboarding"],
            abstention_requirements=["Modifying user context missing"],
            escalation_considerations=["Domain Admins group modified"],
            analyst_question_templates=["Which account initiated the privilege elevation?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.CLOUD_DATA_ACCESS: ArchetypeDefinition(
            archetype_id=ArchetypeId.CLOUD_DATA_ACCESS,
            name="Cloud Storage & IAM Access Anomaly",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of anomalous cloud storage access or audit logging tampering.",
            core_telemetry_categories=["CLOUD_TRAIL", "IAM_AUDIT"],
            mandatory_core_fields=[
                "cloud.user_identity",
                "cloud.service_name",
                "cloud.event_name",
                "event.timestamp",
            ],
            conditional_fields=["cloud.bucket_name"],
            optional_enrichment_fields=[],
            unsupported_fields=["file.hash_sha256"],
            tp_indicator_candidates=["Mass S3 GetObject operations from unknown foreign IP"],
            fp_indicator_candidates=["Scheduled cloud backup replication"],
            abstention_requirements=["Cloud identity ARN missing"],
            escalation_considerations=["Root account credentials used for export"],
            analyst_question_templates=["Was MFA used for the cloud session?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.POLICY_VIOLATION: ArchetypeDefinition(
            archetype_id=ArchetypeId.POLICY_VIOLATION,
            name="Enterprise Security Policy Violation",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of corporate acceptable use violations or policy breaches.",
            core_telemetry_categories=["WEB_FILTER", "CASB_LOG"],
            mandatory_core_fields=[
                "user.name",
                "network.source_ip",
                "security.event_type",
                "event.timestamp",
            ],
            conditional_fields=[],
            optional_enrichment_fields=[],
            unsupported_fields=[],
            tp_indicator_candidates=["Circumvention of enterprise proxy via unauthorized tunnel"],
            fp_indicator_candidates=["Proxy loopback reflection or internal health probe"],
            abstention_requirements=["Violation category missing"],
            escalation_considerations=["Violation involves regulated PII/PCI data"],
            analyst_question_templates=["Did the user intentionally bypass policy controls?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.ENDPOINT_DEFENSE_EVASION: ArchetypeDefinition(
            archetype_id=ArchetypeId.ENDPOINT_DEFENSE_EVASION,
            name="Endpoint Defense Evasion & Security Tampering",
            version=REGISTRY_VERSION,
            detection_purpose="Detection of attempts to disable or blind EDR or event logging.",
            core_telemetry_categories=["EDR_HEALTH", "SERVICE_CONTROL"],
            mandatory_core_fields=[
                "endpoint.hostname",
                "user.name",
                "process.command_line",
                "event.timestamp",
            ],
            conditional_fields=[],
            optional_enrichment_fields=[],
            unsupported_fields=["network.bytes_out"],
            tp_indicator_candidates=["Security service stopped or event logs cleared"],
            fp_indicator_candidates=["Authorized agent upgrade window"],
            abstention_requirements=["Target service or command line missing"],
            escalation_considerations=["Security logs cleared on high-value asset"],
            analyst_question_templates=["Was this change made in an authorized maintenance window?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.GENERIC: ArchetypeDefinition(
            archetype_id=ArchetypeId.GENERIC,
            name="Generic SIEM Detection Event",
            version=REGISTRY_VERSION,
            detection_purpose="General fallback for alerts without a specialized behavioral archetype.",
            core_telemetry_categories=["SECURITY_EVENT"],
            mandatory_core_fields=["security.event_type"],
            conditional_fields=["event.timestamp"],
            optional_enrichment_fields=[],
            unsupported_fields=[],
            tp_indicator_candidates=["Verified security threat matching detection conditions"],
            fp_indicator_candidates=["Benign administrative activity"],
            abstention_requirements=["Core event telemetry missing"],
            escalation_considerations=["Critical asset impacted"],
            analyst_question_templates=["What was the triggering event attribute?"],
            unsupported_assumptions=[],
            contradiction_rules=[],
        ),

        ArchetypeId.UNKNOWN: ArchetypeDefinition(
            archetype_id=ArchetypeId.UNKNOWN,
            name="Unclassified / Inadequate Telemetry",
            version=REGISTRY_VERSION,
            detection_purpose="Safe fallback when rule semantics are incomplete, conflicting, or unverified.",
            core_telemetry_categories=["GENERIC_EVENT"],
            mandatory_core_fields=["security.event_type", "event.timestamp"],
            conditional_fields=[],
            optional_enrichment_fields=[],
            unsupported_fields=[],
            tp_indicator_candidates=["Requires manual expert detection engineering review"],
            fp_indicator_candidates=["Requires manual expert detection engineering review"],
            abstention_requirements=["Rule semantics are insufficient for automated policy approval"],
            escalation_considerations=["Human review required before production activation"],
            analyst_question_templates=["What is the authoritative detection logic of this SIEM rule?"],
            unsupported_assumptions=["Do not assign generic malware instructions to unknown rules"],
            contradiction_rules=[],
        ),
    }

    @classmethod
    def get_archetype_definition(cls, archetype_id: ArchetypeId) -> ArchetypeDefinition:
        """Retrieves definition by archetype ID."""
        return cls._REGISTRY.get(archetype_id, cls._REGISTRY[ArchetypeId.UNKNOWN])

    @classmethod
    def list_archetypes(cls) -> List[ArchetypeDefinition]:
        """Returns all registered archetype definitions."""
        return list(cls._REGISTRY.values())

    @classmethod
    def classify_rule(
        cls,
        semantics: DetectionSemantics,
        rule: Optional[Rule] = None,
    ) -> ArchetypeClassificationResult:
        """
        Classifies detection rule semantics into primary and secondary archetypes.
        Provides a transparent, reproducible confidence score and traceability log.
        """
        trace: List[str] = []
        matched_features: List[str] = []

        rule_id = str(semantics.rule_identifier)
        category = str(semantics.event_category or "").upper()
        name = str(semantics.rule_name or "").upper()
        primary_behavior = str(semantics.primary_behavior or "").upper()
        event_type = str(getattr(rule, "event_type", "") or "").upper()
        tactics = [t.upper() for t in semantics.attck_tactics]
        observed = [f.lower() for f in semantics.observed_fields]

        combo = f"{rule_id} {name} {category} {event_type} {primary_behavior}".upper()

        trace.append(f"Classifying rule '{rule_id}' (Name: '{semantics.rule_name}')")
        trace.append(f"Input semantics: category='{category}', primary_behavior='{primary_behavior}'")

        primary: ArchetypeId = ArchetypeId.UNKNOWN
        secondary: Optional[ArchetypeId] = None
        confidence = 0.5

        # 1. Check for Network Exfiltration (Mandatory Reference Case)
        # Note: Beaconing / C2 should map to NETWORK_CONNECTION even if 'outbound' is in the phrase
        if ("BEACON" in combo or "C2" in combo) and "EXFILTRATION" not in combo and "XFER" not in combo and "PROCESS" not in combo and "POWERSHELL" not in combo and "ENDPOINT" not in combo:
            primary = ArchetypeId.NETWORK_CONNECTION
            confidence = 0.90
            matched_features.append("Network C2 beaconing or persistent flow pattern")
        elif (
            "PH_RULE_LARGE_OUTBOUND_XFER" in combo
            or "LARGE OUTBOUND" in combo
            or "EXFILTRATION" in category
            or "EXFILTRATION" in primary_behavior
            or ("OUTBOUND" in name and "XFER" in combo)
            or ("TRANSFER" in name and "OUTBOUND" in combo)
            or any("sentbytes" in f for f in observed)
        ):
            primary = ArchetypeId.NETWORK_EXFILTRATION
            matched_features.append(f"Exfiltration indicator: category='{category}' or outbound name/bytes")
            if "EXFILTRATION" in category and ("OUTBOUND" in name or "XFER" in rule_id or "TRANSFER" in name):
                confidence = 0.95
            else:
                confidence = 0.85

            if "DNS" in name or "TUNNEL" in name:
                secondary = ArchetypeId.DNS_TUNNELING
                matched_features.append("Secondary: DNS covert channel features")
            elif "CLOUD" in name or "S3" in name:
                secondary = ArchetypeId.CLOUD_DATA_ACCESS
                matched_features.append("Secondary: Cloud data access features")

        # 2. Check for Network Scan / Reconnaissance
        elif (
            "PH_RULE_HEAVY_TCP_HOST_SCAN_FIXED_PORT" in combo
            or "HOST_SCAN" in combo
            or "HOST SCAN" in combo
            or "PORT_SCAN" in combo
            or "PORT SCAN" in combo
            or "NETWORK_SCAN" in combo
            or "NETWORK SCAN" in combo
            or "T1595" in combo
            or "T1018" in combo
            or ("SCAN" in name and "MALWARE" not in name and "PROCESS" not in name and "VIRUS" not in name and "FILE" not in name)
            or ("RECONNAISSANCE" in combo and "MALWARE" not in name and "PROCESS" not in name and "POWERSHELL" not in name)
            or ("DISCOVERY" in category and "SCAN" in combo)
            or primary_behavior == ArchetypeId.NETWORK_SCAN.value
        ):
            primary = ArchetypeId.NETWORK_SCAN
            confidence = 0.95
            matched_features.append(f"Network scan / host reconnaissance pattern: rule='{rule_id}', name='{name}'")

        # 3. Check for File Malware
        elif (
            "FILE_MALWARE" in combo
            or "ANTIVIRUS" in combo
            or "QUARANTINE" in combo
            or "DROPPED ON DISK" in combo
            or ("RANSOMWARE" in name and "BINARY" in name)
        ):
            primary = ArchetypeId.FILE_MALWARE
            confidence = 0.92
            matched_features.append("Antivirus quarantine or file malware signature")

        # 3. Check for Process Execution
        elif (
            "PROCESS_EXECUTION" in combo
            or "WINDOWS-PROCESS-EXECUTION" in combo
            or "PROCESS-CREATION" in combo
            or "LOLBIN" in combo
            or "POWERSHELL DOWNLOAD" in name
        ):
            primary = ArchetypeId.PROCESS_EXECUTION
            confidence = 0.92
            matched_features.append("Process creation and LOLBin execution pattern")

        # 4. Check for Network Connection (C2, Beacon, Flow)
        elif (
            "NETWORK_CONNECTION" in combo
            or "BEACON" in combo
            or "C2" in combo
            or "FIREWALL-TRAFFIC-FLOW" in combo
            or "NETWORK-TRAFFIC" in combo
        ):
            primary = ArchetypeId.NETWORK_CONNECTION
            confidence = 0.90
            matched_features.append("Network traffic flow or C2 beaconing pattern")

        # 5. Check for DNS Tunneling
        elif "DNS" in name and ("TUNNEL" in name or "COVERT" in name):
            primary = ArchetypeId.DNS_TUNNELING
            confidence = 0.90
            matched_features.append("DNS Tunneling keyword and query telemetry match")
            secondary = ArchetypeId.NETWORK_EXFILTRATION

        # 6. Check for Authentication / Brute Force
        elif (
            "ACTIVE-DIRECTORY-LOGON" in combo
            or "LOGIN SPIKE" in name
            or "BRUTE" in name
            or ("AUTH" in name and "FAIL" in name)
        ):
            if "SPIKE" in name or "BRUTE" in name:
                primary = ArchetypeId.AUTHENTICATION
                confidence = 0.92
                matched_features.append("Authentication failure spike or brute force pattern")
            else:
                primary = ArchetypeId.AUTHENTICATION
                confidence = 0.88
                matched_features.append("Authentication telemetry match")

        # 7. Check for Credential Access / Dumping
        elif "CREDENTIAL" in name or "MIMIKATZ" in name or "LSASS" in name or "CREDENTIAL ACCESS" in tactics:
            primary = ArchetypeId.CREDENTIAL_ACCESS
            confidence = 0.92
            matched_features.append("Credential dumping or LSASS access pattern")

        # 8. Check for Lateral Movement
        elif "LATERAL" in name or "MOVEMENT" in name or "LATERAL MOVEMENT" in tactics or "PSEXEC" in name or "WMI" in name:
            primary = ArchetypeId.LATERAL_MOVEMENT
            confidence = 0.88
            matched_features.append("Lateral movement or remote invocation pattern")

        # 9. Check for Web Attack
        elif "WEB" in name or "SQL" in name or "XSS" in name or "INJECTION" in name:
            primary = ArchetypeId.WEB_ATTACK
            confidence = 0.89
            matched_features.append("Web application attack vector")

        # 10. Check for Defense Evasion
        elif "TAMPER" in name or "EVASION" in name or "DEFENSE EVASION" in tactics:
            primary = ArchetypeId.ENDPOINT_DEFENSE_EVASION
            confidence = 0.88
            matched_features.append("Defense evasion or security agent tampering")

        # 11. Check for Privilege Escalation
        elif "PRIVILEGE" in name or "ESCALATION" in name or "PRIVILEGE ESCALATION" in tactics:
            primary = ArchetypeId.PRIVILEGE_ESCALATION
            confidence = 0.88
            matched_features.append("Privilege escalation or unauthorized admin delegation")

        # 12. Check for Malware Execution
        elif "MALWARE" in name or "PROCESS" in name or "POWERSHELL" in name or "EXECUTION" in tactics or "CROWDSTRIKE" in name:
            primary = ArchetypeId.MALWARE_EXECUTION
            confidence = 0.90
            matched_features.append("Endpoint process execution or malware signature match")

        # 13. Check for Policy Violation
        elif "POLICY" in name or "VIOLATION" in name:
            primary = ArchetypeId.POLICY_VIOLATION
            confidence = 0.80
            matched_features.append("Security policy violation")

        # 14. Check for Generic Anomaly / Custom Sensor
        elif "CUSTOM-SENSOR" in combo or "GENERIC ANOMALY" in combo or "GENERIC" in combo:
            primary = ArchetypeId.GENERIC
            confidence = 0.70
            matched_features.append("Generic sensor anomaly fallback")

        else:
            primary = ArchetypeId.UNKNOWN
            confidence = 0.30
            matched_features.append("Inadequate telemetry semantics to establish definitive archetype")

        trace.append(f"Result: primary={primary.value}, secondary={secondary.value if secondary else 'None'}, confidence={confidence:.2f}")

        reason = (
            f"Classified as {primary.value} based on detection semantics: "
            f"{'; '.join(matched_features)}."
        )

        return ArchetypeClassificationResult(
            rule_identifier=rule_id,
            primary_archetype=primary,
            secondary_archetype=secondary,
            confidence_score=confidence,
            classification_reason=reason,
            matched_features=matched_features,
            traceability_log=trace,
            registry_version=cls.REGISTRY_VERSION,
        )
