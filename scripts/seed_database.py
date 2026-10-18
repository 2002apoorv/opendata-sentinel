"""
OpenData Sentinel - Database Seeding Script
Populates the SQLite database with bundled Indian Government open datasets
and executes full initial monitoring runs.
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.dataset import Dataset
from backend.app.api.routes import load_all_sample_datasets

def seed():
    print("Initializing database schema...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Registering and monitoring bundled Indian Government datasets...")
        res = load_all_sample_datasets(db)
        print(f"Result: {res['message']}")
        for name in res["datasets"]:
            print(f" - Loaded & monitored: {name}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
