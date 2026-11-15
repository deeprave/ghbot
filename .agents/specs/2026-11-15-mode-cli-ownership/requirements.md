# Requirements Document: mode CLI ownership

## Introduction

The report-mode refactor colocates processors, collections, and rendering, but `__main__.py` still declares each mode's Click arguments and reconstructs mode options. This leaves command behaviour split between the shell and the mode that owns the operation. Move standalone operation-specific CLI handling into mode units while retaining one shared application group and scan runner.

## Glossary

- **global CLI configuration**: options common to every operation, including configuration, logging, owner selection, concurrency, and authentication source selection.
- **mode command**: a Click command owned and exported by a reportable mode unit.
- **mode options**: command-specific arguments consumed only by one mode, such as output format, labels, and output destination.
- **shared scan runner**: the format-agnostic asynchronous path that authenticates, discovers repositories, constructs mode processors, and collects returned results.

## Requirements

### Requirement 1: Mode units own standalone command interfaces

**User Story:** As a maintainer, I want a mode to own its CLI arguments and invocation behaviour, so that adding or changing a mode does not spread its command details across the shell.

#### Acceptance Criteria

1. EACH reportable mode unit SHALL export its own Click command definition and help text.
2. EACH mode command SHALL declare and parse only its operation-specific arguments.
3. Security and drift mode commands SHALL own `--plain`, `--table`, `--json`, and `--output`.
4. The issues mode command SHALL own `--plain`, `--table`, `--json`, `--labels`, and `--output`.
5. EACH mode command SHALL convert its parsed arguments into that mode's option mapping, invoke the shared scan runner with its mode unit, render its collection using the selected style, and write the result through the shared writer.
6. Mode commands SHALL preserve the existing mutually-exclusive output-format error behaviour.

### Requirement 2: Keep the shell generic

**User Story:** As a maintainer, I want the application shell to manage common configuration but not mode-specific flags, so that mode commands remain cohesive units.

#### Acceptance Criteria

1. `__main__.py` SHALL retain the Click group and only global configuration options.
2. `__main__.py` SHALL register built-in mode commands through a package-level mode registration boundary and SHALL NOT declare report-mode-specific options or construct their option mappings.
3. The shared scan runner SHALL remain independent of CLI format, labels, and output-file logic.
4. The `info` command SHALL remain a non-reporting operation and retain its existing behaviour.
5. The refactor SHALL not implement dynamic discovery, plugins, or the `combo` operation; those remain the scope of the later dynamic-mode-discovery spec.

### Requirement 3: Preserve standalone contracts

**User Story:** As an operator, I want the CLI restructuring to be invisible to existing scripts.

#### Acceptance Criteria

1. Security, issues, and drift SHALL retain their command names, options, defaults, help text, output-file behaviour, format-conflict errors, and rendered output contracts.
2. Mode-specific options SHALL be routed only to the selected mode collection and processor path.
3. The refactor SHALL preserve authentication, repository discovery, archive filtering, owner-type propagation, monitor, TaskPool, and fatal-error behaviour.
4. The refactor SHALL not add dependencies or GitHub API calls.

## Non-Functional Requirements

- Keep synchronous Click command functions at the application boundary and use `asyncio.run` only to enter the existing shared async scan runner.
- Retain the static built-in mode boundary; dynamic registration is deferred.
- Add focused command tests for every retained flag, option routing, output forwarding, and global versus mode option separation.
- Run the full Python gates through `uv run`.
