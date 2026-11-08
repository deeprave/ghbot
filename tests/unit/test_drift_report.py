import json

from ghbot.processor import RepoResult
from ghbot.report import render_drift_report


def _result(
    owner: str,
    repo: str,
    commits: int | None,
    *,
    release: str | None = "v1.0.0",
    branch: str | None = "main",
    pypi: bool | None = False,
) -> RepoResult:
    result = RepoResult(owner=owner, repo=repo)
    result.results.update(
        {
            "latest_release_tag": release,
            "latest_release_published_at": "2026-11-01T00:00:00Z",
            "default_branch": branch,
            "commits_since_release": commits,
            "pypi_publishing_configured": pypi,
        }
    )
    return result


def test_plain_report_filters_non_reportable_repositories_and_summarises():
    text = render_drift_report(
        [_result("acme", "changed", 3), _result("acme", "current", 0)]
    )

    assert "Repos scanned:" in text
    assert "Released repos:" in text
    assert "Repos with drift:" in text
    assert "Commits since release:" in text
    assert "Release published:" in text
    assert "2026-11-01T00:00:00Z" in text
    assert "acme/changed" in text
    assert "acme/current" not in text


def test_table_report_sorts_repositories_and_displays_unknown_pypi():
    text = render_drift_report(
        [_result("z", "repo", 1), _result("a", "repo", 2, pypi=None)],
        format="table",
    )

    assert "|Repository" in text
    assert "Published" in text
    assert "2026-11-01T00:00:00Z" in text
    assert text.index("a/repo") < text.index("z/repo")
    assert "N/A" in text


def test_human_reports_render_missing_release_publication_time_as_na():
    result = _result("acme", "changed", 1)
    result.results["latest_release_published_at"] = None

    assert "N/A" in render_drift_report([result])
    assert "N/A" in render_drift_report([result], format="table")


def test_json_report_contains_only_reportable_repositories_and_null_pypi():
    text = render_drift_report(
        [_result("acme", "changed", 5, pypi=None), _result("acme", "current", 0)],
        format="json",
    )

    payload = json.loads(text)
    assert payload["summary"]["repos_scanned"] == 2
    assert payload["summary"]["repos_with_drift"] == 1
    assert payload["summary"]["commits_since_release"] == 5
    assert payload["repositories"] == [
        {
            "owner": "acme",
            "repo": "changed",
            "repository": "acme/changed",
            "default_branch": "main",
            "latest_release_tag": "v1.0.0",
            "latest_release_published_at": "2026-11-01T00:00:00Z",
            "commits_since_release": 5,
            "pypi_publishing_configured": None,
        }
    ]
