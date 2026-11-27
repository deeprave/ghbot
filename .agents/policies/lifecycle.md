---
specle_policy: true
---

# Spec Lifecycle

This document is the authoritative lifecycle policy for all changes. Each change's versioned
`.specle/changes/<name>/status.json` (or archived equivalent) records its durable instance state;
skills apply these transitions and must not replace them with local rules.

## States and next skill

| Status | Meaning | Next |
| --- | --- | --- |
| `defined` | Required work artifact exists but work has not started. | `activate <change-name>` for an unselected normal change or spike; otherwise its named abbreviated owner. |
| `estimated` | Complexity has been assessed. | `design` for M/L/XL; otherwise `tasks`. |
| `designed` | Technical design exists. | `tasks`. |
| `planned` | `tasks.md` exists but implementation has not started. | `build` for a selected normal change; the named `bugfix` or `refactor` for an unselected abbreviated change. |
| `spiking` | A time-boxed investigation is in progress. | `spike`. |
| `building` | Implementation changed or remains incomplete. | `build`, then `verify`. |
| `verified` | Every acceptance criterion and quality gate passed for the current implementation. | `review`. |
| `approved` | Local Specle review passed; external delivery is not necessarily complete. | `commit`. |
| `committed` | Delivery evidence was recorded and archival finalisation remains. | `complete`, or named `triage` for external feedback before archival finalisation. |
| `review-findings` | Review found actionable issues that need decisions. | `triage`. |
| `triaged` | Review decisions are recorded and routes are ready. | `resolve`. |
| `complete` | Archival finalisation was recorded on the existing delivery path, Resolve found no remaining review action, or a spike delivered its findings. | None. A named `complete <change-name>` may later inspect and synchronise the same merged delivery PR. |
| `cancelled` | Work intentionally ended without asserting delivery. | None. The archived record is immutable. |

## Ownership and transitions

| Skill | Required transition |
| --- | --- |
| `define` | Create an unselected normal change as `defined`, then report its concise summary; it never selects local work or commences planning. |
| `activate` | The sole writer of `.specle/current-change` except for complete's terminal removal of its matching archived selection after synchronisation and cancel's matching terminal removal. A selected archived complete record with an unconfirmed delivery PR blocks replacement; an archived cancelled record is terminal and replaceable. Select a named resumable normal change or `defined`/`spiking` spike in the local worktree. For a normal change, immediately invoke the first missing required estimate → design → tasks stage and set a fully prepared change to `planned` before invoking `build`; for a spike, invoke `spike`. |
| `spike` | Initialize an unselected `kind: "spike"` work item as `defined`. When invoked by `activate`, set it to `spiking` while conducting read-only research. On completion, record findings and optional stable outcome-change name, set verification and review to `not-applicable`, and mark it `complete`. |
| `estimate` | Mark the selected target `estimated`; selected normal work continues to design before tasks, while a named unselected normal estimate writes only its artifact and retains next `activate`. |
| `design` | Mark the selected change `designed`; a named unselected normal design writes only its artifact and retains next `activate`. |
| `tasks` | Require a design. Mark the selected change `planned`, set top-level task progress to `0/N`, and retain verification/review state unless the task plan revised implementation scope; named unselected normal tasks retain next `activate`. |
| `build` | For a planned normal change, first present a specification alignment summary and require explicit confirmation before implementation, including in decision-gated progression. Before or with the first implementation change, mark the active change `building`, set verification and review to `stale` if they previously held evidence, and update progress after every completed task. A named committed normal target may likewise be built in place without replacing the active issue. |
| `prepare` | Invoke `bugfix` or `refactor` without implementation, then set only its matching unselected record to `planned` with next `bugfix` or `refactor`. |
| `bugfix` / `refactor` | When invoked by `prepare`, create the abbreviated artifacts without execution. Otherwise, execute the abbreviated tasks and set only that record to `building` with next `verify`. When linked for concurrent delivery, create reciprocal parent/sidecar records atomically; the parent owns their joint delivery and archival finalisation. |
| `verify` | For the selected change, on a clean pass set verification to `pass` and status to `verified`; on failure set verification to `fail` and status to `building`. For a named committed normal target, update only that record: pass becomes `verified` with next `review`; failure remains `building` with next `build`. For a named unselected abbreviated change, update only that record: pass becomes `verified` with next `review`; failure remains `building` with next set to its owning workflow. A stale or prior selected-change review becomes `not-run` after a new successful verification. |
| `review` | Run only against a verified implementation. Record raw findings in `review-findings.json`. `APPROVE` sets review to `pass` and status to `approved`; `REQUEST_CHANGES` sets review to `findings` and status to `review-findings`. A named non-selected target is updated in place and never replaces the local selection. |
| `commit` | Runs the selected delivery model for an `approved` target. A normal parent discovers candidates only from its own concurrent-delivery relationships and requires a matching reciprocal ready bugfix/refactor record before including it. Every model records shared delivery evidence and `updated_at`, then moves every delivered member to `committed` for joint archive finalisation. |
| `complete` | For every `committed` delivery, generate its summary and archive its durable record through one recoverable finalisation delivery. It removes the completed parent and included sidecars from only matching explicit dependency arrays in other active records, preserving their lifecycle metadata, and includes those updates in the same finalisation commit. A normal parent jointly archives every valid reciprocal committed sidecar; it alone writes `status: "complete"`, `archived_at`, and immutable PR identity on the existing delivery PR. If that PR has already merged before archival delivery, recovery uses a `<delivery-branch>-complete` PR. Direct delivery archives without `delivery.completion`, pushes finalisation, and removes the matching selector. |
| `cancel` | Requires an explicit active target name and may transition any active non-terminal record to `cancelled`. It presents dependency, explicit reciprocal concurrent-delivery, and in-flight cleanup consequences; requires separate confirmation before removing direct dependencies or unlinking each explicit reciprocal partner; archives only the named target; and never performs user-owned cleanup without separate direction and authorisation. |
| `triage` | Consolidate review sources and record decisions without implementation. Active targets become `triaged`; archived records are immutable. |
| `resolve` | Dispatch accepted work without completing the origin. |
| `revise` | Reconcile accepted feedback into eligible active work; it rejects archived targets. |
| `changes` | List pending and dependency-context changes with their recorded next stages; completed archives are not pending solely because they retain completion-delivery identity. It never advances state. |
| `status` | Report the selected change's recorded state and next action, plus compact local worktree state; it never advances state. |

## Invalidation

Any source, test, task, or accepted-requirement change after a successful verification invalidates
that verification and any review based on it. The next build transition records both as `stale`.
A fresh successful verification resets the review to `not-run`; a fresh review and the applicable delivery operation are required before the change can become `complete`.

Every lifecycle owner that changes an active record's lifecycle status writes numeric Unix-second `updated_at` in the same update. Relationship-only metadata updates do not change `updated_at`. Completion archiving writes `archived_at` and preserves `updated_at`; cancellation writes both `updated_at` and `cancelled_at` with its terminal status. Archived records are immutable; a resumed complete operation only inspects delivery and synchronises the checkout.

## Concurrent sidecars

A bugfix or refactor can accompany selected normal work only through an explicit reciprocal relationship. The parent record names the sidecar with its `kind` and `delivery: "with-related-change"`; the sidecar names the parent with `type: "origin"` and the same delivery value. Creation updates both records as one recoverable operation. `commit` and `complete` discover candidates only from the parent declaration, then require exactly one matching reciprocal active record in the required lifecycle state. They never infer a sidecar from ordering, shared files, or a reverse scan. A valid sidecar shares the parent's delivery and immutable completion evidence, and has no separate completion lifecycle.

## Dependency visibility

Active dependency arrays list unresolved explicit prerequisites. Once `complete` records a delivery set's archival finalisation, it removes those names from matching active arrays in its finalisation commit. `cancel` may remove a cancelled name from matching active arrays only after explicit user confirmation. `changes` therefore lists terminal dependency context without treating archived work as pending.
