import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

MISSING_VALUE = "<missing>"


@dataclass(frozen=True)
class BenchmarkAssertion:
    name: str
    expected: Any
    actual: Any
    passed: bool


@dataclass(frozen=True)
class AccuracyMetrics:
    """Ground-truth accuracy with raw counts for correct weighted aggregation."""

    character_errors: int
    character_count: int
    cer: Optional[float]
    word_errors: int
    word_count: int
    wer: Optional[float]
    correct_fields: int
    field_count: int
    field_accuracy: Optional[float]


@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    tags: List[str]
    duration_ms: float
    passed: bool
    assertions: List[BenchmarkAssertion]
    accuracy: Optional[AccuracyMetrics] = None


@dataclass(frozen=True)
class BenchmarkSummary:
    total_cases: int
    passed_cases: int
    total_assertions: int
    passed_assertions: int
    case_pass_rate: float
    assertion_pass_rate: float
    duration_ms: float
    accuracy: AccuracyMetrics


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
    ground_truth_text: Optional[str] = None,
    expected_fields: Optional[Dict[str, Any]] = None,
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
    accuracy = None
    if ground_truth_text is not None:
        actual_text = "\n".join(
            str(page.get("text", ""))
            for page in actual_body.get("pages", [])
            if isinstance(page, dict)
        )
        accuracy = calculate_accuracy(
            ground_truth_text,
            actual_text,
            expected_fields or {},
            actual_body,
        )
    return BenchmarkCase(
        case_id=case_id,
        tags=list(tags),
        duration_ms=round(duration_ms, 2),
        passed=all(assertion.passed for assertion in assertions),
        assertions=assertions,
        accuracy=accuracy,
    )


def normalize_text(value: str) -> str:
    """Normalize Unicode and whitespace while preserving case and punctuation."""

    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip()


def edit_distance(expected: Sequence[Any], actual: Sequence[Any]) -> int:
    """Return Levenshtein distance using one row of memory."""

    if len(expected) < len(actual):
        expected, actual = actual, expected
    previous = list(range(len(actual) + 1))
    for expected_index, expected_item in enumerate(expected, start=1):
        current = [expected_index]
        for actual_index, actual_item in enumerate(actual, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[actual_index] + 1,
                    previous[actual_index - 1]
                    + (expected_item != actual_item),
                )
            )
        previous = current
    return previous[-1]


def calculate_accuracy(
    expected_text: str,
    actual_text: str,
    expected_fields: Dict[str, Any],
    actual_body: Dict[str, Any],
) -> AccuracyMetrics:
    normalized_expected = normalize_text(expected_text)
    normalized_actual = normalize_text(actual_text)
    expected_words = normalized_expected.split()
    actual_words = normalized_actual.split()
    character_errors = edit_distance(normalized_expected, normalized_actual)
    word_errors = edit_distance(expected_words, actual_words)
    correct_fields = sum(
        _resolve_path(actual_body, path) == expected
        for path, expected in expected_fields.items()
    )
    return AccuracyMetrics(
        character_errors=character_errors,
        character_count=len(normalized_expected),
        cer=_rate(character_errors, len(normalized_expected)),
        word_errors=word_errors,
        word_count=len(expected_words),
        wer=_rate(word_errors, len(expected_words)),
        correct_fields=correct_fields,
        field_count=len(expected_fields),
        field_accuracy=(
            correct_fields / len(expected_fields) if expected_fields else None
        ),
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
        f"- Character accuracy: {_accuracy_percent(summary.accuracy.cer)} "
        f"({summary.accuracy.character_errors} edits / "
        f"{summary.accuracy.character_count} reference chars)",
        f"- Word accuracy: {_accuracy_percent(summary.accuracy.wer)} "
        f"({summary.accuracy.word_errors} edits / {summary.accuracy.word_count} reference words)",
        f"- Field accuracy: {_percent(summary.accuracy.field_accuracy)} "
        f"({summary.accuracy.correct_fields}/{summary.accuracy.field_count} exact matches)",
        f"- Total processing time: {summary.duration_ms:.2f} ms",
        "",
        "## Results by case",
        "",
        "| Case | Result | Assertions | CER | WER | Fields | Duration |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case in report.cases:
        passed = sum(assertion.passed for assertion in case.assertions)
        result = "PASS" if case.passed else "FAIL"
        lines.append(
            f"| `{case.case_id}` | {result} | {passed}/{len(case.assertions)} | "
            f"{_percent(case.accuracy.cer) if case.accuracy else '—'} | "
            f"{_percent(case.accuracy.wer) if case.accuracy else '—'} | "
            f"{_percent(case.accuracy.field_accuracy) if case.accuracy else '—'} | "
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
    measured = [case.accuracy for case in case_list if case.accuracy is not None]
    character_errors = sum(metric.character_errors for metric in measured)
    character_count = sum(metric.character_count for metric in measured)
    word_errors = sum(metric.word_errors for metric in measured)
    word_count = sum(metric.word_count for metric in measured)
    correct_fields = sum(metric.correct_fields for metric in measured)
    field_count = sum(metric.field_count for metric in measured)
    return BenchmarkSummary(
        total_cases=len(case_list),
        passed_cases=passed_cases,
        total_assertions=len(assertions),
        passed_assertions=passed_assertions,
        case_pass_rate=passed_cases / len(case_list) if case_list else 0,
        assertion_pass_rate=passed_assertions / len(assertions) if assertions else 0,
        duration_ms=round(sum(case.duration_ms for case in case_list), 2),
        accuracy=AccuracyMetrics(
            character_errors=character_errors,
            character_count=character_count,
            cer=_rate(character_errors, character_count),
            word_errors=word_errors,
            word_count=word_count,
            wer=_rate(word_errors, word_count),
            correct_fields=correct_fields,
            field_count=field_count,
            field_accuracy=correct_fields / field_count if field_count else None,
        ),
    )


def _rate(errors: int, total: int) -> Optional[float]:
    return errors / total if total else None


def _percent(value: Optional[float]) -> str:
    return f"{value:.2%}" if value is not None else "—"


def _accuracy_percent(error_rate: Optional[float]) -> str:
    return f"{max(0.0, 1 - error_rate):.2%}" if error_rate is not None else "—"


def _resolve_path(payload: Dict[str, Any], path: str) -> Any:
    current: Any = payload
    for segment in path.split("."):
        try:
            current = current[int(segment)] if isinstance(current, list) else current[segment]
        except (IndexError, KeyError, TypeError, ValueError):
            return MISSING_VALUE
    return current
