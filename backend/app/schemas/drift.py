from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class DriftMetricDetail(BaseModel):
    column_name: str
    metric_type: str  # 'psi', 'ks_test', 'mean_shift', 'variance_shift', 'category_shift'
    metric_value: float
    p_value: Optional[float] = None
    drift_detected: bool
    interpretation: str
    details: Optional[Dict[str, Any]] = None


class DatasetDriftSummaryResponse(BaseModel):
    dataset_id: str
    baseline_run_id: Optional[str] = None
    current_run_id: Optional[str] = None
    baseline_date: Optional[datetime] = None
    current_date: Optional[datetime] = None
    drift_available: bool
    columns_analyzed: int
    drifted_columns_count: int
    has_significant_drift: bool
    summary: str
    metrics: List[DriftMetricDetail]
