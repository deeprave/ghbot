# Triage late Sourcery review

## Bug

Sourcery posted four review findings for the implementation delivered by PR #68 after its earlier
approval. The PR merged before those findings could be triaged, leaving potentially useful review
feedback without a mutable work item.

## Expected behaviour

The findings from the late Sourcery review are captured in a dedicated, mutable bugfix and
presented for explicit maintainer triage. Accepted findings are addressed in a successor delivery;
inapplicable findings are recorded as declined with their evidence.

## Actual behaviour

PR #68's archived change cannot accept further triage, and its four Sourcery findings have not yet
received dispositions.

## Root cause and fix approach

Sourcery's premature approval made the review appear settled before it posted its detailed
findings. This bugfix does not change the completion workflow. Triage accepted one finding:
`GitHubClient.graphql` must retain `query` as its protocol parameter name so typed consumers can
call it by keyword. Restore that name and add the narrow Vulture suppression required for the
public keyword contract. The remaining findings are declined with recorded evidence: the maintained
hook already disables filename passing, processor factories are direct static mappings, and the
archived design remains immutable.

## Regression evidence

All findings have recorded dispositions. Verify that a typed client can make the supported
`graphql(query=...)` call and that the repository's standard quality gates still pass. No test
should assert merely that a symbol is absent.
