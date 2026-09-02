import io
from typing import List, Tuple

from PIL import Image

from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import BoundingBox, PageContent
from evidence_parse.ocr import PreparedImage
from evidence_parse.service import DocumentParser


class StubOcrProvider:
    def extract(self, pages: List[PreparedImage]) -> Tuple[List[PageContent], List[TextSpan]]:
        page = pages[0]
        text = "Invoice No: STUB-01\nSubtotal: 10.00\nTax: 2.00\nTotal: 12.00"
        return (
            [
                PageContent(
                    page=page.page,
                    width=page.source_width,
                    height=page.source_height,
                    text=text,
                )
            ],
            [
                TextSpan(
                    page=page.page,
                    text=text,
                    bbox=BoundingBox(x0=5, y0=5, x1=95, y1=95),
                    confidence=0.99,
                )
            ],
        )


def _png_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (100, 100), "white").save(output, format="PNG")
    return output.getvalue()


def test_document_parser_accepts_a_replaceable_ocr_provider() -> None:
    result = DocumentParser(ocr_provider=StubOcrProvider()).parse(
        filename="invoice.png",
        content_type="image/png",
        content=_png_bytes(),
    )

    assert result.fields["invoice_number"].value == "STUB-01"
    assert result.fields["total"].value == "12.00"
    assert result.fields["total"].review_required is False
    assert result.validations[0].passed is True


def test_prepared_image_maps_ocr_coordinates_to_the_source() -> None:
    prepared = PreparedImage(
        page=2,
        image=Image.new("RGB", (200, 400), "white"),
        source_width=100,
        source_height=200,
    )

    bbox = prepared.source_bbox(((20, 40), (100, 40), (100, 80), (20, 80)))

    assert bbox == BoundingBox(x0=10, y0=20, x1=50, y1=40)
