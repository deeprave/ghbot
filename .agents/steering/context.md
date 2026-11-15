# Context State

`.agents/CONTEXT.json` is the compact, current instance state for spec work. It is not the source
of lifecycle policy: `.agents/steering/lifecycle.md` defines the permitted states and transitions.
Every skill that reads or writes context must follow both documents.

## Required shape

```json
{
  "$comment": "optional explanation",
  "current_spec": {
    "name": "YYYY-MM-DD-slug",
    "path": ".agents/specs/YYYY-MM-DD-slug",
    "status": "defined",
    "progress": {"tasks_completed": 0, "tasks_total": 0},
    "present_task": null,
    "verification": {
      "status": "not-run",
      "last_run": null,
      "gates": {}
    },
    "review": {
      "status": "not-run",
      "last_run": null,
      "findings": 0
    },
    "revision_note": "short current-state summary"
  },
  "recent_specs": [],
  "queued_specs": [],
  "python_checks": {},
  "commit_policy": {},
  "requirements_summary": {},
  "skills": {}
}
```

## Field rules

- `current_spec.name` and `path` identify the path in `.agents/.current`; keep them aligned.
- `progress` counts top-level implementation tasks unless the task format explicitly says
  otherwise. Nested checkbox counts are not substituted for this lifecycle progress field.
- `verification.status` is one of `not-run`, `stale`, `pass`, or `fail`. `gates` holds the most
  recent concrete gate results.
- `review.status` is one of `not-run`, `stale`, `pass`, or `findings`. `findings` is the number of
  actionable review findings from that pass.
- `recent_specs` is a compact historical record. Older records may omit `verification` and
  `review` details when that evidence was not retained.
- Each `queued_specs` record has `name`, `path`, `status`, and `next`; it may also include
  `depends_on`, a list of short spec slugs.
- Preserve project-wide `python_checks`, `commit_policy`, `requirements_summary`, and `skills`
  unless the relevant source changes.

## Update rules

- State must be valid JSON and concise; never paste full requirements or test output into it.
- Do not infer a lifecycle transition from checked task boxes alone. Record the transition only
  when the owning skill in `lifecycle.md` completes its work.
- When the active spec changes, retain the prior record in `recent_specs` if it is complete, or
  retain it in `queued_specs` if it is unfinished.
- `context` refreshes known evidence without inventing verification or review results.
