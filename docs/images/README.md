# Documentation image provenance

The product screenshots in this directory were captured from a local
EvidenceParse instance. They contain no customer data or private documents.
All interface chrome shown in the README screenshots uses the English locale.

`source-traceability.jpg`, `batch-processing.jpg`, and `mobile-review.jpg` use
the repository's MIT-licensed synthetic fixtures.

`challenging-handwritten-style.jpg` is a real local run against
[`samples/handwritten-style-note.png`](../../samples/handwritten-style-note.png),
an MIT-licensed synthetic note created for this repository. It is intentionally
slightly rotated and uses a handwriting-style font; it is not presented as a
sample of unrestricted human handwriting.

The challenging-document screenshots use files from OCRmyPDF's public test
resources:

| Screenshot | Source fixture | Upstream terms |
| --- | --- | --- |
| `challenging-rotated.jpg` | `rotated_skew.pdf` | Copyright 1985 Forat Electronics; GFDL-1.2-or-later or CC-BY-SA-3.0 |
| `challenging-typewriter.jpg` | `typewriter.png` | Copyright 2005 Ellywa; GFDL-1.2-or-later or CC-BY-SA-1.0/2.0/2.5/3.0 |
| `challenging-illustrated.jpg` | `c03-29.pdf` | Public domain |

Those source excerpts retain their upstream terms and are not relicensed under
the EvidenceParse MIT license. See the full fixture provenance in
[`datasets/external/ocr-evaluation/README.md`](../../datasets/external/ocr-evaluation/README.md)
and OCRmyPDF's upstream
[`REUSE.toml`](https://github.com/ocrmypdf/OCRmyPDF/blob/main/REUSE.toml).
