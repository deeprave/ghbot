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


def output_format(*, plain: bool, table: bool, json_format: bool) -> str:
    """Resolve mode-owned output flags to a report-style name."""
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
class ReportOutcome:
    """A rendered collection together with its run-completion state."""

    collection: CollectionReport
    abort_reason: str | None = None
    not_processed: tuple[str | tuple[str, str], ...] = ()
    explicit_unavailable: bool = False

    @property
    def complete(self) -> bool:
        return self.abort_reason is None

    @property
    def exit_code(self) -> int:
        """Return the post-output process status for this report."""
        if self.abort_reason == "rate_limited":
            return 4
        return 8 if self.explicit_unavailable else 0

    @property
    def sections(self) -> tuple[ReportSection, ...]:
        """Expose combined sections for existing library callers."""
        return getattr(self.collection, "sections")  # noqa: B009 - protocol optionality.

    def document(self) -> dict[str, object]:
        document = dict(self.collection.document())
        document.update(
            {
                "complete": self.complete,
                "abort_reason": self.abort_reason,
                "not_processed": [
                    {
                        "repository": (
                            repository[0]
                            if isinstance(repository, tuple)
                            else repository
                        ),
                        "reason": (
                            repository[1]
                            if isinstance(repository, tuple)
                            else self.abort_reason or "rate_limited"
                        ),
                    }
                    for repository in self.not_processed
                ],
            }
        )
        return document

    def render(self, format: str = "plain") -> str:
        if format == "json":
            return JSONReportStyle().render_document(self.document())
        text = self.collection.render(format)
        if self.complete:
            return text
        reason = self.abort_reason or "unknown"
        return f"INCOMPLETE: {reason.replace('_', ' ')}\n\n{text}"


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
            f"{section.name.capitalize()}\n{(section.collection.collection if isinstance(section.collection, ReportOutcome) else section.collection).render(format).rstrip()}"
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
