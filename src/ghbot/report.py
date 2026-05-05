"""Report formatting for security scan results."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click

from ghbot.processor import RepoResult

_LABEL_WIDTH = 26
_VALUE_WIDTH = 8
_REPOSITORY_WIDTH = 38
_DEPENDABOT_WIDTH = 12
_SCANNING_WIDTH = 10
_SECRETS_WIDTH = 9


def _fmt(label: str, value: int | str) -> str:
    return f"{label:<{_LABEL_WIDTH}}{value:>{_VALUE_WIDTH}}"


def _total(results: list[RepoResult], key: str) -> int | None:
    values = [r.results.get(key) for r in results]
    if all(v is None for v in values):
        return None
    return sum(v for v in values if v is not None)


def _display_total(value: int | None) -> int | str:
    return "N/A" if value is None else value


def _has_issues(result: RepoResult) -> bool:
    return any(
        v not in (None, 0)
        for v in (
            result.results.get("dependabot_alerts"),
            result.results.get("code_scanning_alerts"),
            result.results.get("secret_scanning_alerts"),
        )
    )


def _repos_with_issues(results: list[RepoResult]) -> int:
    return sum(1 for r in results if _has_issues(r))


def _summary(results: list[RepoResult]) -> dict[str, int | None]:
    return {
        "repos_scanned": len(results),
        "repos_with_issues": _repos_with_issues(results),
        "dependabot_alerts": _total(results, "dependabot_alerts"),
        "code_scanning_alerts": _total(results, "code_scanning_alerts"),
        "secret_scanning_alerts": _total(results, "secret_scanning_alerts"),
    }


def _summary_lines(results: list[RepoResult]) -> list[str]:
    summary = _summary(results)
    return [
        _fmt("Repos scanned:", _display_total(summary["repos_scanned"])),
        _fmt("Repos with issues:", _display_total(summary["repos_with_issues"])),
        _fmt("Dependabot alerts:", _display_total(summary["dependabot_alerts"])),
        _fmt(
            "Code scanning alerts:",
            _display_total(summary["code_scanning_alerts"]),
        ),
        _fmt(
            "Secret scanning alerts:",
            _display_total(summary["secret_scanning_alerts"]),
        ),
    ]


def _repos_to_show(results: list[RepoResult]) -> list[RepoResult]:
    return sorted(
        (r for r in results if _has_issues(r)),
        key=lambda r: f"{r.owner}/{r.repo}",
    )


def render_security_report(results: list[RepoResult], *, format: str = "plain") -> str:
    match format:
        case "plain":
            return _render_plain(results)
        case "table":
            return _render_table(results)
        case "json":
            return _render_json(results)
        case _:
            raise ValueError(f"unsupported security report format: {format}")


def print_security_report(
    results: list[RepoResult],
    *,
    format: str = "plain",
    output: Path | None = None,
) -> None:
    text = render_security_report(results, format=format)
    if output is None:
        sys.stdout.write(text)
        return
    try:
        output.write_text(text, encoding="utf-8")
    except OSError as e:
        raise click.ClickException(f"failed to write output file: {e}") from e


def _render_plain(results: list[RepoResult]) -> str:
    lines = _summary_lines(results)
    for r in _repos_to_show(results):
        lines.extend(
            [
                "",
                f"{r.owner}/{r.repo}",
                _fmt(
                    "  Dependabot alerts:",
                    _display(r.results.get("dependabot_alerts")),
                ),
                _fmt(
                    "  Code scanning alerts:",
                    _display(r.results.get("code_scanning_alerts")),
                ),
                _fmt(
                    "  Secret scanning alerts:",
                    _display(r.results.get("secret_scanning_alerts")),
                ),
            ]
        )
    return "\n".join(lines) + "\n"


def _render_table(results: list[RepoResult]) -> str:
    lines = _summary_lines(results)
    repos_to_show = _repos_to_show(results)
    if repos_to_show:
        lines.extend(["", _table_header(), _table_separator()])
        lines.extend(
            _table_row(
                f"{r.owner}/{r.repo}",
                _display(r.results.get("dependabot_alerts")),
                _display(r.results.get("code_scanning_alerts")),
                _display(r.results.get("secret_scanning_alerts")),
            )
            for r in repos_to_show
        )
    return "\n".join(lines) + "\n"


def _render_json(results: list[RepoResult]) -> str:
    return (
        json.dumps(
            {
                "summary": _summary(results),
                "repositories": [
                    {
                        "owner": r.owner,
                        "repo": r.repo,
                        "repository": f"{r.owner}/{r.repo}",
                        "dependabot_alerts": r.results.get("dependabot_alerts"),
                        "code_scanning_alerts": r.results.get("code_scanning_alerts"),
                        "secret_scanning_alerts": r.results.get(
                            "secret_scanning_alerts"
                        ),
                    }
                    for r in results
                ],
            },
            indent=2,
        )
        + "\n"
    )


def _display(value: int | None) -> int | str:
    return "N/A" if value is None else value


def _table_header() -> str:
    return (
        f"|{'Repository':<{_REPOSITORY_WIDTH}}"
        f"|{' Dependabot ':>{_DEPENDABOT_WIDTH}}"
        f"|{' Scanning ':>{_SCANNING_WIDTH}}"
        f"|{' Secrets ':>{_SECRETS_WIDTH}}|"
    )


def _table_separator() -> str:
    return (
        f"|{'-' * _REPOSITORY_WIDTH}"
        f"|{'-' * _DEPENDABOT_WIDTH}"
        f"|{'-' * _SCANNING_WIDTH}"
        f"|{'-' * _SECRETS_WIDTH}|"
    )


def _table_row(
    repository: str,
    dependabot: int | str,
    scanning: int | str,
    secrets: int | str,
) -> str:
    return (
        f"|{repository:<{_REPOSITORY_WIDTH}}"
        f"|{dependabot:>{_DEPENDABOT_WIDTH}}"
        f"|{scanning:>{_SCANNING_WIDTH}}"
        f"|{secrets:>{_SECRETS_WIDTH}}|"
    )
