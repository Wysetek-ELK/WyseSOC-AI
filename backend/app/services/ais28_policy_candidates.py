"""
AIS 2.8 — Experimental Candidate Policy Templates (Diagnostic / Non-Promoted).

CRITICAL GOVERNANCE INVARIANTS:
- These templates are strictly EXPERIMENTAL CANDIDATES (status='EXPERIMENTAL_CANDIDATE').
- They NEVER overwrite or modify existing approved production PromptVersion records in DB.
- They NEVER auto-promote without explicit human review, testing, and administrator approval.
- They remediate AIS 2.7 policy contamination defects:
  1. Removes contradictory 'Web Policy Violations' and 'DO NOT use REQUIRES_ATTENTION' instructions.
  2. Aligns Prisma SASE policy strictly with perimeter network/SASE attributes (file.name, http.url,
     application.name, web.category, network.source_ip, network.destination_ip) instead of EDR process fields.
  3. Removes unverified digital signature requirements when CrowdStrike FortiSIEM events omit signature fields.
"""

from __future__ import annotations

from app.models.prompt import PromptVersion


def get_experimental_candidate_policy(rule_identifier: str) -> PromptVersion:
    """
    Returns an isolated experimental candidate PromptVersion object (in-memory only, not DB-persisted)
    aligned cleanly to real FortiSIEM schemas for controlled benchmark Experiment D.
    """
    clean = str(rule_identifier or "").strip().lower()
    if "cs_" in clean or "crowdstrike" in clean or "suspicious_activity" in clean:
        return PromptVersion(
            id="ais28-exp-candidate-cs-v1",
            prompt_id="ais28-exp-candidate-cs-prompt",
            version_number=9901,
            status="EXPERIMENTAL_CANDIDATE",
            common_prompt=(
                "AIS 2.8 Experimental Candidate Policy: Evaluate endpoint suspicious activity strictly from verified "
                "FortiSIEM / CrowdStrike telemetry, complete detection rule logic, and deterministic evidence intelligence."
            ),
            rule_specific_prompt=(
                "Inspect process.file_name, process.command_line, path_classification, user.name, endpoint.hostname, "
                "and endpoint.process_blocked. Evaluate whether observed software execution reflects unauthorized remote "
                "access/dual-use tooling, malicious execution, authorized IT management software, or genuinely "
                "insufficient authorization context."
            ),
            detection_conditions=(
                "CrowdStrike suspicious endpoint process/tool execution (EppDetectionSummaryEvent). "
                "Treat process execution in Program Files cleanly per path_classification; never call Program Files a temp directory."
            ),
            required_evidence="process.file_name, process.command_line, endpoint.hostname, user.name",
            tp_indicators=(
                "Observed unauthorized remote administration utility (e.g. UltraViewer, TeamViewer, AnyDesk), malicious script/LOLBin abuse, "
                "or unauthorized privilege/persistence execution supported by process telemetry without IT authorization context."
            ),
            fp_indicators=(
                "Verified enterprise systems/endpoint management or IT security agent (e.g. ccmexec, TanClient, QualysAgent, NessusAgent) "
                "executing normally or explicitly verified authorized activity in telemetry."
            ),
            missing_info_criteria=(
                "Return REQUIRES_ATTENTION only when ambiguity prevents distinguishing authorized business IT use from unauthorized execution "
                "and neither malicious compromise nor explicit authorization is established."
            ),
            escalation_conditions=(
                "Active credential dumping, persistence modification, ransomware indicator, or unblocked unauthorized remote access on domain controller/server."
            ),
            analyst_questions=[
                "Is an approved IT change ticket or software allowlist entry documented for this host and tool?",
                "Did endpoint protection block execution (endpoint.process_blocked) or leave an active session?",
            ],
        )

    return PromptVersion(
        id="ais28-exp-candidate-prisma-v1",
        prompt_id="ais28-exp-candidate-prisma-prompt",
        version_number=9902,
        status="EXPERIMENTAL_CANDIDATE",
        common_prompt=(
            "AIS 2.8 Experimental Candidate Policy: Evaluate perimeter gateway/SASE suspicious file transfer events "
            "strictly from observed SASE network/web/file attributes without requiring absent EDR process telemetry."
        ),
        rule_specific_prompt=(
            "Inspect file.name, file_extension_class, file_and_web_context.hashes, http.url, web.category, application.name, "
            "network.source_ip, network.destination_ip, and security.action. Do NOT claim endpoint execution occurred unless "
            "execution_evidence_present=true."
        ),
        detection_conditions=(
            "Prisma SASE gateway detection of suspicious file download or transfer over HTTP/HTTPS."
        ),
        required_evidence="file.name, network.source_ip, network.destination_ip, http.url",
        tp_indicators=(
            "Confirmed malicious hash match, known malware delivery URL/domain, or confirmed unauthorized executable/payload delivery corroborated in telemetry."
        ),
        fp_indicators=(
            "Confirmed benign web UI static resource/library (e.g., CSS, image, standard framework JS from verified SaaS/CDN business traffic) "
            "with no malicious indicators in URL, filename, hash, or category."
        ),
        missing_info_criteria=(
            "Return REQUIRES_ATTENTION when an unknown executable, archive, script, or suspicious file transfer has no file hash verdict, "
            "sandbox result, or endpoint execution telemetry to definitively confirm maliciousness or benign business legitimacy."
        ),
        escalation_conditions=(
            "Executable payload downloaded to server subnet without gateway block or confirmed malicious hash."
        ),
        analyst_questions=[
            "Did gateway threat/wildfire inspection allow or block the file download?",
            "Look up observed SHA256/MD5 or URL in internal threat intelligence and verify user business need.",
        ],
    )
