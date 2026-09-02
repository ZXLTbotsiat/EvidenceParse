import io
from threading import Lock
from typing import Any, List, Optional, Tuple

from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import PageContent
from evidence_parse.ocr.base import PreparedImage


class RapidOcrProvider:
    """CPU OCR provider backed by RapidOCR and bundled ONNX models."""

    def __init__(self) -> None:
        self._engine: Optional[Any] = None
        self._engine_lock = Lock()
        self._inference_lock = Lock()

    def extract(self, pages: List[PreparedImage]) -> Tuple[List[PageContent], List[TextSpan]]:
        engine = self._get_engine()
        contents: List[PageContent] = []
        spans: List[TextSpan] = []

        for prepared in pages:
            image_bytes = io.BytesIO()
            prepared.image.save(image_bytes, format="PNG")
            with self._inference_lock:
                result = engine(image_bytes.getvalue())
            texts = list(result.txts) if result.txts is not None else []
            boxes = list(result.boxes) if result.boxes is not None else []
            scores = list(result.scores) if result.scores is not None else []
            page_spans = [
                TextSpan(
                    page=prepared.page,
                    text=str(text),
                    bbox=prepared.source_bbox(box),
                    confidence=round(float(score), 4),
                )
                for box, text, score in zip(boxes, texts, scores)
            ]
            spans.extend(page_spans)
            contents.append(
                PageContent(
                    page=prepared.page,
                    width=round(prepared.source_width, 2),
                    height=round(prepared.source_height, 2),
                    text="\n".join(span.text for span in page_spans),
                )
            )

        return contents, spans

    def _get_engine(self) -> Any:
        if self._engine is not None:
            return self._engine
        with self._engine_lock:
            if self._engine is None:
                from rapidocr import RapidOCR

                self._engine = RapidOCR()
        return self._engine
