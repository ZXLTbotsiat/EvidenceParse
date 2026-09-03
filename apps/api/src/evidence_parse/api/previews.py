"""Render review-safe PDF page previews without retaining uploaded bytes."""

import fitz


class PdfPreviewError(ValueError):
    """Raised when a PDF cannot be rendered for source comparison."""


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
