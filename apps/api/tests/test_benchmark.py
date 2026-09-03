from evidence_parse.benchmark import (
    build_report,
    calculate_accuracy,
    edit_distance,
    evaluate_case,
    render_markdown,
)


def test_benchmark_reports_missing_and_mismatched_values() -> None:
    case = evaluate_case(
        case_id="example",
        tags=["invoice", "digital-pdf"],
        expected_status=200,
        expected_body={
            "fields.total.value": "118.00",
            "line_items_length": 1,
            "fields.total.evidence.0.text_contains": "Total:",
        },
        actual_status=200,
        actual_body={
            "fields": {
                "total": {
                    "value": "120.00",
                    "evidence": [{"text": "Total: 120.00"}],
                }
            }
        },
        duration_ms=12.345,
    )

    assert case.passed is False
    assert case.assertions[1].actual == "120.00"
    assert case.assertions[2].actual == "<missing>"
    assert case.assertions[3].passed is True


def test_benchmark_summary_and_markdown_are_explicit_about_scope() -> None:
    case = evaluate_case(
        case_id="passing",
        tags=["invoice"],
        expected_status=200,
        expected_body={"page_count": 1},
        actual_status=200,
        actual_body={"page_count": 1},
        duration_ms=10,
    )
    report = build_report("Synthetic corpus", 2, [case])
    markdown = render_markdown(report)

    assert report.summary.case_pass_rate == 1
    assert report.by_tag["invoice"].passed_cases == 1
    assert "not evidence of real-world document accuracy" in report.scope
    assert "1/1 passed" in markdown


def test_accuracy_uses_known_character_word_and_field_edits() -> None:
    metrics = calculate_accuracy(
        "Invoice total 236.00",
        "Invoice total 250.00",
        {"fields.total.value": "236.00", "fields.tax.value": "36.00"},
        {"fields": {"total": {"value": "250.00"}, "tax": {"value": "36.00"}}},
    )

    assert metrics.character_errors == edit_distance("Invoice total 236.00", "Invoice total 250.00")
    assert metrics.word_errors == 1
    assert metrics.word_count == 3
    assert metrics.correct_fields == 1
    assert metrics.field_accuracy == 0.5


def test_accuracy_summary_is_weighted_by_reference_units() -> None:
    short = evaluate_case(
        "short", [], 200, {}, 200, {"pages": [{"text": "x"}]}, 1,
        ground_truth_text="a",
    )
    long = evaluate_case(
        "long", [], 200, {}, 200, {"pages": [{"text": "abcdefghij"}]}, 1,
        ground_truth_text="abcdefghij",
    )

    summary = build_report("weighted", 1, [short, long]).summary.accuracy

    assert summary.character_errors == 1
    assert summary.character_count == 11
    assert summary.cer == 1 / 11


def test_case_without_ground_truth_is_excluded_from_accuracy_denominators() -> None:
    measured = evaluate_case(
        "measured", [], 200, {}, 200, {"pages": [{"text": "same"}]}, 1,
        ground_truth_text="same",
    )
    negative = evaluate_case("negative", [], 415, {}, 415, {}, 1)

    summary = build_report("mixed", 1, [measured, negative]).summary.accuracy

    assert negative.accuracy is None
    assert summary.character_count == 4
    assert summary.cer == 0
