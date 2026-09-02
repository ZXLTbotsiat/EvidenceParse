from evidence_parse.extractors.invoice import InvoiceExtractor
from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import BoundingBox, PageContent
from evidence_parse.validators import InvoiceValidator


def test_extracts_invoice_fields_with_evidence_and_validates_total() -> None:
    text = """INVOICE
Invoice No: INV-2026-0042
Date: 2026-09-02
Subtotal: 100.00
Tax: 18.00
Total: 118.00
"""
    page = PageContent(page=1, width=595, height=842, text=text)
    span = TextSpan(
        page=1,
        text=text,
        bbox=BoundingBox(x0=40, y0=40, x1=300, y1=220),
    )

    fields = InvoiceExtractor().extract([page], [span])
    validations = InvoiceValidator().validate(fields, [])

    assert fields["invoice_number"].value == "INV-2026-0042"
    assert fields["invoice_number"].evidence[0].page == 1
    assert fields["invoice_date"].value == "2026-09-02"
    assert fields["total"].value == "118.00"
    assert "Subtotal" in fields["subtotal"].evidence[0].text
    assert validations[0].passed is True


def test_missing_values_are_not_invented() -> None:
    page = PageContent(page=1, width=595, height=842, text="Invoice No: A-1")
    fields = InvoiceExtractor().extract([page], [])
    validations = InvoiceValidator().validate(fields, [])

    assert fields["total"].value is None
    assert fields["total"].review_required is True
    assert validations[0].passed is None


def test_low_ocr_confidence_requires_human_review() -> None:
    text = "Invoice No: LOW-01"
    page = PageContent(page=1, width=500, height=700, text=text)
    span = TextSpan(
        page=1,
        text=text,
        bbox=BoundingBox(x0=20, y0=30, x1=180, y1=50),
        confidence=0.6,
    )

    fields = InvoiceExtractor().extract([page], [span])

    invoice_number = fields["invoice_number"]
    assert invoice_number.value == "LOW-01"
    assert invoice_number.confidence == 0.552
    assert invoice_number.review_required is True
    assert "below" in invoice_number.review_reason
