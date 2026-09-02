"""OCR provider contracts and implementations."""

from evidence_parse.ocr.base import OcrProvider, PreparedImage
from evidence_parse.ocr.rapidocr_provider import RapidOcrProvider

__all__ = ["OcrProvider", "PreparedImage", "RapidOcrProvider"]
