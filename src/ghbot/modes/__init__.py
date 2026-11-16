"""Self-contained built-in scanner modes and discovery interfaces."""

from ghbot.modes._discovery import (
    ModeDefinition,
    ModeDiscoveryError,
    combinable_modes,
    discover_modes,
)

__all__ = [
    "ModeDefinition",
    "ModeDiscoveryError",
    "combinable_modes",
    "discover_modes",
]
