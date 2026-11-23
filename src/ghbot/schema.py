"""CLI access to packaged report schemas."""

import json

import click

from ghbot.schemas import current_schema, schema_for_id


@click.command()
@click.argument("report", required=False)
@click.option("--id", "schema_id", help="Canonical schema identifier")
def schema(report: str | None, schema_id: str | None) -> None:
    """Print a packaged schema by report identity or canonical ID."""
    if (report is None) == (schema_id is None):
        raise click.UsageError("provide exactly one of REPORT or --id")
    try:
        if report is not None:
            document = current_schema(report)
        else:
            assert schema_id is not None
            document = schema_for_id(schema_id)
    except ValueError as error:
        raise click.UsageError(str(error)) from error
    click.echo(json.dumps(document, indent=2))
