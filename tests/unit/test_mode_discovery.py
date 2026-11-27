"""Tests for trusted built-in mode discovery and validation."""

from types import SimpleNamespace

import click
import pytest


def test_discover_modes_returns_all_builtins_in_canonical_order():
    from ghbot.modes import discover_modes

    modes = discover_modes()

    assert [mode.name for mode in modes] == [
        "drift",
        "info",
        "issues",
        "security",
        "settings",
    ]
    assert [mode.command.name for mode in modes] == [
        "drift",
        "info",
        "issues",
        "security",
        "settings",
    ]


def test_combinable_modes_excludes_unkeyed_info_in_combine_key_order():
    from ghbot.modes import ReportableModeDefinition, combinable_modes

    modes = combinable_modes()

    assert [mode.name for mode in modes] == ["security", "issues", "drift"]
    assert [mode.combine_key for mode in modes] == ["010", "020", "030"]
    assert all(isinstance(mode, ReportableModeDefinition) for mode in modes)


@pytest.mark.parametrize(
    ("mode", "message"),
    [
        (SimpleNamespace(), "MODE"),
        (
            SimpleNamespace(name="", command=click.Command("empty")),
            "name",
        ),
        (
            SimpleNamespace(name="different", command=click.Command("command")),
            "command",
        ),
        (
            SimpleNamespace(
                name="report",
                command=click.Command("report"),
                new_processor=lambda *_args, **_kwargs: None,
                combine_key="010",
            ),
            "new_collection",
        ),
        (
            SimpleNamespace(
                name="report",
                command=click.Command("report"),
                new_processor=lambda *_args, **_kwargs: None,
                new_collection=lambda _options: None,
                combine_key="10",
            ),
            "combine_key",
        ),
    ],
)
def test_invalid_mode_definition_is_actionable(mode, message):
    from ghbot.modes._discovery import ModeDiscoveryError, validate_mode

    with pytest.raises(ModeDiscoveryError, match=message):
        validate_mode("ghbot.modes.invalid", mode)


def test_unkeyed_mode_is_valid_but_not_reportable():
    from ghbot.modes._discovery import validate_mode

    candidate = SimpleNamespace(
        name="info",
        command=click.Command("info"),
        new_processor=lambda *_args, **_kwargs: None,
    )

    assert validate_mode("ghbot.modes.info", candidate) is candidate


def test_combinable_modes_rejects_duplicate_combine_keys(monkeypatch):
    from ghbot.modes import _discovery
    from ghbot.modes._discovery import ModeDiscoveryError

    def mode(name):
        return SimpleNamespace(
            name=name,
            command=click.Command(name),
            new_processor=lambda *_args, **_kwargs: None,
            new_collection=lambda _options: None,
            combine_key="010",
        )

    monkeypatch.setattr(
        _discovery, "discover_modes", lambda: (mode("one"), mode("two"))
    )

    with pytest.raises(ModeDiscoveryError, match="combine_key"):
        _discovery.combinable_modes()


def test_discovery_rejects_duplicate_names(monkeypatch):
    from ghbot.modes import _discovery
    from ghbot.modes._discovery import ModeDiscoveryError

    @click.command(name="duplicate")
    def command() -> None: ...

    first = SimpleNamespace(
        MODE=SimpleNamespace(
            name="duplicate",
            command=command,
            new_processor=lambda *_args, **_kwargs: None,
            new_collection=lambda _options: None,
            combine_key="010",
        )
    )
    second = SimpleNamespace(
        MODE=SimpleNamespace(
            name="duplicate",
            command=command,
            new_processor=lambda *_args, **_kwargs: None,
            new_collection=lambda _options: None,
            combine_key="010",
        )
    )
    modules = iter(
        [
            SimpleNamespace(name="first", ispkg=False),
            SimpleNamespace(name="second", ispkg=False),
        ]
    )

    monkeypatch.setattr(_discovery.pkgutil, "iter_modules", lambda *_: modules)
    monkeypatch.setattr(
        _discovery.importlib,
        "import_module",
        lambda name: first if name.endswith("first") else second,
    )

    with pytest.raises(ModeDiscoveryError, match="duplicate"):
        _discovery.discover_modes()


def test_discovery_wraps_builtin_import_error(monkeypatch):
    from ghbot.modes import _discovery
    from ghbot.modes._discovery import ModeDiscoveryError

    modules = iter([SimpleNamespace(name="broken", ispkg=False)])
    monkeypatch.setattr(_discovery.pkgutil, "iter_modules", lambda *_: modules)

    def fail_import(name):
        if name == "ghbot.modes":
            return _discovery.modes_package
        raise ImportError("missing dependency")

    monkeypatch.setattr(_discovery.importlib, "import_module", fail_import)

    with pytest.raises(ModeDiscoveryError, match="broken"):
        _discovery.discover_modes()
