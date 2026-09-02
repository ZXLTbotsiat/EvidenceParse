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

These numbers measure only the versioned synthetic corpus in `datasets`. They
must not be presented as production accuracy or as performance on unseen,
real-world customer documents. A future real-world benchmark must use a
separately licensed, anonymized, and independently labeled dataset.
