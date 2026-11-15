#!/usr/bin/env python3
"""
Seed script for Verdictum AI Compact UI Validation 1.1.
Populates backend/ai_verdict.db with:
- Authorized test accounts for Administrator, SOC Analyst, and Read-Only Viewer.
- 36 monitored detection rules with titles > 80 characters across diverse archetypes.
- Policies in Draft, Approved, Suspended, Revoked, and Blocked states.
- G1-G8 quality assessments with passing, warning, and failing states.
- 125+ incidents across 36 distinct canonical SIEM rules.
- Ingestion history jobs and telemetry records.
"""

import sqlite3
import json
import uuid
import random
from datetime import datetime, timezone, timedelta

DB_PATH = "backend/ai_verdict.db"

# Passwords:
# admin: AdminPassword123!
# analyst: AnalystPassword123!
# viewer: ViewerPassword123!
ADMIN_HASH = "$2b$12$AiofWMWLwdJiM3JuUJBz1u1/jD9qloa30nb5OXoEQEejZMxAPHxKW"
ANALYST_HASH = "$2b$12$bcGOmV3sjuXeov4Xpo/FE.7AHgB7NnqSijSGcnRViAfqaMyXzgAyS"
VIEWER_HASH = "$2b$12$78JP7oL4SfObLh9gAQvAY.YTxa7RUyh2x6aMWl3pVMOsjQJ6u6p2a"

def iso_now(offset_minutes=0):
    return (datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)).isoformat()

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("[1/6] Seeding authorized RBAC users...")
    users_data = [
        ("admin-user-001", "admin", "admin@verdictum.ai", ADMIN_HASH, "System Administrator", "Administrator", 1),
        ("analyst-user-002", "analyst", "analyst@verdictum.ai", ANALYST_HASH, "Senior SOC Analyst", "SOC Analyst", 1),
        ("viewer-user-003", "viewer", "viewer@verdictum.ai", VIEWER_HASH, "Audit & Compliance Viewer", "Read-Only Viewer", 1),
    ]
    for uid, uname, email, pw_hash, fname, role, active in users_data:
        cur.execute("SELECT id FROM users WHERE username = ?", (uname,))
        row = cur.fetchone()
        if row:
            cur.execute("""
                UPDATE users SET email=?, hashed_password=?, full_name=?, role=?, is_active=?, updated_at=?
                WHERE username=?
            """, (email, pw_hash, fname, role, active, iso_now(), uname))
        else:
            cur.execute("""
                INSERT INTO users (id, username, email, hashed_password, full_name, role, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (uid, uname, email, pw_hash, fname, role, active, iso_now(-1440), iso_now()))

    print("[2/6] Seeding 36 realistic detection rules (>80 chars titles, diverse archetypes)...")
    
    rule_definitions = [
        ("RULE-NET-001", "FortiGate Firewall: High Volume Distributed Inbound TCP Port Scan Detected Across Internal DMZ Web Subnets", "FGT_PORT_SCAN_DISTRIBUTED", "CRITICAL", "NETWORK_SCAN", "ACTIVE"),
        ("RULE-AUTH-002", "Microsoft Active Directory: Distributed Kerberos Pre-Authentication Brute Force Attack Targeting Privileged Domain Accounts", "WIN_KERBEROS_PREAUTH_BRUTE", "HIGH", "BRUTE_FORCE", "ACTIVE"),
        ("RULE-EDR-003", "CrowdStrike Falcon: Suspicious Base64 Encoded PowerShell Command Execution with Memory Code Injection and Cobalt Strike Beacon Artifacts", "CS_POWERSHELL_OBFUSCATED_BEACON", "CRITICAL", "MALWARE_DEFENSE", "ACTIVE"),
        ("RULE-WAF-004", "F5 BIG-IP Advanced WAF: Remote Code Execution Exploit Payload via Malicious JNDI Lookup Attempt Directed at Core Banking API", "F5_LOG4J_JNDI_EXPLOIT_ATTEMPT", "CRITICAL", "WEB_ATTACK", "ACTIVE"),
        ("RULE-EXFIL-005", "Palo Alto Networks NGFW: High-Entropy Outbound DNS Tunneling Session Detected Towards Dynamic Dynamic-DNS Provider Infrastructure", "PAN_DNS_TUNNELING_EXFIL", "HIGH", "DATA_EXFILTRATION", "ACTIVE"),
        ("RULE-CLOUD-006", "AWS GuardDuty: Unauthorized IAM Access Key Secret Modification Combined with Unusual Multi-Region CloudTrail Activity", "AWS_IAM_UNUSUAL_API_ACTIVITY", "HIGH", "CLOUD_INFRASTRUCTURE", "ACTIVE"),
        ("RULE-MAIL-007", "Proofpoint Targeted Attack Protection: High-Risk Phishing Email Containing Macro-Enabled Excel Attachment Targeting Financial Officers", "PFPT_PHISHING_MALICIOUS_MACRO", "MEDIUM", "EMAIL_SECURITY", "ACTIVE"),
        ("RULE-HOST-008", "SentinelOne Endpoint Protection: Ransomware Canary Decoy File Renamed and Volume Shadow Copy Deletion Command Detected", "S1_VSSADMIN_SHADOW_DELETE", "CRITICAL", "MALWARE_DEFENSE", "ACTIVE"),
        ("RULE-IDPS-009", "Cisco Firepower Threat Defense: Inbound Exploit Attempt Triggering Known OpenSSL Remote Buffer Overflow Vulnerability Signature", "CISCO_FTD_BUFFER_OVERFLOW", "CRITICAL", "EXPLOITATION", "ACTIVE"),
        ("RULE-VPN-010", "Pulse Secure Connect: Impossible Travel Geolocation Alert with Simultaneous Active VPN Sessions from Brazil and Singapore", "VPN_IMPOSSIBLE_TRAVEL_ANOMALY", "MEDIUM", "IDENTITY_ACCESS", "ACTIVE"),
        ("RULE-LAT-011", "Microsoft Defender for Endpoint: Suspicious PsExec Lateral Movement Invocation with Pass-the-Hash Credentials on Server Farm", "MDE_PSEXEC_LATERAL_PASS_HASH", "HIGH", "LATERAL_MOVEMENT", "ACTIVE"),
        ("RULE-PRIV-012", "Linux Auditd Syscall Monitor: Unauthorized SUID Binary Privilege Escalation via Sudo Caching Bypass on Production Database Server", "LINUX_SUDO_SUID_PRIV_ESCALATION", "HIGH", "PRIVILEGE_ESCALATION", "ACTIVE"),
        ("RULE-PERS-013", "Windows Event Log 7045: Rogue Windows Service Created with Unquoted Path and Interactive Command Execution Parameters", "WIN_ROGUE_SERVICE_PERSISTENCE", "MEDIUM", "PERSISTENCE", "ACTIVE"),
        ("RULE-CRED-014", "Mimikatz LSASS Memory Dumping Pattern Observed via Unsigned Diagnostic Driver Loading Incident on Workstation", "EDR_LSASS_MEMORY_DUMP_ATTEMPT", "CRITICAL", "CREDENTIAL_ACCESS", "ACTIVE"),
        ("RULE-DEF-015", "Windows Defender Security Center Tampering: Real-Time Protection Disabled via Unauthorized Group Policy Registry Modification", "WIN_DEFENDER_TAMPER_PROTECT_OFF", "HIGH", "DEFENSE_EVASION", "ACTIVE"),
        ("RULE-DISC-016", "Adversary Reconnaissance: Automated Active Directory BloodHound LDAP Query Storm from Non-Administrative Laptop", "AD_BLOODHOUND_LDAP_ENUMERATION", "MEDIUM", "DISCOVERY", "ACTIVE"),
        ("RULE-COLL-017", "Mass File Archiving Activity: Suspicious PowerShell 7z CLI Execution Archiving Financial Share Documents to AppData", "PS_7Z_MASS_DOCUMENT_STAGING", "MEDIUM", "COLLECTION", "ACTIVE"),
        ("RULE-C2-018", "Outbound Network Anomaly: Periodic Periodic HTTP POST Beacons to Dynamic Cloudflare Worker with Encrypted Payload", "C2_HTTP_PERIODIC_BEACON_WORKER", "HIGH", "COMMAND_AND_CONTROL", "ACTIVE"),
        ("RULE-IMPACT-019", "Storage Area Network Warning: Rapid Encryption Entropy Spike Detected on Corporate NAS Volume via SMB Protocol", "NAS_SMB_RAPID_ENCRYPTION_SPIKE", "CRITICAL", "IMPACT", "ACTIVE"),
        ("RULE-SUPPLY-020", "CI/CD Pipeline Security: Unauthorized Modification of GitHub Actions Runner Workflow Script with Secret Exfiltration Step", "CICD_GITHUB_RUNNER_TAMPERING", "HIGH", "SUPPLY_CHAIN", "ACTIVE"),
        ("RULE-K8S-021", "Kubernetes Audit Log: Privileged Pod Creation with HostPID and HostNetwork Access on Production EKS Node Group", "K8S_PRIVILEGED_POD_HOST_ESCAPE", "CRITICAL", "CONTAINER_SECURITY", "ACTIVE"),
        ("RULE-DNS-022", "Infoblox DNS Firewall: Internal Workstation Querying Domain Generated Algorithm (DGA) FQDNs at Anomalous High Rate", "INFOBLOX_DGA_QUERY_ANOMALY", "MEDIUM", "NETWORK_ANOMALY", "ACTIVE"),
        ("RULE-PROXY-023", "Zscaler Internet Access: Outbound Traffic Directly to Known Tor Exit Node Without Corporate Proxy Authorization", "ZSCALER_TOR_EXIT_NODE_DIRECT", "HIGH", "NETWORK_ANOMALY", "ACTIVE"),
        ("RULE-DLP-024", "Symantec Data Loss Prevention: Bulk Confidential Source Code Upload to Personal Cloud Storage Bucket Over HTTPS", "DLP_SOURCE_CODE_EXFIL_CLOUD", "HIGH", "DATA_EXFILTRATION", "ACTIVE"),
        ("RULE-SSO-025", "Okta Identity Engine: Multi-Factor Authentication Fatigue Spamming Followed by Successful Push Acceptance from New Device", "OKTA_MFA_FATIGUE_PUSH_ACCEPT", "HIGH", "IDENTITY_ACCESS", "ACTIVE"),
        ("RULE-DATABASE-026", "Oracle Database Audit: Massive SELECT Query Extracting Over 500,000 Customer Credit Card Records Outside Business Hours", "DB_ORACLE_MASS_RECORD_EXTRACT", "CRITICAL", "DATA_EXFILTRATION", "ACTIVE"),
        ("RULE-API-027", "Kong API Gateway: Excessive Inbound HTTP 401/403 Errors Indicating Automated Broken Object Level Authorization (BOLA) Fuzzing", "KONG_API_BOLA_FUZZING_ATTACK", "HIGH", "WEB_ATTACK", "ACTIVE"),
        ("RULE-AZURE-028", "Microsoft Entra ID: Global Administrator Role Granted to Unmanaged External Guest Account Without PIM Workflow Approval", "ENTRA_GLOBAL_ADMIN_ROGUE_GRANT", "CRITICAL", "CLOUD_INFRASTRUCTURE", "ACTIVE"),
        ("RULE-ENDPOINT-029", "macOS Jamf Pro Security: XProtect Alert for Backdoor.Mac.Eleanor Execution Inside Hidden User Directory", "MACOS_XPROTECT_BACKDOOR_ALERT", "HIGH", "MALWARE_DEFENSE", "ACTIVE"),
        ("RULE-ROUTER-030", "Cisco IOS Core Switch: Unauthorized Configuration Modification via Unencrypted Telnet Session from Remote Subnet", "CISCO_IOS_CONFIG_CHANGE_TELNET", "MEDIUM", "NETWORK_ANOMALY", "ACTIVE"),
        ("RULE-IOT-031", "Nozomi Networks OT Guardian: Modbus TCP Function Code Write Command Issued to SCADA Programmable Logic Controller", "SCADA_MODBUS_UNAUTHORIZED_WRITE", "CRITICAL", "OT_SECURITY", "ACTIVE"),
        ("RULE-ZEEK-032", "Zeek Network Security Monitor: Long-Duration TLS Session with Suspicious Certificate Subject Mismatching SNI Host", "ZEEK_TLS_SNI_CERT_MISMATCH", "MEDIUM", "NETWORK_ANOMALY", "ACTIVE"),
        ("RULE-FILE-033", "Carbon Black App Control: Execution of Unapproved Executable Blocked in User Temporary Directory on Financial Workstation", "CB_UNAPPROVED_EXE_USER_TEMP", "LOW", "MALWARE_DEFENSE", "ACTIVE"),
        ("RULE-VOIP-034", "Cisco Unified Communications Manager: SIP Toll Fraud Pattern with Over 200 International Calls Initiated in 15 Minutes", "CUCM_SIP_TOLL_FRAUD_SURGE", "MEDIUM", "NETWORK_ANOMALY", "ACTIVE"),
        ("RULE-CERT-035", "Active Directory Certificate Services (ADCS): Golden Certificate Extraction via ESC1 Vulnerable Certificate Template Misconfiguration", "ADCS_ESC1_GOLDEN_CERT_EXPLOIT", "CRITICAL", "CREDENTIAL_ACCESS", "ACTIVE"),
        ("RULE-SUSP-036", "Palo Alto Networks Threat Prevention: Suspicious High-Frequency ICMP Ping Tunneling Protocol Smuggling Channel [SUSPENDED]", "PAN_ICMP_TUNNELING_SMUGGLING", "MEDIUM", "NETWORK_ANOMALY", "SUSPENDED")
    ]

    rule_id_map = {}

    for r_ident, r_name, r_event, r_sev, r_arch, r_stat in rule_definitions:
        pattern_str = f"Pattern: {r_ident}_Detect\nIF Event Type == '{r_event}' WHERE COUNT(events) >= 1 GROUP BY Source_IP, Target_Host"
        raw_text_str = f"Name\n{r_name}\nEvent Type\n{r_event}\nSeverity\n{r_sev}\nArchetype\n{r_arch}\nPattern\n{pattern_str}"
        meta_json = json.dumps({"rule_identifier": r_ident, "archetype": r_arch, "severity": r_sev, "vendor": "FortiSIEM Rule Engine"})

        cur.execute("SELECT id FROM rules WHERE rule_id = ?", (r_ident,))
        row = cur.fetchone()
        if row:
            db_id = row[0]
            cur.execute("""
                UPDATE rules SET name=?, event_type=?, severity=?, status=?, description=?, detection_tech=?, evaluation_mode=?, pattern_logic=?, remediation=?, raw_rule_text=?, parsed_metadata=?, updated_at=?
                WHERE id=?
            """, (r_name, r_event, r_sev, r_stat, f"Enterprise SOC SIEM detection rule for {r_name}. Evaluates real-time events for adversary TTPs.", r_arch, "HYBRID", pattern_str, "Isolate target host, capture memory, review audit logs.", raw_text_str, meta_json, iso_now(), db_id))
        else:
            db_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO rules (id, rule_id, name, event_type, description, severity, status, data_source, detection_tech, evaluation_mode, pattern_logic, remediation, raw_rule_text, parsed_metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (db_id, r_ident, r_name, r_event, f"Enterprise SOC SIEM detection rule for {r_name}. Evaluates real-time events for adversary TTPs.", r_sev, r_stat, "FortiSIEM Supervisor", r_arch, "HYBRID", pattern_str, "Isolate target host, capture memory, review audit logs.", raw_text_str, meta_json, iso_now(-2880), iso_now()))
        rule_id_map[r_ident] = db_id

    print(f"[2/6] Total active rules in catalog: {len(rule_id_map)}")

    print("[3/6] Seeding rule prompts, versions, and governance policy states...")
    for idx, (r_ident, r_name, r_event, r_sev, r_arch, r_stat) in enumerate(rule_definitions):
        rule_db_id = rule_id_map[r_ident]
        prompt_db_id = f"prompt-{r_ident.lower()}"
        
        if r_ident == "RULE-NET-001":
            p_status = "APPROVED"
            is_suspended = 0
            susp_reason = None
            q_score = 92
            g1_status = "PASSED"
            approval_eligible = True
        elif r_ident == "RULE-AUTH-002":
            p_status = "APPROVED"
            is_suspended = 0
            susp_reason = None
            q_score = 85
            g1_status = "PASSED"
            approval_eligible = True
        elif r_ident == "RULE-EDR-003":
            p_status = "DRAFT"
            is_suspended = 0
            susp_reason = None
            q_score = 45
            g1_status = "FAILED"
            approval_eligible = False
        elif r_ident == "RULE-WAF-004":
            p_status = "APPROVED"
            is_suspended = 1
            susp_reason = "Model hallucination surge during WAF rule migration: AI verdict execution suspended pending human review calibration."
            q_score = 74
            g1_status = "WARNING"
            approval_eligible = False
        elif r_ident == "RULE-EXFIL-005":
            p_status = "REVOKED"
            is_suspended = 0
            susp_reason = None
            q_score = 68
            g1_status = "PASSED"
            approval_eligible = False
        elif r_ident == "RULE-SUSP-036":
            p_status = "DRAFT"
            is_suspended = 1
            susp_reason = "Rule disabled in FortiSIEM production supervisor; policy execution locked."
            q_score = 50
            g1_status = "WARNING"
            approval_eligible = False
        elif idx % 4 == 0:
            p_status = "DRAFT"
            is_suspended = 0
            susp_reason = None
            q_score = 58
            g1_status = "WARNING"
            approval_eligible = False
        elif idx % 5 == 0:
            p_status = "APPROVED"
            is_suspended = 0
            susp_reason = None
            q_score = 88
            g1_status = "PASSED"
            approval_eligible = True
        else:
            p_status = "APPROVED"
            is_suspended = 0
            susp_reason = None
            q_score = random.randint(78, 96)
            g1_status = "PASSED"
            approval_eligible = True

        version_id = f"pv-{r_ident.lower()}-v1"

        cur.execute("SELECT id FROM rule_prompts WHERE rule_id = ?", (rule_db_id,))
        rp = cur.fetchone()
        if rp:
            prompt_db_id = rp[0]
            cur.execute("""
                UPDATE rule_prompts SET title=?, active_version_id=?, ai_execution_suspended=?, suspension_reason=?, updated_at=?
                WHERE id=?
            """, (f"Governed AI Triage Policy — {r_name}", version_id, is_suspended, susp_reason, iso_now(), prompt_db_id))
        else:
            cur.execute("""
                INSERT INTO rule_prompts (id, rule_id, title, active_version_id, ai_execution_suspended, suspension_reason, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (prompt_db_id, rule_db_id, f"Governed AI Triage Policy — {r_name}", version_id, is_suspended, susp_reason, iso_now(-1440), iso_now()))

        cur.execute("SELECT id FROM prompt_versions WHERE id = ?", (version_id,))
        pv_row = cur.fetchone()
        
        change_summary = f"Synthesized production-ready policy template for {r_name} complying with 8 quality gates."
        revocation_reason = "Subsumed by enterprise DNS contract v2.0" if p_status == "REVOKED" else None
        
        if pv_row:
            cur.execute("""
                UPDATE prompt_versions SET status=?, quality_score=?, change_summary=?, revocation_reason=?, is_template_draft=?
                WHERE id=?
            """, (p_status, q_score, change_summary, revocation_reason, 0 if p_status == "APPROVED" else 1, version_id))
        else:
            cur.execute("""
                INSERT INTO prompt_versions (id, prompt_id, version_number, status, is_template_draft, common_prompt, rule_specific_prompt, detection_conditions, required_evidence, tp_indicators, fp_indicators, missing_info_criteria, escalation_conditions, analyst_questions, change_summary, quality_score, revocation_reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version_id, prompt_db_id, 1, p_status, 0 if p_status == "APPROVED" else 1,
                "Act as an elite Tier-3 SOC Incident Commander. Analyze input telemetry strictly without hallucinating absent forensic artifacts.",
                f"Evaluation criteria specifically tailored for {r_name}.",
                "Target host observed communicating with unauthorized external endpoint or anomalous process execution.",
                "Process commandline, parent process PID, source IPv4, destination IPv4, destination port, DNS query name, user account.",
                "Valid adversary execution sequence matching MITRE ATT&CK techniques.",
                "Authorized administrative maintenance window, scheduled backup job, automated vulnerability scanner.",
                "Absent process commandline arguments or missing firewall rule identifier.",
                "Active lateral movement towards domain controller or ransomware file modification surge.",
                json.dumps(["Has the endpoint been isolated from corporate subnet?", "Were user credentials compromised?"]),
                change_summary, q_score, revocation_reason, iso_now(-720)
            ))

        qa_id = f"qa-{r_ident.lower()}-v1"
        gate_results = {
            "G1_RULE_INTEGRITY": {
                "gate_id": "G1",
                "gate_name": "Rule Definition Integrity",
                "status": g1_status,
                "score": 20 if g1_status == "PASSED" else (15 if g1_status == "WARNING" else 0),
                "max_score": 20,
                "details": "Authoritative criteria verified against vendor documentation." if g1_status == "PASSED" else "Observed byte counts or packet totals not accepted as authoritative thresholds.",
                "blocking_findings": ["G1_MISSING_THRESHOLD: Authoritative event count threshold unverified; draft remains provisional."] if g1_status == "FAILED" else [],
                "warnings": ["Vendor rule file contains deprecated field references."] if g1_status == "WARNING" else []
            },
            "G2_ARCHETYPE_RELEVANCE": {
                "gate_id": "G2", "gate_name": "Detection Archetype Relevance", "status": "PASSED", "score": 20, "max_score": 20,
                "details": f"Correctly classified into {r_arch} archetype.", "blocking_findings": [], "warnings": []
            },
            "G3_EVIDENCE_FEASIBILITY": {
                "gate_id": "G3", "gate_name": "Evidence Contract Feasibility", "status": "PASSED" if q_score > 60 else "WARNING",
                "score": 20 if q_score > 60 else 12, "max_score": 20,
                "details": "Evidence contract defines all mandatory fields.", "blocking_findings": [],
                "warnings": ["Telemetry lacks secondary host metadata."] if q_score <= 60 else []
            },
            "G4_TP_CRITERIA_VALIDITY": {
                "gate_id": "G4", "gate_name": "TP Criteria Validity", "status": "PASSED", "score": 10, "max_score": 10,
                "details": "Objective True Positive criteria verified.", "blocking_findings": [], "warnings": []
            },
            "G5_FP_CRITERIA_VALIDITY": {
                "gate_id": "G5", "gate_name": "FP Criteria & Benign Assumptions", "status": "PASSED", "score": 10, "max_score": 10,
                "details": "Benign assumptions validated against authorized administrative workflows.", "blocking_findings": [], "warnings": []
            },
            "G6_ABSTENTION_ESCALATION": {
                "gate_id": "G6", "gate_name": "Abstention & Escalation Safety", "status": "PASSED", "score": 10, "max_score": 10,
                "details": "Explicit REQUIRES_ATTENTION abstention conditions enforced.", "blocking_findings": [], "warnings": []
            },
            "G7_POLICY_CONSISTENCY": {
                "gate_id": "G7", "gate_name": "Internal Policy & Contract Consistency", "status": "PASSED", "score": 5, "max_score": 5,
                "details": "No contradictions between policy sections.", "blocking_findings": [], "warnings": []
            },
            "G8_SIMULATION_REGRESSION": {
                "gate_id": "G8", "gate_name": "Simulation & Regression Validation",
                "status": "PASSED" if q_score >= 85 else "WARNING",
                "score": 5 if q_score >= 85 else 0, "max_score": 5,
                "details": "Simulation pass rate 100% on historical ground truth." if q_score >= 85 else "Simulation status: INSUFFICIENT_DATA (< 5 historical cases).",
                "blocking_findings": [],
                "warnings": ["Empirical corpus below threshold for autonomous operation."] if q_score < 85 else []
            }
        }

        blocking_issues = ["G1_MISSING_THRESHOLD: Authoritative event count threshold unverified."] if g1_status == "FAILED" else []
        warnings = ["Empirical corpus below threshold for autonomous operation."] if q_score < 85 else []

        cur.execute("SELECT id FROM policy_quality_assessments WHERE id = ?", (qa_id,))
        if cur.fetchone():
            cur.execute("""
                UPDATE policy_quality_assessments SET quality_score=?, approval_eligible=?, gate_results=?, blocking_issues=?, warnings=?, evaluated_at=?
                WHERE id=?
            """, (q_score, 1 if approval_eligible else 0, json.dumps(gate_results), json.dumps(blocking_issues), json.dumps(warnings), iso_now(), qa_id))
        else:
            cur.execute("""
                INSERT INTO policy_quality_assessments (id, rule_id, prompt_version_id, version_number, archetype, quality_score, approval_eligible, simulation_status, score_breakdown, gate_results, blocking_issues, warnings, missing_evidence_mappings, recommendations, policy_digest, contract_digest, rule_digest, validator_version, evaluated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                qa_id, rule_db_id, version_id, 1, r_arch, q_score, 1 if approval_eligible else 0,
                "COMPLETED" if q_score >= 85 else "INSUFFICIENT_DATA",
                json.dumps({"detection_semantics": 20, "evidence_contract": 20, "tp_fp_criteria": 20, "abstention_escalation": 10, "internal_consistency": 5, "historical_simulation": 5 if q_score >= 85 else 0}),
                json.dumps(gate_results), json.dumps(blocking_issues), json.dumps(warnings), json.dumps([]),
                json.dumps(["Maintain double-blind review records for model calibration."]),
                f"sha256:{uuid.uuid4().hex[:16]}", f"sha256:{uuid.uuid4().hex[:16]}", f"sha256:{uuid.uuid4().hex[:16]}", "v2.2.0", iso_now(-360)
            ))

    print("[4/6] Seeding 125 realistic incidents across all 36 canonical SIEM rules...")
    
    verdict_types = ["TRUE_POSITIVE", "FALSE_POSITIVE", "REQUIRES_ATTENTION"]
    status_names = ["New", "In Progress", "Under Investigation", "Escalated", "Closed"]

    for i in range(1, 126):
        inc_id = f"{170000 + i}"
        rule_idx = (i - 1) % len(rule_definitions)
        r_ident, r_name, r_event, r_sev, r_arch, r_stat = rule_definitions[rule_idx]
        rule_db_id = rule_id_map[r_ident]

        chosen_verdict = verdict_types[i % len(verdict_types)]
        confidence = round(random.uniform(78.5, 99.2), 1) if chosen_verdict != "REQUIRES_ATTENTION" else round(random.uniform(45.0, 68.0), 1)
        st_name = status_names[i % len(status_names)]
        
        src_ip = f"192.0.2.{10 + (i % 240)}"
        rep_ip = f"198.51.100.{5 + (i % 50)}"
        dev_name = f"SEC-GW-0{1 + (i % 8)}.example.net"

        inc_title = f"{r_name} [Incident #{inc_id} on {dev_name}]"
        
        ai_verdict_obj = {
            "incident_id": inc_id,
            "verdict": chosen_verdict,
            "confidence": confidence,
            "reason": f"Automated analytical evaluation for {r_ident}: Analyzed {12 + (i % 45)} telemetry events. { 'Pattern strictly matches true positive indicator of attack.' if chosen_verdict == 'TRUE_POSITIVE' else ('Activity corroborated as benign routine maintenance scan.' if chosen_verdict == 'FALSE_POSITIVE' else 'Critical evidence fields missing from packet capture; requires human review adjudication.') }",
            "supporting_evidence": [
                f"Telemetry event count: {18 + (i * 3)}",
                f"Source host: {src_ip}",
                f"Reporting gateway: {dev_name}",
                f"Canonical SIEM rule: {r_ident}"
            ],
            "missing_evidence": ["Raw PCAP dump"] if chosen_verdict == "REQUIRES_ATTENTION" else [],
            "analyst_questions": [
                f"Has host {src_ip} been isolated via EDR containment?",
                "Are unauthorized credentials observed in subsequent logs?"
            ],
            "latency_ms": random.randint(14, 48),
            "model_identifier": "qwen2.5-7b-instruct-awq-simulated",
            "prompt_tokens": random.randint(450, 1200),
            "completion_tokens": random.randint(80, 220),
            "total_tokens": random.randint(530, 1420),
            "is_simulated": True,
            "rule_name": r_name,
            "severity": r_sev,
            "evaluated_at": iso_now(- (i * 12)),
            "evaluated_by_user": "scheduler"
        }

        raw_payload = {
            "incident_id": inc_id,
            "rule_id": r_ident,
            "rule_name": r_name,
            "event_type": r_event,
            "src_ip": src_ip,
            "dst_ip": "198.51.100.80",
            "device_name": dev_name,
            "event_count": 24 + (i * 2),
            "severity": r_sev,
            "raw_log_sample": f"Nov 15 11:20:00 {dev_name} {r_event}: src={src_ip} dst=198.51.100.80 proto=TCP action=ALERT"
        }

        detail_json = json.dumps({"attackTactic": "Automated Alert", "attackTechnique": r_arch, "command": f"process_{r_ident.lower()}.exe"})

        cur.execute("SELECT id FROM incidents WHERE incident_id = ?", (inc_id,))
        inc_row = cur.fetchone()
        if inc_row:
            cur.execute("""
                UPDATE incidents SET rule_id=?, event_type=?, title=?, severity=?, event_severity=?, status_name=?, source_ip=?, reporting_device=?, reporting_ip=?, detail=?, ai_verdict=?, updated_at=?
                WHERE incident_id=?
            """, (rule_db_id, r_event, inc_title, r_sev, r_sev, st_name, src_ip, dev_name, rep_ip, detail_json, json.dumps(ai_verdict_obj), iso_now(), inc_id))
        else:
            cur.execute("""
                INSERT INTO incidents (id, incident_id, rule_id, event_type, title, description, detail, severity, event_severity, status_code, status_name, category, subcategory, source_ip, reporting_device, reporting_ip, customer, ticket_id, raw_payload, ai_verdict, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()), inc_id, rule_db_id, r_event, inc_title,
                f"Automated incident alert generated by FortiSIEM correlation engine for {r_ident}.",
                detail_json, r_sev, r_sev, 2, st_name, "Security", r_arch, src_ip, dev_name, rep_ip, "Enterprise Core SOC",
                f"TICK-{1000 + i}", json.dumps(raw_payload), json.dumps(ai_verdict_obj), iso_now(- (i * 15)), iso_now()
            ))

    print("[5/6] Seeding ingestion jobs history in import_jobs...")
    import_jobs_data = [
        ("job-arch-001", "Incident_json.zip", "ZIP", 94428, 125, 125, 0, 0, "COMPLETED", "{}"),
        ("job-siem-002", "fortisiem_live_pull_batch_1710", "API", 45200, 50, 42, 8, 0, "COMPLETED", "{}"),
        ("job-siem-003", "fortisiem_live_pull_batch_1711", "API", 23100, 23, 18, 3, 2, "COMPLETED", "{\"corrupted_events\": [\"XML_PARSE_ERR_LINE_42\", \"TIMESTAMP_FUTURE_ERR\"]} "),
        ("job-arch-004", "q4_edr_telemetry_sample.json", "JSON", 158200, 35, 35, 0, 0, "COMPLETED", "{}"),
    ]
    for jid, fname, ftype, fsize, tot, imp_cnt, dup_cnt, err_cnt, stat, err_det in import_jobs_data:
        cur.execute("SELECT id FROM import_jobs WHERE id = ?", (jid,))
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO import_jobs (id, filename, file_type, file_size, total_files, imported_count, duplicate_count, error_count, status, error_details, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (jid, fname, ftype, fsize, tot, imp_cnt, dup_cnt, err_cnt, stat, err_det, iso_now(-360), iso_now(-355)))

    print("[6/6] Committing all transactions...")
    conn.commit()
    conn.close()
    print("[SUCCESS] Database seeding complete: 3 RBAC users, 36 detection rules, 125 incidents, and 4 import jobs.")

if __name__ == "__main__":
    main()
