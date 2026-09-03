# Benchmarks

EvidenceParse keeps repeatable benchmark outputs separate from the source
dataset and ordinary unit-test results.

Run the current synthetic corpus from the repository root:

```bash
apps/api/.venv/Scripts/python tools/run_benchmark.py
```

The command writes JSON for automation and Markdown for human review under
`benchmarks/results`. A non-zero exit code means at least one public contract
assertion failed.

Cases with a declared ground-truth transcript additionally report:

- character error rate (CER): character edit distance divided by reference
  character count;
- word error rate (WER): token edit distance divided by reference word count;
- exact field accuracy: correctly extracted declared field values divided by
  declared field count.

Text is normalized with Unicode NFKC and consecutive whitespace is collapsed;
case and punctuation remain significant. Summary rates are calculated from raw
edit and reference counts, not by averaging per-document percentages. Negative
fixtures without ground truth are excluded from accuracy denominators.

These numbers measure only the versioned synthetic corpus in `datasets`. They
must not be presented as production accuracy or as performance on unseen,
real-world customer documents. A future real-world benchmark must use a
separately licensed, anonymized, and independently labeled dataset.

OCR model confidence and preprocessing candidate score are diagnostic signals,
not accuracy measurements. Only comparison with independent ground truth is
reported as accuracy.
