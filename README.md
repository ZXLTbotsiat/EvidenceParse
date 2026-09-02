# EvidenceParse

EvidenceParse is an evidence-first document extraction system for digital PDFs,
scanned documents, and images. It is designed around a simple rule: an extracted
value is useful only when a person can verify where it came from.

The project is being delivered in small, working batches. The current release
provides a runnable invoice pipeline for digital PDFs and OCR-backed images,
plus durable duplicate detection and an audited human-review workflow.

## What works today

- `PDF`, `JPG`, `JPEG`, and `PNG` upload contract
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
- structured JSON API
- browser review screen
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

The response includes extracted fields, evidence locations, validations,
warnings, line items, the selected schema name, and a content fingerprint.

The `schema` form field currently accepts `invoice`. New document types can be
added by implementing the small schema contract and registering the schema,
without changing PDF, image, or OCR ingestion.

Additional review endpoints:

```text
GET  /api/v1/documents
GET  /api/v1/documents/{document_id}
POST /api/v1/documents/{document_id}/corrections
POST /api/v1/documents/{document_id}/review
GET  /api/v1/documents/{document_id}/review-events
```

Correction and review writes require the latest `expected_revision`. Stale
clients receive HTTP `409` instead of overwriting a newer review decision.

## Delivery roadmap

- **Batch 1:** digital PDF evidence pipeline and review UI
- **Batch 2:** RapidOCR provider, image preprocessing, scanned PDF support
- **Batch 3:** layout-aware line-item table extraction and pluggable schemas
- **Batch 4:** review corrections, PostgreSQL persistence, duplicate workflow ✓
- **Batch 5:** benchmark dataset, accuracy reports, jobs/batch processing
- **Batch 6:** authentication, deployment hardening, SDKs and integrations

## Non-goals for the first release

- claiming production accuracy without a benchmark
- hard-coding one parser per supplier
- silently guessing missing fields
- storing uploaded documents without an explicit retention policy
