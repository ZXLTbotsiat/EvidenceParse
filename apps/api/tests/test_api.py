import fitz
from fastapi.testclient import TestClient


def _invoice_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Invoice No: DEMO-1001\nDate: 2026-09-02\nSubtotal: 200.00\nTax: 36.00\nTotal: 236.00",
    )
    return document.tobytes()


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["version"] == "0.7.0"


def test_parse_digital_pdf(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("invoice.pdf", _invoice_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_name"] == "invoice"
    assert payload["source_kind"] == "digital_pdf"
    assert payload["pages"][0]["text"].startswith("Invoice No")
    assert payload["text_blocks"][0]["page"] == 1
    assert payload["text_blocks"][0]["bbox"]["x0"] >= 0
    assert payload["fields"]["invoice_number"]["value"] == "DEMO-1001"
    assert "Subtotal" in payload["fields"]["subtotal"]["evidence"][0]["text"]
    assert payload["validations"][0]["passed"] is True
    assert len(payload["content_fingerprint"]) == 64


def test_generic_ocr_returns_text_without_professional_fields(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/parse",
        data={"schema": "generic"},
        files={"file": ("invoice.pdf", _invoice_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_name"] == "generic"
    assert payload["fields"] == {}
    assert payload["line_items"] == []
    assert payload["validations"] == []
    assert "Invoice No: DEMO-1001" in payload["pages"][0]["text"]
    assert any(block["text"].startswith("Invoice No") for block in payload["text_blocks"])


def test_rejects_unknown_type(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


def test_rejects_unknown_schema(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/parse",
        data={"schema": "receipt"},
        files={"file": ("invoice.pdf", _invoice_pdf(), "application/pdf")},
    )

    assert response.status_code == 400
    assert "Supported schemas: generic, invoice" in response.json()["detail"]
