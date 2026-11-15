import asyncio
import sys
from importlib.metadata import version

import click

from ghbot.config import DEFAULTS, load_config
from ghbot.errors import FatalError
from ghbot.log import configure, get_logger
from ghbot.modes import BUILTIN_COMMANDS
from ghbot.processor import InfoRepoProcessor
from ghbot.runner import run_processor

log = get_logger(__name__)


def _split_owners(
    ctx: click.Context, param: click.Parameter, value: tuple[str, ...]
) -> tuple[str, ...]:
    return tuple(o for v in value for o in v.split(",") if o)


@click.group()
@click.version_option(version("ghbot"))
@click.option("--config", default=None, help="Config file path")
@click.option("--verbose", is_flag=True, default=False, help="Console log level: debug")
@click.option("--quiet", is_flag=True, default=False, help="Console log level: warn")
@click.option("--log-file", default=None, help="Write logs to file")
@click.option(
    "-e",
    "--env/--no-env",
    "use_environment_token",
    default=None,
    help="Read API token from GITHUB_API_TOKEN (or use gh with --no-env)",
)
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
    use_environment_token: bool | None,
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
    if use_environment_token is not None:
        cfg["env"] = use_environment_token
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
        asyncio.run(run_processor(cfg, InfoRepoProcessor))
    except FatalError as e:
        log.error(e.message)
        sys.exit(e.exit_code)


for command in BUILTIN_COMMANDS:
    cli.add_command(command)


if __name__ == "__main__":
    cli()
