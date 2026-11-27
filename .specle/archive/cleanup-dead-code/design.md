# Design: Clean up dead code

## Overview

Remove the Vulture findings that have no production consumer, and retain the intentionally
dynamic/framework-facing surfaces in the narrow existing whitelist. This is a behaviour-preserving
internal cleanup.

## Finding disposition

| Finding | Disposition | Evidence |
| --- | --- | --- |
| `UnexpectedError` | Remove | It is imported only by its self-referential unit test. The archived change described a potential future caller but no current supported path raises or catches it. |
| Processor `_options` snapshots | Remove snapshots; retain constructor parameter | No processor reads the stored snapshot. The existing factory/runner constructor shape still receives `options`, so constructors explicitly discard it to preserve that integration boundary. |
| Mode `processor_type` fields | Remove fields and assertions | The discovered-mode protocol and validator require `new_processor`, not `processor_type`; runtime code uses `new_processor`. Only implementation-detail tests read the fields. |
| `gh._ghbot_skipped_explicit_ids` | Remove assignment | No repository code reads the client attribute; the live value is `TaskPool.skipped_explicit_ids`, which the runner consumes. |
| `RepoProcessor` | Retain and whitelist | It is a runtime-checkable structural protocol validated by processor tests and documents the processor boundary. |
| `LoggerWithTrace.trace` | Retain and whitelist | The registered custom logger class exposes the TRACE-level logging extension dynamically. |
| Click, async-context-manager, and protocol parameters | Rename safely-renamable names; retain only `url_vars` ignore | Only `url_vars` is keyword-only in the GitHub client protocol. The other unused names can be underscore-prefixed without altering a keyword contract. |

## Architecture

```text
mode discovery -> ModeDefinition.new_processor(options) -> processor constructor
                                      |                         |
                                      +-- contract retained       +-- discard unused options

runner -> TaskPool.skipped_explicit_ids -> explicit-result handling
       \-> remove unused GitHub-client attribute
```

The processor-constructor parameter remains for compatibility with the existing mode/runner
construction path, but no processor keeps a private copy of a value it does not use.

The Vulture configuration suppresses only `url_vars`, whose keyword-only name is part of the
GitHub-client protocol. Click callback, context-manager, classmethod, GraphQL positional, and
variadic keyword parameter names use underscore prefixes instead of global scanner suppression.

## API and data

No CLI, report, schema, GitHub request, or persisted data shape changes. Internal dataclass fields
that are not part of the discovered-mode protocol are removed. Processor constructors remain able
to receive `options` from the established factory path.

## Error handling

No error-handling paths change. Removing `UnexpectedError` does not affect runtime handling because
the class has no production raiser or catcher; existing `FatalError` and its in-use subclasses
remain unchanged.

## Report/output rendering

None. Report generation and output are unaffected.

## Test strategy

- Remove unit assertions whose only purpose is to exercise the removed exception or mode fields.
- Run the affected mode/error/runner tests to confirm factory and explicit-repository behaviour.
- Run `uv run pre-commit run vulture --all-files` to prove all remaining source findings are either
  removed or intentionally whitelisted.
- Confirm Vulture reports no finding after reducing `ignore_names` to the unavoidable keyword-only
  client parameter.
- Run the full project quality gates: pytest with warnings as errors, Ruff check, ty, and Ruff
  format check.
