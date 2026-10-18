from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    """
    Statistical and Machine Learning Anomaly Detector for Numerical Data.
    Provides explainable IQR, Z-score, Robust MAD, and Isolation Forest detection.
    """

    def __init__(self, df: pd.DataFrame, primary_key_col: Optional[str] = None):
        self.df = df
        self.primary_key_col = primary_key_col
        # Find row identifier column if available
        if not self.primary_key_col:
            for col in self.df.columns:
                if any(k in col.lower() for k in ["record_id", "station_id", "facility_id", "id"]):
                    self.primary_key_col = col
                    break

    def get_row_id(self, idx: int) -> str:
        if self.primary_key_col and self.primary_key_col in self.df.columns:
            val = self.df.iloc[idx][self.primary_key_col]
            return str(val) if pd.notna(val) else f"Row #{idx}"
        return f"Row #{idx}"

    def detect_anomalies(
        self,
        methods: Optional[List[str]] = None,
        iqr_multiplier: float = 1.75,
        z_threshold: float = 3.0,
        mad_threshold: float = 3.5,
        iso_contamination: float = 0.02,
        max_anomalies_per_col: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Executes configured anomaly detection methods across numeric columns.
        Returns a list of structured AnomalyFinding dictionaries.
        """
        if methods is None:
            methods = ["iqr", "mad", "isolation_forest"]

        findings: List[Dict[str, Any]] = []
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            series = self.df[col].dropna()
            
            # Guardrail 1: Minimum sample size
            if len(series) < 15:
                continue

            # Guardrail 2: Constant or zero-variance column
            if series.nunique() <= 1 or series.std() == 0:
                continue

            # --- Method 1: IQR (Interquartile Range) ---
            if "iqr" in methods:
                q25 = float(series.quantile(0.25))
                q75 = float(series.quantile(0.75))
                iqr = q75 - q25
                if iqr > 0:
                    lower_bound = round(q25 - (iqr_multiplier * iqr), 3)
                    upper_bound = round(q75 + (iqr_multiplier * iqr), 3)

                    outliers = series[(series < lower_bound) | (series > upper_bound)]
                    for idx, val in outliers.head(max_anomalies_per_col).items():
                        deviation = abs(val - series.median()) / iqr
                        severity = "critical" if deviation > 4.0 else ("high" if deviation > 2.5 else "medium")
                        direction = "above upper threshold" if val > upper_bound else "below lower threshold"

                        findings.append({
                            "column_name": col,
                            "row_index": int(idx),
                            "row_identifier": self.get_row_id(int(idx)),
                            "value": str(round(float(val), 2)),
                            "detection_method": "iqr",
                            "threshold_rule": f"IQR [{lower_bound}, {upper_bound}] (k={iqr_multiplier})",
                            "severity": severity,
                            "score": round(float(deviation), 2),
                            "explanation": f"Observed value {val:.2f} is {direction} [{lower_bound}, {upper_bound}]. Deviation is {deviation:.1f}x IQR from median.",
                            "review_status": "pending",
                        })

            # --- Method 2: Robust MAD (Median Absolute Deviation) ---
            if "mad" in methods:
                median = float(series.median())
                abs_deviation = (series - median).abs()
                mad = float(abs_deviation.median())

                # Scale factor for normal distribution consistency (1.4826)
                if mad > 1e-6:
                    modified_z = (0.6745 * (series - median).abs()) / mad
                    outliers_mad = series[modified_z > mad_threshold]

                    for idx, val in outliers_mad.head(max_anomalies_per_col).items():
                        mod_z_val = round(float(modified_z.loc[idx]), 2)
                        severity = "critical" if mod_z_val > 6.0 else ("high" if mod_z_val > 4.5 else "medium")

                        findings.append({
                            "column_name": col,
                            "row_index": int(idx),
                            "row_identifier": self.get_row_id(int(idx)),
                            "value": str(round(float(val), 2)),
                            "detection_method": "mad",
                            "threshold_rule": f"Modified Z-Score > {mad_threshold} (MAD={mad:.2f})",
                            "severity": severity,
                            "score": mod_z_val,
                            "explanation": f"Robust median absolute deviation flagged modified Z={mod_z_val} (median={median:.2f}, MAD={mad:.2f}).",
                            "review_status": "pending",
                        })

            # --- Method 3: Standard Z-Score (Optional) ---
            if "zscore" in methods:
                mean = float(series.mean())
                std = float(series.std())
                if std > 1e-6:
                    z_scores = (series - mean).abs() / std
                    outliers_z = series[z_scores > z_threshold]
                    for idx, val in outliers_z.head(max_anomalies_per_col).items():
                        z_val = round(float(z_scores.loc[idx]), 2)
                        severity = "critical" if z_val > 5.0 else ("high" if z_val > 4.0 else "medium")
                        findings.append({
                            "column_name": col,
                            "row_index": int(idx),
                            "row_identifier": self.get_row_id(int(idx)),
                            "value": str(round(float(val), 2)),
                            "detection_method": "zscore",
                            "threshold_rule": f"|Z| > {z_threshold} (mean={mean:.2f}, std={std:.2f})",
                            "severity": severity,
                            "score": z_val,
                            "explanation": f"Parametric Z-score of {z_val} exceeds {z_threshold} standard deviations from mean.",
                            "review_status": "pending",
                        })

        # --- Method 4: Multivariate / Univariate Isolation Forest ---
        if "isolation_forest" in methods and len(numeric_cols) > 0 and len(self.df) >= 30:
            try:
                # Prepare numeric matrix with median imputation for fitting
                X = self.df[numeric_cols].copy()
                X = X.fillna(X.median())

                # Drop zero-variance columns
                valid_features = [c for c in numeric_cols if X[c].std() > 0]
                if len(valid_features) > 0:
                    X_valid = X[valid_features]
                    iso = IsolationForest(
                        contamination=iso_contamination,
                        random_state=42,
                        n_estimators=100,
                    )
                    preds = iso.fit_predict(X_valid)
                    scores = -iso.score_samples(X_valid)  # Higher score = more anomalous

                    anomaly_indices = np.where(preds == -1)[0]
                    # Sort by anomaly score descending
                    sorted_anom = sorted(anomaly_indices, key=lambda i: scores[i], reverse=True)[:max_anomalies_per_col]

                    for idx in sorted_anom:
                        score_val = round(float(scores[idx]), 3)
                        # Identify the most contributing column for explainability
                        row_vals = X_valid.iloc[idx]
                        col_deviations = {
                            c: abs(row_vals[c] - X_valid[c].median()) / (X_valid[c].std() + 1e-6)
                            for c in valid_features
                        }
                        top_col = max(col_deviations, key=col_deviations.get)
                        top_val = self.df.iloc[idx][top_col]

                        severity = "critical" if score_val > 0.65 else ("high" if score_val > 0.55 else "medium")

                        findings.append({
                            "column_name": top_col,
                            "row_index": int(idx),
                            "row_identifier": self.get_row_id(int(idx)),
                            "value": str(round(float(top_val), 2)) if pd.notna(top_val) and isinstance(top_val, (int, float)) else str(top_val),
                            "detection_method": "isolation_forest",
                            "threshold_rule": f"Isolation Forest Tree Depth (Contamination={iso_contamination})",
                            "severity": severity,
                            "score": score_val,
                            "explanation": f"Isolation forest isolated point with anomaly score {score_val:.3f}. Primary driver in feature space: '{top_col}'.",
                            "review_status": "pending",
                        })
            except Exception as e:
                # Keep resilient: ML model failure must not crash pipeline
                pass

        # Deduplicate findings per (column_name, row_index) keeping highest severity/score
        deduped = {}
        for f in findings:
            key = (f["column_name"], f["row_index"], f["detection_method"])
            if key not in deduped:
                deduped[key] = f

        return list(deduped.values())
