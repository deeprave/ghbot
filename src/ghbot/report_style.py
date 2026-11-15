"""Shared formatting primitives for report mode modules."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import click


@dataclass(frozen=True, slots=True)
class TableColumn:
    heading: str
    width: int
    align: Literal["left", "right"] = "left"


class ReportStyle:
    @classmethod
    def from_format(cls, format_name: str) -> ReportStyle:
        match format_name:
            case "plain":
                return PlainReportStyle()
            case "table":
                return MarkdownTableReportStyle()
            case "json":
                return JSONReportStyle()
            case _:
                raise ValueError(f"unsupported report format: {format_name}")


class PlainReportStyle(ReportStyle):
    def render_lines(self, lines: list[str]) -> str:
        return "\n".join(lines) + "\n"


class JSONReportStyle(ReportStyle):
    def render_document(self, document: dict[str, object]) -> str:
        return json.dumps(document, indent=2) + "\n"


class TableReportStyle(ReportStyle):
    def render_lines(self, lines: list[str]) -> str:
        return "\n".join(lines) + "\n"

    def header(self, columns: list[TableColumn]) -> str:
        return self.row(columns, [column.heading for column in columns])

    def separator(self, columns: list[TableColumn]) -> str:
        return "|" + "|".join("-" * column.width for column in columns) + "|"

    def row(self, columns: list[TableColumn], values: list[object]) -> str:
        cells = []
        for column, value in zip(columns, values, strict=True):
            cells.append(
                f"{value:>{column.width}}"
                if column.align == "right"
                else f"{value:<{column.width}}"
            )
        return "|" + "|".join(cells) + "|"


class MarkdownTableReportStyle(TableReportStyle):
    """The established pipe-delimited table style selected by ``--table``."""


class CollectionReport(Protocol):
    """The rendering surface shared by reportable mode collections."""

    def document(self) -> dict[str, object]: ...

    def render(self, format: str) -> str: ...


@dataclass(frozen=True, slots=True)
class ReportSection:
    name: str
    collection: CollectionReport


@dataclass(frozen=True, slots=True)
class CombinedCollectionReport:
    """Compose already-scanned reportable collections without a CLI command."""

    sections: tuple[ReportSection, ...]

    def document(self) -> dict[str, object]:
        return {
            section.name: section.collection.document() for section in self.sections
        }

    def render(self, format: str = "plain") -> str:
        style = ReportStyle.from_format(format)
        if isinstance(style, JSONReportStyle):
            return style.render_document(self.document())
        rendered = [
            f"{section.name.capitalize()}\n{section.collection.render(format).rstrip()}"
            for section in self.sections
        ]
        return "\n\n".join(rendered) + "\n"


def write_report(text: str, output: Path | None = None) -> None:
    if output is None:
        sys.stdout.write(text)
        return
    try:
        output.write_text(text, encoding="utf-8")
    except OSError as error:
        raise click.ClickException(f"failed to write output file: {error}") from error
