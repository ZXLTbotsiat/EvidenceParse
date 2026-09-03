# Test dataset

This directory contains the versioned regression corpus for EvidenceParse.
Documents referenced by `manifest.json` are synthetic, contain no customer or
personal data, and are covered by the repository's MIT license.

`external/` is a separate, manually curated evaluation set downloaded from
public sources. It is not part of the automated regression manifest and each
file keeps the source and license documented beside it.

## Layout

```text
datasets/
├── manifest.json                 # Machine-readable case index
├── expected/                     # Observable API expectations per case
├── external/                     # Licensed public samples for manual evaluation
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

The same manifest drives `tools/run_benchmark.py`. Versioned benchmark reports
live under `benchmarks/results`; see `benchmarks/README.md` for their scope and
interpretation limits.

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
