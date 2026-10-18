import pytest
import pandas as pd
import numpy as np
from backend.app.services.validation import DataQualityValidator
from backend.app.services.quality_scoring import calculate_quality_score


def test_validation_completeness():
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "name": ["A", None, "C", None],
        "val": [10, 20, 30, 40],
    })
    validator = DataQualityValidator(df)
    results = validator.run_all_checks("test-id", "test-run")

    comp_chk = next((c for c in results if c["check_id"] == "COMP-002"), None)
    assert comp_chk is not None
    assert comp_chk["affected_rows"] == 2
    assert "name" in comp_chk["affected_columns"]


def test_validation_duplicates():
    df = pd.DataFrame({
        "id": [101, 102, 101, 103],
        "city": ["Delhi", "Mumbai", "Delhi", "Pune"],
    })
    validator = DataQualityValidator(df, custom_rules={"primary_key": "id"})
    results = validator.run_all_checks("test-id", "test-run")

    id_chk = next((c for c in results if "DUP-ID" in c["check_id"]), None)
    assert id_chk is not None
    assert id_chk["status"] == "failed"
    assert id_chk["affected_rows"] == 1


def test_validation_cross_field_bounds():
    df = pd.DataFrame({
        "min_price_inr_qtl": [1500, 2500, 3000],
        "max_price_inr_qtl": [2000, 2200, 3500], # Row 1: 2500 > 2200 (violator!)
    })
    validator = DataQualityValidator(df)
    results = validator.run_all_checks("test-id", "test-run")

    cross_chk = next((c for c in results if c["check_id"] == "CROSS-001"), None)
    assert cross_chk is not None
    assert cross_chk["status"] == "failed"
    assert cross_chk["affected_rows"] == 1


def test_validation_non_negative_constraint():
    df = pd.DataFrame({
        "facility_id": [1, 2, 3],
        "icu_beds": [10, -5, 20],
        "total_beds": [50, 40, 80],
    })
    validator = DataQualityValidator(df)
    results = validator.run_all_checks("test-id", "test-run")

    neg_chk = next((c for c in results if c["check_id"] == "VAL-001"), None)
    assert neg_chk is not None
    assert neg_chk["status"] == "failed"
    assert "icu_beds" in neg_chk["affected_columns"]


def test_quality_score_calculation():
    check_results = [
        {"category": "completeness", "status": "passed", "severity": "info"},
        {"category": "uniqueness", "status": "passed", "severity": "info"},
        {"category": "validity", "status": "passed", "severity": "info"},
        {"category": "consistency", "status": "passed", "severity": "info"},
    ]
    score_res = calculate_quality_score(check_results, freshness_score=100.0)
    assert score_res["overall_score"] >= 95.0
    assert score_res["is_passing"] is True
    assert score_res["critical_failures_count"] == 0
