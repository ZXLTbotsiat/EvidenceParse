import json

import httpx
import pytest

from evidence_parse_sdk import EvidenceParseClient, EvidenceParseError


def test_client_sends_api_key_and_query_parameters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-API-Key"] == "test-key"
        assert request.url.params["review_status"] == "pending"
        return httpx.Response(200, json={"items": [], "total": 0})

    with EvidenceParseClient(
        "https://example.test",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.list_documents(review_status="pending")

    assert result["total"] == 0


def test_client_builds_review_correction_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/v1/documents/doc-1/corrections"
        assert payload["field_path"] == "fields.total"
        assert payload["expected_revision"] == 2
        return httpx.Response(200, json={"review": {"revision": 3}})

    with EvidenceParseClient(
        "https://example.test", transport=httpx.MockTransport(handler)
    ) as client:
        result = client.correct_field(
            "doc-1",
            "fields.total",
            "118.00",
            "Verified arithmetic.",
            "reviewer",
            2,
        )

    assert result["review"]["revision"] == 3


def test_client_exposes_api_errors() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(409, json={"detail": "Revision conflict."})
    )

    with EvidenceParseClient("https://example.test", transport=transport) as client:
        with pytest.raises(EvidenceParseError) as captured:
            client.get_document("doc-1")

    assert captured.value.status_code == 409
    assert captured.value.detail == "Revision conflict."


def test_client_builds_multipart_parse_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        content_type = request.headers["content-type"]
        assert content_type.startswith("multipart/form-data;")
        assert b'invoice.pdf' in request.content
        assert b'Invoice No: SDK-1' in request.content
        return httpx.Response(200, json={"document_id": "doc-1"})

    with EvidenceParseClient(
        "https://example.test", transport=httpx.MockTransport(handler)
    ) as client:
        result = client.parse_bytes(
            "invoice.pdf",
            b"Invoice No: SDK-1",
            "application/pdf",
        )

    assert result["document_id"] == "doc-1"
