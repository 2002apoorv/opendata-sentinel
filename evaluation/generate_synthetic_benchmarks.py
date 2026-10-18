"""
OpenData Sentinel - Synthetic Benchmark Dataset Generator with Known Ground Truth
Generates reproducible baseline and corrupted datasets with recorded ground-truth
annotations for rigorous evaluation of validation, anomaly detection, and drift detection.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

EVAL_DIR = Path(__file__).resolve().parent
EVAL_DIR.mkdir(parents=True, exist_ok=True)


def generate_benchmark_datasets():
    np.random.seed(42)
    n_samples = 1000

    # Clean Baseline Dataset (Simulating Commodity Mandi Arrivals)
    record_ids = [f"BENCH-REC-{i:05d}" for i in range(1, n_samples + 1)]
    states = ["Punjab", "Haryana", "Uttar Pradesh", "Maharashtra", "Karnataka", "Rajasthan"]
    state_col = np.random.choice(states, size=n_samples)
    commodities = ["Wheat", "Mustard", "Paddy", "Chana"]
    comm_col = np.random.choice(commodities, size=n_samples)
    
    # Normal distribution around base price
    base_modal = np.random.normal(loc=2500, scale=300, size=n_samples)
    base_modal = np.clip(base_modal, 1200, 4000)
    
    spread = np.random.uniform(50, 150, size=n_samples)
    min_price = np.round(base_modal - spread, 2)
    max_price = np.round(base_modal + spread, 2)
    modal_price = np.round(base_modal, 2)
    volume_tonnes = np.round(np.random.exponential(scale=50, size=n_samples) + 5, 2)

    start_date = datetime(2026, 8, 1)
    dates = [(start_date + timedelta(days=int(i % 60))).strftime("%Y-%m-%d") for i in range(n_samples)]

    df_clean = pd.DataFrame({
        "record_id": record_ids,
        "state": state_col,
        "commodity": comm_col,
        "arrival_date": dates,
        "min_price": min_price,
        "max_price": max_price,
        "modal_price": modal_price,
        "volume_tonnes": volume_tonnes,
    })

    clean_path = EVAL_DIR / "benchmark_clean_baseline.csv"
    df_clean.to_csv(clean_path, index=False)
    print(f"Generated clean benchmark baseline: {len(df_clean)} rows at {clean_path}")

    # Corrupted Dataset with Exact Ground-Truth Injections
    df_corrupt = df_clean.copy()
    ground_truth = {
        "total_records": n_samples,
        "injected_missing_cells": [],
        "injected_duplicate_rows": [],
        "injected_cross_field_violations": [],
        "injected_negative_values": [],
        "injected_numerical_anomalies": [],
        "injected_schema_changes": {
            "added_columns": ["grade_code"],
            "removed_columns": ["volume_tonnes"],
            "renamed_columns": {"volume_tonnes": "daily_volume_mt"},
        },
        "distribution_drift": {
            "shifted_column": "modal_price",
            "mean_shift_percent": 45.0,
            "variance_multiplier": 2.2,
        }
    }

    # 1. Inject Missing Values (50 rows in 'max_price')
    missing_indices = list(np.random.choice(n_samples, size=50, replace=False))
    df_corrupt.loc[missing_indices, "max_price"] = np.nan
    ground_truth["injected_missing_cells"] = [int(i) for i in missing_indices]

    # 2. Inject Duplicate Rows (25 rows cloned)
    dup_sources = list(np.random.choice(n_samples, size=25, replace=False))
    dup_rows = df_corrupt.iloc[dup_sources].copy()
    start_dup_idx = len(df_corrupt)
    df_corrupt = pd.concat([df_corrupt, dup_rows], ignore_index=True)
    ground_truth["injected_duplicate_rows"] = list(range(start_dup_idx, len(df_corrupt)))

    # 3. Inject Cross-Field Violations (15 rows where min_price > max_price)
    cross_indices = list(np.random.choice([i for i in range(n_samples) if i not in missing_indices], size=15, replace=False))
    for idx in cross_indices:
        orig_min = df_corrupt.loc[idx, "min_price"]
        orig_max = df_corrupt.loc[idx, "max_price"]
        df_corrupt.loc[idx, "min_price"] = orig_max + 500.0
        df_corrupt.loc[idx, "max_price"] = orig_min
    ground_truth["injected_cross_field_violations"] = [int(i) for i in cross_indices]

    # 4. Inject Negative Values (15 rows where min_price < 0)
    neg_indices = list(np.random.choice(n_samples, size=15, replace=False))
    for idx in neg_indices:
        df_corrupt.loc[idx, "min_price"] = -abs(float(df_corrupt.loc[idx, "min_price"]))
    ground_truth["injected_negative_values"] = [int(i) for i in neg_indices]

    # 5. Inject Statistical Anomalies (40 rows with extreme price deviations in 'modal_price')
    # Ground truth records: row_index, true_anomaly=True
    anomaly_indices = list(np.random.choice(n_samples, size=40, replace=False))
    for idx in anomaly_indices:
        multiplier = np.random.uniform(3.5, 7.0)
        df_corrupt.loc[idx, "modal_price"] = round(df_corrupt.loc[idx, "modal_price"] * multiplier, 2)
        ground_truth["injected_numerical_anomalies"].append({
            "row_index": int(idx),
            "column": "modal_price",
            "injected_value": float(df_corrupt.loc[idx, "modal_price"]),
            "original_value": float(df_clean.loc[idx, "modal_price"]),
        })

    corrupt_path = EVAL_DIR / "benchmark_corrupted_test.csv"
    df_corrupt.to_csv(corrupt_path, index=False)
    print(f"Generated corrupted benchmark dataset: {len(df_corrupt)} rows at {corrupt_path}")

    # 6. Generate Distribution Drifted Baseline (for testing PSI & KS-Test)
    df_drifted = df_clean.copy()
    # Apply a significant +45% mean shift and widened variance to 'modal_price'
    df_drifted["modal_price"] = df_drifted["modal_price"] * 1.45 + np.random.normal(0, 400, size=len(df_drifted))
    df_drifted["modal_price"] = np.round(np.clip(df_drifted["modal_price"], 1500, 12000), 2)
    # Add a new categorical state to test category shift
    df_drifted.loc[:100, "state"] = "Assam (New Region)"
    drift_path = EVAL_DIR / "benchmark_distribution_drifted.csv"
    df_drifted.to_csv(drift_path, index=False)
    print(f"Generated distribution-drifted benchmark: {len(df_drifted)} rows at {drift_path}")

    # Save Ground Truth Spec
    gt_path = EVAL_DIR / "ground_truth.json"
    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"Saved ground truth annotations to {gt_path}")


if __name__ == "__main__":
    generate_benchmark_datasets()
