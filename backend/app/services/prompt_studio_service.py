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

COMMON_SOC_BASELINE = """# ENTERPRISE SOC INVESTIGATION PROTOCOL
You are an advanced Security Operations Center (SOC) Incident Analysis Assistant.
Your objective is to perform comprehensive, evidence-based triage on normalized telemetry alerts.

GUIDELINES:
1. Ground your reasoning strictly on observed telemetry attributes and events.
2. Formulate explicit investigative hypotheses (Benign System Activity vs. Malicious Activity).
3. Identify all critical artifacts: execution paths, parent-child process lineage, network connections, and user context.
4. Categorize verdicts into:
   - TRUE_POSITIVE: Clear malicious activity or unauthorized adversary behavior matching known threat techniques.
   - FALSE_POSITIVE: Legitimate administrative actions, scheduled tasks, benign software updates, or expected business operations.
   - REQUIRES_ATTENTION: Inconclusive findings requiring immediate human endpoint isolation, live forensic triage, or missing telemetry.
5. Never invent or hallucinate IOCs, logs, or user credentials.
"""


class PromptStudioService:
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
            
            # Expire session so selectinload reloads fresh versions
            self.db.expire_all()
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

        rule_specific = f"""### SPECIFIC INVESTIGATION DIRECTIVE FOR {rule.name.upper()}
Vendor / Event Type: {rule.event_type}
Default Severity: {rule.severity}
Data Source: {rule.data_source}

OBJECTIVE:
Investigate alerts triggered under rule condition: {rule.name}.
Analyze process command lines, execution directories, and triggering attributes to determine whether execution is unauthorized adversary activity or benign IT management.
"""

        detection_conds = f"""Detection Pattern: {detection_pattern}
Triggered Attributes: {', '.join(triggered_attrs) if triggered_attrs else 'Generic event attributes'}"""

        req_evidence = """1. Full command line and executing process name
2. Parent process hierarchy (PPID lineage)
3. User context (SYSTEM, Administrator, Service Account, or Standard Interactive User)
4. Network connections, remote destination IP/port and domain reputation
5. File hash (SHA256/MD5) reputation and digital signature validity"""

        if "CrowdStrike" in rule.name or "Activity" in rule.name:
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
            change_summary="TEMPLATE-GENERATED DRAFT: Synthesized from SIEM rule specifications (Not AI generated)",
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
