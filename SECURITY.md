# Security policy

## Supported versions

Security fixes are applied to the latest release on `main` while the project is
pre-1.0.

## Reporting a vulnerability

Please use GitHub private vulnerability reporting for this repository. Do not
open a public issue containing API keys, customer documents, exploit details,
or personal data.

## Data boundary

The repository contains only synthetic fixtures. OCRWorkbench performs OCR
locally and does not transmit uploaded documents to an external AI service.
Self-hosters are responsible for transport security, database access, backups,
retention, deletion, and any regulatory obligations for their own documents.
