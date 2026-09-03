<div align="center">

# EvidenceParse

**Evidence-first OCR and document extraction for PDFs and images.**

Turn documents into structured data without losing the connection to the
original page, text, and coordinates.

[![CI](https://github.com/ZXLTbotsiat/EvidenceParse/actions/workflows/ci.yml/badge.svg)](https://github.com/ZXLTbotsiat/EvidenceParse/actions/workflows/ci.yml)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](apps/api/pyproject.toml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

EvidenceParse is a self-hosted document understanding system built for
traceability. It combines local OCR, structured extraction, deterministic
validation, and human review in one workflow. Every extracted value can carry
its source page and bounding box, so reviewers can verify results against the
original document instead of trusting an opaque JSON response.

Documents are processed locally. EvidenceParse does not send uploaded files to
an external OCR or AI service.

## Features

- **General OCR** — extract ordered text blocks, coordinates, and confidence
  scores from digital PDFs, scanned PDFs, PNGs, and JPEGs.
- **Professional extraction** — parse invoice fields and line items on top of
  the same auditable OCR result.
- **Source comparison** — click an OCR result to open the matching page, scroll
  to the original location, and highlight the source region.
- **Batch processing** — upload multiple documents or a ZIP archive and inspect
  progress and results per file.
- **Safe ZIP handling** — reject path traversal, encrypted entries, symbolic
  links, oversized archives, and suspicious compression ratios.
- **Human review** — correct fields with optimistic revision checks, preserve
  original values, and keep an immutable audit trail.
- **Deterministic validation** — verify invoice totals, line-item arithmetic,
  and other schema-specific rules without asking a model to guess.
- **Duplicate detection** — identify identical content without repeating the
  extraction pipeline.
- **Pluggable design** — keep OCR providers, schemas, extractors, and validators
  behind small, replaceable interfaces.
- **Deployment ready** — use SQLite for a zero-configuration local setup or
  PostgreSQL, API-key protection, health probes, and non-root containers for a
  hosted environment.

## Quick start

The easiest way to run the complete application is Docker Compose.

```bash
git clone https://github.com/ZXLTbotsiat/EvidenceParse.git
cd EvidenceParse
docker compose up --build
```

Open the following services after the containers are healthy:

- Web application: <http://localhost:3000>
- OpenAPI documentation: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

PostgreSQL data is stored in a named Docker volume. Database migrations run
before the API starts.

## Using the web application

1. Drag one or more `PDF`, `PNG`, `JPG`, or `JPEG` files into the source panel.
   You can also upload a single ZIP containing supported documents.
2. Select **General OCR** or **Professional Invoice OCR**.
3. Start recognition and wait for the document or batch to complete.
4. Click any OCR text block to locate and highlight it in the original file.
5. For invoice results, review extracted fields, validations, and audit history.

ZIP members are expanded in memory and are never written to a temporary
directory. When a result is opened, the browser extracts only the selected ZIP
member for source comparison. Uploaded source bytes are not retained by the API
after processing.

## API

Parse one document with the invoice schema:

```bash
curl -F "file=@invoice.pdf" -F "schema=invoice" \
  http://localhost:8000/api/v1/documents/parse
```

Run general OCR over a ZIP archive:

```bash
curl -F "files=@documents.zip;type=application/zip" -F "schema=generic" \
  http://localhost:8000/api/v1/batches
```

The `schema` form field accepts:

| Value | Purpose |
| --- | --- |
| `generic` | Ordered OCR text blocks with page coordinates and confidence |
| `invoice` | General OCR plus invoice fields, line items, evidence, and validations |

Core endpoints:

```text
POST /api/v1/documents/parse
GET  /api/v1/documents
GET  /api/v1/documents/{document_id}
POST /api/v1/documents/{document_id}/corrections
POST /api/v1/documents/{document_id}/review
GET  /api/v1/documents/{document_id}/review-events
POST /api/v1/batches
GET  /api/v1/batches/{batch_id}
POST /api/v1/previews/pdf-page
```

Correction and review requests include `expected_revision`. A stale client
receives HTTP `409` instead of overwriting a newer review decision.

When API-key protection is enabled, send the key with every request:

```bash
curl -H "X-API-Key: your-runtime-key" http://localhost:8000/api/v1/documents
```

## Python SDK

Install the SDK from this repository:

```bash
pip install -e packages/python-sdk
```

```python
from evidence_parse_sdk import EvidenceParseClient

with EvidenceParseClient(
    "http://localhost:8000",
    api_key="your-runtime-key",
) as client:
    result = client.parse_document("invoice.pdf")
    print(result["fields"])
```

The SDK supports document parsing, batch jobs, document queries, corrections,
review decisions, and audit history. It does not persist API keys.

## Architecture

```text
                         +----------------------+
 PDF / image / ZIP ----> | FastAPI ingestion    |
                         +----------+-----------+
                                    |
                       +------------v-------------+
                       | Type detection            |
                       | PDF text layer / local OCR|
                       +------------+-------------+
                                    |
                       +------------v-------------+
                       | Schema extraction         |
                       | Evidence + coordinates    |
                       | Deterministic validation  |
                       +------------+-------------+
                                    |
                   +----------------v----------------+
                   | SQL persistence and review      |
                   | Revisions, corrections, audit   |
                   +----------------+----------------+
                                    |
                         +----------v-----------+
                         | Next.js workbench    |
                         +----------------------+
```

The repository uses a monorepo layout:

```text
apps/
  api/                 FastAPI service, extraction pipeline, and migrations
  web/                 Next.js source-comparison and review interface
packages/
  python-sdk/          Typed Python client
datasets/              Synthetic regression corpus and expected results
benchmarks/            Reproducible benchmark reports
docs/                  Deployment and operational guidance
samples/               Small files for manual testing
tools/                 Dataset and benchmark utilities
```

Inside the API, transport, application use cases, persistence, OCR, schemas,
and validators are separate modules. Adding a document type normally means
implementing and registering a schema; it does not require changing PDF, image,
or ZIP ingestion.

## Configuration

Copy [`.env.example`](.env.example) and override only the values needed for your
environment.

| Variable | Default | Description |
| --- | --- | --- |
| `EVIDENCE_PARSE_MAX_UPLOAD_MB` | `20` | Maximum size of one document |
| `EVIDENCE_PARSE_MAX_BATCH_FILES` | `20` | Maximum ordinary files in one batch |
| `EVIDENCE_PARSE_MAX_BATCH_MB` | `100` | Maximum total upload or ZIP size |
| `EVIDENCE_PARSE_MAX_ARCHIVE_ENTRIES` | `100` | Maximum entries inspected in a ZIP |
| `EVIDENCE_PARSE_MAX_ZIP_RATIO` | `200` | Maximum accepted compression ratio |
| `EVIDENCE_PARSE_DATABASE_URL` | SQLite | SQLAlchemy database URL |
| `EVIDENCE_PARSE_AUTO_CREATE_SCHEMA` | `true` | Create tables automatically for local use |
| `EVIDENCE_PARSE_AUTH_REQUIRED` | `false` | Require an API key when enabled |
| `EVIDENCE_PARSE_API_KEYS` | empty | Comma-separated accepted API keys |
| `EVIDENCE_PARSE_CORS_ORIGINS` | local web URLs | Allowed browser origins |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | API URL used by the web application |

Do not commit real API keys or production passwords. See
[`docs/deployment.md`](docs/deployment.md) for PostgreSQL migrations, key
rotation, reverse-proxy boundaries, and deployment checks.

## Local development

### API

```bash
cd apps/api
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Or on macOS and Linux:

```bash
source .venv/bin/activate
```

Then install and run the service:

```bash
pip install -e ".[dev]"
uvicorn evidence_parse.main:app --reload
```

Local execution uses `apps/api/data/evidence_parse.db` unless
`EVIDENCE_PARSE_DATABASE_URL` is set.

### Web

```bash
cd apps/web
npm install
npm run dev
```

### Tests and checks

```bash
cd apps/api
pytest
ruff check src tests
```

```bash
cd apps/web
npm run build
npm audit
```

```bash
cd packages/python-sdk
pytest
ruff check src tests
```

To run the versioned synthetic benchmark from the repository root:

```bash
apps/api/.venv/Scripts/python tools/run_benchmark.py
```

The benchmark is regression evidence for the included synthetic fixtures. It
is not a claim about accuracy on unseen or production documents. Dataset
coverage and provenance are documented in [`datasets/README.md`](datasets/README.md)
and [`benchmarks/README.md`](benchmarks/README.md).

## Security and data handling

- OCR and PDF preview rendering run on the self-hosted API.
- Source bytes are transient unless a separate retention mechanism is added by
  the operator.
- Low-confidence or missing values remain visible for review; they are not
  silently invented.
- ZIP limits are enforced before and during extraction.
- Production operators are responsible for TLS, access control, backups,
  retention, deletion, and regulatory requirements.

Please report vulnerabilities through GitHub private vulnerability reporting.
See [`SECURITY.md`](SECURITY.md) for the full policy.

## Contributing

Issues and pull requests are welcome. Keep changes focused, add tests for new
behavior, and use only synthetic or clearly redistributable documents in the
repository. Customer files, credentials, cookies, tokens, and private datasets
must never be committed.

## License

EvidenceParse is available under the [MIT License](LICENSE).
