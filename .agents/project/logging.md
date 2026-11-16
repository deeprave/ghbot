# Logging Standards

## Format and destinations

- `src/ghbot/log.py` configures human-readable console output by default and structured JSON with
  `--log-json` for machine consumers.
- Log severity and verbosity are controlled through the CLI configuration. Monitoring events remain
  distinct from application logs so mode output can stay concise.
- Use the project logger acquired through `get_logger(__name__)`; do not add ad-hoc `print` calls
  for operational diagnostics.

## Sensitive data

- Never log GitHub tokens, credentials, or raw authentication headers.
- Do not expose private repository details through error messages when API access is denied.
- Treat API payloads as potentially sensitive: log only the minimum identifiers and diagnostics
  required to explain a recoverable failure.
