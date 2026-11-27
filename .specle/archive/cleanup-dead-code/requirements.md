# Requirements: Clean up dead code

## Introduction

Vulture is now configured as a pre-commit gate over ghbot production code. Its remaining findings
may represent dead implementation, but static analysis alone cannot prove that a public,
framework-provided, or reflective surface is safe to remove. This change must make that
distinction explicitly.

## Requirements

### Requirement 1: Assess every non-whitelisted finding

**User Story:** As a maintainer, I want dead-code reports investigated rather than blindly
suppressed or blindly removed.

#### Acceptance Criteria

1. THE change SHALL assess each Vulture finding not already identified as an intentional framework
   or protocol surface against production references, supported interfaces, and runtime discovery.
2. WHEN a finding has a supported or dynamic use, THE change SHALL retain it and add the narrowest
   maintainable Vulture whitelist entry with an explanatory comment.
3. WHEN a finding has no supported or runtime use, THE change SHALL remove it and any tests that
   exist solely for the removed implementation.

### Requirement 2: Remove confirmed unused implementation

**User Story:** As a maintainer, I want confirmed unused state and symbols removed so they do not
mislead readers or obscure future dead-code reports.

#### Acceptance Criteria

1. THE change SHALL assess the unreferenced `UnexpectedError` class, per-processor `_options`
   snapshots, mode `processor_type` fields, and runner-set GitHub-client attribute reported by
   Vulture.
2. THE change SHALL remove each assessed item only when evidence shows it has no supported,
   reflective, or runtime consumer.
3. THE change SHALL preserve externally observable CLI, report, configuration, and GitHub API
   behaviour.

### Requirement 3: Keep the dead-code gate effective

**User Story:** As a maintainer, I want future commits to reject credible dead code without a
noisy or toothless gate.

#### Acceptance Criteria

1. THE Vulture hook SHALL continue to scan the configured production paths at 60% minimum
   confidence.
2. THE configured whitelist and ignored names SHALL be limited to established Click, context
   manager, logging, and protocol-signature surfaces; they SHALL NOT suppress confirmed dead code.
3. `uv run pre-commit run vulture --all-files` SHALL pass after the change.

## Boundaries

- This change does not add Vulture to project dependencies or CI.
- It does not scan test-only control-flow fixtures as production dead-code findings.
- It does not introduce unrelated refactoring.
