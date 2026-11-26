# Estimate: mode CLI ownership

## T-shirt size

M

## Breakdown

- New files: ~0.
- Modified files: ~6: the application shell, the modes package boundary, three reportable mode
  modules, and CLI tests.
- Estimated tasks: ~5.
- Key risks: preserve Click help and mutual-exclusion behaviour while moving decorators; avoid
  circular imports between the shell and mode commands; retain global-option handling and the
  existing async runner's owner-type, TaskPool, and fatal-error behaviour.

## Confidence

High. The completed `report-style-handlers` work already supplies the named `MODE` units and shared
scan runner that this change will connect to mode-owned commands.

## Recommendation

Design is recommended. The change crosses the application-to-mode command boundary and needs a
clear registration and dependency direction before implementation. It does not need splitting.

## Similar past work

- `report-style-handlers` moved processors and collection reports into the same mode
  modules while leaving the Click command definitions in `__main__.py`.
