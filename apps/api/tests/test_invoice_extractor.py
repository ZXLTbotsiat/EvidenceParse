from evidence_parse.extractors.invoice import InvoiceExtractor
from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import BoundingBox, PageContent


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

    fields, validations = InvoiceExtractor().extract([page], [span])

    assert fields["invoice_number"].value == "INV-2026-0042"
    assert fields["invoice_number"].evidence[0].page == 1
    assert fields["invoice_date"].value == "2026-09-02"
    assert fields["total"].value == "118.00"
    assert "Subtotal" in fields["subtotal"].evidence[0].text
    assert validations[0].passed is True


def test_missing_values_are_not_invented() -> None:
    page = PageContent(page=1, width=595, height=842, text="Invoice No: A-1")
    fields, validations = InvoiceExtractor().extract([page], [])

    assert fields["total"].value is None
    assert fields["total"].review_required is True
    assert validations[0].passed is None
