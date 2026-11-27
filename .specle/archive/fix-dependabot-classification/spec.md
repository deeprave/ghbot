# Fix Dependabot classification

## Problem

Issues mode checks GraphQL authors only for `dependabot[bot]`, but GitHub can return `dependabot`. Genuine Dependabot pull requests are therefore reported as other pull requests even though their displayed author identifies Dependabot.

## Outcome

Both issues and security modes will share one exact Dependabot identity rule that recognises GitHub's two observed login representations. Issues-mode counts, readiness, age, and listed Dependabot pull requests will agree with the underlying author identity.

## Scope

- Centralise Dependabot login classification.
- Apply it to issues and security pull-request metrics.
- Cover both accepted login forms, representative exact-match near misses, safe malformed REST-user handling, and the issues-mode reporting effects.
- Remove the adjacent pre-existing unused check-conclusion constant while touching the shared constants.

## Boundaries

- Preserve existing report contracts and merge-readiness handling.
- Do not broaden matching beyond the two exact recognised logins.

## Verification

Unit tests will prove both login forms classify as Dependabot, exact-match near misses and malformed REST users remain other without failing a scan, and a GraphQL `dependabot` pull request contributes to all affected issues-mode metrics.
