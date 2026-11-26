---
name: summary
specle_group: Reporting
description: >-
  Summarise completed Specle work for people.
usage: >-
  Use only after work is complete to create a human-facing report and copy-ready update; it does not publish externally.
---

# Summarise completed work

Produce `summary.md` as a concise human account of completed work. It is a communication artifact, not an AI verification record, delivery log, or external publication.

## Workflow

1. Read `.specle/current-change` when present, relevant policies, steering, applicable project guidance, and the target status record. Resolve the target in either active changes or archive. Select the local work item by default, including a selected archived completed item awaiting wrapup.
2. Apply the state guard before writing anything. The selected record must have `status: "complete"`. Otherwise, stop and identify the owning next workflow. Do not imply completion, run verification or review, or change lifecycle state.
3. Read the target's evidence in full:
   - For normal work, read its requirements, design, task plan, verification evidence, review outcome, and the relevant implementation.
   - For a bugfix or refactor, read its abbreviated `spec.md`, task plan, verification evidence, review outcome, and the relevant implementation.
   - For a spike, read `findings.json`, including recommendations, risks, and `outcome_change`.
4. Write `summary.md` inside the target's resolved active or archived directory. Make it stand on its own for people who have not followed the workflow. Use this concise structure, omitting sections that do not apply:

   ```md
   # Summary: <plain-language title>

   ## Summary

   ## Outcome

   ## What changed

   ## Key decisions and limits
   ```

   `Summary` comes first and is a short standalone, copy-ready paragraph suitable for a Jira comment, release note, or similar update. `Outcome` and `What changed` should explain only the user-meaningful result and delivered behaviour. `Key decisions and limits` is optional: include it only when a choice, deliberate exclusion, or lasting limitation matters to a reader.

   Do not include test counts, pass/fail results, CI or pull-request activity, commit references, routine verification, workflow mechanics, generic recommendations, or future-work boilerplate. Refer to evidence only when it explains a material result or limitation. For a spike, foreground the finding and recommendation in `Summary` and `Outcome`.
5. Preserve every context, lifecycle, tracker, and review record. Do not post or publish the summary. External publication remains an explicit `track` operation when a project has a configured destination and the user authorises it.

## Next

- Share or adapt the copy-ready update when the user asks.
- `track` — publish only with explicit authorisation and a configured destination.
