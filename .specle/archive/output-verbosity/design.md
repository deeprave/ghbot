# Design Document: output-verbosity

## Overview

This feature corrects log-level assignments across three existing files — `processor.py`,
`__main__.py`, and `log.py` — so that console output at each verbosity level contains only the
messages an operator actually needs. No new modules are introduced.

The changes fall into four groups:

1. **`LoggingMonitor.send_event`** — add `"debug"` to the severity→level map so that
   `FeedbackEvent` objects with `severity="debug"` are routed to `logging.DEBUG`.
2. **`InfoRepoProcessor` fetch methods** — change empty-state events (`"warning"` → `"debug"`)
   and per-step progress events (`"info"` → `"debug"`); change the `run()` completion event
   (`"info"` → `"debug"`).
3. **`configure()` in `log.py`** — accept a `requests: bool` parameter and, when `False`,
   attach a `logging.CRITICAL + 1` level filter to the `ghbot.requests` logger so it is
   silenced regardless of the console handler level.
4. **`main()` in `__main__.py`** — add a `--requests` CLI flag and thread it through to
   `configure()`.

---

## Architecture

All changes are confined to existing files. The call flow is unchanged:

```
main() [__main__.py]
  └─ configure(console_level, log_file, log_level, json_format, requests) [log.py]
  └─ asyncio.run(_main(cfg))
       └─ InfoRepoProcessor.run() [processor.py]
            └─ self._monitor.send_event(FeedbackEvent(...))
                 └─ LoggingMonitor.send_event() [processor.py]
                      └─ self._log.<level>(msg)
```

The `Requests_Logger` (`ghbot.requests`) is a standard Python logger that lives in the
`ghbot.requests` namespace. It is silenced by setting its effective level to
`logging.CRITICAL + 1` (i.e. 51) when `--requests` is not passed. When `--requests` is passed,
its level is left at the root logger's level (`TRACE = 5`), so the console handler's level
governs what appears on stderr.

```mermaid
flowchart TD
    CLI["main() --requests flag"] -->|requests=True/False| CFG["configure()"]
    CFG -->|requests=False| SILENCE["logging.getLogger('ghbot.requests')\n.setLevel(CRITICAL+1)"]
    CFG -->|requests=True| PASS["requests logger inherits root level"]
    GH["github_api_call / callers"] -->|log.debug(...)| REQLOG["ghbot.requests logger"]
    REQLOG --> SILENCE
    REQLOG --> PASS
    PROC["InfoRepoProcessor._fetch_*"] -->|FeedbackEvent(severity='debug')| MON["LoggingMonitor"]
    MON -->|logging.DEBUG| ROOT["root logger → console handler"]
```

---

## Components and Interfaces

### `LoggingMonitor.send_event` (`processor.py`)

**Current** `level_map`:
```python
level_map = {
    "info": self._log.info,
    "warning": self._log.warning,
    "error": self._log.error,
}
```

**After**:
```python
level_map = {
    "debug": self._log.debug,
    "info": self._log.info,
    "warning": self._log.warning,
    "error": self._log.error,
}
```

The fallback (`self._log.warning`) is unchanged — unknown severities still surface at WARNING.

---

### `InfoRepoProcessor` event severity changes (`processor.py`)

#### `run()` — lifecycle events

| Event | Before | After |
|---|---|---|
| `"processing started"` | `"info"` | `"info"` (unchanged) |
| `"processing finished"` | `"info"` | `"debug"` |

#### Per-step progress events (all 8 `_fetch_*` methods)

Every `FeedbackEvent("progress", "info", "fetching …")` call at the top of each fetch method
changes to `FeedbackEvent("progress", "debug", "fetching …")`.

Affected methods: `_fetch_repo_metadata`, `_fetch_file_count`, `_fetch_languages`,
`_fetch_contributors`, `_fetch_latest_release`, `_fetch_open_pull_requests`,
`_fetch_open_issues`, `_fetch_security_alerts`.

#### Empty-state events

| Method | Condition | Before | After |
|---|---|---|---|
| `_fetch_latest_release` | `GitHubNotFoundError` | `"warning"` | `"debug"` |
| `_fetch_languages` | empty response (`not data`) | `"warning"` | `"debug"` |
| `_fetch_languages` | `GitHubNotFoundError` | `"warning"` | `"debug"` |
| `_fetch_security_alerts` | `GitHubNotFoundError` | `"warning"` | `"debug"` |

Error events (`"error"` severity) are unchanged.

---

### `configure()` (`log.py`)

**Signature change**:
```python
def configure(
    console_level: str = "INFO",
    log_file: str | None = None,
    log_level: str = "INFO",
    json_format: bool = False,
    requests: bool = False,          # NEW
) -> None:
```

**New behaviour** — appended after the existing handler setup:
```python
requests_logger = logging.getLogger("ghbot.requests")
if not requests:
    requests_logger.setLevel(logging.CRITICAL + 1)  # silence completely
# When requests=True, the logger inherits root level (TRACE=5) and the
# console handler's own level governs what appears on stderr.
```

Setting the logger's own level (rather than adding a filter to the handler) is the correct
approach: it prevents the log record from being created at all, which is cheaper and avoids
the record reaching any file handler either.

---

### `main()` (`__main__.py`)

**New CLI option**:
```python
@click.option(
    "--requests",
    is_flag=True,
    default=False,
    help="Enable HTTP request/response detail logging (ghbot.requests logger)",
)
```

**Updated `configure()` call**:
```python
configure(
    console_level=console_level,
    log_file=cfg.get("log-file"),
    log_level=cfg.get("log-level", log_level),
    json_format=cfg.get("log-json", False),
    requests=requests,  # NEW
)
```

The `requests` parameter is added to the `main()` function signature alongside the other
existing parameters.

---

### `github_api_call` and its callers (`github/client.py`)

The `github_api_call` context manager currently does not emit any log messages. HTTP
request/response detail logging (requirement 4.4) will be added by having callers (or the
context manager itself) use `get_logger("ghbot.requests")` for any HTTP-layer debug lines.

The context manager is the natural place to add entry/exit logging because it already wraps
every GitHub API call. A minimal implementation:

```python
_requests_log = get_logger("ghbot.requests")


@asynccontextmanager
async def github_api_call(gh):
    _requests_log.debug("github api call starting")
    try:
        yield
        _requests_log.debug("github api call completed")
    except _RETRYABLE as e:
        ...
```

The exact message content is an implementation detail; the key constraint is that the logger
name is `ghbot.requests` and `LoggingMonitor` never uses this logger.

---

## Data Models

No new data models are introduced. The existing `FeedbackEvent` dataclass already accepts any
string for `severity`; the only change is that `"debug"` is now a first-class value in
`LoggingMonitor`'s dispatch map.

The `configure()` function signature gains one `bool` parameter (`requests`). No config file
key is added — `--requests` is a runtime flag only, consistent with `--verbose` and `--quiet`.

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions
of a system — essentially, a formal statement about what the system should do. Properties serve
as the bridge between human-readable specifications and machine-verifiable correctness
guarantees.*

### Property 1: Empty-state conditions emit debug-severity events

*For any* repository where a fetch step encounters an empty-state condition (a
`GitHubNotFoundError` on the releases, languages, or security-alerts endpoint, or an empty
response from the languages endpoint), the `FeedbackEvent` emitted by `InfoRepoProcessor`
SHALL have `severity` equal to `"debug"`.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4**

---

### Property 2: Severity-to-log-level mapping is complete and correct

*For any* `FeedbackEvent` with `severity` in `{"debug", "info", "warning", "error"}`,
`LoggingMonitor.send_event` SHALL log at the corresponding Python level
(`DEBUG`, `INFO`, `WARNING`, `ERROR` respectively). *For any* `FeedbackEvent` with a
severity value outside that set, `LoggingMonitor.send_event` SHALL log at `WARNING`.

**Validates: Requirements 2.2, 5.1, 5.2, 5.3, 5.4, 5.5**

---

### Property 3: Run lifecycle events have correct severities

*For any* `InfoRepoProcessor` run, the first `FeedbackEvent` emitted SHALL have `type`
`"progress"` and `severity` `"info"`, and the last `FeedbackEvent` emitted SHALL have
`type` `"progress"` and `severity` `"debug"`.

**Validates: Requirements 3.1, 3.2**

---

### Property 4: LoggingMonitor never routes to the requests logger

*For any* `FeedbackEvent` sent through `LoggingMonitor.send_event`, no log record SHALL
appear on the `ghbot.requests` logger.

**Validates: Requirement 4.5**

---

## Error Handling

No new error conditions are introduced. The changes are purely to log-level assignments and
logger routing.

- `configure()` is called once at startup in the sync layer; if `logging.getLogger` raises
  (it never does under normal circumstances), the exception propagates to `main()` and the
  process exits with a non-zero code via the existing `FatalError` handler.
- The `--requests` flag is a boolean; Click handles type validation.
- Setting `requests_logger.setLevel(logging.CRITICAL + 1)` is idempotent and safe to call
  multiple times (relevant for tests that call `configure()` repeatedly).

---

## Testing Strategy

### Unit tests

**`tests/unit/test_processor.py`** — extend `TestLoggingMonitor`:

- `test_severity_debug_logs_at_debug`: send a `FeedbackEvent(severity="debug")` and assert
  `record.levelno == logging.DEBUG`. This is a new example-based test for the new map entry.

**`tests/unit/test_info_processor.py`** — add example-based tests for the severity changes:

- For each empty-state condition (4 cases), inject the appropriate error/empty response and
  assert the captured `FeedbackEvent` has `severity="debug"`.
- Assert that `run()` emits `severity="info"` for the start event and `severity="debug"` for
  the finish event.
- Assert that each `_fetch_*` progress event has `severity="debug"`.

**`tests/unit/test_main.py`** — extend CLI tests:

- `test_requests_flag_defaults_false`: invoke `main` without `--requests`, assert
  `configure` is called with `requests=False`.
- `test_requests_flag_true`: invoke `main` with `--requests`, assert `configure` is called
  with `requests=True`.

**`tests/unit/test_log.py`** (new file):

- `test_configure_suppresses_requests_logger_by_default`: call `configure()` without
  `requests=True`, assert `logging.getLogger("ghbot.requests").level > logging.DEBUG`.
- `test_configure_enables_requests_logger_when_flag_set`: call `configure(requests=True)`,
  assert `logging.getLogger("ghbot.requests").level <= logging.DEBUG`.

### Property-based tests

**`tests/unit/test_processor_props.py`** — extend existing property tests:

**Property 1** — Empty-state conditions emit debug severity:

```python
# Feature: output-verbosity, Property 1: Empty-state conditions emit debug-severity events
@settings(max_examples=100)
@given(
    owner=st.text(min_size=1),
    repo=st.text(min_size=1),
    empty_state=st.sampled_from(
        [
            "release_not_found",
            "languages_empty",
            "languages_not_found",
            "security_not_found",
        ]
    ),
)
def test_empty_state_events_are_debug(owner, repo, empty_state): ...
```

For each `empty_state` variant, configure the gh mock to trigger that condition, run the
processor, collect all `FeedbackEvent` objects passed to `monitor.send_event`, and assert
that the empty-state event has `severity == "debug"`.

**Property 2** — Severity-to-log-level mapping (extend existing `test_severity_to_log_level`):

Change `st.sampled_from(["info", "warning", "error"])` to
`st.sampled_from(["debug", "info", "warning", "error"])` and add `"debug": logging.DEBUG`
to `SEVERITY_TO_LEVEL`. The existing test body is otherwise unchanged.

**Property 3** — Run lifecycle events:

```python
# Feature: output-verbosity, Property 3: Run lifecycle events have correct severities
@settings(max_examples=100)
@given(owner=st.text(min_size=1), repo=st.text(min_size=1))
def test_run_lifecycle_event_severities(owner, repo): ...
```

Run the processor with all steps succeeding, collect all `send_event` calls, assert the
first call has `type="progress"` and `severity="info"`, and the last call has
`type="progress"` and `severity="debug"`.

**Property 4** — LoggingMonitor never routes to requests logger:

```python
# Feature: output-verbosity, Property 4: LoggingMonitor never routes to the requests logger
@settings(max_examples=100)
@given(
    event=st.builds(
        FeedbackEvent, type=st.text(), severity=st.text(), message=st.text()
    )
)
def test_logging_monitor_never_uses_requests_logger(event): ...
```

Attach a `MemoryHandler` to `logging.getLogger("ghbot.requests")`, send the event
through `LoggingMonitor`, assert the handler's buffer is empty.

### Test configuration

- All async tests use `@pytest.mark.anyio` with the `asyncio` backend (set in `conftest.py`).
- Property tests use `@settings(max_examples=100)` (Hypothesis).
- Mocking follows the project convention: patch at the import site
  (`ghbot.processor.github_api_call`), use `AsyncMock` for async callables.
- `configure()` tests must reset logger state after each test to avoid cross-test pollution
  (set `logging.getLogger("ghbot.requests").setLevel(logging.NOTSET)` in teardown).
