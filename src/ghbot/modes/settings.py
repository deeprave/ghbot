"""Repository settings inventory mode."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import click

from ghbot.errors import (
    FatalError,
    GitHubApiError,
    GitHubGraphQLPartialDataError,
    GitHubPrimaryRateLimitError,
    GitHubSecondaryRateLimitError,
)
from ghbot.github.client import github_api_call
from ghbot.log import get_logger
from ghbot.processor import (
    FeedbackEvent,
    RepoResult,
    record_unavailable,
    report_metadata,
    unavailable_reason,
)
from ghbot.report_style import (
    JSONReportStyle,
    PlainReportStyle,
    ReportStyle,
    output_format,
    write_report,
)
from ghbot.runner import run_mode

log = get_logger(__name__)

_SETTINGS_QUERY = """
query RepositorySettings($owner: String!, $repo: String!) {
  repository(owner: $owner, name: $repo) {
    visibility
    isTemplate
    mergeCommitAllowed
    squashMergeAllowed
    rebaseMergeAllowed
    squashMergeCommitTitle
    squashMergeCommitMessage
    deleteBranchOnMerge
    autoMergeAllowed
    allowUpdateBranch
    forkingAllowed
    webCommitSignoffRequired
    hasIssuesEnabled
    hasDiscussionsEnabled
    hasProjectsEnabled
    hasWikiEnabled
    hasVulnerabilityAlertsEnabled
    isSecurityPolicyEnabled
    defaultBranchRef {
      name
      branchProtectionRule {
        pattern
        isAdminEnforced
        allowsDeletions
        allowsForcePushes
        requiresApprovingReviews
        requiredApprovingReviewCount
        requiresCodeOwnerReviews
        requiresCommitSignatures
        requiresConversationResolution
        requiresLinearHistory
        requiresStatusChecks
        requiresStrictStatusChecks
      }
    }
    rulesets(first: 100, includeParents: true) {
      pageInfo { hasNextPage }
      nodes {
        name
        target
        enforcement
        source {
          __typename
          ... on Repository { nameWithOwner }
          ... on Organization { login }
          ... on Enterprise { slug }
        }
        conditions { refName { include exclude } }
        rules(first: 100) { nodes { type } pageInfo { hasNextPage } }
        bypassActors(first: 1) { totalCount }
      }
    }
  }
}
"""

_CORE_SECTIONS = ("general", "security", "classic_protection", "rulesets")
_SECURITY_ANALYSIS_KEYS = (
    "advanced_security",
    "code_scanning",
    "secret_scanning",
    "secret_scanning_push_protection",
)


class SettingsRepoProcessor:
    """Collect consequential, non-secret settings for one repository."""

    def __init__(
        self,
        owner: str,
        repo: str,
        gh: Any,
        monitor: Any,
        options: dict | None = None,
        *,
        owner_type: str | None = None,
    ) -> None:
        if not owner or not repo:
            raise ValueError("owner and repo must be non-empty strings")
        self._owner = owner
        self._repo = repo
        self._gh = gh
        self._monitor = monitor
        self._owner_type = owner_type
        del options

    @property
    def owner(self) -> str:
        return self._owner

    @property
    def repo(self) -> str:
        return self._repo

    @property
    def owner_type(self) -> str | None:
        return self._owner_type

    async def run(self) -> RepoResult:
        result = RepoResult(owner=self._owner, repo=self._repo)
        try:
            await self._fetch_core_settings(result)
            await self._fetch_security_analysis(result)
            await self._fetch_actions_names(
                result,
                metric="actions_variables",
                endpoint="/repos/{owner}/{repo}/actions/variables",
                iterable_key="variables",
            )
            await self._fetch_actions_names(
                result,
                metric="actions_secrets",
                endpoint="/repos/{owner}/{repo}/actions/secrets",
                iterable_key="secrets",
            )
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError, FatalError):
            raise
        except Exception as error:  # noqa: BLE001 - processors return failed results.
            result.status = "failed"
            result.errors.append(str(error))
            await self._monitor.send_event(
                FeedbackEvent("error", "error", f"unexpected settings error: {error}")
            )
        else:
            if result.errors:
                result.status = (
                    "partial" if _has_reportable_settings(result) else "failed"
                )
        return result

    async def _fetch_core_settings(self, result: RepoResult) -> None:
        try:
            async with github_api_call(self._gh):
                data = await self._gh.graphql(
                    _SETTINGS_QUERY, owner=self._owner, repo=self._repo
                )
        except GitHubGraphQLPartialDataError as error:
            try:
                self._project_core(result, error.data)
            except GitHubApiError as projection_error:
                await self._record_core_projection_error(result, projection_error)
            else:
                await self._record_partial_sections(result, error)
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            for section in _CORE_SECTIONS:
                result.results[section] = None
            record_unavailable(
                result, *_CORE_SECTIONS, reason=unavailable_reason(error), error=error
            )
            result.errors.append(f"settings: {error}")
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch settings: {error}")
            )
        else:
            try:
                self._project_core(result, data)
            except GitHubApiError as error:
                await self._record_core_projection_error(result, error)

    async def _record_core_projection_error(
        self, result: RepoResult, error: GitHubApiError
    ) -> None:
        for section in _CORE_SECTIONS:
            result.results[section] = None
        record_unavailable(
            result, *_CORE_SECTIONS, reason=unavailable_reason(error), error=error
        )
        result.errors.append(f"settings: {error}")
        await self._monitor.send_event(
            FeedbackEvent("fetch", "error", f"failed to project settings: {error}")
        )

    async def _fetch_security_analysis(self, result: RepoResult) -> None:
        try:
            async with github_api_call(self._gh):
                data = await self._gh.getitem(
                    "/repos/{owner}/{repo}",
                    url_vars={"owner": self._owner, "repo": self._repo},
                )
            analysis = (
                data.get("security_and_analysis") if isinstance(data, Mapping) else None
            )
            if analysis is None:
                await self._record_security_analysis_unavailable(result)
                return
            if not isinstance(analysis, Mapping):
                raise GitHubApiError("security analysis response is invalid")
            security = result.results.get("security")
            if not isinstance(security, dict):
                return
            for output, sources in (
                ("advanced_security", ("advanced_security",)),
                ("code_scanning", ("code_security", "code_scanning")),
                ("secret_scanning", ("secret_scanning",)),
                (
                    "secret_scanning_push_protection",
                    ("secret_scanning_push_protection",),
                ),
            ):
                value = next(
                    (analysis.get(source) for source in sources if source in analysis),
                    None,
                )
                if isinstance(value, Mapping):
                    security[output] = value.get("status")
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            await self._record_security_analysis_unavailable(result, error)
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch", "error", f"failed to fetch security analysis: {error}"
                )
            )

    async def _record_security_analysis_unavailable(
        self, result: RepoResult, error: GitHubApiError | None = None
    ) -> None:
        security = result.results.get("security")
        if isinstance(security, dict):
            for key in _SECURITY_ANALYSIS_KEYS:
                security[key] = None
        unavailable_error = error or GitHubApiError(
            "security analysis configuration is unavailable"
        )
        record_unavailable(
            result,
            *_SECURITY_ANALYSIS_KEYS,
            reason=unavailable_reason(unavailable_error),
            error=unavailable_error,
        )
        result.errors.append(f"security analysis: {unavailable_error}")

    def _project_core(self, result: RepoResult, data: Mapping[str, object]) -> None:
        repository = data.get("repository")
        if not isinstance(repository, Mapping):
            raise GitHubApiError("settings response has no repository data")
        branch = repository.get("defaultBranchRef")
        if not isinstance(branch, Mapping):
            branch = {}
        result.results["general"] = {
            "visibility": repository.get("visibility"),
            "default_branch": branch.get("name"),
            "is_template": repository.get("isTemplate"),
            "merge_commit_allowed": repository.get("mergeCommitAllowed"),
            "squash_merge_allowed": repository.get("squashMergeAllowed"),
            "rebase_merge_allowed": repository.get("rebaseMergeAllowed"),
            "squash_merge_commit_title": repository.get("squashMergeCommitTitle"),
            "squash_merge_commit_message": repository.get("squashMergeCommitMessage"),
            "delete_branch_on_merge": repository.get("deleteBranchOnMerge"),
            "auto_merge_allowed": repository.get("autoMergeAllowed"),
            "allow_update_branch": repository.get("allowUpdateBranch"),
            "forking_allowed": repository.get("forkingAllowed"),
            "web_commit_signoff_required": repository.get("webCommitSignoffRequired"),
            "issues_enabled": repository.get("hasIssuesEnabled"),
            "discussions_enabled": repository.get("hasDiscussionsEnabled"),
            "projects_enabled": repository.get("hasProjectsEnabled"),
            "wiki_enabled": repository.get("hasWikiEnabled"),
        }
        result.results["security"] = {
            "vulnerability_alerts_enabled": repository.get(
                "hasVulnerabilityAlertsEnabled"
            ),
            "security_policy_enabled": repository.get("isSecurityPolicyEnabled"),
        }
        result.results["classic_protection"] = _classic_protection(branch)
        rulesets, bypass_available = _rulesets(repository.get("rulesets"))
        result.results["rulesets"] = rulesets
        result.results["rulesets_truncated"] = _connection_is_truncated(
            repository.get("rulesets")
        )
        if not bypass_available:
            record_unavailable(result, "ruleset_bypass_actors", reason="error")
            result.errors.append("ruleset bypass presence is unavailable")

    async def _record_partial_sections(
        self, result: RepoResult, error: GitHubGraphQLPartialDataError
    ) -> None:
        sections = _sections_for_graphql_errors(error.errors)
        bypass_errors = tuple(
            details
            for details in error.errors
            if "bypassActors" in _graphql_error_path(details)
        )
        if bypass_errors:
            _omit_unavailable_bypass_actors(result, bypass_errors)
            record_unavailable(
                result,
                "ruleset_bypass_actors",
                reason=_graphql_error_reason(bypass_errors),
                error=error,
            )
            await self._monitor.send_event(
                FeedbackEvent(
                    "fetch", "error", "ruleset bypass presence is unavailable"
                )
            )
        for section in sections:
            result.results[section] = None
            matching = tuple(
                details
                for details in error.errors
                if section in _sections_for_graphql_errors((details,))
            )
            record_unavailable(
                result,
                section,
                reason=_graphql_error_reason(matching),
                error=error,
            )
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"settings {section} is unavailable")
            )
        result.errors.append("settings: partial GraphQL response")

    async def _fetch_actions_names(
        self,
        result: RepoResult,
        *,
        metric: str,
        endpoint: str,
        iterable_key: str,
    ) -> None:
        try:
            async with github_api_call(self._gh):
                entries = [
                    entry
                    async for entry in self._gh.getiter(
                        endpoint,
                        url_vars={"owner": self._owner, "repo": self._repo},
                        iterable_key=iterable_key,
                    )
                ]
            names = [
                entry.get("name") for entry in entries if isinstance(entry, Mapping)
            ]
            if not all(isinstance(name, str) for name in names):
                raise GitHubApiError(f"{metric} response has an invalid name")
            result.results[metric] = names
        except (GitHubPrimaryRateLimitError, GitHubSecondaryRateLimitError):
            raise
        except GitHubApiError as error:
            result.results[metric] = None
            record_unavailable(
                result, metric, reason=unavailable_reason(error), error=error
            )
            result.errors.append(f"{metric}: {error}")
            await self._monitor.send_event(
                FeedbackEvent("fetch", "error", f"failed to fetch {metric}: {error}")
            )


def _classic_protection(branch: Mapping[str, object]) -> dict[str, object] | None:
    rule = branch.get("branchProtectionRule")
    if rule is None:
        return None
    if not isinstance(rule, Mapping):
        raise GitHubApiError("classic protection response is invalid")
    return {
        "pattern": rule.get("pattern"),
        "admin_enforced": rule.get("isAdminEnforced"),
        "allows_deletions": rule.get("allowsDeletions"),
        "allows_force_pushes": rule.get("allowsForcePushes"),
        "requires_approving_reviews": rule.get("requiresApprovingReviews"),
        "required_approving_review_count": rule.get("requiredApprovingReviewCount"),
        "requires_code_owner_reviews": rule.get("requiresCodeOwnerReviews"),
        "requires_commit_signatures": rule.get("requiresCommitSignatures"),
        "requires_conversation_resolution": rule.get("requiresConversationResolution"),
        "requires_linear_history": rule.get("requiresLinearHistory"),
        "requires_status_checks": rule.get("requiresStatusChecks"),
        "requires_strict_status_checks": rule.get("requiresStrictStatusChecks"),
    }


def _rulesets(value: object) -> tuple[list[dict[str, object]] | None, bool]:
    if value is None:
        return None, True
    nodes = value.get("nodes") if isinstance(value, Mapping) else None
    if not isinstance(nodes, list):
        raise GitHubApiError("rulesets response is invalid")
    projected = []
    bypass_available = True
    for node in nodes:
        if not isinstance(node, Mapping):
            raise GitHubApiError("ruleset entry is invalid")
        conditions = node.get("conditions")
        ref_name = conditions.get("refName") if isinstance(conditions, Mapping) else {}
        rules = node.get("rules")
        rule_nodes = rules.get("nodes") if isinstance(rules, Mapping) else []
        if not isinstance(rule_nodes, list):
            raise GitHubApiError("ruleset rules response is invalid")
        bypass = node.get("bypassActors")
        count = bypass.get("totalCount") if isinstance(bypass, Mapping) else None
        source = node.get("source")
        item: dict[str, object] = {
            "name": node.get("name"),
            "target": node.get("target"),
            "source": source.get("__typename") if isinstance(source, Mapping) else None,
            "source_identity": _ruleset_source_identity(source),
            "enforcement": node.get("enforcement"),
            "rule_types": [
                rule.get("type") for rule in rule_nodes if isinstance(rule, Mapping)
            ],
            "ref_name": {
                "include": ref_name.get("include", [])
                if isinstance(ref_name, Mapping)
                else [],
                "exclude": ref_name.get("exclude", [])
                if isinstance(ref_name, Mapping)
                else [],
            },
            "rules_truncated": _connection_is_truncated(rules),
        }
        if isinstance(count, int):
            item["bypass_actors"] = count > 0
        else:
            bypass_available = False
        projected.append(item)
    return projected, bypass_available


def _sections_for_graphql_errors(
    errors: tuple[Mapping[str, object], ...],
) -> set[str]:
    sections: set[str] = set()
    for error in errors:
        path_values = _graphql_error_path(error)
        if "rulesets" in path_values:
            if "bypassActors" in path_values:
                continue
            sections.add("rulesets")
        elif "branchProtectionRule" in path_values:
            sections.add("classic_protection")
        elif "defaultBranchRef" in path_values:
            sections.add("general")
            sections.add("classic_protection")
        elif any(
            value in path_values
            for value in ("hasVulnerabilityAlertsEnabled", "isSecurityPolicyEnabled")
        ):
            sections.add("security")
        else:
            sections.update(_CORE_SECTIONS)
    return sections if errors else set(_CORE_SECTIONS)


def _graphql_error_path(error: Mapping[str, object]) -> tuple[object, ...]:
    path = error.get("path")
    return tuple(path) if isinstance(path, list) else ()


def _omit_unavailable_bypass_actors(
    result: RepoResult, errors: tuple[Mapping[str, object], ...]
) -> None:
    rulesets = result.results.get("rulesets")
    if not isinstance(rulesets, list):
        return
    indexes = {
        path[path.index("nodes") + 1]
        for error in errors
        if (path := _graphql_error_path(error))
        and "nodes" in path
        and path.index("nodes") + 1 < len(path)
        and isinstance(path[path.index("nodes") + 1], int)
    }
    for index, ruleset in enumerate(rulesets):
        if isinstance(ruleset, dict) and (not indexes or index in indexes):
            ruleset.pop("bypass_actors", None)


def _graphql_error_reason(
    errors: tuple[Mapping[str, object], ...],
) -> Literal["forbidden", "error"]:
    for error in errors:
        extensions = error.get("extensions")
        code = extensions.get("code") if isinstance(extensions, Mapping) else None
        error_type = error.get("type")
        extension_type = (
            extensions.get("type") if isinstance(extensions, Mapping) else None
        )
        if "FORBIDDEN" in (error_type, code, extension_type):
            return "forbidden"
    return "error"


def _ruleset_source_identity(source: object) -> str | None:
    if not isinstance(source, Mapping):
        return None
    for key in ("nameWithOwner", "login", "slug"):
        value = source.get(key)
        if isinstance(value, str):
            return value
    return None


def _connection_is_truncated(connection: object) -> bool:
    if not isinstance(connection, Mapping):
        return False
    page_info = connection.get("pageInfo")
    return (
        bool(page_info.get("hasNextPage")) if isinstance(page_info, Mapping) else False
    )


def _has_reportable_settings(result: RepoResult) -> bool:
    return any(value is not None for value in result.results.values())


@dataclass(slots=True)
class SettingsCollectionReport:
    results: list[RepoResult] = field(default_factory=list)

    def add(self, result: RepoResult) -> None:
        self.results.append(result)

    def document(self) -> dict[str, object]:
        return {
            "summary": {"repos_scanned": len(self.results)},
            "repositories": [
                {
                    "owner": result.owner,
                    "repo": result.repo,
                    "repository": f"{result.owner}/{result.repo}",
                    **{
                        key: result.results.get(key)
                        for key in (
                            "general",
                            "security",
                            "classic_protection",
                            "rulesets",
                            "actions_variables",
                            "actions_secrets",
                        )
                    },
                    "rulesets_truncated": bool(
                        result.results.get("rulesets_truncated", False)
                    ),
                    **report_metadata(result),
                }
                for result in sorted(
                    self.results, key=lambda item: (item.owner, item.repo)
                )
            ],
        }

    def render(self, format: str = "plain") -> str:
        style = ReportStyle.from_format(format)
        if isinstance(style, JSONReportStyle):
            return style.render_document(self.document())
        assert isinstance(style, PlainReportStyle)
        lines = [f"Repositories scanned: {len(self.results)}"]
        for result in sorted(self.results, key=lambda item: (item.owner, item.repo)):
            lines.extend(["", f"{result.owner}/{result.repo}"])
            for heading, key in (
                ("General", "general"),
                ("Security", "security"),
                ("Classic protection", "classic_protection"),
                ("Rulesets", "rulesets"),
                ("Actions variables", "actions_variables"),
                ("Actions secrets", "actions_secrets"),
            ):
                value = result.results.get(key)
                unavailable = result.unavailable.get(key)
                if value is None:
                    state = unavailable.reason if unavailable else "not configured"
                    lines.append(f"  {heading}: N/A ({state})")
                    continue
                lines.append(f"  {heading}:")
                lines.extend(_plain_settings_lines(value, indent="    "))
            if unavailable := result.unavailable.get("ruleset_bypass_actors"):
                lines.append(f"  Ruleset bypass actors: N/A ({unavailable.reason})")
            if result.results.get("rulesets_truncated"):
                lines.append("  Rulesets: truncated after 100 entries")
        return style.render_lines(lines)


def _plain_settings_lines(value: object, *, indent: str) -> list[str]:
    if isinstance(value, Mapping):
        return [
            f"{indent}{key.replace('_', ' ')}: {_plain_value(item)}"
            for key, item in value.items()
        ]
    if isinstance(value, list):
        if not value:
            return [f"{indent}None"]
        lines: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                name = item.get("name", "unnamed")
                lines.append(f"{indent}- {name}")
                lines.extend(_plain_settings_lines(item, indent=f"{indent}  "))
            else:
                lines.append(f"{indent}- {_plain_value(item)}")
        return lines
    return [f"{indent}{_plain_value(value)}"]


def _plain_value(value: object) -> object:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "None"
    if value is None:
        return "None"
    return value


@dataclass(frozen=True, slots=True)
class SettingsMode:
    name: str = "settings"

    @property
    def command(self) -> click.Command:
        return settings

    def new_collection(self, options: dict) -> SettingsCollectionReport:
        del options
        return SettingsCollectionReport()

    def new_processor(self, owner, repo, gh, monitor, options, *, owner_type=None):
        return SettingsRepoProcessor(
            owner, repo, gh, monitor, options, owner_type=owner_type
        )


MODE = SettingsMode()


@click.command()
@click.option("--plain", "format_plain", is_flag=True, default=False)
@click.option("--json", "format_json", is_flag=True, default=False)
@click.option("--output", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.pass_context
def settings(
    ctx: click.Context, format_plain: bool, format_json: bool, output: Path | None
) -> None:
    """Scan for repository settings."""
    selected_format = output_format(
        plain=format_plain, table=False, json_format=format_json
    )
    try:
        collection = asyncio.run(
            run_mode(ctx.obj["cfg"], MODE, {"format": selected_format})
        )
    except FatalError as error:
        log.error(error.message)
        sys.exit(error.exit_code)
    write_report(collection.render(selected_format), output)
    if getattr(collection, "exit_code", 0) == 4:
        log.error("rate limited; wrote incomplete report")
        sys.exit(4)
    if getattr(collection, "exit_code", 0) == 8:
        log.error(
            "unavailable explicit repository; wrote report with missing expected data"
        )
        sys.exit(8)
