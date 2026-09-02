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

    def source_bbox(self, points: Sequence[Sequence[float]]) -> BoundingBox:
        """Map an OCR quadrilateral back to source-document coordinates."""
        coordinates = list(points)
        x_values = [float(point[0]) for point in coordinates]
        y_values = [float(point[1]) for point in coordinates]
        scale_x = self.source_width / self.image.width
        scale_y = self.source_height / self.image.height
        return BoundingBox(
            x0=round(min(x_values) * scale_x, 2),
            y0=round(min(y_values) * scale_y, 2),
            x1=round(max(x_values) * scale_x, 2),
            y1=round(max(y_values) * scale_y, 2),
        )


class OcrProvider(Protocol):
    """Replaceable boundary for OCR engines."""

    def extract(self, pages: List[PreparedImage]) -> Tuple[List[PageContent], List[TextSpan]]:
        """Recognize ordered text spans while preserving source coordinates."""
        ...
