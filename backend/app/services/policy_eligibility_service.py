"""
Centralized Policy Version Governance & Runtime Eligibility Service.
Shared across:
- Local LLM Verdict Pipeline (live triage & simulation)
- Policy Activation & Approval Governance
- Rollback Verification
- Automated Fallback Guardrails
- Agent Intelligence Studio Status Indicators
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.prompt import RulePrompt, PromptVersion
from app.models.rule import Rule
from app.utils.datetime_utils import utc_now


@dataclass
class PolicyEligibilityResult:
    is_eligible: bool
    status: str  # "ELIGIBLE", "POLICY_REVOKED", "POLICY_ARCHIVED", "POLICY_DRAFT", "NO_ELIGIBLE_POLICY", "SEMANTIC_MISMATCH", "RULE_SUSPENDED"
    reason_code: str
    explanation: str
    policy_version: Optional[PromptVersion] = None
    rule: Optional[Rule] = None
    requires_revocation: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


class PolicyEligibilityService:
    """Authoritative policy version governance and runtime safety engine."""

    @classmethod
    def detect_semantic_mismatch(
        cls,
        rule: Rule,
        prompt_version: PromptVersion,
        archetype: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Detects if a policy version contains severe semantic contradictions against
        the detection archetype and SIEM rule definition.
        """
        rule_name = (rule.name or "").lower()
        rule_id = (rule.rule_id or "").lower()
        evt = (rule.event_type or "").lower()
        if isinstance(prompt_version, str):
            prompt_body = prompt_version.lower()
        elif prompt_version:
            prompt_body = f"{getattr(prompt_version, 'rule_specific_prompt', '') or ''} {getattr(prompt_version, 'detection_conditions', '') or ''} {getattr(prompt_version, 'required_evidence', '') or ''} {getattr(prompt_version, 'tp_indicators', '') or ''}".lower()
        else:
            return False, None

        # Check 1: Target rule is NETWORK_SCAN but policy contains generic endpoint malware file-execution logic
        is_scan_rule = (
            "scan" in rule_name
            or "scan" in rule_id
            or "scan" in evt
            or (archetype and "scan" in archetype.lower())
        )
        if is_scan_rule:
            malware_indicators = [
                "malware infection",
                "malicious binary",
                "process execution",
                "process.name",
                "parent process",
                "file hash",
                "powershell invocation",
                "endpoint file execution",
            ]
            network_indicators = [
                "scan",
                "port",
                "sweep",
                "destport",
                "destination_port",
                "destip",
                "destination_ip",
                "connection",
                "syn",
                "syn_flood",
                "tcp",
                "udp",
                "host scan",
            ]
            has_malware = any(m in prompt_body for m in malware_indicators)
            has_network = any(n in prompt_body for n in network_indicators)

            # If heavily infested with malware keywords and missing network scan concepts
            if has_malware and not has_network:
                ver_num = getattr(prompt_version, "version_number", "?")
                return (
                    True,
                    f"Policy v{ver_num} contains endpoint malware/binary-execution instructions incompatible with NETWORK_SCAN detection rule '{rule.name}'."
                )

        return False, None

    @classmethod
    async def evaluate_eligibility(
        cls,
        db: AsyncSession,
        rule: Optional[Rule],
        candidate_version: Optional[PromptVersion] = None,
        active_approved_version: Optional[PromptVersion] = None,
        is_simulation: bool = False,
        archetype: Optional[str] = None,
    ) -> PolicyEligibilityResult:
        """
        Evaluates whether a policy version can safely be dispatched to Local LLM (Server 2).
        Enforces strict lifecycle boundaries: DRAFT -> VALIDATED -> APPROVED -> ACTIVE,
        with REVOKED and ARCHIVED terminals.
        """
        if not rule:
            return PolicyEligibilityResult(
                is_eligible=False,
                status="NO_ELIGIBLE_POLICY",
                reason_code="RULE_NOT_FOUND",
                explanation="No detection rule specified or resolved. AI verdict generation deferred to human analyst.",
            )

        # 1. Fetch parent RulePrompt and check rule-level suspension
        rp_res = await db.execute(
            select(RulePrompt).where(RulePrompt.rule_id == rule.id).options(selectinload(RulePrompt.versions))
        )
        rule_prompt = rp_res.scalars().first()

        if rule_prompt and getattr(rule_prompt, "ai_execution_suspended", False):
            return PolicyEligibilityResult(
                is_eligible=False,
                status="RULE_SUSPENDED",
                reason_code="RULE_AI_EXECUTION_SUSPENDED",
                explanation=f"AI verdict execution is suspended for rule '{rule.name}' (Reason: {rule_prompt.suspension_reason or 'Administrative safety hold'}).",
                rule=rule,
            )

        # 2. Resolve target policy version
        target_version = active_approved_version
        if is_simulation:
            target_version = candidate_version or active_approved_version

        if not target_version:
            if candidate_version and getattr(candidate_version, "status", "") == "DRAFT":
                return PolicyEligibilityResult(
                    is_eligible=False,
                    status="DRAFT_NOT_APPROVED",
                    reason_code="DRAFT_NOT_APPROVED",
                    explanation=f"Policy version v{getattr(candidate_version, 'version_number', 0)} is in DRAFT status and cannot be dispatched for production verdicts until validated and approved.",
                    policy_version=candidate_version,
                    rule=rule,
                )
            return PolicyEligibilityResult(
                is_eligible=False,
                status="NO_ELIGIBLE_POLICY",
                reason_code="POLICY_NOT_APPROVED",
                explanation=f"No approved policy version is active for rule '{rule.name}'. Triage deferred to human analyst.",
                rule=rule,
            )

        v_status = str(getattr(target_version, "status", "DRAFT") or "DRAFT").upper().strip()

        # 3. Check REVOKED state
        if v_status == "REVOKED":
            rev_reason = getattr(target_version, "revocation_reason", None) or "Previously approved policy is no longer trusted"
            return PolicyEligibilityResult(
                is_eligible=False,
                status="POLICY_REVOKED",
                reason_code="POLICY_REVOKED",
                explanation=f"Policy version v{target_version.version_number} was revoked (Reason: {rev_reason}). AI verdict execution is suspended for this rule until a corrected policy is validated and approved.",
                policy_version=target_version,
                rule=rule,
                details={
                    "revoked_at": str(getattr(target_version, "revoked_at", "")),
                    "revocation_reason": rev_reason,
                    "previous_status": getattr(target_version, "previous_status", None),
                }
            )

        # 4. Check ARCHIVED state
        if v_status == "ARCHIVED":
            return PolicyEligibilityResult(
                is_eligible=False,
                status="POLICY_ARCHIVED",
                reason_code="POLICY_ARCHIVED",
                explanation=f"Policy version v{target_version.version_number} is ARCHIVED and not eligible for active verdict execution.",
                policy_version=target_version,
                rule=rule,
            )

        # 5. Check DRAFT state for live production triage
        if not is_simulation and v_status != "APPROVED":
            return PolicyEligibilityResult(
                is_eligible=False,
                status="POLICY_DRAFT",
                reason_code="POLICY_NOT_APPROVED",
                explanation=f"Policy version v{target_version.version_number} is in {v_status} state and has not been approved for production verdict execution.",
                policy_version=target_version,
                rule=rule,
            )

        # 6. Check Semantic Mismatch
        is_mismatch, mismatch_desc = cls.detect_semantic_mismatch(rule, target_version, archetype=archetype)
        if is_mismatch:
            return PolicyEligibilityResult(
                is_eligible=False,
                status="SEMANTIC_MISMATCH",
                reason_code="POLICY_SEMANTIC_MISMATCH",
                explanation=mismatch_desc or f"Policy v{target_version.version_number} has a verified semantic mismatch with rule '{rule.name}'.",
                policy_version=target_version,
                rule=rule,
                requires_revocation=True,
                details={"mismatch_reason": mismatch_desc}
            )

        # 7. In simulation mode with a draft: mark explicitly as simulation
        if is_simulation and v_status != "APPROVED":
            return PolicyEligibilityResult(
                is_eligible=True,
                status="SIMULATION_DRAFT",
                reason_code="DRAFT_SIMULATION_ONLY",
                explanation=f"Offline draft simulation for v{target_version.version_number} ({v_status}). Not valid for production execution.",
                policy_version=target_version,
                rule=rule,
            )

        # 8. All checks passed
        return PolicyEligibilityResult(
            is_eligible=True,
            status="ELIGIBLE",
            reason_code="APPROVED_ACTIVE",
            explanation=f"Policy version v{target_version.version_number} is APPROVED and eligible for active AI verdict execution.",
            policy_version=target_version,
            rule=rule,
        )
