import pytest
from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == "OpenData Sentinel"


def test_dashboard_summary_empty(client: TestClient):
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_datasets" in data
    assert "healthy_datasets" in data


def test_sample_datasets_listing(client: TestClient):
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json()
    assert len(samples) >= 4
    sample_names = [s["filename"] for s in samples]
    assert "indian_agri_mandi_prices_clean.csv" in sample_names


def test_ssrf_protection_blocked(client: TestClient):
    # Attempt to register forbidden internal metadata URL
    payload = {
        "name": "Malicious Metadata Probe",
        "publisher": "Attacker",
        "source_url": "http://169.254.169.254/latest/meta-data/",
        "source_type": "url",
        "data_format": "csv",
        "update_cadence": "daily",
    }
    response = client.post("/api/datasets", json=payload)
    assert response.status_code == 400
    assert "blocked" in response.json()["detail"].lower() or "restricted" in response.json()["detail"].lower()


def test_register_and_preview_sample_dataset(client: TestClient):
    # Register bundled sample dataset
    payload = {
        "name": "Test Agricultural Mandi Dataset",
        "publisher": "Ministry of Agriculture",
        "source_url": "indian_agri_mandi_prices_clean.csv",
        "source_type": "sample",
        "data_format": "csv",
        "update_cadence": "daily",
    }
    create_resp = client.post("/api/datasets", json=payload)
    assert create_resp.status_code == 201
    dataset = create_resp.json()
    dataset_id = dataset["id"]

    # Preview data
    preview_resp = client.get(f"/api/datasets/{dataset_id}/preview?page=1&page_size=10")
    assert preview_resp.status_code == 200
    preview_data = preview_resp.json()
    assert preview_data["total_rows"] > 0
    assert len(preview_data["data"]) == 10
    assert "commodity" in preview_data["columns"]

    # Quality report
    quality_resp = client.get(f"/api/datasets/{dataset_id}/quality")
    assert quality_resp.status_code == 200
    quality_data = quality_resp.json()
    assert "overall_score" in quality_data
    assert len(quality_data["checks"]) > 0

    # Anomalies
    anom_resp = client.get(f"/api/datasets/{dataset_id}/anomalies")
    assert anom_resp.status_code == 200

    # AI Diagnostic Brief
    explain_resp = client.post(f"/api/datasets/{dataset_id}/explain")
    assert explain_resp.status_code == 200
    explain_data = explain_resp.json()
    assert "executive_summary" in explain_data
    assert "action_items" in explain_data
