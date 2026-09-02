from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import BoundingBox, PageContent
from evidence_parse.schemas.invoice import InvoiceSchema


def _extract(text: str):
    page = PageContent(page=1, width=595, height=842, text=text)
    span = TextSpan(
        page=1,
        text=text,
        bbox=BoundingBox(x0=40, y0=40, x1=550, y1=400),
    )
    return InvoiceSchema().extract([page], [span])


def test_extracts_multiple_rows_from_a_whitespace_table() -> None:
    result = _extract(
        """Invoice No: TABLE-01
Date: 2026-09-02
Description          Quantity     Unit Price     Amount
Document scanner     1            120.00         120.00
Archive service      2            40.00          80.00
Subtotal: 200.00
Tax: 36.00
Total: 236.00"""
    )

    assert len(result.line_items) == 2
    assert result.line_items[0].description.value == "Document scanner"
    assert "Document scanner" in result.line_items[0].description.evidence[0].text
    assert result.line_items[1].quantity.value == "2"
    assert result.line_items[1].amount.value == "80.00"
    assert all(validation.passed is True for validation in result.validations)


def test_extracts_a_pipe_delimited_table() -> None:
    result = _extract(
        """Invoice No: PIPE-01
Date: 2026-09-02
Item | Qty | Unit Price | Amount
Security camera | 2 | 75.00 | 150.00
Setup service | 1 | 50.00 | 50.00
Subtotal: 200.00
Tax: 36.00
Total: 236.00"""
    )

    assert [item.description.value for item in result.line_items] == [
        "Security camera",
        "Setup service",
    ]
    assert result.line_items[0].unit_price.value == "75.00"
    assert result.validations[-1].code == "invoice.line_items_subtotal"
    assert result.validations[-1].passed is True


def test_extracts_a_vertical_labeled_item_without_guessing_missing_values() -> None:
    result = _extract(
        """Invoice No: LABEL-01
Date: 2026-09-02
Description: Evidence review
Quantity: 1
Unit Price: 200.00
Line Amount: 200.00
Subtotal: 200.00
Tax: 36.00
Total: 236.00"""
    )

    item = result.line_items[0]
    assert item.description.value == "Evidence review"
    assert item.tax_rate is None
    assert result.validations[1].passed is True
    assert result.validations[2].passed is True


def test_reports_a_line_item_amount_mismatch() -> None:
    result = _extract(
        """Invoice No: BAD-LINE-01
Date: 2026-09-02
Item | Qty | Unit Price | Amount
Evidence review | 2 | 75.00 | 140.00
Subtotal: 140.00
Tax: 25.20
Total: 165.20"""
    )

    assert result.validations[1].code == "invoice.line_item.1.arithmetic"
    assert result.validations[1].passed is False
    assert "10.00" in result.validations[1].message
