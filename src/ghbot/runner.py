"""Shared asynchronous repository scan runners."""

from typing import Any

import gidgethub.httpx as gh_httpx
import httpx

from ghbot.executor import TaskPool
from ghbot.github.auth import get_auth_token
from ghbot.github.repos import scan_repositories
from ghbot.log import get_logger
from ghbot.modes import ReportableModeDefinition
from ghbot.processor import LoggingMonitor, RepoResult
from ghbot.report_style import CombinedCollectionReport, ReportSection

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


async def run_combo(
    cfg: dict,
    modes: tuple[ReportableModeDefinition, ...],
    options_by_mode: dict[str, dict] | None = None,
) -> CombinedCollectionReport:
    """Scan each repository once and collect every selected reportable mode."""
    options_by_mode = {
        name: dict(options) for name, options in (options_by_mode or {}).items()
    }
    collections = {
        mode.name: mode.new_collection(options_by_mode.get(mode.name, {}))
        for mode in modes
    }
    sections = tuple(ReportSection(mode.name, collections[mode.name]) for mode in modes)

    token = await get_auth_token(use_environment=cfg.get("env", False))
    async with httpx.AsyncClient() as client:
        gh = gh_httpx.GitHubAPI(client, "ghbot", oauth_token=token)
        async with TaskPool(limit=cfg["concurrency"]) as pool:
            async for discovered in scan_repositories(
                cfg["owners"],
                gh,
                explicit_repositories=cfg.get("explicit_repositories"),
            ):

                async def collect(discovered=discovered):
                    monitor = LoggingMonitor(discovered.owner, discovered.name)
                    results = {}
                    for mode in modes:
                        processor = mode.new_processor(
                            discovered.owner,
                            discovered.name,
                            gh,
                            monitor,
                            options_by_mode.get(mode.name, {}),
                            owner_type=discovered.owner_type,
                        )
                        results[mode.name] = await processor.run()
                    for mode in modes:
                        collections[mode.name].add(results[mode.name])

                await pool.submit(collect)
    log.info("stats: %s", pool.stats)
    return CombinedCollectionReport(sections)
