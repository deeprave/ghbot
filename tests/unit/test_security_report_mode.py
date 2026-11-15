import json

from ghbot.processor import RepoResult


def test_security_mode_unit_pairs_processor_with_collection_report():
    from ghbot.modes.security import (
        MODE,
        SecurityCollectionReport,
        SecurityRepoProcessor,
    )

    assert MODE.name == "security"
    assert MODE.processor_type is SecurityRepoProcessor
    assert isinstance(MODE.new_collection({}), SecurityCollectionReport)


def test_security_collection_aggregates_results():
    from ghbot.modes.security import MODE
    from ghbot.report_style import PlainReportStyle

    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "dependabot_alerts": 2,
            "code_scanning_alerts": 0,
            "secret_scanning_alerts": 0,
            "dependabot_open_pull_requests": 0,
            "dependabot_ready_pull_requests": 0,
        }
    )
    report = MODE.new_collection({})
    report.add(result)

    assert report.document()["summary"]["dependabot_alerts"] == 2
    assert "acme/api" in report.render(PlainReportStyle())


def test_security_collection_plain_output_matches_existing_contract():
    from ghbot.modes.security import MODE, SecurityCollectionReport
    from ghbot.report_style import PlainReportStyle

    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "dependabot_alerts": 2,
            "code_scanning_alerts": None,
            "secret_scanning_alerts": 1,
            "dependabot_open_pull_requests": 3,
            "dependabot_ready_pull_requests": 2,
        }
    )
    report = MODE.new_collection({})
    report.add(result)

    assert report.render(PlainReportStyle()) == SecurityCollectionReport(
        results=[result]
    ).render("plain")


def test_security_collection_table_output_matches_existing_contract():
    from ghbot.modes.security import MODE, SecurityCollectionReport
    from ghbot.report_style import MarkdownTableReportStyle

    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "dependabot_alerts": 2,
            "code_scanning_alerts": None,
            "secret_scanning_alerts": 1,
            "dependabot_open_pull_requests": 3,
            "dependabot_ready_pull_requests": 2,
        }
    )
    report = MODE.new_collection({})
    report.add(result)

    assert report.render(MarkdownTableReportStyle()) == SecurityCollectionReport(
        results=[result]
    ).render("table")


def test_security_collection_json_document_matches_existing_contract():
    from ghbot.modes.security import MODE, SecurityCollectionReport
    from ghbot.report_style import JSONReportStyle

    result = RepoResult(owner="acme", repo="api")
    result.results.update(
        {
            "dependabot_alerts": 2,
            "code_scanning_alerts": None,
            "secret_scanning_alerts": 1,
            "dependabot_open_pull_requests": 3,
            "dependabot_ready_pull_requests": 2,
        }
    )
    report = MODE.new_collection({})
    report.add(result)

    assert json.loads(report.render(JSONReportStyle())) == json.loads(
        SecurityCollectionReport(results=[result]).render("json")
    )
