# Estimate: command refactor

## T-shirt size

S

## Breakdown

- New files: none expected.
- Modified files: approximately 4–5: root CLI dispatch, schema helper, command docstrings, README
  examples, and focused CLI tests.
- Estimated implementation tasks: 3–4.
- Key risk: Click normally resolves the first positional token as a subcommand, so the leading
  `--schema` form needs narrow pre-dispatch without making `--id` or `--list` global options.

## Confidence

High. Schema selection and output already live in an isolated module, while command registration
and help descriptions have direct, focused tests.

## Recommendation

Design the root dispatch boundary before tasks: it must consume only a leading `--schema`, pass the
remaining tokens to the existing schema selector, and leave all ordinary command parsing unchanged.

## Similar past work

- `list-schemas` introduced the current packaged-schema command and selector tests.
- `mode-cli-ownership` and `dynamic-mode-discovery` established the current root command
  registration and discovered-mode help surface.
