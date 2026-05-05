"""Tests for processor data types, protocols, and LoggingMonitor."""

import logging

import pytest

from ghbot.processor import (
    FeedbackEvent,
    LoggingMonitor,
    Monitor,
    RepoProcessor,
    RepoResult,
)


class TestFeedbackEvent:
    """Tests for FeedbackEvent frozen dataclass."""

    def test_construction_and_field_access(self) -> None:
        event = FeedbackEvent(type="progress", severity="info", message="started")
        assert event.type == "progress"
        assert event.severity == "info"
        assert event.message == "started"

    def test_frozen_type_raises(self) -> None:
        event = FeedbackEvent(type="progress", severity="info", message="started")
        with pytest.raises(AttributeError):
            event.type = "other"  # type: ignore[misc]

    def test_frozen_severity_raises(self) -> None:
        event = FeedbackEvent(type="progress", severity="info", message="started")
        with pytest.raises(AttributeError):
            event.severity = "error"  # type: ignore[misc]

    def test_frozen_message_raises(self) -> None:
        event = FeedbackEvent(type="progress", severity="info", message="started")
        with pytest.raises(AttributeError):
            event.message = "changed"  # type: ignore[misc]

    def test_equality(self) -> None:
        a = FeedbackEvent(type="progress", severity="info", message="hi")
        b = FeedbackEvent(type="progress", severity="info", message="hi")
        assert a == b

    def test_inequality(self) -> None:
        a = FeedbackEvent(type="progress", severity="info", message="hi")
        b = FeedbackEvent(type="error", severity="error", message="fail")
        assert a != b


class TestRepoResult:
    """Tests for RepoResult dataclass."""

    def test_construction_with_required_fields(self) -> None:
        result = RepoResult(owner="acme", repo="widgets")
        assert result.owner == "acme"
        assert result.repo == "widgets"

    def test_defaults(self) -> None:
        result = RepoResult(owner="acme", repo="widgets")
        assert result.status == "success"
        assert result.errors == []
        assert result.results == {}

    def test_status_mutation(self) -> None:
        result = RepoResult(owner="acme", repo="widgets")
        result.status = "partial"
        assert result.status == "partial"

    def test_errors_list_accumulation(self) -> None:
        result = RepoResult(owner="acme", repo="widgets")
        result.errors.append("fetch failed")
        result.errors.append("timeout")
        assert result.errors == ["fetch failed", "timeout"]

    def test_results_dict_population(self) -> None:
        result = RepoResult(owner="acme", repo="widgets")
        result.results["languages"] = {"Python": 100}
        result.results["file_count"] = 42
        assert result.results["languages"] == {"Python": 100}
        assert result.results["file_count"] == 42

    def test_errors_default_factory_isolation(self) -> None:
        """Each instance gets its own errors list."""
        a = RepoResult(owner="a", repo="r")
        b = RepoResult(owner="b", repo="r")
        a.errors.append("oops")
        assert b.errors == []

    def test_results_default_factory_isolation(self) -> None:
        """Each instance gets its own results dict."""
        a = RepoResult(owner="a", repo="r")
        b = RepoResult(owner="b", repo="r")
        a.results["key"] = "val"
        assert b.results == {}

    def test_explicit_status_construction(self) -> None:
        result = RepoResult(owner="acme", repo="widgets", status="failed")
        assert result.status == "failed"


class TestMonitorProtocol:
    """Tests for Monitor runtime-checkable protocol."""

    def test_conforming_class_passes_isinstance(self) -> None:
        class _Good:
            async def send_event(self, event: FeedbackEvent) -> None: ...

        assert isinstance(_Good(), Monitor)

    def test_non_conforming_class_fails_isinstance(self) -> None:
        class _Bad:
            def not_send_event(self) -> None: ...

        assert not isinstance(_Bad(), Monitor)


class TestRepoProcessorProtocol:
    """Tests for RepoProcessor runtime-checkable protocol."""

    def test_conforming_class_passes_isinstance(self) -> None:
        class _Good:
            @property
            def owner(self) -> str:
                return "acme"

            @property
            def repo(self) -> str:
                return "widgets"

            async def run(self) -> RepoResult:
                return RepoResult(owner=self.owner, repo=self.repo)

        assert isinstance(_Good(), RepoProcessor)

    def test_non_conforming_class_fails_isinstance(self) -> None:
        class _Bad:
            def something_else(self) -> None: ...

        assert not isinstance(_Bad(), RepoProcessor)


class TestLoggingMonitor:
    """Tests for LoggingMonitor concrete implementation."""

    _LOGGER = "ghbot.processor.acme/widgets"

    def _monitor_records(
        self, caplog: pytest.LogCaptureFixture
    ) -> list[logging.LogRecord]:
        """Return only log records from the monitor's logger."""
        return [r for r in caplog.records if r.name == self._LOGGER]

    def test_isinstance_monitor(self) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        assert isinstance(monitor, Monitor)

    @pytest.mark.anyio
    async def test_severity_debug_logs_at_debug(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        event = FeedbackEvent(
            type="progress", severity="debug", message="some debug message"
        )
        with caplog.at_level(logging.DEBUG, logger=self._LOGGER):
            await monitor.send_event(event)
        records = self._monitor_records(caplog)
        assert len(records) == 1
        assert records[0].levelno == logging.DEBUG

    @pytest.mark.anyio
    async def test_severity_info_logs_at_info(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        event = FeedbackEvent(type="progress", severity="info", message="started")
        with caplog.at_level(logging.DEBUG, logger=self._LOGGER):
            await monitor.send_event(event)
        records = self._monitor_records(caplog)
        assert len(records) == 1
        assert records[0].levelno == logging.INFO

    @pytest.mark.anyio
    async def test_severity_warning_logs_at_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        event = FeedbackEvent(type="fetch", severity="warning", message="no releases")
        with caplog.at_level(logging.DEBUG, logger=self._LOGGER):
            await monitor.send_event(event)
        records = self._monitor_records(caplog)
        assert len(records) == 1
        assert records[0].levelno == logging.WARNING

    @pytest.mark.anyio
    async def test_severity_error_logs_at_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        event = FeedbackEvent(type="fetch", severity="error", message="api failed")
        with caplog.at_level(logging.DEBUG, logger=self._LOGGER):
            await monitor.send_event(event)
        records = self._monitor_records(caplog)
        assert len(records) == 1
        assert records[0].levelno == logging.ERROR

    @pytest.mark.anyio
    async def test_unknown_severity_falls_back_to_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        event = FeedbackEvent(type="fetch", severity="critical", message="unknown sev")
        with caplog.at_level(logging.DEBUG, logger=self._LOGGER):
            await monitor.send_event(event)
        records = self._monitor_records(caplog)
        assert len(records) == 1
        assert records[0].levelno == logging.WARNING

    def test_logger_name_includes_owner_and_repo(self) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        assert "acme/widgets" in monitor._log.name  # type: ignore[attr-defined]

    @pytest.mark.anyio
    async def test_log_message_contains_owner_and_repo(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        event = FeedbackEvent(type="progress", severity="info", message="hello")
        with caplog.at_level(logging.DEBUG, logger=self._LOGGER):
            await monitor.send_event(event)
        records = self._monitor_records(caplog)
        assert "acme" in records[0].message
        assert "widgets" in records[0].message
