from datetime import datetime, timedelta
from typing import Dict, Any, Optional


CADENCE_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
    "quarterly": timedelta(days=90),
}

# Grace periods before marking overdue
CADENCE_GRACE_PERIODS = {
    "daily": timedelta(days=2),
    "weekly": timedelta(days=5),
    "monthly": timedelta(days=15),
    "quarterly": timedelta(days=30),
}


def assess_freshness(
    update_cadence: str,
    last_successful_ingestion: Optional[datetime],
    last_content_change: Optional[datetime],
    last_attempted_ingestion: Optional[datetime],
    last_ingestion_status: Optional[str] = "success",
) -> Dict[str, Any]:
    """
    Evaluates dataset freshness, overdue status, and source health.
    Distinguishes failed ingestion from unchanged content.
    """
    now = datetime.utcnow()
    cadence = update_cadence.lower() if update_cadence else "unknown"

    if not last_successful_ingestion:
        return {
            "status": "never_ingested" if not last_attempted_ingestion else "source_unavailable",
            "is_overdue": False,
            "dataset_age_hours": None,
            "expected_next_update": None,
            "days_overdue": 0,
            "freshness_score": 0.0,
            "explanation": "Dataset has never been successfully ingested.",
        }

    age = now - last_successful_ingestion
    age_hours = round(age.total_seconds() / 3600, 1)

    expected_interval = CADENCE_INTERVALS.get(cadence)
    grace_period = CADENCE_GRACE_PERIODS.get(cadence)

    if expected_interval and grace_period:
        expected_next = last_successful_ingestion + expected_interval
        deadline = expected_next + grace_period
        is_overdue = now > deadline
        days_overdue = max(0, (now - deadline).days) if is_overdue else 0
    else:
        expected_next = None
        is_overdue = False
        days_overdue = 0

    # Determine status
    if last_ingestion_status == "failed":
        status = "source_unavailable"
        explanation = f"Source retrieval failed on last attempted run at {last_attempted_ingestion}."
        freshness_score = 40.0
    elif is_overdue:
        status = "overdue"
        explanation = f"Dataset is overdue by {days_overdue} day(s) based on expected '{cadence}' cadence."
        freshness_score = max(20.0, 100.0 - (days_overdue * 10))
    elif age_hours > 72 and cadence == "daily":
        status = "warning"
        explanation = f"Last update was {age_hours} hours ago, approaching overdue threshold."
        freshness_score = 75.0
    else:
        status = "healthy"
        explanation = f"Dataset is up to date. Ingested {age_hours} hours ago."
        freshness_score = 100.0

    return {
        "status": status,
        "is_overdue": is_overdue,
        "dataset_age_hours": age_hours,
        "last_content_change": last_content_change.isoformat() if last_content_change else None,
        "expected_next_update": expected_next.isoformat() if expected_next else None,
        "days_overdue": days_overdue,
        "freshness_score": round(freshness_score, 1),
        "explanation": explanation,
    }
