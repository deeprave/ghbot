"""Tests for the cohesive issues mode unit and collection report."""

from ghbot.modes.issues import MODE, IssuesCollectionReport, IssuesRepoProcessor
from ghbot.processor import RepoProcessor, RepoResult


def _result() -> RepoResult:
    result = RepoResult(owner="acme", repo="web")
    result.results.update(
        {
            "open_item_count": 1,
            "open_items": [
                {
                    "number": 12,
                    "title": "Fix login",
                    "type": "issue",
                    "labels": ["bug"],
                }
            ],
        }
    )
    return result


def test_mode_owns_issues_processor_and_collection_options():
    assert MODE.name == "issues"
    assert MODE.processor_type is IssuesRepoProcessor
    assert isinstance(IssuesRepoProcessor("a", "b", None, None), RepoProcessor)
    assert MODE.new_collection({"labels": True}).labels is True


def test_collection_aggregates_and_renders_labels_by_style():
    collection = IssuesCollectionReport(labels=True)
    collection.add(_result())

    assert collection.document()["summary"] == {
        "repos_scanned": 1,
        "repos_with_items": 1,
        "open_issues": 1,
        "open_prs": 0,
    }
    assert "+bug" in collection.render("plain")
    assert "Labels" in collection.render("table")
    assert '"labels": [' in collection.render("json")
