from evidence_parse.benchmark import build_report, evaluate_case, render_markdown


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
