from unittest.mock import AsyncMock, patch

import pytest

from ghbot.errors import (
    GitHubApiError,
    GitHubNotFoundError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.repos import DiscoveredRepository, list_repos, scan_repositories


def _make_gh(pages: list[list[dict]], owner_type: str = "User"):
    """Return a mock GitHubAPI whose getiter yields repos from pages."""

    async def _getiter(url, url_vars=None):
        for page in pages:
            for repo in page:
                yield repo

    gh = AsyncMock()
    gh.getiter = _getiter
    gh.getitem = AsyncMock(return_value={"type": owner_type})
    return gh


@pytest.mark.anyio
async def test_list_repos_single_page():
    repos = [{"name": "repo1"}, {"name": "repo2"}]
    gh = _make_gh([repos])
    result = [r async for r in list_repos("owner1", gh)]
    assert [discovered.metadata for discovered in result] == repos
    assert all(discovered.owner_type == "User" for discovered in result)


@pytest.mark.anyio
async def test_list_repos_multi_page():
    page1 = [{"name": "repo1"}, {"name": "repo2"}]
    page2 = [{"name": "repo3"}]
    gh = _make_gh([page1, page2])
    result = [r async for r in list_repos("owner1", gh)]
    assert [discovered.metadata for discovered in result] == page1 + page2


@pytest.mark.anyio
async def test_list_repos_uses_type_all():
    captured = {}

    async def _getiter(url, url_vars=None):
        captured["url_vars"] = url_vars
        return
        yield

    gh = AsyncMock()
    gh.getitem = AsyncMock(return_value={"type": "User"})
    gh.getiter = _getiter
    _ = [r async for r in list_repos("owner1", gh)]
    assert captured.get("url_vars", {}).get("type") == "all"


@pytest.mark.anyio
async def test_list_repos_uses_user_endpoint_for_user_owner():
    captured = {}

    async def _getiter(url, url_vars=None):
        captured["url"] = url
        captured["url_vars"] = url_vars
        yield {"name": "personal"}

    gh = AsyncMock()
    gh.getitem = AsyncMock(return_value={"type": "User"})
    gh.getiter = _getiter

    result = [item async for item in list_repos("alice", gh)]

    assert captured == {
        "url": "/users/{owner}/repos",
        "url_vars": {"owner": "alice", "type": "all"},
    }
    assert result[0].owner_type == "User"


@pytest.mark.anyio
async def test_list_repos_uses_organisation_endpoint_for_organisation_owner():
    captured = {}

    async def _getiter(url, url_vars=None):
        captured["url"] = url
        captured["url_vars"] = url_vars
        yield {"name": "private", "private": True}

    gh = AsyncMock()
    gh.getitem = AsyncMock(return_value={"type": "Organization"})
    gh.getiter = _getiter

    result = [item async for item in list_repos("acme", gh)]

    assert captured == {
        "url": "/orgs/{owner}/repos",
        "url_vars": {"owner": "acme", "type": "all"},
    }
    assert result[0].owner_type == "Organization"


@pytest.mark.anyio
async def test_list_repos_preserves_unknown_owner_type_as_none(caplog):
    import logging

    captured = {}

    async def _getiter(url, url_vars=None):
        captured["url"] = url
        yield {"name": "legacy"}

    gh = AsyncMock()
    gh.getitem = AsyncMock(return_value={"type": "Bot"})
    gh.getiter = _getiter

    with caplog.at_level(logging.WARNING):
        result = [item async for item in list_repos("legacy-owner", gh)]

    assert captured["url"] == "/users/{owner}/repos"
    assert result[0].owner_type is None
    assert any("Unknown owner type" in record.message for record in caplog.records)


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
            yield DiscoveredRepository(owner, repo, "Organization")

    with patch("ghbot.github.repos.list_repos", side_effect=_stub):
        gh = AsyncMock()
        result = [
            (item.owner, item.metadata)
            async for item in scan_repositories(["myorg"], gh)
        ]

    assert result == [("myorg", {"name": "alpha"}), ("myorg", {"name": "beta"})]


@pytest.mark.anyio
async def test_scan_repositories_multiple_owners():
    async def _stub(owner, gh):
        yield DiscoveredRepository(owner, {"name": f"{owner}-repo"}, "Organization")

    with patch("ghbot.github.repos.list_repos", side_effect=_stub):
        gh = AsyncMock()
        result = [
            (item.owner, item.name)
            async for item in scan_repositories(["org1", "org2"], gh)
        ]

    assert result == [("org1", "org1-repo"), ("org2", "org2-repo")]


@pytest.mark.anyio
async def test_scan_repositories_skips_archived_repositories():
    async def _stub(owner, gh):
        yield DiscoveredRepository(owner, {"name": "active", "archived": False}, "User")
        yield DiscoveredRepository(
            owner, {"name": "archived", "archived": True}, "User"
        )
        yield DiscoveredRepository(owner, {"name": "missing-flag"}, "User")

    with patch("ghbot.github.repos.list_repos", side_effect=_stub):
        result = [
            (item.owner, item.name)
            async for item in scan_repositories(["acme"], AsyncMock())
        ]

    assert result == [("acme", "active"), ("acme", "missing-flag")]


@pytest.mark.anyio
async def test_scan_repositories_yields_private_organisation_with_owner_type():
    gh = _make_gh([[{"name": "private", "private": True}]], "Organization")

    result = [item async for item in scan_repositories(["acme"], gh)]

    assert len(result) == 1
    assert result[0].owner == "acme"
    assert result[0].name == "private"
    assert result[0].owner_type == "Organization"
    assert result[0].metadata["private"] is True


@pytest.mark.anyio
async def test_scan_repositories_empty_owners_warns(caplog):
    import logging

    gh = AsyncMock()
    with caplog.at_level(logging.WARNING):
        result = [item async for item in scan_repositories([], gh)]
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
            yield {"name": "partial-first-attempt"}
            raise GitHubApiError("api error")
        yield {"name": "repo1"}

    gh = AsyncMock()
    gh.getitem = AsyncMock(return_value={"type": "User"})
    gh.getiter = _getiter

    result = [r async for r in list_repos("owner1", gh)]

    assert [item.metadata for item in result] == [{"name": "repo1"}]
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
    gh.getitem = AsyncMock(return_value={"type": "User"})
    gh.getiter = _getiter

    with caplog.at_level(logging.ERROR):
        result = [r async for r in list_repos("owner1", gh)]

    assert result == []
    assert call_count == 2
    assert any("owner1" in r.message for r in caplog.records)


@pytest.mark.anyio
async def test_list_repos_retries_owner_lookup_before_listing():
    lookup_count = 0

    async def _getitem(url, url_vars=None):
        nonlocal lookup_count
        lookup_count += 1
        if lookup_count == 1:
            raise GitHubApiError("transient lookup failure")
        return {"type": "Organization"}

    async def _getiter(url, url_vars=None):
        yield {"name": "private", "private": True}

    gh = AsyncMock()
    gh.getitem = _getitem
    gh.getiter = _getiter

    result = [item async for item in list_repos("acme", gh)]

    assert lookup_count == 2
    assert result[0].owner_type == "Organization"


@pytest.mark.anyio
async def test_list_repos_skips_owner_when_lookup_is_not_found(caplog):
    import logging

    gh = AsyncMock()
    gh.getitem = AsyncMock(side_effect=GitHubNotFoundError("not found"))

    with caplog.at_level(logging.WARNING):
        result = [item async for item in list_repos("ghost", gh)]

    assert result == []
    gh.getiter.assert_not_called()
    assert any("ghost" in record.message for record in caplog.records)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error_type", [GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError]
)
async def test_list_repos_propagates_rate_limit_from_owner_lookup(error_type):
    gh = AsyncMock()
    gh.getitem = AsyncMock(side_effect=error_type("rate limited"))

    with pytest.raises(error_type):
        _ = [item async for item in list_repos("acme", gh)]


@pytest.mark.anyio
@pytest.mark.parametrize(
    "error_type", [GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError]
)
async def test_list_repos_propagates_rate_limit_from_listing(error_type):
    async def _getiter(url, url_vars=None):
        raise error_type("rate limited")
        yield

    gh = AsyncMock()
    gh.getitem = AsyncMock(return_value={"type": "Organization"})
    gh.getiter = _getiter

    with pytest.raises(error_type):
        _ = [item async for item in list_repos("acme", gh)]
