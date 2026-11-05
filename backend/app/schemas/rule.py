from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel


class RuleBase(BaseModel):
    rule_id: str
    name: str
    event_type: str
    description: Optional[str] = ""
    severity: Optional[str] = "MEDIUM"
    status: Optional[str] = "ACTIVE"
    data_source: Optional[str] = ""
    detection_tech: Optional[str] = ""
    evaluation_mode: Optional[str] = ""
    pattern_logic: Optional[str] = ""
    remediation: Optional[str] = ""
    raw_rule_text: Optional[str] = ""
    parsed_metadata: Optional[Dict[str, Any]] = None


class RuleCreate(RuleBase):
    pass


class RuleResponse(RuleBase):
    id: str
    incident_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RuleDetailResponse(RuleResponse):
    pass


class RuleListResponse(BaseModel):
    items: List[RuleResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
