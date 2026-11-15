"""Self-contained reportable mode units and their built-in CLI commands."""

from ghbot.modes import drift, issues, security

BUILTIN_COMMANDS = (security.security, issues.issues, drift.drift)
