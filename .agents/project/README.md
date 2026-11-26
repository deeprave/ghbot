# Project Overlay

This directory contains the authoritative, versioned facts and conventions for this repository. It
is the companion to the portable Specle policies: policies define how work proceeds, while this
overlay defines what is true for ghbot.

Read only the documents relevant to the change. Keep these documents factual, concise, and current
with the codebase. Do not put per-change requirements here; those belong in `.specle/changes/<slug>/`.

| Document | Purpose |
| --- | --- |
| `product.md` | Product intent, users, and supported behaviour. |
| `tech.md` | Runtime, tools, architecture, and project-wide implementation conventions. |
| `testing.md` | Test locations, framework conventions, and required quality gates. |
| `language.md` | Human language, spelling locale, and accepted terminology exceptions. |
| `security.md` | Authentication, secrets, input, and sensitive-code requirements. |
| `logging.md` | Logging formats, destinations, and sensitive-data requirements. |
| `api-standards.md` | GitHub API client, URL, pagination, and error-handling conventions. |
| `review.md` | Review-finding presentation and decision policy. |
| `delivery.md` | Branch, pull-request, check, and merge conventions. |
| `automation.md` | Workflow progression mode and mandatory stops. |
| `tracking.md` | Configured issue tracker and identifier/link conventions. |

Use the `onboard` skill to establish or refresh this overlay in another repository.
