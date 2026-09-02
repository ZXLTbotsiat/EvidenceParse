# EvidenceParse

EvidenceParse is an evidence-first document extraction system for digital PDFs,
scanned documents, and images. It is designed around a simple rule: an extracted
value is useful only when a person can verify where it came from.

The project is being delivered in small, working batches. The first batch
implements a runnable invoice pipeline for digital PDFs and establishes the
contracts that later OCR, layout, and review components will use.

## What works today

- `PDF`, `JPG`, `JPEG`, and `PNG` upload contract
- digital-versus-scanned PDF detection
- invoice number, date, subtotal, tax, and total extraction from digital PDFs
- page and bounding-box evidence for matched values
- confidence and human-review flags
- arithmetic validation for subtotal + tax = total
- content fingerprint for duplicate detection by callers
- structured JSON API
- browser review screen
- Docker Compose development environment
- API and parser tests

Image OCR and scanned-PDF OCR are intentionally reported as `review_required`
in this first batch rather than returning invented values.

## Architecture

```text
Upload
  -> document type detection
  -> text layer extraction or OCR provider
  -> schema extractor
  -> evidence locator
  -> deterministic validators
  -> structured result + human review flags
```

- `apps/api`: FastAPI extraction service
- `apps/web`: Next.js review interface
- `samples`: synthetic or redistributable test material

## Run with Docker

```bash
docker compose up --build
```

Then open:

- Web: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

## Run the API locally

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[dev]"
uvicorn evidence_parse.main:app --reload
```

Run tests:

```bash
pytest
```

## API example

```bash
curl -F "file=@invoice.pdf" http://localhost:8000/api/v1/documents/parse
```

The response includes extracted fields, evidence locations, validations,
warnings, and a content fingerprint.

## Delivery roadmap

- **Batch 1:** digital PDF evidence pipeline and review UI
- **Batch 2:** PaddleOCR provider, image preprocessing, scanned PDF support
- **Batch 3:** layout-aware line-item table extraction and pluggable schemas
- **Batch 4:** review corrections, PostgreSQL persistence, duplicate workflow
- **Batch 5:** benchmark dataset, accuracy reports, jobs/batch processing
- **Batch 6:** authentication, deployment hardening, SDKs and integrations

## Non-goals for the first release

- claiming production accuracy without a benchmark
- hard-coding one parser per supplier
- silently guessing missing fields
- storing uploaded documents without an explicit retention policy

