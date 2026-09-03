import hashlib
import uuid
from dataclasses import replace
from typing import List, Optional

import fitz
from PIL import UnidentifiedImageError

from evidence_parse.extractors.pdf import PdfTextExtractor, TextSpan
from evidence_parse.models import (
    DocumentParseResult,
    OcrTextBlock,
    PageContent,
    PreprocessingCandidate,
    PreprocessingPage,
    SourceKind,
)
from evidence_parse.ocr import OcrProvider, PreparedImage, RapidOcrProvider
from evidence_parse.ocr.preprocessing import ImageCandidate, ImagePreprocessor, ScannedPdfRenderer
from evidence_parse.schemas import (
    DocumentSchema,
    GenericOcrSchema,
    InvoiceSchema,
    SchemaRegistry,
)


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
        self.schema_registry = schema_registry or SchemaRegistry(
            [GenericOcrSchema(), InvoiceSchema()]
        )

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
        pages: List[PageContent] = []
        spans: List[TextSpan] = []
        preprocessing: List[PreprocessingPage] = []
        for prepared_page in prepared_pages:
            page_contents, page_spans, selected, candidate_metrics = self._recognize_best(
                prepared_page
            )
            pages.extend(page_contents)
            spans.extend(page_spans)
            preprocessing.append(
                PreprocessingPage(
                    page=prepared_page.page,
                    variant=selected.variant,
                    rotation_degrees=selected.prepared.rotation_degrees,
                    deskew_degrees=selected.prepared.deskew_degrees,
                    average_confidence=next(
                        metric.average_confidence
                        for metric in candidate_metrics
                        if metric.selected
                    ),
                    candidate_count=7,
                    candidates=candidate_metrics,
                )
            )
        result = self._build_result(
            document_id=document_id,
            fingerprint=fingerprint,
            filename=filename,
            content_type=content_type,
            source_kind=source_kind,
            pages=pages,
            spans=spans,
            schema=schema,
            preprocessing=preprocessing,
        )
        if not spans:
            result.warnings.insert(
                0, "OCR produced no text; all missing values require human review."
            )
        return result

    def _recognize_best(
        self, source: PreparedImage
    ) -> tuple[
        List[PageContent],
        List[TextSpan],
        ImageCandidate,
        List[PreprocessingCandidate],
    ]:
        """Select orientation and pixels by OCR quality, preserving the original source."""

        orientation_results = []
        for candidate in self.image_preprocessor.orientation_candidates(source):
            # Orientation selection needs boxes in candidate-image coordinates.
            # Source mapping is applied only after the winning orientation is known.
            image = candidate.prepared.image
            scoring_image = replace(
                candidate.prepared,
                source_width=float(image.width),
                source_height=float(image.height),
                source_pixel_width=float(image.width),
                source_pixel_height=float(image.height),
                rotation_degrees=0,
                deskew_degrees=0,
            )
            orientation_results.append(
                (candidate, *self.ocr_provider.extract([scoring_image]))
            )
        best_orientation = max(
            orientation_results,
            key=lambda item: self._orientation_score(item[2]),
        )[0].prepared.rotation_degrees

        candidates = self.image_preprocessor.recognition_candidates(source, best_orientation)
        evaluated = [
            (candidate, *self.ocr_provider.extract([candidate.prepared]))
            for candidate in candidates
        ]
        selected = evaluated[0]
        selected_score = self._recognition_score(selected[2])
        # Keep the least transformed candidate unless another view wins clearly.
        for candidate_result in evaluated[1:]:
            score = self._recognition_score(candidate_result[2])
            if score > selected_score + 0.01:
                selected = candidate_result
                selected_score = score
        candidate, pages, spans = selected
        metrics = [
            self._candidate_metrics(
                evaluated_candidate,
                evaluated_spans,
                selected=evaluated_candidate == candidate,
            )
            for evaluated_candidate, _, evaluated_spans in evaluated
        ]
        return pages, spans, candidate, metrics

    @classmethod
    def _candidate_metrics(
        cls,
        candidate: ImageCandidate,
        spans: List[TextSpan],
        *,
        selected: bool,
    ) -> PreprocessingCandidate:
        character_count = sum(len("".join(span.text.split())) for span in spans)
        average_confidence = (
            sum(span.confidence for span in spans) / len(spans) if spans else 0
        )
        return PreprocessingCandidate(
            variant=candidate.variant,
            rotation_degrees=candidate.prepared.rotation_degrees,
            deskew_degrees=candidate.prepared.deskew_degrees,
            average_confidence=round(average_confidence, 4),
            quality_score=round(cls._recognition_score(spans), 4),
            text_region_count=len(spans),
            character_count=character_count,
            selected=selected,
        )

    @staticmethod
    def _recognition_score(spans: List[TextSpan]) -> float:
        if not spans:
            return 0
        character_count = sum(max(len("".join(span.text.split())), 1) for span in spans)
        confidence = sum(
            span.confidence * max(len("".join(span.text.split())), 1) for span in spans
        ) / character_count
        coverage_bonus = min(character_count / 100, 1) * 0.03
        region_bonus = min(len(spans) / 10, 1) * 0.02
        return confidence + coverage_bonus + region_bonus

    @classmethod
    def _orientation_score(cls, spans: List[TextSpan]) -> float:
        """Prefer confident text arranged as horizontal, top-to-bottom lines."""

        if not spans:
            return 0
        weights = [max(len("".join(span.text.split())), 1) for span in spans]
        horizontal = sum(
            weight
            for span, weight in zip(spans, weights)
            if (span.bbox.x1 - span.bbox.x0) >= (span.bbox.y1 - span.bbox.y0) * 1.4
        ) / sum(weights)
        ordered_pairs = list(zip(spans, spans[1:]))
        reading_order = (
            sum(current.bbox.y0 <= following.bbox.y0 + 2 for current, following in ordered_pairs)
            / len(ordered_pairs)
            if ordered_pairs
            else 1
        )
        return cls._recognition_score(spans) + horizontal * 0.2 + reading_order * 0.05

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
        preprocessing: Optional[List[PreprocessingPage]] = None,
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
            pages=pages,
            text_blocks=[
                OcrTextBlock(
                    page=span.page,
                    text=span.text,
                    bbox=span.bbox,
                    confidence=span.confidence,
                )
                for span in spans
            ],
            preprocessing=preprocessing or [],
            fields=extraction.fields,
            line_items=extraction.line_items,
            validations=extraction.validations,
            warnings=extraction.warnings,
        )
