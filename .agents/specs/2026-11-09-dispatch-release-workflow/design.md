# Technical Design: dispatch release workflow

## Overview

Replace the event-driven `Build and Publish` workflow with a manual release pipeline. A dispatch on `main` first confirms that the repository's existing `Validate` workflow completed successfully for the precise commit being released. It then builds once, publishes to PyPI using trusted publishing, and creates the corresponding GitHub Release only after publication succeeds.

## Architecture

```text
workflow_dispatch on refs/heads/main (GITHUB_SHA)
  -> validate-release
       -> gh run list --workflow Validate --branch main --commit GITHUB_SHA --status success
       -> extract project.version from pyproject.toml; expose version and tag
  -> publish (needs validate-release)
       -> checkout GITHUB_SHA
       -> uv build
       -> uv publish --trusted-publishing always
  -> create-release (needs publish)
       -> gh release create v<version> --target GITHUB_SHA --generate-notes
```

`workflow_dispatch` is defined without inputs. GitHub permits selecting a ref for dispatch, so the validation job explicitly rejects any ref other than `refs/heads/main`; this prevents a maintainer from releasing a passing feature-branch commit.

## Workflow data and permissions

The validation job reads the version directly from `pyproject.toml` using Python's standard-library `tomllib`, and publishes `version` and `tag` as job outputs. `tag` is `v${version}`. All jobs use `github.sha` as the immutable release commit; the publish job checks out this SHA and the release command supplies it as `--target`.

The validation command uses the authenticated `gh` CLI with `${{ github.token }}` to find a successful run of workflow `Validate` for `main` and the exact `github.sha`. Its absence fails the job. The job needs `actions: read` and `contents: read` only.

The publishing job has `id-token: write` only, preserving PyPI trusted publishing and avoiding long-lived registry credentials. The final job has `contents: write` only and uses `${{ github.token }}` to run `gh release create`; it cannot run if publication failed.

No release job runs pytest, Ruff, ty, format checking, or a Python matrix. `Validate` remains the sole test workflow and already has the complete required matrix. The release workflow uses `uv build` once to produce the artifact it publishes.

## Failure policy

| Failure | Outcome |
| --- | --- |
| Dispatch ref is not `main` | validation job fails; no build, publish, or release |
| No successful `Validate` run for the SHA | validation job fails; no build, publish, or release |
| Version cannot be read | validation job fails; no build, publish, or release |
| Build or PyPI trusted publication fails | publish job fails; GitHub Release job is not run |
| GitHub Release creation fails | PyPI package remains published; workflow visibly fails for manual follow-up |

## Verification strategy

- Inspect the workflow directly for its dispatch-only trigger, main-ref guard, exact-SHA `Validate` query, version extraction, job ordering, and narrow job permissions. Do not add Python tests for declarative workflow YAML.
- Run the existing Python quality gates: `uv run pytest -v -Werror -Walways`, `uv run ruff check`, `uv run ty check src/`, and `uv run ruff format --check`.
