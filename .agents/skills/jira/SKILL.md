---
name: jira
description: >-
  Integrate specs with Jira — pull requirements from issues, sync a spec up as a Jira issue, pull
  updates, or create subtasks. Use when asked to work with Jira issues. Requires an Atlassian MCP
  connection.
---

# Jira integration

Bridge specs and Jira. **Prerequisite:** an Atlassian MCP connection must be configured (search
available MCP tools). If MCP calls fail, tell the user to connect Atlassian MCP first.

## Capabilities

1. **Pull from Jira** (user provides issue keys): fetch issue details via MCP, extract summary,
   description, acceptance criteria, and comments; consolidate multiple issues into unified
   requirements; create `requirements.md`/`spec.md` with `Source: JIRA-XXX` attribution and links
   for traceability.
2. **Pull updates** (sync from Jira): read `jira-links.json` for linked keys, fetch latest state,
   and present a **CHANGE REPORT** (new/modified acceptance criteria, updated descriptions, new
   comments, status changes). **Never auto-update the spec** — get confirmation, then update the
   spec and regenerate `spec-lite.md`.
3. **Sync to Jira** (push): create or update a "Technical Specification" issue with the spec
   content, link to source stories, add a review-request comment, set labels.
4. **Create subtasks**: read `tasks.md`, create a Jira sub-task per task linked to the parent spec
   issue.

## Workflow

1. Read `.agents/CONTEXT.json` for the current spec state.
2. Identify the operation (pull / sync / pull-updates / subtasks).
3. Use Atlassian MCP for all Jira operations.
4. Record linked keys in `jira-links.json`; reflect the Jira links in `.agents/CONTEXT.json`.
5. Report what was created/updated.

## Important

- Always include Jira links and `Source: JIRA-XXX` attribution in the spec.
- On pull-updates, present changes and confirm before touching the spec.

## Next

- `/spec` or `/verify` after pulling requirements; `/tasks` before creating subtasks.
