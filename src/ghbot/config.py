import tomllib
from pathlib import Path
from typing import Any

CONFIG_FILENAME = "ghbot.toml"

DEFAULTS: dict[str, Any] = {
    "owners": [],
    "log-file": None,
    "log-json": False,
    "log-level": "info",
    "concurrency": 16,
}

_SEARCH_PATHS = [
    Path.cwd() / CONFIG_FILENAME,
    Path.home() / ".config" / "ghbot" / "config.toml",
]


def load_config(path: str | None = None) -> dict[str, Any]:
    candidates = [Path(path)] if path else _SEARCH_PATHS
    for candidate in candidates:
        if candidate.exists():
            with open(candidate, "rb") as f:
                return {**DEFAULTS, **tomllib.load(f)}
    return dict(DEFAULTS)
