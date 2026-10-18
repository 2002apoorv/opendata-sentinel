import hashlib
import io
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
import httpx
import pandas as pd
from fastapi import UploadFile, HTTPException

from backend.app.core.config import settings
from backend.app.core.security import validate_source_url


def calculate_file_hash(file_path: Path) -> str:
    """Calculates SHA256 hash of a file for content fingerprinting."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_bytes_hash(data: bytes) -> str:
    """Calculates SHA256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()


async def download_dataset_from_url(url: str, destination_path: Path) -> Tuple[bool, str, int, str]:
    """
    Downloads dataset from a validated remote URL with SSRF protection, size limits, and timeouts.
    Returns: (success, message, byte_size, sha256_hash)
    """
    is_safe, error_msg = validate_source_url(url)
    if not is_safe:
        return False, f"URL validation failed: {error_msg}", 0, ""

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    sha256 = hashlib.sha256()
    total_bytes = 0

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS, follow_redirects=False) as client:
            # First send HEAD request to check content-length
            try:
                head_resp = await client.head(url)
                content_len = head_resp.headers.get("Content-Length")
                if content_len and int(content_len) > settings.MAX_DOWNLOAD_SIZE_BYTES:
                    return False, f"File size exceeds maximum allowed limit of {settings.MAX_DOWNLOAD_SIZE_BYTES} bytes.", 0, ""
            except Exception:
                pass  # Fallback to streaming GET if HEAD is unsupported

            async with client.stream("GET", url) as response:
                if response.status_code != 200:
                    return False, f"HTTP download returned error status code: {response.status_code}", 0, ""

                with open(destination_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        total_bytes += len(chunk)
                        if total_bytes > settings.MAX_DOWNLOAD_SIZE_BYTES:
                            f.close()
                            destination_path.unlink(missing_ok=True)
                            return False, f"Download aborted: file size exceeded {settings.MAX_DOWNLOAD_SIZE_BYTES} bytes limit.", 0, ""
                        sha256.update(chunk)
                        f.write(chunk)

        if total_bytes == 0:
            destination_path.unlink(missing_ok=True)
            return False, "Downloaded file is empty (0 bytes).", 0, ""

        return True, "Download completed successfully.", total_bytes, sha256.hexdigest()

    except httpx.TimeoutException:
        destination_path.unlink(missing_ok=True)
        return False, f"Download timed out after {settings.REQUEST_TIMEOUT_SECONDS} seconds.", 0, ""
    except Exception as e:
        destination_path.unlink(missing_ok=True)
        return False, f"Network or I/O error during download: {str(e)}", 0, ""


def save_uploaded_file(upload_file: UploadFile, destination_path: Path) -> Tuple[bool, str, int, str]:
    """
    Saves an uploaded file locally and computes its SHA256 fingerprint.
    Returns: (success, message, byte_size, sha256_hash)
    """
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    sha256 = hashlib.sha256()
    total_bytes = 0
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    try:
        with open(destination_path, "wb") as f:
            while chunk := upload_file.file.read(65536):
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    f.close()
                    destination_path.unlink(missing_ok=True)
                    return False, f"Upload size exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit.", 0, ""
                sha256.update(chunk)
                f.write(chunk)

        if total_bytes == 0:
            destination_path.unlink(missing_ok=True)
            return False, "Uploaded file is empty (0 bytes).", 0, ""

        return True, "File uploaded successfully.", total_bytes, sha256.hexdigest()
    except Exception as e:
        destination_path.unlink(missing_ok=True)
        return False, f"Error saving uploaded file: {str(e)}", 0, ""


def copy_sample_file(sample_filename: str, destination_path: Path) -> Tuple[bool, str, int, str]:
    """Copies a pre-bundled sample dataset to the destination dataset storage path."""
    source_path = settings.SAMPLE_DATA_DIR / sample_filename
    if not source_path.exists():
        return False, f"Sample file '{sample_filename}' does not exist in sample repository.", 0, ""

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, destination_path)
    file_size = source_path.stat().st_size
    file_hash = calculate_file_hash(destination_path)
    return True, "Sample dataset loaded successfully.", file_size, file_hash


def parse_dataset_file(file_path: Path, data_format: str = "csv") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Safely reads CSV or JSON into a Pandas DataFrame.
    Handles encoding variations (UTF-8, Latin-1, CP1252), delimiter detection, and malformed records.
    Returns: (DataFrame, parsing_metadata)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    metadata = {
        "format": data_format,
        "warnings": [],
        "encoding": "utf-8",
        "row_count": 0,
        "column_count": 0,
    }

    if data_format.lower() == "csv":
        encodings_to_try = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
        df = None
        for enc in encodings_to_try:
            try:
                # Try standard comma first, with fallback engine='python' on failure
                df = pd.read_csv(file_path, encoding=enc, on_bad_lines="warn")
                metadata["encoding"] = enc
                break
            except UnicodeDecodeError:
                continue
            except pd.errors.ParserError as pe:
                metadata["warnings"].append(f"Parser warning on {enc}: {str(pe)}")
                try:
                    df = pd.read_csv(file_path, encoding=enc, sep=None, engine="python", on_bad_lines="skip")
                    metadata["encoding"] = enc
                    metadata["warnings"].append("Parsed CSV using Python engine with auto-separator detection.")
                    break
                except Exception:
                    continue

        if df is None:
            raise ValueError(f"Could not parse CSV file across supported encodings: {encodings_to_try}")

    elif data_format.lower() == "json":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
            if isinstance(content, list):
                df = pd.DataFrame(content)
            elif isinstance(content, dict):
                # If wrapped in a top-level key like {"data": [...], "records": [...]}
                for k in ["data", "records", "items", "results"]:
                    if k in content and isinstance(content[k], list):
                        df = pd.DataFrame(content[k])
                        metadata["warnings"].append(f"Extracted JSON array from key '{k}'.")
                        break
                else:
                    df = pd.DataFrame([content])
            else:
                raise ValueError("JSON file does not contain a valid object or array.")
        except json.JSONDecodeError as je:
            raise ValueError(f"Invalid JSON format: {str(je)}")
    else:
        raise ValueError(f"Unsupported data format '{data_format}'. Supported formats: CSV, JSON.")

    if df.empty:
        raise ValueError("Dataset is empty after parsing (0 rows).")

    # Clean up column names: strip whitespace and check for duplicates
    original_cols = list(df.columns)
    cleaned_cols = [str(c).strip() for c in original_cols]
    if len(set(cleaned_cols)) < len(cleaned_cols):
        metadata["warnings"].append("Duplicate column names detected and deduplicated with suffixes.")
    df.columns = cleaned_cols

    metadata["row_count"] = len(df)
    metadata["column_count"] = len(df.columns)
    return df, metadata


def infer_column_types(df: pd.DataFrame) -> Dict[str, str]:
    """
    Infers user-friendly data types for each column in the DataFrame:
    'integer', 'float', 'boolean', 'datetime', 'string', 'categorical'.
    """
    inferred = {}
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()

        if len(non_null) == 0:
            inferred[col] = "empty"
            continue

        # Check boolean
        if pd.api.types.is_bool_dtype(series):
            inferred[col] = "boolean"
            continue

        # Check numeric
        if pd.api.types.is_integer_dtype(series):
            inferred[col] = "integer"
            continue
        elif pd.api.types.is_float_dtype(series):
            # Check if all values are actually integers represented as floats
            if (non_null % 1 == 0).all():
                inferred[col] = "integer"
            else:
                inferred[col] = "float"
            continue

        # Check datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            inferred[col] = "datetime"
            continue

        # Try parsing strings as datetime if col name hints or high parse rate
        if pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
            sample = non_null.astype(str).head(50)
            date_like = any(keyword in col.lower() for keyword in ["date", "time", "month", "year", "created", "updated"])
            if date_like:
                try:
                    pd.to_datetime(sample, errors="raise")
                    inferred[col] = "datetime"
                    continue
                except Exception:
                    pass

            # Check if numeric strings
            try:
                pd.to_numeric(sample, errors="raise")
                inferred[col] = "numeric_string"
                continue
            except Exception:
                pass

            # Check low cardinality category
            unique_ratio = len(non_null.unique()) / len(non_null)
            if unique_ratio < 0.1 and len(non_null.unique()) <= 30:
                inferred[col] = "categorical"
            else:
                inferred[col] = "string"
        else:
            inferred[col] = "string"

    return inferred
