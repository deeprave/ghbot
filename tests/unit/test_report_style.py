import json

import pytest

from ghbot.report_style import (
    JSONReportStyle,
    MarkdownTableReportStyle,
    PlainReportStyle,
    ReportStyle,
    TableColumn,
    TableReportStyle,
    write_report,
)


def test_style_factory_selects_concrete_styles():
    assert isinstance(ReportStyle.from_format("plain"), PlainReportStyle)
    assert isinstance(ReportStyle.from_format("json"), JSONReportStyle)
    table = ReportStyle.from_format("table")
    assert isinstance(table, MarkdownTableReportStyle)
    assert isinstance(table, TableReportStyle)


def test_style_factory_rejects_unknown_format():
    with pytest.raises(ValueError, match="format"):
        ReportStyle.from_format("xml")


def test_plain_and_json_styles_render_stable_documents():
    assert PlainReportStyle().render_lines(["one", "two"]) == "one\ntwo\n"
    assert json.loads(JSONReportStyle().render_document({"summary": {"count": 1}})) == {
        "summary": {"count": 1}
    }


def test_markdown_table_style_applies_columns_and_alignment():
    style = MarkdownTableReportStyle()
    columns = [TableColumn("Name", 6), TableColumn("Count", 5, align="right")]
    assert style.header(columns) == "|Name  |Count|"
    assert style.separator(columns) == "|------|-----|"
    assert style.row(columns, ["api", 3]) == "|api   |    3|"


def test_write_report_writes_utf8_file(tmp_path):
    output = tmp_path / "report.txt"
    write_report("hello\n", output)
    assert output.read_text(encoding="utf-8") == "hello\n"
