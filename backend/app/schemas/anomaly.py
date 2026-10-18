from typing import Optional
from datetime import datetime
from pydantic import BaseModel


class AnomalyFindingResponse(BaseModel):
    id: str
    run_id: str
    dataset_id: str
    column_name: str
    row_index: int
    row_identifier: Optional[str] = None
    value: str
    detection_method: str
    threshold_rule: str
    severity: str
    score: Optional[float] = None
    explanation: str
    review_status: str
    acknowledged_notes: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AnomalyAcknowledgeRequest(BaseModel):
    notes: Optional[str] = None
    is_false_positive: bool = False
