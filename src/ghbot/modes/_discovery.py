"""Discovery of trusted, built-in ghbot mode definitions."""

import importlib
import pkgutil
from typing import Any, Protocol, runtime_checkable

import click

from ghbot import modes as modes_package


class ModeDiscoveryError(RuntimeError):
    """A built-in mode module does not meet the discovery contract."""


@runtime_checkable
class ModeDefinition(Protocol):
    """Common interface exposed by every discoverable built-in mode."""

    name: str
    command: click.Command
    combinable: bool

    def new_processor(
        self,
        owner: str,
        repo: str,
        gh: Any,
        monitor: Any,
        options: dict,
        *,
        owner_type: str | None = None,
    ) -> Any: ...


@runtime_checkable
class ReportableModeDefinition(ModeDefinition, Protocol):
    """Discovery contract for modes with a collection-level report."""

    def new_collection(self, options: dict) -> Any: ...


def validate_mode(module_name: str, candidate: object) -> ModeDefinition:
    """Validate one module's exported mode definition."""
    name = getattr(candidate, "name", None)
    if not isinstance(name, str) or not name:
        raise ModeDiscoveryError(f"{module_name}: MODE must define a non-empty name")

    command = getattr(candidate, "command", None)
    if not isinstance(command, click.Command):
        raise ModeDiscoveryError(f"{module_name}: MODE must define a Click command")
    if command.name != name:
        raise ModeDiscoveryError(
            f"{module_name}: MODE command name {command.name!r} does not match {name!r}"
        )

    if not isinstance(getattr(candidate, "combinable", None), bool):
        raise ModeDiscoveryError(
            f"{module_name}: MODE must define a boolean combinable flag"
        )
    if not callable(getattr(candidate, "new_processor", None)):
        raise ModeDiscoveryError(f"{module_name}: MODE must define new_processor")
    if not isinstance(candidate, ModeDefinition):
        raise ModeDiscoveryError(
            f"{module_name}: MODE does not satisfy the mode definition"
        )
    if candidate.combinable and not isinstance(candidate, ReportableModeDefinition):
        raise ModeDiscoveryError(
            f"{module_name}: combinable MODE must define new_collection"
        )
    return candidate


def discover_modes() -> tuple[ModeDefinition, ...]:
    """Return validated built-in modes in deterministic canonical-name order."""
    definitions: list[ModeDefinition] = []
    names: set[str] = set()
    prefix = f"{modes_package.__name__}."
    for module_info in pkgutil.iter_modules(modes_package.__path__, prefix):
        short_name = module_info.name.removeprefix(prefix)
        if module_info.ispkg or short_name.startswith("_"):
            continue
        try:
            module = importlib.import_module(module_info.name)
        except Exception as error:
            raise ModeDiscoveryError(
                f"unable to import built-in mode {module_info.name}: {error}"
            ) from error
        try:
            mode = validate_mode(module_info.name, module.MODE)
        except AttributeError as error:
            raise ModeDiscoveryError(
                f"{module_info.name}: module must export MODE"
            ) from error
        if mode.name in names:
            raise ModeDiscoveryError(f"duplicate built-in mode name: {mode.name}")
        names.add(mode.name)
        definitions.append(mode)
    return tuple(sorted(definitions, key=lambda mode: mode.name))


def combinable_modes() -> tuple[ReportableModeDefinition, ...]:
    """Return discovered modes eligible for a future combined scan."""
    modes: list[ReportableModeDefinition] = []
    for mode in discover_modes():
        if not mode.combinable:
            continue
        assert isinstance(mode, ReportableModeDefinition)
        modes.append(mode)
    return tuple(modes)
