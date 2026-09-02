# Test dataset

This directory is the versioned regression corpus for EvidenceParse. Every
document is synthetic, contains no customer or personal data, and is covered by
the repository's MIT license.

## Layout

```text
datasets/
├── manifest.json                 # Machine-readable case index
├── expected/                     # Observable API expectations per case
└── synthetic/
    ├── invoices/
    │   ├── digital-pdf/          # Text-layer PDFs and edge cases
    │   ├── scanned-pdf/          # Image-only PDFs
    │   └── images/               # PNG and JPEG inputs
    └── invalid/                  # Unsupported and deliberately corrupt inputs
```

The manifest is the source of truth used by the integration test. Expectations
assert public API behavior rather than private implementation details, so the
corpus remains useful while OCR and extraction providers evolve.

## Cases

- standard digital PDF;
- missing monetary fields;
- inconsistent subtotal, tax, and total;
- repeated amounts with different semantic labels;
- multi-page invoice;
- two-row whitespace-aligned table;
- two-row pipe-delimited table;
- scanned PDF;
- PNG and JPEG invoices;
- unsupported text file;
- deliberately corrupt PDF.

Scanned and image fixtures exercise the real CPU OCR pipeline. Their expected
results include recognized values, evidence coordinates, confidence-driven
review decisions, and arithmetic validation.

## Regenerate

From the repository root, using the API development environment:

```bash
python tools/generate_test_dataset.py
```

Review generated binary changes before committing them. The generator only
writes the paths declared by its case definitions and never consumes external
documents.
