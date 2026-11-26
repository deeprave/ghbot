# Requirements Document

## Introduction

ghbot currently carries a repository-local workflow. The project should adopt the supported Specle workflow while preserving its project-specific guidance, existing change records, and delivery evidence. This is a workflow-only change.

## Glossary

- **Specle workflow**: The portable, Specle-managed skills and policies used for change-driven development.
- **project overlay**: ghbot-specific architecture, testing, security, tracking, and product guidance.
- **workflow state**: Existing change records and compact lifecycle evidence migrated into Specle records.
- **cutover**: Replacing the portable workflow layer while retaining project-owned guidance and state.

## Requirements

### Requirement 1: Preserve ghbot-owned workflow state

**User Story:** As a maintainer, I want to adopt Specle without losing work already planned or delivered in ghbot.

#### Acceptance Criteria

1. THE cutover SHALL preserve `.agents/project/` and compatibly transform legacy change records and lifecycle evidence into `.specle/changes/<slug>/` and `status.json`.
2. THE cutover SHALL retain the issue-item-metadata delivery record and the queued report-schema and combo-report specifications.
3. THE cutover SHALL NOT change ghbot product code or report behaviour.

### Requirement 2: Install the supported portable workflow

**User Story:** As a maintainer, I want the repository to use the maintained Specle workflow rather than a copied local variant.

#### Acceptance Criteria

1. THE repository SHALL use the supported Specle installation mechanism for its portable skills and policies.
2. THE installed workflow SHALL expose the skills needed to plan, implement, verify, review, and deliver a ghbot change.
3. THE repository root instructions SHALL direct agents to the installed workflow without duplicating portable policy.

### Requirement 3: Keep scope explicit

**User Story:** As a maintainer, I want the workflow migration to remain separate from product work.

#### Acceptance Criteria

1. THE migration SHALL remain a workflow-only change, with no new GitHub issue created for the local spec.
2. THE migration plan SHALL NOT presume an execution order relative to other specifications.

## Non-Functional Requirements

- Preserve GitHub Issues as the active requirements tracker and retain the project rule that implementing pull requests use `Closes #<number>` in their descriptions.
- Follow the existing delivery policy for branch, pull-request, verification, and review actions when the work is selected.
- Keep Markdown prose paragraphs on one logical line.
