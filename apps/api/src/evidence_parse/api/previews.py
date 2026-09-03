"""Render source and OCR-input previews without retaining uploaded bytes."""

import io

import fitz
from PIL import Image, ImageOps, UnidentifiedImageError

from evidence_parse.ocr.preprocessing import ImagePreprocessor


class PdfPreviewError(ValueError):
    """Raised when a PDF cannot be rendered for source comparison."""


class OcrPreviewError(ValueError):
    """Raised when a selected OCR recipe cannot be reproduced."""


def render_pdf_page(content: bytes, page_number: int, max_long_edge: int = 1800) -> bytes:
    """Return one PDF page as PNG while preserving its source coordinate ratio."""

    try:
        document = fitz.open(stream=content, filetype="pdf")
    except (fitz.FileDataError, RuntimeError) as exc:
        raise PdfPreviewError("The uploaded file is not a valid PDF.") from exc

    try:
        if page_number < 1 or page_number > document.page_count:
            raise PdfPreviewError(f"PDF page must be between 1 and {document.page_count}.")
        page = document.load_page(page_number - 1)
        long_edge = max(float(page.rect.width), float(page.rect.height), 1.0)
        scale = min(2.0, max_long_edge / long_edge)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pixmap.tobytes("png")
    except PdfPreviewError:
        raise
    except (fitz.FileDataError, RuntimeError) as exc:
        raise PdfPreviewError("The PDF page could not be rendered.") from exc
    finally:
        document.close()


def render_ocr_input(
    content: bytes,
    filename: str,
    page_number: int,
    variant: str,
    rotation_degrees: int,
    deskew_degrees: float,
) -> bytes:
    """Recreate the transient pixels selected by adaptive preprocessing."""

    preprocessor = ImagePreprocessor()
    if filename.lower().endswith(".pdf"):
        try:
            document = fitz.open(stream=content, filetype="pdf")
            if page_number < 1 or page_number > document.page_count:
                raise OcrPreviewError(
                    f"PDF page must be between 1 and {document.page_count}."
                )
            page = document.load_page(page_number - 1)
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            source = preprocessor.prepare(
                image, page_number, float(page.rect.width), float(page.rect.height)
            )
        except OcrPreviewError:
            raise
        except (fitz.FileDataError, RuntimeError) as exc:
            raise OcrPreviewError("The PDF could not be rendered for OCR preview.") from exc
        finally:
            if "document" in locals():
                document.close()
    else:
        if page_number != 1:
            raise OcrPreviewError("Image OCR preview only supports page 1.")
        try:
            with Image.open(io.BytesIO(content)) as uploaded:
                uploaded.load()
                image = ImageOps.exif_transpose(uploaded).convert("RGB")
            source = preprocessor.prepare(
                image, 1, float(image.width), float(image.height)
            )
        except (OSError, UnidentifiedImageError) as exc:
            raise OcrPreviewError("The image could not be rendered for OCR preview.") from exc

    try:
        return preprocessor.render_recipe(
            source, variant, rotation_degrees, deskew_degrees
        )
    except ValueError as exc:
        raise OcrPreviewError(str(exc)) from exc
