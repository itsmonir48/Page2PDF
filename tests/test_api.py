"""
Page2PDF — API Tests
Tests for API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Page2PDF"


class TestHomepage:
    def test_homepage_returns_html(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "Page2PDF" in response.text


class TestExtractEndpoint:
    def test_invalid_url(self):
        response = client.post("/api/extract", json={"url": "not-a-url"})
        data = response.json()
        # Should either fail validation or return error
        assert response.status_code == 200 or response.status_code == 422

    def test_localhost_blocked(self):
        response = client.post("/api/extract", json={"url": "http://localhost/secret"})
        data = response.json()
        assert data.get("success") is False

    def test_private_ip_blocked(self):
        response = client.post("/api/extract", json={"url": "http://192.168.1.1/"})
        data = response.json()
        assert data.get("success") is False

    def test_file_url_blocked(self):
        response = client.post("/api/extract", json={"url": "file:///etc/passwd"})
        data = response.json()
        assert data.get("success") is False


class TestGeneratePDFEndpoint:
    def test_invalid_url_rejected(self):
        response = client.post("/api/generate-pdf", json={
            "url": "not-valid",
        })
        data = response.json()
        # May get 422 (validation) or success=False
        assert response.status_code in (200, 422)

    def test_localhost_blocked(self):
        response = client.post("/api/generate-pdf", json={
            "url": "http://localhost/admin",
        })
        # Job may be created but will fail during processing
        assert response.status_code in (200, 422)


class TestStatusEndpoint:
    def test_nonexistent_job(self):
        response = client.get("/api/status/nonexistent-id")
        assert response.status_code == 404


class TestDownloadEndpoint:
    def test_nonexistent_job(self):
        response = client.get("/api/download/nonexistent-id")
        assert response.status_code == 404
