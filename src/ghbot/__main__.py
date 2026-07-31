import asyncio
import sys
from importlib.metadata import version
from pathlib import Path

import click
import gidgethub.httpx as gh_httpx
import httpx

from ghbot.config import DEFAULTS, load_config
from ghbot.errors import FatalError
from ghbot.executor import TaskPool
from ghbot.github.auth import get_auth_token
from ghbot.github.repos import scan_repositories
from ghbot.log import configure, get_logger
from ghbot.processor import (
    InfoRepoProcessor,
    IssuesRepoProcessor,
    LoggingMonitor,
    RepoResult,
    SecurityRepoProcessor,
)
from ghbot.report import print_issues_report, print_security_report

log = get_logger(__name__)


def _split_owners(
    ctx: click.Context, param: click.Parameter, value: tuple[str, ...]
) -> tuple[str, ...]:
    return tuple(o for v in value for o in v.split(",") if o)


async def _main(
    cfg: dict, processor_cls: type, options: dict | None = None
) -> list[RepoResult]:
    log.info("ghbot starting")
    token = await get_auth_token()
    async with httpx.AsyncClient() as client:
        gh = gh_httpx.GitHubAPI(client, "ghbot", oauth_token=token)
        async with TaskPool(limit=cfg["concurrency"]) as pool:
            async for owner, repo in scan_repositories(cfg["owners"], gh):
                monitor = LoggingMonitor(owner, repo["name"])
                processor = processor_cls(
                    owner, repo["name"], gh, monitor, options=options
                )
                await pool.submit(processor.run)
    log.info("stats: %s", pool.stats)
    return pool.results


@click.group()
@click.version_option(version("ghbot"))
@click.option("--config", default=None, help="Config file path")
@click.option("--verbose", is_flag=True, default=False, help="Console log level: debug")
@click.option("--quiet", is_flag=True, default=False, help="Console log level: warn")
@click.option("--log-file", default=None, help="Write logs to file")
@click.option(
    "--log-level",
    default="info",
    show_default=True,
    type=click.Choice(
        ["trace", "debug", "info", "warn", "error"], case_sensitive=False
    ),
    help="Log level for --log-file destination",
)
@click.option(
    "--log-json",
    is_flag=True,
    default=False,
    help="Structured JSON logging for --log-file",
)
@click.option(
    "--requests",
    is_flag=True,
    default=False,
    help="Enable HTTP request/response detail logging (ghbot.requests logger)",
)
@click.option(
    "--owner",
    multiple=True,
    callback=_split_owners,
    help="Owner(s) to target: --owner owner1,owner2 or repeated --owner flags",
)
@click.option(
    "--concurrency",
    default=None,
    type=int,
    help="Max concurrent repository tasks (default: 16)",
)
@click.pass_context
def cli(
    ctx: click.Context,
    config: str | None,
    verbose: bool,
    quiet: bool,
    log_file: str | None,
    log_level: str,
    log_json: bool,
    requests: bool,
    owner: tuple[str, ...],
    concurrency: int | None,
) -> None:
    ctx.ensure_object(dict)
    cfg = {**DEFAULTS}
    cfg.update(load_config(config))
    if owner:
        cfg["owners"] = list(owner)
    elif isinstance(cfg.get("owners"), str):
        cfg["owners"] = [o for o in cfg["owners"].split(",") if o]
    if log_file:
        cfg["log-file"] = log_file
    if log_json:
        cfg["log-json"] = log_json
    if concurrency is not None:
        cfg["concurrency"] = concurrency
    console_level = "debug" if verbose else "warn" if quiet else "info"
    configure(
        console_level=console_level,
        log_file=cfg.get("log-file"),
        log_level=cfg.get("log-level", log_level),
        json_format=cfg.get("log-json", False),
        requests=requests,
    )
    ctx.obj["cfg"] = cfg


@cli.command()
@click.pass_context
def info(ctx: click.Context) -> None:
    """Gather repository summary statistics."""
    cfg = ctx.obj["cfg"]
    try:
        asyncio.run(_main(cfg, InfoRepoProcessor))
    except FatalError as e:
        log.error(e.message)
        sys.exit(e.exit_code)


def _output_format(*, plain: bool, table: bool, json_format: bool) -> str:
    selected = [
        name
        for flag, name in (
            (plain, "plain"),
            (table, "table"),
            (json_format, "json"),
        )
        if flag
    ]
    if len(selected) > 1:
        raise click.UsageError("choose only one of --plain, --table, or --json")
    return selected[0] if selected else "plain"


@cli.command()
@click.option("--plain", "format_plain", is_flag=True, default=False)
@click.option("--table", "format_table", is_flag=True, default=False)
@click.option("--json", "format_json", is_flag=True, default=False)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the final report to a file",
)
@click.pass_context
def security(
    ctx: click.Context,
    format_plain: bool,
    format_table: bool,
    format_json: bool,
    output: Path | None,
) -> None:
    """Scan repositories for open security alerts."""
    cfg = ctx.obj["cfg"]
    output_format = _output_format(
        plain=format_plain, table=format_table, json_format=format_json
    )
    options = {"format": output_format}
    try:
        results = asyncio.run(_main(cfg, SecurityRepoProcessor, options=options))
    except FatalError as e:
        log.error(e.message)
        sys.exit(e.exit_code)
    print_security_report(results, format=output_format, output=output)


@cli.command()
@click.option("--plain", "format_plain", is_flag=True, default=False)
@click.option("--table", "format_table", is_flag=True, default=False)
@click.option("--json", "format_json", is_flag=True, default=False)
@click.option(
    "--labels",
    "show_labels",
    is_flag=True,
    default=False,
    help="Include issue labels in the report",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the final report to a file",
)
@click.pass_context
def issues(
    ctx: click.Context,
    format_plain: bool,
    format_table: bool,
    format_json: bool,
    show_labels: bool,
    output: Path | None,
) -> None:
    """Scan repositories for open issues and pull requests."""
    cfg = ctx.obj["cfg"]
    output_format = _output_format(
        plain=format_plain, table=format_table, json_format=format_json
    )
    try:
        results = asyncio.run(_main(cfg, IssuesRepoProcessor))
    except FatalError as e:
        log.error(e.message)
        sys.exit(e.exit_code)
    print_issues_report(
        results, format=output_format, labels=show_labels, output=output
    )


if __name__ == "__main__":
    cli()
