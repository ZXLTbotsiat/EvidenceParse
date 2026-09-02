import uuid

import fitz
from fastapi.testclient import TestClient


def _invoice_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        (
            f"Invoice No: BATCH-{uuid.uuid4().hex[:8]}\n"
            "Date: 2026-09-02\n"
            "Subtotal: 100.00\n"
            "Tax: 18.00\n"
            "Total: 118.00"
        ),
    )
    content = document.tobytes(no_new_id=True)
    document.close()
    return content


def test_batch_tracks_completed_and_failed_items(client: TestClient) -> None:
    response = client.post(
        "/api/v1/batches",
        files=[
            ("files", ("invoice.pdf", _invoice_pdf(), "application/pdf")),
            ("files", ("notes.txt", b"unsupported", "text/plain")),
        ],
    )

    assert response.status_code == 202
    batch_id = response.json()["batch_id"]
    batch = client.get(f"/api/v1/batches/{batch_id}").json()

    assert batch["status"] == "partial_failure"
    assert batch["total_items"] == 2
    assert batch["completed_items"] == 1
    assert batch["failed_items"] == 1
    assert batch["items"][0]["status"] == "completed"
    assert batch["items"][0]["document_id"]
    assert batch["items"][1]["status"] == "failed"
    assert "Only PDF" in batch["items"][1]["error"]


def test_batch_reuses_a_canonical_document_for_exact_duplicates(client: TestClient) -> None:
    content = _invoice_pdf()
    response = client.post(
        "/api/v1/batches",
        files=[
            ("files", ("first.pdf", content, "application/pdf")),
            ("files", ("copy.pdf", content, "application/pdf")),
        ],
    )
    batch = client.get(f"/api/v1/batches/{response.json()['batch_id']}").json()

    document_ids = [item["document_id"] for item in batch["items"]]
    assert batch["status"] == "completed"
    assert document_ids[0] == document_ids[1]
    document = client.get(f"/api/v1/documents/{document_ids[0]}").json()
    assert document["duplicate"]["occurrences"] == 2


def test_batch_file_count_is_bounded(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("EVIDENCE_PARSE_MAX_BATCH_FILES", "1")

    response = client.post(
        "/api/v1/batches",
        files=[
            ("files", ("one.pdf", _invoice_pdf(), "application/pdf")),
            ("files", ("two.pdf", _invoice_pdf(), "application/pdf")),
        ],
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "A batch can contain at most 1 files."


def test_unknown_batch_returns_not_found(client: TestClient) -> None:
    response = client.get(f"/api/v1/batches/{uuid.uuid4()}")

    assert response.status_code == 404
