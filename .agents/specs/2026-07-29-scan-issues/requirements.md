# Requirements Document

## Introduction

ghbot can gather repository metadata (`info`) and surface security findings (`security`), but it
has no command dedicated to open issue tracking across an owner's repositories. Operators managing
many repositories want a single command that reports, per repository, how many issues are open and
what those issues are.

This feature adds a new `issues` subcommand backed by a new `IssuesRepoProcessor`. The processor
follows the established protocol-based processing architecture (like `InfoRepoProcessor` and
`SecurityRepoProcessor`) and produces, per repository:

- the number of open issues
- a list of the open issues, each rendered as `#<number> <description>`
- optionally, the labels attached to each issue (behind a `--labels` switch)

Pull requests are excluded. GitHub's issues endpoint returns pull requests as issues; this feature
reports genuine issues only, consistent with `InfoRepoProcessor`'s existing open-issue counting.

## Glossary

- **Open_Issue**: An item returned by `GET /repos/{owner}/{repo}/issues?state=open` that does NOT
  carry a `pull_request` field. Items carrying a `pull_request` field are pull requests and are
  excluded.
- **Open_Issue_Count**: The number of Open_Issues in a repository.
- **Issue_Description**: The GitHub issue `title`.
- **Issue_Label**: A `name` drawn from a GitHub issue's `labels` array. GitHub's own term is
  "label"; the CLI switch and output use that term.
- **Labels_Enabled**: The rendering mode active when the user passes `--labels` to the `issues`
  subcommand.

## Requirements

### Requirement 1: Add an `issues` subcommand

**User Story:** As an operator, I want an `issues` subcommand, so that I can scan an owner's
repositories for open issues the same way I scan for `info` and `security`.

#### Acceptance Criteria

1. THE CLI SHALL provide an `issues` subcommand under the existing Click group.
2. `ghbot --owner <name> issues` SHALL run `IssuesRepoProcessor` for each discovered repository.
3. THE `issues` subcommand SHALL accept the existing mutually-exclusive output-format flags
   `--plain`, `--table`, and `--json`, defaulting to `--plain`, using the same selection helper as
   `security`.
4. THE `issues` subcommand SHALL accept `--output <path>` to write the report to a file instead of
   stdout, matching the `security` subcommand.
5. THE `issues` subcommand SHALL accept a `--labels` flag (default off) that enables label
   rendering.
6. Selecting more than one of `--plain`, `--table`, `--json` SHALL raise a usage error.

### Requirement 2: Count open issues per repository

**User Story:** As an operator, I want the number of open issues per repository, so that I can see
issue load at a glance.

#### Acceptance Criteria

1. THE `IssuesRepoProcessor` SHALL fetch open issues for each scanned repository via the existing
   GitHub API wrapper path and SHALL NOT make raw HTTP calls.
2. THE fetch SHALL request only open issues (`state=open`).
3. THE processor SHALL exclude any item carrying a `pull_request` field from the count.
4. THE processor SHALL store the count under `open_issue_count`.
5. IF the issues endpoint returns 403 or 404, THEN `open_issue_count` SHALL be `None` and no
   processor error SHALL be recorded.
6. IF the issues endpoint raises a non-fatal `GitHubApiError`, THEN `open_issue_count` SHALL be
   `None`, an error SHALL be recorded, and the result status SHALL become `"partial"`.
7. Fatal rate-limit errors SHALL be re-raised following the existing processor error policy.

### Requirement 3: Collect the open-issue list

**User Story:** As an operator, I want the actual open issues listed, so that I can see what is
outstanding, not just how many.

#### Acceptance Criteria

1. THE processor SHALL store the open issues under `open_issues` as an ordered list.
2. EACH stored issue SHALL retain its issue `number`, its `title` (Issue_Description), and its
   labels as a list of label names.
3. THE list SHALL preserve GitHub's returned ordering.
4. THE list SHALL exclude pull requests, consistent with the count in Requirement 2.
5. IF the issues endpoint is unavailable (403/404) or fails with a non-fatal `GitHubApiError`, THEN
   `open_issues` SHALL be `None`, mirroring `open_issue_count`.
6. Labels SHALL always be collected into the stored issue records regardless of the `--labels`
   flag; the flag governs rendering only (Requirement 5).

### Requirement 4: Render the report in plain, table, and JSON formats

**User Story:** As an operator, I want the open-issue report in plain, table, and JSON output, so
that human and automated consumers receive the same signal.

#### Acceptance Criteria

1. THE report SHALL include a summary block reporting repositories scanned, repositories with open
   issues, and total open issues across all repositories.
2. THE total open-issue count SHALL be `None`-aware: it SHALL sum only non-`None` counts, and SHALL
   display as `"N/A"` in text output when every repository returned `None`.
3. THE plain report SHALL, for each repository with at least one open issue, print a repository
   header and one line per issue formatted `#<number> <description>`.
4. THE table report SHALL render one row per open issue with columns `Repository`, `#`, and
   `Description`, preceded by the summary block.
5. THE JSON report SHALL include the summary and a `repositories` array; EACH repository object
   SHALL include `owner`, `repo`, `repository`, `open_issue_count`, and an `issues` array of
   objects carrying `number` and `title`.
6. THE plain and table reports SHALL omit repositories that have no open issues (count `0` or
   `None`); THE JSON report SHALL include every scanned repository.
7. Text reports SHALL display a `None` open-issue count as `"N/A"`; JSON SHALL preserve it as
   `null`.

### Requirement 5: Render labels only when `--labels` is enabled

**User Story:** As an operator, I want issue labels included on demand, so that output stays compact
by default but can show label context when I ask for it.

#### Acceptance Criteria

1. WHEN `--labels` is NOT passed, THE report SHALL NOT render any label data in any format: plain
   lines SHALL be `#<number> <description>` with no label suffix, the table SHALL NOT include a
   `Labels` column, and JSON issue objects SHALL NOT include a `labels` field.
2. WHEN `--labels` IS passed, THE plain report SHALL append each label to its issue line with a `+`
   prefix, separated by spaces, e.g. `#12 Fix the login redirect +bug +urgent`.
3. WHEN `--labels` IS passed, THE table report SHALL include a trailing `Labels` column rendering
   each issue's labels as a comma-separated list.
4. WHEN `--labels` IS passed, THE JSON issue objects SHALL include a `labels` field as a JSON array
   of label-name strings.
5. An issue with no labels SHALL render as an empty suffix (plain), an empty column (table), and an
   empty array (JSON) when `--labels` is enabled.

## Non-Functional Requirements

- No new dependencies.
- `IssuesRepoProcessor` SHALL live in `src/ghbot/processor.py` alongside the existing processors.
- Report rendering SHALL live in `src/ghbot/report.py` alongside the security report rendering.
- All GitHub API access SHALL go through `github_api_call`.
- URL construction SHALL use `url_vars`, not f-strings.
- All Python commands SHALL be run through `uv run`.
- Existing `info` and `security` behavior and existing output controls SHALL be unchanged.
