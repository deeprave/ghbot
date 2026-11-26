# Key learnings

- The existing pool owns both concurrency and rate-limit retry, but its fixed secondary-limit sleep affects only one worker.
- A post-abort report requires changing the runner/pool hand-off because `TaskPool.__aexit__()` currently raises before a collection is returned.
- Per-repository result collection already occurs only after the complete task succeeds, which is compatible with whole-repository partial reports.
- The implementation specification should follow versioned JSON schemas so incomplete-report fields are versioned intentionally.
