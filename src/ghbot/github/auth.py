import asyncio
import os
import platform

from ghbot.errors import AuthError

_tokens: dict[str, str | None] = {"environment": None, "gh": None}
_lock = asyncio.Lock()

_INSTALL_HINTS = {
    "Darwin": "brew install gh  (or: port install gh)",
    "Linux": "sudo apt install gh  (or see your distro's package manager)",
    "Windows": "winget install GitHub.cli  (or: scoop install gh)",
}


async def get_auth_token(*, use_environment: bool = False) -> str:
    """Return an API token from the selected authentication source."""
    source = "environment" if use_environment else "gh"
    async with _lock:
        if _tokens[source] is None:
            if use_environment:
                token = os.environ.get("GITHUB_API_TOKEN", "").strip()
                if not token:
                    raise AuthError("GITHUB_API_TOKEN is not set or is empty")
                _tokens[source] = token
                return token
            try:
                proc = await asyncio.create_subprocess_exec(
                    "gh",
                    "auth",
                    "token",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await proc.communicate()
            except FileNotFoundError as e:
                hint = _INSTALL_HINTS.get(
                    platform.system(), "see https://cli.github.com"
                )
                raise AuthError(
                    f"gh not found. Install it: {hint}\nhttps://cli.github.com"
                ) from e
            if proc.returncode != 0:
                raise AuthError("Not authenticated. Run: gh auth login")
            token = stdout.decode().strip()
            if not token:
                raise AuthError("gh returned an empty token. Run: gh auth login")
            _tokens[source] = token
    token = _tokens[source]
    assert token is not None
    return token
