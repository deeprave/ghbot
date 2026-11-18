"""Tests for issues report rendering (issues + pull requests, tagged by type)."""

import json
import os
import time

from ghbot.modes.issues import IssuesCollectionReport
from ghbot.processor import RepoResult
from ghbot.report_style import write_report

PULL_REQUEST_METRIC_KEYS = (
    "dependabot_open_pull_requests",
    "dependabot_merge_ready_pull_requests",
    "other_open_pull_requests",
    "other_merge_ready_pull_requests",
)
PULL_REQUEST_AGE_METRIC_KEYS = (
    "oldest_dependabot_pull_request_created_at",
    "oldest_other_pull_request_created_at",
)


def render_issues_report(results, *, format="plain", labels=False):
    return IssuesCollectionReport(labels=labels, results=list(results)).render(format)


def print_issues_report(results, *, format="plain", labels=False, output=None):
    write_report(render_issues_report(results, format=format, labels=labels), output)


def _item(number, title, type="issue", labels=None, **metadata):
    return {
        "number": number,
        "title": title,
        "type": type,
        "labels": labels or [],
        "created_at": metadata.get("created_at"),
        "updated_at": metadata.get("updated_at"),
        "url": metadata.get("url"),
        "author": metadata.get("author"),
        "draft": metadata.get("draft") if type == "pr" else None,
    }


def _result(owner, repo, count=None, items=None, status="success", metrics=None):
    r = RepoResult(owner=owner, repo=repo, status=status)
    r.results["open_item_count"] = count
    r.results["open_items"] = items
    if metrics is not None:
        r.results.update(metrics)
    return r


def _metrics(dependabot_total, dependabot_ready, other_total, other_ready):
    return dict(
        zip(
            PULL_REQUEST_METRIC_KEYS,
            (dependabot_total, dependabot_ready, other_total, other_ready),
            strict=True,
        )
    )


def _age_metrics(dependabot_oldest, other_oldest):
    return dict(
        zip(
            PULL_REQUEST_AGE_METRIC_KEYS,
            (dependabot_oldest, other_oldest),
            strict=True,
        )
    )


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

    def test_summary_includes_pull_request_category_metrics(self, capsys):
        results = [
            _result(
                "o",
                "a",
                1,
                [_item(1, "Bug")],
                metrics=_metrics(2, 1, 3, 2),
            ),
            _result("o", "b", 0, [], metrics=_metrics(0, 0, 0, 0)),
        ]

        print_issues_report(results)

        lines = capsys.readouterr().out.splitlines()
        assert next(line for line in lines if line.startswith("Dependabot PRs:")) == (
            f"{'Dependabot PRs:':<26}{2:>8}"
        )
        assert (
            next(
                line for line in lines if line.startswith("Dependabot merge-ready PRs:")
            )
            == f"{'Dependabot merge-ready PRs:':<26}{1:>8}"
        )
        assert next(line for line in lines if line.startswith("Other PRs:")) == (
            f"{'Other PRs:':<26}{3:>8}"
        )
        assert (
            next(line for line in lines if line.startswith("Other merge-ready PRs:"))
            == f"{'Other merge-ready PRs:':<26}{2:>8}"
        )

    def test_summary_notifies_when_pull_request_metrics_are_incomplete(self, capsys):
        print_issues_report(
            [
                _result(
                    "o", "available", 1, [_item(1, "Bug")], metrics=_metrics(2, 1, 3, 2)
                ),
                _result(
                    "o",
                    "unavailable",
                    1,
                    [_item(2, "Bug")],
                    metrics=_metrics(None, None, None, None),
                ),
            ]
        )

        output = capsys.readouterr().out
        assert "Pull-request metrics unavailable: incomplete repository data" in output
        assert "N/A" in next(
            line for line in output.splitlines() if line.startswith("Dependabot PRs:")
        )


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

    def test_includes_pull_request_metrics_for_each_displayed_repository(self):
        results = [
            _result(
                "acme",
                "web",
                1,
                [_item(1, "Bug")],
                metrics=_metrics(2, 1, 3, 2),
            )
        ]

        out = render_issues_report(results, format="plain")

        repository_block = out.split("acme/web", maxsplit=1)[1]
        assert f"  {'Dependabot PRs:':<26}{2:>8}" in repository_block
        assert f"  {'Dependabot merge-ready PRs:':<26}{1:>8}" in repository_block
        assert f"  {'Other PRs:':<26}{3:>8}" in repository_block
        assert f"  {'Other merge-ready PRs:':<26}{2:>8}" in repository_block

    def test_dates_render_in_operator_local_timezone_and_compose_with_labels(
        self, monkeypatch
    ):
        original_tz = os.environ.get("TZ")
        original_timezone = time.tzname
        monkeypatch.setenv("TZ", "Australia/Melbourne")
        time.tzset()
        try:
            report = IssuesCollectionReport(
                labels=True,
                dates=True,
                results=[
                    _result(
                        "acme",
                        "web",
                        1,
                        [
                            _item(
                                12,
                                "Fix login",
                                labels=["bug"],
                                created_at="2026-01-01T00:20:30Z",
                            )
                        ],
                    )
                ],
            )
            plain = report.render("plain")
            table = report.render("table")
        finally:
            if original_tz is None:
                monkeypatch.delenv("TZ", raising=False)
            else:
                monkeypatch.setenv("TZ", original_tz)
            time.tzset()

        assert "#12 [issue] 2026-01-01 11:20 AEDT Fix login +bug" in plain
        assert "Created (local)" in table
        assert "2026-01-01 11:20 AEDT" in table
        assert original_timezone == time.tzname

    def test_dates_render_aest_in_winter(self, monkeypatch):
        original_tz = os.environ.get("TZ")
        monkeypatch.setenv("TZ", "Australia/Melbourne")
        time.tzset()
        try:
            report = IssuesCollectionReport(
                dates=True,
                results=[
                    _result(
                        "acme",
                        "web",
                        1,
                        [
                            _item(
                                12,
                                "Fix login",
                                created_at="2026-06-01T00:20:30Z",
                            )
                        ],
                    )
                ],
            )
            plain = report.render("plain")
        finally:
            if original_tz is None:
                monkeypatch.delenv("TZ", raising=False)
            else:
                monkeypatch.setenv("TZ", original_tz)
            time.tzset()

        assert "#12 [issue] 2026-06-01 10:20 AEST Fix login" in plain


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

    def test_includes_pull_request_metric_columns_and_values(self):
        results = [
            _result(
                "acme",
                "web",
                1,
                [_item(1, "Bug")],
                metrics=_metrics(2, 1, 3, 2),
            )
        ]

        out = render_issues_report(results, format="table")

        assert "Dependabot PRs" in out
        assert "Dependabot ready" in out
        assert "Other PRs" in out
        assert "Other ready" in out
        row = next(line for line in out.splitlines() if "acme/web" in line)
        cells = [cell.strip() for cell in row.split("|")[1:-1]]
        assert cells[4:] == ["2", "1", "3", "2"]


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
        assert web["items"][0] == {
            "number": 12,
            "title": "Fix login",
            "type": "issue",
            "created_at": None,
            "updated_at": None,
            "url": None,
            "author": None,
            "draft": None,
        }
        assert web["items"][1] == {
            "number": 15,
            "title": "Add retry",
            "type": "pr",
            "created_at": None,
            "updated_at": None,
            "url": None,
            "author": None,
            "draft": None,
        }
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
            "created_at": None,
            "updated_at": None,
            "url": None,
            "author": None,
            "draft": None,
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

    def test_includes_pull_request_metrics_and_nulls(self):
        results = [
            _result(
                "acme",
                "web",
                1,
                [_item(1, "Bug")],
                metrics=_metrics(2, 1, 3, 2),
            ),
            _result(
                "acme",
                "unavailable",
                None,
                None,
                metrics=_metrics(None, None, None, None),
            ),
        ]

        data = json.loads(render_issues_report(results, format="json"))

        assert {
            key: data["summary"][key] for key in PULL_REQUEST_METRIC_KEYS
        } == _metrics(None, None, None, None)
        assert data["summary"]["pull_request_metrics_complete"] is False
        unavailable = next(
            repository
            for repository in data["repositories"]
            if repository["repo"] == "unavailable"
        )
        assert {key: unavailable[key] for key in PULL_REQUEST_METRIC_KEYS} == _metrics(
            None, None, None, None
        )

    def test_includes_metadata_dependabot_detail_and_oldest_timestamps(self):
        result = _result(
            "acme",
            "web",
            1,
            [
                _item(
                    12,
                    "Fix login",
                    "pr",
                    created_at="2026-11-01T10:20:30Z",
                    updated_at="2026-11-02T10:20:30Z",
                    url="https://github.com/acme/widgets/pull/12",
                    author="dependabot[bot]",
                    draft=False,
                )
            ],
            metrics={
                **_metrics(1, 1, 2, 1),
                **_age_metrics("2026-11-01T10:20:30Z", "2026-11-02T10:20:30Z"),
                "dependabot_pull_requests": [
                    {
                        "number": 12,
                        "url": "https://github.com/acme/widgets/pull/12",
                        "created_at": "2026-11-01T10:20:30Z",
                        "draft": False,
                        "merge_ready": True,
                    }
                ],
            },
        )

        data = json.loads(render_issues_report([result], format="json"))

        repository = data["repositories"][0]
        assert repository["items"][0]["author"] == "dependabot[bot]"
        assert (
            repository["dependabot_pull_requests"]
            == result.results["dependabot_pull_requests"]
        )
        assert {
            key: repository[key] for key in PULL_REQUEST_AGE_METRIC_KEYS
        } == _age_metrics("2026-11-01T10:20:30Z", "2026-11-02T10:20:30Z")
        assert {
            key: data["summary"][key] for key in PULL_REQUEST_AGE_METRIC_KEYS
        } == _age_metrics("2026-11-01T10:20:30Z", "2026-11-02T10:20:30Z")


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
