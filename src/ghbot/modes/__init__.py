"""Self-contained built-in scanner modes and discovery interfaces."""

from ghbot.modes._discovery import (
    ModeDefinition,
    ModeDiscoveryError,
    ReportableModeDefinition,
    combinable_modes,
    discover_modes,
)

__all__ = [
    "ModeDefinition",
    "ModeDiscoveryError",
    "ReportableModeDefinition",
    "combinable_modes",
    "discover_modes",
]
