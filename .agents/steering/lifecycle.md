# Spec Lifecycle

This document is the authoritative lifecycle policy for all specs. `CONTEXT.json` records an
instance of this state; skills apply these transitions and must not replace them with local rules.

## States and next skill

| Status | Meaning | Next |
| --- | --- | --- |
| `defined` | Requirements exist. | `estimate` or `design`/`tasks` for small, understood work. |
| `estimated` | Complexity has been assessed. | `design` for M/L/XL; otherwise `tasks`. |
| `designed` | Technical design exists. | `tasks`. |
| `planned` | `tasks.md` exists but implementation has not started. | `build`. |
| `building` | Implementation changed or remains incomplete. | `build`, then `verify`. |
| `verified` | Every acceptance criterion and quality gate passed for the current implementation. | `review`. |
| `review-findings` | Review found actionable issues. | `build`, then `verify` and `review`. |
| `complete` | Current implementation passed verification and review. | None. |

## Ownership and transitions

| Skill | Required transition |
| --- | --- |
| `spec` | Initialize a new active spec as `defined`, with verification and review both `not-run`. |
| `estimate` | Mark the active target `estimated`; estimating a named queued spec does not change the active spec. |
| `design` | Mark the active spec `designed`. |
| `tasks` | Mark the active spec `planned`, set top-level task progress to `0/N`, and retain verification/review state unless the task plan revised implementation scope. |
| `build` | Before or with the first implementation change, mark the spec `building`, set verification and review to `stale` if they previously held evidence, and update progress after every completed task. |
| `verify` | On a clean pass, set verification to `pass` and status to `verified`. On any failure, set verification to `fail` and status to `building`. A stale or prior review becomes `not-run` after a new successful verification. |
| `review` | Run only against a verified implementation. On `APPROVE`, set review to `pass` and status to `complete`. On `REQUEST_CHANGES`, set review to `findings` and status to `review-findings`. |
| `revise` | When accepted requirement changes alter implementation scope, invalidate verification and review, then set the state to `defined`, `designed`, or `planned` according to the updated artifacts. |
| `context` | Reconcile recorded evidence with this policy; it does not manufacture a transition. |
| `status` | Report the recorded state and the next skill from this table; it never advances state. |

## Invalidation

Any source, test, task, or accepted-requirement change after a successful verification invalidates
that verification and any review based on it. The next build transition records both as `stale`.
A fresh successful verification resets the review to `not-run`; a fresh review is required before
the spec can become `complete`.

## Dependency visibility

`status` lists unfinished specs and also includes a completed spec when a pending spec explicitly
depends on it. This preserves a readable dependency graph without treating a completed dependency
as pending work.
