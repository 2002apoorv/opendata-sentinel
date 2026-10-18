from typing import List, Dict, Any, Optional


DEFAULT_WEIGHTS = {
    "completeness": 0.25,
    "validity": 0.25,
    "uniqueness": 0.15,
    "schema": 0.15,
    "consistency": 0.10,
    "freshness": 0.10,
}


def calculate_quality_score(
    check_results: List[Dict[str, Any]],
    freshness_score: float = 100.0,
    custom_weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Computes an explainable multi-dimensional dataset quality score.
    Includes dimension breakdowns, check counts, and caps the score
    if critical failures are present so severe errors cannot be masked.
    """
    weights = custom_weights or DEFAULT_WEIGHTS

    # Group check results by category
    categories = {
        "completeness": [],
        "validity": [],
        "uniqueness": [],
        "schema": [],
        "consistency": [],
    }

    critical_count = 0
    passed_total = 0
    warning_total = 0
    failed_total = 0

    for chk in check_results:
        cat = chk.get("category", "validity")
        status = chk.get("status", "passed")
        severity = chk.get("severity", "info")

        if severity == "critical" and status == "failed":
            critical_count += 1

        if status == "passed":
            passed_total += 1
        elif status == "warning":
            warning_total += 1
        elif status == "failed":
            failed_total += 1

        if cat in categories:
            categories[cat].append(chk)
        else:
            categories["validity"].append(chk)

    dimension_scores = {}
    weighted_sum = 0.0
    active_weight_total = 0.0

    for cat_name, chk_list in categories.items():
        w = weights.get(cat_name, 0.15)
        if not chk_list:
            # If no checks were executed in this dimension, don't penalize to 0, mark as neutral 100
            dim_score = 100.0
            p_cnt, w_cnt, f_cnt = 0, 0, 0
            explanation = "No specific rules configured for this dimension."
        else:
            p_cnt = sum(1 for c in chk_list if c["status"] == "passed")
            w_cnt = sum(1 for c in chk_list if c["status"] == "warning")
            f_cnt = sum(1 for c in chk_list if c["status"] == "failed")
            
            # Points: passed = 1.0, warning = 0.65, failed = 0.0
            points = (p_cnt * 1.0) + (w_cnt * 0.65) + (f_cnt * 0.0)
            dim_score = round((points / len(chk_list)) * 100, 1)

            if f_cnt > 0:
                explanation = f"{f_cnt} check(s) failed in this dimension."
            elif w_cnt > 0:
                explanation = f"{w_cnt} warning(s) flagged."
            else:
                explanation = f"All {p_cnt} checks passed."

        dimension_scores[cat_name] = {
            "score": dim_score,
            "weight": w,
            "checks_count": len(chk_list),
            "passed_count": p_cnt,
            "warning_count": w_cnt,
            "failed_count": f_cnt,
            "explanation": explanation,
        }
        weighted_sum += dim_score * w
        active_weight_total += w

    # Freshness dimension
    freshness_weight = weights.get("freshness", 0.10)
    dimension_scores["freshness"] = {
        "score": round(freshness_score, 1),
        "weight": freshness_weight,
        "checks_count": 1,
        "passed_count": 1 if freshness_score >= 80 else 0,
        "warning_count": 1 if 40 <= freshness_score < 80 else 0,
        "failed_count": 1 if freshness_score < 40 else 0,
        "explanation": "Evaluated against expected publication cadence.",
    }
    weighted_sum += freshness_score * freshness_weight
    active_weight_total += freshness_weight

    raw_overall = weighted_sum / active_weight_total if active_weight_total > 0 else 0.0

    # Critical failure penalty: If there are critical failures (e.g. primary key duplicate, empty file, schema breaking)
    # the overall score is capped to prevent masking severe failures behind an average.
    if critical_count > 0:
        overall_score = min(58.0, raw_overall - (critical_count * 15.0))
        overall_score = max(10.0, overall_score)
        summary_text = f"Quality score capped at {overall_score:.1f}/100 due to {critical_count} critical failure(s)."
    else:
        overall_score = round(raw_overall, 1)
        if overall_score >= 85.0:
            summary_text = f"High reliability dataset (Score: {overall_score:.1f}/100)."
        elif overall_score >= 70.0:
            summary_text = f"Acceptable quality with moderate warnings (Score: {overall_score:.1f}/100)."
        else:
            summary_text = f"Low reliability dataset requiring manual review (Score: {overall_score:.1f}/100)."

    return {
        "overall_score": round(overall_score, 1),
        "is_passing": overall_score >= 70.0 and critical_count == 0,
        "critical_failures_count": critical_count,
        "total_checks": len(check_results) + 1,
        "passed_checks": passed_total + (1 if freshness_score >= 80 else 0),
        "warning_checks": warning_total + (1 if 40 <= freshness_score < 80 else 0),
        "failed_checks": failed_total + (1 if freshness_score < 40 else 0),
        "dimensions": dimension_scores,
        "summary_text": summary_text,
    }
