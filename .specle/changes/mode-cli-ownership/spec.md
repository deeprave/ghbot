# Mode CLI ownership

## Problem

The shell declares report-mode flags and rebuilds mode options, even though modes now own their processors, collections, and rendering.

## Goal

Each reportable mode exports its own Click command and command-specific options. The shell keeps only global configuration and registers built-in mode commands through the modes package. The shared scan runner stays CLI-format-agnostic.

## Scope

- Security and drift own format/output flags.
- Issues additionally owns `--labels`.
- Commands translate their arguments into mode options, invoke the shared scan runner, render, and use the shared writer.
- Preserve names, defaults, output, help, errors, scan semantics, and `info`.

## Out of scope

Dynamic discovery, plugins, and `combo`; those remain in the dynamic-mode-discovery spec.

## Verification

Add CLI tests for all mode flags, option routing, output forwarding, and global-versus-mode option separation; run pytest, Ruff, Ty, and format checks through `uv run`.
