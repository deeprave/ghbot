# Requirements Document

## Introduction

ghbot can gather repository metadata (`info`) and surface security findings (`security`), but it
has no command dedicated to open work-item tracking across an owner's repositories. Operators
managing many repositories want a single command that reports, per repository, how many open items
there are and what they are — covering **both issues and pull requests**, each tagged by type.

This feature adds an `issues` subcommand backed by a new `IssuesRepoProcessor`. The processor
follows the established protocol-based processing architecture (like `InfoRepoProcessor` and
`SecurityRepoProcessor`) and produces, per repository:

- the number of open items (issues + pull requests)
- a list of the open items, each rendered as `#<number> [<type>] <description>`, where `<type>` is
  `issue` or `pr`
- optionally, the GitHub labels attached to each item (behind a `--labels` switch)

GitHub's issues endpoint returns pull requests alongside issues (a pull request carries a
`pull_request` field). This feature includes those pull requests and tags each item accordingly,
rather than excluding them.

## Glossary

- **Open_Item**: An item returned by `GET /repos/{owner}/{repo}/issues?state=open`.
- **Item_Type**: `"pr"` when the item carries a `pull_request` field, otherwise `"issue"`.
- **Open_Item_Count**: The number of Open_Items in a repository (issues + pull requests).
- **Item_Description**: The GitHub item `title`.
- **Item_Label**: A `name` drawn from an item's `labels` array. GitHub's own term is "label"; the
  CLI switch and output use that term. Distinct from Item_Type.
- **Labels_Enabled**: The rendering mode active when the user passes `--labels`.

## Requirements

### Requirement 1: Add an `issues` subcommand

**User Story:** As an operator, I want an `issues` subcommand, so that I can scan an owner's
repositories for open items the same way I scan for `info` and `security`.

#### Acceptance Criteria

1. THE CLI SHALL provide an `issues` subcommand under the existing Click group.
2. `ghbot --owner <name> issues` SHALL run `IssuesRepoProcessor` for each discovered repository.
3. THE `issues` subcommand SHALL accept the existing mutually-exclusive output-format flags
   `--plain`, `--table`, and `--json`, defaulting to `--plain`, using the same selection helper as
   `security`.
4. THE `issues` subcommand SHALL accept `--output <path>` to write the report to a file.
5. THE `issues` subcommand SHALL accept a `--labels` flag (default off) that enables GitHub-label
   rendering.
6. Selecting more than one of `--plain`, `--table`, `--json` SHALL raise a usage error.

### Requirement 2: Collect open issues and pull requests per repository

**User Story:** As an operator, I want the open issues and pull requests per repository, each tagged
by type, so that I can see the full open workload and tell issues from PRs.

#### Acceptance Criteria

1. THE `IssuesRepoProcessor` SHALL fetch open items via the existing GitHub API wrapper path and
   SHALL NOT make raw HTTP calls.
2. THE fetch SHALL request only open items (`state=open`).
3. THE processor SHALL include pull requests as well as issues (it SHALL NOT exclude items carrying
   a `pull_request` field).
4. THE processor SHALL tag each item with an `Item_Type` of `"pr"` when it carries a `pull_request`
   field, otherwise `"issue"`.
5. THE processor SHALL store the total count under `open_item_count`.
6. IF the endpoint returns 403 or 404, THEN `open_item_count` SHALL be `None` and no processor
   error SHALL be recorded.
7. IF the endpoint raises a non-fatal `GitHubApiError`, THEN `open_item_count` SHALL be `None`, an
   error SHALL be recorded, and the result status SHALL become `"partial"`.
8. Fatal rate-limit errors SHALL be re-raised following the existing processor error policy.

### Requirement 3: Collect the open-item list

**User Story:** As an operator, I want the actual open items listed with their type, so that I can
see what is outstanding, not just how many.

#### Acceptance Criteria

1. THE processor SHALL store the open items under `open_items` as an ordered list.
2. EACH stored record SHALL retain its `number`, its `title` (Item_Description), its `type`
   (`"issue"` or `"pr"`), and its labels as a list of label names.
3. THE list SHALL preserve GitHub's returned ordering and SHALL include both issues and pull
   requests.
4. IF the endpoint is unavailable (403/404) or fails with a non-fatal `GitHubApiError`, THEN
   `open_items` SHALL be `None`, mirroring `open_item_count`.
5. Labels SHALL always be collected into the stored records regardless of the `--labels` flag; the
   flag governs rendering only (Requirement 5). `type` is always present.

### Requirement 4: Render the report in plain, table, and JSON formats

**User Story:** As an operator, I want the open-item report in plain, table, and JSON output, with
issues and pull requests distinguished, so that human and automated consumers receive the same
signal.

#### Acceptance Criteria

1. THE report SHALL include a summary block reporting repositories scanned, repositories with open
   items, total open **issues**, and total open **pull requests** across all repositories.
2. THE open-issue and open-PR totals SHALL be `None`-aware: they SHALL sum only repositories whose
   items are available, and SHALL display as `"N/A"` in text output when every repository returned
   `None`.
3. THE plain report SHALL, for each repository with at least one open item, print a repository
   header and one line per item formatted `#<number> [<type>] <description>`.
4. THE table report SHALL render one row per open item with columns `Repository`, `#`, `Type`, and
   `Description`, preceded by the summary block.
5. THE JSON report SHALL include the summary and a `repositories` array; EACH repository object
   SHALL include `owner`, `repo`, `repository`, `open_item_count`, and an `items` array of objects
   carrying `number`, `title`, and `type`.
6. THE plain and table reports SHALL omit repositories that have no open items (count `0` or
   `None`); THE JSON report SHALL include every scanned repository.
7. Text reports SHALL display a `None` count as `"N/A"`; JSON SHALL preserve `open_item_count` as
   `null`.

### Requirement 5: Render labels only when `--labels` is enabled

**User Story:** As an operator, I want GitHub labels included on demand, so that output stays compact
by default but can show label context when I ask for it.

#### Acceptance Criteria

1. WHEN `--labels` is NOT passed, THE report SHALL NOT render any label data: plain lines end after
   the description, the table SHALL NOT include a `Labels` column, and JSON item objects SHALL NOT
   include a `labels` field.
2. WHEN `--labels` IS passed, THE plain report SHALL append each label to its item line with a `+`
   prefix, e.g. `#12 [pr] Fix the login redirect +bug +urgent`.
3. WHEN `--labels` IS passed, THE table report SHALL include a trailing `Labels` column rendering
   each item's labels as a comma-separated list.
4. WHEN `--labels` IS passed, THE JSON item objects SHALL include a `labels` field as a JSON array
   of label-name strings.
5. An item with no labels SHALL render as an empty suffix (plain), an empty column (table), and an
   empty array (JSON) when `--labels` is enabled.
6. The `type` tag is independent of `--labels`: `type` is always shown; only GitHub labels are
   gated by the flag.

## Non-Functional Requirements

- No new dependencies.
- `IssuesRepoProcessor` SHALL live in `src/ghbot/processor.py` alongside the existing processors.
- Report rendering SHALL live in `src/ghbot/report.py`.
- All GitHub API access SHALL go through `github_api_call`; URL construction SHALL use `url_vars`.
- All Python commands SHALL be run through `uv run`.
- Existing `info` and `security` behavior and existing output controls SHALL be unchanged.
