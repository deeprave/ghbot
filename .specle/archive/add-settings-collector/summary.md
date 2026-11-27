# Summary: Add repository settings collector

## Summary

ghbot now provides a standalone `settings` report for consequential repository configuration,
including branch governance, security features, and safe Actions inventory names.

## Outcome

Maintainers can compare settings across selected repositories in detailed plain text or structured
JSON without exposing secret values or bypass-actor identities.

## What changed

- Added the `settings` command and its packaged versioned JSON schema.
- Collected curated core settings through GraphQL and Actions variable and secret names through
  dedicated REST listings.
- Preserved usable GraphQL partial data, including readable rulesets when only bypass presence is
  unavailable.

## Key decisions and limits

Settings remains separate from table and combo reports. Ruleset bypass presence is shown only when
available; inaccessible bypass information is omitted rather than exposing identities or a
misleading value.
