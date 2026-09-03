# OCRWorkbench development guide

## Product goal

Build a self-hosted OCR and document extraction workbench. Every extracted value should remain traceable to a source page and region, validated where possible, and marked for human review when confidence is insufficient.

## Engineering rules

- Keep OCR, layout analysis, schema extraction, and validation behind replaceable interfaces.
- Never invent values that are absent from the document.
- Prefer `null` plus a review reason over a guessed value.
- Every feature must include tests or a documented reason why automated coverage is not yet practical.
- Do not commit credentials, customer documents, tokens, or private datasets.
- Keep sample documents synthetic or clearly licensed for redistribution.

## Delivery cadence

Each batch should remain runnable and include:

1. source changes;
2. tests;
3. README or changelog updates;
4. a scoped Git commit.
