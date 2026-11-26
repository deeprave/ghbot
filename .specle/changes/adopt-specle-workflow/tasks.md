# Tasks: Adopt Specle workflow

- [x] 1. Replace the portable workflow inventory and entrypoints (`.agents/skills/`, `.agents/policies/`, `.agents/AGENTS.md`, `AGENTS.md`)
  - [x] 1.1 Install the pinned Specle distribution and remove superseded legacy skills and steering.
  - [x] 1.2 Retain only ghbot-local instructions in the root entrypoint and direct change work to Specle.
- [x] 2. Migrate legacy specifications into the Specle change inventory (`.specle/changes/`, `.specle/current-change`)
  - [x] 2.1 Rename dated directories to slugs and reconcile `spec.md` names without losing detailed specifications.
  - [x] 2.2 Normalize internal references and create valid lifecycle status records from retained evidence.
- [x] 3. Refresh repository-owned workflow settings (`.agents/project/`, `.github/pull_request_template.md`)
  - [x] 3.1 Run onboarding and record confirmed language, review, delivery, and automation policy.
  - [x] 3.2 Align the pull-request template with the confirmed concise format.
- [x] 4. Validate the cutover without product changes (`.specle/`, `.agents/`, working tree)
  - [x] 4.1 Run Specle validation and migration integrity searches.
  - [x] 4.2 Confirm no source or test files changed and run whitespace validation.
