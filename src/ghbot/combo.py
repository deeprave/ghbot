"""Combined reporting command over discovered reportable modes."""

import asyncio
import sys
from pathlib import Path

import click

from ghbot.errors import FatalError
from ghbot.log import get_logger
from ghbot.modes import combinable_modes
from ghbot.report_style import output_format, write_report
from ghbot.runner import run_combo

log = get_logger(__name__)


@click.command()
@click.option("--plain", "format_plain", is_flag=True, default=False)
@click.option("--table", "format_table", is_flag=True, default=False)
@click.option("--json", "format_json", is_flag=True, default=False)
@click.option(
    "--labels",
    "show_labels",
    is_flag=True,
    default=False,
    help="Include issue labels in the issues report section",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the final report to a file",
)
@click.pass_context
def combo(
    ctx: click.Context,
    format_plain: bool,
    format_table: bool,
    format_json: bool,
    show_labels: bool,
    output: Path | None,
) -> None:
    """Run every keyed reportable mode in one repository scan."""
    selected_format = output_format(
        plain=format_plain, table=format_table, json_format=format_json
    )
    modes = combinable_modes()
    options_by_mode = {
        mode.name: {
            "format": selected_format,
            **({"labels": show_labels} if mode.name == "issues" else {}),
        }
        for mode in modes
    }
    try:
        report = asyncio.run(run_combo(ctx.obj["cfg"], modes, options_by_mode))
    except FatalError as error:
        log.error(error.message)
        sys.exit(error.exit_code)
    write_report(report.render(selected_format), output)
    if getattr(report, "abort_reason", None) == "rate_limited":
        log.error("rate limited; wrote incomplete report")
        sys.exit(4)
