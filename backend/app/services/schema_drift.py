from typing import List, Dict, Any, Optional
import pandas as pd
from backend.app.services.ingestion import infer_column_types


def extract_schema_snapshot(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Extracts a detailed schema snapshot from a DataFrame:
    column names, inferred types, nullability, null count, unique count, and sample values.
    """
    inferred_types = infer_column_types(df)
    snapshot = []
    
    for col in df.columns:
        series = df[col]
        null_count = int(series.isna().sum())
        total = len(df)
        null_pct = round((null_count / total * 100), 2) if total > 0 else 0.0
        unique_cnt = int(series.nunique(dropna=True))
        
        # Safe JSON serializable sample values
        samples = []
        for val in series.dropna().unique()[:4]:
            if isinstance(val, (int, float, str, bool)):
                samples.append(val)
            else:
                samples.append(str(val))

        snapshot.append({
            "name": str(col),
            "inferred_type": inferred_types.get(col, "string"),
            "nullable": null_count > 0,
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_count": unique_cnt,
            "sample_values": samples,
        })
        
    return snapshot


def compare_schemas(
    current_snapshot: List[Dict[str, Any]],
    baseline_snapshot: Optional[List[Dict[str, Any]]] = None,
    expected_schema: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Compares current schema snapshot against baseline or expected schema.
    Detects added, removed, type-changed, nullability-changed, and likely renamed columns.
    """
    current_cols = {c["name"]: c for c in current_snapshot}
    
    if not baseline_snapshot:
        # Check against expected schema if provided
        if expected_schema:
            missing_expected = [col for col in expected_schema.keys() if col not in current_cols]
            return {
                "has_drift": len(missing_expected) > 0,
                "severity": "critical" if missing_expected else "info",
                "added_columns": [col for col in current_cols.keys() if col not in expected_schema],
                "removed_columns": missing_expected,
                "type_changes": [],
                "possible_renames": [],
                "diff_items": [],
                "summary": "Initial baseline established. Conforms to expected schema." if not missing_expected else f"Missing expected columns: {missing_expected}",
            }
        
        return {
            "has_drift": False,
            "severity": "info",
            "added_columns": [],
            "removed_columns": [],
            "type_changes": [],
            "possible_renames": [],
            "diff_items": [],
            "summary": "Initial schema snapshot recorded. Baseline established for subsequent drift comparisons.",
        }

    baseline_cols = {c["name"]: c for c in baseline_snapshot}
    
    curr_names = set(current_cols.keys())
    base_names = set(baseline_cols.keys())

    added = sorted(list(curr_names - base_names))
    removed = sorted(list(base_names - curr_names))

    diff_items = []
    possible_renames = []

    # Detect potential column renames (e.g. arrivals_in_tonnes -> daily_arrivals_tonnes)
    # Evidence: type matches, unique count is comparable, sample value overlap
    unmatched_added = list(added)
    unmatched_removed = list(removed)

    for rem in list(unmatched_removed):
        rem_meta = baseline_cols[rem]
        for add in list(unmatched_added):
            add_meta = current_cols[add]
            # Match on inferred type and similar nullability
            if rem_meta["inferred_type"] == add_meta["inferred_type"]:
                # Check for substring similarity or sample overlap
                rem_lower = rem.lower().replace("_", "")
                add_lower = add.lower().replace("_", "")
                name_overlap = any(token in add_lower for token in rem_lower.split()) or (rem_lower in add_lower or add_lower in rem_lower)
                
                if name_overlap:
                    confidence = "high" if (rem_lower in add_lower or add_lower in rem_lower) else "medium"
                    rename_candidate = {
                        "old_column": rem,
                        "new_column": add,
                        "confidence": confidence,
                        "inferred_type": rem_meta["inferred_type"],
                        "evidence": f"Matching type '{rem_meta['inferred_type']}' and lexical name similarity ({rem} -> {add}).",
                    }
                    possible_renames.append(rename_candidate)
                    diff_items.append({
                        "column_name": add,
                        "change_type": "renamed_likely",
                        "severity": "warning",
                        "old_value": rem,
                        "new_value": add,
                        "impact_analysis": f"Potential rename of '{rem}' to '{add}'. Downstream queries referencing '{rem}' will fail until updated.",
                        "evidence": rename_candidate,
                    })
                    if rem in unmatched_removed:
                        unmatched_removed.remove(rem)
                    if add in unmatched_added:
                        unmatched_added.remove(add)
                    break

    # Record genuinely added columns
    for add in unmatched_added:
        diff_items.append({
            "column_name": add,
            "change_type": "added",
            "severity": "info",
            "old_value": None,
            "new_value": current_cols[add]["inferred_type"],
            "impact_analysis": f"New column '{add}' introduced. Non-breaking for existing readers, but warrants schema tracking.",
            "evidence": current_cols[add],
        })

    # Record genuinely removed columns
    for rem in unmatched_removed:
        diff_items.append({
            "column_name": rem,
            "change_type": "removed",
            "severity": "critical",
            "old_value": baseline_cols[rem]["inferred_type"],
            "new_value": None,
            "impact_analysis": f"Column '{rem}' was removed from the source. Downstream models and consumers expecting this column may break.",
            "evidence": baseline_cols[rem],
        })

    # Check for type changes in common columns
    type_changes = []
    common_cols = curr_names.intersection(base_names)
    for col in common_cols:
        base_t = baseline_cols[col]["inferred_type"]
        curr_t = current_cols[col]["inferred_type"]
        if base_t != curr_t:
            item = {
                "column_name": col,
                "change_type": "type_changed",
                "severity": "critical" if (base_t in ["integer", "float"] and curr_t == "string") else "warning",
                "old_value": base_t,
                "new_value": curr_t,
                "impact_analysis": f"Type drifted from '{base_t}' to '{curr_t}'. Type coercion errors may occur.",
                "evidence": {"baseline_type": base_t, "current_type": curr_t},
            }
            type_changes.append(item)
            diff_items.append(item)

        # Check for significant nullability shift
        base_null_pct = baseline_cols[col]["null_percentage"]
        curr_null_pct = current_cols[col]["null_percentage"]
        if base_null_pct == 0.0 and curr_null_pct > 15.0:
            diff_items.append({
                "column_name": col,
                "change_type": "nullability_changed",
                "severity": "warning",
                "old_value": f"{base_null_pct}% nulls",
                "new_value": f"{curr_null_pct}% nulls",
                "impact_analysis": f"Column '{col}' was previously non-nullable (0% null), now exhibits {curr_null_pct}% missing values.",
                "evidence": {"baseline_null_pct": base_null_pct, "current_null_pct": curr_null_pct},
            })

    has_drift = len(diff_items) > 0
    severity = "info"
    if any(d["severity"] == "critical" for d in diff_items):
        severity = "critical"
    elif any(d["severity"] == "warning" for d in diff_items):
        severity = "warning"

    summary_parts = []
    if added:
        summary_parts.append(f"{len(added)} column(s) added")
    if removed:
        summary_parts.append(f"{len(removed)} column(s) removed")
    if type_changes:
        summary_parts.append(f"{len(type_changes)} type change(s)")
    if possible_renames:
        summary_parts.append(f"{len(possible_renames)} likely rename(s)")
    
    summary = "; ".join(summary_parts) if summary_parts else "Schema is identical to previous baseline snapshot."

    return {
        "has_drift": has_drift,
        "severity": severity,
        "added_columns": added,
        "removed_columns": removed,
        "type_changes": type_changes,
        "possible_renames": possible_renames,
        "diff_items": diff_items,
        "summary": summary,
    }
