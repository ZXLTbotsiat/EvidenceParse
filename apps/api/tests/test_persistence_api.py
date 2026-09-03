import json
import uuid
from io import BytesIO

import fitz
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw
from sqlalchemy import text


def _invoice_pdf(invoice_number: str, total: str = "236.00") -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        (
            f"Invoice No: {invoice_number}\n"
            "Date: 2026-09-02\n"
            "Subtotal: 200.00\n"
            "Tax: 36.00\n"
            f"Total: {total}"
        ),
    )
    content = document.tobytes(no_new_id=True)
    document.close()
    return content


def _upload(client: TestClient, content: bytes, filename: str = "invoice.pdf"):
    return client.post(
        "/api/v1/documents/parse",
        files={"file": (filename, content, "application/pdf")},
    )


def _image_upload(client: TestClient, content: bytes, filename: str = "invoice.png"):
    return client.post(
        "/api/v1/documents/parse",
        files={"file": (filename, content, "image/png")},
    )


def test_duplicate_upload_reuses_the_canonical_document(client: TestClient) -> None:
    content = _invoice_pdf(f"DUP-{uuid.uuid4().hex[:8]}")

    first = _upload(client, content, "original.pdf").json()
    second_response = _upload(client, content, "renamed-copy.pdf")
    second = second_response.json()

    assert second_response.status_code == 200
    assert second["document_id"] == first["document_id"]
    assert second["filename"] == "renamed-copy.pdf"
    assert second["duplicate"] == {
        "is_duplicate": True,
        "canonical_document_id": first["document_id"],
        "occurrences": 2,
    }

    stored = client.get(f"/api/v1/documents/{first['document_id']}").json()
    assert stored["filename"] == "original.pdf"
    assert stored["duplicate"]["occurrences"] == 2


def test_duplicate_upload_backfills_source_content_for_legacy_record(client: TestClient) -> None:
    content = _invoice_pdf(f"LEGACY-{uuid.uuid4().hex[:8]}")
    first = _upload(client, content).json()
    database = client.app.state.database
    with database.engine.begin() as connection:
        row = connection.execute(
            text("SELECT result_json FROM documents WHERE id = :id"), {"id": first["document_id"]}
        ).scalar_one()
        payload = json.loads(row) if isinstance(row, str) else row
        payload.pop("pages", None)
        payload.pop("text_blocks", None)
        connection.execute(
            text("UPDATE documents SET result_json = :payload WHERE id = :id"),
            {"payload": json.dumps(payload), "id": first["document_id"]},
        )

    duplicate = _upload(client, content, "legacy-copy.pdf").json()

    assert duplicate["pages"]
    assert duplicate["text_blocks"]


def test_duplicate_scan_backfills_preprocessing_without_replacing_results(
    client: TestClient,
) -> None:
    image = Image.new("RGB", (640, 420), "white")
    ImageDraw.Draw(image).text(
        (50, 80), f"LEGACY SCAN {uuid.uuid4().hex[:8]}", fill="black"
    )
    output = BytesIO()
    image.save(output, format="PNG")
    content = output.getvalue()
    first = _image_upload(client, content).json()
    database = client.app.state.database
    with database.engine.begin() as connection:
        row = connection.execute(
            text("SELECT result_json FROM documents WHERE id = :id"),
            {"id": first["document_id"]},
        ).scalar_one()
        payload = json.loads(row) if isinstance(row, str) else row
        payload.pop("preprocessing", None)
        connection.execute(
            text("UPDATE documents SET result_json = :payload WHERE id = :id"),
            {"payload": json.dumps(payload), "id": first["document_id"]},
        )

    duplicate = _image_upload(client, content, "legacy-scan-copy.png").json()

    assert duplicate["preprocessing"]
    assert duplicate["document_id"] == first["document_id"]


def test_duplicate_scan_backfills_candidate_metrics_for_legacy_recipe(
    client: TestClient,
) -> None:
    image = Image.new("RGB", (640, 420), "white")
    ImageDraw.Draw(image).text(
        (50, 80), f"LEGACY CANDIDATES {uuid.uuid4().hex[:8]}", fill="black"
    )
    output = BytesIO()
    image.save(output, format="PNG")
    content = output.getvalue()
    first = _image_upload(client, content).json()
    database = client.app.state.database
    with database.engine.begin() as connection:
        row = connection.execute(
            text("SELECT result_json FROM documents WHERE id = :id"),
            {"id": first["document_id"]},
        ).scalar_one()
        payload = json.loads(row) if isinstance(row, str) else row
        payload["preprocessing"][0].pop("candidates", None)
        connection.execute(
            text("UPDATE documents SET result_json = :payload WHERE id = :id"),
            {"payload": json.dumps(payload), "id": first["document_id"]},
        )

    duplicate = _image_upload(client, content, "legacy-candidates-copy.png").json()

    candidates = duplicate["preprocessing"][0]["candidates"]
    assert [candidate["variant"] for candidate in candidates] == [
        "original",
        "enhanced",
        "binary",
    ]
    assert sum(candidate["selected"] for candidate in candidates) == 1


def test_human_correction_revalidates_and_creates_an_audit_event(
    client: TestClient,
) -> None:
    content = _invoice_pdf(f"REVIEW-{uuid.uuid4().hex[:8]}", total="250.00")
    parsed = _upload(client, content).json()
    assert parsed["validations"][0]["passed"] is False
    assert parsed["review"]["status"] == "pending"
    assert parsed["review"]["unresolved_fields"] == [
        "fields.subtotal",
        "fields.tax",
        "fields.total",
    ]

    correction = client.post(
        f"/api/v1/documents/{parsed['document_id']}/corrections",
        json={
            "field_path": "fields.total",
            "value": "236.00",
            "reason": "Confirmed against the signed invoice.",
            "reviewer": "test-reviewer",
            "expected_revision": 0,
        },
    )
    corrected = correction.json()

    assert correction.status_code == 200
    assert corrected["fields"]["total"]["value"] == "236.00"
    assert corrected["fields"]["total"]["original_value"] == "250.00"
    assert corrected["fields"]["total"]["source"] == "human_corrected"
    assert corrected["fields"]["total"]["reviewed_by"] == "test-reviewer"
    assert corrected["review"]["status"] == "in_review"
    assert corrected["review"]["revision"] == 1
    assert corrected["review"]["unresolved_fields"] == []
    assert corrected["validations"][0]["passed"] is True

    events = client.get(f"/api/v1/documents/{parsed['document_id']}/review-events").json()
    assert len(events) == 1
    assert events[0]["field_path"] == "fields.total"
    assert events[0]["previous_value"] == "250.00"
    assert events[0]["new_value"] == "236.00"


def test_stale_revision_cannot_overwrite_a_newer_review(client: TestClient) -> None:
    content = _invoice_pdf(f"CONFLICT-{uuid.uuid4().hex[:8]}")
    parsed = _upload(client, content).json()
    endpoint = f"/api/v1/documents/{parsed['document_id']}/corrections"
    request = {
        "field_path": "fields.total",
        "value": "236.00",
        "reason": "First review decision.",
        "reviewer": "reviewer-a",
        "expected_revision": 0,
    }

    assert client.post(endpoint, json=request).status_code == 200
    conflict = client.post(endpoint, json={**request, "reviewer": "reviewer-b"})

    assert conflict.status_code == 409


def test_review_approval_requires_all_flagged_fields_to_be_resolved(
    client: TestClient,
) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), f"Invoice No: MISSING-{uuid.uuid4().hex[:8]}")
    content = document.tobytes(no_new_id=True)
    document.close()
    parsed = _upload(client, content).json()

    response = client.post(
        f"/api/v1/documents/{parsed['document_id']}/review",
        json={
            "status": "approved",
            "note": "Attempted approval.",
            "reviewer": "test-reviewer",
            "expected_revision": 0,
        },
    )

    assert parsed["review"]["status"] == "pending"
    assert response.status_code == 400
    assert "fields.invoice_date" in response.json()["detail"]


def test_document_list_supports_review_status_filtering(client: TestClient) -> None:
    response = client.get("/api/v1/documents", params={"review_status": "pending", "limit": 10})
    payload = response.json()

    assert response.status_code == 200
    assert payload["total"] >= 1
    assert payload["limit"] == 10
    assert all(item["review_status"] == "pending" for item in payload["items"])
