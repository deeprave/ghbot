# Estimate: settings collector

## T-shirt size

XL

## Breakdown

- New production files: approximately 2–3: a `settings` mode with its processor/report and the
  packaged settings schema and registration resource.
- Modified production files: approximately 5–7: GraphQL client error translation, GitHub error
  types or result representation, issues GraphQL handling, mode/CLI discovery, schema registry,
  and documentation.
- Modified test files: approximately 7–10: client partial-data translation, settings projection,
  REST endpoint failures and redaction, issues partial GraphQL handling, report rendering, mode
  discovery, and schema validation.
- Estimated implementation tasks: 8–10.

## Key risks

- GitHub GraphQL can return usable `data` with field-level errors; the shared client needs an
  explicit partial-data path without weakening its fatal, rate-limit, not-found, forbidden, or
  no-data failure semantics.
- General settings, classic protection, and rulesets have mixed availability. The processor must
  preserve accessible fields while distinguishing absent configuration from inaccessible data.
- Ruleset bypasses and Actions secrets demand strict projection: report only bypass presence and
  names, never actor identities, values, or encryption material.
- The settings mode deliberately excludes table and combo support, so mode discovery must support
  a standalone report without accidentally making it combinable.

## Confidence

Medium-high. The existing GraphQL wrapper, issues-mode query, report conventions, and schema
registry provide clear integration points. The exact gidgethub partial-response shape and GitHub
field availability need to be established in design.

## Recommendation

Create a technical design before tasks. First define the shared partial-GraphQL contract, then the
settings query/projection and REST fallbacks; include the narrow migration of issues-mode GraphQL
handling in the same design.

## Similar past work

- `issues-ci-report` introduced the current GraphQL request and paginated pull-request metrics.
- `distinguish-permission-failures` established metric-level unavailable reasons and report
  visibility for inaccessible repository data.
- `versioned-report-schemas` and `list-schemas` established packaged schema registration and CLI
  distribution.
