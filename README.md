# EvidenceParse

EvidenceParse is an evidence-first document extraction system for digital PDFs,
scanned documents, and images. It is designed around a simple rule: an extracted
value is useful only when a person can verify where it came from.

The project is being delivered in small, working batches. The first two batches
provide a runnable invoice pipeline for digital PDFs and OCR-backed images,
while keeping layout and review components behind stable contracts.

## What works today

- `PDF`, `JPG`, `JPEG`, and `PNG` upload contract
- digital-versus-scanned PDF detection
- local CPU OCR for scanned PDFs and images using bundled ONNX models
- image orientation, contrast, and small-input normalization before OCR
- invoice number, date, subtotal, tax, and total extraction across supported inputs
- page and bounding-box evidence for matched values
- confidence and human-review flags
- arithmetic validation for subtotal + tax = total
- content fingerprint for duplicate detection by callers
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
  -> structured result + human review flags
```

- `apps/api`: FastAPI extraction service
- `apps/web`: Next.js review interface
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

The test suite includes a manifest-driven contract test over every file in the
public synthetic dataset.

## API example

```bash
curl -F "file=@invoice.pdf" http://localhost:8000/api/v1/documents/parse
```

The response includes extracted fields, evidence locations, validations,
warnings, and a content fingerprint.

## Delivery roadmap

- **Batch 1:** digital PDF evidence pipeline and review UI
- **Batch 2:** RapidOCR provider, image preprocessing, scanned PDF support
- **Batch 3:** layout-aware line-item table extraction and pluggable schemas
- **Batch 4:** review corrections, PostgreSQL persistence, duplicate workflow
- **Batch 5:** benchmark dataset, accuracy reports, jobs/batch processing
- **Batch 6:** authentication, deployment hardening, SDKs and integrations

## Non-goals for the first release

- claiming production accuracy without a benchmark
- hard-coding one parser per supplier
- silently guessing missing fields
- storing uploaded documents without an explicit retention policy
