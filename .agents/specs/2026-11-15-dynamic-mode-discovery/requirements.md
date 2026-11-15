# Requirements Document: dynamic mode discovery

## Introduction

The shell application currently names processors and report functions directly in its command
runner. As reportable modes move into `ghbot.modes`, their declarations should become the source
of truth for discovery, command registration, mode-specific options, and future combined scans.
This removes mode-specific wiring from the shell application while retaining the existing trusted,
built-in package boundary.

## Glossary

- **mode definition**: A concrete class or object in `ghbot.modes` that satisfies the runtime
  mode protocol and describes one scanner operation.
- **discovery**: Enumerating built-in `ghbot.modes` modules and loading their valid mode
  definitions.
- **standalone mode**: A discovered mode invoked as its own CLI operation.
- **combinable mode**: A discovered, reportable mode that may be selected for a combined scan.
- **combo**: The generic combined-scan operation that coordinates selected combinable modes.
- **mode options**: CLI arguments declared by a mode definition and passed only to that mode.

## Requirements

### Requirement 1: Discover built-in mode definitions

**User Story:** As a maintainer, I want scanner modes discovered from their own package, so that
adding a mode does not require editing the shell application's mode registry.

#### Acceptance Criteria

1. THE application SHALL discover eligible mode definitions from modules in the built-in
   `ghbot.modes` package.
2. A discoverable mode definition SHALL satisfy a documented runtime protocol or concrete base
   class that supplies its canonical name, scanner construction, command metadata, and whether it
   is combinable.
3. THE discovery result SHALL use canonical mode names as unique identifiers and SHALL reject
   duplicate names with an actionable startup error.
4. IF a built-in candidate module cannot be imported or does not provide a valid mode definition,
   THEN THE application SHALL raise an actionable configuration/programming error rather than
   silently omit the mode.
5. THE shell application SHALL NOT import individual reportable mode implementations or maintain
   a hard-coded list of their names.
6. THE application SHALL load only modules from the installed `ghbot.modes` package and SHALL NOT
   load arbitrary filesystem paths, user configuration values, or third-party plugins.

### Requirement 2: Register standalone operations from discovered modes

**User Story:** As an operator, I want each discovered mode to expose its own operation and
arguments, so that adding a scanner also adds its CLI surface without runner changes.

#### Acceptance Criteria

1. FOR EACH discovered standalone mode, THE CLI SHALL register an operation using that mode's
   canonical name and help metadata.
2. EACH mode definition SHALL declare its own operation-specific arguments, and the CLI SHALL
   parse and pass them only to that mode's scanner/collection path.
3. THE shell runner SHALL construct a standalone scan through the discovered definition rather
   than directly naming a processor class or report function.
4. Existing `security`, `issues`, and `drift` operations SHALL retain their names, options,
   defaults, output-file behaviour, and rendered output contracts.
5. The existing `info` operation SHALL remain available as a non-reporting discovered mode and
   SHALL NOT be eligible for combination output.

### Requirement 3: Select discovered modes for combined scans

**User Story:** As an operator, I want a combined scan to select several discovered modes or omit
unwanted ones, so that one scan can be tailored without changing application code.

#### Acceptance Criteria

1. THE combo operation SHALL obtain its default mode set from all discovered combinable modes in
   deterministic canonical-name order.
2. THE combo operation SHALL support selecting multiple discovered combinable modes explicitly.
3. THE combo operation SHALL support excluding a discovered combinable mode from its default
   selection.
4. IF a selected or excluded mode name is unknown, non-combinable, or would leave no selected
   modes, THEN THE CLI SHALL reject the invocation with an actionable usage error.
5. THE combo operation SHALL NOT include itself or the non-reporting `info` mode in its selection.
6. The combined output SHALL compose the selected modes in the requested selection order, or in
   canonical-name order when no explicit selection is supplied.

### Requirement 4: Run discovered modes through shared scanning

**User Story:** As a maintainer, I want discovered scanners to use the same repository scan and
execution policy, so that extensibility does not weaken existing behaviour.

#### Acceptance Criteria

1. A standalone discovered mode SHALL use the existing authentication, repository discovery,
   archive filtering, owner-type propagation, monitor, TaskPool, and fatal-error policy.
2. A combo operation SHALL discover each repository once and construct every selected mode's
   scanner with the same owner, repository, API client, monitor context, owner type, and that
   mode's parsed options.
3. IF one selected mode yields a partial repository result, THEN the combination SHALL retain
   results from the other selected modes for that repository.
4. THE combination SHALL use each selected mode collection's existing document/render interface
   so JSON embeds mode documents directly and human output retains mode-owned sections.
5. The refactor SHALL NOT add GitHub API calls beyond those made by the selected scanners.

## Non-Functional Requirements

- Depend on the completed `report-style-handlers` collection-report interfaces and the `mode-cli-ownership` command boundary.
- Use runtime-checkable protocols or a concrete base class; do not add dependencies or a general
  third-party plugin mechanism.
- Preserve async TaskPool concurrency and all existing API error policies.
- Add focused unit tests for discovery, duplicate/invalid definitions, dynamic operation
  registration, option routing, combo selection/exclusion, deterministic composition, shared
  scanning, partial-result isolation, and unchanged standalone compatibility.
- Run verification through `uv run` and preserve public CLI documentation.
