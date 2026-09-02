import io
from typing import List

import fitz
from PIL import Image, ImageOps

from evidence_parse.ocr.base import PreparedImage


class ImagePreprocessor:
    """Normalize source images without losing their original coordinate space."""

    def __init__(self, minimum_long_edge: int = 1600) -> None:
        self.minimum_long_edge = minimum_long_edge

    def from_bytes(self, content: bytes, page: int = 1) -> PreparedImage:
        with Image.open(io.BytesIO(content)) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
        return self.prepare(image, page, float(image.width), float(image.height))

    def prepare(
        self,
        image: Image.Image,
        page: int,
        source_width: float,
        source_height: float,
    ) -> PreparedImage:
        normalized = ImageOps.autocontrast(image.convert("L")).convert("RGB")
        long_edge = max(normalized.size)
        if long_edge < self.minimum_long_edge:
            scale = self.minimum_long_edge / long_edge
            normalized = normalized.resize(
                (round(normalized.width * scale), round(normalized.height * scale)),
                Image.Resampling.LANCZOS,
            )
        return PreparedImage(page, normalized, source_width, source_height)


class ScannedPdfRenderer:
    """Render image-only PDF pages for OCR while retaining PDF point coordinates."""

    def __init__(self, preprocessor: ImagePreprocessor, scale: float = 2.0) -> None:
        self.preprocessor = preprocessor
        self.scale = scale

    def render(self, content: bytes) -> List[PreparedImage]:
        document = fitz.open(stream=content, filetype="pdf")
        pages: List[PreparedImage] = []
        try:
            for index, page in enumerate(document):
                pixmap = page.get_pixmap(matrix=fitz.Matrix(self.scale, self.scale), alpha=False)
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                pages.append(
                    self.preprocessor.prepare(
                        image=image,
                        page=index + 1,
                        source_width=float(page.rect.width),
                        source_height=float(page.rect.height),
                    )
                )
        finally:
            document.close()
        return pages
