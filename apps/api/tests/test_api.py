import fitz
from fastapi.testclient import TestClient

from evidence_parse.main import app

client = TestClient(app)


def _invoice_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Invoice No: DEMO-1001\nDate: 2026-09-02\nSubtotal: 200.00\nTax: 36.00\nTotal: 236.00",
    )
    return document.tobytes()


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_parse_digital_pdf() -> None:
    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("invoice.pdf", _invoice_pdf(), "application/pdf")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_kind"] == "digital_pdf"
    assert payload["fields"]["invoice_number"]["value"] == "DEMO-1001"
    assert "Subtotal" in payload["fields"]["subtotal"]["evidence"][0]["text"]
    assert payload["validations"][0]["passed"] is True
    assert len(payload["content_fingerprint"]) == 64


def test_rejects_unknown_type() -> None:
    response = client.post(
        "/api/v1/documents/parse",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415
