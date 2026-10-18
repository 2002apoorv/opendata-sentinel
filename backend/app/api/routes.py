import os
import shutil
import uuid
from pathlib import Path
from typing import List, Optional
from datetime import datetime
import numpy as np

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.app.core.config import settings
from backend.app.core.database import get_db, Base, engine
from backend.app.models.dataset import (
    Dataset,
    IngestionRun,
    QualityCheckResult,
    AnomalyFinding,
    SchemaSnapshot,
    DriftResult,
    Alert,
)
from backend.app.schemas.dataset import (
    DatasetCreate,
    DatasetUpdate,
    DatasetResponse,
    DatasetPreviewResponse,
)
from backend.app.schemas.quality import (
    QualityReportResponse,
    QualityScoreBreakdown,
    QualityCheckResultResponse,
)
from backend.app.schemas.anomaly import (
    AnomalyFindingResponse,
    AnomalyAcknowledgeRequest,
)
from backend.app.schemas.schema_drift import (
    SchemaSnapshotResponse,
    SchemaDiffResponse,
)
from backend.app.schemas.drift import (
    DatasetDriftSummaryResponse,
    DriftMetricDetail,
)
from backend.app.schemas.run import (
    IngestionRunResponse,
    RunComparisonResponse,
)
from backend.app.schemas.dashboard import DashboardSummaryResponse

from backend.app.services.ingestion import (
    download_dataset_from_url,
    save_uploaded_file,
    copy_sample_file,
    parse_dataset_file,
    calculate_file_hash,
)
from backend.app.services.monitoring import MonitoringPipeline, compare_runs
from backend.app.services.schema_drift import compare_schemas
from backend.app.services.freshness import assess_freshness
from backend.app.services.ai_explanation import generate_diagnostic_brief

# Create tables if not present
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/api")


# =====================================================================
# Dashboard & Summary Endpoints
# =====================================================================
@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).all()
    total_datasets = len(datasets)
    
    healthy_cnt = sum(1 for d in datasets if d.status == "healthy")
    warning_cnt = sum(1 for d in datasets if d.status == "warning")
    critical_cnt = sum(1 for d in datasets if d.status == "critical")
    unavailable_cnt = sum(1 for d in datasets if d.status == "unavailable")
    
    scores = [d.latest_quality_score for d in datasets if d.latest_quality_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    total_anomalies = db.query(AnomalyFinding).count()
    pending_anomalies = db.query(AnomalyFinding).filter(AnomalyFinding.review_status == "pending").count()

    # Recent runs
    recent_runs_db = db.query(IngestionRun).order_by(desc(IngestionRun.started_at)).limit(6).all()
    recent_runs = []
    for r in recent_runs_db:
        d_name = r.dataset.name if r.dataset else "Unknown"
        recent_runs.append({
            "id": r.id,
            "dataset_id": r.dataset_id,
            "dataset_name": d_name,
            "run_type": r.run_type,
            "status": r.status,
            "quality_score": r.quality_score,
            "row_count": r.row_count,
            "started_at": r.started_at.isoformat(),
        })

    # Recent anomalies
    recent_anom_db = db.query(AnomalyFinding).order_by(desc(AnomalyFinding.created_at)).limit(6).all()
    recent_anomalies = []
    for a in recent_anom_db:
        recent_anomalies.append({
            "id": a.id,
            "dataset_id": a.dataset_id,
            "column_name": a.column_name,
            "value": a.value,
            "detection_method": a.detection_method,
            "severity": a.severity,
            "explanation": a.explanation,
            "review_status": a.review_status,
            "created_at": a.created_at.isoformat(),
        })

    # Recent alerts / schema changes
    recent_alerts_db = db.query(Alert).order_by(desc(Alert.created_at)).limit(6).all()
    recent_alerts = []
    for al in recent_alerts_db:
        recent_alerts.append({
            "id": al.id,
            "dataset_id": al.dataset_id,
            "title": al.title,
            "severity": al.severity,
            "message": al.message,
            "created_at": al.created_at.isoformat(),
        })

    # Quality score trend across recent successful runs
    trend_runs = (
        db.query(IngestionRun)
        .filter(IngestionRun.quality_score.isnot(None))
        .order_by(IngestionRun.started_at.asc())
        .limit(20)
        .all()
    )
    trends = []
    for tr in trend_runs:
        trends.append({
            "run_id": tr.id,
            "dataset_name": tr.dataset.name if tr.dataset else "Unknown",
            "quality_score": tr.quality_score,
            "timestamp": tr.started_at.strftime("%m/%d %H:%M"),
        })

    return DashboardSummaryResponse(
        total_datasets=total_datasets,
        healthy_datasets=healthy_cnt,
        warning_datasets=warning_cnt,
        critical_datasets=critical_cnt,
        unavailable_sources=unavailable_cnt,
        average_quality_score=avg_score,
        total_anomalies_detected=total_anomalies,
        pending_anomalies_count=pending_anomalies,
        recent_runs=recent_runs,
        recent_anomalies=recent_anomalies,
        recent_schema_changes=recent_alerts,
        quality_score_trends=trends,
    )


# =====================================================================
# Dataset Registry Endpoints
# =====================================================================
@router.get("/datasets", response_model=List[DatasetResponse])
def list_datasets(
    search: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Dataset)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter((Dataset.name.ilike(search_fmt)) | (Dataset.publisher.ilike(search_fmt)))
    if status_filter:
        query = query.filter(Dataset.status == status_filter.lower())

    return query.order_by(desc(Dataset.updated_at)).all()


@router.post("/datasets", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def register_dataset(payload: DatasetCreate, db: Session = Depends(get_db)):
    dataset_id = str(uuid.uuid4())
    dest_file = settings.RAW_DATA_DIR / f"{dataset_id}.{payload.data_format}"

    dataset = Dataset(
        id=dataset_id,
        name=payload.name,
        description=payload.description,
        publisher=payload.publisher,
        source_url=payload.source_url,
        source_type=payload.source_type,
        data_format=payload.data_format,
        update_cadence=payload.update_cadence,
        expected_schema=payload.expected_schema,
        custom_rules=payload.custom_rules,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    # If registered via remote URL
    if payload.source_type == "url" and payload.source_url:
        success, msg, byte_size, f_hash = await download_dataset_from_url(payload.source_url, dest_file)
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        dataset.current_file_path = str(dest_file)
        dataset.file_hash = f_hash
    elif payload.source_type == "sample" and payload.source_url:
        success, msg, byte_size, f_hash = copy_sample_file(payload.source_url, dest_file)
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        dataset.current_file_path = str(dest_file)
        dataset.file_hash = f_hash

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Trigger initial ingestion and monitoring run automatically if file is available
    if dataset.current_file_path and Path(dataset.current_file_path).exists():
        pipeline = MonitoringPipeline(db)
        pipeline.execute_monitoring_run(dataset.id, run_type="ingest")
        db.refresh(dataset)

    return dataset


@router.post("/datasets/upload", response_model=DatasetResponse)
async def upload_dataset(
    name: str = Query(...),
    publisher: str = Query(...),
    description: Optional[str] = Query(None),
    data_format: str = Query("csv"),
    update_cadence: str = Query("unknown"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    dataset_id = str(uuid.uuid4())
    fmt = "csv" if file.filename and file.filename.lower().endswith(".csv") else ("json" if file.filename and file.filename.lower().endswith(".json") else data_format)
    dest_file = settings.RAW_DATA_DIR / f"{dataset_id}.{fmt}"

    success, msg, byte_size, f_hash = save_uploaded_file(file, dest_file)
    if not success:
        raise HTTPException(status_code=400, detail=msg)

    dataset = Dataset(
        id=dataset_id,
        name=name,
        description=description or f"Uploaded file: {file.filename}",
        publisher=publisher,
        source_url=file.filename,
        source_type="upload",
        data_format=fmt,
        update_cadence=update_cadence,
        current_file_path=str(dest_file),
        file_hash=f_hash,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    # Run initial pipeline
    pipeline = MonitoringPipeline(db)
    pipeline.execute_monitoring_run(dataset.id, run_type="ingest")
    db.refresh(dataset)

    return dataset


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return dataset


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    
    # Remove file on disk if exists
    if dataset.current_file_path and Path(dataset.current_file_path).exists():
        try:
            Path(dataset.current_file_path).unlink(missing_ok=True)
        except Exception:
            pass

    db.delete(dataset)
    db.commit()
    return {"message": f"Dataset '{dataset.name}' and all associated runs successfully deleted."}


# =====================================================================
# Pipeline Trigger Endpoints
# =====================================================================
@router.post("/datasets/{dataset_id}/monitor", response_model=IngestionRunResponse)
def trigger_monitoring_run(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    pipeline = MonitoringPipeline(db)
    try:
        run = pipeline.execute_monitoring_run(dataset_id, run_type="monitor")
        return run
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monitoring run failed: {str(e)}")


@router.post("/datasets/{dataset_id}/ingest", response_model=IngestionRunResponse)
async def trigger_ingestion(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # If it's a remote URL, re-download the file
    if dataset.source_type == "url" and dataset.source_url:
        dest_file = settings.RAW_DATA_DIR / f"{dataset.id}.{dataset.data_format}"
        success, msg, byte_size, f_hash = await download_dataset_from_url(dataset.source_url, dest_file)
        if not success:
            raise HTTPException(status_code=400, detail=msg)
        dataset.current_file_path = str(dest_file)
        dataset.file_hash = f_hash
        db.commit()

    pipeline = MonitoringPipeline(db)
    run = pipeline.execute_monitoring_run(dataset_id, run_type="ingest")
    return run


# =====================================================================
# Data Preview Endpoint (Safe Paginated)
# =====================================================================
@router.get("/datasets/{dataset_id}/preview", response_model=DatasetPreviewResponse)
def get_dataset_preview(
    dataset_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset or not dataset.current_file_path:
        raise HTTPException(status_code=404, detail="Dataset or underlying file not found.")

    file_path = Path(dataset.current_file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Dataset file missing on disk.")

    df, _ = parse_dataset_file(file_path, dataset.data_format)
    
    # Optional search filtering across text columns
    if search:
        search_lower = search.strip().lower()
        mask = df.astype(str).apply(lambda row: row.str.lower().str.contains(search_lower, regex=False)).any(axis=1)
        df = df[mask]

    total_rows = len(df)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size

    sliced = df.iloc[start_idx:end_idx]
    
    # Safe JSON serialization (convert NaN to None)
    records = sliced.replace({np.nan: None}).to_dict(orient="records")
    column_types = {c: str(df[c].dtype) for c in df.columns}

    return DatasetPreviewResponse(
        dataset_id=dataset.id,
        dataset_name=dataset.name,
        total_rows=total_rows,
        total_columns=len(df.columns),
        columns=list(df.columns),
        column_types=column_types,
        page=page,
        page_size=page_size,
        data=records,
    )


# =====================================================================
# Quality & Check Results Endpoints
# =====================================================================
@router.get("/datasets/{dataset_id}/quality", response_model=QualityReportResponse)
def get_dataset_quality_report(dataset_id: str, run_id: Optional[str] = None, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    # Target specific run or latest run
    query = db.query(IngestionRun).filter(IngestionRun.dataset_id == dataset_id)
    if run_id:
        target_run = query.filter(IngestionRun.id == run_id).first()
    else:
        target_run = query.order_by(desc(IngestionRun.started_at)).first()

    if not target_run:
        raise HTTPException(status_code=404, detail="No monitoring runs found for this dataset. Please run checks first.")

    checks = db.query(QualityCheckResult).filter(QualityCheckResult.run_id == target_run.id).all()
    
    score_breakdown = target_run.metrics_snapshot.get("score_breakdown", {}) if target_run.metrics_snapshot else {}
    
    return QualityReportResponse(
        dataset_id=dataset.id,
        run_id=target_run.id,
        evaluated_at=target_run.completed_at or target_run.started_at,
        overall_score=target_run.quality_score or 0.0,
        breakdown=score_breakdown,
        checks=checks,
    )


# =====================================================================
# Anomaly Detection & Acknowledge Endpoints
# =====================================================================
@router.get("/datasets/{dataset_id}/anomalies", response_model=List[AnomalyFindingResponse])
def get_dataset_anomalies(
    dataset_id: str,
    method: Optional[str] = None,
    severity: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(AnomalyFinding).filter(AnomalyFinding.dataset_id == dataset_id)
    if method:
        query = query.filter(AnomalyFinding.detection_method == method.lower())
    if severity:
        query = query.filter(AnomalyFinding.severity == severity.lower())
    if status_filter:
        query = query.filter(AnomalyFinding.review_status == status_filter.lower())

    return query.order_by(desc(AnomalyFinding.created_at)).all()


@router.post("/datasets/{dataset_id}/anomalies/{anomaly_id}/acknowledge")
def acknowledge_anomaly(
    dataset_id: str,
    anomaly_id: str,
    payload: AnomalyAcknowledgeRequest,
    db: Session = Depends(get_db),
):
    finding = (
        db.query(AnomalyFinding)
        .filter(AnomalyFinding.id == anomaly_id, AnomalyFinding.dataset_id == dataset_id)
        .first()
    )
    if not finding:
        raise HTTPException(status_code=404, detail="Anomaly finding not found.")

    finding.review_status = "false_positive" if payload.is_false_positive else "acknowledged"
    finding.acknowledged_notes = payload.notes
    finding.acknowledged_at = datetime.utcnow()
    db.commit()

    return {
        "id": finding.id,
        "status": finding.review_status,
        "notes": finding.acknowledged_notes,
        "message": "Anomaly finding review status updated without altering underlying dataset.",
    }


# =====================================================================
# Schema Drift Endpoints
# =====================================================================
@router.get("/datasets/{dataset_id}/schema", response_model=SchemaSnapshotResponse)
def get_latest_schema(dataset_id: str, db: Session = Depends(get_db)):
    snapshot = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.dataset_id == dataset_id)
        .order_by(desc(SchemaSnapshot.created_at))
        .first()
    )
    if not snapshot:
        raise HTTPException(status_code=404, detail="No schema snapshot available.")
    return snapshot


@router.get("/datasets/{dataset_id}/schema/diff", response_model=SchemaDiffResponse)
def get_schema_diff(dataset_id: str, db: Session = Depends(get_db)):
    snapshots = (
        db.query(SchemaSnapshot)
        .filter(SchemaSnapshot.dataset_id == dataset_id)
        .order_by(desc(SchemaSnapshot.created_at))
        .limit(2)
        .all()
    )
    if not snapshots:
        raise HTTPException(status_code=404, detail="No schema snapshots available.")

    curr = snapshots[0]
    base = snapshots[1] if len(snapshots) > 1 else None

    diff = compare_schemas(curr.columns_schema, base.columns_schema if base else None)
    return SchemaDiffResponse(
        has_drift=diff["has_drift"],
        severity=diff["severity"],
        baseline_run_id=base.run_id if base else None,
        current_run_id=curr.run_id,
        added_columns=diff["added_columns"],
        removed_columns=diff["removed_columns"],
        type_changes=diff["type_changes"],
        possible_renames=diff["possible_renames"],
        diff_items=diff["diff_items"],
        summary=diff["summary"],
    )


# =====================================================================
# Distribution Drift Endpoints
# =====================================================================
@router.get("/datasets/{dataset_id}/drift", response_model=DatasetDriftSummaryResponse)
def get_dataset_drift(dataset_id: str, db: Session = Depends(get_db)):
    runs = (
        db.query(IngestionRun)
        .filter(IngestionRun.dataset_id == dataset_id, IngestionRun.status == "success")
        .order_by(desc(IngestionRun.started_at))
        .limit(2)
        .all()
    )
    
    if len(runs) < 2:
        return DatasetDriftSummaryResponse(
            dataset_id=dataset_id,
            drift_available=False,
            columns_analyzed=0,
            drifted_columns_count=0,
            has_significant_drift=False,
            summary="Distribution drift detection requires at least two completed monitoring runs to compare baseline with current data.",
            metrics=[],
        )

    curr_run = runs[0]
    base_run = runs[1]

    drift_records = db.query(DriftResult).filter(DriftResult.run_id == curr_run.id).all()
    metrics = []
    for d in drift_records:
        metrics.append(DriftMetricDetail(
            column_name=d.column_name,
            metric_type=d.metric_type,
            metric_value=d.metric_value,
            p_value=d.p_value,
            drift_detected=d.drift_detected,
            interpretation=d.details.get("interpretation", "Drift test executed.") if d.details else "",
            details=d.details,
        ))

    drifted_count = sum(1 for m in metrics if m.drift_detected)

    return DatasetDriftSummaryResponse(
        dataset_id=dataset_id,
        baseline_run_id=base_run.id,
        current_run_id=curr_run.id,
        baseline_date=base_run.started_at,
        current_date=curr_run.started_at,
        drift_available=True,
        columns_analyzed=len(metrics),
        drifted_columns_count=drifted_count,
        has_significant_drift=drifted_count > 0,
        summary=(
            f"Compared current run ({curr_run.started_at.strftime('%Y-%m-%d')}) with baseline ({base_run.started_at.strftime('%Y-%m-%d')}). "
            f"Detected distribution shift in {drifted_count} column(s)."
            if drifted_count > 0
            else f"Compared {len(metrics)} column(s) against historical baseline. All distributions remain stable."
        ),
        metrics=metrics,
    )


# =====================================================================
# Run History & Run Comparison Endpoints
# =====================================================================
@router.get("/datasets/{dataset_id}/runs", response_model=List[IngestionRunResponse])
def get_dataset_runs(dataset_id: str, db: Session = Depends(get_db)):
    return (
        db.query(IngestionRun)
        .filter(IngestionRun.dataset_id == dataset_id)
        .order_by(desc(IngestionRun.started_at))
        .all()
    )


@router.get("/datasets/{dataset_id}/runs/{run_id}/compare", response_model=RunComparisonResponse)
def compare_run_with_previous(dataset_id: str, run_id: str, db: Session = Depends(get_db)):
    curr_run = db.query(IngestionRun).filter(IngestionRun.id == run_id, IngestionRun.dataset_id == dataset_id).first()
    if not curr_run:
        raise HTTPException(status_code=404, detail="Run not found.")

    # Find the previous run before this one
    prev_run = (
        db.query(IngestionRun)
        .filter(IngestionRun.dataset_id == dataset_id, IngestionRun.started_at < curr_run.started_at)
        .order_by(desc(IngestionRun.started_at))
        .first()
    )

    diff = compare_runs(curr_run, prev_run, db)
    return RunComparisonResponse(**diff)


# =====================================================================
# AI Diagnostic Briefing Endpoint
# =====================================================================
@router.post("/datasets/{dataset_id}/explain")
def get_ai_diagnostic_explanation(dataset_id: str, db: Session = Depends(get_db)):
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found.")

    latest_run = (
        db.query(IngestionRun)
        .filter(IngestionRun.dataset_id == dataset_id)
        .order_by(desc(IngestionRun.started_at))
        .first()
    )
    if not latest_run:
        raise HTTPException(status_code=404, detail="No monitoring run available to explain.")

    checks = [
        {
            "check_id": c.check_id,
            "check_name": c.check_name,
            "category": c.category,
            "status": c.status,
            "severity": c.severity,
            "affected_rows": c.affected_rows,
            "affected_columns": c.affected_columns,
            "explanation": c.explanation,
            "suggested_action": c.suggested_action,
        }
        for c in latest_run.quality_checks
    ]

    anomalies = [
        {
            "column_name": a.column_name,
            "value": a.value,
            "detection_method": a.detection_method,
            "severity": a.severity,
            "score": a.score,
            "explanation": a.explanation,
        }
        for a in latest_run.anomalies
    ]

    schema_diff = latest_run.metrics_snapshot.get("schema_diff", {}) if latest_run.metrics_snapshot else {}
    drift_summary = latest_run.metrics_snapshot.get("drift_summary", {}) if latest_run.metrics_snapshot else {}

    brief = generate_diagnostic_brief(
        dataset_name=dataset.name,
        overall_score=latest_run.quality_score or 0.0,
        check_results=checks,
        anomaly_findings=anomalies,
        schema_diff=schema_diff,
        drift_summary=drift_summary,
    )

    return brief


# =====================================================================
# Demonstration Samples & Benchmarks Endpoints
# =====================================================================
@router.get("/samples")
def list_available_samples():
    """Returns curated Indian Government open data demonstration datasets."""
    samples = [
        {
            "id": "agri_mandi_prices_clean",
            "name": "Indian Agricultural Mandi Commodity Prices (Clean Baseline)",
            "publisher": "Ministry of Agriculture & Farmers Welfare, DMI (data.gov.in)",
            "filename": "indian_agri_mandi_prices_clean.csv",
            "format": "csv",
            "update_cadence": "daily",
            "description": "Daily arrivals and modal prices of Wheat, Mustard, Paddy, Onion, Tomato across Indian APMC mandis.",
            "expected_schema": {
                "min_price_inr_qtl": "numeric",
                "max_price_inr_qtl": "numeric",
                "modal_price_inr_qtl": "numeric",
                "arrival_date": "datetime",
            },
            "custom_rules": {
                "primary_key": "record_id",
                "cross_field_rules": [
                    {"field_a": "min_price_inr_qtl", "field_b": "max_price_inr_qtl", "operator": "<=", "name": "Min Price <= Max Price"}
                ]
            }
        },
        {
            "id": "agri_mandi_prices_drifted",
            "name": "Indian Agricultural Mandi Prices (Drifted & Corrupted Edition)",
            "publisher": "Ministry of Agriculture & Farmers Welfare, DMI (data.gov.in)",
            "filename": "indian_agri_mandi_prices_drifted.csv",
            "format": "csv",
            "update_cadence": "daily",
            "description": "Simulated live update with intentional schema changes, inverted prices, duplicates, and seasonal price spikes for drift evaluation.",
        },
        {
            "id": "cpcb_air_quality",
            "name": "National Ambient Air Quality Index (CPCB)",
            "publisher": "Central Pollution Control Board, MoEFCC (data.gov.in)",
            "filename": "indian_aqi_air_quality_clean.csv",
            "format": "csv",
            "update_cadence": "daily",
            "description": "Continuous ambient air quality monitoring (PM2.5, PM10, NO2, SO2, CO, Ozone, AQI) across Delhi, Mumbai, Bengaluru, Kolkata.",
        },
        {
            "id": "bee_ev_charging_infrastructure",
            "name": "National Public EV Charging Station Infrastructure",
            "publisher": "Bureau of Energy Efficiency (BEE), Ministry of Power (data.gov.in)",
            "filename": "indian_ev_charging_infrastructure.json",
            "format": "json",
            "update_cadence": "monthly",
            "description": "Public EV charging locations, connector types, power capacity in kW, and tariffs across Indian metropolitan cities.",
        },
        {
            "id": "nhm_health_infrastructure",
            "name": "National Health Mission Hospital & Facility Metrics",
            "publisher": "Ministry of Health and Family Welfare (MoHFW) (data.gov.in)",
            "filename": "indian_health_infrastructure.csv",
            "format": "csv",
            "update_cadence": "monthly",
            "description": "District hospital and primary health centre capacity, total bed count, ICU beds, doctors on duty, and OPD attendance.",
            "custom_rules": {
                "cross_field_rules": [
                    {"field_a": "icu_beds", "field_b": "total_beds", "operator": "<=", "name": "ICU Beds <= Total Beds"}
                ]
            }
        },
    ]
    return samples


@router.post("/samples/load-all")
def load_all_sample_datasets(db: Session = Depends(get_db)):
    """Registers and executes monitoring cycles on all bundled Indian Government datasets."""
    samples = list_available_samples()
    created = []

    for s in samples:
        # Check if already registered
        existing = db.query(Dataset).filter(Dataset.name == s["name"]).first()
        if existing:
            created.append(existing.name)
            continue

        dataset_id = str(uuid.uuid4())
        dest_file = settings.RAW_DATA_DIR / f"{dataset_id}.{s['format']}"
        success, msg, byte_size, f_hash = copy_sample_file(s["filename"], dest_file)
        if not success:
            continue

        dataset = Dataset(
            id=dataset_id,
            name=s["name"],
            description=s["description"],
            publisher=s["publisher"],
            source_url=s["filename"],
            source_type="sample",
            data_format=s["format"],
            update_cadence=s["update_cadence"],
            expected_schema=s.get("expected_schema"),
            custom_rules=s.get("custom_rules"),
            current_file_path=str(dest_file),
            file_hash=f_hash,
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)

        # Run pipeline
        pipeline = MonitoringPipeline(db)
        pipeline.execute_monitoring_run(dataset.id, run_type="ingest")
        created.append(dataset.name)

    return {"message": f"Successfully registered and monitored {len(created)} dataset(s).", "datasets": created}


@router.get("/evaluation/benchmarks")
def get_evaluation_benchmarks():
    """Returns measured machine learning and data quality evaluation benchmark metrics."""
    bench_file = Path(__file__).resolve().parent.parent.parent.parent / "evaluation" / "benchmark_results.json"
    if bench_file.exists():
        import json
        with open(bench_file, "r") as f:
            return json.load(f)
    return {
        "status": "pending_execution",
        "message": "Benchmarks script has not been executed yet.",
    }
