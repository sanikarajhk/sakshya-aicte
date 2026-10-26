"""
Sakshya Test Suite: FastAPI REST Endpoints
Verifies API responses, status codes, and JSON schema compliance.
"""

import pytest
from fastapi.testclient import TestClient
from sakshya.api.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health_check(client):
    """Test health endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_list_applications(client):
    """Test listing applications via REST API."""
    resp = client.get("/api/applications")
    assert resp.status_code == 200
    data = resp.json()
    assert "applications" in data
    assert len(data["applications"]) == 30


def test_get_single_application(client):
    """Test retrieving details of an application."""
    resp = client.get("/api/applications/APP-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["application_id"] == "APP-001"
    assert "documents" in data
    assert "findings" in data


def test_mock_issuer_endpoint(client):
    """Test querying mock issuer via REST API."""
    payload = {
        "document_type": "LAND_TITLE",
        "document_number": "REG-DEED-2021-DL",
        "institution_name": "Vidyapeeth Institute of Technology",
        "issuing_authority": "State Land Revenue Department",
        "additional_params": {"application_id": "APP-001"}
    }
    resp = client.post("/api/mock-issuer/verify", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "verified"
    assert data["matched"] is True


def test_ring_detection_endpoint(client):
    """Test cross-institution ring detection endpoint."""
    resp = client.get("/api/ring-detection")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_applications_analyzed"] == 30
    assert data["detected_clusters_count"] == 1
    assert len(data["clusters"][0]["institutions"]) == 6


def test_audit_verify_endpoint(client):
    """Test audit chain verification endpoint."""
    resp = client.get("/api/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True


def test_upload_and_validate_document_api(client):
    """Test upload and targeted validation endpoint via REST API."""
    from pathlib import Path
    from sakshya.data_generator.ground_truth import load_ground_truth
    gt = load_ground_truth()
    doc_path = Path(gt["APP-001"]["documents"][0]["file_path"])

    with open(doc_path, "rb") as f:
        file_bytes = f.read()

    files = {"file": (doc_path.name, file_bytes, "application/pdf")}
    data = {"target_college_id": "APP-001"}
    resp = client.post("/api/documents/validate-upload", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()
    assert "identification" in res_data
    assert "validation" in res_data
    assert res_data["validation"]["college_id"] == "APP-001"
    assert res_data["validation"]["overall_status"] == "VERIFIED_AUTO"

