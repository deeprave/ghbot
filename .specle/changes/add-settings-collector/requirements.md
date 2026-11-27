# Requirements: Settings collector

## Introduction

ghbot currently reports repository security, open work, and release drift, but does not provide a
focused inventory of repository configuration. Maintainers need to compare consequential settings
across repositories without exposing secret material or being overwhelmed by ordinary metadata.

## Glossary

- **Settings report**: The standalone report produced by the `settings` command for every scanned
  repository.
- **Curated general settings**: Repository settings with a broad operational, collaboration, or
  security effect, rather than presentation metadata or GitHub defaults of little diagnostic value.
- **Classic protection**: GitHub's branch-protection configuration for the repository's default
  branch, distinct from rulesets.
- **Ruleset bypass**: The presence of one or more actors that may bypass a ruleset; actor identity
  is not reported.

## Requirements

### Requirement 1: Provide a standalone settings report

**User Story:** As a maintainer, I want one command that inventories consequential repository
configuration across my selected repositories.

#### Acceptance Criteria

1. THE CLI SHALL provide a `settings` mode using the existing owner, explicit-repository,
   concurrency, authentication, partial-result, and exit-code behaviour.
2. THE mode SHALL render a detailed plain-text report by default and a structured JSON report with
   `--json`, and SHALL support `--output`.
3. THE mode SHALL NOT provide a table format or participate in `combo`.
4. THE JSON report SHALL have a packaged versioned schema available through `ghbot --schema`.

### Requirement 2: Report a curated general-settings inventory

**User Story:** As a maintainer, I want to see settings that materially affect repository use and
governance without a raw dump of GitHub metadata.

#### Acceptance Criteria

1. FOR each accessible repository, THE report SHALL include visibility, default branch, template
   status, merge strategies and related merge behaviour, branch deletion on merge, auto-merge and
   update-branch settings, fork policy, sign-off policy, and the enabled state of issues,
   discussions, projects, and wiki features.
2. THE report SHALL include available security-and-analysis feature states that affect Dependabot
   or security scanning.
3. THE report SHALL NOT include descriptive presentation metadata, timestamps, contributor data,
   topic lists, raw API payloads, or settings that are not consequential to repository governance
   or automation.

### Requirement 3: Report branch governance without exposing bypass identities

**User Story:** As a maintainer, I want to identify protection and ruleset posture without
revealing individual bypass actors.

#### Acceptance Criteria

1. WHEN the default branch has classic branch protection, THE report SHALL include a concise
   summary of its consequential protection settings; WHEN it has none, THE report SHALL record
   that absence distinctly from unavailable data.
2. THE report SHALL list applicable repository rulesets with their name, target, source,
   enforcement state, rule types, ref conditions, and whether bypass actors exist or that fact is
   unavailable to the caller.
3. THE report SHALL NOT include bypass-actor identities or identifiers.

### Requirement 4: List repository Actions configuration names safely

**User Story:** As a maintainer, I want to know which repository-level variables and secrets
exist without exposing their values.

#### Acceptance Criteria

1. THE report SHALL list repository-level Actions variable names and secret names, with no
   variable values, secret values, encryption material, or per-secret retrieval.
2. WHEN access to variables or secrets is unavailable, THE report SHALL retain the repository
   result and represent that metric as unavailable using the established reason metadata.

### Requirement 5: Preserve resilient reporting semantics

**User Story:** As a maintainer, I want one unavailable settings endpoint not to turn valid
configuration data into an empty or misleading report.

#### Acceptance Criteria

1. THE processor SHALL re-raise fatal and rate-limit errors.
2. WHEN an individual settings fetch has a recoverable GitHub API failure, THE processor SHALL
   record only the affected data as unavailable and return a partial result with a clear monitor
   event.
3. THE human-readable and JSON reports SHALL distinguish fetched-empty, unavailable, and failed
   repository data according to existing report conventions.

### Requirement 6: Preserve usable GraphQL partial data

**User Story:** As a maintainer, I want a mixed-access GraphQL query to retain the fields GitHub
returned when another requested field is unavailable.

#### Acceptance Criteria

1. WHEN GitHub returns GraphQL `data` together with one or more field errors, THE GitHub client
   layer SHALL expose a distinct partial-data condition retaining both the data and error details.
2. THE settings processor SHALL use a GraphQL query for compatible general settings, classic
   branch-protection rules, and rulesets, then retain accessible projected data while marking only
   affected settings sections unavailable.
3. THE settings processor SHALL use independent REST listing calls for Actions variables and
   secrets, whose APIs are not available through the required GraphQL query surface.
4. THE existing issues processor SHALL adopt the partial-data path where it can retain its
   accessible GraphQL result; no other existing scanner requires migration because no other
   scanner currently uses GraphQL.
5. THE client SHALL retain existing fatal, rate-limit, not-found, and forbidden error semantics;
   a GraphQL response without usable data SHALL remain an ordinary API failure.

## Boundaries

- This change reports repository-level configuration only; it excludes organisation settings,
  environment configuration, webhooks, deploy keys, collaborators, teams, and repository content.
- Ruleset bypasses are represented only as present, absent, or unavailable; actor identities are
  never reported.
- The report is an inventory, not a compliance engine and does not declare settings compliant or
  non-compliant with an external baseline.
- The report does not mutate GitHub settings.
