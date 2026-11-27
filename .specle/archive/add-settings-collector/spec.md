# Add settings collector

## Problem

Repository settings that control merge behaviour, governance, security features, branch rules,
and Actions configuration cannot currently be compared through ghbot. Raw repository metadata is
too noisy and may expose information that does not belong in an operational inventory.

## Outcome

Add a standalone `settings` mode backed by `SettingsRepoProcessor`. It will provide a curated,
non-secret settings inventory in readable plain text and stable JSON.

## Scope

- A reusable GraphQL partial-data condition that preserves `data` and field errors together.
- Curated general repository and security-analysis settings obtained efficiently through GraphQL.
- Default-branch classic protection summary and applicable ruleset summaries through GraphQL.
- Ruleset bypass presence as true or false when available; omit the property when unavailable;
  never actor identity.
- Names of repository-level Actions variables and secrets only.
- Adoption of the partial-data path by the existing issues GraphQL scanner where it can preserve
  useful results.
- Packaged `ghbot://schemas/settings/1.0.json` schema and schema-registry support.

## Boundaries

- No table renderer and no `combo` participation.
- No values, encrypted data, actor identities, organisation settings, environment settings, or
  raw GitHub payloads.
- No compliance judgement or settings mutation.

## Assumptions

- The default branch is the appropriate branch for classic-protection reporting.
- Inherited/applicable rulesets are useful context when GitHub returns them; their source remains
  visible, while bypass actors remain anonymous and may be unavailable to a caller without
  sufficient access.

## Verification

Unit tests will cover GraphQL partial-data translation, accessible-field retention, curated
projection, protection/ruleset summaries, variable and secret redaction, endpoint-level partial
failures, the existing issues GraphQL path, report rendering, mode discovery, and JSON-schema
validation.
