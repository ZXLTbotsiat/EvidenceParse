# OCRWorkbench synthetic invoice regression corpus benchmark

Generated: `2026-09-03T08:10:18.384525+00:00`

> Synthetic regression accuracy only; this report is not evidence of real-world document accuracy.

## Summary

- Cases: 12/12 passed (100.00%)
- Assertions: 77/77 passed (100.00%)
- Character accuracy: 99.95% (1 edits / 2143 reference chars)
- Word accuracy: 99.37% (2 edits / 318 reference words)
- Field accuracy: 100.00% (23/23 exact matches)
- Total processing time: 19526.16 ms

## Results by case

| Case | Result | Assertions | CER | WER | Fields | Duration |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `digital-standard` | PASS | 12/12 | 0.00% | 0.00% | 100.00% | 35.04 ms |
| `digital-missing-fields` | PASS | 6/6 | 0.00% | 0.00% | 100.00% | 8.19 ms |
| `digital-amount-mismatch` | PASS | 4/4 | 0.00% | 0.00% | 100.00% | 8.31 ms |
| `digital-repeated-amounts` | PASS | 4/4 | 0.00% | 0.00% | 100.00% | 9.51 ms |
| `digital-multi-page` | PASS | 6/6 | 0.00% | 0.00% | 100.00% | 8.62 ms |
| `digital-whitespace-table` | PASS | 8/8 | 0.00% | 0.00% | 100.00% | 8.84 ms |
| `digital-pipe-table` | PASS | 8/8 | 0.00% | 0.00% | 100.00% | 7.89 ms |
| `scanned-pdf` | PASS | 9/9 | 0.41% | 5.71% | 100.00% | 7495.95 ms |
| `image-png` | PASS | 8/8 | 0.00% | 0.00% | 100.00% | 6340.40 ms |
| `image-jpeg` | PASS | 8/8 | 0.00% | 0.00% | 100.00% | 5588.01 ms |
| `unsupported-file` | PASS | 2/2 | — | — | — | 3.57 ms |
| `corrupt-pdf` | PASS | 2/2 | — | — | — | 11.83 ms |
