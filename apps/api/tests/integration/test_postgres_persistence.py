import os
import uuid

import fitz
import pytest
from sqlalchemy.engine import make_url

from evidence_parse.application import DocumentApplicationService
from evidence_parse.persistence import Database, DocumentRepository
from evidence_parse.schemas import InvoiceSchema, SchemaRegistry
from evidence_parse.service import DocumentParser


def _invoice_pdf(invoice_number: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        (
            f"Invoice No: {invoice_number}\n"
            "Date: 2026-09-02\n"
            "Subtotal: 100.00\n"
            "Tax: 18.00\n"
            "Total: 118.00"
        ),
    )
    content = document.tobytes(no_new_id=True)
    document.close()
    return content


def test_real_postgres_persists_duplicate_occurrences_and_review_history() -> None:
    database_url = os.getenv("EVIDENCE_PARSE_TEST_POSTGRES_URL")
    if not database_url:
        pytest.skip("A dedicated PostgreSQL test URL was not provided.")
    assert make_url(database_url).get_backend_name() == "postgresql"

    database = Database(database_url)
    schemas = SchemaRegistry([InvoiceSchema()])
    service = DocumentApplicationService(
        DocumentParser(schema_registry=schemas),
        DocumentRepository(database.engine),
        schemas,
    )
    content = _invoice_pdf(f"POSTGRES-{uuid.uuid4().hex}")

    first = service.parse_and_store("postgres.pdf", "application/pdf", content, "invoice")
    duplicate = service.parse_and_store("copy.pdf", "application/pdf", content, "invoice")
    corrected = service.correct_field(
        document_id=first.document_id,
        field_path="fields.total",
        value="118.00",
        reason="PostgreSQL integration verification.",
        reviewer="github-actions",
        expected_revision=0,
    )
    events = service.review_events(first.document_id)

    assert duplicate.duplicate.is_duplicate is True
    assert duplicate.duplicate.occurrences == 2
    assert corrected.review.revision == 1
    assert events[0].event_type == "field_corrected"
    database.dispose()
