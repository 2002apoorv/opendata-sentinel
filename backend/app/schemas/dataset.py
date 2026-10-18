from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


class DatasetBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    publisher: str = Field(..., min_length=2, max_length=255)
    source_url: Optional[str] = None
    source_type: str = Field("upload", pattern="^(url|upload|sample)$")
    data_format: str = Field("csv", pattern="^(csv|json)$")
    update_cadence: str = Field("unknown", pattern="^(daily|weekly|monthly|quarterly|unknown)$")
    expected_schema: Optional[Dict[str, Any]] = None
    custom_rules: Optional[Dict[str, Any]] = None


class DatasetCreate(DatasetBase):
    pass


class DatasetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    publisher: Optional[str] = None
    update_cadence: Optional[str] = None
    expected_schema: Optional[Dict[str, Any]] = None
    custom_rules: Optional[Dict[str, Any]] = None


class DatasetResponse(DatasetBase):
    id: str
    status: str
    latest_quality_score: Optional[float] = None
    row_count: int
    column_count: int
    file_hash: Optional[str] = None
    last_ingested_at: Optional[datetime] = None
    last_successful_ingestion_at: Optional[datetime] = None
    last_content_change_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DatasetPreviewResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    total_rows: int
    total_columns: int
    columns: List[str]
    column_types: Dict[str, str]
    page: int
    page_size: int
    data: List[Dict[str, Any]]
