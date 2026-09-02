"""Run the public synthetic corpus and write machine- and human-readable reports."""

import argparse
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from fastapi.testclient import TestClient

from evidence_parse.benchmark import build_report, evaluate_case, render_markdown
from evidence_parse.main import create_app

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = REPOSITORY_ROOT / "datasets"


def run(output_directory: Path) -> dict[str, Any]:
    manifest = json.loads((DATASET_ROOT / "manifest.json").read_text(encoding="utf-8"))
    app = create_app("sqlite+pysqlite:///:memory:", auto_create_schema=True)
    cases = []
    with TestClient(app) as client:
        for definition in manifest["cases"]:
            source_path = DATASET_ROOT / definition["source"]
            expected = json.loads(
                (DATASET_ROOT / definition["expected"]).read_text(encoding="utf-8")
            )
            started = perf_counter()
            response = client.post(
                "/api/v1/documents/parse",
                files={
                    "file": (
                        source_path.name,
                        source_path.read_bytes(),
                        definition["content_type"],
                    )
                },
            )
            duration_ms = (perf_counter() - started) * 1000
            cases.append(
                evaluate_case(
                    case_id=definition["id"],
                    tags=definition["tags"],
                    expected_status=expected["status_code"],
                    expected_body=expected["body"],
                    actual_status=response.status_code,
                    actual_body=response.json(),
                    duration_ms=duration_ms,
                )
            )

    report = build_report(manifest["name"], manifest["version"], cases)
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = f"synthetic-v{manifest['version']}"
    (output_directory / f"{stem}.json").write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_directory / f"{stem}.md").write_text(render_markdown(report), encoding="utf-8")
    return report.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=REPOSITORY_ROOT / "benchmarks" / "results",
    )
    args = parser.parse_args()
    report = run(args.output_directory)
    summary = report["summary"]
    print(
        f"{summary['passed_cases']}/{summary['total_cases']} cases passed; "
        f"report written to {args.output_directory}"
    )
    return 0 if summary["passed_cases"] == summary["total_cases"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
