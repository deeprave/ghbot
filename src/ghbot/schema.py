"""CLI access to packaged report schemas."""

import json

import click

from ghbot.schemas import current_schema, schema_entries, schema_for_id


@click.command()
@click.argument("report", required=False)
@click.option("--id", "schema_id", help="Canonical schema identifier")
@click.option("--list", "list_schemas", is_flag=True, help="List schema names and IDs")
def schema(report: str | None, schema_id: str | None, list_schemas: bool) -> None:
    """Print or list packaged schemas by identity or canonical ID."""
    if sum((report is not None, schema_id is not None, list_schemas)) != 1:
        raise click.UsageError("provide exactly one of REPORT, --id, or --list")
    if list_schemas:
        click.echo(
            json.dumps(
                [
                    {"name": name, "id": schema_id}
                    for name, schema_id in schema_entries()
                ],
                indent=2,
            )
        )
        return
    try:
        if report is not None:
            document = current_schema(report)
        else:
            assert schema_id is not None
            document = schema_for_id(schema_id)
    except ValueError as error:
        raise click.UsageError(str(error)) from error
    click.echo(json.dumps(document, indent=2))
