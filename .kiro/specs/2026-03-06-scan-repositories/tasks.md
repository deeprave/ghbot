# Tasks: Scan Repositories

## Task 1: UnexpectedError in errors.py
- [x] 1.1 Add test in `tests/unit/test_errors.py`: `UnexpectedError` is a subclass of `FatalError`
- [x] 1.2 Add `UnexpectedError(FatalError)` to `src/ghbot/errors.py`

## Task 2: list_repos retry on GitHubApiError
- [x] 2.1 Add tests in `tests/unit/test_repos.py`: first `GitHubApiError` retries; second `GitHubApiError` logs error and skips (no exception propagated)
- [x] 2.2 Update `list_repos` in `src/ghbot/github/repos.py` to retry once on `GitHubApiError`; second failure logs error + returns

## Task 3: config.py — DEFAULTS and recognised keys
- [x] 3.1 Add tests in `tests/unit/test_config.py`: `load_config` parses `owners`, `log-file`, `log-json`, `log-level` from a TOML file; missing file returns `DEFAULTS`
- [x] 3.2 Update `src/ghbot/config.py`: add `owners`, `log-file`, `log-json`, `log-level` to `DEFAULTS` with sensible defaults

## Task 4: main() config merge and _main(cfg) refactor
- [x] 4.1 Add tests in `tests/unit/test_main.py`: CLI `--owner` overrides config file owners; config file overrides defaults; `_main(cfg)` reads `cfg["owners"]` (no separate `owners` param)
- [x] 4.2 Refactor `src/ghbot/__main__.py`: `_main(cfg)` takes only `cfg`; `main()` merges `DEFAULTS → load_config() → CLI flags` into `cfg` before calling `_main(cfg)`

## Task 5: Sequence[str] type annotations
- [x] 5.1 Update `src/ghbot/github/repos.py`: annotate `owners` param of `scan_repositories` as `Sequence[str]`; annotate `list_repos` owner param as `str` (already correct — verify no regressions)
