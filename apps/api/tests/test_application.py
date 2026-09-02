from unittest.mock import Mock

import fitz

from evidence_parse.application import DocumentApplicationService
from evidence_parse.persistence import DuplicateDocumentRaceError
from evidence_parse.schemas import InvoiceSchema, SchemaRegistry
from evidence_parse.service import DocumentParser


def _invoice_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Invoice No: RACE-001\nDate: 2026-09-02\nSubtotal: 100.00\nTax: 18.00\nTotal: 118.00",
    )
    content = document.tobytes(no_new_id=True)
    document.close()
    return content


def test_duplicate_race_returns_current_upload_metadata() -> None:
    schemas = SchemaRegistry([InvoiceSchema()])
    parser = DocumentParser(schema_registry=schemas)
    content = _invoice_pdf()
    canonical = parser.parse("first.pdf", "application/pdf", content)
    duplicate = canonical.model_copy(deep=True)
    duplicate.duplicate.is_duplicate = True
    duplicate.duplicate.canonical_document_id = canonical.document_id
    duplicate.duplicate.occurrences = 2

    repository = Mock()
    repository.find_by_fingerprint.side_effect = [None, canonical]
    repository.create.side_effect = DuplicateDocumentRaceError(
        canonical.content_fingerprint
    )
    repository.record_duplicate_upload.return_value = duplicate
    service = DocumentApplicationService(parser, repository, schemas)

    result = service.parse_and_store(
        "second-name.pdf", "application/x-custom-pdf", content, "invoice"
    )

    assert result.document_id == canonical.document_id
    assert result.filename == "second-name.pdf"
    assert result.content_type == "application/x-custom-pdf"
    repository.record_duplicate_upload.assert_called_once_with(
        canonical.document_id, "second-name.pdf", "application/x-custom-pdf"
    )
