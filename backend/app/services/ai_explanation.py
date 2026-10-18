import os
from typing import List, Dict, Any, Optional


def generate_diagnostic_brief(
    dataset_name: str,
    overall_score: float,
    check_results: List[Dict[str, Any]],
    anomaly_findings: List[Dict[str, Any]],
    schema_diff: Optional[Dict[str, Any]] = None,
    drift_summary: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generates an executive diagnostic briefing from structured monitoring evidence.
    Deterministic, explainable, and cites exact check IDs without hallucinating values.
    """
    failed_checks = [c for c in check_results if c.get("status") == "failed"]
    warning_checks = [c for c in check_results if c.get("status") == "warning"]

    # 1. Executive Summary
    if overall_score >= 85.0 and len(failed_checks) == 0:
        verdict = "HEALTHY & PRODUCTION READY"
        executive_summary = (
            f"Dataset '{dataset_name}' exhibits high structural and statistical reliability "
            f"with an overall quality score of {overall_score:.1f}/100. "
            f"No critical schema or validation violations were detected."
        )
    elif overall_score >= 70.0:
        verdict = "MONITOR WITH CAUTION"
        executive_summary = (
            f"Dataset '{dataset_name}' scored {overall_score:.1f}/100. "
            f"While core structural checks passed, {len(warning_checks)} warning(s) "
            f"were flagged that may indicate upstream recording inconsistencies."
        )
    else:
        verdict = "REQUIRES HUMAN REVIEW"
        executive_summary = (
            f"Dataset '{dataset_name}' scored {overall_score:.1f}/100 with {len(failed_checks)} failure(s). "
            f"Potential integrity risks exist. Downstream ingestion or analytics should proceed only after review."
        )

    # 2. Key Findings & Hypotheses (Ground-truth driven)
    findings_analysis = []
    
    for chk in failed_checks:
        cid = chk.get("check_id")
        cname = chk.get("check_name")
        expl = chk.get("explanation")
        aff_cols = chk.get("affected_columns", [])
        aff_rows = chk.get("affected_rows", 0)

        hypothesis = (
            "Possible data export glitch, inverted column mapping, or missing field validations at the point of source entry."
            if "cross" in cid.lower() or "val" in cid.lower()
            else "Potential ingestion pipe discontinuity or unhandled schema migration."
        )

        findings_analysis.append({
            "check_id": cid,
            "title": cname,
            "severity": chk.get("severity", "high"),
            "observation": expl,
            "affected_scope": f"{aff_rows} rows affected across {aff_cols if aff_cols else 'dataset'}",
            "hypothesis": hypothesis,
            "recommended_action": chk.get("suggested_action", "Investigate source file."),
        })

    for chk in warning_checks[:3]:
        cid = chk.get("check_id")
        findings_analysis.append({
            "check_id": cid,
            "title": chk.get("check_name"),
            "severity": "medium",
            "observation": chk.get("explanation"),
            "affected_scope": f"{chk.get('affected_rows', 0)} rows affected",
            "hypothesis": "Non-breaking anomaly, likely minor sampling or data format variance.",
            "recommended_action": chk.get("suggested_action", "Monitor next run."),
        })

    # 3. Anomaly Synthesis
    anomaly_summary = []
    if anomaly_findings:
        anom_by_col = {}
        for a in anomaly_findings:
            col = a["column_name"]
            anom_by_col.setdefault(col, []).append(a)

        for col, anom_list in anom_by_col.items():
            methods = list(set(a["detection_method"] for a in anom_list))
            max_dev = max((a.get("score") or 0.0) for a in anom_list)
            sample_val = anom_list[0]["value"]
            anomaly_summary.append({
                "column": col,
                "count": len(anom_list),
                "methods": methods,
                "highest_deviation": round(max_dev, 2),
                "sample_value": sample_val,
                "interpretation": (
                    f"Column '{col}' exhibits {len(anom_list)} statistical outlier(s) detected via {', '.join(methods)}. "
                    f"Note: Statistical outliers represent unusual observations, not necessarily corrupt records (e.g. seasonal price peaks or high-volume facilities)."
                )
            })

    # 4. Schema & Drift Analysis
    schema_notes = []
    if schema_diff and schema_diff.get("has_drift"):
        if schema_diff.get("added_columns"):
            schema_notes.append(f"Newly introduced columns: {schema_diff['added_columns']}")
        if schema_diff.get("removed_columns"):
            schema_notes.append(f"Removed columns (Breaking): {schema_diff['removed_columns']}")
        if schema_diff.get("possible_renames"):
            for r in schema_diff["possible_renames"]:
                schema_notes.append(f"Likely rename: '{r['old_column']}' -> '{r['new_column']}' (Confidence: {r['confidence']})")

    drift_notes = []
    if drift_summary and drift_summary.get("drift_available"):
        for m in drift_summary.get("metrics", []):
            if m.get("drift_detected"):
                drift_notes.append(f"Column '{m['column_name']}': {m['interpretation']}")

    # 5. Remediation Checklist
    action_items = []
    if failed_checks:
        action_items.append("Audit records violating cross-field and non-negative constraints.")
    if schema_diff and schema_diff.get("removed_columns"):
        action_items.append("Update downstream ingestion models to handle removed column schemas.")
    if any(a.get("severity") == "critical" for a in anomaly_findings):
        action_items.append("Review critical outliers in the Anomaly Explorer to confirm whether they reflect legitimate market events.")
    if not action_items:
        action_items.append("No immediate intervention required. Dataset is within normal operating tolerance.")

    return {
        "dataset_name": dataset_name,
        "verdict": verdict,
        "executive_summary": executive_summary,
        "overall_score": overall_score,
        "findings_analysis": findings_analysis,
        "anomaly_summary": anomaly_summary,
        "schema_notes": schema_notes,
        "drift_notes": drift_notes,
        "action_items": action_items,
    }
