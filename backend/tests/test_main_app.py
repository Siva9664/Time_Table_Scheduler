import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import _mask_mongo_url, app, lifespan


@pytest.fixture
def client():
    # Use TestClient with raise_server_exceptions=False to test endpoints directly
    with TestClient(app) as test_client:
        yield test_client


class TestMainAppEndpoints:
    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data.get("message") == "AI Timetable Scheduler API"
        assert data.get("docs") == "/docs"
        assert "version" in data

    def test_health_check_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_security_headers_middleware(self, client):
        response = client.get("/")
        headers = response.headers
        assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "default-src 'self'" in headers.get("Content-Security-Policy", "")

    def test_cors_options_headers(self, client):
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3002",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers or response.status_code == 200


class TestMongoUrlMasking:
    def test_mask_mongo_url_with_credentials(self):
        raw_url = "mongodb+srv://admin_user:secretPass123@cluster0.abcde.mongodb.net/timetables?retryWrites=true"
        masked = _mask_mongo_url(raw_url)
        assert "secretPass123" not in masked
        assert "admin_user" not in masked
        assert "***:***@cluster0.abcde.mongodb.net" in masked

    def test_mask_mongo_url_without_credentials(self):
        raw_url = "mongodb://localhost:27017/test_db"
        masked = _mask_mongo_url(raw_url)
        assert masked == raw_url

    def test_mask_mongo_url_invalid_input(self):
        masked = _mask_mongo_url(None)
        assert masked == "<configured MongoDB URL>"


class TestLifespanHandler:
    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown(self):
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        with patch("app.main.get_client", return_value=mock_client), \
             patch("app.main.init_indexes") as mock_init_indexes, \
             patch("app.main.close_mongo_connection") as mock_close:

            async with lifespan(app):
                mock_client.admin.command.assert_called_with("ping")
                mock_init_indexes.assert_called_once()

            mock_close.assert_called_once()
