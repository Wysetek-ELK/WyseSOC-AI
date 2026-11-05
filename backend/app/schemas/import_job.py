from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel


class ImportJobResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    total_files: int
    imported_count: int
    duplicate_count: int
    error_count: int
    status: str
    error_details: List[Dict[str, Any]] = []
    created_by: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ImportSummaryResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    total_found: int
    imported: int
    duplicates: int
    rules_detected: int
    errors: int
    error_messages: List[str] = []
