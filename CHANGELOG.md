# Changelog

All notable changes to EvidenceParse are documented here.

## [0.7.0] - 2026-09-03

### Added

- Generic OCR mode with per-page text, ordered text blocks, source coordinates, and confidence.
- Professional invoice OCR mode layered on the same auditable raw-text result.
- Immediate in-browser PDF and image preview before recognition starts.
- Side-by-side source comparison, page navigation, clickable OCR blocks, and image overlays.
- Safe source-content backfill for duplicate records created before raw OCR persistence.

### Changed

- Reworked the browser UI into a calm review workspace with readable Chinese and Latin system fonts.
- Split frontend API contracts, preview, OCR, structured results, and review controls into focused modules.

## [0.6.0] - 2026-09-02

### Added

- Optional constant-time API key authentication with OpenAPI integration and key rotation.
- Configurable CORS origins, request IDs, defensive response headers, and readiness probes.
- Non-root API and web images plus end-to-end container verification in CI.
- A separately packaged Python SDK for parsing, batches, corrections, and review decisions.
- Deployment and security guidance for responsible self-hosting.

### Changed

- The web workbench accepts an optional in-memory API key for protected deployments.
- Docker Compose waits for PostgreSQL and API readiness before dependent services start.

## [0.5.0] - 2026-09-02

### Added

- Bounded multi-file batch submission with persistent job and item statuses.
- Item-level document references and safe per-file failure reporting.
- PostgreSQL migration and integration coverage for batch lifecycle records.
- Reproducible synthetic-corpus benchmark with JSON and Markdown outputs.
- Per-case, per-assertion, and per-tag benchmark summaries with CI artifacts.

### Documented

- Synthetic benchmark results are explicitly separated from real-world accuracy claims.
- Uploaded batch bytes remain transient until a retention policy is defined.

## [0.4.0] - 2026-09-02

### Added

- SQLAlchemy persistence with zero-configuration SQLite and PostgreSQL support.
- Alembic migration for canonical documents, upload occurrences, and review events.
- Exact duplicate reuse keyed by content fingerprint and extraction schema.
- Revision-protected field corrections with original values and reviewer metadata.
- Review decisions, deterministic revalidation, and immutable audit history.
- Document-list filtering and a browser-based human-review workbench.
- Dedicated PostgreSQL integration coverage in GitHub Actions.

### Fixed

- Failed deterministic validations now route their concrete fields to human review.
- Concurrent duplicate-ingestion fallback now returns the current upload metadata.

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
