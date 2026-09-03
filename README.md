# EvidenceParse

[![CI](https://github.com/ZXLTbotsiat/EvidenceParse/actions/workflows/ci.yml/badge.svg)](https://github.com/ZXLTbotsiat/EvidenceParse/actions/workflows/ci.yml)

EvidenceParse is an evidence-first document extraction system for digital PDFs,
scanned documents, and images. It is designed around a simple rule: an extracted
value is useful only when a person can verify where it came from.

The project is being delivered in small, working batches. The current release
provides a runnable invoice pipeline for digital PDFs and OCR-backed images,
plus durable duplicate detection and an audited human-review workflow.

## What works today

- `PDF`, `JPG`, `JPEG`, `PNG`, and ZIP batch upload contract
- generic OCR with ordered text blocks, source coordinates, and confidence
- professional invoice OCR layered on the same raw-text result
- digital-versus-scanned PDF detection
- local CPU OCR for scanned PDFs and images using bundled ONNX models
- image orientation, contrast, and small-input normalization before OCR
- invoice number, date, subtotal, tax, and total extraction across supported inputs
- line-item extraction from labeled blocks, aligned columns, and pipe-delimited tables
- page and bounding-box evidence for matched values
- confidence and human-review flags
- arithmetic validation for subtotal + tax = total
- quantity × unit price and line-item sum validation
- exact duplicate detection without repeating extraction work
- SQLite for zero-configuration local use and PostgreSQL for deployed environments
- revision-protected field corrections with original-value preservation
- deterministic revalidation, review decisions, and immutable audit events
- document listing and review-status filtering
- bounded multi-file and ZIP batch jobs with persistent item-level status
- click-to-source OCR positioning for images and locally rendered PDF pages
- reproducible JSON and Markdown benchmark reports
- optional API key protection and documented key rotation
- liveness/readiness probes, defensive headers, and non-root containers
- a separately packaged Python SDK
- structured JSON API
- immediate browser preview with side-by-side OCR comparison and image-region highlighting
- browser review screen for professional fields and audit history
- Docker Compose development environment
- API and parser tests

OCR providers are isolated behind a small interface. Recognized text keeps its
source coordinates and OCR confidence; low-confidence matches remain visible
but are marked for human review instead of being silently accepted.
OCR runs locally and does not send documents to an external service. The first
OCR request can take a few seconds while the bundled models are initialized.

## Architecture

```text
Upload
  -> document type detection
  -> text layer extraction or OCR provider
  -> schema extractor
  -> evidence locator
  -> deterministic validators
  -> canonical persisted result
  -> revision-protected human review + audit history
```

- `apps/api`: FastAPI extraction service
- `apps/web`: Next.js review interface
- `apps/api/src/evidence_parse/api`: HTTP routes and request/response contracts
- `apps/api/src/evidence_parse/application`: ingestion and review use cases
- `apps/api/src/evidence_parse/persistence`: SQLAlchemy repository and tables
- `apps/api/src/evidence_parse/schemas`: replaceable document-schema composition
- `apps/api/src/evidence_parse/validators`: deterministic business validation
- `apps/api/migrations`: versioned Alembic database migrations
- `packages/python-sdk`: client library with an independent test and release boundary
- `benchmarks`: reproducible reports over the versioned synthetic corpus
- `datasets`: versioned synthetic regression corpus and expected API results
- `samples`: small inputs intended for manual product demonstrations
- `tools`: repository maintenance and dataset generation utilities

The repository follows a monorepo-style layout: deployable applications live
under `apps`, stable test assets live under `datasets`, and developer tooling is
kept outside runtime packages. See [`datasets/README.md`](datasets/README.md) for
the corpus structure and coverage.

## Run with Docker

```bash
docker compose up --build
```

Then open:

- Web: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

Compose stores application state in a named PostgreSQL volume and applies the
latest Alembic migration before the API starts.

For a protected deployment, set `EVIDENCE_PARSE_AUTH_REQUIRED=true` and provide
one or more comma-separated values in `EVIDENCE_PARSE_API_KEYS`. Keep real keys
in your environment or secret manager—never in this repository. See
[`docs/deployment.md`](docs/deployment.md) for deployment boundaries and key rotation.

## Run the API locally

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[dev]"
uvicorn evidence_parse.main:app --reload
```

Local execution defaults to `data/evidence_parse.db`. For PostgreSQL, set
`EVIDENCE_PARSE_DATABASE_URL`, set `EVIDENCE_PARSE_AUTO_CREATE_SCHEMA=false`,
and run `alembic upgrade head` before starting the API. See `.env.example` for
the supported configuration names.

Batch uploads accept either multiple ordinary documents or ZIP archives. ZIP
members are expanded in memory and are protected by path, file-count,
uncompressed-size, compression-ratio, encryption, and symbolic-link checks.
Unsupported archive metadata and non-document files are ignored. Batch status
and document references are persisted, while source bytes are discarded after
processing. When a user opens a completed ZIP item, the browser extracts only
that bounded member from the locally selected archive so the source and OCR can
still be compared without server-side document retention. The current executor
runs inside the API process; a restart-safe external queue belongs to deployment
hardening rather than this local-first release.

For PDF results, selecting an OCR text block renders the matching page through
the local API, scrolls the source pane to the original coordinates, and draws a
highlight box. The self-hosted service performs the rendering; no third-party
PDF viewer receives the file.

Run tests:

```bash
pytest
```

The test suite includes a manifest-driven contract test over every file in the
public synthetic dataset. Set `EVIDENCE_PARSE_TEST_POSTGRES_URL` to a dedicated
PostgreSQL test database to enable the database-specific integration test. The
GitHub Actions workflow provisions this database and applies migrations before
running the suite.

## API example

```bash
curl -F "file=@invoice.pdf" -F "schema=invoice" \
  http://localhost:8000/api/v1/documents/parse
```

Create a batch from a ZIP archive:

```bash
curl -F "files=@documents.zip;type=application/zip" -F "schema=generic" \
  http://localhost:8000/api/v1/batches
```

The response includes raw pages and ordered text blocks with coordinates and
confidence. Professional schemas additionally return extracted fields,
evidence locations, validations, warnings, and line items.

The `schema` form field accepts `generic` for document-wide OCR or `invoice`
for professional invoice extraction. New document types can be added by
implementing the small schema contract and registering the schema, without
changing PDF, image, or OCR ingestion.

Additional review endpoints:

```text
GET  /api/v1/documents
GET  /api/v1/documents/{document_id}
POST /api/v1/documents/{document_id}/corrections
POST /api/v1/documents/{document_id}/review
GET  /api/v1/documents/{document_id}/review-events
POST /api/v1/batches
GET  /api/v1/batches/{batch_id}
```

Correction and review writes require the latest `expected_revision`. Stale
clients receive HTTP `409` instead of overwriting a newer review decision.

## Reproducible benchmark

```bash
apps/api/.venv/Scripts/python tools/run_benchmark.py
```

The current synthetic corpus contains 12 positive, edge, OCR, and negative
cases. The committed v2 report passes all cases and all declared assertions.
This is regression evidence for known synthetic fixtures—not a production or
unseen-document accuracy claim. See [`benchmarks/README.md`](benchmarks/README.md).

## Python SDK

```bash
pip install -e packages/python-sdk
```

```python
from evidence_parse_sdk import EvidenceParseClient

with EvidenceParseClient("http://localhost:8000", api_key="your-runtime-key") as client:
    result = client.parse_document("invoice.pdf")
```

The SDK does not persist API keys. It covers individual parsing, batch jobs,
document queries, field corrections, review decisions, and audit history.

## Delivery roadmap

- **Batch 1:** digital PDF evidence pipeline and review UI
- **Batch 2:** RapidOCR provider, image preprocessing, scanned PDF support
- **Batch 3:** layout-aware line-item table extraction and pluggable schemas
- **Batch 4:** review corrections, PostgreSQL persistence, duplicate workflow ✓
- **Batch 5:** benchmark dataset, accuracy reports, jobs/batch processing ✓
- **Batch 6:** authentication, deployment hardening, SDKs and integrations ✓

## Non-goals for the first release

- claiming production accuracy from the synthetic benchmark
- hard-coding one parser per supplier
- silently guessing missing fields
- storing uploaded documents without an explicit retention policy
