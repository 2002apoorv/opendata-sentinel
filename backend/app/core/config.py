import os
from pathlib import Path
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"

# Ensure data directories exist
DATA_DIR.mkdir(exist_ok=True)
SAMPLE_DATA_DIR.mkdir(exist_ok=True)
RAW_DATA_DIR.mkdir(exist_ok=True)
PROCESSED_DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseModel):
    PROJECT_NAME: str = "OpenData Sentinel"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = f"sqlite:///{DATA_DIR / 'sentinel.db'}"
    MAX_UPLOAD_SIZE_MB: int = 50
    REQUEST_TIMEOUT_SECONDS: int = 15
    MAX_DOWNLOAD_SIZE_BYTES: int = 50 * 1024 * 1024  # 50MB
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = DATA_DIR
    SAMPLE_DATA_DIR: Path = SAMPLE_DATA_DIR
    RAW_DATA_DIR: Path = RAW_DATA_DIR
    PROCESSED_DATA_DIR: Path = PROCESSED_DATA_DIR
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


settings = Settings()
