import hashlib
import uuid
from typing import List, Optional

import fitz
from PIL import UnidentifiedImageError

from evidence_parse.extractors.pdf import PdfTextExtractor, TextSpan
from evidence_parse.models import DocumentParseResult, PageContent, SourceKind
from evidence_parse.ocr import OcrProvider, PreparedImage, RapidOcrProvider
from evidence_parse.ocr.preprocessing import ImagePreprocessor, ScannedPdfRenderer
from evidence_parse.schemas import DocumentSchema, InvoiceSchema, SchemaRegistry


class UnsupportedDocumentError(ValueError):
    pass


class InvalidDocumentError(ValueError):
    pass


class DocumentParser:
    def __init__(
        self,
        ocr_provider: Optional[OcrProvider] = None,
        schema_registry: Optional[SchemaRegistry] = None,
    ) -> None:
        self.pdf_extractor = PdfTextExtractor()
        self.image_preprocessor = ImagePreprocessor()
        self.pdf_renderer = ScannedPdfRenderer(self.image_preprocessor)
        self.ocr_provider = ocr_provider or RapidOcrProvider()
        self.schema_registry = schema_registry or SchemaRegistry([InvoiceSchema()])

    def parse(
        self,
        filename: str,
        content_type: str,
        content: bytes,
        schema_name: str = "invoice",
    ) -> DocumentParseResult:
        fingerprint = hashlib.sha256(content).hexdigest()
        document_id = str(uuid.uuid4())
        normalized_type = content_type.lower().split(";", 1)[0]
        schema = self.schema_registry.get(schema_name)

        if normalized_type == "application/pdf" or filename.lower().endswith(".pdf"):
            try:
                extraction = self.pdf_extractor.extract(content)
            except (fitz.FileDataError, RuntimeError) as exc:
                raise InvalidDocumentError("The PDF could not be parsed.") from exc
            if extraction.source_kind is SourceKind.SCANNED_PDF:
                return self._parse_ocr(
                    document_id,
                    fingerprint,
                    filename,
                    content_type,
                    SourceKind.SCANNED_PDF,
                    self.pdf_renderer.render(content),
                    schema,
                )
            return self._build_result(
                document_id=document_id,
                fingerprint=fingerprint,
                filename=filename,
                content_type=content_type,
                source_kind=extraction.source_kind,
                pages=extraction.pages,
                spans=extraction.spans,
                schema=schema,
            )

        if normalized_type in {"image/jpeg", "image/png"} or filename.lower().endswith(
            (".jpg", ".jpeg", ".png")
        ):
            try:
                prepared_image = self.image_preprocessor.from_bytes(content)
            except (OSError, UnidentifiedImageError) as exc:
                raise InvalidDocumentError("The image could not be parsed.") from exc
            return self._parse_ocr(
                document_id,
                fingerprint,
                filename,
                content_type,
                SourceKind.IMAGE,
                [prepared_image],
                schema,
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
        schema: DocumentSchema,
    ) -> DocumentParseResult:
        pages, spans = self.ocr_provider.extract(prepared_pages)
        result = self._build_result(
            document_id=document_id,
            fingerprint=fingerprint,
            filename=filename,
            content_type=content_type,
            source_kind=source_kind,
            pages=pages,
            spans=spans,
            schema=schema,
        )
        if not spans:
            result.warnings.insert(
                0, "OCR produced no text; all missing values require human review."
            )
        return result

    @staticmethod
    def _build_result(
        document_id: str,
        fingerprint: str,
        filename: str,
        content_type: str,
        source_kind: SourceKind,
        pages: List[PageContent],
        spans: List[TextSpan],
        schema: DocumentSchema,
    ) -> DocumentParseResult:
        extraction = schema.extract(pages, spans)
        return DocumentParseResult(
            document_id=document_id,
            content_fingerprint=fingerprint,
            filename=filename,
            content_type=content_type,
            schema_name=schema.name,
            source_kind=source_kind,
            page_count=len(pages),
            fields=extraction.fields,
            line_items=extraction.line_items,
            validations=extraction.validations,
            warnings=extraction.warnings,
        )
