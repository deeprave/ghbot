"""Self-contained reportable mode units and their built-in CLI commands."""

from ghbot.modes.drift import drift
from ghbot.modes.issues import issues
from ghbot.modes.security import security

BUILTIN_COMMANDS = (security, issues, drift)
