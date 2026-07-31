from unittest.mock import AsyncMock, patch

import pytest

from ghbot.errors import GitHubNotFoundError
from ghbot.github.repos import list_repos, scan_repositories


def _make_gh(pages: list[list[dict]]):
    """Return a mock GitHubAPI whose getiter yields repos from pages."""

    async def _getiter(url, url_vars=None):
        for page in pages:
            for repo in page:
                yield repo

    gh = AsyncMock()
    gh.getiter = _getiter
    return gh


@pytest.mark.anyio
async def test_list_repos_single_page():
    repos = [{"name": "repo1"}, {"name": "repo2"}]
    gh = _make_gh([repos])
    result = [r async for r in list_repos("owner1", gh)]
    assert result == repos


@pytest.mark.anyio
async def test_list_repos_multi_page():
    page1 = [{"name": "repo1"}, {"name": "repo2"}]
    page2 = [{"name": "repo3"}]
    gh = _make_gh([page1, page2])
    result = [r async for r in list_repos("owner1", gh)]
    assert result == page1 + page2


@pytest.mark.anyio
async def test_list_repos_uses_type_all():
    captured = {}

    async def _getiter(url, url_vars=None):
        captured["url_vars"] = url_vars
        return
        yield

    gh = AsyncMock()
    gh.getiter = _getiter
    _ = [r async for r in list_repos("owner1", gh)]
    assert captured.get("url_vars", {}).get("type") == "all"


@pytest.mark.anyio
async def test_list_repos_not_found_logs_warning_and_skips(caplog):
    import logging

    gh = AsyncMock()

    with patch("ghbot.github.repos.github_api_call") as mock_cm:
        mock_cm.return_value.__aenter__ = AsyncMock(
            side_effect=GitHubNotFoundError("not found")
        )
        mock_cm.return_value.__aexit__ = AsyncMock(return_value=False)
        with caplog.at_level(logging.WARNING):
            result = [r async for r in list_repos("ghost", gh)]

    assert result == []
    assert any("ghost" in r.message for r in caplog.records)


@pytest.mark.anyio
async def test_scan_repositories_yields_owner_repo_tuples():
    async def _stub(owner, gh):
        for repo in [{"name": "alpha"}, {"name": "beta"}]:
            yield repo

    with patch("ghbot.github.repos.list_repos", side_effect=_stub):
        gh = AsyncMock()
        result = [(o, r) async for o, r in scan_repositories(["myorg"], gh)]

    assert result == [("myorg", {"name": "alpha"}), ("myorg", {"name": "beta"})]


@pytest.mark.anyio
async def test_scan_repositories_multiple_owners():
    async def _stub(owner, gh):
        yield {"name": f"{owner}-repo"}

    with patch("ghbot.github.repos.list_repos", side_effect=_stub):
        gh = AsyncMock()
        result = [
            (o, r["name"]) async for o, r in scan_repositories(["org1", "org2"], gh)
        ]

    assert result == [("org1", "org1-repo"), ("org2", "org2-repo")]


@pytest.mark.anyio
async def test_scan_repositories_empty_owners_warns(caplog):
    import logging

    gh = AsyncMock()
    with caplog.at_level(logging.WARNING):
        result = [(o, r) async for o, r in scan_repositories([], gh)]
    assert result == []
    assert any("owner" in r.message.lower() for r in caplog.records)


@pytest.mark.anyio
async def test_list_repos_retries_once_on_api_error():
    from ghbot.errors import GitHubApiError

    call_count = 0

    async def _getiter(url, url_vars=None):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise GitHubApiError("api error")
        yield {"name": "repo1"}

    gh = AsyncMock()
    gh.getiter = _getiter

    result = [r async for r in list_repos("owner1", gh)]

    assert result == [{"name": "repo1"}]
    assert call_count == 2


@pytest.mark.anyio
async def test_list_repos_second_api_error_logs_and_skips(caplog):
    import logging

    from ghbot.errors import GitHubApiError

    call_count = 0

    async def _getiter(url, url_vars=None):
        nonlocal call_count
        call_count += 1
        raise GitHubApiError("api error")
        yield  # make it a generator

    gh = AsyncMock()
    gh.getiter = _getiter

    with caplog.at_level(logging.ERROR):
        result = [r async for r in list_repos("owner1", gh)]

    assert result == []
    assert call_count == 2
    assert any("owner1" in r.message for r in caplog.records)
