# Dynamic mode discovery

## Problem

The shell still registers built-in mode commands through a static `BUILTIN_COMMANDS` tuple.
Adding a new built-in mode therefore requires editing central application wiring despite the
completed mode-owned command and report refactors.

## Goal

Discover trusted built-in mode definitions from `ghbot.modes`. Each definition supplies its
canonical name, Click command, scanner construction, and combinability. The shell registers
standalone commands from those definitions, and a later combo feature can reuse the ordered
combinable set.

## Behaviour

- Discovery accepts only valid definitions in the installed `ghbot.modes` package; invalid,
  duplicate, or unimportable definitions fail clearly.
- `security`, `issues`, `drift`, and non-reporting `info` remain available through discovery with
  their current CLI and output contracts.
- Discovery exposes combinable reportable modes in canonical-name order and excludes `info`.
- The existing standalone runner, repository discovery, API use, concurrency, and error policy
  are preserved.

## Constraints

This is not a third-party plugin system and does not add API calls. It does not implement the
`combo` command, its selection/exclusion flags, combined rendering, or shared multi-mode scans;
those remain in the existing `combo-reports` specification.

## Verification

Test discovery validation, dynamic command registration, the migrated info command, deterministic
combinable ordering, and standalone compatibility.
