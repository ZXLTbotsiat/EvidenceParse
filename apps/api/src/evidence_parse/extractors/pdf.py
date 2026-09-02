from dataclasses import dataclass
from typing import List, Optional

import fitz

from evidence_parse.models import BoundingBox, PageContent, SourceKind


@dataclass(frozen=True)
class TextSpan:
    page: int
    text: str
    bbox: BoundingBox
    confidence: float = 1.0


@dataclass(frozen=True)
class PdfExtraction:
    source_kind: SourceKind
    pages: List[PageContent]
    spans: List[TextSpan]


class PdfTextExtractor:
    """Extract a PDF text layer and retain coordinates for evidence lookup."""

    def extract(self, content: bytes) -> PdfExtraction:
        document = fitz.open(stream=content, filetype="pdf")
        pages: List[PageContent] = []
        spans: List[TextSpan] = []

        for page_index, page in enumerate(document):
            page_number = page_index + 1
            text = page.get_text("text").strip()
            pages.append(
                PageContent(
                    page=page_number,
                    width=round(page.rect.width, 2),
                    height=round(page.rect.height, 2),
                    text=text,
                )
            )
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    line_text = "".join(
                        str(span.get("text", "")) for span in line.get("spans", [])
                    ).strip()
                    if not line_text:
                        continue
                    bbox = line["bbox"]
                    spans.append(
                        TextSpan(
                            page=page_number,
                            text=line_text,
                            bbox=BoundingBox(
                                x0=round(float(bbox[0]), 2),
                                y0=round(float(bbox[1]), 2),
                                x1=round(float(bbox[2]), 2),
                                y1=round(float(bbox[3]), 2),
                            ),
                        )
                    )

        visible_characters = sum(len("".join(page.text.split())) for page in pages)
        source_kind = SourceKind.DIGITAL_PDF if visible_characters >= 20 else SourceKind.SCANNED_PDF
        return PdfExtraction(source_kind=source_kind, pages=pages, spans=spans)


def locate_text(value: str, spans: List[TextSpan], page: Optional[int] = None) -> TextSpan:
    normalized = value.casefold().strip()
    for span in spans:
        if page is not None and span.page != page:
            continue
        if normalized and normalized in span.text.casefold():
            return span
    raise LookupError(value)
