# Release drift

Add `ghbot drift` to identify released repositories whose configured default branch is ahead of the latest stable GitHub release. Repositories with no release and repositories with zero newer commits are deliberately not listed.

For each repository, `DriftRepoProcessor` obtains `releases/latest`, then compares the release tag to the default branch and uses `ahead_by` as `commits_since_release`. GitHub's latest-release endpoint establishes the stable baseline, so drafts and prereleases are excluded. The processor uses the discovered default branch rather than assuming `main`.

For reportable repositories only, inspect `.github/workflows/*.yml` and `*.yaml` on the default branch. A filename, workflow name, or workflow content that signals PyPI publication (`pypi`, `pypa/gh-action-pypi-publish`, or `pypi.org`) sets `pypi_publishing_configured` to true. This is configuration detection only; do not query PyPI or claim that uploads succeeded.

Results include `latest_release_tag`, `latest_release_published_at`, `default_branch`, `commits_since_release`, and `pypi_publishing_configured`. Render plain, table, and JSON reports with a summary; per-repository output includes only reportable entries, sorted by repository. A PyPI-inspection failure is displayed as N/A/null but does not hide an otherwise reportable repository.

The processor follows `RepoProcessor`, uses the existing GitHub CLI token/client, `github_api_call`, URL variables, monitor events, and `TaskPool`. No-release is a successful skip. Rate limits propagate; other metadata/compare failures produce partial results and are not reported as zero drift.

Verification will cover stable-release eligibility, default-branch comparison, zero/nonzero filtering, PyPI workflow signals, error paths, each report format, CLI options, and the standard `uv run` pytest, Ruff, ty, and formatting gates.

Implemented: `DriftRepoProcessor`, the shared `report.py` renderer/printer, and the `ghbot drift` command. Focused processor, renderer, and CLI tests pass; full quality-gate results are recorded after verification.
