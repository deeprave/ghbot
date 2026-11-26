---
specle_policy: true
---

# Testing Principles

## Approach

Use TDD: Red → Green → Refactor.

- Start each behaviour change with a focused failing test, then implement the smallest change that
  makes it pass.
- Keep each cycle narrow. Do not add speculative behaviour merely because nearby code might use it.
- Add a regression test for every fixed defect.

## Evidence

- Tests must demonstrate observable behaviour, including relevant error and boundary cases.
- Keep test setup isolated and deterministic. Restore process-wide state that a test changes.
- Use the project's documented test runner, quality gates, async conventions, and mocking patterns.
- Run the required project checks before declaring a change verified.

Project-specific test locations, frameworks, commands, fixtures, and coverage rules belong in
`.agents/project/testing.md` when the project has them.
