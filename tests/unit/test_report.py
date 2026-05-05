"""Tests for security report rendering."""

import json

from ghbot.processor import RepoResult
from ghbot.report import print_security_report, render_security_report


def _result(
    owner,
    repo,
    dependabot=None,
    code_scanning=None,
    secret_scanning=None,
    status="success",
):
    r = RepoResult(owner=owner, repo=repo, status=status)
    r.results["dependabot_alerts"] = dependabot
    r.results["code_scanning_alerts"] = code_scanning
    r.results["secret_scanning_alerts"] = secret_scanning
    return r


class TestPrintSecurityReportSummary:
    def test_empty_results_shows_zero_scanned(self, capsys):
        print_security_report([])
        out = capsys.readouterr().out
        assert "Repos scanned" in out
        assert "0" in out

    def test_scanned_count(self, capsys):
        results = [_result("o", "a", 1, 0, 0), _result("o", "b", 0, 0, 0)]
        print_security_report(results)
        out = capsys.readouterr().out
        assert "2" in out

    def test_repos_with_issues_count(self, capsys):
        results = [
            _result("o", "a", dependabot=3, code_scanning=0, secret_scanning=0),
            _result("o", "b", dependabot=0, code_scanning=0, secret_scanning=0),
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        assert "Repos with issues" in out
        # only repo a has issues
        lines = out.splitlines()
        issues_line = next(line for line in lines if "Repos with issues" in line)
        assert "1" in issues_line

    def test_dependabot_total(self, capsys):
        results = [
            _result("o", "a", dependabot=3, code_scanning=0, secret_scanning=0),
            _result("o", "b", dependabot=2, code_scanning=0, secret_scanning=0),
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        lines = out.splitlines()
        dep_line = next(
            line
            for line in lines
            if "Dependabot" in line and ":" in line and "owner" not in line.lower()
        )
        assert "5" in dep_line

    def test_all_none_for_type_shows_na(self, capsys):
        results = [
            _result("o", "a", dependabot=None, code_scanning=1, secret_scanning=0),
            _result("o", "b", dependabot=None, code_scanning=0, secret_scanning=0),
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        lines = out.splitlines()
        dep_line = next(
            line
            for line in lines
            if "Dependabot" in line and ":" in line and "owner" not in line.lower()
        )
        assert "N/A" in dep_line

    def test_mix_of_none_and_int_excludes_none_from_sum(self, capsys):
        results = [
            _result("o", "a", dependabot=None, code_scanning=3, secret_scanning=0),
            _result("o", "b", dependabot=2, code_scanning=1, secret_scanning=0),
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        lines = out.splitlines()
        dep_line = next(
            line
            for line in lines
            if "Dependabot" in line and ":" in line and "owner" not in line.lower()
        )
        # None excluded, only 2 counted
        assert "2" in dep_line
        assert "N/A" not in dep_line

    def test_nothing_on_stderr(self, capsys):
        print_security_report([_result("o", "a", 1, 0, 0)])
        err = capsys.readouterr().err
        assert err == ""


class TestPrintSecurityReportPerRepo:
    def test_repo_with_issues_appears_in_output(self, capsys):
        results = [
            _result("acme", "widgets", dependabot=5, code_scanning=2, secret_scanning=0)
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        assert "acme/widgets" in out

    def test_repo_without_issues_absent_from_per_repo_section(self, capsys):
        results = [
            _result(
                "acme", "widgets", dependabot=5, code_scanning=0, secret_scanning=0
            ),
            _result("acme", "clean", dependabot=0, code_scanning=0, secret_scanning=0),
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        assert "acme/widgets" in out
        assert "acme/clean" not in out

    def test_repo_with_all_none_absent_from_per_repo_section(self, capsys):
        results = [
            _result(
                "acme",
                "noaccess",
                dependabot=None,
                code_scanning=None,
                secret_scanning=None,
            )
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        assert "acme/noaccess" not in out

    def test_per_repo_shows_individual_counts(self, capsys):
        results = [
            _result("acme", "widgets", dependabot=5, code_scanning=2, secret_scanning=1)
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        assert "acme/widgets" in out
        assert "  Dependabot alerts:             5" in out
        assert "  Code scanning alerts:          2" in out
        assert "  Secret scanning alerts:        1" in out

    def test_no_issues_means_no_per_repo_section(self, capsys):
        results = [
            _result("acme", "clean", dependabot=0, code_scanning=0, secret_scanning=0)
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        assert "acme/clean" not in out
        assert "|Repository" not in out

    def test_repos_sorted_by_owner_repo(self, capsys):
        results = [
            _result(
                "z-owner", "repo", dependabot=1, code_scanning=0, secret_scanning=0
            ),
            _result(
                "a-owner", "repo", dependabot=1, code_scanning=0, secret_scanning=0
            ),
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        a_pos = out.index("a-owner/repo")
        z_pos = out.index("z-owner/repo")
        assert a_pos < z_pos

    def test_none_values_show_na_in_plain(self, capsys):
        results = [
            _result(
                "acme",
                "mixed",
                dependabot=None,
                code_scanning=2,
                secret_scanning=0,
            )
        ]
        print_security_report(results)
        out = capsys.readouterr().out
        assert "  Dependabot alerts:           N/A" in out
        assert "  Code scanning alerts:          2" in out
        assert "  Secret scanning alerts:        0" in out


class TestRenderSecurityReport:
    def test_table_format_uses_markdown_table(self):
        results = [
            _result("acme", "widgets", dependabot=5, code_scanning=2, secret_scanning=1)
        ]
        out = render_security_report(results, format="table")
        assert (
            "|Repository                            | Dependabot | Scanning | Secrets |"
            in out
        )
        assert (
            "|--------------------------------------|------------|----------|---------|"
            in out
        )
        assert (
            "|acme/widgets                          |           5|         2|        1|"
            in out
        )

    def test_table_format_shows_na(self):
        results = [
            _result(
                "acme",
                "mixed",
                dependabot=None,
                code_scanning=2,
                secret_scanning=0,
            )
        ]
        out = render_security_report(results, format="table")
        assert (
            "|acme/mixed                            |         N/A|         2|        0|"
            in out
        )

    def test_json_format_is_valid_json(self):
        out = render_security_report(
            [_result("acme", "widgets", 1, 2, 3)], format="json"
        )
        assert json.loads(out)

    def test_json_format_has_summary_and_repositories(self):
        out = render_security_report(
            [_result("acme", "widgets", 1, 2, 3)], format="json"
        )
        data = json.loads(out)
        assert set(data) == {"summary", "repositories"}
        assert data["summary"]["repos_scanned"] == 1
        assert data["summary"]["repos_with_issues"] == 1

    def test_json_format_includes_clean_repositories(self):
        results = [
            _result("acme", "widgets", 1, 0, 0),
            _result("acme", "clean", 0, 0, 0),
        ]
        out = render_security_report(results, format="json")
        data = json.loads(out)
        assert [r["repository"] for r in data["repositories"]] == [
            "acme/widgets",
            "acme/clean",
        ]

    def test_json_format_preserves_none_as_null(self):
        out = render_security_report(
            [_result("acme", "widgets", None, 2, 0)], format="json"
        )
        data = json.loads(out)
        assert data["repositories"][0]["dependabot_alerts"] is None

    def test_unknown_format_raises_value_error(self):
        try:
            render_security_report([], format="xml")
        except ValueError as e:
            assert "format" in str(e)
        else:
            raise AssertionError("expected ValueError")


class TestPrintSecurityReportOutput:
    def test_output_path_writes_report_to_file(self, tmp_path, capsys):
        output = tmp_path / "security.md"
        print_security_report([_result("acme", "widgets", 1, 0, 0)], output=output)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "acme/widgets" in output.read_text()

    def test_output_path_uses_requested_format(self, tmp_path):
        output = tmp_path / "security.json"
        print_security_report(
            [_result("acme", "widgets", 1, 0, 0)], format="json", output=output
        )
        assert json.loads(output.read_text())["summary"]["repos_scanned"] == 1
