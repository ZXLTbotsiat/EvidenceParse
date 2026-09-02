import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DATASET_ROOT = REPOSITORY_ROOT / "datasets"
MANIFEST = json.loads((DATASET_ROOT / "manifest.json").read_text(encoding="utf-8"))


def _resolve_path(value: Any, path: str) -> Any:
    current = value
    for segment in path.split("."):
        current = current[int(segment)] if isinstance(current, list) else current[segment]
    return current


def _assert_expected_body(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    for path, expected_value in expected.items():
        if path.endswith("_length"):
            actual_value = _resolve_path(actual, path.removesuffix("_length"))
            assert len(actual_value) == expected_value
        elif path.endswith("_contains"):
            actual_value = _resolve_path(actual, path.removesuffix("_contains"))
            assert expected_value in actual_value
        else:
            assert _resolve_path(actual, path) == expected_value


@pytest.mark.parametrize("case", MANIFEST["cases"], ids=lambda case: case["id"])
def test_dataset_case_matches_public_api_contract(case: dict[str, Any], client: TestClient) -> None:
    source_path = DATASET_ROOT / case["source"]
    expected = json.loads((DATASET_ROOT / case["expected"]).read_text(encoding="utf-8"))

    assert source_path.is_file(), f"Dataset source is missing: {case['source']}"
    with source_path.open("rb") as source:
        response = client.post(
            "/api/v1/documents/parse",
            files={"file": (source_path.name, source, case["content_type"])},
        )

    assert response.status_code == expected["status_code"]
    _assert_expected_body(response.json(), expected["body"])
