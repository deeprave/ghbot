import logging
from unittest.mock import AsyncMock, MagicMock, patch

import gidgethub.httpx as gh_httpx
import pytest
from click.testing import CliRunner

from ghbot.github.repos import DiscoveredRepository
from ghbot.modes.drift import DriftRepoProcessor
from ghbot.modes.security import SecurityRepoProcessor
from ghbot.processor import InfoRepoProcessor


async def _scan_stub(owners, gh):
    yield DiscoveredRepository("owner1", {"name": "repo1"}, "User")


async def _empty_scan(owners, gh):
    return
    yield


# ---------------------------------------------------------------------------
# _main — core async loop (processor_cls-agnostic)
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_main_reads_owners_from_cfg():
    """_main(cfg, processor_cls) reads owners from cfg["owners"]."""
    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {}
    mock_pool.results = []
    with (
        patch("ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")),
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_scan_stub) as mock_scan,
        patch("ghbot.__main__.TaskPool", return_value=mock_pool),
    ):
        from ghbot.__main__ import _main

        await _main({"owners": ["owner1"], "concurrency": 16}, InfoRepoProcessor)
    mock_scan.assert_called_once_with(["owner1"], mock_gh)


@pytest.mark.anyio
async def test_main_uses_environment_token_when_selected():
    """_main selects the environment source only when configured by the CLI."""
    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {}
    mock_pool.results = []
    with (
        patch(
            "ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")
        ) as mock_auth,
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_empty_scan),
        patch("ghbot.__main__.TaskPool", return_value=mock_pool),
    ):
        from ghbot.__main__ import _main

        await _main(
            {"owners": [], "concurrency": 16, "env": True},
            InfoRepoProcessor,
        )

    mock_auth.assert_awaited_once_with(use_environment=True)


@pytest.mark.anyio
async def test_main_defaults_to_gh_token_authentication():
    """Without -e/--env, _main keeps the existing gh token behaviour."""
    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {}
    mock_pool.results = []
    with (
        patch(
            "ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")
        ) as mock_auth,
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_empty_scan),
        patch("ghbot.__main__.TaskPool", return_value=mock_pool),
    ):
        from ghbot.__main__ import _main

        await _main({"owners": [], "concurrency": 16}, InfoRepoProcessor)

    mock_auth.assert_awaited_once_with(use_environment=False)


@pytest.mark.anyio
async def test_main_creates_taskpool_with_concurrency():
    """_main creates TaskPool with limit=cfg["concurrency"]."""
    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {}
    mock_pool.results = []
    with (
        patch("ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")),
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_empty_scan),
        patch("ghbot.__main__.TaskPool", return_value=mock_pool) as mock_tp,
    ):
        from ghbot.__main__ import _main

        await _main({"owners": [], "concurrency": 8}, InfoRepoProcessor)
    mock_tp.assert_called_once_with(limit=8)


@pytest.mark.anyio
async def test_main_submits_processor_run_for_each_repo():
    """_main constructs processor_cls per repo and submits processor.run."""
    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {}
    mock_pool.results = []
    mock_monitor = AsyncMock()
    mock_processor = AsyncMock()
    mock_processor.run = AsyncMock()
    mock_processor_cls = MagicMock(return_value=mock_processor)
    with (
        patch("ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")),
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_scan_stub),
        patch("ghbot.__main__.TaskPool", return_value=mock_pool),
        patch("ghbot.__main__.LoggingMonitor", return_value=mock_monitor) as mock_lm,
    ):
        from ghbot.__main__ import _main

        await _main({"owners": ["owner1"], "concurrency": 16}, mock_processor_cls)
    mock_lm.assert_called_once_with("owner1", "repo1")
    mock_processor_cls.assert_called_once_with(
        "owner1", "repo1", mock_gh, mock_monitor, options=None, owner_type="User"
    )
    mock_pool.submit.assert_called_once_with(mock_processor.run)


@pytest.mark.anyio
async def test_main_passes_options_to_processor_constructor():
    """_main passes generic command options to processor constructors."""
    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {}
    mock_pool.results = []
    mock_monitor = AsyncMock()
    mock_processor = AsyncMock()
    mock_processor.run = AsyncMock()
    mock_processor_cls = MagicMock(return_value=mock_processor)
    options = {"format": "json"}
    with (
        patch("ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")),
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_scan_stub),
        patch("ghbot.__main__.TaskPool", return_value=mock_pool),
        patch("ghbot.__main__.LoggingMonitor", return_value=mock_monitor),
    ):
        from ghbot.__main__ import _main

        await _main(
            {"owners": ["owner1"], "concurrency": 16},
            mock_processor_cls,
            options=options,
        )
    mock_processor_cls.assert_called_once_with(
        "owner1", "repo1", mock_gh, mock_monitor, options=options, owner_type="User"
    )


@pytest.mark.anyio
async def test_main_passes_discovered_owner_type_as_keyword_only_argument():
    """_main preserves command options while forwarding the discovery owner type."""
    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {}
    mock_pool.results = []
    mock_monitor = AsyncMock()
    mock_processor = AsyncMock()
    mock_processor.run = AsyncMock()
    mock_processor_cls = MagicMock(return_value=mock_processor)

    async def _scan_organisation(owners, gh):
        yield DiscoveredRepository("acme", {"name": "private"}, "Organization")

    with (
        patch("ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")),
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_scan_organisation),
        patch("ghbot.__main__.TaskPool", return_value=mock_pool),
        patch("ghbot.__main__.LoggingMonitor", return_value=mock_monitor),
    ):
        from ghbot.__main__ import _main

        await _main(
            {"owners": ["acme"], "concurrency": 16},
            mock_processor_cls,
            options={"format": "json"},
        )

    mock_processor_cls.assert_called_once_with(
        "acme",
        "private",
        mock_gh,
        mock_monitor,
        options={"format": "json"},
        owner_type="Organization",
    )


@pytest.mark.anyio
async def test_run_mode_constructs_mode_processor_and_collects_inside_pool_task():
    from ghbot.__main__ import _run_mode
    from ghbot.processor import RepoResult

    class ImmediatePool:
        def __init__(self):
            self.stats = {}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def submit(self, fn):
            await fn()

    async def scan(owners, gh):
        yield DiscoveredRepository("acme", {"name": "api"}, "Organization")

    result = RepoResult(owner="acme", repo="api")
    processor = MagicMock()
    processor.run = AsyncMock(return_value=result)
    collection = MagicMock()
    mode = MagicMock()
    mode.new_collection.return_value = collection
    mode.new_processor.return_value = processor

    with (
        patch("ghbot.__main__.get_auth_token", new=AsyncMock(return_value="token")),
        patch("ghbot.__main__.gh_httpx.GitHubAPI"),
        patch("ghbot.__main__.scan_repositories", side_effect=scan),
        patch("ghbot.__main__.TaskPool", return_value=ImmediatePool()),
    ):
        await _run_mode({"owners": ["acme"], "concurrency": 1}, mode, {"x": 1})

    mode.new_processor.assert_called_once()
    collection.add.assert_called_once_with(result)


def test_builtin_processors_default_owner_type_to_none():
    """Built-in processors remain directly constructible without owner type."""
    from ghbot.modes.issues import IssuesRepoProcessor

    gh = MagicMock()
    monitor = AsyncMock()
    for processor_cls in (
        InfoRepoProcessor,
        SecurityRepoProcessor,
        IssuesRepoProcessor,
        DriftRepoProcessor,
    ):
        assert processor_cls("acme", "widgets", gh, monitor).owner_type is None


@pytest.mark.anyio
async def test_main_logs_pool_stats_at_info(caplog):
    """_main logs pool.stats at INFO after pool exits."""
    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {"completed": 1, "not_found": 0}
    mock_pool.results = []
    with (
        patch("ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")),
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_empty_scan),
        patch("ghbot.__main__.TaskPool", return_value=mock_pool),
        caplog.at_level(logging.INFO),
    ):
        from ghbot.__main__ import _main

        await _main({"owners": [], "concurrency": 16}, InfoRepoProcessor)
    assert any("stats" in r.message for r in caplog.records)


@pytest.mark.anyio
async def test_main_returns_pool_results():
    """_main returns pool.results."""
    from ghbot.processor import RepoResult

    mock_gh = MagicMock(spec=gh_httpx.GitHubAPI)
    mock_pool = AsyncMock()
    mock_pool.__aenter__ = AsyncMock(return_value=mock_pool)
    mock_pool.__aexit__ = AsyncMock(return_value=False)
    mock_pool.stats = {}
    mock_pool.results = [RepoResult(owner="o", repo="r")]
    with (
        patch("ghbot.__main__.get_auth_token", new=AsyncMock(return_value="tok")),
        patch("ghbot.__main__.gh_httpx.GitHubAPI", return_value=mock_gh),
        patch("ghbot.__main__.scan_repositories", side_effect=_empty_scan),
        patch("ghbot.__main__.TaskPool", return_value=mock_pool),
    ):
        from ghbot.__main__ import _main

        results = await _main({"owners": [], "concurrency": 16}, InfoRepoProcessor)
    assert results == mock_pool.results


# ---------------------------------------------------------------------------
# CLI group — subcommand routing
# ---------------------------------------------------------------------------


def test_no_subcommand_exits_nonzero():
    """ghbot with no subcommand exits non-zero."""
    from ghbot.__main__ import cli

    result = CliRunner().invoke(cli, [])
    assert result.exit_code != 0


def test_info_subcommand_calls_main_with_info_processor():
    """ghbot info → _main called with InfoRepoProcessor."""
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])) as mock_main,
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        CliRunner().invoke(cli, ["info"])
    mock_main.assert_called_once()
    _, processor_cls = mock_main.call_args[0]
    assert processor_cls is InfoRepoProcessor


def test_env_flag_selects_environment_authentication():
    """The global -e/--env flag is passed to the main loop."""
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])) as mock_main,
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--env", "info"])

    assert result.exit_code == 0
    assert mock_main.call_args.args[0]["env"] is True


@pytest.mark.parametrize(
    ("command", "mode", "options"),
    [
        ("security", "SECURITY_MODE", {"format": "plain"}),
        ("issues", "ISSUES_MODE", {"labels": False}),
        ("drift", "DRIFT_MODE", {"format": "plain"}),
    ],
)
def test_report_commands_resolve_mode_before_scanning(command, mode, options):
    with (
        patch("ghbot.__main__._run_mode", new=AsyncMock()) as run_mode,
        patch("ghbot.__main__.write_report"),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot import __main__

        run_mode.return_value = MagicMock()
        run_mode.return_value.render.return_value = "report\n"
        result = CliRunner().invoke(__main__.cli, [command])

    assert result.exit_code == 0
    assert run_mode.call_args.args[1] is getattr(__main__, mode)
    assert run_mode.call_args.args[2] == options


def test_security_subcommand_rejects_multiple_format_flags():
    """Security format flags are mutually exclusive."""
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])) as mock_main,
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["security", "--json", "--table"])
    assert result.exit_code != 0
    assert "choose only one" in result.output.lower()
    mock_main.assert_not_called()


@pytest.mark.parametrize("flag", ["--plain", "--table", "--json"])
def test_info_subcommand_rejects_security_format_flags(flag):
    """Security output flags are not global and do not apply to info."""
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])) as mock_main,
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["info", flag])
    assert result.exit_code != 0
    mock_main.assert_not_called()


def test_issues_subcommand_rejects_multiple_format_flags():
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["issues", "--json", "--table"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# CLI group — global options still work
# ---------------------------------------------------------------------------


def test_cli_owner_overrides_config_file(tmp_path):
    """CLI --owner wins over config file owners."""
    cfg_file = tmp_path / "ghbot.toml"
    cfg_file.write_text('owners = "config-owner"\n')
    captured = {}

    async def _capture(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.__main__._main", side_effect=_capture),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(
            cli, ["--config", str(cfg_file), "--owner", "cli-owner", "info"]
        )
    assert result.exit_code == 0
    assert captured["owners"] == ["cli-owner"]


def test_config_file_overrides_defaults(tmp_path):
    """Config file owners override DEFAULTS."""
    cfg_file = tmp_path / "ghbot.toml"
    cfg_file.write_text('owners = "file-owner"\n')
    captured = {}

    async def _capture(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.__main__._main", side_effect=_capture),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--config", str(cfg_file), "info"])
    assert result.exit_code == 0
    assert "file-owner" in captured["owners"]


def test_config_env_true_selects_environment_authentication(tmp_path):
    """env = true persists environment-token mode without a CLI flag."""
    cfg_file = tmp_path / "ghbot.toml"
    cfg_file.write_text("env = true\n")
    captured = {}

    async def _capture(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.__main__._main", side_effect=_capture),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--config", str(cfg_file), "info"])

    assert result.exit_code == 0
    assert captured["env"] is True


def test_no_env_flag_overrides_configured_environment_authentication(tmp_path):
    """--no-env restores gh authentication for one configured environment run."""
    cfg_file = tmp_path / "ghbot.toml"
    cfg_file.write_text("env = true\n")
    captured = {}

    async def _capture(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.__main__._main", side_effect=_capture),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(
            cli, ["--config", str(cfg_file), "--no-env", "info"]
        )

    assert result.exit_code == 0
    assert captured["env"] is False


def test_cli_concurrency_overrides_config_file(tmp_path):
    """CLI --concurrency wins over config file."""
    cfg_file = tmp_path / "ghbot.toml"
    cfg_file.write_text("concurrency = 4\n")
    captured = {}

    async def _capture(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.__main__._main", side_effect=_capture),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(
            cli, ["--config", str(cfg_file), "--concurrency", "8", "info"]
        )
    assert result.exit_code == 0
    assert captured["concurrency"] == 8


def test_omitting_concurrency_uses_default(tmp_path):
    """Omitting --concurrency leaves cfg["concurrency"] at 16."""
    cfg_file = tmp_path / "ghbot.toml"
    cfg_file.write_text("")
    captured = {}

    async def _capture(cfg, processor_cls):
        captured.update(cfg)
        return []

    with (
        patch("ghbot.__main__._main", side_effect=_capture),
        patch("ghbot.__main__.configure"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--config", str(cfg_file), "info"])
    assert result.exit_code == 0
    assert captured["concurrency"] == 16


def test_requests_flag_defaults_false():
    """Invoking cli without --requests calls configure with requests=False."""
    with (
        patch("ghbot.__main__.configure") as mock_configure,
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["info"])
    assert result.exit_code == 0
    mock_configure.assert_called_once()
    _, kwargs = mock_configure.call_args
    assert kwargs.get("requests") is False


def test_requests_flag_true():
    """Invoking cli with --requests calls configure with requests=True."""
    with (
        patch("ghbot.__main__.configure") as mock_configure,
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["--requests", "info"])
    assert result.exit_code == 0
    mock_configure.assert_called_once()
    _, kwargs = mock_configure.call_args
    assert kwargs.get("requests") is True
