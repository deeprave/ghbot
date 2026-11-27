# Summary: Preserve GraphQL keyword calls

## Summary

ghbot again supports typed `GitHubClient.graphql(query=...)` calls, correcting a protocol
compatibility regression identified in late review feedback.

## Outcome

The issues processor now makes its GraphQL request using the public `query` keyword, matching the
client protocol available to processors and external typed consumers.

## What changed

- Restored `query` as the GraphQL protocol parameter name.
- Added focused coverage for the keyword request path.
- Recorded evidence-based dispositions for all late Sourcery findings from PR #68.

## Key decisions and limits

Only the supported keyword-call contract was changed. The remaining late-review suggestions were
declined because they were inapplicable, tautological, or concerned immutable historical records.
