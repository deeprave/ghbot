# Security Requirements

## Authentication and secrets

- The default GitHub token comes from the `gh` CLI. `-e` / `--env` or `env = true` selects
  `GITHUB_API_TOKEN`; `--no-env` overrides configured environment-token use.
- Never store tokens, credentials, or `.env` files in the repository or configuration.
- Do not log token values or include them in error messages.
- Token access is lazy and cached by source. Authentication failures raise `AuthError` to the
  synchronous application boundary.

## API and input handling

- Use the GitHub client wrapper and `url_vars` rules in `api-standards.md`; do not add raw HTTP in
  application code.
- Treat permission-denied responses according to the documented API error policy without exposing
  private-resource details.
- Never execute or evaluate user-supplied owner or repository data.

## Sensitive code

- `src/ghbot/github/auth.py` — token acquisition and caching.
- `src/ghbot/github/client.py` — outbound API error translation.
- `src/ghbot/config.py` — configuration loading.
- `src/ghbot/log.py` — output redaction and request logging.
