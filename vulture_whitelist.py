"""Vulture whitelist for intentional framework and runtime protocol surfaces."""

from ghbot.log import LoggerWithTrace
from ghbot.processor import RepoProcessor

LoggerWithTrace.trace  # noqa: B018 - dynamic TRACE extension
RepoProcessor  # noqa: B018 - runtime-checkable processor protocol
