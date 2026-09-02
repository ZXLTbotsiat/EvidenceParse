from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Sequence

MISSING_VALUE = "<missing>"


@dataclass(frozen=True)
class BenchmarkAssertion:
    name: str
    expected: Any
    actual: Any
    passed: bool


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    tags: List[str]
    duration_ms: float
    passed: bool
    assertions: List[BenchmarkAssertion]


@dataclass(frozen=True)
class BenchmarkSummary:
    total_cases: int
    passed_cases: int
    total_assertions: int
    passed_assertions: int
    case_pass_rate: float
    assertion_pass_rate: float
    duration_ms: float


@dataclass(frozen=True)
class BenchmarkReport:
    corpus_name: str
    corpus_version: int
    generated_at: str
    scope: str
    summary: BenchmarkSummary
    by_tag: Dict[str, BenchmarkSummary]
    cases: List[BenchmarkCase]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def evaluate_case(
    case_id: str,
    tags: Sequence[str],
    expected_status: int,
    expected_body: Dict[str, Any],
    actual_status: int,
    actual_body: Dict[str, Any],
    duration_ms: float,
) -> BenchmarkCase:
    assertions = [
        BenchmarkAssertion(
            name="status_code",
            expected=expected_status,
            actual=actual_status,
            passed=actual_status == expected_status,
        )
    ]
    for path, expected in expected_body.items():
        if path.endswith("_length"):
            value = _resolve_path(actual_body, path.removesuffix("_length"))
            actual = (
                len(value)
                if value != MISSING_VALUE and isinstance(value, (dict, list, str))
                else MISSING_VALUE
            )
            passed = actual == expected
        elif path.endswith("_contains"):
            value = _resolve_path(actual_body, path.removesuffix("_contains"))
            actual = value
            passed = value != MISSING_VALUE and isinstance(value, (list, str)) and expected in value
        else:
            actual = _resolve_path(actual_body, path)
            passed = actual == expected
        assertions.append(
            BenchmarkAssertion(
                name=path,
                expected=expected,
                actual=actual,
                passed=passed,
            )
        )
    return BenchmarkCase(
        case_id=case_id,
        tags=list(tags),
        duration_ms=round(duration_ms, 2),
        passed=all(assertion.passed for assertion in assertions),
        assertions=assertions,
    )


def build_report(
    corpus_name: str,
    corpus_version: int,
    cases: Sequence[BenchmarkCase],
) -> BenchmarkReport:
    case_list = list(cases)
    return BenchmarkReport(
        corpus_name=corpus_name,
        corpus_version=corpus_version,
        generated_at=datetime.now(timezone.utc).isoformat(),
        scope=(
            "Synthetic regression accuracy only; this report is not evidence of "
            "real-world document accuracy."
        ),
        summary=_summarize(case_list),
        by_tag={
            tag: _summarize(case for case in case_list if tag in case.tags)
            for tag in sorted({tag for case in case_list for tag in case.tags})
        },
        cases=case_list,
    )


def render_markdown(report: BenchmarkReport) -> str:
    summary = report.summary
    lines = [
        f"# {report.corpus_name} benchmark",
        "",
        f"Generated: `{report.generated_at}`",
        "",
        f"> {report.scope}",
        "",
        "## Summary",
        "",
        f"- Cases: {summary.passed_cases}/{summary.total_cases} passed "
        f"({summary.case_pass_rate:.2%})",
        f"- Assertions: {summary.passed_assertions}/{summary.total_assertions} passed "
        f"({summary.assertion_pass_rate:.2%})",
        f"- Total processing time: {summary.duration_ms:.2f} ms",
        "",
        "## Results by case",
        "",
        "| Case | Result | Assertions | Duration |",
        "| --- | --- | ---: | ---: |",
    ]
    for case in report.cases:
        passed = sum(assertion.passed for assertion in case.assertions)
        result = "PASS" if case.passed else "FAIL"
        lines.append(
            f"| `{case.case_id}` | {result} | {passed}/{len(case.assertions)} | "
            f"{case.duration_ms:.2f} ms |"
        )

    failed_assertions = [
        (case.case_id, assertion)
        for case in report.cases
        for assertion in case.assertions
        if not assertion.passed
    ]
    if failed_assertions:
        lines.extend(["", "## Failed assertions", ""])
        for case_id, assertion in failed_assertions:
            lines.append(
                f"- `{case_id}` / `{assertion.name}`: expected "
                f"`{assertion.expected}`, got `{assertion.actual}`"
            )
    return "\n".join(lines) + "\n"


def _summarize(cases: Iterable[BenchmarkCase]) -> BenchmarkSummary:
    case_list = list(cases)
    assertions = [assertion for case in case_list for assertion in case.assertions]
    passed_cases = sum(case.passed for case in case_list)
    passed_assertions = sum(assertion.passed for assertion in assertions)
    return BenchmarkSummary(
        total_cases=len(case_list),
        passed_cases=passed_cases,
        total_assertions=len(assertions),
        passed_assertions=passed_assertions,
        case_pass_rate=passed_cases / len(case_list) if case_list else 0,
        assertion_pass_rate=passed_assertions / len(assertions) if assertions else 0,
        duration_ms=round(sum(case.duration_ms for case in case_list), 2),
    )


def _resolve_path(payload: Dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        try:
            current = current[int(segment)] if isinstance(current, list) else current[segment]
        except (IndexError, KeyError, TypeError, ValueError):
            return MISSING_VALUE
    return current
