from ghbot.config import DEFAULTS, load_config


def test_defaults_has_required_keys():
    for key in ("owners", "log-file", "log-json", "log-level", "concurrency"):
        assert key in DEFAULTS


def test_defaults_concurrency_is_16():
    assert DEFAULTS["concurrency"] == 16


def test_load_config_missing_file_returns_defaults(tmp_path):
    result = load_config(str(tmp_path / "nonexistent.toml"))
    assert result == DEFAULTS


def test_load_config_parses_all_keys(tmp_path):
    cfg_file = tmp_path / "ghbot.toml"
    cfg_file.write_text(
        'owners = "owner1,owner2"\nlog-file = "/tmp/fix.log"\nlog-json = true\nlog-level = "debug"\nconcurrency = 8\n'
    )
    result = load_config(str(cfg_file))
    assert result["owners"] == "owner1,owner2"
    assert result["log-file"] == "/tmp/fix.log"
    assert result["log-json"] is True
    assert result["log-level"] == "debug"
    assert result["concurrency"] == 8
