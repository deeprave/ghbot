# Requirements Document: dynamic mode discovery

## Introduction

The completed mode-command and report-style refactors place each reportable mode in
`ghbot.modes`, but the shell still imports their Click commands through the static
`BUILTIN_COMMANDS` tuple. Adding a built-in mode therefore still needs central registration
wiring. Mode definitions should instead be the trusted source of truth for their identity,
standalone command, scanner construction, and whether a future combined scan may include them.

The separate `combo-reports` specification owns the combined command, its selection options, and
single-pass multi-mode execution. This change supplies its discovered-mode boundary only.

## Glossary

- **mode definition**: A concrete class or object in `ghbot.modes` that satisfies the runtime
  mode protocol and describes one scanner operation.
- **discovery**: Enumerating built-in `ghbot.modes` modules and loading their valid mode
  definitions.
- **standalone mode**: A discovered mode invoked as its own CLI operation.
- **combinable mode**: A discovered, reportable mode that may be selected for a combined scan.
- **mode options**: CLI arguments declared by a mode definition and passed only to that mode.

## Requirements

### Requirement 1: Discover built-in mode definitions

**User Story:** As a maintainer, I want scanner modes discovered from their own package, so that
adding a mode does not require editing the shell application's mode registry.

#### Acceptance Criteria

1. THE application SHALL discover eligible mode definitions from modules in the built-in
   `ghbot.modes` package.
2. A discoverable mode definition SHALL satisfy a documented runtime protocol or concrete base
   class that supplies its canonical name, Click command, scanner construction, and whether it is
   combinable.
3. THE discovery result SHALL use canonical mode names as unique identifiers and SHALL reject
   duplicate names with an actionable startup error.
4. IF a built-in candidate module cannot be imported or does not provide a valid mode definition,
   THEN THE application SHALL raise an actionable configuration/programming error rather than
   silently omit the mode.
5. THE shell application SHALL NOT import individual mode implementations or maintain
   a hard-coded list of their names.
6. THE application SHALL load only modules from the installed `ghbot.modes` package and SHALL NOT
   load arbitrary filesystem paths, user configuration values, or third-party plugins.

### Requirement 2: Register standalone operations from discovered modes

**User Story:** As an operator, I want each discovered mode to expose its own operation and
arguments, so that adding a scanner also adds its CLI surface without runner changes.

#### Acceptance Criteria

1. FOR EACH discovered standalone mode, THE CLI SHALL register its declared Click command.
2. EACH mode definition SHALL declare its own operation-specific arguments, and the CLI SHALL
   parse and pass them only to that mode's scanner/collection path.
3. THE shell runner SHALL construct a standalone scan through the discovered definition rather
   than directly naming a processor class or report function.
4. Existing `security`, `issues`, and `drift` operations SHALL retain their names, options,
   defaults, output-file behaviour, and rendered output contracts.
5. The existing `info` operation SHALL move into a non-reporting discovered mode, remain
   available with its existing behaviour, and SHALL NOT be eligible for combination output.

### Requirement 3: Expose combinable mode metadata

**User Story:** As a maintainer of a future combined scan, I want an ordered discovered set of
eligible modes, so that the combined command need not duplicate the mode registry.

#### Acceptance Criteria

1. Discovery SHALL expose all combinable discovered modes in deterministic canonical-name order.
2. The exposed combinable set SHALL exclude the non-reporting `info` mode.
3. The discovery API SHALL be reusable by the later `combo-reports` implementation without
   importing individual mode modules or maintaining another static mode list.
4. Every combinable mode definition SHALL expose `new_collection(options)` through the
   reportable-mode contract, and discovery SHALL reject a combinable definition that omits it.
5. This change SHALL NOT implement the `combo` command, mode selection/exclusion options,
   combined output, or multi-mode execution; those remain in `combo-reports`.

### Requirement 4: Run discovered modes through shared scanning

**User Story:** As a maintainer, I want discovered standalone scanners to retain the established
execution policy, so that making registration dynamic does not change scan behaviour.

#### Acceptance Criteria

1. A standalone discovered mode SHALL use the existing authentication, repository discovery,
   archive filtering, owner-type propagation, monitor, TaskPool, and fatal-error policy.
2. The refactor SHALL NOT add GitHub API calls or alter the current concurrency policy.
3. Existing reportable modes SHALL continue to use their mode-owned collections and renderers.

## Non-Functional Requirements

- Depend on the completed `report-style-handlers` collection-report interfaces and the `mode-cli-ownership` command boundary.
- Use runtime-checkable protocols or a concrete base class; do not add dependencies or a general
  third-party plugin mechanism.
- Preserve async TaskPool concurrency and all existing API error policies.
- Add focused unit tests for discovery, duplicate and invalid definitions, dynamic command
  registration, the migrated `info` command, deterministic combinable metadata and collection
  contract, and unchanged standalone compatibility.
- Run verification through `uv run` and preserve public CLI documentation.
