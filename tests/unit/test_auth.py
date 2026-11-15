import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghbot.errors import AuthError


def _make_proc(returncode: int, stdout: bytes) -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, b""))
    return proc


@pytest.fixture(autouse=True)
def reset_auth_state():
    import ghbot.github.auth as auth_mod

    auth_mod._tokens = {"environment": None, "gh": None}
    auth_mod._lock = asyncio.Lock()
    yield
    auth_mod._tokens = {"environment": None, "gh": None}
    auth_mod._lock = asyncio.Lock()


@pytest.mark.anyio
async def test_gh_not_found_raises_auth_error():
    with (
        patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert "gh" in exc_info.value.message.lower()
    assert "https://cli.github.com" in exc_info.value.message


@pytest.mark.anyio
async def test_gh_not_found_chains_original_exception():
    with (
        patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


@pytest.mark.anyio
@pytest.mark.parametrize("returncode, stdout", [(1, b""), (0, b"\n")])
async def test_invalid_gh_token_raises_auth_error(returncode, stdout):
    with (
        patch(
            "asyncio.create_subprocess_exec",
            return_value=_make_proc(returncode, stdout),
        ),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert "gh auth login" in exc_info.value.message


@pytest.mark.anyio
async def test_environment_token_is_trimmed_without_invoking_gh(monkeypatch):
    monkeypatch.setenv("GITHUB_API_TOKEN", "  environment-token  \n")
    with patch("asyncio.create_subprocess_exec") as create_subprocess:
        from ghbot.github.auth import get_auth_token

        token = await get_auth_token(use_environment=True)

    assert token == "environment-token"
    create_subprocess.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize("value", [None, "", " \t\n"])
async def test_environment_token_missing_or_empty_never_invokes_gh(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("GITHUB_API_TOKEN", raising=False)
    else:
        monkeypatch.setenv("GITHUB_API_TOKEN", value)

    with (
        patch("asyncio.create_subprocess_exec") as create_subprocess,
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token(use_environment=True)

    assert "GITHUB_API_TOKEN" in exc_info.value.message
    create_subprocess.assert_not_called()


@pytest.mark.anyio
async def test_environment_token_mode_does_not_use_github_token(monkeypatch):
    monkeypatch.delenv("GITHUB_API_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "workflow-token")

    with (
        patch("asyncio.create_subprocess_exec") as create_subprocess,
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token(use_environment=True)

    assert "GITHUB_API_TOKEN" in exc_info.value.message
    create_subprocess.assert_not_called()


@pytest.mark.anyio
async def test_environment_and_gh_tokens_have_isolated_caches(monkeypatch):
    monkeypatch.setenv("GITHUB_API_TOKEN", "environment-token")
    with patch(
        "asyncio.create_subprocess_exec", return_value=_make_proc(0, b"gh-token\n")
    ) as create_subprocess:
        from ghbot.github.auth import get_auth_token

        assert await get_auth_token(use_environment=True) == "environment-token"
        assert await get_auth_token() == "gh-token"
        assert await get_auth_token(use_environment=True) == "environment-token"

    create_subprocess.assert_called_once()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("system", "hint"),
    [("Darwin", "brew install gh"), ("Linux", "apt"), ("Windows", "winget")],
)
async def test_missing_gh_includes_platform_install_hint(system, hint):
    with (
        patch("platform.system", return_value=system),
        patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert hint in exc_info.value.message
