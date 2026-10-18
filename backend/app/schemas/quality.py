from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class QualityCheckResultResponse(BaseModel):
    id: str
    run_id: str
    dataset_id: str
    check_id: str
    check_name: str
    category: str
    status: str
    severity: str
    affected_rows: int
    affected_columns: Optional[List[str]] = None
    explanation: str
    evidence: Optional[Dict[str, Any]] = None
    suggested_action: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DimensionScore(BaseModel):
    score: float
    weight: float
    checks_count: int
    passed_count: int
    warning_count: int
    failed_count: int
    explanation: str


class QualityScoreBreakdown(BaseModel):
    overall_score: float
    is_passing: bool
    critical_failures_count: int
    total_checks: int
    passed_checks: int
    warning_checks: int
    failed_checks: int
    dimensions: Dict[str, DimensionScore]
    summary_text: str


class QualityReportResponse(BaseModel):
    dataset_id: str
    run_id: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    overall_score: float
    breakdown: QualityScoreBreakdown
    checks: List[QualityCheckResultResponse]
