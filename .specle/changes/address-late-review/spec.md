# Address late PR #71 review

## Bug

Sourcery approved PR #71, then posted thirteen review findings after it merged. The archived
`add-settings-collector` change is immutable and cannot receive their dispositions.

## Expected behaviour

Every late finding is captured in a mutable successor bugfix, independently assessed, and presented
for explicit maintainer triage. The settings and issues reports must not describe unavailable
GraphQL data as real data, independent Actions data must survive a core-settings projection
failure, and the settings command must propagate incomplete-report exit codes. The settings
inventory must report bounded ruleset results honestly, include applicable inherited provenance,
and expose the agreed curated merge and security-analysis configuration. JSON output must be
deterministic. Rejected findings retain their evidence and rationale.
Recognised security product-gating responses must use canonical wording that says a feature is not
enabled for the repository, while retaining GitHub's raw response as structured metadata.

## Actual behaviour

The late review is available only in GitHub and an ignored local capture, with no mutable tracked
triage record.

## Root cause and fix approach

The approval preceded Sourcery's detailed review. This bugfix captures all thirteen claims as
untrusted external evidence. The accepted claims correct partial GraphQL error attribution,
contain projection failures, propagate established outcome handling, and extend the agreed
settings projection without making extra pagination requests. Error reasons are derived only from
the matching field errors; unmappable core errors make all core sections unavailable. Ruleset
output records connection truncation, applicable source identity, and unavailable bypass presence
without emitting null values. The pull-request metric group is unavailable when its author or
merge-state field is unavailable. The declined test-expansion suggestion remains recorded but is
not implemented. Recognised Code Security, secret-scanning, and Dependabot feature-gating errors
are translated only for user-facing diagnostics; the established `disabled` availability reason
and raw GitHub message remain intact for compatibility and diagnosis.

## Regression evidence

Every captured item has a recorded disposition. Focused behavioural tests cover the corrected
partial-data, projection-resilience, report-contract, and deterministic-output paths; the project
quality gates validate the successor delivery. Focused coverage confirms canonical feature-gating
diagnostics and preserved raw metadata.
Both GitHub Code Security response variants are recognised, and canonical feature-gating
diagnostics are emitted even where the repository has no other security activity.
