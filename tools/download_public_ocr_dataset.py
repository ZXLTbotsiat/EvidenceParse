"""Download the curated public OCR evaluation set without vendoring it.

Every download is pinned by SHA-256. A changed or truncated upstream file is
rejected instead of silently becoming a different benchmark input.
"""

from __future__ import annotations

import hashlib
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "datasets" / "external" / "ocr-evaluation"
OCRMY_PDF_BASE = (
    "https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/tests/resources"
)


@dataclass(frozen=True)
class PublicSample:
    """One immutable download with its expected content digest."""

    filename: str
    url: str
    sha256: str


SAMPLES = (
    PublicSample(
        "01-hard-illustrated-scan.pdf",
        f"{OCRMY_PDF_BASE}/c03-29.pdf",
        "c2ff83af7d028c95209cc7eebdf80fd5bb4cd292973ed6601e4bab7d1929f201",
    ),
    PublicSample(
        "02-rotated-skewed-two-column.pdf",
        f"{OCRMY_PDF_BASE}/rotated_skew.pdf",
        "5122c07d05a61219eb9f8305776ef16def6b34c29358e05c5ae2e884a351438f",
    ),
    PublicSample(
        "03-multipage-mixed-scan.pdf",
        f"{OCRMY_PDF_BASE}/multipage.pdf",
        "07987c44650938fa8dcf08c0937691712fdd800669b4607c2c7e3fee21cb1f80",
    ),
    PublicSample(
        "04-french-diacritics.pdf",
        f"{OCRMY_PDF_BASE}/francais.pdf",
        "600c27f8dd2ef085a94d3500f6ccdb3b37f4b89aa8ffdf9a00a06a1367887e8b",
    ),
    PublicSample(
        "05-typewriter-text.png",
        f"{OCRMY_PDF_BASE}/typewriter.png",
        "6f7a83685a83af954e9672b3e2db3253af165513d2826d780a48e175742f4469",
    ),
    PublicSample(
        "06-multilingual-color-map.jpg",
        f"{OCRMY_PDF_BASE}/baiona_color.jpg",
        "ca10778da7da3084de6fecceca3778836b87ce7cbe814d6837285df2c12129d7",
    ),
    PublicSample(
        "07-vector-text-no-font-map.pdf",
        f"{OCRMY_PDF_BASE}/vector.pdf",
        "f530547f86ca3884ef8e2e3cde686ca04c3a587b09d529a9d74817e77192cbb7",
    ),
    PublicSample(
        "08-irs-w9-form.pdf",
        "https://www.irs.gov/pub/irs-pdf/fw9.pdf",
        "2d420cbb4123dcf1fb82595b2359cfbb5d81f00b9df9d359fcc7af361d093f53",
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(sample: PublicSample) -> None:
    destination = OUTPUT_DIR / sample.filename
    if destination.exists() and _sha256(destination) == sample.sha256:
        print(f"verified  {sample.filename}")
        return

    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(
        sample.url,
        headers={"User-Agent": "OCRWorkbench public dataset downloader"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            temporary.write_bytes(response.read())
        actual = _sha256(temporary)
        if actual != sample.sha256:
            raise ValueError(
                f"SHA-256 mismatch for {sample.filename}: "
                f"expected {sample.sha256}, received {actual}"
            )
        os.replace(temporary, destination)
        print(f"downloaded {sample.filename}")
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    """Download missing files and verify every local sample."""

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for sample in SAMPLES:
        _download(sample)
    print(f"ready: {len(SAMPLES)} files in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
