# Release workflow review fixes

## Bug

The dispatch release workflow cannot check out its release SHA with OIDC-only permissions, can publish a version whose tag or release already exists, and invokes `gh release create` without a repository in a fresh job.

## Expected behaviour

- The publish job has the repository-read permission required for checkout.
- Validation rejects a version whose GitHub tag or release already exists before PyPI publication.
- Release creation explicitly identifies the repository.

## Fix approach

Grant `contents: read` to the publish job, perform the tag/release preflight with GitHub's API in the validation job, and pass `$GITHUB_REPOSITORY` to `gh release create`. Do not add tests for workflow YAML; inspect the workflow directly and run the established Python gates.
