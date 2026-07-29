"""Tests for issues report rendering (issues + pull requests, tagged by type)."""

import json

from ghbot.processor import RepoResult
from ghbot.report import print_issues_report, render_issues_report


def _item(number, title, type="issue", labels=None):
    return {"number": number, "title": title, "type": type, "labels": labels or []}


def _result(owner, repo, count=None, items=None, status="success"):
    r = RepoResult(owner=owner, repo=repo, status=status)
    r.results["open_item_count"] = count
    r.results["open_items"] = items
    return r


class TestIssuesReportSummary:
    def test_plain_summary_splits_issues_and_prs(self, capsys):
        results = [
            _result(
                "o",
                "a",
                3,
                [
                    _item(12, "x", "issue"),
                    _item(13, "y", "pr"),
                    _item(14, "z", "issue"),
                ],
            ),
            _result("o", "b", 0, []),
        ]
        print_issues_report(results)
        lines = capsys.readouterr().out.splitlines()
        assert "2" in next(line for line in lines if line.startswith("Repos scanned:"))
        assert "1" in next(
            line for line in lines if line.startswith("Repos with open items:")
        )
        assert "2" in next(line for line in lines if line.startswith("Open issues:"))
        assert "1" in next(line for line in lines if line.startswith("Open PRs:"))

    def test_nothing_on_stderr(self, capsys):
        print_issues_report([_result("o", "a", 1, [_item(1, "Bug")])])
        assert capsys.readouterr().err == ""

    def test_all_none_shows_na(self, capsys):
        print_issues_report([_result("o", "a", None, None)])
        lines = capsys.readouterr().out.splitlines()
        assert "N/A" in next(line for line in lines if line.startswith("Open issues:"))
        assert "N/A" in next(line for line in lines if line.startswith("Open PRs:"))


class TestIssuesReportPlain:
    def test_per_repo_header_and_item_lines_with_type(self):
        results = [
            _result(
                "acme",
                "web",
                2,
                [
                    _item(12, "Fix the login redirect", "issue"),
                    _item(15, "Add retry to fetch", "pr"),
                ],
            )
        ]
        out = render_issues_report(results, format="plain")
        assert "acme/web  (2 open)" in out
        assert "  #12 [issue] Fix the login redirect" in out
        assert "  #15 [pr] Add retry to fetch" in out

    def test_labels_flag_adds_prefixed_labels(self):
        results = [
            _result("acme", "web", 1, [_item(12, "Fix login", "pr", ["bug", "urgent"])])
        ]
        with_labels = render_issues_report(results, format="plain", labels=True)
        assert "  #12 [pr] Fix login +bug +urgent" in with_labels

    def test_default_omits_labels_but_keeps_type(self):
        results = [
            _result("acme", "web", 1, [_item(12, "Fix login", "issue", ["bug"])])
        ]
        out = render_issues_report(results, format="plain")
        assert "  #12 [issue] Fix login" in out
        assert "+bug" not in out

    def test_omits_repos_without_open_items(self):
        results = [
            _result("acme", "web", 1, [_item(1, "Bug")]),
            _result("acme", "empty", 0, []),
            _result("acme", "denied", None, None),
        ]
        out = render_issues_report(results, format="plain")
        assert "acme/web" in out
        assert "acme/empty" not in out
        assert "acme/denied" not in out


class TestIssuesReportTable:
    def test_one_row_per_item_with_type_column(self):
        results = [
            _result(
                "acme",
                "web",
                2,
                [_item(12, "Fix login", "issue"), _item(15, "Add retry", "pr")],
            )
        ]
        out = render_issues_report(results, format="table")
        assert "|Repository" in out
        assert "|Type" in out
        assert "|Description" in out
        lines = out.splitlines()
        assert any(
            "acme/web" in line
            and "12" in line
            and "issue" in line
            and "Fix login" in line
            for line in lines
        )
        assert any(
            "acme/web" in line and "15" in line and "pr" in line and "Add retry" in line
            for line in lines
        )

    def test_labels_column_only_with_flag(self):
        results = [
            _result("acme", "web", 1, [_item(12, "Fix login", "pr", ["bug", "urgent"])])
        ]
        with_labels = render_issues_report(results, format="table", labels=True)
        assert "Labels" in with_labels
        assert "bug, urgent" in with_labels
        without = render_issues_report(results, format="table")
        assert "Labels" not in without

    def test_long_description_truncated_in_table_not_plain(self):
        long_title = "x" * 100
        results = [_result("acme", "web", 1, [_item(1, long_title)])]
        table = render_issues_report(results, format="table")
        assert "…" in table
        assert long_title not in table
        plain = render_issues_report(results, format="plain")
        assert long_title in plain

    def test_omits_repos_without_open_items(self):
        results = [
            _result("acme", "web", 1, [_item(1, "Bug")]),
            _result("acme", "empty", 0, []),
        ]
        out = render_issues_report(results, format="table")
        assert "acme/web" in out
        assert "acme/empty" not in out


class TestIssuesReportJson:
    def test_structure_and_null_and_all_repos(self):
        results = [
            _result(
                "acme",
                "web",
                2,
                [
                    _item(12, "Fix login", "issue", ["bug"]),
                    _item(15, "Add retry", "pr"),
                ],
            ),
            _result("acme", "api", None, None),
        ]
        data = json.loads(render_issues_report(results, format="json"))
        assert data["summary"]["repos_scanned"] == 2
        assert data["summary"]["open_issues"] == 1
        assert data["summary"]["open_prs"] == 1
        repos = data["repositories"]
        assert len(repos) == 2  # every scanned repo included
        web = next(r for r in repos if r["repo"] == "web")
        assert web["repository"] == "acme/web"
        assert web["open_item_count"] == 2
        assert web["items"][0] == {"number": 12, "title": "Fix login", "type": "issue"}
        assert web["items"][1] == {"number": 15, "title": "Add retry", "type": "pr"}
        api = next(r for r in repos if r["repo"] == "api")
        assert api["open_item_count"] is None  # null preserved
        assert api["items"] == []

    def test_labels_gated_by_flag(self):
        results = [
            _result("acme", "web", 1, [_item(12, "Fix login", "pr", ["bug", "urgent"])])
        ]
        data = json.loads(render_issues_report(results, format="json", labels=True))
        item = data["repositories"][0]["items"][0]
        assert item == {
            "number": 12,
            "title": "Fix login",
            "type": "pr",
            "labels": ["bug", "urgent"],
        }

    def test_labels_absent_without_flag_type_still_present(self):
        results = [_result("acme", "web", 1, [_item(12, "Fix login", "pr", ["bug"])])]
        data = json.loads(render_issues_report(results, format="json"))
        item = data["repositories"][0]["items"][0]
        assert "labels" not in item
        assert item["type"] == "pr"

    def test_labels_enabled_item_without_labels_renders_empty(self):
        # Req 5.5: with --labels on, an item that has no labels renders an empty
        # suffix (plain), an empty column (table), and an empty array (JSON).
        results = [_result("acme", "web", 1, [_item(12, "Fix login", "issue", [])])]

        plain = render_issues_report(results, format="plain", labels=True)
        assert "  #12 [issue] Fix login\n" in plain  # no trailing "+label"

        table = render_issues_report(results, format="table", labels=True)
        assert "Labels" in table  # column present, but this item's cell is blank
        assert "+" not in table

        data = json.loads(render_issues_report(results, format="json", labels=True))
        assert data["repositories"][0]["items"][0]["labels"] == []


class TestIssuesReportOutput:
    def test_output_path_writes_file(self, tmp_path, capsys):
        results = [_result("acme", "web", 1, [_item(1, "Bug")])]
        path = tmp_path / "issues.txt"
        print_issues_report(results, output=path)
        assert "acme/web" in path.read_text(encoding="utf-8")
        assert capsys.readouterr().out == ""

    def test_unknown_format_raises(self):
        try:
            render_issues_report([], format="xml")
        except ValueError:
            return
        raise AssertionError("expected ValueError for unknown format")
