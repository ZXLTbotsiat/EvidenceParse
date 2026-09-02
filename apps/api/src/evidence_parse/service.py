import hashlib
import uuid
from typing import List, Optional

from evidence_parse.extractors.invoice import InvoiceExtractor
from evidence_parse.extractors.pdf import PdfTextExtractor
from evidence_parse.models import DocumentParseResult, SourceKind
from evidence_parse.ocr import OcrProvider, PreparedImage, RapidOcrProvider
from evidence_parse.ocr.preprocessing import ImagePreprocessor, ScannedPdfRenderer


class UnsupportedDocumentError(ValueError):
    pass


class DocumentParser:
    def __init__(self, ocr_provider: Optional[OcrProvider] = None) -> None:
        self.pdf_extractor = PdfTextExtractor()
        self.invoice_extractor = InvoiceExtractor()
        self.image_preprocessor = ImagePreprocessor()
        self.pdf_renderer = ScannedPdfRenderer(self.image_preprocessor)
        self.ocr_provider = ocr_provider or RapidOcrProvider()

    def parse(self, filename: str, content_type: str, content: bytes) -> DocumentParseResult:
        fingerprint = hashlib.sha256(content).hexdigest()
        document_id = str(uuid.uuid4())
        normalized_type = content_type.lower().split(";", 1)[0]

        if normalized_type == "application/pdf" or filename.lower().endswith(".pdf"):
            extraction = self.pdf_extractor.extract(content)
            if extraction.source_kind is SourceKind.SCANNED_PDF:
                return self._parse_ocr(
                    document_id,
                    fingerprint,
                    filename,
                    content_type,
                    SourceKind.SCANNED_PDF,
                    self.pdf_renderer.render(content),
                )
            fields, validations = self.invoice_extractor.extract(extraction.pages, extraction.spans)
            return DocumentParseResult(
                document_id=document_id,
                content_fingerprint=fingerprint,
                filename=filename,
                content_type=content_type,
                source_kind=extraction.source_kind,
                page_count=len(extraction.pages),
                fields=fields,
                validations=validations,
            )

        if normalized_type in {"image/jpeg", "image/png"} or filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            return self._parse_ocr(
                document_id,
                fingerprint,
                filename,
                content_type,
                SourceKind.IMAGE,
                [self.image_preprocessor.from_bytes(content)],
            )

        raise UnsupportedDocumentError("Only PDF, JPG, JPEG, and PNG are supported.")

    def _parse_ocr(
        self,
        document_id: str,
        fingerprint: str,
        filename: str,
        content_type: str,
        source_kind: SourceKind,
        prepared_pages: List[PreparedImage],
    ) -> DocumentParseResult:
        pages, spans = self.ocr_provider.extract(prepared_pages)
        fields, validations = self.invoice_extractor.extract(pages, spans)
        warnings = []
        if not spans:
            warnings.append("OCR produced no text; all missing values require human review.")
        return DocumentParseResult(
            document_id=document_id,
            content_fingerprint=fingerprint,
            filename=filename,
            content_type=content_type,
            source_kind=source_kind,
            page_count=len(pages),
            fields=fields,
            validations=validations,
            warnings=warnings,
        )
