import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    publisher = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=True)
    source_type = Column(String(32), default="upload")  # 'url', 'upload', 'sample'
    data_format = Column(String(16), default="csv")     # 'csv', 'json'
    update_cadence = Column(String(32), default="unknown")  # 'daily', 'weekly', 'monthly', 'quarterly', 'unknown'
    status = Column(String(32), default="healthy")      # 'healthy', 'warning', 'critical', 'unavailable', 'pending'
    
    expected_schema = Column(JSON, nullable=True)
    custom_rules = Column(JSON, nullable=True)
    
    latest_quality_score = Column(Float, nullable=True)
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    file_hash = Column(String(128), nullable=True)
    current_file_path = Column(Text, nullable=True)
    
    last_ingested_at = Column(DateTime, nullable=True)
    last_successful_ingestion_at = Column(DateTime, nullable=True)
    last_content_change_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    runs = relationship("IngestionRun", back_populates="dataset", cascade="all, delete-orphan", order_by="desc(IngestionRun.started_at)")
    anomalies = relationship("AnomalyFinding", back_populates="dataset", cascade="all, delete-orphan")
    schema_snapshots = relationship("SchemaSnapshot", back_populates="dataset", cascade="all, delete-orphan", order_by="desc(SchemaSnapshot.created_at)")
    alerts = relationship("Alert", back_populates="dataset", cascade="all, delete-orphan", order_by="desc(Alert.created_at)")


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    run_type = Column(String(32), default="monitor")  # 'ingest', 'validate', 'monitor'
    status = Column(String(32), default="success")     # 'success', 'warning', 'failed'
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    quality_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    file_path = Column(Text, nullable=True)
    file_hash = Column(String(128), nullable=True)
    metrics_snapshot = Column(JSON, nullable=True)

    # Relationships
    dataset = relationship("Dataset", back_populates="runs")
    quality_checks = relationship("QualityCheckResult", back_populates="run", cascade="all, delete-orphan")
    anomalies = relationship("AnomalyFinding", back_populates="run", cascade="all, delete-orphan")
    schema_snapshot = relationship("SchemaSnapshot", back_populates="run", uselist=False, cascade="all, delete-orphan")
    drift_results = relationship("DriftResult", back_populates="run", cascade="all, delete-orphan")


class QualityCheckResult(Base):
    __tablename__ = "quality_check_results"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(64), ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    check_id = Column(String(64), nullable=False)
    check_name = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False)  # 'completeness', 'uniqueness', 'validity', 'schema', 'consistency', 'structure'
    status = Column(String(32), nullable=False)    # 'passed', 'warning', 'failed', 'not_applicable'
    severity = Column(String(32), nullable=False)  # 'info', 'low', 'medium', 'high', 'critical'
    
    affected_rows = Column(Integer, default=0)
    affected_columns = Column(JSON, nullable=True)
    explanation = Column(Text, nullable=False)
    evidence = Column(JSON, nullable=True)
    suggested_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("IngestionRun", back_populates="quality_checks")


class AnomalyFinding(Base):
    __tablename__ = "anomaly_findings"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(64), ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    column_name = Column(String(128), nullable=False)
    row_index = Column(Integer, nullable=False)
    row_identifier = Column(String(255), nullable=True)
    value = Column(String(255), nullable=False)
    detection_method = Column(String(64), nullable=False)  # 'iqr', 'zscore', 'mad', 'isolation_forest'
    threshold_rule = Column(String(255), nullable=False)
    severity = Column(String(32), default="medium")        # 'low', 'medium', 'high', 'critical'
    score = Column(Float, nullable=True)
    explanation = Column(Text, nullable=False)
    
    review_status = Column(String(32), default="pending")  # 'pending', 'acknowledged', 'false_positive'
    acknowledged_notes = Column(Text, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dataset = relationship("Dataset", back_populates="anomalies")
    run = relationship("IngestionRun", back_populates="anomalies")


class SchemaSnapshot(Base):
    __tablename__ = "schema_snapshots"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(64), ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    columns_schema = Column(JSON, nullable=False)  # list of {name, type, nullable, unique_ratio, sample_values}
    row_count = Column(Integer, default=0)
    column_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dataset = relationship("Dataset", back_populates="schema_snapshots")
    run = relationship("IngestionRun", back_populates="schema_snapshot")


class DriftResult(Base):
    __tablename__ = "drift_results"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(64), ForeignKey("ingestion_runs.id", ondelete="CASCADE"), nullable=False)
    dataset_id = Column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    
    column_name = Column(String(128), nullable=False)
    metric_type = Column(String(64), nullable=False)  # 'psi', 'ks_test', 'mean_shift', 'variance_shift', 'category_shift'
    metric_value = Column(Float, nullable=False)
    p_value = Column(Float, nullable=True)
    drift_detected = Column(Boolean, default=False)
    baseline_run_id = Column(String(64), nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    run = relationship("IngestionRun", back_populates="drift_results")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_id = Column(String(64), ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False)
    run_id = Column(String(64), nullable=True)
    
    severity = Column(String(32), default="warning")  # 'info', 'warning', 'critical'
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    dataset = relationship("Dataset", back_populates="alerts")
