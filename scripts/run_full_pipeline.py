"""
OpenData Sentinel - CLI Pipeline Runner
Executes an end-to-end monitoring run on registered datasets directly from the terminal.
Usage:
    python scripts/run_full_pipeline.py --all
    python scripts/run_full_pipeline.py --dataset-id <ID>
"""

import sys
import argparse
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.dataset import Dataset
from backend.app.services.monitoring import MonitoringPipeline


def main():
    parser = argparse.ArgumentParser(description="OpenData Sentinel CLI Monitoring Runner")
    parser.add_argument("--all", action="store_true", help="Run monitoring pipeline across all registered datasets")
    parser.add_argument("--dataset-id", type=str, help="Target specific dataset ID to monitor")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    pipeline = MonitoringPipeline(db)

    try:
        if args.dataset_id:
            targets = db.query(Dataset).filter(Dataset.id == args.dataset_id).all()
            if not targets:
                print(f"Error: Dataset '{args.dataset_id}' not found.")
                return
        else:
            targets = db.query(Dataset).all()
            if not targets:
                print("No datasets registered yet. Run scripts/seed_database.py first or register via API.")
                return

        print("=" * 70)
        print(f"OPENDATA SENTINEL: RUNNING MONITORING PIPELINE ON {len(targets)} DATASET(S)")
        print("=" * 70)

        for d in targets:
            print(f"\n[AUDITING] {d.name} ({d.id})")
            run = pipeline.execute_monitoring_run(d.id, run_type="monitor")
            print(f" -> Status: {run.status.upper()}")
            print(f" -> Quality Score: {run.quality_score}%")
            print(f" -> Records: {run.row_count} rows, {run.column_count} cols")
            print(f" -> Summary: {run.summary}")

        print("\n" + "=" * 70)
        print("MONITORING RUN COMPLETED SUCCESSFULLY")
        print("=" * 70)
    finally:
        db.close()


if __name__ == "__main__":
    main()
