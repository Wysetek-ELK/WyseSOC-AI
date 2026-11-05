import pytest
from app.services.rule_parser import RuleParser

SAMPLE_CROWDSTRIKE_TEXT = """Name
Crowdstrike: Suspicious Activity
Event Type
PH_RULE_CS_SUSPICIOUS_ACTIVITY
Description
Crowdstrike agent detected suspicious activity
Status
INACTIVE    Notification Frequency: 1 Day    Incident Category: Server
Data Source
Crowdstrike via FALCON_STREAMING_API or FALCON_DATA_REPLICATOR
Detection Technology
Correlation
Evaluation Mode
Streaming
Pattern: CSDetect
IF
Event Type IN Crowdstrike-Falcon-EppDetectionSummaryEvent-suspicious-activity
WHERE
COUNT(Matched Events) >= 1
Incidents
GENERATE
Severity 8 (MEDIUM) Incident: PH_RULE_CS_SUSPICIOUS_ACTIVITY Display Name: Crowdstrike: Suspicious Activity
Triggered Event Attributes
Event Receive Time,Event Type,Message,Host Name,User,Attack Tactic,Attack Technique,File Name,Command
"""

SAMPLE_PRISMA_TEXT = """Name
Prisma SASE: Suspicious File Threat Detection
Event Type
Prisma_SASE_Suspicious_File_Threat_Detection_
Description
Detects genuinely suspicious file downloads from Prisma SASE
Status
ACTIVE    Notification Frequency: 1 Hour    Incident Category: Other
Data Source
Palo Alto Prisma SASE
Detection Technology
Correlation
Evaluation Mode
Streaming
Remediation:
Verify file hash, check source user activity.
Pattern: Filter_1
IF
Event Type = PaloAltoPrismaSASE-THREAT-file
Incidents
GENERATE
Severity 7 (HIGH) Incident: Prisma_SASE_Suspicious_File_Threat_Detection_
Triggered Event Attributes
Event Receive Time,Event Type,Reporting IP,Raw Event Log,Source User,Source IP,File Name,Application Name
"""


def test_parse_crowdstrike_rule():
    parsed = RuleParser.parse_rule_text(SAMPLE_CROWDSTRIKE_TEXT)
    assert parsed["name"] == "Crowdstrike: Suspicious Activity"
    assert parsed["event_type"] == "PH_RULE_CS_SUSPICIOUS_ACTIVITY"
    assert parsed["severity"] == "MEDIUM"
    assert parsed["status"] == "INACTIVE"
    assert "FALCON" in parsed["data_source"]
    assert "Triggered Event Attributes" in SAMPLE_CROWDSTRIKE_TEXT
    assert len(parsed["parsed_metadata"]["triggered_attributes"]) == 9
    assert "Host Name" in parsed["parsed_metadata"]["triggered_attributes"]


def test_parse_prisma_rule():
    parsed = RuleParser.parse_rule_text(SAMPLE_PRISMA_TEXT)
    assert parsed["name"] == "Prisma SASE: Suspicious File Threat Detection"
    assert parsed["event_type"] == "Prisma_SASE_Suspicious_File_Threat_Detection_"
    assert parsed["severity"] == "HIGH"
    assert parsed["status"] == "ACTIVE"
    assert "Prisma SASE" in parsed["data_source"]
    assert len(parsed["parsed_metadata"]["triggered_attributes"]) == 8
    assert "Source User" in parsed["parsed_metadata"]["triggered_attributes"]
    assert "Verify file hash" in parsed["remediation"]

