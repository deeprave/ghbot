---
specle_policy: true
---

# Review Severity

Use P1 through P6 for review findings, in priority order:

- **P1 — critical:** a severe failure or security issue.
- **P2 — high:** likely to cause issues, including a less severe security issue.
- **P3 — medium:** correctness, possible functionality, or user-experience issue.
- **P4 — low:** not serious, but should be corrected.
- **P5 — optional:** documentation change or inapplicable comment.
- **P6 — note only:** inconsistency or suggestion.

Assign a severity to each actionable review finding. Project guidance determines how findings are presented and whether they may be addressed automatically.

## Default presentation

### One at a time

Present each finding in this order:

```text
<item>/<total-items> <severity> <description>
Source
Analysis
Recommendation
```

The user may accept, decline, skip, defer, or discuss the finding.

### Batch

Present findings in severity order. Use the same item heading and identify the source and recommendation for every item, but keep analysis concise until the user selects or discusses a finding.

### Automatic

Apply findings only according to the project's automatic-decision policy. When a finding requires a user decision or presents an open question, present it using the one-at-a-time format rather than applying it automatically.
