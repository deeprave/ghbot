# Project Overlay

This directory contains the authoritative, versioned facts and conventions for this repository. It
is the companion to the portable workflow in `.agents/steering/`: steering defines how work
proceeds, while this overlay defines what is true for ghbot.

Read only the documents relevant to the change. Keep these documents factual, concise, and current
with the codebase. Do not put per-change requirements here; those belong in `.agents/specs/`.

| Document | Purpose |
| --- | --- |
| `product.md` | Product intent, users, and supported behaviour. |
| `tech.md` | Runtime, tools, architecture, and project-wide implementation conventions. |
| `testing.md` | Test locations, framework conventions, and required quality gates. |
| `security.md` | Authentication, secrets, input, and sensitive-code requirements. |
| `logging.md` | Logging formats, destinations, and sensitive-data requirements. |
| `api-standards.md` | GitHub API client, URL, pagination, and error-handling conventions. |
| `tracking.md` | Configured issue tracker and identifier/link conventions. |

Use the `onboard` skill to establish or refresh this overlay in another repository.
