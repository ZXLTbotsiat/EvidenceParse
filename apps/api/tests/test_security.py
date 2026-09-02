import pytest
from fastapi.testclient import TestClient

from evidence_parse.main import create_app
from evidence_parse.settings import Settings


def test_api_key_protects_api_routes_but_not_health(monkeypatch) -> None:
    monkeypatch.setenv("EVIDENCE_PARSE_AUTH_REQUIRED", "true")
    monkeypatch.setenv("EVIDENCE_PARSE_API_KEYS", "first-secret,rotated-secret")
    app = create_app("sqlite+pysqlite:///:memory:", auto_create_schema=True)

    with TestClient(app) as client:
        missing = client.get("/api/v1/documents")
        invalid = client.get("/api/v1/documents", headers={"X-API-Key": "wrong"})
        authorized = client.get(
            "/api/v1/documents", headers={"X-API-Key": "rotated-secret"}
        )
        health = client.get("/health/ready")

    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "ApiKey"
    assert invalid.status_code == 401
    assert authorized.status_code == 200
    assert health.status_code == 200


def test_required_authentication_rejects_an_empty_key_set(monkeypatch) -> None:
    monkeypatch.setenv("EVIDENCE_PARSE_AUTH_REQUIRED", "true")
    monkeypatch.delenv("EVIDENCE_PARSE_API_KEYS", raising=False)

    with pytest.raises(ValueError, match="must contain at least one key"):
        Settings.from_environment()


def test_responses_include_security_and_request_headers(client: TestClient) -> None:
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-request-id"]


def test_openapi_describes_the_api_key_scheme(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()

    security_scheme = schema["components"]["securitySchemes"]["APIKeyHeader"]
    assert security_scheme == {"type": "apiKey", "in": "header", "name": "X-API-Key"}
