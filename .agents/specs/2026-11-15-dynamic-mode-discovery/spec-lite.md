# Dynamic mode discovery

## Problem

The shell runner currently imports and wires individual modes, scanners, and report functions.
Adding a mode therefore requires editing central application code, and a future combo scan cannot
derive its contents from the modes themselves.

## Goal

Discover trusted built-in mode definitions from `ghbot.modes`. Each definition supplies its name,
scanner construction, CLI metadata/options, and combinability. The runner uses those definitions
for standalone operations and generic combined scans.

## Behaviour

- Discovery accepts only valid definitions in the installed `ghbot.modes` package; invalid,
  duplicate, or unimportable definitions fail clearly.
- `security`, `issues`, `drift`, and non-reporting `info` remain available through discovery with
  their current CLI and output contracts.
- Combo derives its default set from combinable modes, can select several or exclude defaults,
  rejects unknown/non-combinable/empty selections, and never includes itself or `info`.
- One combo repository discovery supplies the same API client, monitor, owner type, and
  mode-specific options to each selected scanner. Mode collection documents compose directly.

## Constraints

This follows the completed `report-style-handlers` interfaces. It is not a third-party plugin
system, does not add API calls, and preserves TaskPool/error behaviour.

## Verification

Test discovery validation, dynamic command/option routing, combo selection and exclusion, shared
scanning, partial-result isolation, composition ordering, and standalone regression behaviour.
