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


def test_composition_keeps_discovered_canonical_order():
    report = CombinedCollectionReport(
        (
            ReportSection("drift", FakeCollection("drift")),
            ReportSection("issues", FakeCollection("issues")),
            ReportSection("security", FakeCollection("security")),
        )
    )

    text = report.render("table")
    assert text.index("Drift") < text.index("Issues") < text.index("Security")
    assert "Info" not in text


def test_composition_plain_output_keeps_labelled_canonical_sections():
    report = CombinedCollectionReport(
        (
            ReportSection("drift", FakeCollection("drift")),
            ReportSection("issues", FakeCollection("issues")),
            ReportSection("security", FakeCollection("security")),
        )
    )

    assert report.render("plain") == (
        "Drift\nplain drift\n\nIssues\nplain issues\n\nSecurity\nplain security\n"
    )


def test_composition_json_nests_each_collection_document_directly():
    report = CombinedCollectionReport(
        (
            ReportSection("drift", FakeCollection("drift")),
            ReportSection("security", FakeCollection("security")),
        )
    )

    assert json.loads(report.render("json")) == {
        "drift": {"summary": {"name": "drift"}},
        "security": {"summary": {"name": "security"}},
    }
