"""Tests for composition of prebuilt reportable collections."""

import json

from ghbot.report_style import CombinedCollectionReport, ReportOutcome, ReportSection


class _Collection:
    def document(self):
        return {"repositories": []}

    def render(self, format):
        return "report\n"


def test_rate_limited_outcome_marks_json_and_plain_output_incomplete():
    outcome = ReportOutcome(
        _Collection(), abort_reason="rate_limited", not_processed=("acme/api",)
    )

    assert outcome.document()["complete"] is False
    assert outcome.document()["not_processed"] == [
        {"repository": "acme/api", "reason": "rate_limited"}
    ]
    assert outcome.render("plain").startswith("INCOMPLETE: rate limited\n")


def test_task_failure_outcome_keeps_its_distinct_reason():
    outcome = ReportOutcome(
        _Collection(),
        abort_reason="task_failed",
        not_processed=(("acme/api", "task_failed"),),
    )

    assert outcome.document()["not_processed"] == [
        {"repository": "acme/api", "reason": "task_failed"}
    ]
    assert outcome.render("plain").startswith("INCOMPLETE: task failed\n")


def test_rate_limit_exit_takes_precedence_over_explicit_repository_unavailability():
    outcome = ReportOutcome(
        _Collection(), abort_reason="rate_limited", explicit_unavailable=True
    )

    assert outcome.exit_code == 4


def test_metric_unavailability_does_not_change_a_successful_exit():
    outcome = ReportOutcome(_Collection())

    assert outcome.exit_code == 0


class FakeCollection:
    def __init__(self, name: str) -> None:
        self.name = name

    def document(self) -> dict[str, object]:
        return {"summary": {"name": self.name}}

    def render(self, format: str) -> str:
        return f"{format} {self.name}\n"


def test_composition_keeps_discovered_combine_key_order():
    report = CombinedCollectionReport(
        (
            ReportSection("security", FakeCollection("security")),
            ReportSection("issues", FakeCollection("issues")),
            ReportSection("drift", FakeCollection("drift")),
        )
    )

    text = report.render("table")
    assert text.index("Security") < text.index("Issues") < text.index("Drift")
    assert "Info" not in text


def test_composition_plain_output_keeps_labelled_combine_key_sections():
    report = CombinedCollectionReport(
        (
            ReportSection("security", FakeCollection("security")),
            ReportSection("issues", FakeCollection("issues")),
            ReportSection("drift", FakeCollection("drift")),
        )
    )

    assert report.render("plain") == (
        "Security\nplain security\n\nIssues\nplain issues\n\nDrift\nplain drift\n"
    )


def test_incomplete_combined_text_has_one_banner():
    report = ReportOutcome(
        CombinedCollectionReport(
            (
                ReportSection(
                    "security",
                    ReportOutcome(FakeCollection("security"), "rate_limited"),
                ),
                ReportSection(
                    "issues",
                    ReportOutcome(FakeCollection("issues"), "rate_limited"),
                ),
            )
        ),
        "rate_limited",
    )

    assert report.render("plain").count("INCOMPLETE: rate limited") == 1


def test_composition_json_nests_each_collection_document_directly():
    report = CombinedCollectionReport(
        (
            ReportSection("security", FakeCollection("security")),
            ReportSection("drift", FakeCollection("drift")),
        )
    )

    assert json.loads(report.render("json")) == {
        "security": {"summary": {"name": "security"}},
        "drift": {"summary": {"name": "drift"}},
    }
