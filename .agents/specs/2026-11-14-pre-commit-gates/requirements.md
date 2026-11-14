# Requirements Document

## Introduction

Repository commits currently depend on contributors remembering to run the project's quality checks. Add a versioned pre-commit configuration so standard file hygiene and the existing Python quality gates run before a commit is created.

## Glossary

- **pre-commit**: The repository-managed hook runner installed in the local Git checkout.
- **hygiene hooks**: Standard pre-commit checks for whitespace, file endings, malformed YAML/TOML, merge-conflict markers, and unexpectedly large added files.
- **project gates**: The repository's Ruff lint, Ruff format check, ty type check, and pytest commands.

## Requirements

### Requirement 1: Provide a reproducible hook configuration

**User Story:** As a contributor, I want a checked-in pre-commit configuration, so that every checkout uses the same commit checks.

#### Acceptance Criteria

1. THE repository SHALL contain `.pre-commit-config.yaml`.
2. THE configuration SHALL include the standard hygiene hooks for trailing whitespace, end-of-file fixing, YAML validation, TOML validation, merge-conflict detection, and added-file size limits.
3. THE configuration SHALL reject commits made directly on the `main` branch.
4. THE project SHALL declare `pre-commit` as a development dependency managed by `uv`.

### Requirement 2: Enforce project quality gates before commits

**User Story:** As a maintainer, I want commits blocked by the same core checks used locally and in CI, so that avoidable failures do not enter history.

#### Acceptance Criteria

1. THE configuration SHALL run `uv run ruff check` as a project-wide commit gate.
2. THE configuration SHALL run `uv run ruff format --check` as a project-wide commit gate.
3. THE configuration SHALL run `uv run ty check src/` as a project-wide commit gate.
4. THE configuration SHALL run `uv run pytest -Walways -Werror` as a project-wide commit gate.
5. THE four project gates SHALL not receive staged filenames, so each command retains its repository-wide scope.

### Requirement 3: Install and validate the hook

**User Story:** As a contributor, I want the hook active in this checkout and validated once, so that it protects subsequent commits immediately.

#### Acceptance Criteria

1. THE local Git checkout SHALL have the pre-commit hook installed through `uv run pre-commit install`.
2. WHEN run on `main`, THEN THE branch-protection hook SHALL reject the invocation and all other configured hooks SHALL pass over the repository's files.

## Non-Functional Requirements

- Use `uv` to add and run dependencies; do not use `pip`.
- Do not add new application dependencies or alter application runtime behaviour.
- Keep hook configuration declarative and use only the requested project gates plus standard hygiene hooks.
