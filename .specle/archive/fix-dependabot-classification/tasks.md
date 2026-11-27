# Tasks: Fix Dependabot classification

- [x] 1. Define the shared Dependabot identity rule (`src/ghbot/processor.py`, `tests/unit/test_processor.py`)
  - [x] 1.1 Add failing tests for `dependabot`, `dependabot[bot]`, and non-Dependabot login values.
  - [x] 1.2 Implement the exact shared predicate without broad matching.
- [x] 2. Apply the shared classification to issues metrics (`src/ghbot/modes/issues.py`, `tests/unit/test_issues_processor.py`)
  - [x] 2.1 Add a GraphQL `dependabot` regression case covering open, CLEAN-ready, oldest-date, and listed-PR results.
  - [x] 2.2 Route issues-mode author classification through the shared predicate.
- [x] 3. Apply the shared classification to security metrics (`src/ghbot/modes/security.py`, `tests/unit/test_security_processor.py`)
  - [x] 3.1 Add a REST `dependabot` regression case.
  - [x] 3.2 Route security-mode author classification through the shared predicate.
- [x] 4. Prepare the point release (`pyproject.toml`, `CHANGELOG.md`)
  - [x] 4.1 Set the package version to 1.0.1 and document the user-facing classification correction.
- [x] 5. Correct security-test API wrapper patching (`tests/unit/test_security_processor.py`)
  - [x] 5.1 Replace every ineffective `ghbot.processor.github_api_call` patch with the security module import-site target.
  - [x] 5.2 Run the complete security-processor test module to confirm the isolated wrapper path remains covered.
- [x] 6. Harden identity boundaries and REST payload handling (`src/ghbot/processor.py`, `src/ghbot/modes/security.py`, `tests/unit/test_processor.py`, `tests/unit/test_security_processor.py`)
  - [x] 6.1 Treat null and non-mapping REST `user` payloads as non-Dependabot without failing the scan.
  - [x] 6.2 Cover representative prefix, suffix, case, whitespace, and empty-string near misses for the exact identity predicate.
  - [x] 6.3 Remove the pre-existing unused check-conclusion constant from the shared processor module.
