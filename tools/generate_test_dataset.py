"""Generate the public, synthetic regression corpus for EvidenceParse.

The generated documents are committed so contributors can run the test suite
without first installing dataset tooling. Re-running this script replaces only
the source and expectation paths defined by the case catalog below.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = ROOT / "datasets"
SOURCE_ROOT = DATASET_ROOT / "synthetic"
EXPECTED_ROOT = DATASET_ROOT / "expected"


@dataclass(frozen=True)
class DatasetCase:
    """One generated document and its observable API contract."""

    case_id: str
    description: str
    source: str
    content_type: str
    tags: tuple[str, ...]
    build: Callable[[Path], None]
    expected: dict[str, Any]


def _add_text_page(document: fitz.Document, lines: list[str]) -> None:
    page = document.new_page(width=595, height=842)
    y = 64
    for line in lines:
        page.insert_text((56, y), line, fontsize=11)
        y += 24


def _write_pdf(path: Path, pages: list[list[str]]) -> None:
    document = fitz.open()
    for lines in pages:
        _add_text_page(document, lines)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path, no_new_id=True)
    document.close()


def _invoice_lines(
    *,
    invoice_number: str = "SYN-2026-0001",
    subtotal: str = "200.00",
    tax: str = "36.00",
    total: str = "236.00",
) -> list[str]:
    return [
        "SYNTHETIC INVOICE - NOT FOR PAYMENT",
        f"Invoice No: {invoice_number}",
        "Date: 2026-09-02",
        "Description: Document scanner",
        "Quantity: 1",
        "Unit Price: 200.00",
        f"Subtotal: {subtotal}",
        f"Tax: {tax}",
        f"Total: {total}",
        "No customer or personal data is present.",
    ]


def _write_standard_pdf(path: Path) -> None:
    _write_pdf(path, [_invoice_lines()])


def _write_missing_fields_pdf(path: Path) -> None:
    _write_pdf(
        path,
        [["SYNTHETIC INVOICE", "Invoice No: SYN-MISSING-01", "Date: 2026-09-02"]],
    )


def _write_amount_mismatch_pdf(path: Path) -> None:
    _write_pdf(path, [_invoice_lines(invoice_number="SYN-MISMATCH-01", total="250.00")])


def _write_repeated_amounts_pdf(path: Path) -> None:
    _write_pdf(path, [_invoice_lines(invoice_number="SYN-REPEAT-01")])


def _write_multi_page_pdf(path: Path) -> None:
    first_page = [
        "SYNTHETIC INVOICE - PAGE 1 OF 2",
        "Invoice No: SYN-MULTI-01",
        "Date: 2026-09-02",
        "Description: Document scanner",
        "Amount: 200.00",
    ]
    second_page = [
        "SYNTHETIC INVOICE - PAGE 2 OF 2",
        "Subtotal: 200.00",
        "Tax: 36.00",
        "Total: 236.00",
    ]
    _write_pdf(path, [first_page, second_page])


def _invoice_image() -> Image.Image:
    image = Image.new("RGB", (1000, 1400), "white")
    draw = ImageDraw.Draw(image)
    y = 80
    for line in _invoice_lines(invoice_number="SYN-IMAGE-01"):
        draw.text((80, y), line, fill="black")
        y += 70
    return image


def _write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _invoice_image().save(path, format="PNG")


def _write_jpeg(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _invoice_image().save(path, format="JPEG", quality=90)


def _write_scanned_pdf(path: Path) -> None:
    image = _invoice_image()
    image_bytes = _image_bytes(image, "JPEG")
    document = fitz.open()
    page = document.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=image_bytes)
    path.parent.mkdir(parents=True, exist_ok=True)
    document.save(path, no_new_id=True)
    document.close()


def _image_bytes(image: Image.Image, image_format: str) -> bytes:
    import io

    output = io.BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


def _write_text(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"Synthetic unsupported fixture.\n")


def _write_corrupt_pdf(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"%PDF-1.7\nThis is intentionally not a valid PDF.\n%%EOF\n")


def _success_expectation(**body: Any) -> dict[str, Any]:
    return {"status_code": 200, "body": body}


CASES = (
    DatasetCase(
        "digital-standard",
        "Single-page digital PDF with reconciling totals.",
        "synthetic/invoices/digital-pdf/standard-invoice.pdf",
        "application/pdf",
        ("invoice", "digital-pdf", "happy-path"),
        _write_standard_pdf,
        _success_expectation(
            source_kind="digital_pdf",
            page_count=1,
            **{
                "fields.invoice_number.value": "SYN-2026-0001",
                "fields.subtotal.value": "200.00",
                "fields.total.value": "236.00",
                "validations.0.passed": True,
            },
        ),
    ),
    DatasetCase(
        "digital-missing-fields",
        "Digital PDF with no monetary fields; missing values must remain null.",
        "synthetic/invoices/digital-pdf/missing-fields.pdf",
        "application/pdf",
        ("invoice", "digital-pdf", "missing-data"),
        _write_missing_fields_pdf,
        _success_expectation(
            source_kind="digital_pdf",
            **{
                "fields.invoice_number.value": "SYN-MISSING-01",
                "fields.total.value": None,
                "fields.total.review_required": True,
                "validations.0.passed": None,
            },
        ),
    ),
    DatasetCase(
        "digital-amount-mismatch",
        "Digital PDF whose subtotal and tax do not reconcile with total.",
        "synthetic/invoices/digital-pdf/amount-mismatch.pdf",
        "application/pdf",
        ("invoice", "digital-pdf", "validation"),
        _write_amount_mismatch_pdf,
        _success_expectation(
            source_kind="digital_pdf",
            **{"fields.total.value": "250.00", "validations.0.passed": False},
        ),
    ),
    DatasetCase(
        "digital-repeated-amounts",
        "The same amount appears as unit price and subtotal; evidence must retain its label.",
        "synthetic/invoices/digital-pdf/repeated-amounts.pdf",
        "application/pdf",
        ("invoice", "digital-pdf", "evidence"),
        _write_repeated_amounts_pdf,
        _success_expectation(
            source_kind="digital_pdf",
            **{
                "fields.subtotal.value": "200.00",
                "fields.subtotal.evidence.0.text_contains": "Subtotal: 200.00",
            },
        ),
    ),
    DatasetCase(
        "digital-multi-page",
        "Two-page invoice with totals on the second page.",
        "synthetic/invoices/digital-pdf/multi-page.pdf",
        "application/pdf",
        ("invoice", "digital-pdf", "multi-page"),
        _write_multi_page_pdf,
        _success_expectation(
            source_kind="digital_pdf",
            page_count=2,
            **{
                "fields.total.value": "236.00",
                "fields.total.evidence.0.page": 2,
                "validations.0.passed": True,
            },
        ),
    ),
    DatasetCase(
        "scanned-pdf",
        "Image-only PDF that must be routed to OCR and human review.",
        "synthetic/invoices/scanned-pdf/scanned-invoice.pdf",
        "application/pdf",
        ("invoice", "scanned-pdf", "ocr-pending"),
        _write_scanned_pdf,
        _success_expectation(
            source_kind="scanned_pdf",
            **{
                "fields.total.value": None,
                "fields.total.review_required": True,
                "validations.0.passed": None,
            },
        ),
    ),
    DatasetCase(
        "image-png",
        "PNG invoice routed to OCR and human review.",
        "synthetic/invoices/images/invoice.png",
        "image/png",
        ("invoice", "png", "ocr-pending"),
        _write_png,
        _success_expectation(
            source_kind="image",
            **{"fields.total.value": None, "fields.total.review_required": True},
        ),
    ),
    DatasetCase(
        "image-jpeg",
        "JPEG invoice routed to OCR and human review.",
        "synthetic/invoices/images/invoice.jpg",
        "image/jpeg",
        ("invoice", "jpeg", "ocr-pending"),
        _write_jpeg,
        _success_expectation(
            source_kind="image",
            **{"fields.total.value": None, "fields.total.review_required": True},
        ),
    ),
    DatasetCase(
        "unsupported-file",
        "A valid but unsupported text file.",
        "synthetic/invalid/unsupported.txt",
        "text/plain",
        ("negative", "unsupported"),
        _write_text,
        {"status_code": 415, "body": {"detail": "Only PDF, JPG, JPEG, and PNG are supported."}},
    ),
    DatasetCase(
        "corrupt-pdf",
        "A PDF-like payload that cannot be parsed.",
        "synthetic/invalid/corrupt.pdf",
        "application/pdf",
        ("negative", "corrupt"),
        _write_corrupt_pdf,
        {"status_code": 422, "body": {"detail": "The document could not be parsed."}},
    ),
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.write_bytes(content.encode("utf-8"))


def main() -> None:
    manifest_cases = []
    for case in CASES:
        source_path = DATASET_ROOT / case.source
        case.build(source_path)
        expected_path = EXPECTED_ROOT / f"{case.case_id}.json"
        _write_json(expected_path, case.expected)
        manifest_cases.append(
            {
                "id": case.case_id,
                "description": case.description,
                "source": case.source,
                "content_type": case.content_type,
                "expected": expected_path.relative_to(DATASET_ROOT).as_posix(),
                "tags": list(case.tags),
            }
        )

    _write_json(
        DATASET_ROOT / "manifest.json",
        {
            "name": "EvidenceParse synthetic invoice regression corpus",
            "version": 1,
            "license": "MIT",
            "contains_real_personal_data": False,
            "cases": manifest_cases,
        },
    )
    print(f"Generated {len(CASES)} cases in {DATASET_ROOT}")


if __name__ == "__main__":
    main()
