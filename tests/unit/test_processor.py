"""Tests for processor data types, protocols, and LoggingMonitor."""

import logging

import pytest

from ghbot.processor import (
    FeedbackEvent,
    LoggingMonitor,
    Monitor,
    RepoResult,
    UnavailableMetric,
)


def test_repo_result_preserves_unavailable_metric_metadata():
    result = RepoResult(owner="acme", repo="widgets")
    result.unavailable["dependabot_alerts"] = UnavailableMetric(
        reason="forbidden", message="Resource not accessible by integration"
    )

    assert result.unavailable["dependabot_alerts"].reason == "forbidden"
    assert result.unavailable["dependabot_alerts"].message == (
        "Resource not accessible by integration"
    )


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
    @pytest.mark.parametrize(
        ("event", "expected_level"),
        [
            (FeedbackEvent("progress", "debug", "debug"), logging.DEBUG),
            (FeedbackEvent("progress", "info", "info"), logging.INFO),
            (FeedbackEvent("fetch", "warning", "warning"), logging.WARNING),
            (FeedbackEvent("fetch", "error", "error"), logging.ERROR),
            (FeedbackEvent("fetch", "critical", "unknown"), logging.WARNING),
        ],
    )
    async def test_severity_maps_to_expected_log_level(
        self,
        caplog: pytest.LogCaptureFixture,
        event: FeedbackEvent,
        expected_level: int,
    ) -> None:
        monitor = LoggingMonitor(owner="acme", repo="widgets")
        with caplog.at_level(logging.DEBUG, logger=self._LOGGER):
            await monitor.send_event(event)
        records = self._monitor_records(caplog)
        assert len(records) == 1
        assert records[0].levelno == expected_level

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
