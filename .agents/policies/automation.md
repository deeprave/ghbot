---
specle_policy: true
---

# Workflow automation

Projects select progression in `.agents/project/automation.md`.

## Modes

- **Manual:** after every completed lifecycle skill, report the next step and wait.
- **decision-gated:** after a successful local transition, invoke the unambiguous next owning skill and preserve its full preflight, evidence, and state update.

Missing or unsupported project policy means manual mode.

## Mandatory stops

decision-gated progression stops for a material requirement or design decision, the pre-build specification alignment summary and explicit confirmation, a verification failure, a completed triage decision-and-route summary, or delivery authorisation. It never skips lifecycle skills and never authorises an external write. A successful review stops at `approved` to request commit authority; review findings enter triage, which stops after its final summary until explicit `resolve`.
