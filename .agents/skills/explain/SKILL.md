---
name: explain
specle_group: Reference
description: >-
  Explain a Specle change's purpose, requirements, approach, and current lifecycle state.
usage: >-
  Use with a named change when a user wants to understand its intent, implementation direction, kind, status, and next action without changing it.
---

# Explain a Specle change

Give a concise, evidence-based explanation of one Specle work item. This is a discussion and navigation skill: it never selects, activates, edits, implements, or delivers work.

## Workflow

1. Require an explicit stable change name unless `.specle/current-change` identifies an active selection. Resolve the name in `.specle/changes/` or `.specle/archive/`; never infer a target from directory ordering.
2. Read the target `status.json`, relevant `.agents/policies/lifecycle.md`, applicable steering and project guidance, and every available artifact that defines the target:
   - normal change — `requirements.md`, `spec.md`, and `design.md` when present;
   - bugfix or refactor — `spec.md` and `tasks.md` when present;
   - spike — `findings.json` and its `outcome_change` when present.
3. State only what the recorded artifacts support. Identify missing, incomplete, or conflicting artifacts as uncertainty; do not invent requirements, implementation details, dependencies, or delivery evidence.
4. Explain the change in a format suited to the question. Normally cover:
   - **Purpose** — the problem, motivation, and intended outcome;
   - **Requirements and scope** — important expected behaviour, boundaries, and constraints;
   - **Approach** — the documented design or likely workflow, including verification direction when known;
   - **State** — stable change name, kind, lifecycle status, active or archived location, relevant progress and delivery evidence;
   - **Next action** — the lifecycle action derived from recorded status and evidence, or state that no action remains for an archived complete or cancelled item.
5. Keep the explanation proportionate. Call out material trade-offs and open questions, but do not turn the response into a task plan unless the user asks.

## Boundaries

- Do not change `.specle/current-change`, `status.json`, artifacts, source files, or external systems.
- Do not activate a defined change or continue workflow progression.
- An archived complete or cancelled item is explainable by explicit name, even when no work is selected locally.
