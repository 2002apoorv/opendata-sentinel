from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class ColumnSchemaItem(BaseModel):
    name: str
    inferred_type: str
    nullable: bool
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: List[Any] = []


class SchemaSnapshotResponse(BaseModel):
    id: str
    run_id: str
    dataset_id: str
    row_count: int
    column_count: int
    columns_schema: List[ColumnSchemaItem]
    created_at: datetime

    class Config:
        from_attributes = True


class ColumnDiffItem(BaseModel):
    column_name: str
    change_type: str  # 'added', 'removed', 'type_changed', 'nullability_changed', 'renamed_likely'
    severity: str     # 'info', 'warning', 'critical'
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    impact_analysis: str
    evidence: Optional[Dict[str, Any]] = None


class SchemaDiffResponse(BaseModel):
    has_drift: bool
    severity: str
    baseline_run_id: Optional[str] = None
    current_run_id: str
    added_columns: List[str]
    removed_columns: List[str]
    type_changes: List[ColumnDiffItem]
    possible_renames: List[Dict[str, Any]]
    diff_items: List[ColumnDiffItem]
    summary: str
