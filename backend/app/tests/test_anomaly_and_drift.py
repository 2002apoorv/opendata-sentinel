import pytest
import numpy as np
import pandas as pd
from backend.app.services.anomaly_detection import AnomalyDetector
from backend.app.services.drift_detection import calculate_psi, DistributionDriftDetector
from backend.app.services.schema_drift import compare_schemas


def test_anomaly_detection_iqr_and_mad():
    np.random.seed(42)
    # 100 normal values with 2 clear outliers
    normal = np.random.normal(loc=100, scale=10, size=100)
    normal[10] = 950.0  # Outlier 1
    normal[55] = 1200.0 # Outlier 2

    df = pd.DataFrame({"record_id": [f"REC-{i}" for i in range(100)], "price": normal})
    detector = AnomalyDetector(df)
    findings = detector.detect_anomalies(methods=["iqr", "mad"])

    flagged_indices = set(f["row_index"] for f in findings if f["column_name"] == "price")
    assert 10 in flagged_indices
    assert 55 in flagged_indices


def test_anomaly_detection_guardrails_constant_col():
    # Constant-valued column must not produce div-by-zero or crash
    df = pd.DataFrame({"station_id": [f"STN-{i}" for i in range(50)], "val": [42.0] * 50})
    detector = AnomalyDetector(df)
    findings = detector.detect_anomalies(methods=["iqr", "mad", "zscore", "isolation_forest"])
    val_findings = [f for f in findings if f["column_name"] == "val"]
    assert len(val_findings) == 0


def test_distribution_drift_psi():
    np.random.seed(42)
    baseline = np.random.normal(loc=100, scale=15, size=500)
    
    # 1. Identical distribution -> PSI should be < 0.10
    same = np.random.normal(loc=100, scale=15, size=500)
    psi_low, _ = calculate_psi(baseline, same)
    assert psi_low < 0.10

    # 2. Significantly shifted distribution -> PSI should exceed 0.25
    shifted = np.random.normal(loc=160, scale=30, size=500)
    psi_high, _ = calculate_psi(baseline, shifted)
    assert psi_high >= 0.25


def test_schema_drift_detection():
    current_schema = [
        {"name": "id", "inferred_type": "integer", "nullable": False, "null_percentage": 0.0},
        {"name": "new_col", "inferred_type": "string", "nullable": True, "null_percentage": 5.0},
    ]
    baseline_schema = [
        {"name": "id", "inferred_type": "integer", "nullable": False, "null_percentage": 0.0},
        {"name": "old_col", "inferred_type": "float", "nullable": False, "null_percentage": 0.0},
    ]

    diff = compare_schemas(current_schema, baseline_schema)
    assert diff["has_drift"] is True
    assert "new_col" in diff["added_columns"]
    assert "old_col" in diff["removed_columns"]
