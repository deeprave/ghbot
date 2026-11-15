"""Tests for the cohesive drift mode unit and collection report."""

from ghbot.modes.drift import MODE, DriftCollectionReport, DriftRepoProcessor
from ghbot.processor import RepoProcessor, RepoResult


def test_mode_owns_drift_processor_and_collection():
    assert MODE.name == "drift"
    assert MODE.processor_type is DriftRepoProcessor
    assert isinstance(DriftRepoProcessor("a", "b", None, None), RepoProcessor)
    assert isinstance(MODE.new_collection({}), DriftCollectionReport)


def test_collection_filters_positive_drift_and_preserves_pypi_null():
    report = DriftCollectionReport()
    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "latest_release_tag": "v1.0",
            "latest_release_published_at": None,
            "default_branch": "main",
            "commits_since_release": 2,
            "pypi_publishing_configured": None,
        }
    )
    report.add(result)

    assert report.document()["summary"]["repos_with_drift"] == 1
    assert "N/A" in report.render("plain")
    assert report.document()["repositories"][0]["pypi_publishing_configured"] is None
