# Dispatch release workflow

Replace the GitHub-Release-triggered publish process with a manually dispatched workflow restricted to `main`. It must use the workflow run's exact `main` SHA and only proceed when the existing `Validate` workflow has completed successfully for that SHA. This reuses CI evidence rather than rerunning pytest, lint, formatting, type checks, or a separate test matrix.

The workflow reads `[project].version` from `pyproject.toml`, derives the tag `v<version>`, builds once, and publishes through PyPI trusted publishing. Only after publication succeeds does it create the GitHub Release at the same commit, with generated notes. The PyPI job retains OIDC-only permissions; release creation receives `contents: write`.

Verification will directly inspect the workflow structure and run the normal Python quality gates. The existing `Validate` workflow remains unchanged and continues to cover Python 3.13, 3.14, and 3.15.

Implemented: the release workflow is dispatch-only, rejects non-main refs, requires a successful `Validate` run for its exact SHA, reads the version from `pyproject.toml`, publishes via OIDC, and only then creates the matching GitHub Release. No workflow-specific Python test was added. The standard Python gates pass (287 tests, Ruff, Ty, and formatting).
