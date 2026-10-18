from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class IngestionRunResponse(BaseModel):
    id: str
    dataset_id: str
    run_type: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    row_count: int
    column_count: int
    quality_score: Optional[float] = None
    summary: Optional[str] = None
    error_message: Optional[str] = None
    file_hash: Optional[str] = None

    class Config:
        from_attributes = True


class RunComparisonResponse(BaseModel):
    dataset_id: str
    current_run_id: str
    previous_run_id: Optional[str] = None
    has_comparison: bool
    quality_score_change: float
    row_count_change: int
    new_failures: List[Dict[str, Any]]
    resolved_failures: List[Dict[str, Any]]
    new_anomalies_count: int
    schema_changed: bool
    summary: str
