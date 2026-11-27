# Summary: Add a dead-code quality gate

## Summary

ghbot now checks production code for credible unused implementation before every commit and has
removed the unused state that established the gate identified.

## Outcome

Future changes receive early dead-code feedback without weakening ghbot's processor protocol,
TRACE logging capability, or GitHub client keyword contract.

## What changed

- Added Vulture's maintained pre-commit hook at a useful confidence threshold.
- Removed confirmed unused processor state, mode metadata, and an unconsumed error type.
- Kept a minimal whitelist for the shared processor protocol and TRACE logging extension.

## Key decisions and limits

Only the GitHub client's keyword-only `url_vars` parameter is globally ignored; other framework
and protocol parameters use underscore names instead.
