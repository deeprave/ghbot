"""Shared asynchronous repository scan runners."""

from collections.abc import AsyncGenerator
from typing import Any

import gidgethub.httpx as gh_httpx
import httpx

from ghbot.errors import (
    FatalError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.executor import RateLimitAbort, TaskPool
from ghbot.github.auth import get_auth_token
from ghbot.github.repos import scan_repositories
from ghbot.log import get_logger
from ghbot.modes import ReportableModeDefinition
from ghbot.processor import LoggingMonitor, RepoResult
from ghbot.rate_limit import RateLimitGate
from ghbot.report_style import CombinedCollectionReport, ReportOutcome, ReportSection

log = get_logger(__name__)


async def _scan_with_rate_retries(
    cfg: dict, gh: Any, pool: TaskPool
) -> AsyncGenerator[Any]:
    """Resume discovery after recoverable limits without yielding a repository twice."""
    seen: set[str] = set()
    while not isinstance(getattr(pool, "rate_limit_abort", None), RateLimitAbort):
        try:
            async for discovered in scan_repositories(
                cfg["owners"],
                gh,
                explicit_repositories=cfg.get("explicit_repositories"),
            ):
                key = f"{discovered.owner}/{discovered.name}"
                if key not in seen:
                    seen.add(key)
                    yield discovered
            return
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError) as error:
            gate = gh.rate_limit_gate
            if not await gate.record(error):
                pool.abort_rate_limit(error)
                return
            await gate.wait()


async def run_processor(
    cfg: dict, processor_cls: type, options: dict | None = None
) -> list[RepoResult]:
    """Run a non-reporting processor for each discovered repository."""
    log.info("ghbot starting")
    token = await get_auth_token(use_environment=cfg.get("env", False))
    async with httpx.AsyncClient() as client:
        gh: Any = gh_httpx.GitHubAPI(client, "ghbot", oauth_token=token)
        gh.rate_limit_gate = RateLimitGate(
            max_wait=cfg.get("max-rate-wait", 120),
            max_hits=cfg.get("max-rate-limit-hits", 3),
        )
        async with TaskPool(
            limit=cfg["concurrency"], rate_limit_gate=gh.rate_limit_gate
        ) as pool:
            async for discovered in _scan_with_rate_retries(cfg, gh, pool):
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


async def run_mode(cfg: dict, mode: Any, options: dict | None = None) -> ReportOutcome:
    """Construct mode processors and collect each successful result in the pool task."""
    options = dict(options or {})
    collection = mode.new_collection(options)
    requested: list[str] = []
    token = await get_auth_token(use_environment=cfg.get("env", False))
    async with httpx.AsyncClient() as client:
        gh: Any = gh_httpx.GitHubAPI(client, "ghbot", oauth_token=token)
        gh.rate_limit_gate = RateLimitGate(
            max_wait=cfg.get("max-rate-wait", 120),
            max_hits=cfg.get("max-rate-limit-hits", 3),
        )
        async with TaskPool(
            limit=cfg["concurrency"], rate_limit_gate=gh.rate_limit_gate
        ) as pool:
            async for discovered in _scan_with_rate_retries(cfg, gh, pool):
                repository = f"{discovered.owner}/{discovered.name}"
                requested.append(repository)
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

                await pool.submit(collect, task_id=repository)
    log.info("stats: %s", pool.stats)
    abort_reason = "rate_limited" if getattr(pool, "rate_limit_abort", None) else None
    completed_ids = getattr(pool, "completed_ids", set(requested))
    not_processed = tuple(
        repository for repository in requested if repository not in completed_ids
    )
    return ReportOutcome(collection, abort_reason, not_processed)


async def run_combo(
    cfg: dict,
    modes: tuple[ReportableModeDefinition, ...],
    options_by_mode: dict[str, dict] | None = None,
) -> ReportOutcome:
    """Scan each repository once and collect every selected reportable mode."""
    options_by_mode = {
        name: dict(options) for name, options in (options_by_mode or {}).items()
    }
    collections = {
        mode.name: mode.new_collection(options_by_mode.get(mode.name, {}))
        for mode in modes
    }
    sections = tuple(ReportSection(mode.name, collections[mode.name]) for mode in modes)
    requested: list[str] = []

    token = await get_auth_token(use_environment=cfg.get("env", False))
    async with httpx.AsyncClient() as client:
        gh: Any = gh_httpx.GitHubAPI(client, "ghbot", oauth_token=token)
        gh.rate_limit_gate = RateLimitGate(
            max_wait=cfg.get("max-rate-wait", 120),
            max_hits=cfg.get("max-rate-limit-hits", 3),
        )
        async with TaskPool(
            limit=cfg["concurrency"], rate_limit_gate=gh.rate_limit_gate
        ) as pool:
            async for discovered in _scan_with_rate_retries(cfg, gh, pool):
                repository = f"{discovered.owner}/{discovered.name}"
                requested.append(repository)
                results: dict[str, RepoResult] = {}

                async def collect(discovered=discovered, results=results):
                    monitor = LoggingMonitor(discovered.owner, discovered.name)
                    try:
                        for mode in modes:
                            if mode.name in results:
                                continue
                            processor = mode.new_processor(
                                discovered.owner,
                                discovered.name,
                                gh,
                                monitor,
                                options_by_mode.get(mode.name, {}),
                                owner_type=discovered.owner_type,
                            )
                            results[mode.name] = await processor.run()
                    except FatalError:
                        raise
                    except Exception:
                        for mode in modes:
                            if mode.name in results:
                                collections[mode.name].add(results[mode.name])
                        raise
                    for mode in modes:
                        collections[mode.name].add(results[mode.name])

                await pool.submit(collect, task_id=repository)
    log.info("stats: %s", pool.stats)
    abort_reason = "rate_limited" if getattr(pool, "rate_limit_abort", None) else None
    completed_ids = getattr(pool, "completed_ids", set(requested))
    not_processed = tuple(
        repository for repository in requested if repository not in completed_ids
    )
    outcome_sections = (
        sections
        if abort_reason is None
        else tuple(
            ReportSection(
                section.name,
                ReportOutcome(section.collection, abort_reason, not_processed),
            )
            for section in sections
        )
    )
    return ReportOutcome(
        CombinedCollectionReport(outcome_sections), abort_reason, not_processed
    )
