from collections.abc import AsyncIterator

import pytest

from ghbot.errors import GitHubApiError, GitHubGraphQLPartialDataError
from ghbot.modes.settings import SettingsRepoProcessor


class Monitor:
    def __init__(self) -> None:
        self.events = []

    async def send_event(self, event) -> None:
        self.events.append(event)


class GitHub:
    def __init__(self) -> None:
        self.queries = []
        self.iterations = []

    async def graphql(self, query: str, **variables):
        self.queries.append((query, variables))
        return {
            "repository": {
                "visibility": "PRIVATE",
                "defaultBranchRef": {
                    "name": "main",
                    "branchProtectionRule": None,
                },
                "isTemplate": False,
                "mergeCommitAllowed": True,
                "squashMergeAllowed": True,
                "rebaseMergeAllowed": False,
                "deleteBranchOnMerge": True,
                "autoMergeAllowed": True,
                "allowUpdateBranch": True,
                "forkingAllowed": False,
                "webCommitSignoffRequired": True,
                "hasIssuesEnabled": True,
                "hasDiscussionsEnabled": False,
                "hasProjectsEnabled": True,
                "hasWikiEnabled": False,
                "hasVulnerabilityAlertsEnabled": True,
                "isSecurityPolicyEnabled": True,
                "rulesets": {
                    "nodes": [
                        {
                            "name": "main protection",
                            "target": "BRANCH",
                            "enforcement": "ACTIVE",
                            "source": {"__typename": "Repository"},
                            "conditions": {"refName": {"include": ["~DEFAULT_BRANCH"]}},
                            "rules": {"nodes": [{"type": "REQUIRED_STATUS_CHECKS"}]},
                            "bypassActors": {"totalCount": 1},
                        }
                    ]
                },
            }
        }

    async def getitem(self, url: str, *, url_vars=None):
        raise AssertionError(f"unexpected getitem: {url}")

    def getiter(
        self, url: str, *, url_vars=None, iterable_key=None
    ) -> AsyncIterator[dict]:
        self.iterations.append((url, url_vars, iterable_key))

        async def entries():
            if iterable_key == "variables":
                yield {"name": "DEPLOY_ENV", "value": "must-not-leak"}
            if iterable_key == "secrets":
                yield {"name": "PYPI_TOKEN"}

        return entries()


@pytest.mark.anyio
async def test_collects_curated_settings_without_bypass_actors_or_values():
    gh = GitHub()
    processor = SettingsRepoProcessor("owner", "repo", gh, Monitor())

    result = await processor.run()

    assert result.status == "success"
    assert result.results["general"] == {
        "visibility": "PRIVATE",
        "default_branch": "main",
        "is_template": False,
        "merge_commit_allowed": True,
        "squash_merge_allowed": True,
        "rebase_merge_allowed": False,
        "delete_branch_on_merge": True,
        "auto_merge_allowed": True,
        "allow_update_branch": True,
        "forking_allowed": False,
        "web_commit_signoff_required": True,
        "issues_enabled": True,
        "discussions_enabled": False,
        "projects_enabled": True,
        "wiki_enabled": False,
    }
    assert result.results["security"] == {
        "vulnerability_alerts_enabled": True,
        "security_policy_enabled": True,
    }
    assert result.results["classic_protection"] is None
    assert result.results["rulesets"] == [
        {
            "name": "main protection",
            "target": "BRANCH",
            "source": "Repository",
            "enforcement": "ACTIVE",
            "rule_types": ["REQUIRED_STATUS_CHECKS"],
            "ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []},
            "bypass_actors": True,
        }
    ]
    assert "value" not in repr(result.results)
    assert all(key != "bypassActors" for key in result.results["rulesets"][0])


@pytest.mark.anyio
async def test_lists_actions_names_without_retaining_values():
    gh = GitHub()
    processor = SettingsRepoProcessor("owner", "repo", gh, Monitor())

    result = await processor.run()

    assert result.results["actions_variables"] == ["DEPLOY_ENV"]
    assert result.results["actions_secrets"] == ["PYPI_TOKEN"]
    assert "must-not-leak" not in repr(result.results)
    assert [entry[2] for entry in gh.iterations] == ["variables", "secrets"]


@pytest.mark.anyio
async def test_partial_graphql_ruleset_error_retains_other_settings():
    class PartialGitHub(GitHub):
        async def graphql(self, query: str, **variables):
            data = await super().graphql(query, **variables)
            raise GitHubGraphQLPartialDataError(
                "rulesets unavailable",
                data=data,
                errors=(
                    {
                        "message": "Resource not accessible",
                        "path": ["repository", "rulesets"],
                    },
                ),
            )

    result = await SettingsRepoProcessor(
        "owner", "repo", PartialGitHub(), Monitor()
    ).run()

    assert result.status == "partial"
    assert result.results["general"]["default_branch"] == "main"
    assert result.results["rulesets"] is None
    assert result.unavailable["rulesets"].reason == "error"


@pytest.mark.anyio
async def test_partial_graphql_forbidden_rulesets_are_unavailable_not_failed():
    class PartialGitHub(GitHub):
        async def graphql(self, query: str, **variables):
            data = await super().graphql(query, **variables)
            raise GitHubGraphQLPartialDataError(
                "bypass actors forbidden",
                data=data,
                errors=(
                    {
                        "path": ["repository", "rulesets", "nodes", 0, "bypassActors"],
                        "extensions": {"code": "FORBIDDEN"},
                    },
                ),
            )

    result = await SettingsRepoProcessor(
        "owner", "repo", PartialGitHub(), Monitor()
    ).run()

    assert result.status == "partial"
    assert result.results["rulesets"][0]["name"] == "main protection"
    assert "bypass_actors" not in result.results["rulesets"][0]
    assert result.unavailable["ruleset_bypass_actors"].reason == "forbidden"


@pytest.mark.anyio
async def test_partial_graphql_rulesets_connection_error_remains_unavailable():
    class PartialGitHub(GitHub):
        async def graphql(self, query: str, **variables):
            data = await super().graphql(query, **variables)
            data["repository"]["rulesets"] = None
            raise GitHubGraphQLPartialDataError(
                "rulesets forbidden",
                data=data,
                errors=(
                    {
                        "path": ["repository", "rulesets"],
                        "extensions": {"code": "FORBIDDEN"},
                    },
                ),
            )

    result = await SettingsRepoProcessor(
        "owner", "repo", PartialGitHub(), Monitor()
    ).run()

    assert result.status == "partial"
    assert result.results["rulesets"] is None
    assert result.unavailable["rulesets"].reason == "forbidden"


@pytest.mark.anyio
async def test_actions_endpoint_failure_retains_other_settings():
    class VariableFailureGitHub(GitHub):
        def getiter(self, url: str, *, url_vars=None, iterable_key=None):
            if iterable_key == "variables":

                async def failed():
                    raise GitHubApiError("variables unavailable")
                    yield  # pragma: no cover

                return failed()
            return super().getiter(url, url_vars=url_vars, iterable_key=iterable_key)

    result = await SettingsRepoProcessor(
        "owner", "repo", VariableFailureGitHub(), Monitor()
    ).run()

    assert result.status == "partial"
    assert result.results["actions_variables"] is None
    assert result.unavailable["actions_variables"].reason == "error"
    assert result.results["actions_secrets"] == ["PYPI_TOKEN"]


@pytest.mark.anyio
async def test_empty_actions_lists_are_not_unavailable():
    class EmptyActionsGitHub(GitHub):
        def getiter(self, url: str, *, url_vars=None, iterable_key=None):
            async def entries():
                return
                yield  # pragma: no cover

            return entries()

    result = await SettingsRepoProcessor(
        "owner", "repo", EmptyActionsGitHub(), Monitor()
    ).run()

    assert result.results["actions_variables"] == []
    assert result.results["actions_secrets"] == []
    assert "actions_variables" not in result.unavailable
    assert "actions_secrets" not in result.unavailable
