import re
from typing import Dict, Any, Optional


class DetectionContextEngine:
    """
    Detection Context Engine (formerly RuleParser).
    Parses vendor text-based SIEM rule definitions (e.g., CrowdStrike, Prisma SASE)
    into structured detection context and pattern logic while preserving full raw text.
    """

    @classmethod
    def parse_rule_text(cls, text: str) -> Dict[str, Any]:
        lines = [line.strip() for line in text.strip().splitlines()]
        data: Dict[str, Any] = {
            "name": "",
            "event_type": "",
            "description": "",
            "severity": "MEDIUM",
            "status": "ACTIVE",
            "data_source": "",
            "detection_tech": "",
            "evaluation_mode": "",
            "pattern_logic": "",
            "remediation": "",
            "raw_rule_text": text,
            "parsed_metadata": {},
        }

        # Simple section state machine
        current_header = None
        buffer = []
        sections: Dict[str, str] = {}

        headers_known = [
            "name",
            "event type",
            "description",
            "status",
            "data source",
            "detection technology",
            "evaluation mode",
            "remediation",
            "remediation:",
            "pattern",
            "pattern conditions",
            "incidents",
            "watch lists",
            "triggered event attributes",
            "tag",
        ]

        def flush_section(header: Optional[str], content_lines: list):
            if header:
                val = "\n".join(content_lines).strip()
                sections[header.lower().rstrip(":")] = val

        i = 0
        while i < len(lines):
            line = lines[i]
            lower_line = line.lower().rstrip(":")

            # Check if this line is a known header or begins with "Pattern:"
            if lower_line in [h.rstrip(":") for h in headers_known] or line.lower().startswith("pattern:"):
                flush_section(current_header, buffer)
                if line.lower().startswith("pattern:"):
                    current_header = "pattern_logic"
                    buffer = [line]
                else:
                    current_header = lower_line
                    buffer = []
            else:
                if current_header:
                    buffer.append(line)
                else:
                    if line:
                        buffer.append(line)
            i += 1

        flush_section(current_header, buffer)

        # Extract fields
        if "name" in sections:
            data["name"] = sections["name"].splitlines()[0].strip()

        if "event type" in sections:
            data["event_type"] = sections["event type"].splitlines()[0].strip()

        if "description" in sections:
            data["description"] = sections["description"]

        if "status" in sections:
            status_line = sections["status"]
            if "INACTIVE" in status_line.upper():
                data["status"] = "INACTIVE"
            elif "ACTIVE" in status_line.upper():
                data["status"] = "ACTIVE"
            data["parsed_metadata"]["status_raw"] = status_line

        if "data source" in sections:
            data["data_source"] = sections["data source"]

        if "detection technology" in sections:
            data["detection_tech"] = sections["detection technology"]

        if "evaluation mode" in sections:
            data["evaluation_mode"] = sections["evaluation mode"]

        if "remediation" in sections:
            data["remediation"] = sections["remediation"]

        if "pattern_logic" in sections:
            data["pattern_logic"] = sections["pattern_logic"]
        elif "pattern conditions" in sections:
            data["pattern_logic"] = sections["pattern conditions"]
        elif "pattern" in sections:
            data["pattern_logic"] = sections["pattern"]

        if "triggered event attributes" in sections:
            attrs = [a.strip() for a in sections["triggered event attributes"].split(",") if a.strip()]
            data["parsed_metadata"]["triggered_attributes"] = attrs

        # Severity extraction from Incidents section or Pattern
        incidents_section = sections.get("incidents", "")
        sev_match = re.search(r"Severity\s+\d+\s*\((CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL)\)", incidents_section, re.IGNORECASE)
        if sev_match:
            data["severity"] = sev_match.group(1).upper()
        else:
            # Fallback severity regex
            sev_fallback = re.search(r"\b(CRITICAL|HIGH|MEDIUM|LOW|INFO|INFORMATIONAL)\b", text, re.IGNORECASE)
            if sev_fallback:
                val = sev_fallback.group(1).upper()
                data["severity"] = "INFORMATIONAL" if val == "INFO" else val

        # Fallbacks if name or event_type weren't under explicit headers
        if not data["name"]:
            data["name"] = data["event_type"] or "Unknown Rule"
        if not data["event_type"]:
            data["event_type"] = re.sub(r"[^A-Za-z0-9_]", "_", data["name"])

        data["rule_id"] = data["event_type"]
        return data


# Backward compatibility alias
RuleParser = DetectionContextEngine


