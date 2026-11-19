"""Tests for composition of prebuilt reportable collections."""

import json

from ghbot.report_style import CombinedCollectionReport, ReportSection


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
