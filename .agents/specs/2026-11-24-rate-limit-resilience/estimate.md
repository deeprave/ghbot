# Estimate: rate-limit resilience

## T-shirt size

**XL**

## Breakdown

- Modified areas: GitHub client/error translation, async execution, runner orchestration, command
  output, configuration, all report schemas, documentation, and tests.
- New components: rate-limit policy/gate and a partial-run outcome record.
- Estimated implementation tasks: 6–8.
- Key risks: correct concurrent admission after a limit signal; preserving whole-repository output;
  compatibility of versioned schema resources; and graceful cancellation without swallowing other
  fatal errors.

## Confidence

**High.** The prior rate-limit spike traced the current error and pool boundaries. Versioned schema
resources and explicit repository selection are now available.

## Recommendation

Create a technical design before tasks. Keep pacing and consumer-side resume/import tooling out of
scope.

## Similar past work

- `2026-11-17-rate-limit-resilience-spike` — traced the current failure paths and constraints.
- `2026-11-17-versioned-report-schemas` — established the additive minor-version policy and local
  schema registry.
- `2026-11-14-combo-reports` — established combined-report orchestration.
