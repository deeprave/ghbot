from unittest.mock import AsyncMock, patch
from ghbot.errors import (
    AuthError,
    FatalError,
    GitHubApiError,
    GitHubNotFoundError,
    UnexpectedError,
)


def test_fatal_error_attributes():
    e = FatalError("something went wrong", exit_code=2)
    assert e.message == "something went wrong"
    assert e.exit_code == 2
    assert isinstance(e, Exception)


def test_auth_error_is_fatal_error():
    e = AuthError("bad auth")
    assert isinstance(e, FatalError)
    assert e.exit_code == 1
    assert e.message == "bad auth"


def test_main_catches_fatal_error_and_exits():
    from ghbot.__main__ import cli
    from click.testing import CliRunner

    with patch(
        "ghbot.__main__._main",
        new=AsyncMock(side_effect=FatalError("boom", exit_code=3)),
    ):
        result = CliRunner().invoke(cli, ["info"])

    assert result.exit_code == 3


def test_github_api_error_is_fatal_error():
    e = GitHubApiError("api failure")
    assert isinstance(e, FatalError)
    assert e.exit_code == 1
    assert e.message == "api failure"


def test_github_not_found_error_is_github_api_error():
    e = GitHubNotFoundError("not found")
    assert isinstance(e, GitHubApiError)
    assert isinstance(e, FatalError)
    assert e.exit_code == 1


def test_unexpected_error_is_fatal_error():
    e = UnexpectedError("something unexpected", exit_code=2)
    assert isinstance(e, FatalError)
    assert e.message == "something unexpected"
    assert e.exit_code == 2
