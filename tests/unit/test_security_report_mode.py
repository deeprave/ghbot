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
