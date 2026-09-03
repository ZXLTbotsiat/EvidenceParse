import io
from dataclasses import dataclass
from typing import List

import fitz
from PIL import Image, ImageFilter, ImageOps

from evidence_parse.ocr.base import PreparedImage

PREPROCESSING_VARIANTS = ("original", "enhanced", "binary")
RIGHT_ANGLE_ROTATIONS = (0, 90, 180, 270)


@dataclass(frozen=True)
class ImageCandidate:
    """One auditable OCR input plus the recipe needed to reproduce it."""

    prepared: PreparedImage
    variant: str


class ImagePreprocessor:
    """Build conservative OCR candidates without changing the retained source."""

    def __init__(self, minimum_long_edge: int = 1600) -> None:
        self.minimum_long_edge = minimum_long_edge

    def from_bytes(self, content: bytes, page: int = 1) -> PreparedImage:
        with Image.open(io.BytesIO(content)) as source:
            source.load()
            image = ImageOps.exif_transpose(source).convert("RGB")
        return self._base(image, page, float(image.width), float(image.height))

    def prepare(
        self,
        image: Image.Image,
        page: int,
        source_width: float,
        source_height: float,
    ) -> PreparedImage:
        return self._base(image.convert("RGB"), page, source_width, source_height)

    def orientation_candidates(self, source: PreparedImage) -> List[ImageCandidate]:
        """Create four enhanced candidates for orientation scoring."""

        return [self.apply(source, "enhanced", rotation) for rotation in RIGHT_ANGLE_ROTATIONS]

    def recognition_candidates(
        self, source: PreparedImage, rotation_degrees: int
    ) -> List[ImageCandidate]:
        oriented = self._rotate(source.image, rotation_degrees)
        deskew_degrees = self._estimate_deskew(oriented)
        return [
            self.apply(source, variant, rotation_degrees, deskew_degrees)
            for variant in PREPROCESSING_VARIANTS
        ]

    def apply(
        self,
        source: PreparedImage,
        variant: str,
        rotation_degrees: int = 0,
        deskew_degrees: float = 0,
    ) -> ImageCandidate:
        if variant not in PREPROCESSING_VARIANTS:
            raise ValueError(f"Unknown preprocessing variant: {variant}")
        if rotation_degrees not in RIGHT_ANGLE_ROTATIONS:
            raise ValueError("Rotation must be 0, 90, 180, or 270 degrees.")
        if abs(deskew_degrees) > 5:
            raise ValueError("Deskew angle must be between -5 and 5 degrees.")

        image = self._rotate(source.image, rotation_degrees)
        if deskew_degrees:
            image = image.rotate(
                deskew_degrees,
                resample=Image.Resampling.BICUBIC,
                expand=False,
                fillcolor="white",
            )
        image = self._apply_variant(image, variant)
        image = self._upscale(image)
        prepared = PreparedImage(
            page=source.page,
            image=image,
            source_width=source.source_width,
            source_height=source.source_height,
            source_pixel_width=source.source_pixel_width or source.image.width,
            source_pixel_height=source.source_pixel_height or source.image.height,
            rotation_degrees=rotation_degrees,
            deskew_degrees=deskew_degrees,
        )
        return ImageCandidate(prepared=prepared, variant=variant)

    def render_recipe(
        self,
        source: PreparedImage,
        variant: str,
        rotation_degrees: int,
        deskew_degrees: float,
    ) -> bytes:
        candidate = self.apply(source, variant, rotation_degrees, deskew_degrees)
        output = io.BytesIO()
        candidate.prepared.image.save(output, format="PNG", optimize=True)
        return output.getvalue()

    @staticmethod
    def _base(
        image: Image.Image,
        page: int,
        source_width: float,
        source_height: float,
    ) -> PreparedImage:
        return PreparedImage(
            page=page,
            image=image,
            source_width=source_width,
            source_height=source_height,
            source_pixel_width=float(image.width),
            source_pixel_height=float(image.height),
        )

    @staticmethod
    def _rotate(image: Image.Image, degrees: int) -> Image.Image:
        if degrees == 90:
            return image.transpose(Image.Transpose.ROTATE_270)
        if degrees == 180:
            return image.transpose(Image.Transpose.ROTATE_180)
        if degrees == 270:
            return image.transpose(Image.Transpose.ROTATE_90)
        return image.copy()

    @staticmethod
    def _apply_variant(image: Image.Image, variant: str) -> Image.Image:
        if variant == "original":
            return image.convert("RGB")
        grayscale = ImageOps.autocontrast(image.convert("L"))
        denoised = grayscale.filter(ImageFilter.MedianFilter(size=3))
        if variant == "enhanced":
            return denoised.convert("RGB")
        threshold = _otsu_threshold(denoised.histogram())
        return denoised.point(lambda value: 255 if value > threshold else 0).convert("RGB")

    def _upscale(self, image: Image.Image) -> Image.Image:
        long_edge = max(image.size)
        if long_edge >= self.minimum_long_edge:
            return image
        scale = self.minimum_long_edge / max(long_edge, 1)
        return image.resize(
            (round(image.width * scale), round(image.height * scale)),
            Image.Resampling.LANCZOS,
        )

    @staticmethod
    def _estimate_deskew(image: Image.Image) -> float:
        """Choose a small correction angle by maximizing horizontal ink alignment."""

        sample = ImageOps.autocontrast(image.convert("L"))
        sample.thumbnail((900, 900), Image.Resampling.LANCZOS)
        threshold = _otsu_threshold(sample.histogram())
        binary = sample.point(lambda value: 1 if value < threshold else 0)

        def score(angle: float) -> float:
            rotated = binary.rotate(
                angle,
                resample=Image.Resampling.NEAREST,
                expand=False,
                fillcolor=0,
            )
            rows = [sum(row) for row in _rows(rotated)]
            if not rows:
                return 0
            mean = sum(rows) / len(rows)
            return sum((value - mean) ** 2 for value in rows) / len(rows)

        baseline = score(0)
        options = [step / 2 for step in range(-10, 11)]
        best_angle, best_score = max(
            ((angle, score(angle)) for angle in options), key=lambda item: item[1]
        )
        if abs(best_angle) < 0.5 or baseline <= 0 or best_score < baseline * 1.04:
            return 0
        return best_angle


class ScannedPdfRenderer:
    """Render image-only PDF pages while retaining PDF point coordinates."""

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


def _rows(image: Image.Image):
    pixels = list(image.getdata())
    width = image.width
    return (pixels[offset : offset + width] for offset in range(0, len(pixels), width))


def _otsu_threshold(histogram: List[int]) -> int:
    total = sum(histogram)
    weighted_total = sum(index * count for index, count in enumerate(histogram))
    background_weight = 0
    background_sum = 0
    best_variance = -1.0
    best_threshold = 127
    for threshold, count in enumerate(histogram):
        background_weight += count
        if not background_weight:
            continue
        foreground_weight = total - background_weight
        if not foreground_weight:
            break
        background_sum += threshold * count
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_total - background_sum) / foreground_weight
        variance = background_weight * foreground_weight * (background_mean - foreground_mean) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold
    return best_threshold
