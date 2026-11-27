"""Repository summary mode."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from typing import Any

import click

from ghbot.errors import FatalError
from ghbot.log import get_logger
from ghbot.processor import InfoRepoProcessor
from ghbot.runner import run_processor

log = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class InfoMode:
    """Non-reporting repository summary mode."""

    name: str = "info"

    @property
    def command(self) -> click.Command:
        return info

    def new_processor(
        self,
        owner: str,
        repo: str,
        gh: Any,
        monitor: Any,
        options: dict,
        *,
        owner_type: str | None = None,
    ) -> InfoRepoProcessor:
        return InfoRepoProcessor(
            owner, repo, gh, monitor, options=options, owner_type=owner_type
        )


MODE = InfoMode()


@click.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Scan for repository summary statistics."""
    try:
        asyncio.run(run_processor(ctx.obj["cfg"], InfoRepoProcessor))
    except FatalError as error:
        log.error(error.message)
        sys.exit(error.exit_code)
