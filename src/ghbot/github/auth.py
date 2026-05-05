import asyncio
import platform
from ghbot.errors import AuthError

_token: str | None = None
_lock = asyncio.Lock()

_INSTALL_HINTS = {
    "Darwin": "brew install gh  (or: port install gh)",
    "Linux": "sudo apt install gh  (or see your distro's package manager)",
    "Windows": "winget install GitHub.cli  (or: scoop install gh)",
}


async def get_auth_token() -> str:
    global _token
    async with _lock:
        if _token is None:
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
            _token = stdout.decode().strip()
            if not _token:
                raise AuthError("gh returned an empty token. Run: gh auth login")
    return _token
