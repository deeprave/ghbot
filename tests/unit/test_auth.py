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

    auth_mod._token = None
    auth_mod._lock = asyncio.Lock()
    yield
    auth_mod._token = None
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
async def test_gh_non_zero_raises_auth_error():
    with (
        patch("asyncio.create_subprocess_exec", return_value=_make_proc(1, b"")),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert "gh auth login" in exc_info.value.message


@pytest.mark.anyio
async def test_gh_empty_token_raises_auth_error():
    with (
        patch("asyncio.create_subprocess_exec", return_value=_make_proc(0, b"\n")),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert "gh auth login" in exc_info.value.message


@pytest.mark.anyio
async def test_platform_hint_darwin():
    with (
        patch("platform.system", return_value="Darwin"),
        patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert "brew install gh" in exc_info.value.message


@pytest.mark.anyio
async def test_platform_hint_linux():
    with (
        patch("platform.system", return_value="Linux"),
        patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert "apt" in exc_info.value.message


@pytest.mark.anyio
async def test_platform_hint_windows():
    with (
        patch("platform.system", return_value="Windows"),
        patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError),
        pytest.raises(AuthError) as exc_info,
    ):
        from ghbot.github.auth import get_auth_token

        await get_auth_token()
    assert "winget" in exc_info.value.message
