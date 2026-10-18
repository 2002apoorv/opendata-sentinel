from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats


def calculate_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    num_bins: int = 10,
    epsilon: float = 1e-4,
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Calculates Population Stability Index (PSI) between baseline (expected) and current (actual).
    Uses baseline quantiles for bin edges.
    Interpretation:
      - PSI < 0.10: Stable (insignificant change)
      - 0.10 <= PSI < 0.25: Moderate shift (monitor closely)
      - PSI >= 0.25: Significant distribution drift (action required)
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0, []

    # Calculate quantile bin edges from baseline
    try:
        quantiles = np.linspace(0, 1, num_bins + 1)
        bin_edges = np.percentile(expected, quantiles * 100)
        bin_edges = np.unique(bin_edges)  # remove duplicate edges for discrete values
    except Exception:
        return 0.0, []

    if len(bin_edges) < 2:
        return 0.0, []

    # Adjust edges slightly for outer boundaries
    bin_edges[0] -= 1e-5
    bin_edges[-1] += 1e-5

    # Count occurrences in each bin
    expected_counts, _ = np.histogram(expected, bins=bin_edges)
    actual_counts, _ = np.histogram(actual, bins=bin_edges)

    expected_pct = expected_counts / len(expected)
    actual_pct = actual_counts / len(actual)

    # Smooth zero probabilities
    expected_pct = np.where(expected_pct == 0, epsilon, expected_pct)
    actual_pct = np.where(actual_pct == 0, epsilon, actual_pct)

    # Re-normalize
    expected_pct = expected_pct / np.sum(expected_pct)
    actual_pct = actual_pct / np.sum(actual_pct)

    bin_psi = (actual_pct - expected_pct) * np.log(actual_pct / expected_pct)
    total_psi = float(np.sum(bin_psi))

    bin_details = []
    for i in range(len(bin_edges) - 1):
        bin_details.append({
            "bin_range": f"[{bin_edges[i]:.2f}, {bin_edges[i+1]:.2f})",
            "baseline_pct": round(float(expected_pct[i] * 100), 2),
            "current_pct": round(float(actual_pct[i] * 100), 2),
            "psi_contribution": round(float(bin_psi[i]), 4),
        })

    return round(total_psi, 4), bin_details


class DistributionDriftDetector:
    """
    Detects dataset-level distribution drift between current data and historical baseline.
    """

    def __init__(self, current_df: pd.DataFrame, baseline_df: Optional[pd.DataFrame] = None):
        self.current_df = current_df
        self.baseline_df = baseline_df

    def detect_drift(self) -> Dict[str, Any]:
        """
        Executes drift tests across numerical and categorical columns.
        If baseline_df is None or empty, returns drift_available=False honestly.
        """
        if self.baseline_df is None or self.baseline_df.empty:
            return {
                "drift_available": False,
                "summary": "Distribution drift detection requires a prior successful monitoring run baseline. Baseline snapshot is currently unavailable.",
                "columns_analyzed": 0,
                "drifted_columns_count": 0,
                "has_significant_drift": False,
                "metrics": [],
            }

        metrics: List[Dict[str, Any]] = []
        drifted_columns = set()

        # Shared columns between current and baseline
        common_cols = [c for c in self.current_df.columns if c in self.baseline_df.columns]

        for col in common_cols:
            curr_series = self.current_df[col].dropna()
            base_series = self.baseline_df[col].dropna()

            if len(curr_series) < 15 or len(base_series) < 15:
                continue

            # 1. Numerical Drift
            if pd.api.types.is_numeric_dtype(curr_series) and pd.api.types.is_numeric_dtype(base_series):
                base_mean = float(base_series.mean())
                curr_mean = float(curr_series.mean())
                mean_pct_shift = abs((curr_mean - base_mean) / (base_mean + 1e-6)) * 100

                base_median = float(base_series.median())
                curr_median = float(curr_series.median())

                # Two-sample Kolmogorov-Smirnov test
                try:
                    ks_res = stats.ks_2samp(base_series.values, curr_series.values)
                    ks_stat = round(float(ks_res.statistic), 4)
                    ks_pval = round(float(ks_res.pvalue), 6)
                except Exception:
                    ks_stat, ks_pval = 0.0, 1.0

                # Population Stability Index (PSI)
                psi_val, bin_breakdown = calculate_psi(base_series.values, curr_series.values)

                # Determine if drifted
                is_drifted = (psi_val >= 0.25) or (ks_pval < 0.01 and ks_stat > 0.20) or (mean_pct_shift > 35.0)

                if psi_val >= 0.25:
                    interp = f"Significant drift detected (PSI={psi_val:.3f} >= 0.25). Distribution has shifted substantially from baseline."
                elif psi_val >= 0.10:
                    interp = f"Moderate shift (PSI={psi_val:.3f} in [0.10, 0.25)). Distribution warrants monitoring."
                else:
                    interp = f"Stable distribution (PSI={psi_val:.3f} < 0.10). No meaningful deviation from baseline."

                if is_drifted:
                    drifted_columns.add(col)

                metrics.append({
                    "column_name": col,
                    "metric_type": "psi_ks_numerical",
                    "metric_value": psi_val,
                    "p_value": ks_pval,
                    "drift_detected": is_drifted,
                    "interpretation": interp,
                    "details": {
                        "psi": psi_val,
                        "ks_statistic": ks_stat,
                        "ks_pvalue": ks_pval,
                        "baseline_mean": round(base_mean, 2),
                        "current_mean": round(curr_mean, 2),
                        "mean_shift_pct": round(mean_pct_shift, 2),
                        "baseline_median": round(base_median, 2),
                        "current_median": round(curr_median, 2),
                        "bins": bin_breakdown[:6],
                    }
                })

            # 2. Categorical Drift
            elif pd.api.types.is_string_dtype(curr_series) or pd.api.types.is_object_dtype(curr_series):
                base_cats = set(base_series.unique())
                curr_cats = set(curr_series.unique())
                new_cats = list(curr_cats - base_cats)
                lost_cats = list(base_cats - curr_cats)

                base_dist = base_series.value_counts(normalize=True).to_dict()
                curr_dist = curr_series.value_counts(normalize=True).to_dict()

                # Calculate total variation distance
                all_cats = base_cats.union(curr_cats)
                tvd = 0.5 * sum(abs(curr_dist.get(c, 0.0) - base_dist.get(c, 0.0)) for c in all_cats)
                tvd = round(float(tvd), 4)

                cat_drifted = (tvd > 0.25) or len(new_cats) > 0

                if cat_drifted:
                    drifted_columns.add(col)
                    interp = f"Categorical shift detected (Total Variation Distance={tvd:.3f})."
                    if new_cats:
                        interp += f" New categories observed: {new_cats[:3]}."
                else:
                    interp = f"Category proportions stable (TVD={tvd:.3f})."

                metrics.append({
                    "column_name": col,
                    "metric_type": "category_shift",
                    "metric_value": tvd,
                    "p_value": None,
                    "drift_detected": cat_drifted,
                    "interpretation": interp,
                    "details": {
                        "total_variation_distance": tvd,
                        "new_categories": new_cats,
                        "lost_categories": lost_cats,
                        "current_distribution": {k: round(v, 3) for k, v in list(curr_dist.items())[:5]},
                        "baseline_distribution": {k: round(v, 3) for k, v in list(base_dist.items())[:5]},
                    }
                })

        summary_text = (
            f"Analyzed {len(common_cols)} columns against baseline. "
            f"Detected distribution shift in {len(drifted_columns)} column(s)."
            if drifted_columns
            else f"Analyzed {len(common_cols)} columns. All numerical distributions and categorical domains remain stable."
        )

        return {
            "drift_available": True,
            "summary": summary_text,
            "columns_analyzed": len(common_cols),
            "drifted_columns_count": len(drifted_columns),
            "has_significant_drift": len(drifted_columns) > 0,
            "metrics": metrics,
        }
