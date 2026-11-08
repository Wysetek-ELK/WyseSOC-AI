import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule import Rule
from app.models.user import User
from app.schemas.prompt import (
    RulePromptResponse,
    PromptVersionResponse,
    PromptVersionCreate,
)

COMMON_SOC_BASELINE = """# ENTERPRISE SOC LEVEL-2 INVESTIGATION & TRIAGE PROTOCOL
You are an expert Level-2 Security Operations Center (SOC) Senior Incident Investigator.
Your mission is to perform strict, evidence-grounded triage on incoming SIEM incident telemetry and determine the ground-truth status.

## VERDICT CLASSIFICATION FRAMEWORK:

### 1. FALSE_POSITIVE (Benign Operational Noise / Expected Business Activity):
Vote FALSE_POSITIVE (confidence 80-98%) when observed indicators match known benign patterns:
- Web Policy Violations with Same Source & Destination (SAME_SRC_SAME_DEST / PH_RULE_WEB_POL_VIOLATION_*):
  * Source and Destination IPs/entities are identical, or point to internal RFC-1918 subnets (10.x, 172.16-31.x, 192.168.x) or localhost/loopback (127.0.0.1).
  * Proxy loopback reflection, internal health probes (/healthz, /ready, keep-alive), or local WAF inspection artifacts.
  * No external malicious domain or data exfiltration payload is present.
- Administrative Management: Known administrative maintenance running under authorized accounts, standard patch management (SCCM, Tanium, InTune), monitoring agents (Datadog, Zabbix), or signed vendor software updates.
- Benign IT/Developer Activity: Internal SSH/RDP between known administrative subnets without anomalous lateral movement or credential dumping.

### 2. TRUE_POSITIVE (Active Threat / Adversary Attack Tradecraft):
Vote TRUE_POSITIVE (confidence 85-99%) when observed indicators confirm malicious techniques:
- Suspicious Execution & LOLBins (CrowdStrike / EDR alerts):
  * PowerShell execution with base64 encoded payloads (-enc, -encodedcommand), download cradles (IWR, Invoke-WebRequest, DownloadString, bitsadmin, certutil -urlcache).
  * Living-off-the-Land Binaries (LOLBins) used anomalously (vssadmin delete shadows, mshta, rundll32, regsvr32 executing unverified remote scripts).
  * Reconnaissance commands in rapid sequence (whoami, net user, net group, nltest, systeminfo, ipconfig /all).
- Credential Access & Defense Evasion: Mimikatz, LSASS memory dumping, tampering with Windows Defender / EDR services, deleting security event logs.
- Command and Control (C2) & Exfiltration: High-frequency beaconing to untrusted external domains/IPs, DNS tunneling, or unauthorized external data transfer.

### 3. REQUIRES_ATTENTION (Ambiguous / Incomplete Evidence):
Reserve REQUIRES_ATTENTION strictly for cases where:
- Critical telemetry is completely absent, corrupted, or truncated so that no meaningful assessment can be made.
- High-severity alerts with conflicting indicators requiring immediate physical host containment or memory capture by human incident response team.
DO NOT use REQUIRES_ATTENTION for routine internal web policy, loopback, or health-check alerts — classify them as FALSE_POSITIVE with clear rationale.
"""


class AgentPolicyEngine:
    """
    Agent Policy Engine.
    Manages rule-level triage policies, prompts, versioning, criteria,
    and SOC baseline frameworks for the Agentic SOC Intelligence Platform.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_rule_prompt(self, rule_id: str) -> RulePrompt:
        query = select(RulePrompt).where(RulePrompt.rule_id == rule_id).options(
            selectinload(RulePrompt.rule),
            selectinload(RulePrompt.versions)
        )
        res = await self.db.execute(query)
        prompt = res.scalars().first()

        if not prompt:
            rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
            rule = rule_res.scalars().first()
            if not rule:
                raise ValueError(f"SIEM Rule {rule_id} not found")

            prompt = RulePrompt(
                rule_id=rule.id,
                title=f"Investigation Prompt — {rule.name}",
            )
            self.db.add(prompt)
            await self.db.commit()
            await self.db.refresh(prompt)

            # Auto-generate initial template draft
            await self.generate_template_draft(rule_id=rule.id, user_id=None)
            if prompt in self.db:
                self.db.expire(prompt)
            prompt = await self.get_rule_prompt(rule_id)
        elif not prompt.versions or len(prompt.versions) == 0:
            # Self-healing: if rule_prompt exists in database but has no versions, auto-generate initial template draft
            await self.generate_template_draft(rule_id=rule_id, user_id=None)
            if prompt in self.db:
                self.db.expire(prompt)
            prompt = await self.get_rule_prompt(rule_id)

        return prompt

    async def get_rule_prompt(self, rule_id: str) -> Optional[RulePrompt]:
        query = select(RulePrompt).where(RulePrompt.rule_id == rule_id).options(
            selectinload(RulePrompt.rule),
            selectinload(RulePrompt.versions)
        )
        res = await self.db.execute(query)
        return res.scalars().first()

    async def generate_template_draft(self, rule_id: str, user_id: Optional[str] = None) -> PromptVersion:
        """
        Synthesizes a rule-specific prompt draft based on the ingested SIEM rule text.
        This is explicitly tagged as a TEMPLATE-GENERATED DRAFT (NOT AI-generated).
        """
        rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_res.scalars().first()
        if not rule:
            raise ValueError(f"Rule with id {rule_id} not found")

        # Get or create rule prompt parent record
        prompt_res = await self.db.execute(
            select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
        )
        rule_prompt = prompt_res.scalars().first()
        if not rule_prompt:
            rule_prompt = RulePrompt(
                rule_id=rule.id,
                title=f"Investigation Prompt — {rule.name}",
            )
            self.db.add(rule_prompt)
            await self.db.flush()

        next_ver = 1
        if rule_prompt.versions:
            next_ver = max(v.version_number for v in rule_prompt.versions) + 1

        # Synthesize rule-specific prompt sections deterministically from parsed rule attributes
        detection_pattern = rule.pattern_logic or "No specific pattern defined in rule text."
        triggered_attrs = (rule.parsed_metadata or {}).get("triggered_event_attributes", [])
        remediation = rule.remediation or "Follow standard incident response runbook."

        detection_conds = f"""Detection Pattern: {detection_pattern}
Triggered Attributes: {', '.join(triggered_attrs) if triggered_attrs else 'Generic event attributes'}"""

        req_evidence = """1. Full command line and executing process name
2. Parent process hierarchy (PPID lineage)
3. User context (SYSTEM, Administrator, Service Account, or Standard Interactive User)
4. Network connections, remote destination IP/port and domain reputation
5. File hash (SHA256/MD5) reputation and digital signature validity"""

        norm_name = f"{rule.name} {rule.event_type}".lower()

        if "crowdstrike" in norm_name or "suspicious" in norm_name or "process" in norm_name or "activity" in norm_name:
            tp_ind = """- Process execution from unusual temp directories (e.g. C:\\Users\\*\\AppData\\Local\\Temp, /tmp)
- Encoded PowerShell commands (-enc, -encodedcommand) or obfuscated arguments
- Suspicious child processes spawned from Office apps, web servers, or script interpreters (wscript, cscript)
- Known LOLBins (Living Off the Land Binaries) abused for discovery or defense evasion"""
            fp_ind = """- Approved enterprise software deployments (SCCM, Tanium, InTune, Ansible)
- Scheduled administrative scripts signed by internal corporate PKI
- Backup software, monitoring agents (Datadog, Splunk Forwarder)"""
            missing_info = """- Parent process name or command line is truncated in raw event
- User authentication context is absent from event telemetry
- Destination IP is not resolved to an internal host or external ASN"""
            escalation = """- Execution of ransomware precursors (vssadmin delete shadows, bcdedit)
- Credential dumping tools (Mimikatz, lsass access)
- Domain Controller or critical database host compromised"""
            questions = [
                "What is the parent process that spawned this command?",
                "Is the user account an interactive user or a dedicated service account?",
                "Has this executable been observed running on other endpoints in the fleet?",
                "Does the network connection reach a known malicious C2 infrastructure?",
            ]
        elif "web" in norm_name or "policy" in norm_name or "dest" in norm_name or "traffic" in norm_name:
            tp_ind = """- Repeated outbound connections to known malicious domains or external C2 IP addresses
- Data exfiltration payloads encoded in HTTP headers, cookies, or URL query parameters
- Unauthorized port tunneling (e.g. SSH over port 80/443, DNS tunneling)
- Malicious user-agent strings associated with automated attack tools (sqlmap, nikto, cobaltstrike)"""
            fp_ind = """- Internal loopback traffic where source IP and destination IP are identical (local proxy reflection, WAF loopback, localhost testing)
- Web policy alerts triggered by routine internal health-check endpoints (/healthz, /ready, /ping, keep-alive)
- Local corporate proxy re-routing or gateway inspection artifacts
- Internal RFC-1918 traffic (10.x, 172.16-31.x, 192.168.x) accessing approved internal intranet portals without anomalous payloads"""
            missing_info = """- Specific destination URL or HTTP request headers
- Packet payload data to determine if external communication was attempted"""
            escalation = """- High-volume data transfer to unclassified external IP
- Multiple hosts exhibiting identical beaconing behavior"""
            questions = [
                "Are the source and destination IPs both internal/loopback or proxy interfaces?",
                "Is this traffic generated by an automated health check or monitoring service?",
                "Does the request contain any encoded external web destinations?",
            ]
        else:
            tp_ind = """- Executable or script downloaded from untrusted internet domain
- High entropy executable matching known malware signatures or unsigned binary
- Outbound beaconing traffic to suspicious external IP addresses
- Attempted persistence mechanisms (Registry Run keys, cron jobs, systemd unit injection)"""
            fp_ind = """- Software patch downloaded directly from verified vendor domain (Microsoft, Palo Alto, Google)
- Internal security testing or authorized vulnerability scan
- Benign installation package initiated by IT helpdesk"""
            missing_info = """- File hash not present in threat intelligence or local hash repository
- Complete network packet capture or TLS SNI header unavailable"""
            escalation = """- Malicious file executed across multiple subnets within 15 minutes
- Lateral movement indicators following file download"""
            questions = [
                "What was the download URL or source IP of the suspicious file?",
                "Was the file executed after download or blocked inline by security controls?",
                "Does the file hash match any known threat intelligence indicator?",
            ]

        rule_specific = f"""### SPECIFIC INVESTIGATION DIRECTIVE FOR {rule.name.upper()}
Vendor / Event Type: {rule.event_type}
Default Severity: {rule.severity}
Data Source: {rule.data_source or "SIEM Ingestion"}

OBJECTIVE:
Investigate alerts triggered under rule condition: {rule.name}.
Analyze process execution, network connections, source/destination entities, and triggering attributes to classify definitively as TRUE_POSITIVE, FALSE_POSITIVE, or REQUIRES_ATTENTION.

DETECTION CONDITIONS:
{detection_conds}

### TRUE POSITIVE INDICATORS (MALICIOUS ATTACK):
{tp_ind}

### FALSE POSITIVE INDICATORS (BENIGN OPERATIONAL NOISE):
{fp_ind}

### REQUIRED EVIDENCE:
{req_evidence}

### WHEN TO ABSTAIN (REQUIRES ATTENTION):
{missing_info}
"""

        new_version = PromptVersion(
            prompt_id=rule_prompt.id,
            version_number=next_ver,
            status="DRAFT",
            is_template_draft=True,
            common_prompt=COMMON_SOC_BASELINE.strip(),
            rule_specific_prompt=rule_specific.strip(),
            detection_conditions=detection_conds.strip(),
            required_evidence=req_evidence.strip(),
            tp_indicators=tp_ind.strip(),
            fp_indicators=fp_ind.strip(),
            missing_info_criteria=missing_info.strip(),
            escalation_conditions=escalation.strip(),
            analyst_questions=questions,
            change_summary="TEMPLATE-GENERATED DRAFT: Synthesized from SIEM rule specifications with specialized decision criteria",
            created_by_user_id=user_id,
        )

        self.db.add(new_version)
        await self.db.commit()
        await self.db.refresh(new_version)

        return new_version

    async def create_draft_version(
        self,
        rule_id: str,
        data: PromptVersionCreate,
        user_id: Optional[str] = None
    ) -> PromptVersion:
        rule_prompt = await self.get_or_create_rule_prompt(rule_id)

        next_ver = 1
        if rule_prompt.versions:
            next_ver = max(v.version_number for v in rule_prompt.versions) + 1

        new_ver = PromptVersion(
            prompt_id=rule_prompt.id,
            version_number=next_ver,
            status="DRAFT",
            is_template_draft=False,
            common_prompt=data.common_prompt or COMMON_SOC_BASELINE.strip(),
            rule_specific_prompt=data.rule_specific_prompt,
            detection_conditions=data.detection_conditions,
            required_evidence=data.required_evidence,
            tp_indicators=data.tp_indicators,
            fp_indicators=data.fp_indicators,
            missing_info_criteria=data.missing_info_criteria,
            escalation_conditions=data.escalation_conditions,
            analyst_questions=data.analyst_questions,
            change_summary=data.change_summary or f"Version {next_ver} manual draft update",
            created_by_user_id=user_id,
        )

        self.db.add(new_ver)
        await self.db.commit()
        await self.db.refresh(new_ver)
        return new_ver

    async def approve_version(
        self,
        rule_id: str,
        version_id: str,
        user_id: Optional[str] = None,
        change_summary: Optional[str] = None
    ) -> PromptVersion:
        rule_prompt = await self.get_or_create_rule_prompt(rule_id)

        target_version = None
        for v in rule_prompt.versions:
            if v.id == version_id:
                target_version = v
                break

        if not target_version:
            raise ValueError(f"Prompt version {version_id} not found for rule {rule_id}")

        # Archive any currently active approved version
        for v in rule_prompt.versions:
            if v.status == "APPROVED" and v.id != version_id:
                v.status = "ARCHIVED"

        target_version.status = "APPROVED"
        target_version.approved_by_user_id = user_id
        target_version.approved_at = datetime.utcnow()
        if change_summary:
            target_version.change_summary = change_summary

        rule_prompt.active_version_id = target_version.id
        rule_prompt.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(target_version)
        return target_version

    async def rollback_version(
        self,
        rule_id: str,
        target_version_id: str,
        user_id: Optional[str] = None
    ) -> PromptVersion:
        rule_prompt = await self.get_or_create_rule_prompt(rule_id)

        source_version = None
        for v in rule_prompt.versions:
            if v.id == target_version_id:
                source_version = v
                break

        if not source_version:
            raise ValueError(f"Target version {target_version_id} not found")

        # Create a new version that clones source_version and approves it
        next_ver = max(v.version_number for v in rule_prompt.versions) + 1

        rolled_version = PromptVersion(
            prompt_id=rule_prompt.id,
            version_number=next_ver,
            status="APPROVED",
            is_template_draft=source_version.is_template_draft,
            common_prompt=source_version.common_prompt,
            rule_specific_prompt=source_version.rule_specific_prompt,
            detection_conditions=source_version.detection_conditions,
            required_evidence=source_version.required_evidence,
            tp_indicators=source_version.tp_indicators,
            fp_indicators=source_version.fp_indicators,
            missing_info_criteria=source_version.missing_info_criteria,
            escalation_conditions=source_version.escalation_conditions,
            analyst_questions=source_version.analyst_questions,
            change_summary=f"Rollback to Version {source_version.version_number}",
            created_by_user_id=user_id,
            approved_by_user_id=user_id,
            approved_at=datetime.utcnow(),
        )

        # Archive others
        for v in rule_prompt.versions:
            if v.status == "APPROVED":
                v.status = "ARCHIVED"

        self.db.add(rolled_version)
        await self.db.flush()

        rule_prompt.active_version_id = rolled_version.id
        rule_prompt.updated_at = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(rolled_version)
        return rolled_version

    def _version_to_dict(self, v: PromptVersion) -> Dict[str, Any]:
        return {
            "version_id": v.id,
            "version_number": v.version_number,
            "status": v.status,
            "is_template_draft": v.is_template_draft,
            "common_prompt": v.common_prompt,
            "rule_specific_prompt": v.rule_specific_prompt,
            "detection_conditions": v.detection_conditions,
            "required_evidence": v.required_evidence,
            "tp_indicators": v.tp_indicators,
            "fp_indicators": v.fp_indicators,
            "missing_info_criteria": v.missing_info_criteria,
            "escalation_conditions": v.escalation_conditions,
            "analyst_questions": v.analyst_questions or [],
            "change_summary": v.change_summary,
            "created_by_user_id": v.created_by_user_id,
            "approved_by_user_id": v.approved_by_user_id,
            "approved_at": v.approved_at.isoformat() if v.approved_at else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }

    def _rule_to_export_item(self, rule: Rule, prompt: Optional[RulePrompt]) -> Dict[str, Any]:
        versions = prompt.versions if (prompt and prompt.versions) else []
        active_v = next((v for v in versions if v.id == prompt.active_version_id), None) if prompt else None
        if not active_v and versions:
            active_v = versions[0]

        return {
            "rule_id": rule.id,
            "rule_identifier": rule.rule_id,
            "rule_name": rule.name,
            "event_type": rule.event_type,
            "severity": rule.severity,
            "status": rule.status,
            "data_source": rule.data_source,
            "detection_tech": rule.detection_tech,
            "evaluation_mode": rule.evaluation_mode,
            "description": rule.description,
            "pattern_logic": rule.pattern_logic,
            "remediation": rule.remediation,
            "parsed_metadata": rule.parsed_metadata or {},
            "prompt_metadata": {
                "prompt_id": prompt.id if prompt else None,
                "has_approved_prompt": any(v.status == "APPROVED" for v in versions),
                "total_versions": len(versions),
                "active_version_id": prompt.active_version_id if prompt else None,
                "active_version_number": active_v.version_number if active_v else None,
                "last_updated": (prompt.updated_at if prompt else rule.updated_at).isoformat() if (prompt or rule) else None,
            },
            "active_prompt_configuration": self._version_to_dict(active_v) if active_v else None,
            "all_versions": [self._version_to_dict(v) for v in versions],
        }

    def _format_markdown_report(self, export_items: List[Dict[str, Any]], title: str = "Agent Intelligence Studio — Rule-Wise Prompts & Configurations") -> str:
        lines = [
            f"# {title}",
            "",
            f"- **Generated At:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Total Rules Included:** {len(export_items)}",
            "",
            "---",
            "",
        ]

        for idx, item in enumerate(export_items, start=1):
            rule_name = item.get("rule_name", "Unknown Rule")
            severity = item.get("severity", "MEDIUM")
            lines.append(f"## {idx}. {rule_name} `[{severity}]`")
            lines.append(f"- **Internal Rule ID:** `{item.get('rule_id')}`")
            lines.append(f"- **Event Type:** `{item.get('event_type')}`")
            lines.append(f"- **Data Source:** {item.get('data_source') or 'N/A'}")

            active_cfg = item.get("active_prompt_configuration")
            if active_cfg:
                status_badge = active_cfg.get("status")
                is_template = " (Template Synthesized)" if active_cfg.get("is_template_draft") else " (Manual Draft)"
                lines.append(f"- **Active Baseline:** Version {active_cfg.get('version_number')} `[{status_badge}]`{is_template}")
                lines.append(f"- **Change Summary:** *{active_cfg.get('change_summary') or 'N/A'}*")
                lines.append("")
                lines.append("### 1. COMMON SOC BASELINE PROTOCOL")
                lines.append("```")
                lines.append(active_cfg.get("common_prompt") or "N/A")
                lines.append("```")
                lines.append("")
                lines.append("### 2. RULE-SPECIFIC DIRECTIVE & PATTERN DETAILS")
                lines.append("```")
                lines.append(active_cfg.get("rule_specific_prompt") or "N/A")
                lines.append("```")
                lines.append("")
                lines.append("### 3. DETECTION CONDITIONS & PATTERN LOGIC")
                lines.append(f"> {active_cfg.get('detection_conditions') or 'None specified'}")
                lines.append("")
                lines.append("### 4. MANDATORY EVIDENCE GATHERING CHECKLIST")
                lines.append(active_cfg.get("required_evidence") or "None specified")
                lines.append("")
                lines.append("### 5. TRUE POSITIVE INDICATORS (MALICIOUS ATTACK)")
                lines.append(active_cfg.get("tp_indicators") or "None specified")
                lines.append("")
                lines.append("### 6. FALSE POSITIVE INDICATORS (BENIGN OPERATIONAL NOISE)")
                lines.append(active_cfg.get("fp_indicators") or "None specified")
                lines.append("")
                lines.append("### 7. WHEN TO ABSTAIN (REQUIRES ATTENTION)")
                lines.append(active_cfg.get("missing_info_criteria") or "None specified")
                lines.append("")
                lines.append("### 8. P1/P2 ESCALATION CONDITIONS")
                lines.append(active_cfg.get("escalation_conditions") or "None specified")
                lines.append("")
                lines.append("### 9. STANDARD INVESTIGATIVE Q&A CHECKLIST")
                questions = active_cfg.get("analyst_questions", [])
                if questions:
                    for q_idx, q in enumerate(questions, start=1):
                        lines.append(f"{q_idx}. {q}")
                else:
                    lines.append("*No questions configured.*")
            else:
                lines.append("*No prompt configuration found for this rule.*")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    async def export_all_rule_prompts(self, format: str = "json") -> Tuple[str, str, str]:
        rules_res = await self.db.execute(select(Rule).order_by(Rule.name.asc()))
        rules = rules_res.scalars().all()

        prompts_res = await self.db.execute(select(RulePrompt).options(selectinload(RulePrompt.versions)))
        prompts_by_rule_id = {rp.rule_id: rp for rp in prompts_res.scalars().all()}

        items = []
        for r in rules:
            rp = prompts_by_rule_id.get(r.id)
            items.append(self._rule_to_export_item(r, rp))

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        if format.lower() in ("markdown", "md"):
            md_content = self._format_markdown_report(items)
            return md_content, "text/markdown; charset=utf-8", f"agent_intelligence_studio_rules_prompts_{timestamp}.md"

        export_data = {
            "schema_version": "1.0",
            "title": "Agent Intelligence Studio — Rule-Wise Prompts & Configurations",
            "exported_at": datetime.utcnow().isoformat(),
            "total_rules": len(items),
            "rules": items,
        }
        return json.dumps(export_data, indent=2), "application/json", f"agent_intelligence_studio_rules_prompts_{timestamp}.json"

    async def export_single_rule_prompt(self, rule_id: str, format: str = "json") -> Tuple[str, str, str]:
        rule_res = await self.db.execute(select(Rule).where(Rule.id == rule_id))
        rule = rule_res.scalars().first()
        if not rule:
            raise ValueError(f"Rule with id {rule_id} not found")

        prompt = await self.get_or_create_rule_prompt(rule_id)
        item = self._rule_to_export_item(rule, prompt)

        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in rule.name.lower())[:40]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        if format.lower() in ("markdown", "md"):
            md_content = self._format_markdown_report([item], title=f"Agent Intelligence Policy — {rule.name}")
            return md_content, "text/markdown; charset=utf-8", f"rule_prompt_{safe_name}_{timestamp}.md"

        export_data = {
            "schema_version": "1.0",
            "title": f"Agent Intelligence Policy — {rule.name}",
            "exported_at": datetime.utcnow().isoformat(),
            "rule": item,
        }
        return json.dumps(export_data, indent=2), "application/json", f"rule_prompt_{safe_name}_{timestamp}.json"


# Backward compatibility alias
PromptStudioService = AgentPolicyEngine

