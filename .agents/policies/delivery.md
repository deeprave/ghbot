---
specle_policy: true
---

# Delivery policy

Specle separates local implementation quality from the event that delivers work to a shared repository or its users. This document describes portable delivery models; `.agents/project/delivery.md` selects a model and records that project's conventions.

## Portable models

### Local-only Git

Git is local to the project. A successful local review makes work `approved`. The applicable `commit` operation records the local commit as the delivery event and moves the work to `committed`. `complete` then records completion and performs archival finalisation.

### Shared upstream, direct to the delivery branch

Git has a shared upstream, but work is committed directly to the configured delivery branch without peer review. A successful local review makes work `approved`. The applicable `commit` operation creates or updates the authorised shared-upstream commit, records that delivery event, and moves the work to `committed`. `complete` then records completion and performs archival finalisation.

### Shared upstream, branch and pull request

Git has a shared upstream and work is delivered through a branch and reviewable pull request or equivalent change request. A successful local review makes work `approved`. The `commit` operation creates or updates the approved branch delivery and records it as `committed`. The `complete` operation confirms the configured final event, normally merge, and prepares archival finalisation. When that archival work requires its own completion PR, `wrapup` merges the recorded completion PR and synchronises the delivery branch.

## Policy boundary

Projects record their selected model and confirmed local policy in `.agents/project/delivery.md`. That document may define another model and may cover delivery branch, branch naming, commit title and message conventions, required checks, secret scanning, pull-request format or templates, the final delivery event, and authority for agent-performed external writes.

Unknown policy remains explicitly unestablished. Skills must not infer it from the available client, repository host, branch name, or a user mentioning a generic workflow.

## Lifecycle meanings

- `approved` means the local Specle review passed. It is not evidence that shared delivery or peer review is finished.
- `committed` applies to every delivery model after its delivery event is recorded. It remains addressable for later external feedback.
- `complete` means the project's configured final delivery event has been confirmed and the archived record is terminal. An explicitly invoked `wrapup` may inspect and merge a recorded completion PR without changing that archival state. A spike is an exception: its recorded findings complete it without implementation delivery.

External writes require both project policy and explicit user authorisation. A skill may provide exact instructions when either is absent.
