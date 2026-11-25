"""Contract tests for packaged report schemas."""

import json

import pytest
from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry, Resource

from ghbot.modes.drift import DriftCollectionReport
from ghbot.modes.issues import IssuesCollectionReport
from ghbot.modes.security import SecurityCollectionReport
from ghbot.processor import RepoResult, record_unavailable
from ghbot.report_style import CombinedCollectionReport, ReportSection
from ghbot.schemas import current_schema, schema_for_id, schema_ids


def _registry() -> Registry:
    return Registry().with_resources(
        (schema_id, Resource.from_contents(schema_for_id(schema_id)))
        for schema_id in schema_ids()
    )


@pytest.mark.parametrize(
    "schema_id",
    [
        "ghbot://schemas/security/1.0.json",
        "ghbot://schemas/issues/1.0.json",
        "ghbot://schemas/drift/1.0.json",
    ],
)
def test_standalone_schema_rejects_a_document_missing_required_report_fields(schema_id):
    document = {"summary": {}}

    with pytest.raises(ValidationError):
        Draft202012Validator(schema_for_id(schema_id)).validate(document)


def test_combined_schema_rejects_a_document_missing_required_report_sections():
    document = {"security": {}}

    with pytest.raises(ValidationError):
        Draft202012Validator(
            schema_for_id("ghbot://schemas/combined/1.0.json"), registry=_registry()
        ).validate(document)


def test_combined_schema_resolves_nested_schemas_from_the_local_registry():
    document = CombinedCollectionReport(
        (
            ReportSection("security", SecurityCollectionReport()),
            ReportSection("issues", IssuesCollectionReport()),
            ReportSection("drift", DriftCollectionReport()),
        )
    ).document()

    Draft202012Validator(
        schema_for_id("ghbot://schemas/combined/1.0.json"), registry=_registry()
    ).validate(document)


def test_combined_schema_rejects_an_invalid_nested_document():
    document = CombinedCollectionReport(
        (
            ReportSection("security", SecurityCollectionReport()),
            ReportSection("issues", IssuesCollectionReport()),
            ReportSection("drift", DriftCollectionReport()),
        )
    ).document()
    document["security"]["summary"]["repos_scanned"] = "invalid"

    with pytest.raises(ValidationError):
        Draft202012Validator(
            schema_for_id("ghbot://schemas/combined/1.0.json"), registry=_registry()
        ).validate(document)


def test_combined_schema_validates_populated_partial_output():
    result = RepoResult(owner="acme", repo="api", status="partial")
    result.results.update(
        {
            "dependabot_alerts": None,
            "code_scanning_alerts": 1,
            "secret_scanning_alerts": 0,
            "dependabot_open_pull_requests": None,
            "dependabot_ready_pull_requests": None,
        }
    )
    document = CombinedCollectionReport(
        (
            ReportSection("security", SecurityCollectionReport([result])),
            ReportSection("issues", IssuesCollectionReport()),
            ReportSection("drift", DriftCollectionReport()),
        )
    ).document()

    Draft202012Validator(
        schema_for_id("ghbot://schemas/combined/1.0.json"), registry=_registry()
    ).validate(document)


@pytest.mark.parametrize("schema_id", schema_ids())
def test_packaged_schema_is_a_valid_draft_2020_12_schema(schema_id):
    Draft202012Validator.check_schema(schema_for_id(schema_id))


@pytest.mark.parametrize(
    ("report", "document"),
    [
        ("security", SecurityCollectionReport().document()),
        ("issues", IssuesCollectionReport().document()),
        ("drift", DriftCollectionReport().document()),
    ],
)
def test_standalone_schemas_allow_additive_top_level_properties(report, document):
    document["future_field"] = True
    Draft202012Validator(current_schema(report)).validate(document)


def test_json_rendering_preserves_collection_document_shape():
    collections = (
        SecurityCollectionReport(),
        IssuesCollectionReport(),
        DriftCollectionReport(),
    )

    for collection in collections:
        assert json.loads(collection.render("json")) == collection.document()


@pytest.mark.parametrize(
    ("report", "document"),
    [
        ("security", SecurityCollectionReport().document()),
        ("issues", IssuesCollectionReport().document()),
        ("drift", DriftCollectionReport().document()),
    ],
)
def test_current_schema_validates_real_empty_collection_output(report, document):
    Draft202012Validator(current_schema(report)).validate(document)


def test_security_schema_validates_a_real_current_collection_output():
    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "dependabot_alerts": 1,
            "code_scanning_alerts": 2,
            "secret_scanning_alerts": 3,
            "dependabot_open_pull_requests": 4,
            "dependabot_ready_pull_requests": 5,
        }
    )
    report = SecurityCollectionReport([result]).document()

    Draft202012Validator(current_schema("security")).validate(report)


def test_issues_schema_validates_a_real_current_collection_output():
    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "open_item_count": 1,
            "open_items": [
                {
                    "number": 1,
                    "title": "Update dependency",
                    "type": "pr",
                    "created_at": "2026-11-23T00:00:00Z",
                    "updated_at": "2026-11-23T00:00:00Z",
                    "url": "https://example.test/pull/1",
                    "author": "dependabot[bot]",
                    "draft": False,
                    "labels": ["dependencies"],
                }
            ],
            "dependabot_open_pull_requests": 1,
            "dependabot_merge_ready_pull_requests": 1,
            "other_open_pull_requests": 0,
            "other_merge_ready_pull_requests": 0,
            "oldest_dependabot_pull_request_created_at": "2026-11-23T00:00:00Z",
            "oldest_other_pull_request_created_at": None,
            "dependabot_pull_requests": [
                {
                    "number": 1,
                    "url": "https://example.test/pull/1",
                    "created_at": "2026-11-23T00:00:00Z",
                    "draft": False,
                    "merge_ready": True,
                }
            ],
        }
    )
    report = IssuesCollectionReport(labels=True, results=[result]).document()

    Draft202012Validator(current_schema("issues")).validate(report)


def test_drift_schema_validates_a_real_current_collection_output():
    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "default_branch": "main",
            "latest_release_tag": "v1.0.0",
            "latest_release_published_at": "2026-11-01T00:00:00Z",
            "commits_since_release": 2,
            "pypi_publishing_configured": True,
        }
    )
    report = DriftCollectionReport([result]).document()

    Draft202012Validator(current_schema("drift")).validate(report)


@pytest.mark.parametrize(
    ("report", "collection_type"),
    [
        ("security", SecurityCollectionReport),
        ("issues", IssuesCollectionReport),
        ("drift", DriftCollectionReport),
    ],
)
def test_current_schemas_validate_unavailable_reasons_and_reject_unknown_ones(
    report, collection_type
):
    result = RepoResult(
        owner="acme", repo="private", status="failed", reason="forbidden"
    )
    record_unavailable(result, "repository", reason="forbidden")
    document = collection_type(results=[result]).document()

    validator = Draft202012Validator(current_schema(report))
    validator.validate(document)
    document["repositories"][0]["unavailable"]["repository"]["reason"] = "unknown"
    with pytest.raises(ValidationError):
        validator.validate(document)


@pytest.mark.parametrize(
    ("report", "document"),
    [
        ("security", SecurityCollectionReport([RepoResult("acme", "api")]).document()),
        (
            "issues",
            IssuesCollectionReport(results=[RepoResult("acme", "api")]).document(),
        ),
        ("drift", DriftCollectionReport([RepoResult("acme", "api")]).document()),
    ],
)
def test_current_schema_validates_real_unavailable_collection_output(report, document):
    Draft202012Validator(current_schema(report)).validate(document)


def test_security_schema_validates_a_partial_real_collection_output():
    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "dependabot_alerts": None,
            "code_scanning_alerts": 0,
            "secret_scanning_alerts": 1,
            "dependabot_open_pull_requests": None,
            "dependabot_ready_pull_requests": None,
        }
    )
    report = SecurityCollectionReport([result]).document()

    Draft202012Validator(current_schema("security")).validate(report)


def test_issues_schema_validates_a_partial_real_collection_output():
    result = RepoResult(owner="acme", repo="api", status="partial")
    result.results.update(
        {
            "open_item_count": 1,
            "open_items": [
                {
                    "number": 1,
                    "title": "Update dependency",
                    "type": "pr",
                    "created_at": "2026-11-23T00:00:00Z",
                    "updated_at": "2026-11-23T00:00:00Z",
                    "url": "https://example.test/pull/1",
                    "author": "dependabot[bot]",
                    "draft": False,
                }
            ],
            "dependabot_open_pull_requests": None,
            "dependabot_merge_ready_pull_requests": None,
            "other_open_pull_requests": None,
            "other_merge_ready_pull_requests": None,
            "oldest_dependabot_pull_request_created_at": None,
            "oldest_other_pull_request_created_at": None,
            "dependabot_pull_requests": None,
        }
    )
    report = IssuesCollectionReport(results=[result]).document()

    Draft202012Validator(current_schema("issues")).validate(report)


def test_drift_schema_validates_a_partial_real_collection_output():
    result = RepoResult(owner="acme", repo="api", status="partial")
    result.results.update(
        {
            "default_branch": "main",
            "latest_release_tag": "v1.0.0",
            "latest_release_published_at": "2026-11-01T00:00:00Z",
            "commits_since_release": 2,
            "pypi_publishing_configured": None,
        }
    )
    report = DriftCollectionReport([result]).document()

    Draft202012Validator(current_schema("drift")).validate(report)


@pytest.mark.parametrize(
    ("report", "document", "path"),
    [
        (
            "security",
            SecurityCollectionReport().document(),
            ("summary", "repos_scanned"),
        ),
        (
            "issues",
            IssuesCollectionReport().document(),
            ("summary", "pull_request_metrics_complete"),
        ),
        (
            "drift",
            DriftCollectionReport().document(),
            ("summary", "commits_since_release"),
        ),
    ],
)
def test_identity_selected_schema_rejects_invalid_real_document_field(
    report, document, path
):
    parent, field = path
    document[parent][field] = "invalid"

    with pytest.raises(ValidationError):
        Draft202012Validator(current_schema(report)).validate(document)
