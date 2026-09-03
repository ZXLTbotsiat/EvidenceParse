import math
from dataclasses import dataclass
from typing import List, Protocol, Sequence, Tuple

from PIL import Image

from evidence_parse.extractors.pdf import TextSpan
from evidence_parse.models import BoundingBox, PageContent


@dataclass(frozen=True)
class PreparedImage:
    """OCR-ready pixels plus the coordinate system of the source document."""

    page: int
    image: Image.Image
    source_width: float
    source_height: float
    source_pixel_width: float = 0
    source_pixel_height: float = 0
    rotation_degrees: int = 0
    deskew_degrees: float = 0

    def source_bbox(self, points: Sequence[Sequence[float]]) -> BoundingBox:
        """Map an OCR quadrilateral back to source-document coordinates."""
        pixel_width = self.source_pixel_width or self.source_width
        pixel_height = self.source_pixel_height or self.source_height
        oriented_width = pixel_height if self.rotation_degrees in {90, 270} else pixel_width
        oriented_height = pixel_width if self.rotation_degrees in {90, 270} else pixel_height
        scale_x = oriented_width / self.image.width
        scale_y = oriented_height / self.image.height
        coordinates = [
            self._to_source(float(point[0]) * scale_x, float(point[1]) * scale_y)
            for point in points
        ]
        x_values = [point[0] * self.source_width / pixel_width for point in coordinates]
        y_values = [point[1] * self.source_height / pixel_height for point in coordinates]
        return BoundingBox(
            x0=round(max(0, min(self.source_width, min(x_values))), 2),
            y0=round(max(0, min(self.source_height, min(y_values))), 2),
            x1=round(max(0, min(self.source_width, max(x_values))), 2),
            y1=round(max(0, min(self.source_height, max(y_values))), 2),
        )

    def _to_source(self, x: float, y: float) -> Tuple[float, float]:
        """Undo deskew and right-angle rotation for evidence coordinates."""

        pixel_width = self.source_pixel_width or self.source_width
        pixel_height = self.source_pixel_height or self.source_height
        oriented_width = pixel_height if self.rotation_degrees in {90, 270} else pixel_width
        oriented_height = pixel_width if self.rotation_degrees in {90, 270} else pixel_height
        if self.deskew_degrees:
            # Pillow rotates in image coordinates (positive angles move the
            # right-hand side upward). Applying the same signed angle here
            # maps OCR output coordinates back to the pre-deskew source.
            radians = math.radians(self.deskew_degrees)
            center_x, center_y = oriented_width / 2, oriented_height / 2
            offset_x, offset_y = x - center_x, y - center_y
            x = center_x + offset_x * math.cos(radians) - offset_y * math.sin(radians)
            y = center_y + offset_x * math.sin(radians) + offset_y * math.cos(radians)

        rotation = self.rotation_degrees % 360
        if rotation == 90:
            return y, pixel_height - x
        if rotation == 180:
            return pixel_width - x, pixel_height - y
        if rotation == 270:
            return pixel_width - y, x
        return x, y


class OcrProvider(Protocol):
    """Replaceable boundary for OCR engines."""

    def extract(self, pages: List[PreparedImage]) -> Tuple[List[PageContent], List[TextSpan]]:
        """Recognize ordered text spans while preserving source coordinates."""
        ...
