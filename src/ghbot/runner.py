"""Shared asynchronous repository scan runners."""

from collections.abc import AsyncGenerator
from typing import Any

import gidgethub.httpx as gh_httpx
import httpx

from ghbot.errors import (
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
    RateLimitAbortError,
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
    skipped_explicit_ids: set[str] = set()
    pool.skipped_explicit_ids = skipped_explicit_ids
    gh._ghbot_skipped_explicit_ids = skipped_explicit_ids
    while not isinstance(getattr(pool, "rate_limit_abort", None), RateLimitAbort):
        try:
            async for discovered in scan_repositories(
                cfg["owners"],
                gh,
                explicit_repositories=cfg.get("explicit_repositories"),
            ):
                if isinstance(getattr(pool, "rate_limit_abort", None), RateLimitAbort):
                    return
                key = f"{discovered.owner}/{discovered.name}"
                if key not in seen:
                    seen.add(key)
                    yield discovered
            return
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError) as error:
            if isinstance(getattr(pool, "rate_limit_abort", None), RateLimitAbort):
                return
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
    if isinstance(abort := getattr(pool, "rate_limit_abort", None), RateLimitAbort):
        raise RateLimitAbortError(abort.reason)
    return pool.results


def _requested_with_explicit_selections(
    cfg: dict, requested: list[str], pool: TaskPool
) -> list[str]:
    """Keep user-selected repositories visible if discovery is interrupted."""
    if not isinstance(getattr(pool, "rate_limit_abort", None), RateLimitAbort):
        return requested
    result = list(requested)
    identities = {identity.casefold() for identity in result}
    skipped = getattr(pool, "skipped_explicit_ids", set())
    for owner, repository in cfg.get("explicit_repositories") or ():
        identity = f"{owner}/{repository}"
        if identity.casefold() not in identities and identity.casefold() not in skipped:
            result.append(identity)
            identities.add(identity.casefold())
    return result


def _report_outcome(
    collection: Any, cfg: dict, requested: list[str], pool: TaskPool
) -> ReportOutcome:
    requested = _requested_with_explicit_selections(cfg, requested, pool)
    abort_reason = (
        "rate_limited"
        if isinstance(getattr(pool, "rate_limit_abort", None), RateLimitAbort)
        else None
    )
    failed_ids = getattr(pool, "failed_ids", set())
    if abort_reason is None and failed_ids:
        abort_reason = "task_failed"
    settled = getattr(pool, "completed_ids", set(requested)) | getattr(
        pool, "terminal_ids", set()
    )
    not_processed = tuple(
        (repository, "task_failed" if repository in failed_ids else abort_reason)
        for repository in requested
        if repository not in settled and abort_reason is not None
    )
    return ReportOutcome(collection, abort_reason, not_processed)


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
    return _report_outcome(collection, cfg, requested, pool)


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
    completed_by_mode: dict[str, set[str]] = {mode.name: set() for mode in modes}

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

                async def collect(
                    discovered=discovered, results=results, repository=repository
                ):
                    monitor = LoggingMonitor(discovered.owner, discovered.name)
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
                        collections[mode.name].add(results[mode.name])
                        completed_by_mode[mode.name].add(repository)

                await pool.submit(collect, task_id=repository)
    log.info("stats: %s", pool.stats)
    requested = _requested_with_explicit_selections(cfg, requested, pool)
    abort_reason = (
        "rate_limited"
        if isinstance(getattr(pool, "rate_limit_abort", None), RateLimitAbort)
        else None
    )
    failed_ids = getattr(pool, "failed_ids", set())
    terminal_ids = getattr(pool, "terminal_ids", set())
    if abort_reason is None and failed_ids:
        abort_reason = "task_failed"
    outcome_sections = []
    for section in sections:
        not_processed = tuple(
            (
                repository,
                "task_failed" if repository in failed_ids else "rate_limited",
            )
            for repository in requested
            if repository not in completed_by_mode[section.name]
            and repository not in terminal_ids
        )
        outcome_sections.append(
            ReportSection(
                section.name,
                ReportOutcome(
                    section.collection,
                    abort_reason if not_processed else None,
                    not_processed,
                ),
            )
        )
    return _report_outcome(
        CombinedCollectionReport(tuple(outcome_sections)), cfg, requested, pool
    )
