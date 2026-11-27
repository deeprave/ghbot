from importlib.metadata import version
from pathlib import Path

import click

from ghbot.combo import combo
from ghbot.config import DEFAULTS, load_config
from ghbot.log import configure, get_logger
from ghbot.modes import discover_modes
from ghbot.schema import schema

log = get_logger(__name__)

_SCHEMA_SENTINEL = "__schema__"


class SchemaDispatchGroup(click.Group):
    """Route a leading schema invocation without registering a schema command."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        super().format_help(ctx, formatter)
        formatter.write_paragraph()
        formatter.write(
            "Schema retrieval:\n"
            "  ghbot --schema REPORT\n"
            "  ghbot --schema --id TEXT\n"
            "  ghbot --schema --list"
        )

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        if args and args[0] == "--schema":
            ctx.meta["schema_args"] = args[1:]
            return super().parse_args(ctx, [_SCHEMA_SENTINEL])
        return super().parse_args(ctx, args)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        if cmd_name == _SCHEMA_SENTINEL and "schema_args" in ctx.meta:
            return schema
        return super().get_command(ctx, cmd_name)

    def invoke(self, ctx: click.Context) -> object:
        if (schema_args := ctx.meta.get("schema_args")) is not None:
            return schema.main(
                args=schema_args,
                prog_name=f"{ctx.info_name} --schema",
                standalone_mode=False,
            )
        return super().invoke(ctx)


def _split_owners(
    ctx: click.Context, _param: click.Parameter, value: tuple[str, ...]
) -> tuple[str, ...]:
    return tuple(
        owner
        for item in value
        for owner in (o.strip() for o in item.split(","))
        if owner
    )


def _deduplicate_owners(owners: list[str]) -> list[str]:
    unique: dict[str, str] = {}
    for owner in owners:
        key = owner.casefold()
        if key in unique:
            log.warning("Duplicate owner skipped: %s", owner)
            continue
        unique[key] = owner
    return list(unique.values())


def _repository_entries(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        entry.strip() for value in values for entry in value.split(",") if entry.strip()
    )


def _file_repository_entries(path: Path | None) -> tuple[str, ...]:
    if path is None:
        return ()

    entries: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as e:
        raise click.UsageError(f"unable to read repository file: {path}") from e
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        entries.extend(_repository_entries((line,)))
    return tuple(entries)


def _resolve_explicit_repositories(
    owners: list[str], repositories: tuple[str, ...], repository_file: Path | None
) -> tuple[tuple[str, str], ...] | None:
    if not repositories and repository_file is None:
        return None

    candidates: dict[str, tuple[str, str]] = {}
    for entry in (
        *_repository_entries(repositories),
        *_file_repository_entries(repository_file),
    ):
        parts = [part.strip() for part in entry.split("/")]
        if len(parts) == 1:
            if not owners:
                raise click.UsageError(f"repository requires an owner: {entry}")
            expanded = ((owner, parts[0]) for owner in owners)
        elif len(parts) == 2 and all(parts):
            expanded = ((parts[0], parts[1]),)
        else:
            raise click.UsageError(f"invalid repository: {entry}")

        for owner, repo in expanded:
            key = f"{owner}/{repo}".casefold()
            if key in candidates:
                log.warning(
                    "Duplicate repository selection skipped: %s/%s", owner, repo
                )
                continue
            candidates[key] = (owner, repo)
    return tuple(candidates.values())


@click.group(cls=SchemaDispatchGroup)
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
    "--repo",
    "repositories",
    multiple=True,
    help="Repository entries: owner/repo or bare repo",
)
@click.option(
    "--repos",
    "repository_files",
    multiple=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="File containing repository entries",
)
@click.option(
    "--concurrency",
    default=None,
    type=int,
    help="Max concurrent repository tasks (default: 16)",
)
@click.option(
    "--max-rate-wait",
    type=click.IntRange(min=0),
    default=None,
    help="Longest rate-limit wait to honour in seconds",
)
@click.option(
    "--max-rate-limit-hits",
    type=click.IntRange(min=0),
    default=None,
    help="Maximum rate-limit episodes to recover from",
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
    repositories: tuple[str, ...],
    repository_files: tuple[Path, ...],
    concurrency: int | None,
    max_rate_wait: int | None,
    max_rate_limit_hits: int | None,
) -> None:
    ctx.ensure_object(dict)
    if len(repository_files) > 1:
        raise click.UsageError("--repos may not be used multiple times")

    cfg = {**DEFAULTS}
    cfg.update(load_config(config))
    if owner:
        cfg["owners"] = list(owner)
    elif isinstance(cfg.get("owners"), str):
        cfg["owners"] = [
            owner for item in cfg["owners"].split(",") if (owner := item.strip())
        ]
    cfg["owners"] = _deduplicate_owners(cfg["owners"])
    if log_file:
        cfg["log-file"] = log_file
    if use_environment_token is not None:
        cfg["env"] = use_environment_token
    if log_json:
        cfg["log-json"] = log_json
    if concurrency is not None:
        cfg["concurrency"] = concurrency
    if max_rate_wait is not None:
        cfg["max-rate-wait"] = max_rate_wait
    if max_rate_limit_hits is not None:
        cfg["max-rate-limit-hits"] = max_rate_limit_hits
    for name in ("max-rate-wait", "max-rate-limit-hits"):
        value = cfg[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise click.UsageError(f"{name} must be a non-negative integer")
    cfg["explicit_repositories"] = _resolve_explicit_repositories(
        cfg["owners"], repositories, repository_files[0] if repository_files else None
    )
    console_level = "debug" if verbose else "warn" if quiet else "info"
    configure(
        console_level=console_level,
        log_file=cfg.get("log-file"),
        log_level=cfg.get("log-level", log_level),
        json_format=cfg.get("log-json", False),
        requests=requests,
    )
    ctx.obj["cfg"] = cfg


for mode in discover_modes():
    cli.add_command(mode.command)
cli.add_command(combo)


if __name__ == "__main__":
    cli()
