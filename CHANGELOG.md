# Changelog

All notable changes to EvidenceParse are documented here.

## [0.3.0] - 2026-09-02

### Added

- Pluggable document-schema registry with explicit schema selection in the API.
- Invoice line-item extraction for labeled blocks, whitespace tables, and pipe tables.
- Per-line arithmetic and line-item-to-subtotal validation.
- Two multi-row layout fixtures and manifest-driven expectations.
- Line-item review rendering in the web interface.

## [0.2.0] - 2026-09-02

### Added

- Versioned, manifest-driven synthetic test dataset with ten document variants.
- Expected API results for digital, scanned, image, invalid, and corrupt inputs.
- Dataset generator and integration contract coverage.
- Replaceable RapidOCR provider with bundled CPU-compatible ONNX models.
- Scanned-PDF rendering and image preprocessing with source-coordinate mapping.
- Confidence-driven human review for OCR-derived fields.

## [0.1.0] - 2026-09-02

### Added

- FastAPI upload and parse endpoint for PDF, JPG, JPEG, and PNG files.
- Digital-versus-scanned PDF detection.
- Evidence-backed extraction for core invoice fields.
- Deterministic subtotal, tax, and total validation.
- Explicit review-required results when OCR is unavailable or evidence is missing.
- Next.js upload and review interface.
- Docker Compose and GitHub Actions configuration.
- Initial parser and API test suite.
