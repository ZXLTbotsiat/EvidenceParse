import hashlib
import io
import uuid
from typing import List

from PIL import Image

from evidence_parse.extractors.invoice import InvoiceExtractor
from evidence_parse.extractors.pdf import PdfTextExtractor
from evidence_parse.models import DocumentParseResult, ExtractedValue, SourceKind, ValidationResult


class UnsupportedDocumentError(ValueError):
    pass


class DocumentParser:
    def __init__(self) -> None:
        self.pdf_extractor = PdfTextExtractor()
        self.invoice_extractor = InvoiceExtractor()

    def parse(self, filename: str, content_type: str, content: bytes) -> DocumentParseResult:
        fingerprint = hashlib.sha256(content).hexdigest()
        document_id = str(uuid.uuid4())
        normalized_type = content_type.lower().split(";", 1)[0]

        if normalized_type == "application/pdf" or filename.lower().endswith(".pdf"):
            extraction = self.pdf_extractor.extract(content)
            if extraction.source_kind is SourceKind.SCANNED_PDF:
                return self._ocr_pending_result(
                    document_id,
                    fingerprint,
                    filename,
                    content_type,
                    SourceKind.SCANNED_PDF,
                    len(extraction.pages),
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
            image = Image.open(io.BytesIO(content))
            image.verify()
            return self._ocr_pending_result(
                document_id, fingerprint, filename, content_type, SourceKind.IMAGE, 1
            )

        raise UnsupportedDocumentError("Only PDF, JPG, JPEG, and PNG are supported.")

    def _ocr_pending_result(
        self,
        document_id: str,
        fingerprint: str,
        filename: str,
        content_type: str,
        source_kind: SourceKind,
        page_count: int,
    ) -> DocumentParseResult:
        field_names = ["invoice_number", "invoice_date", "subtotal", "tax", "total"]
        fields = {
            name: ExtractedValue(
                confidence=0,
                review_required=True,
                review_reason="OCR provider is not enabled in the current release.",
            )
            for name in field_names
        }
        validations: List[ValidationResult] = [
            ValidationResult(
                code="invoice.total_arithmetic",
                passed=None,
                message="Unable to verify totals until OCR extraction is available.",
                fields=["subtotal", "tax", "total"],
            )
        ]
        return DocumentParseResult(
            document_id=document_id,
            content_fingerprint=fingerprint,
            filename=filename,
            content_type=content_type,
            source_kind=source_kind,
            page_count=page_count,
            fields=fields,
            validations=validations,
            warnings=["OCR is scheduled for Batch 2; no values were guessed."],
        )
