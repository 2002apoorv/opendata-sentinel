import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import pandas as pd
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.dataset import (
    Dataset,
    IngestionRun,
    QualityCheckResult,
    AnomalyFinding,
    SchemaSnapshot,
    DriftResult,
    Alert,
)
from backend.app.services.ingestion import (
    parse_dataset_file,
    calculate_file_hash,
)
from backend.app.services.validation import DataQualityValidator
from backend.app.services.schema_drift import extract_schema_snapshot, compare_schemas
from backend.app.services.anomaly_detection import AnomalyDetector
from backend.app.services.drift_detection import DistributionDriftDetector
from backend.app.services.freshness import assess_freshness
from backend.app.services.quality_scoring import calculate_quality_score


class MonitoringPipeline:
    """
    OpenData Sentinel Monitoring Pipeline Orchestrator.
    Executes an end-to-end audit cycle: ingestion -> validation -> schema drift ->
    anomaly detection -> distribution drift -> scoring -> persistence.
    """

    def __init__(self, db: Session):
        self.db = db

    def execute_monitoring_run(
        self,
        dataset_id: str,
        file_path_override: Optional[Path] = None,
        run_type: str = "monitor",
    ) -> IngestionRun:
        dataset = self.db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise ValueError(f"Dataset with ID '{dataset_id}' not found.")

        target_file = file_path_override or (Path(dataset.current_file_path) if dataset.current_file_path else None)
        if not target_file or not target_file.exists():
            raise FileNotFoundError(f"Dataset data file not found at: {target_file}")

        run_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # Update dataset last attempted ingestion
        dataset.last_ingested_at = started_at

        # 1. Parse Data File
        try:
            df, parse_meta = parse_dataset_file(target_file, dataset.data_format)
            file_hash = calculate_file_hash(target_file)
            content_changed = dataset.file_hash != file_hash
            if content_changed or dataset.last_content_change_at is None:
                dataset.last_content_change_at = started_at
            dataset.file_hash = file_hash
        except Exception as e:
            # Record failed run
            failed_run = IngestionRun(
                id=run_id,
                dataset_id=dataset.id,
                run_type=run_type,
                status="failed",
                started_at=started_at,
                completed_at=datetime.utcnow(),
                error_message=f"Ingestion parsing failure: {str(e)}",
                summary="Failed to parse dataset file.",
            )
            dataset.status = "critical"
            self.db.add(failed_run)
            self.db.commit()
            return failed_run

        # 2. Extract Schema Snapshot & Compare Schema Drift
        curr_schema_list = extract_schema_snapshot(df)
        previous_snapshot_record = (
            self.db.query(SchemaSnapshot)
            .filter(SchemaSnapshot.dataset_id == dataset.id)
            .order_by(SchemaSnapshot.created_at.desc())
            .first()
        )
        base_schema_list = previous_snapshot_record.columns_schema if previous_snapshot_record else None
        schema_diff = compare_schemas(curr_schema_list, base_schema_list, dataset.expected_schema)

        # 3. Execute Quality Checks
        validator = DataQualityValidator(
            df=df,
            expected_schema=dataset.expected_schema,
            custom_rules=dataset.custom_rules,
        )
        check_dicts = validator.run_all_checks(dataset.id, run_id)

        # 4. Statistical Anomaly Detection
        detector = AnomalyDetector(df)
        anomaly_dicts = detector.detect_anomalies()

        # 5. Distribution Drift (if previous baseline data is available)
        baseline_df = None
        previous_successful_run = (
            self.db.query(IngestionRun)
            .filter(IngestionRun.dataset_id == dataset.id, IngestionRun.status == "success")
            .order_by(IngestionRun.started_at.desc())
            .first()
        )

        if previous_successful_run and previous_successful_run.file_path and Path(previous_successful_run.file_path).exists():
            try:
                baseline_df, _ = parse_dataset_file(Path(previous_successful_run.file_path), dataset.data_format)
            except Exception:
                baseline_df = None

        drift_detector = DistributionDriftDetector(df, baseline_df)
        drift_res = drift_detector.detect_drift()

        # 6. Freshness Assessment
        freshness_info = assess_freshness(
            update_cadence=dataset.update_cadence,
            last_successful_ingestion=dataset.last_successful_ingestion_at,
            last_content_change=dataset.last_content_change_at,
            last_attempted_ingestion=started_at,
            last_ingestion_status="success",
        )

        # 7. Quality Scoring
        score_info = calculate_quality_score(
            check_results=check_dicts,
            freshness_score=freshness_info["freshness_score"],
        )

        # 8. Create IngestionRun Record
        completed_at = datetime.utcnow()
        run_status = "success" if score_info["critical_failures_count"] == 0 else "warning"

        ingestion_run = IngestionRun(
            id=run_id,
            dataset_id=dataset.id,
            run_type=run_type,
            status=run_status,
            started_at=started_at,
            completed_at=completed_at,
            row_count=len(df),
            column_count=len(df.columns),
            quality_score=score_info["overall_score"],
            summary=score_info["summary_text"],
            file_path=str(target_file),
            file_hash=file_hash,
            metrics_snapshot={
                "score_breakdown": score_info,
                "freshness": freshness_info,
                "schema_diff": schema_diff,
                "drift_summary": {
                    "drift_available": drift_res["drift_available"],
                    "summary": drift_res["summary"],
                    "drifted_columns_count": drift_res["drifted_columns_count"],
                },
            },
        )
        self.db.add(ingestion_run)

        # 9. Persist Quality Check Results
        for c in check_dicts:
            chk_obj = QualityCheckResult(
                id=str(uuid.uuid4()),
                run_id=run_id,
                dataset_id=dataset.id,
                check_id=c["check_id"],
                check_name=c["check_name"],
                category=c["category"],
                status=c["status"],
                severity=c["severity"],
                affected_rows=c["affected_rows"],
                affected_columns=c["affected_columns"],
                explanation=c["explanation"],
                evidence=c["evidence"],
                suggested_action=c["suggested_action"],
                created_at=c["created_at"],
            )
            self.db.add(chk_obj)

        # 10. Persist Anomaly Findings
        for a in anomaly_dicts:
            anom_obj = AnomalyFinding(
                id=str(uuid.uuid4()),
                run_id=run_id,
                dataset_id=dataset.id,
                column_name=a["column_name"],
                row_index=a["row_index"],
                row_identifier=a["row_identifier"],
                value=str(a["value"]),
                detection_method=a["detection_method"],
                threshold_rule=a["threshold_rule"],
                severity=a["severity"],
                score=a["score"],
                explanation=a["explanation"],
                review_status="pending",
                created_at=datetime.utcnow(),
            )
            self.db.add(anom_obj)

        # 11. Persist Schema Snapshot
        snapshot_obj = SchemaSnapshot(
            id=str(uuid.uuid4()),
            run_id=run_id,
            dataset_id=dataset.id,
            columns_schema=curr_schema_list,
            row_count=len(df),
            column_count=len(df.columns),
            created_at=datetime.utcnow(),
        )
        self.db.add(snapshot_obj)

        # 12. Persist Drift Results
        for m in drift_res.get("metrics", []):
            drift_obj = DriftResult(
                id=str(uuid.uuid4()),
                run_id=run_id,
                dataset_id=dataset.id,
                column_name=m["column_name"],
                metric_type=m["metric_type"],
                metric_value=m["metric_value"],
                p_value=m.get("p_value"),
                drift_detected=m["drift_detected"],
                baseline_run_id=previous_successful_run.id if previous_successful_run else None,
                details=m["details"],
                created_at=datetime.utcnow(),
            )
            self.db.add(drift_obj)

        # 13. In-App Alerts for Critical Events
        if score_info["critical_failures_count"] > 0:
            alert = Alert(
                id=str(uuid.uuid4()),
                dataset_id=dataset.id,
                run_id=run_id,
                severity="critical",
                title=f"Critical Integrity Failures on {dataset.name}",
                message=f"Run detected {score_info['critical_failures_count']} critical failure(s). Quality score: {score_info['overall_score']:.1f}/100.",
            )
            self.db.add(alert)

        if schema_diff["has_drift"] and schema_diff["severity"] in ["warning", "critical"]:
            alert = Alert(
                id=str(uuid.uuid4()),
                dataset_id=dataset.id,
                run_id=run_id,
                severity=schema_diff["severity"],
                title=f"Schema Drift Detected: {dataset.name}",
                message=schema_diff["summary"],
            )
            self.db.add(alert)

        # 14. Update Dataset Master Record
        dataset.latest_quality_score = score_info["overall_score"]
        dataset.row_count = len(df)
        dataset.column_count = len(df.columns)
        dataset.last_successful_ingestion_at = completed_at
        dataset.status = "healthy" if score_info["overall_score"] >= 80.0 and score_info["critical_failures_count"] == 0 else ("warning" if score_info["overall_score"] >= 60.0 else "critical")
        dataset.current_file_path = str(target_file)

        self.db.commit()
        self.db.refresh(ingestion_run)
        return ingestion_run


def compare_runs(current_run: IngestionRun, previous_run: Optional[IngestionRun], db: Session) -> Dict[str, Any]:
    """Compares two monitoring runs to detect new issues, resolved issues, and score deltas."""
    if not previous_run:
        return {
            "dataset_id": current_run.dataset_id,
            "current_run_id": current_run.id,
            "previous_run_id": None,
            "has_comparison": False,
            "quality_score_change": 0.0,
            "row_count_change": 0,
            "new_failures": [],
            "resolved_failures": [],
            "new_anomalies_count": len(current_run.anomalies),
            "schema_changed": False,
            "summary": "First recorded monitoring run. No prior run available for diff comparison.",
        }

    score_change = round((current_run.quality_score or 0.0) - (previous_run.quality_score or 0.0), 2)
    row_change = (current_run.row_count or 0) - (previous_run.row_count or 0)

    curr_checks = {c.check_id: c for c in current_run.quality_checks}
    prev_checks = {c.check_id: c for c in previous_run.quality_checks}

    new_failures = []
    resolved_failures = []

    for cid, c in curr_checks.items():
        if c.status == "failed":
            if cid not in prev_checks or prev_checks[cid].status != "failed":
                new_failures.append({
                    "check_id": c.check_id,
                    "check_name": c.check_name,
                    "severity": c.severity,
                    "explanation": c.explanation,
                })

    for pid, p in prev_checks.items():
        if p.status == "failed":
            if pid not in curr_checks or curr_checks[pid].status != "failed":
                resolved_failures.append({
                    "check_id": p.check_id,
                    "check_name": p.check_name,
                    "explanation": p.explanation,
                })

    schema_changed = current_run.file_hash != previous_run.file_hash

    summary = (
        f"Score shifted by {score_change:+.1f} pts. "
        f"Found {len(new_failures)} new failure(s) and resolved {len(resolved_failures)} prior failure(s)."
    )

    return {
        "dataset_id": current_run.dataset_id,
        "current_run_id": current_run.id,
        "previous_run_id": previous_run.id,
        "has_comparison": True,
        "quality_score_change": score_change,
        "row_count_change": row_change,
        "new_failures": new_failures,
        "resolved_failures": resolved_failures,
        "new_anomalies_count": len(current_run.anomalies),
        "schema_changed": schema_changed,
        "summary": summary,
    }
