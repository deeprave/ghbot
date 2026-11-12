from pathlib import Path


def test_changelog_documents_drift_and_owner_type_api_change():
    """The changelog records the recent feature and processor API change."""
    changelog = Path("CHANGELOG.md").read_text()

    assert "## [0.10.0]" in changelog
    assert "drift" in changelog.lower()
    assert "## [Unreleased]" in changelog
    assert "owner_type" in changelog
    assert "breaking" in changelog.lower()
