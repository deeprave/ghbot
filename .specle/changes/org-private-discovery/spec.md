# Organisation private repository discovery

Fix issue #38 by making shared repository discovery select its GitHub list endpoint from the owner account type. Resolve each configured owner through `GET /users/{owner}`. Use `/orgs/{owner}/repos?type=all` for `Organization`, and keep `/users/{owner}/repos?type=all` for `User`.

This covers token-accessible private organisation repositories for every current command because `info`, `issues`, `security`, and `drift` all consume `scan_repositories()`. Existing archive filtering, pagination, no-owner handling, and CLI interfaces remain unchanged.

Discovery records explicitly carry the resolved `owner_type` (`User`, `Organization`, or `None` for malformed metadata) alongside the raw repository metadata. The main loop passes it as the keyword-only `owner_type` processor argument. Built-in processors accept `owner_type=None` by default; custom `RepoProcessor` implementations must add the keyword-only argument.

All requests use `github_api_call()` and `url_vars`. A not-found/access-denied owner is skipped with a warning. Other API failures retry the complete metadata-plus-listing attempt once; rate-limit errors continue to propagate. Unknown account types warn and use the existing user endpoint as a compatibility fallback.

Tests will cover user versus organisation endpoint selection, forwarding a private organisation repository and owner type through to a processor, archive filtering, lookup/list retry and not-found policy, and URL variables. Verification will run the repository's four standard `uv run` quality gates.

Create a root `CHANGELOG.md`: document the released `0.10.0` drift command and an Unreleased breaking-change notice for the processor `owner_type` argument.

Implemented: shared discovery now classifies owners, lists organisations through the organisation endpoint, preserves private repositories and archive filtering, and yields `DiscoveredRepository` records. The main loop passes `owner_type` through the keyword-only processor argument. `CHANGELOG.md` documents drift in 0.10.0 and the Unreleased processor API change. All standard quality gates pass (300 tests, Ruff, Ty, and formatting).
