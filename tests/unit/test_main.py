import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner
import gidgethub.httpx as gh_httpx

from ghbot.processor import InfoRepoProcessor, SecurityRepoProcessor


async def _scan_stub(owners, gh):
    yield "owner1", {"name": "repo1"}


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
        "owner1", "repo1", mock_gh, mock_monitor, options=None
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
        "owner1", "repo1", mock_gh, mock_monitor, options=options
    )


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


def test_security_subcommand_calls_main_with_security_processor():
    """ghbot security → _main called with SecurityRepoProcessor."""
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])) as mock_main,
        patch("ghbot.__main__.configure"),
        patch("ghbot.__main__.print_security_report"),
    ):
        from ghbot.__main__ import cli

        CliRunner().invoke(cli, ["security"])
    mock_main.assert_called_once()
    _, processor_cls = mock_main.call_args[0]
    assert processor_cls is SecurityRepoProcessor


def test_security_subcommand_calls_print_security_report():
    """ghbot security → print_security_report called with pool.results."""
    from ghbot.processor import RepoResult

    fake_results = [RepoResult(owner="o", repo="r")]
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=fake_results)),
        patch("ghbot.__main__.configure"),
        patch("ghbot.__main__.print_security_report") as mock_report,
    ):
        from ghbot.__main__ import cli

        CliRunner().invoke(cli, ["security"])
    mock_report.assert_called_once_with(fake_results, format="plain", output=None)


def test_security_subcommand_default_passes_plain_format_options():
    """ghbot security defaults to plain output format."""
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])) as mock_main,
        patch("ghbot.__main__.configure"),
        patch("ghbot.__main__.print_security_report"),
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["security"])
    assert result.exit_code == 0
    assert mock_main.call_args.kwargs["options"] == {"format": "plain"}


@pytest.mark.parametrize(
    ("flag", "expected"),
    [("--plain", "plain"), ("--table", "table"), ("--json", "json")],
)
def test_security_subcommand_format_flags_pass_options(flag, expected):
    """Security format flags pass reusable output options."""
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])) as mock_main,
        patch("ghbot.__main__.configure"),
        patch("ghbot.__main__.print_security_report") as mock_report,
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(cli, ["security", flag])
    assert result.exit_code == 0
    assert mock_main.call_args.kwargs["options"] == {"format": expected}
    assert mock_report.call_args.kwargs["format"] == expected


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


def test_security_subcommand_passes_output_to_report(tmp_path):
    """--output controls only the final security report destination."""
    output = tmp_path / "security.json"
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])),
        patch("ghbot.__main__.configure"),
        patch("ghbot.__main__.print_security_report") as mock_report,
    ):
        from ghbot.__main__ import cli

        result = CliRunner().invoke(
            cli, ["security", "--json", "--output", str(output)]
        )
    assert result.exit_code == 0
    assert mock_report.call_args.kwargs["output"] == output


def test_info_subcommand_does_not_call_print_security_report():
    """ghbot info → print_security_report not called."""
    with (
        patch("ghbot.__main__._main", new=AsyncMock(return_value=[])),
        patch("ghbot.__main__.configure"),
        patch("ghbot.__main__.print_security_report") as mock_report,
    ):
        from ghbot.__main__ import cli

        CliRunner().invoke(cli, ["info"])
    mock_report.assert_not_called()


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
