# Technical Design: dynamic mode discovery

## Overview

Replace the static `BUILTIN_COMMANDS` tuple with discovery of trusted, built-in mode modules.
Each mode exports one `MODE` definition that owns its canonical name, Click command, processor
factory, and combinability. The CLI registers the discovered commands, while the existing runner
continues to execute reportable and non-reporting modes unchanged.

This refactor does not implement the `combo` command or alter the scan fan-out model. It exposes
the ordered combinable definitions that the separate `combo-reports` change will consume.

## Architecture

```text
ghbot.__main__.cli
    |
    +-- discover_modes() ----------------------------+
    |                                                 |
    |                                             ghbot.modes package
    |                                                 |
    |                               public built-in modules only
    |                                 |       |       |       |
    |                            security issues  drift    info
    |                                 |       |       |       |
    |                               MODE    MODE    MODE    MODE
    |                                                 |
    +-- cli.add_command(mode.command) <--------------+

standalone command
    |
    +-- reportable mode -> run_mode(cfg, MODE, options) -> collection.render(...)
    |
    +-- non-reporting info -> run_processor(cfg, InfoRepoProcessor)

future combo-reports -> combinable_modes(discover_modes())
```

### Mode contract

Add a runtime-checkable protocol in `ghbot.modes` (or a private sibling module) for the shared
discovery boundary. A definition must expose:

- `name: str` — the unique, canonical mode identifier;
- `command: click.Command` — the complete standalone Click command;
- `combinable: bool` — whether a future combined scan may select it; and
- `new_processor(...)` — the processor construction path consumed by the runner.

Reportable definitions retain `new_collection(options)`, which `run_mode` already consumes. The
protocol must not require a collection from the non-reporting `info` mode.

Existing `SecurityMode`, `IssuesMode`, and `DriftMode` remain small frozen definitions. Their
modules attach their command to the definition after the decorated Click function has been
created. A new `InfoMode` definition and its Click command move the current shell-owned `info`
behaviour into `ghbot.modes.info`; it is `combinable=False` and invokes the existing
`run_processor` path.

## Discovery and registration

`discover_modes()` will enumerate module names from the installed `ghbot.modes` package using
package metadata (`pkgutil.iter_modules` with the package path). It will:

1. consider only public, non-package module names, so support modules remain private;
2. import each candidate with `importlib.import_module` under the package namespace;
3. read exactly its `MODE` definition and validate the common mode protocol, a non-empty canonical
   name, and a Click command whose registered command name matches that canonical name;
4. reject duplicate canonical names and import or validation failures with an actionable
   `ModeDiscoveryError`; and
5. return the definitions sorted by canonical name.

The candidate namespace is fixed to the installed package path. No command-line value,
configuration value, arbitrary path, or entry-point plugin controls imports.

`__main__` will import only the discovery API and register every discovered command during module
initialisation. It will no longer import `InfoRepoProcessor`, `run_processor`, individual mode
commands, or `BUILTIN_COMMANDS`.

`combinable_modes()` will be a small discovery helper (or a documented filter over its result)
that returns only definitions with `combinable=True`, retaining discovery's canonical-name order.
It is an API for the later combo implementation; it registers nothing and causes no scans.

## API and data

```python
@runtime_checkable
class ModeDefinition(Protocol):
    name: str
    command: click.Command
    combinable: bool

    def new_processor(self, owner, repo, gh, monitor, options, *, owner_type): ...


def discover_modes() -> tuple[ModeDefinition, ...]: ...
def combinable_modes() -> tuple[ModeDefinition, ...]: ...
```

`ModeDiscoveryError` is an application programming/configuration error for a malformed trusted
builtin. It includes the module name and the violated rule. It is raised while constructing the
CLI, before authentication or repository discovery, rather than silently producing a partial
command set.

The mode definitions are immutable existing dataclasses where practical. No result-document or
report schema changes are needed: security, issues, and drift continue to use their collections,
and info remains non-reporting.

## Error handling

| Situation | Behaviour |
| --- | --- |
| Candidate import fails | Raise `ModeDiscoveryError` naming the module and original failure. |
| Candidate lacks `MODE` or fails the mode contract | Raise `ModeDiscoveryError` naming the module and invalid requirement. |
| Empty, invalid, or duplicate canonical name | Raise `ModeDiscoveryError`; never register an ambiguous command. |
| Click command name differs from mode name | Raise `ModeDiscoveryError`; the mode must own a consistent public identity. |
| Regular standalone scan failure | Unchanged: processor/runner API policy and `FatalError` propagation remain as today. |

Discovery does not catch or transform scanner failures, make GitHub calls, or alter TaskPool
concurrency.

## Report and CLI output

No rendered report changes are introduced. The registered public commands remain:

```text
ghbot info
ghbot security [--plain|--table|--json] [--output FILE]
ghbot issues [--plain|--table|--json] [--labels] [--output FILE]
ghbot drift [--plain|--table|--json] [--output FILE]
```

Their option parsing, defaults, report styles, file writing, and error behaviour continue to be
owned by their respective mode modules. `info` keeps its existing summary output and has no
report-style options.

## Test strategy

Use focused unit tests with patched package enumeration/imports where required:

1. Discover the real built-in definitions, assert canonical ordering and the four command names.
2. Assert `combinable_modes()` returns security, issues, and drift only, in canonical order.
3. Exercise invalid candidates: import failure, missing `MODE`, invalid definition, duplicate name,
   empty name, and mismatched Click command name; each must fail with useful context.
4. Invoke the top-level CLI to confirm dynamic registration retains each existing command and
   `info` works through its moved mode command.
5. Retain and run the existing standalone command/runner tests to demonstrate that options,
   rendering, owner-type propagation, TaskPool behaviour, and fatal-error handling have not
   changed.

Run all project quality gates through `uv run` after implementation:

```bash
uv run pytest -v -Werror -Walways
uv run ruff check
uv run ty check src/
uv run ruff format --check
```
