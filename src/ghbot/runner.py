"""Shared asynchronous repository scan runners."""

from typing import Any

import gidgethub.httpx as gh_httpx
import httpx

from ghbot.executor import TaskPool
from ghbot.github.auth import get_auth_token
from ghbot.github.repos import scan_repositories
from ghbot.log import get_logger
from ghbot.processor import LoggingMonitor, RepoResult

log = get_logger(__name__)


async def run_processor(
    cfg: dict, processor_cls: type, options: dict | None = None
) -> list[RepoResult]:
    """Run a non-reporting processor for each discovered repository."""
    log.info("ghbot starting")
    token = await get_auth_token(use_environment=cfg.get("env", False))
    async with httpx.AsyncClient() as client:
        gh = gh_httpx.GitHubAPI(client, "ghbot", oauth_token=token)
        async with TaskPool(limit=cfg["concurrency"]) as pool:
            async for discovered in scan_repositories(
                cfg["owners"],
                gh,
                explicit_repositories=cfg.get("explicit_repositories"),
            ):
                monitor = LoggingMonitor(discovered.owner, discovered.name)
                processor = processor_cls(
                    discovered.owner,
                    discovered.name,
                    gh,
                    monitor,
                    options=options,
                    owner_type=discovered.owner_type,
                )
                await pool.submit(processor.run)
    log.info("stats: %s", pool.stats)
    return pool.results


async def run_mode(cfg: dict, mode: Any, options: dict | None = None) -> Any:
    """Construct mode processors and collect each successful result in the pool task."""
    options = dict(options or {})
    collection = mode.new_collection(options)
    token = await get_auth_token(use_environment=cfg.get("env", False))
    async with httpx.AsyncClient() as client:
        gh = gh_httpx.GitHubAPI(client, "ghbot", oauth_token=token)
        async with TaskPool(limit=cfg["concurrency"]) as pool:
            async for discovered in scan_repositories(
                cfg["owners"],
                gh,
                explicit_repositories=cfg.get("explicit_repositories"),
            ):
                processor = mode.new_processor(
                    discovered.owner,
                    discovered.name,
                    gh,
                    LoggingMonitor(discovered.owner, discovered.name),
                    options,
                    owner_type=discovered.owner_type,
                )

                async def collect(processor=processor):
                    collection.add(await processor.run())

                await pool.submit(collect)
    log.info("stats: %s", pool.stats)
    return collection
