---
name: verify
description: >-
  Verify a spec implementation against its specification. Use when asked to "verify",
  "check against the spec", "confirm the implementation is complete", or before
  committing/closing a spec. Reads the current spec (.agents), checks every acceptance
  criterion (and any contract checks) against code and tests, runs the Python quality gates
  (pytest, ruff, ty), and reports PASS/FAIL with a gap list.
---

# Verify implementation against spec

Verify that the current spec implementation actually satisfies its specification — matching
every acceptance criterion, closing gaps, adhering to the steering standards, and passing the
Python quality gates.

Do **not** trust recorded status (checked `[x]` tasks, a spec-lite that says "passing"). Re-verify
against the working tree every time.

Run **every** command through `uv run` — never bare `pytest`/`ruff`/`ty`.

## Step 1 — Establish what to verify

1. Read `.agents/CONTEXT.json` (current spec + progress) and `.agents/.current` (the active spec path).
2. Read that spec's documents in full:
   - `requirements.md` (or `spec.md` on older specs) — the **acceptance criteria** (`SHALL` clauses)
     and, if present, a `## Contract` `checks[]` array. These are the conformance checklist.
   - `design.md` — intended architecture, API endpoints, result keys, error policy, test strategy.
   - `tasks.md` — the task list and completion marks.
   - `spec-lite.md` — the condensed intent.
3. Read the relevant steering docs so you can check adherence:
   `.agents/steering/{tech,api-standards,security,testing}.md`.

If the user names a different spec, verify that one instead of `.current`.

## Step 2 — Run the Python quality gates

Run all four and capture pass/fail plus any failing output:

```bash
uv run pytest -v -Werror -Walways     # tests; -Werror makes warnings (e.g. unawaited coroutines) hard failures
uv run ruff check                      # lint
uv run ty check src/                   # type check (NOT mypy)
uv run ruff format --check             # formatting (check-only; do not reformat during verify)
```

A failure in any gate means the implementation does **not** pass verification, regardless of the
acceptance-criteria review.

## Step 3 — Verify task completeness

- Confirm every task in `tasks.md` is marked `[x]`. List any that are not.
- For each completed task, confirm the claimed change actually exists in the code/tests (spot-check
  the files the task names). A checked box with no corresponding code is a gap, not a pass.

## Step 4 — Check every acceptance criterion

Go through each requirement's `SHALL` clauses (and each `Contract.checks[]` entry, if present) one
by one. For each, find the concrete evidence:

- the code that implements it (cite `file:line`), and
- the test that exercises it (cite the test name/file).

Mark each criterion **PASS / FAIL / PARTIAL**:
- **PASS** — implemented and covered by a test.
- **PARTIAL** — implemented but untested, or tested but the implementation diverges in a detail.
- **FAIL** — not implemented, or contradicted by the code.

Pay attention to the criteria the spec calls out as easy to get wrong, e.g. `None` vs `0`
semantics, `state=open` query params, pull-request exclusion, error-to-`partial`-status mapping,
and re-raising fatal rate-limit errors.

## Step 5 — Gaps, completeness, and spec adherence

- **Coverage gaps** — any spec requirement with no implementation and/or no test.
- **Scope creep** — implementation behavior that is *not* in the spec (flag it; it may need a spec
  update or removal).
- **Steering adherence** — confirm the implementation follows the repo standards:
  - All GitHub API calls go through `github_api_call`; no raw HTTP (`api-standards.md`, `security.md`).
  - URL parameters use `url_vars`, never f-strings/interpolation.
  - No new dependencies unless the spec's non-functional section allows them.
  - Async tests use `@pytest.mark.anyio` and `AsyncMock`; patched at the import site (`testing.md`).
  - Tokens/secrets never logged or put in error messages (`security.md`).

## Step 6 — Report

Produce a clear verification report:

- **Overall: PASS / FAIL** (FAIL if any gate fails, any acceptance criterion is FAIL, or any task is
  incomplete).
- **Quality gates** — one line each: pytest, ruff check, ty check, ruff format.
- **Tasks** — `X/Y` complete; list incomplete ones.
- **Acceptance criteria** — a table of criterion → PASS/PARTIAL/FAIL → evidence (`file:line` / test).
- **Gaps & adherence** — bulleted list of coverage gaps, scope creep, and any steering violations.
- **Next step** — if PASS, the spec is ready to commit; if FAIL, list the specific fixes needed
  before re-verifying (`/build` to fix, then re-run `/verify`).

Keep evidence concrete (cite files, lines, and test names). Do not report PASS on a criterion whose
only support is a checked task box or a claim in `spec-lite.md`.
