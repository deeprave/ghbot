# Estimate: list schema names and IDs

## T-shirt size

S

## Breakdown

- New files: 0
- Modified files: approximately 3–4 (`ghbot.schemas`, schema CLI, focused CLI/registry tests, and README)
- Estimated implementation tasks: 2
- Key risks: retain the registry as the single source of names and IDs; reject selector conflicts
  before registry I/O.

## Confidence

High

## Recommendation

Skip design. Use the abbreviated `fix` workflow: reproduce `--list` rejection in a focused test,
add registry-backed enumeration and the CLI path, then confirm existing retrieval remains unchanged.

## Similar past work

`2026-11-23-add-schema-to-cli` added the same local command and selection validation. The current
fix extends that command without touching repository scanning or authentication paths.
