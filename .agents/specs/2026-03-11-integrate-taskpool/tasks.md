# Tasks: Integrate TaskPool

## Task 1: process_repo in repos.py
- [x] 1.1 Add test in `tests/unit/test_repos.py`: `process_repo(owner, repo, gh)` returns `{"owner": owner, "repo": repo["name"]}`
- [x] 1.2 Add `process_repo` to `src/ghbot/github/repos.py`

## Task 2: DEFAULTS["concurrency"] in config.py
- [x] 2.1 Add test in `tests/unit/test_config.py`: `DEFAULTS["concurrency"]` is `16`; config file `concurrency` key is parsed as int
- [x] 2.2 Add `"concurrency": 16` to `DEFAULTS` in `src/ghbot/config.py`

## Task 3: --concurrency CLI flag and cfg merge in main()
- [x] 3.1 Add tests in `tests/unit/test_main.py`: CLI `--concurrency` overrides config file value; config file overrides default; omitting flag leaves default
- [x] 3.2 Add `--concurrency` option to `main()` in `src/ghbot/__main__.py`; merge with `if concurrency is not None: cfg["concurrency"] = concurrency`

## Task 4: Wire TaskPool into _main
- [x] 4.1 Add tests in `tests/unit/test_main.py`: `_main` creates `TaskPool` with `limit=cfg["concurrency"]`; submits `process_repo` for each `(owner, repo)`; logs `pool.stats` at INFO after pool exits
- [x] 4.2 Update `_main` in `src/ghbot/__main__.py`: wrap scan loop in `TaskPool`, submit `process_repo`, log stats after exit
