from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    total_datasets: int
    healthy_datasets: int
    warning_datasets: int
    critical_datasets: int
    unavailable_sources: int
    average_quality_score: float
    total_anomalies_detected: int
    pending_anomalies_count: int
    recent_runs: List[Dict[str, Any]]
    recent_anomalies: List[Dict[str, Any]]
    recent_schema_changes: List[Dict[str, Any]]
    quality_score_trends: List[Dict[str, Any]]
