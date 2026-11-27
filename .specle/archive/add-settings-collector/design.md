# Technical design: Settings collector

## Overview

Add a standalone `settings` mode that reports consequential repository configuration without
exposing secret values or ruleset bypass identities. It combines one GraphQL query for core
repository, protection, and ruleset data with independently paginated REST listings for Actions
variable and secret names.

The first implementation slice establishes a reusable GraphQL partial-data condition. GidgetHub
raises `QueryError` whenever a response has an `errors` member, even when its retained response
also has usable `data`; ghbot must preserve that data rather than converting the whole response to
an unavailable result.

## Architecture

```text
GitHub GraphQL response
  ├─ data only ────────────────> projected settings sections
  ├─ data + field errors ──────> GitHubGraphQLPartialDataError(data, errors)
  │                                └─ project usable sections; mark errored sections unavailable
  └─ no usable data ───────────> existing GitHub API error translation

SettingsRepoProcessor
  ├─ GraphQL core settings, default-branch protection, rulesets
  ├─ REST Actions variable-name listing
  ├─ REST Actions secret-name listing
  └─ RepoResult(settings sections + unavailable metadata)
       └─ SettingsCollectionReport ─> plain or JSON output
```

`SettingsMode` is discoverable but has no `combine_key`, so it is a standalone command and is
excluded from `combo`. It still provides a collection factory for `run_mode`.

## GraphQL partial-data contract

Add `GitHubGraphQLPartialDataError`, a `GitHubApiError` subtype carrying the response `data`
mapping and a normalised sequence of GraphQL error mappings. `github_api_call()` will recognise a
GidgetHub GraphQL query error with a non-empty mapping at `response["data"]` after checking for
rate-limit conditions. It raises the partial-data error instead of discarding the data.

Primary and secondary rate-limit errors remain fatal and take precedence over partial reporting.
GraphQL responses with no usable `data` keep the existing not-found, forbidden, and ordinary API
error translation. Callers catch the partial-data condition before generic `GitHubApiError` and
must use its data deliberately; it is never silently treated as a normal success.

The settings processor maps GraphQL error paths to its three core sections:

| Error path area | Settings section | Result |
| --- | --- | --- |
| general repository or security field | `general` or `security` | `null` and unavailable metadata |
| default-branch protection field | `classic_protection` | `null` and unavailable metadata |
| rulesets connection, rules, or conditions | `rulesets` | `null` and unavailable metadata |
| a ruleset's bypass count | that ruleset only | retain the ruleset, omit `bypass_actors`, and record bypass presence as unavailable |
| unmappable repository-level error | every affected GraphQL section | `null` and unavailable metadata |

Each affected section produces one safe `fetch` monitor error. Its reason is `forbidden` only for
the recognised GraphQL permission condition; otherwise it is `error`. A fetched `false`, empty
list, or absent classic protection is valid data, not unavailability.

If core GraphQL data is unavailable, the processor still attempts the independent Actions
listings. A repository result is `partial` whenever at least one settings section was fetched; it
is `failed` only when no reportable section can be obtained. This retains the client-level API
failure while avoiding an empty failure where usable independent settings exist.

The existing issues processor adopts the same exception path for its pull-request query. It
processes a valid returned connection; if errors make the connection unusable, it retains the
current unavailable-metric behaviour rather than misreporting an empty PR set.

## API and projected data

The core query is parameterised by owner and repository and fetches only these projected fields:

- repository visibility, default branch, template state, merge methods and their configured
  message/title behaviour, delete-on-merge, auto-merge, update-branch, forking, commit sign-off,
  and enabled issues/discussions/projects/wiki features;
- available security and policy flags exposed by GraphQL;
- `defaultBranchRef.branchProtectionRule` with consequential classic-protection fields;
- repository rulesets with name, target, source type, enforcement, rule types, ref-name include/
  exclude conditions, and `bypassActors(first: 1) { totalCount }` only.

Ruleset bypass output is `true` or `false` when GitHub returns the count. If only the bypass count
is unavailable, the ruleset remains in the output and omits `bypass_actors`; availability metadata
records that omission separately. The query never selects `bypassActors.nodes` or actor
identifiers. Ruleset source is rendered from its GraphQL type and safe repository/organisation
identity when present.

Actions variables and secrets use `getiter(..., iterable_key="variables")` and
`getiter(..., iterable_key="secrets")` on their respective repository endpoints. Extend the
`GitHubClient` protocol to include GidgetHub's `iterable_key` keyword so both endpoints paginate
without manual page loops. Project only each entry's `name`; values, URLs, keys, and raw payloads
are discarded.

Per-repository JSON has stable section keys:

```json
{
  "repository": "owner/repo",
  "general": {"visibility": "PUBLIC", "default_branch": "main"},
  "security": {"vulnerability_alerts_enabled": true},
  "classic_protection": null,
  "rulesets": [],
  "actions_variables": ["DEPLOY_ENV"],
  "actions_secrets": ["PYPI_TOKEN"],
  "unavailable": {
    "classic_protection": {"reason": "forbidden"}
  }
}
```

`null` represents unavailable sections, while empty lists represent fetched-empty Actions or
ruleset data. The new `ghbot://schemas/settings/1.0.json` schema describes this document and is
registered alongside the existing packaged schemas.

## Rendering and command

`ghbot settings` supports default plain output, `--plain`, `--json`, and `--output`; it does not
accept `--table` and has no `combo` participation. Plain output is one detailed repository block
with grouped General, Security, Branch protection, Rulesets, and Actions headings. Unavailable
sections use the established `N/A (<reason>)` presentation. JSON preserves `null`, empty lists,
repository status, and availability metadata without embedding schema IDs in report payloads.

## Error handling

| Condition | Processor result |
| --- | --- |
| successful core section | projected value |
| GraphQL data plus field error | usable values plus unavailable affected section; bypass-only errors omit that property without discarding the ruleset |
| variable or secret listing failure | only that list unavailable; other sections retained |
| fetched-empty rulesets, variables, or secrets | empty list, no error |
| no usable core data but independent REST data | partial result |
| no reportable section | failed result with safe errors |
| primary/secondary rate limit or other fatal error | re-raise unchanged |

## Test strategy

- Client tests prove GidgetHub query errors with `data` become the explicit partial-data
  condition, while no-data, forbidden, not-found, and rate-limit paths retain their semantics.
- Settings processor tests cover projection, default-branch protection absence, ruleset bypass
  count-only handling, per-section GraphQL errors, no usable GraphQL data with usable REST data,
  and independent Actions failures/redaction.
- Issues tests cover processing a usable partial GraphQL connection and preserving unavailable PR
  metrics when the connection is unusable.
- Mode/report tests cover discovery without combo, option validation, plain and JSON rendering,
  unavailable versus empty semantics, output files, schema registration, and JSON-schema
  validation.
- Run the required pytest, Ruff, ty, and formatting gates through `uv run`.
